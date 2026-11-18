from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import auth, documents
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import AppException
import app.models  # noqa: F401 - ensure ORM models are registered on Base.metadata


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure database tables exist on startup during development."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Allows app & unit tests to import main even before Postgres container is running
        pass
    yield


app = FastAPI(
    title="Ju - Assistente Jurídica API (Jus Digital)",
    description=(
        "Sistema web de gestão e análise de documentos com IA, "
        "integrando Google OAuth 2.0, AWS S3 e OpenAI GPT-4o-mini."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = list(
    dict.fromkeys(
        [
            settings.FRONTEND_URL.rstrip("/"),
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """Return structured, predictable JSON errors for all domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic/FastAPI request validation errors into a friendly message."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Dados inválidos.") if errors else "Dados inválidos."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": f"Erro de validação nos campos enviados: {first_msg}",
            "details": errors,
        },
    )


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Liveness and PostgreSQL connectivity check."""
    db_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    return {"status": "ok", "database": db_status}


app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
