import io

from docx import Document as DocxDocument
from pypdf import PdfWriter
import pytest

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.text_extractor import (
    MAX_EXTRACTED_CHARS,
    extract_content,
    validate_file,
)


def _make_docx_bytes(paragraphs: list[str], table_rows: list[list[str]] | None = None) -> bytes:
    """Create a real in-memory .docx file with paragraphs and optional table rows."""
    doc = DocxDocument()
    for text in paragraphs:
        doc.add_paragraph(text)
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for row_idx, row in enumerate(table_rows):
            for col_idx, cell_text in enumerate(row):
                table.cell(row_idx, col_idx).text = cell_text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_blank_pdf_bytes() -> bytes:
    """Create a valid PDF with one blank page (no selectable text)."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_text_pdf_bytes(text: str) -> bytes:
    """Build a minimal valid single-page PDF containing selectable ASCII text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.write(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    return out.getvalue()


# ---------------------------------------------------------------------------
# validate_file tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_name", "payload", "expected_name", "expected_ext", "expected_mime"),
    [
        ("../../pasta/CONTRATO.PDF", b"%PDF-1.4 fake body", "CONTRATO.PDF", ".pdf", "application/pdf"),
        (
            "peticao.DOCX",
            b"PK\x03\x04fake-zip",
            "peticao.DOCX",
            ".docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("antigo.DOC", b"Texto legado", "antigo.DOC", ".doc", "application/msword"),
        ("notas.TXT", b"Texto juridico", "notas.TXT", ".txt", "text/plain"),
        ("resumo.MD", b"# Clausula", "resumo.MD", ".md", "text/markdown"),
        ("tabela.CSV", b"parte,valor\nJus,100", "tabela.CSV", ".csv", "text/csv"),
        ("comprovante.PNG", b"\x89PNG\r\n\x1a\nrest", "comprovante.PNG", ".png", "image/png"),
        ("foto.JPG", b"\xff\xd8\xff\xe0rest", "foto.JPG", ".jpg", "image/jpeg"),
        ("foto.JPEG", b"\xff\xd8\xff\xe0rest", "foto.JPEG", ".jpeg", "image/jpeg"),
        ("scan.webp", b"RIFF\x00\x00\x00\x00WEBPdata", "scan.webp", ".webp", "image/webp"),
    ],
)
def test_validate_file_accepts_all_supported_formats_and_normalizes_uppercase(
    raw_name, payload, expected_name, expected_ext, expected_mime
):
    safe_name, ext, mime = validate_file(raw_name, payload)
    assert safe_name == expected_name
    assert ext == expected_ext
    assert mime == expected_mime


@pytest.mark.parametrize("bad_name", [None, "", "   "])
def test_validate_file_rejects_missing_filename(bad_name):
    with pytest.raises(ValidationException, match="Nome do arquivo inválido"):
        validate_file(bad_name, b"conteudo")


@pytest.mark.parametrize("filename", ["virus.exe", "script.sh", "arquivo_sem_extensao"])
def test_validate_file_rejects_unsupported_extensions(filename):
    with pytest.raises(ValidationException, match="não suportado"):
        validate_file(filename, b"conteudo")


def test_validate_file_rejects_empty_file():
    with pytest.raises(ValidationException, match="vazio"):
        validate_file("vazio.txt", b"")


def test_validate_file_respects_exact_size_boundary():
    exact_limit = b"a" * settings.MAX_UPLOAD_SIZE_BYTES
    safe_name, ext, _ = validate_file("limite.txt", exact_limit)
    assert safe_name == "limite.txt"
    assert ext == ".txt"

    over_limit = b"a" * (settings.MAX_UPLOAD_SIZE_BYTES + 1)
    with pytest.raises(ValidationException, match="limite máximo"):
        validate_file("grande.txt", over_limit)


@pytest.mark.parametrize(
    ("filename", "payload", "expected_error"),
    [
        ("falso.pdf", b"nao sou um pdf", "assinatura PDF"),
        ("falso.docx", b"nao sou um zip", "estrutura válida"),
        ("falso.png", b"nao sou um png", "assinatura PNG"),
        ("falso.jpg", b"nao sou um jpg", "JPEG"),
        ("falso.webp", b"RIFF0000XXXXdata", "assinatura WEBP"),
    ],
)
def test_validate_file_rejects_spoofed_magic_bytes(filename, payload, expected_error):
    with pytest.raises(ValidationException, match=expected_error):
        validate_file(filename, payload)


# ---------------------------------------------------------------------------
# extract_content tests
# ---------------------------------------------------------------------------


def test_extract_content_decodes_utf8_and_latin1_accents():
    utf8_bytes = "Cláusula 1ª: rescisão contratual com aviso prévio.".encode("utf-8")
    result_utf8 = extract_content(utf8_bytes, ".txt", "text/plain")
    assert result_utf8.kind == "text"
    assert "Cláusula 1ª" in (result_utf8.text or "")

    latin1_bytes = "Notificação extrajudicial - ação nº 42.".encode("latin-1")
    result_latin1 = extract_content(latin1_bytes, ".txt", "text/plain")
    assert result_latin1.kind == "text"
    assert "Notificação extrajudicial" in (result_latin1.text or "")


def test_extract_content_reads_docx_paragraphs_and_tables():
    docx_bytes = _make_docx_bytes(
        paragraphs=["Contrato de Prestacao de Servicos", "Clausula primeira."],
        table_rows=[["Parte", "Valor"], ["Jus Digital", "R$ 5.000,00"]],
    )
    result = extract_content(
        docx_bytes,
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert result.kind == "text"
    assert result.text is not None
    assert "Contrato de Prestacao de Servicos" in result.text
    assert "Jus Digital | R$ 5.000,00" in result.text


def test_extract_content_reads_selectable_pdf_text():
    pdf_bytes = _make_text_pdf_bytes("Peticao inicial protocolo 2026")
    result = extract_content(pdf_bytes, ".pdf", "application/pdf")

    assert result.kind == "text"
    assert result.text is not None
    assert "--- Página 1 ---" in result.text
    assert "Peticao inicial protocolo 2026" in result.text


def test_extract_content_rejects_blank_scanned_pdf():
    blank_pdf = _make_blank_pdf_bytes()
    with pytest.raises(ValueError, match="Não foi possível extrair texto legível"):
        extract_content(blank_pdf, ".pdf", "application/pdf")


def test_extract_content_corrupted_pdf_returns_sanitized_message():
    with pytest.raises(ValueError, match="Não foi possível ler o arquivo PDF") as exc_info:
        extract_content(b"%PDF-1.4 corrupted-garbage", ".pdf", "application/pdf")

    msg = str(exc_info.value)
    assert "EOF" not in msg
    assert "pypdf" not in msg.lower()


def test_extract_content_corrupted_docx_returns_sanitized_message():
    with pytest.raises(ValueError, match="Não foi possível ler o arquivo DOCX") as exc_info:
        extract_content(
            b"PK\x03\x04corrupted-docx-payload",
            ".docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    msg = str(exc_info.value)
    assert "BytesIO" not in msg
    assert "zip" not in msg.lower()


def test_extract_content_rejects_legacy_binary_ole_doc():
    ole_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32
    with pytest.raises(ValueError, match="binários legados .doc"):
        extract_content(ole_bytes, ".doc", "application/msword")


def test_extract_content_truncates_very_long_documents():
    huge_text = ("A" * (MAX_EXTRACTED_CHARS + 500)).encode("utf-8")
    result = extract_content(huge_text, ".txt", "text/plain")

    assert result.kind == "text"
    assert result.text is not None
    assert result.text.startswith("A" * 100)
    assert "[Conteúdo truncado para respeitar o limite de análise.]" in result.text


def test_extract_content_prepares_image_for_vision():
    png_bytes = b"\x89PNG\r\n\x1a\nfake-image-payload"
    result = extract_content(png_bytes, ".png", "image/png")

    assert result.kind == "image"
    assert result.text is None
    assert result.image_bytes == png_bytes
    assert result.mime_type == "image/png"
