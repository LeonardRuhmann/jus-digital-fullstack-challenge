from typing import Annotated
from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.models.user import User


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    session_cookie: Annotated[str | None, Cookie(alias=settings.COOKIE_NAME)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Resolve the authenticated user from either the HttpOnly session cookie
    or an Authorization: Bearer <token> header.
    """
    token: str | None = session_cookie
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise UnauthorizedException("Você precisa estar autenticado para continuar.")

    user_id = decode_access_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedException("Usuário da sessão não encontrado.")
    return user
