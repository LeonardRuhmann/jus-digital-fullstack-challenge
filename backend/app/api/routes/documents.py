from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_analyze_document(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File(description="Documento ou imagem para análise")],
    title: Annotated[str, Form(description="Título do documento")],
    instruction: Annotated[str, Form(description="Instrução para a análise da IA")],
) -> DocumentResponse:
    """
    Upload a document, store the raw file in AWS S3, run GPT-4o-mini analysis,
    and persist metadata + AI response in PostgreSQL.
    """
    file_bytes = await file.read()
    return document_service.create_and_analyze_document(
        db=db,
        user=current_user,
        filename=file.filename,
        file_bytes=file_bytes,
        title=title,
        instruction=instruction,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentListResponse:
    """List all documents belonging to the authenticated user."""
    return document_service.list_user_documents(db=db, user=current_user)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    """Fetch a single document with its AI analysis and a fresh S3 Presigned GET URL."""
    return document_service.get_user_document(
        db=db,
        user=current_user,
        document_id=document_id,
    )


@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry_document_ai_analysis(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    """
    Retry the GPT-4o-mini analysis for a document that previously failed,
    reusing the file already saved in AWS S3.
    """
    return document_service.retry_document_analysis(
        db=db,
        user=current_user,
        document_id=document_id,
    )


@router.delete("/{document_id}", response_model=BulkDeleteResponse)
def delete_single_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkDeleteResponse:
    """Delete a single document from AWS S3 and PostgreSQL."""
    return document_service.delete_user_documents(
        db=db,
        user=current_user,
        document_ids=[document_id],
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_documents(
    payload: BulkDeleteRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkDeleteResponse:
    """Delete multiple selected documents from AWS S3 and PostgreSQL."""
    return document_service.delete_user_documents(
        db=db,
        user=current_user,
        document_ids=payload.document_ids,
    )
