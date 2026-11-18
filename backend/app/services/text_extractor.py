from dataclasses import dataclass
import io
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader

from app.core.config import settings
from app.core.exceptions import ValidationException

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS

EXTENSION_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

MAX_EXTRACTED_CHARS = 60_000


@dataclass(frozen=True)
class ExtractedContent:
    """Normalized content ready to be sent to OpenAI GPT-4o-mini."""

    kind: str  # "text" or "image"
    text: str | None = None
    image_bytes: bytes | None = None
    mime_type: str = "application/octet-stream"


def normalize_extension(filename: str) -> str:
    """Return lowercase extension including the leading dot (e.g., '.pdf')."""
    return Path(filename).suffix.lower()


def validate_file(filename: str | None, file_bytes: bytes) -> tuple[str, str, str]:
    """
    Validate file name, non-empty size, max size (10MB), extension, and magic bytes.
    Returns (safe_filename, extension, resolved_mime_type).
    """
    if not filename or not filename.strip():
        raise ValidationException("Nome do arquivo inválido.")

    safe_name = Path(filename).name.strip()
    ext = normalize_extension(safe_name)

    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationException(
            f"Tipo de arquivo '{ext or 'desconhecido'}' não suportado. "
            f"Formatos aceitos: {allowed_list}."
        )

    size = len(file_bytes)
    if size == 0:
        raise ValidationException("O arquivo enviado está vazio.")

    if size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationException(
            f"O arquivo excede o limite máximo de {max_mb} MB."
        )

    _validate_magic_bytes(ext, file_bytes)
    return safe_name, ext, EXTENSION_TO_MIME[ext]


def _validate_magic_bytes(ext: str, data: bytes) -> None:
    """Verify real binary file headers to prevent disguised/spoofed uploads."""
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise ValidationException("O arquivo .pdf não possui assinatura PDF válida.")
    if ext == ".docx" and not data.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        raise ValidationException("O arquivo .docx não possui estrutura válida.")
    if ext == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationException("O arquivo .png não possui assinatura PNG válida.")
    if ext in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        raise ValidationException("O arquivo de imagem JPEG não é válido.")
    if ext == ".webp" and not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        raise ValidationException("O arquivo .webp não possui assinatura WEBP válida.")


def extract_content(
    file_bytes: bytes, extension: str, mime_type: str
) -> ExtractedContent:
    """
    Extract readable text from documents or prepare images for GPT-4o-mini Vision.
    Raises ValueError if the document is unreadable or contains no extractable text.
    """
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return ExtractedContent(
            kind="image",
            image_bytes=file_bytes,
            mime_type=mime_type,
        )

    if extension == ".pdf":
        text = _extract_pdf_text(file_bytes)
    elif extension == ".docx":
        text = _extract_docx_text(file_bytes)
    elif extension == ".doc":
        text = _extract_legacy_doc_text(file_bytes)
    elif extension in {".txt", ".md", ".csv"}:
        text = _decode_plain_text(file_bytes)
    else:
        raise ValueError(f"Formato não suportado para extração: {extension}")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError(
            "Não foi possível extrair texto legível do arquivo. "
            "Se for um PDF escaneado como imagem, envie uma captura em PNG/JPG ou um PDF com texto selecionável."
        )

    if len(cleaned) > MAX_EXTRACTED_CHARS:
        cleaned = (
            cleaned[:MAX_EXTRACTED_CHARS]
            + "\n\n[Conteúdo truncado para respeitar o limite de análise.]"
        )

    return ExtractedContent(kind="text", text=cleaned, mime_type=mime_type)


def _extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages_text: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages_text.append(f"--- Página {idx} ---\n{page_text}")
        return "\n\n".join(pages_text)
    except Exception as exc:
        raise ValueError(f"Falha ao ler arquivo PDF: {exc}") from exc


def _extract_docx_text(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
        parts: list[str] = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"Falha ao ler arquivo DOCX: {exc}") from exc


def _extract_legacy_doc_text(data: bytes) -> str:
    """
    Handle .doc files: if it's actually plain text/UTF-8 or DOCX-zip saved as .doc, extract it;
    legacy binary Word 97-2003 OLE (.doc) requires LibreOffice/antiword and gets a clear message.
    """
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return _extract_docx_text(data)
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise ValueError(
            "Arquivos binários legados .doc (Word 97-2003) não permitem extração direta. "
            "Por favor, salve como .docx ou .pdf e tente novamente."
        )
    return _decode_plain_text(data)


def _decode_plain_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o texto do arquivo.")
