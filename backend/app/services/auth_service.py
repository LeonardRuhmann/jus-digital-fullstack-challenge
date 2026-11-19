import logging
from urllib.parse import urlencode
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ExternalServiceException, UnauthorizedException, ValidationException
from app.models.user import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthService:
    """Handles Google OAuth 2.0 authentication and User persistence."""

    def get_google_login_url(self, state: str, redirect_uri: str | None = None) -> str:
        """Build the Google OAuth 2.0 consent screen URL."""
        if not settings.GOOGLE_CLIENT_ID:
            raise ValidationException(
                "GOOGLE_CLIENT_ID não está configurado no servidor (.env)."
            )
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    async def authenticate_with_code(
        self,
        db: Session,
        code: str,
        redirect_uri: str | None = None,
    ) -> User:
        """
        Exchange an OAuth 2.0 authorization code for tokens on the back-end,
        fetch the verified Google profile, and upsert the user in PostgreSQL.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValidationException(
                "Credenciais do Google OAuth (CLIENT_ID / CLIENT_SECRET) ausentes no .env."
            )

        token_payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=token_payload)
            if token_resp.status_code != 200:
                raise UnauthorizedException(
                    "Não foi possível validar o código de autorização com o Google."
                )
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise UnauthorizedException("Token de acesso do Google ausente.")

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise ExternalServiceException(
                    "Falha ao obter dados de perfil da conta Google.",
                    error_code="GOOGLE_USERINFO_ERROR",
                )
            profile = userinfo_resp.json()

        return self._upsert_google_user(
            db=db,
            google_id=str(profile.get("sub") or ""),
            email=str(profile.get("email") or ""),
            name=str(profile.get("name") or profile.get("email") or "Usuário"),
            avatar_url=profile.get("picture"),
        )

    def authenticate_with_id_token(self, db: Session, credential: str) -> User:
        """Verify a Google ID token (credential) directly and upsert the user."""
        if not settings.GOOGLE_CLIENT_ID:
            raise ValidationException("GOOGLE_CLIENT_ID não configurado no servidor.")
        try:
            id_info = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as exc:
            logger.warning("Invalid Google ID token: %s", exc)
            raise UnauthorizedException(
                "Token do Google inválido ou expirado. Faça login novamente."
            ) from exc

        return self._upsert_google_user(
            db=db,
            google_id=str(id_info.get("sub") or ""),
            email=str(id_info.get("email") or ""),
            name=str(id_info.get("name") or id_info.get("email") or "Usuário"),
            avatar_url=id_info.get("picture"),
        )

    def _upsert_google_user(
        self,
        db: Session,
        google_id: str,
        email: str,
        name: str,
        avatar_url: str | None,
    ) -> User:
        if not google_id or not email:
            raise UnauthorizedException(
                "A conta Google não retornou identificador ou e-mail válido."
            )

        stmt = select(User).where(
            (User.google_id == google_id) | (User.email == email)
        )
        user = db.execute(stmt).scalar_one_or_none()

        if user is None:
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
            )
            db.add(user)
        else:
            user.google_id = google_id
            user.email = email
            user.name = name
            user.avatar_url = avatar_url

        db.commit()
        db.refresh(user)
        return user


auth_service = AuthService()
