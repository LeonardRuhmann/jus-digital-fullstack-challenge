import base64
import io
from types import SimpleNamespace
from uuid import uuid4

from botocore.exceptions import EndpointConnectionError
import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pypdf import PdfWriter
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.security import create_access_token
from app.models import Document, DocumentStatus, User
from app.services import document_service as doc_service_module
from app.services.ai_service import AIAnalysisError, AIService, SYSTEM_PROMPT
from app.services.auth_service import auth_service
from app.services.s3_service import S3Service
from app.services.text_extractor import ExtractedContent


def _login_as(client, user) -> None:
    """Set the HttpOnly session cookie on TestClient for the given user."""
    client.cookies.set(settings.COOKIE_NAME, create_access_token(user.id))


def _make_fake_openai_client(content: str | None = "Analise juridica concluida.", error: Exception | None = None):
    """Build a minimal stub matching openai.OpenAI().chat.completions.create."""
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        if error is not None:
            raise error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    return fake_client, captured


def _make_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# AIService unit tests (prompt structure, configurable model, error mapping)
# ---------------------------------------------------------------------------


def test_ai_service_sends_prompt_instruction_and_configurable_model(monkeypatch):
    service = AIService()
    fake_client, captured = _make_fake_openai_client("Resumo da clausula de multa.")
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o-custom-test")

    extracted = ExtractedContent(
        kind="text",
        text="Clausula 5a: multa rescisoria de 20%.",
        mime_type="text/plain",
    )
    answer = service.analyze_document(
        title="Contrato Locacao",
        instruction="Extraia a multa rescisoria",
        content=extracted,
    )

    assert answer == "Resumo da clausula de multa."
    assert captured["model"] == "gpt-4o-custom-test"
    assert captured["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    user_msg = captured["messages"][1]["content"]
    assert "Contrato Locacao" in user_msg
    assert "Extraia a multa rescisoria" in user_msg
    assert "Clausula 5a: multa rescisoria de 20%." in user_msg


def test_ai_service_sends_base64_image_payload_for_vision(monkeypatch):
    service = AIService()
    fake_client, captured = _make_fake_openai_client("Imagem analisada.")
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)

    raw_png = b"\x89PNG\r\n\x1a\nfake-bytes"
    extracted = ExtractedContent(
        kind="image",
        image_bytes=raw_png,
        mime_type="image/png",
    )
    answer = service.analyze_document(
        title="Comprovante PIX",
        instruction="Qual o valor pago?",
        content=extracted,
    )

    assert answer == "Imagem analisada."
    user_parts = captured["messages"][1]["content"]
    assert isinstance(user_parts, list)
    assert user_parts[0]["type"] == "text"
    assert "Comprovante PIX" in user_parts[0]["text"]
    assert "Qual o valor pago?" in user_parts[0]["text"]

    expected_b64 = base64.b64encode(raw_png).decode("ascii")
    assert user_parts[1]["type"] == "image_url"
    assert user_parts[1]["image_url"]["url"] == f"data:image/png;base64,{expected_b64}"


def test_ai_service_rejects_empty_response(monkeypatch):
    service = AIService()
    fake_client, _ = _make_fake_openai_client("   ")
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)

    extracted = ExtractedContent(kind="text", text="Texto valido.", mime_type="text/plain")
    with pytest.raises(AIAnalysisError, match="resposta vazia"):
        service.analyze_document("Doc", "Resuma", extracted)


def _openai_error_cases():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return [
        (APITimeoutError(request=req), "Tempo limite excedido"),
        (
            RateLimitError("rate limit", response=httpx.Response(429, request=req), body=None),
            "Limite de uso",
        ),
        (
            AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None),
            "Falha de autenticação",
        ),
        (APIConnectionError(request=req), "Erro de conexão"),
    ]


@pytest.mark.parametrize(("sdk_error", "expected_msg"), _openai_error_cases())
def test_ai_service_translates_openai_sdk_errors(monkeypatch, sdk_error, expected_msg):
    service = AIService()
    fake_client, _ = _make_fake_openai_client(error=sdk_error)
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)

    extracted = ExtractedContent(kind="text", text="Texto valido.", mime_type="text/plain")
    with pytest.raises(AIAnalysisError, match=expected_msg):
        service.analyze_document("Doc", "Resuma", extracted)


# ---------------------------------------------------------------------------
# Full HTTP Document lifecycle (Upload, AI Failure + Retry, S3 consistency)
# ---------------------------------------------------------------------------


def test_upload_and_analyze_document_happy_path(
    client, db_session, test_user, fake_s3, monkeypatch
):
    monkeypatch.setattr(
        doc_service_module.ai_service,
        "analyze_document",
        lambda **kwargs: "Resumo: contrato valido por 12 meses.",
    )
    _login_as(client, test_user)

    response = client.post(
        "/api/documents",
        data={"title": "Contrato 2026", "instruction": "Resuma o prazo"},
        files={"file": ("contrato.txt", b"Prazo de vigencia: 12 meses.", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Contrato 2026"
    assert body["status"] == DocumentStatus.COMPLETED.value
    assert body["ai_response"] == "Resumo: contrato valido por 12 meses."
    assert body["error_message"] is None
    assert body["presigned_url"].startswith("https://fake-s3.local/")
    assert "s3_key" not in body

    # Raw bytes saved in S3 and metadata persisted in DB
    assert len(fake_s3) == 1
    assert b"Prazo de vigencia: 12 meses." in fake_s3.values()
    stored_docs = db_session.execute(select(Document)).scalars().all()
    assert len(stored_docs) == 1


def test_upload_preserves_file_on_ai_failure_and_retry_recovers_from_s3(
    client, db_session, test_user, fake_s3, monkeypatch
):
    def fail_ai(**kwargs):
        raise AIAnalysisError("Tempo limite excedido ao aguardar resposta da OpenAI.")

    monkeypatch.setattr(doc_service_module.ai_service, "analyze_document", fail_ai)
    _login_as(client, test_user)

    # 1. Upload succeeds in S3 + DB, but AI analysis transitions status to FAILED
    upload_resp = client.post(
        "/api/documents",
        data={"title": "Peticao Urgente", "instruction": "Liste os pedidos"},
        files={"file": ("peticao.txt", b"Pedido 1: tutela de urgencia.", "text/plain")},
    )

    assert upload_resp.status_code == 201
    failed_doc = upload_resp.json()
    assert failed_doc["status"] == DocumentStatus.FAILED.value
    assert failed_doc["ai_response"] is None
    assert "Tempo limite excedido" in failed_doc["error_message"]
    assert len(fake_s3) == 1

    # 2. Retry downloads original bytes from S3 (no re-upload) and recovers to COMPLETED
    captured_retry: dict = {}

    def succeed_ai(**kwargs):
        captured_retry.update(kwargs)
        return "Pedido principal: concessao de tutela de urgencia."

    monkeypatch.setattr(doc_service_module.ai_service, "analyze_document", succeed_ai)

    retry_resp = client.post(f"/api/documents/{failed_doc['id']}/retry")
    assert retry_resp.status_code == 200
    recovered = retry_resp.json()
    assert recovered["status"] == DocumentStatus.COMPLETED.value
    assert recovered["ai_response"] == "Pedido principal: concessao de tutela de urgencia."
    assert recovered["error_message"] is None
    assert "tutela de urgencia" in (captured_retry["content"].text or "")


def test_upload_blank_pdf_marks_document_failed_without_crashing(
    client, test_user, fake_s3
):
    _login_as(client, test_user)
    blank_pdf = _make_blank_pdf_bytes()

    response = client.post(
        "/api/documents",
        data={"title": "PDF Escaneado", "instruction": "Extraia os nomes"},
        files={"file": ("escaneado.pdf", blank_pdf, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == DocumentStatus.FAILED.value
    assert "Não foi possível extrair texto legível" in body["error_message"]
    assert len(fake_s3) == 1


def test_upload_s3_failure_writes_nothing_to_database(
    client, db_session, test_user, monkeypatch
):
    def fail_s3_upload(**kwargs):
        raise ExternalServiceException(
            "Erro ao enviar arquivo para o armazenamento AWS S3",
            error_code="S3_UPLOAD_ERROR",
        )

    monkeypatch.setattr(doc_service_module.s3_service, "upload_file", fail_s3_upload)
    _login_as(client, test_user)

    response = client.post(
        "/api/documents",
        data={"title": "Contrato", "instruction": "Resuma"},
        files={"file": ("contrato.txt", b"Texto valido.", "text/plain")},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "S3_UPLOAD_ERROR"
    assert db_session.execute(select(Document)).scalars().all() == []


def test_upload_db_failure_cleans_up_s3_object(
    db_session, test_user, fake_s3, monkeypatch
):
    uploaded_keys: list[str] = []
    original_upload = doc_service_module.s3_service.upload_file

    def tracking_upload(file_bytes: bytes, s3_key: str, content_type: str) -> None:
        uploaded_keys.append(s3_key)
        original_upload(file_bytes=file_bytes, s3_key=s3_key, content_type=content_type)

    def fail_commit():
        raise RuntimeError("Simulated database commit failure")

    monkeypatch.setattr(doc_service_module.s3_service, "upload_file", tracking_upload)
    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="Simulated database commit failure"):
        doc_service_module.document_service.create_and_analyze_document(
            db=db_session,
            user=test_user,
            filename="contrato.txt",
            file_bytes=b"Texto valido.",
            title="Contrato",
            instruction="Resuma",
        )

    assert len(uploaded_keys) == 1
    assert uploaded_keys[0] not in fake_s3
    assert len(fake_s3) == 0
    assert db_session.execute(select(Document)).scalars().all() == []


@pytest.mark.parametrize(
    ("title", "instruction", "expected_msg"),
    [
        ("   ", "Resuma o texto", "Título"),
        ("Contrato valido", "   ", "Instrução para IA"),
    ],
)
def test_upload_rejects_whitespace_title_or_instruction(
    client, db_session, test_user, fake_s3, title, instruction, expected_msg
):
    _login_as(client, test_user)
    response = client.post(
        "/api/documents",
        data={"title": title, "instruction": instruction},
        files={"file": ("contrato.txt", b"Texto valido.", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"
    assert expected_msg in response.json()["message"]
    assert len(fake_s3) == 0
    assert db_session.execute(select(Document)).scalars().all() == []


# ---------------------------------------------------------------------------
# S3 key hygiene, deletion edge cases, AuthService upsert & DB cascade
# ---------------------------------------------------------------------------


def test_s3_key_sanitizes_path_traversal_and_special_characters():
    user_id = uuid4()
    doc_id = uuid4()
    key = S3Service.build_s3_key(user_id, doc_id, "../../contrato final (v1).pdf")

    prefix = f"users/{user_id}/documents/{doc_id}/"
    assert key.startswith(prefix)
    filename_part = key[len(prefix) :]
    assert "/" not in filename_part
    assert " " not in filename_part
    assert "(" not in filename_part
    assert filename_part.endswith(".pdf")


def test_s3_service_error_does_not_leak_bucket_or_key(monkeypatch):
    service = S3Service()
    secret_bucket = "bucket-interno-secreto-2026"
    secret_key = "users/123/documents/456/contrato.pdf"

    def fail_put_object(**kwargs):
        raise EndpointConnectionError(
            endpoint_url=f"https://{secret_bucket}.s3.sa-east-1.amazonaws.com/{secret_key}"
        )

    monkeypatch.setattr(service, "_get_client", lambda: SimpleNamespace(put_object=fail_put_object))

    with pytest.raises(ExternalServiceException) as exc_info:
        service.upload_file(b"dados", secret_key, "application/pdf")

    assert exc_info.value.error_code == "S3_UPLOAD_ERROR"
    assert secret_bucket not in exc_info.value.message
    assert secret_key not in exc_info.value.message
    assert "amazonaws.com" not in exc_info.value.message


def test_delete_single_document_removes_from_db_and_s3(
    client, db_session, test_user, sample_document, fake_s3
):
    _login_as(client, test_user)
    response = client.delete(f"/api/documents/{sample_document.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_count"] == 1
    assert body["deleted_ids"] == [str(sample_document.id)]
    assert db_session.get(Document, sample_document.id) is None
    assert sample_document.s3_key not in fake_s3


def test_bulk_delete_empty_list_returns_422(client, test_user):
    _login_as(client, test_user)
    response = client.post("/api/documents/bulk-delete", json={"document_ids": []})

    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_bulk_delete_missing_id_is_atomic_and_returns_404(
    client, db_session, test_user, sample_document, fake_s3
):
    _login_as(client, test_user)
    response = client.post(
        "/api/documents/bulk-delete",
        json={"document_ids": [str(sample_document.id), str(uuid4())]},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"
    # Existing document must not be partially deleted
    assert db_session.get(Document, sample_document.id) is not None
    assert sample_document.s3_key in fake_s3


def test_bulk_delete_deduplicates_repeated_ids(
    client, db_session, test_user, sample_document, fake_s3
):
    _login_as(client, test_user)
    doc_id = str(sample_document.id)
    response = client.post(
        "/api/documents/bulk-delete",
        json={"document_ids": [doc_id, doc_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_count"] == 1
    assert body["deleted_ids"] == [doc_id]
    assert db_session.get(Document, sample_document.id) is None
    assert sample_document.s3_key not in fake_s3


def test_auth_service_upsert_updates_existing_user_without_duplicating(db_session):
    first = auth_service._upsert_google_user(
        db=db_session,
        google_id="google-upsert-999",
        email="advogada@jusdigital.com.br",
        name="Nome Antigo",
        avatar_url="https://example.com/old.png",
    )
    second = auth_service._upsert_google_user(
        db=db_session,
        google_id="google-upsert-999",
        email="advogada@jusdigital.com.br",
        name="Nome Atualizado",
        avatar_url="https://example.com/new.png",
    )

    assert second.id == first.id
    assert second.name == "Nome Atualizado"
    assert second.avatar_url == "https://example.com/new.png"
    all_users = db_session.execute(select(User)).scalars().all()
    assert len(all_users) == 1


def test_deleting_user_cascades_to_documents(db_session, test_user, sample_document):
    doc_id = sample_document.id
    db_session.delete(test_user)
    db_session.commit()

    assert db_session.get(Document, doc_id) is None
