import secrets
from typing import Annotated
from urllib.parse import urlencode
from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException, ValidationException
from app.core.security import clear_auth_cookie, create_access_token, set_auth_cookie
from app.models.user import User
from app.schemas.user import GoogleTokenLoginRequest, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

OAUTH_STATE_COOKIE = "jusdigital_oauth_state"


@router.get("/google/login")
def google_login() -> RedirectResponse:
    """
    Initiate the Google OAuth 2.0 flow on the server.
    Stores a random CSRF state token in an HttpOnly cookie and redirects to Google.
    """
    state = secrets.token_urlsafe(32)
    auth_url = auth_service.get_google_login_url(state=state)
    response = RedirectResponse(url=auth_url, status_code=302)
    is_prod = settings.APP_ENV.lower() == "production"
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    saved_state: Annotated[str | None, Cookie(alias=OAUTH_STATE_COOKIE)] = None,
) -> RedirectResponse:
    """
    Handle Google's OAuth 2.0 redirect, verify CSRF state, exchange the code
    using the back-end secret, issue our HttpOnly JWT cookie, and redirect to the UI.
    """
    frontend_base = settings.FRONTEND_URL.rstrip("/")

    if error:
        query = urlencode({"error": "Login com Google cancelado ou negado."})
        return RedirectResponse(url=f"{frontend_base}/login?{query}", status_code=302)

    if not code:
        query = urlencode({"error": "Código de autorização do Google ausente."})
        return RedirectResponse(url=f"{frontend_base}/login?{query}", status_code=302)

    if saved_state and state and saved_state != state:
        query = urlencode({"error": "Estado de segurança OAuth inválido. Tente novamente."})
        return RedirectResponse(url=f"{frontend_base}/login?{query}", status_code=302)

    try:
        user = await auth_service.authenticate_with_code(db=db, code=code)
    except AppException as exc:
        query = urlencode({"error": exc.message})
        return RedirectResponse(url=f"{frontend_base}/login?{query}", status_code=302)

    jwt_token = create_access_token(user.id)
    redirect = RedirectResponse(url=f"{frontend_base}/documentos", status_code=302)
    set_auth_cookie(redirect, jwt_token)
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")
    return redirect


@router.post("/google/token", response_model=UserResponse)
async def google_token_exchange(
    payload: GoogleTokenLoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """
    Alternative JSON endpoint to exchange a Google OAuth code or ID token credential
    and set the HttpOnly session cookie.
    """
    if payload.code:
        user = await auth_service.authenticate_with_code(
            db=db,
            code=payload.code,
            redirect_uri=payload.redirect_uri,
        )
    elif payload.credential:
        user = auth_service.authenticate_with_id_token(
            db=db,
            credential=payload.credential,
        )
    else:
        raise ValidationException("Forneça 'code' ou 'credential' para autenticar.")

    jwt_token = create_access_token(user.id)
    set_auth_cookie(response, jwt_token)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the authenticated user's profile (Sidebar photo, name, and email)."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=204)
def logout() -> Response:
    """Clear the HttpOnly authentication cookie."""
    response = Response(status_code=204)
    clear_auth_cookie(response)
    return response
