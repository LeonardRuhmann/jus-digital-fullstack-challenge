from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Document, DocumentStatus, User  # Imports both User & Document
from app.services import document_service as doc_service_module

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try: 
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def test_user(db_session):
    user = User(google_id="google-test-123", email="mariana@gmail.com", name="Dra. Mariana Gomes")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user) # Populates the auto-generated user.id UUID
    return user

@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


@pytest.fixture()
def other_user(db_session):
    user = User(
        google_id="google-other-456",
        email="carlos@outroescritorio.com",
        name="Dr. Carlos Silva",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def fake_s3(monkeypatch):
    """In-memory fake S3 bucket so tests never call real AWS."""
    bucket: dict[str, bytes] = {}

    def fake_upload(file_bytes: bytes, s3_key: str, content_type: str) -> None:
        bucket[s3_key] = file_bytes

    def fake_download(s3_key: str) -> bytes:
        return bucket[s3_key]

    def fake_presign(
        s3_key: str, filename: str | None = None, expiration: int | None = None
    ) -> str:
        return f"https://fake-s3.local/{s3_key}?expires=900"

    def fake_delete(s3_keys: list[str]) -> None:
        for key in s3_keys:
            bucket.pop(key, None)

    monkeypatch.setattr(doc_service_module.s3_service, "upload_file", fake_upload)
    monkeypatch.setattr(doc_service_module.s3_service, "download_file", fake_download)
    monkeypatch.setattr(
        doc_service_module.s3_service, "generate_presigned_url", fake_presign
    )
    monkeypatch.setattr(doc_service_module.s3_service, "delete_files", fake_delete)
    return bucket


@pytest.fixture()
def sample_document(db_session, test_user, fake_s3):
    """Creates a document owned by test_user (Dra. Mariana) in SQLite and fake S3."""
    doc_id = uuid4()
    s3_key = f"users/{test_user.id}/documents/{doc_id}/contrato.txt"
    fake_s3[s3_key] = b"Conteudo sigiloso do contrato da Mariana."

    doc = Document(
        id=doc_id,
        user_id=test_user.id,
        title="Contrato Sigiloso",
        instruction="Resuma as clausulas principais",
        ai_response="Resumo gerado pela IA.",
        status=DocumentStatus.COMPLETED,
        file_name="contrato.txt",
        file_extension=".txt",
        content_type="text/plain",
        file_size=len(fake_s3[s3_key]),
        s3_key=s3_key,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc
