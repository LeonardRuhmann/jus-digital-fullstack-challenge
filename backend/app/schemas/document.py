from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """
    Serialized document returned to the Front-end.
    Includes a short-lived presigned_url when requested so the private S3 bucket
    is never exposed publicly.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    instruction: str
    ai_response: str | None = None
    status: DocumentStatus
    error_message: str | None = None
    file_name: str
    file_extension: str
    content_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime
    presigned_url: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated/counted list of documents matching the Figma '4 Documentos' header."""

    total: int
    items: list[DocumentResponse]


class BulkDeleteRequest(BaseModel):
    """Supports the 'Exclusão segura (seleção de vários documentos)' differential."""

    document_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of document UUIDs to delete from PostgreSQL and AWS S3.",
    )


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    deleted_ids: list[UUID]
