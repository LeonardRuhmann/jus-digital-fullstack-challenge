import logging
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    BulkDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.ai_service import AIAnalysisError, ai_service
from app.services.s3_service import s3_service
from app.services.text_extractor import extract_content, validate_file

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Orchestrates document validation, S3 storage, database persistence,
    and OpenAI GPT-4o-mini analysis (including retry on AI failure).
    """

    def create_and_analyze_document(
        self,
        db: Session,
        user: User,
        filename: str | None,
        file_bytes: bytes,
        title: str,
        instruction: str,
    ) -> DocumentResponse:
        clean_title = title.strip()
        clean_instruction = instruction.strip()

        if not clean_title:
            raise ValidationException("O campo 'Título' é obrigatório.")
        if len(clean_title) > 255:
            raise ValidationException("O título deve ter no máximo 255 caracteres.")
        if not clean_instruction:
            raise ValidationException("O campo 'Instrução para IA' é obrigatório.")
        if len(clean_instruction) > 5000:
            raise ValidationException(
                "A instrução para a IA deve ter no máximo 5000 caracteres."
            )

        safe_filename, ext, resolved_mime = validate_file(filename, file_bytes)

        doc_id = uuid4()
        s3_key = s3_service.build_s3_key(user.id, doc_id, safe_filename)

        # 1. Upload raw file to private AWS S3 bucket first
        s3_service.upload_file(
            file_bytes=file_bytes,
            s3_key=s3_key,
            content_type=resolved_mime,
        )

        # 2. Persist initial PROCESSING record in PostgreSQL
        document = Document(
            id=doc_id,
            user_id=user.id,
            title=clean_title,
            instruction=clean_instruction,
            status=DocumentStatus.PROCESSING,
            file_name=safe_filename,
            file_extension=ext,
            content_type=resolved_mime,
            file_size=len(file_bytes),
            s3_key=s3_key,
        )
        try:
            db.add(document)
            db.commit()
            db.refresh(document)
        except Exception:
            db.rollback()
            try:
                s3_service.delete_files([s3_key])
            except Exception:
                logger.exception(
                    "Failed to clean up orphaned S3 object after DB commit failure: %s",
                    s3_key,
                )
            raise

        # 3. Extract text/image and run GPT-4o-mini analysis
        self._run_ai_pipeline(db=db, document=document, file_bytes=file_bytes)
        return self._to_response(document, include_presigned_url=True)

    def list_user_documents(self, db: Session, user: User) -> DocumentListResponse:
        stmt = (
            select(Document)
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc())
        )
        docs = list(db.execute(stmt).scalars().all())
        items = [self._to_response(doc, include_presigned_url=True) for doc in docs]
        return DocumentListResponse(total=len(items), items=items)

    def get_user_document(
        self, db: Session, user: User, document_id: UUID
    ) -> DocumentResponse:
        doc = self._get_owned_document(db, user, document_id)
        return self._to_response(doc, include_presigned_url=True)

    def retry_document_analysis(
        self, db: Session, user: User, document_id: UUID
    ) -> DocumentResponse:
        """
        Re-run OpenAI analysis for an existing document by downloading its
        original file from S3—without requiring the user to re-upload.
        """
        doc = self._get_owned_document(db, user, document_id)
        file_bytes = s3_service.download_file(doc.s3_key)

        doc.status = DocumentStatus.PROCESSING
        doc.error_message = None
        db.commit()
        db.refresh(doc)

        self._run_ai_pipeline(db=db, document=doc, file_bytes=file_bytes)
        return self._to_response(doc, include_presigned_url=True)

    def delete_user_documents(
        self, db: Session, user: User, document_ids: list[UUID]
    ) -> BulkDeleteResponse:
        """
        Delete one or multiple documents owned by the current user from both
        AWS S3 and PostgreSQL.
        """
        unique_ids = list(dict.fromkeys(document_ids))
        if not unique_ids:
            raise ValidationException("Nenhum documento selecionado para exclusão.")

        stmt = select(Document).where(Document.id.in_(unique_ids))
        found_docs = list(db.execute(stmt).scalars().all())

        if len(found_docs) != len(unique_ids):
            raise NotFoundException(
                "Um ou mais documentos selecionados não foram encontrados."
            )

        for doc in found_docs:
            if doc.user_id != user.id:
                raise ForbiddenException(
                    "Você não tem permissão para excluir documentos de outro usuário."
                )

        s3_keys = [doc.s3_key for doc in found_docs]
        s3_service.delete_files(s3_keys)

        deleted_ids: list[UUID] = []
        for doc in found_docs:
            deleted_ids.append(doc.id)
            db.delete(doc)

        db.commit()
        return BulkDeleteResponse(
            deleted_count=len(deleted_ids),
            deleted_ids=deleted_ids,
        )

    def _get_owned_document(
        self, db: Session, user: User, document_id: UUID
    ) -> Document:
        doc = db.get(Document, document_id)
        if doc is None:
            raise NotFoundException("Documento não encontrado.")
        if doc.user_id != user.id:
            raise ForbiddenException(
                "Você não tem permissão para acessar este documento."
            )
        return doc

    def _run_ai_pipeline(
        self, db: Session, document: Document, file_bytes: bytes
    ) -> None:
        try:
            extracted = extract_content(
                file_bytes=file_bytes,
                extension=document.file_extension,
                mime_type=document.content_type,
            )
            ai_text = ai_service.analyze_document(
                title=document.title,
                instruction=document.instruction,
                content=extracted,
            )
            document.ai_response = ai_text
            document.status = DocumentStatus.COMPLETED
            document.error_message = None
        except (ValueError, AIAnalysisError) as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
        except Exception:
            logger.exception(
                "Unexpected error during AI analysis for document %s", document.id
            )
            document.status = DocumentStatus.FAILED
            document.error_message = (
                "Erro inesperado durante a análise com IA. Tente novamente em instantes."
            )

        db.commit()
        db.refresh(document)

    def _to_response(
        self, document: Document, include_presigned_url: bool = True
    ) -> DocumentResponse:
        presigned_url: str | None = None
        if include_presigned_url:
            try:
                presigned_url = s3_service.generate_presigned_url(
                    s3_key=document.s3_key,
                    filename=document.file_name,
                )
            except Exception:
                presigned_url = None

        response = DocumentResponse.model_validate(document)
        response.presigned_url = presigned_url
        return response


document_service = DocumentService()
