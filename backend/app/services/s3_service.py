import re
from uuid import UUID
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import ExternalServiceException


class S3Service:
    """
    Encapsulates all AWS S3 object operations on a strictly PRIVATE bucket.
    Never exposes raw bucket URLs—access is granted via short-lived Presigned GET URLs.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if not settings.AWS_S3_BUCKET_NAME:
            raise ExternalServiceException(
                "AWS S3 não configurado (AWS_S3_BUCKET_NAME ausente).",
                error_code="S3_CONFIG_ERROR",
            )
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
                config=BotoConfig(signature_version="s3v4"),
            )
        return self._client

    @staticmethod
    def build_s3_key(user_id: UUID, document_id: UUID, filename: str) -> str:
        """Build a tenant-isolated object key inside the S3 bucket."""
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        return f"users/{user_id}/documents/{document_id}/{sanitized}"

    def upload_file(self, file_bytes: bytes, s3_key: str, content_type: str) -> None:
        """Upload raw document bytes to S3 with server-side AES256 encryption."""
        client = self._get_client()
        try:
            client.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceException(
                f"Erro ao enviar arquivo para o armazenamento AWS S3: {exc}",
                error_code="S3_UPLOAD_ERROR",
            ) from exc

    def download_file(self, s3_key: str) -> bytes:
        """Download raw bytes from S3 (used when retrying a failed AI analysis)."""
        client = self._get_client()
        try:
            response = client.get_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
            )
            return response["Body"].read()
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceException(
                f"Erro ao recuperar arquivo do AWS S3: {exc}",
                error_code="S3_DOWNLOAD_ERROR",
            ) from exc

    def generate_presigned_url(
        self,
        s3_key: str,
        filename: str | None = None,
        expiration: int | None = None,
    ) -> str:
        """Generate a short-lived Presigned GET URL for an already-authorized user."""
        client = self._get_client()
        ttl = expiration or settings.AWS_PRESIGNED_URL_EXPIRATION
        params: dict[str, str] = {
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": s3_key,
        }
        if filename:
            safe_disp = filename.replace('"', "")
            params["ResponseContentDisposition"] = f'inline; filename="{safe_disp}"'

        try:
            return client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=ttl,
            )
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceException(
                f"Erro ao gerar URL segura de visualização no S3: {exc}",
                error_code="S3_PRESIGN_ERROR",
            ) from exc

    def delete_files(self, s3_keys: list[str]) -> None:
        """Delete one or more objects from S3 cleanly using batch delete_objects."""
        if not s3_keys:
            return
        client = self._get_client()
        try:
            objects = [{"Key": key} for key in s3_keys]
            # S3 delete_objects accepts up to 1000 keys per request
            for start in range(0, len(objects), 1000):
                batch = objects[start : start + 1000]
                client.delete_objects(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Delete={"Objects": batch, "Quiet": True},
                )
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceException(
                f"Erro ao remover arquivo(s) do AWS S3: {exc}",
                error_code="S3_DELETE_ERROR",
            ) from exc


s3_service = S3Service()
