"""Extract text from PDF and DOC/DOCX files."""

from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text.
    """
    reader = PdfReader(pdf_path)
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def extract_text_from_docx(doc_path: str) -> str:
    """
    Extract all text from a DOCX file.

    Args:
        doc_path: Path to the .docx file.

    Returns:
        Extracted text.
    """
    doc = Document(doc_path)
    parts: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    return "\n".join(parts).strip()


def extract_document_text(file_path: str) -> str | None:
    """
    Extract text from a PDF or DOCX file based on extension.

    Args:
        file_path: Path to the file.

    Returns:
        Extracted text or None if format not supported.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    if suffix in (".docx", ".doc"):
        # python-docx only supports .docx; .doc would need another lib
        if suffix == ".doc":
            return None  # Legacy .doc not supported by python-docx
        return extract_text_from_docx(file_path)
    return None
