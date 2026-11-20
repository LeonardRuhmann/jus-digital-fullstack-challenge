from uuid import uuid4

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Document, DocumentStatus


def _login_as(client, user) -> None:
    """Set the HttpOnly session cookie on TestClient for the given user."""
    client.cookies.set(settings.COOKIE_NAME, create_access_token(user.id))


def test_list_documents_returns_only_own_documents(
    client, test_user, other_user, sample_document
):
    # Mariana sees her own document
    _login_as(client, test_user)
    mariana_resp = client.get("/api/documents")
    assert mariana_resp.status_code == 200
    assert mariana_resp.json()["total"] == 1
    assert mariana_resp.json()["items"][0]["id"] == str(sample_document.id)

    # Carlos sees 0 documents (Mariana's document never leaks)
    _login_as(client, other_user)
    carlos_resp = client.get("/api/documents")
    assert carlos_resp.status_code == 200
    assert carlos_resp.json()["total"] == 0
    assert carlos_resp.json()["items"] == []


def test_owner_can_read_own_document_without_exposing_s3_key(
    client, test_user, sample_document
):
    _login_as(client, test_user)
    response = client.get(f"/api/documents/{sample_document.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(sample_document.id)
    assert body["presigned_url"].startswith("https://fake-s3.local/")
    assert "s3_key" not in body


def test_other_user_cannot_read_document(client, other_user, sample_document):
    _login_as(client, other_user)
    response = client.get(f"/api/documents/{sample_document.id}")

    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"


def test_other_user_cannot_retry_document(client, other_user, sample_document):
    _login_as(client, other_user)
    response = client.post(f"/api/documents/{sample_document.id}/retry")

    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"


def test_other_user_cannot_delete_single_document(
    client, db_session, other_user, sample_document, fake_s3
):
    _login_as(client, other_user)
    response = client.delete(f"/api/documents/{sample_document.id}")

    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"
    # Document must still exist in both DB and S3
    assert db_session.get(Document, sample_document.id) is not None
    assert sample_document.s3_key in fake_s3


def test_bulk_delete_mixed_ownership_is_atomic(
    client, db_session, other_user, sample_document, fake_s3
):
    # Create a document owned by Carlos
    carlos_doc_id = uuid4()
    carlos_s3_key = f"users/{other_user.id}/documents/{carlos_doc_id}/carlos.txt"
    fake_s3[carlos_s3_key] = b"Documento do Carlos."

    carlos_doc = Document(
        id=carlos_doc_id,
        user_id=other_user.id,
        title="Doc do Carlos",
        instruction="Resuma",
        ai_response="Ok",
        status=DocumentStatus.COMPLETED,
        file_name="carlos.txt",
        file_extension=".txt",
        content_type="text/plain",
        file_size=len(fake_s3[carlos_s3_key]),
        s3_key=carlos_s3_key,
    )
    db_session.add(carlos_doc)
    db_session.commit()

    # Carlos tries bulk-deleting HIS own doc + MARIANA's doc together
    _login_as(client, other_user)
    response = client.post(
        "/api/documents/bulk-delete",
        json={"document_ids": [str(carlos_doc.id), str(sample_document.id)]},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"
    # Neither document may be deleted (all-or-nothing)
    assert db_session.get(Document, carlos_doc.id) is not None
    assert db_session.get(Document, sample_document.id) is not None
    assert carlos_s3_key in fake_s3
    assert sample_document.s3_key in fake_s3


def test_get_nonexistent_document_returns_404(client, test_user):
    _login_as(client, test_user)
    response = client.get(f"/api/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_get_invalid_uuid_returns_422(client, test_user):
    _login_as(client, test_user)
    response = client.get("/api/documents/not-a-valid-uuid")

    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"
