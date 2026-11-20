from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Response
import jwt
import pytest

from app.api.routes.auth import OAUTH_STATE_COOKIE
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    decode_access_token,
    set_auth_cookie,
)
from app.services import auth_service as auth_service_module
from app.services.auth_service import auth_service


def test_create_and_decode_valid_jwt():
    user_id = uuid4()
    token = create_access_token(user_id)
    decoded_user_id = decode_access_token(token)

    assert decoded_user_id == user_id


def test_decode_malformed_jwt_raises_unauthorized():
    with pytest.raises(UnauthorizedException, match="inválido"):
        decode_access_token("not.a.valid.jwt")


def test_decode_wrong_secret_jwt_raises_unauthorized():
    forged_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        "wrong-secret-key",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedException, match="inválido"):
        decode_access_token(forged_token)


def test_decode_expired_jwt_raises_unauthorized():
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedException, match="expirou"):
        decode_access_token(expired_token)


def test_decode_missing_subject_raises_unauthorized():
    token_without_sub = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedException, match="identificador ausente"):
        decode_access_token(token_without_sub)


def test_decode_non_uuid_subject_raises_unauthorized():
    token_with_bad_sub = jwt.encode(
        {
            "sub": "not-a-uuid",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedException, match="inválido"):
        decode_access_token(token_with_bad_sub)


def test_auth_cookie_is_httponly_and_clears_on_logout():
    login_response = Response()
    set_auth_cookie(login_response, "fake-jwt-token")
    set_cookie_header = login_response.headers["set-cookie"].lower()

    assert settings.COOKIE_NAME in set_cookie_header
    assert "httponly" in set_cookie_header

    logout_response = Response()
    clear_auth_cookie(logout_response)
    clear_cookie_header = logout_response.headers["set-cookie"].lower()

    assert settings.COOKIE_NAME in clear_cookie_header
    assert "max-age=0" in clear_cookie_header


def test_auth_me_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_auth_me_accepts_valid_session_cookie(client, test_user):
    token = create_access_token(test_user.id)
    client.cookies.set(settings.COOKIE_NAME, token)
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(test_user.id)
    assert body["email"] == test_user.email
    assert body["name"] == test_user.name


def test_auth_me_accepts_valid_bearer_header(client, test_user):
    token = create_access_token(test_user.id)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)


def test_auth_me_rejects_token_for_nonexistent_user(client):
    ghost_token = create_access_token(uuid4())
    client.cookies.set(settings.COOKIE_NAME, ghost_token)
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_oauth_callback_rejects_missing_csrf_state_cookie(client):
    # Sends callback with a state query param, but WITHOUT the HttpOnly state cookie.
    # Must reject immediately for invalid CSRF state instead of talking to Google.
    response = client.get(
        "/api/auth/google/callback?code=fake-code&state=attacker-state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "Estado" in response.headers["location"]


def test_oauth_callback_rejects_mismatched_csrf_state_cookie(client):
    # Cookie exists, but its value does not match the query param state.
    client.cookies.set(OAUTH_STATE_COOKIE, "expected-state-123")
    response = client.get(
        "/api/auth/google/callback?code=fake-code&state=different-state-999",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "Estado" in response.headers["location"]


def test_google_id_token_error_returns_sanitized_message(db_session, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "fake-google-client-id")

    def fail_verify(*args, **kwargs):
        raise ValueError("Internal google-auth detail 0xDEADBEEF")

    monkeypatch.setattr(
        auth_service_module.google_id_token, "verify_oauth2_token", fail_verify
    )

    with pytest.raises(UnauthorizedException, match="Token do Google inválido ou expirado") as exc_info:
        auth_service.authenticate_with_id_token(db_session, "invalid-credential")

    assert "0xDEADBEEF" not in exc_info.value.message
    assert "google-auth" not in exc_info.value.message
