from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in the project root (Jus-Digital/.env) or inside backend/.env
ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
LOCAL_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """
    Centralized application configuration validated via Pydantic Settings.
    Fails fast at startup if critical settings are malformed.
    """

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV_PATH), str(LOCAL_ENV_PATH)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # Security / JWT Session
    JWT_SECRET_KEY: str = "change-me-in-local-env-with-a-long-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    COOKIE_NAME: str = "jusdigital_session"

    # PostgreSQL Database
    DATABASE_URL: str = (
        "postgresql://jusdigital:jusdigital_dev_pass@localhost:5432/jusdigital_db"
    )

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # AWS S3 Storage
    AWS_REGION: str = "sa-east-1"
    AWS_S3_BUCKET_NAME: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_PRESIGNED_URL_EXPIRATION: int = 900  # 15 minutes

    # OpenAI API
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Upload Validation Limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


settings = Settings()
