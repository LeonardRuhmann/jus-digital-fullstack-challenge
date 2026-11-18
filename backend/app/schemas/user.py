from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Serialized user profile returned to the Front-end (populates Sidebar)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    google_id: str
    email: EmailStr
    name: str
    avatar_url: str | None = None
    created_at: datetime


class GoogleTokenLoginRequest(BaseModel):
    """Payload when exchanging a Google OAuth authorization code or ID token."""

    code: str | None = None
    credential: str | None = None
    redirect_uri: str | None = None
