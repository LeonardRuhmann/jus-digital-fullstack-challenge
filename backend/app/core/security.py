from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from fastapi import Response

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


def create_access_token(user_id: UUID) -> str:
    """Create a signed JWT token containing the authenticated user's ID."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> UUID:
    """Verify and decode a JWT token, returning the user's UUID."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        subject = payload.get("sub")
        if not subject:
            raise UnauthorizedException("Token inválido: identificador ausente.")
        return UUID(subject)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedException("Sua sessão expirou. Faça login novamente.") from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise UnauthorizedException("Token de autenticação inválido.") from exc


def set_auth_cookie(response: Response, token: str) -> None:
    """Attach the JWT session token inside an HttpOnly cookie to prevent XSS access."""
    is_prod = settings.APP_ENV.lower() == "production"
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Remove the HttpOnly session cookie on logout."""
    is_prod = settings.APP_ENV.lower() == "production"
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        path="/",
    )
