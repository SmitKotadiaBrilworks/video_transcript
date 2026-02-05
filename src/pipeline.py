"""Main pipeline: route uploads by type (video / PDF / DOCX) or URL; process."""

import os
from pathlib import Path
from typing import Any

from src.audio_utils import extract_audio_from_video
from src.document_utils import extract_document_text
from src.download_utils import download_media, is_url
from src.pdf_generator import get_transcript_pdf_path, transcript_to_pdf
from src.transcription import transcribe_long_audio
from src.vector_store import add_chunked_to_vector_db


# Supported extensions
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv"}
DOC_EXTENSIONS = {".pdf", ".docx"}
DOCX_EXT = ".docx"
DOC_EXT = ".doc"


def _get_file_type(file_path: str) -> str:
    """Return 'video', 'pdf', 'docx', or 'unknown'."""
    suffix = Path(file_path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix == ".pdf":
        return "pdf"
    if suffix in (DOCX_EXT, DOC_EXT):
        return "docx" if suffix == DOCX_EXT else "doc"
    return "unknown"


def process_video(
    video_path: str,
    metadata: dict[str, Any],
    output_audio_dir: str = "output_audio_files",
    output_transcript_dir: str = "output_transcripts",
    chroma_dir: str = "chroma_db",
) -> dict[str, Any]:
    """
    Process a video: extract audio → transcribe → create PDF → store in vector DB.

    Args:
        video_path: Path to the video file.
        metadata: Metadata for vector DB (e.g. user_id, subject, subject_id, chapter, chapter_id, part).
        output_audio_dir: Directory for extracted audio.
        output_transcript_dir: Directory for transcript PDFs.
        chroma_dir: ChromaDB persist directory.

    Returns:
        Dict with keys: transcript_text, pdf_path, doc_id, success.
    """
    base_name = Path(video_path).stem
    result: dict[str, Any] = {"success": False, "transcript_text": "", "pdf_path": "", "doc_id": ""}

    # 1. Extract audio from video
    audio_path = extract_audio_from_video(video_path, output_dir=output_audio_dir)
    # 2. Transcribe (chunked for long audio)
    transcript = transcribe_long_audio(audio_path, output_dir=output_audio_dir)
    if not transcript:
        return result

    result["transcript_text"] = transcript

    # 3. Create PDF of transcript
    pdf_path = get_transcript_pdf_path(base_name, output_dir=output_transcript_dir)
    transcript_to_pdf(transcript, pdf_path, title=f"Transcript: {base_name}")
    result["pdf_path"] = pdf_path

    # 4. Store in vector DB with metadata (video_id = reference for filtering answers by video)
    meta = {
        "file_type": "video",
        "filename": os.path.basename(video_path),
        "video_id": metadata.get("video_id", ""),
        "subject": metadata.get("subject", ""),
        "subject_id": metadata.get("subject_id", ""),
        "chapter": metadata.get("chapter", ""),
        "chapter_id": metadata.get("chapter_id", ""),
        "part": metadata.get("part", ""),
        "user_id": metadata.get("user_id", ""),
    }
    source_id = add_chunked_to_vector_db(transcript, meta, source_id=None, persist_directory=chroma_dir)
    result["doc_id"] = source_id
    result["success"] = True
    return result


def process_document(
    file_path: str,
    metadata: dict[str, Any],
    chroma_dir: str = "chroma_db",
) -> dict[str, Any]:
    """
    Process a PDF or DOCX: extract text → store in vector DB.

    Args:
        file_path: Path to the PDF or DOCX file.
        metadata: Metadata for vector DB.
        chroma_dir: ChromaDB persist directory.

    Returns:
        Dict with keys: text, doc_id, success.
    """
    result: dict[str, Any] = {"success": False, "text": "", "doc_id": ""}
    text = extract_document_text(file_path)
    if not text:
        return result

    result["text"] = text
    meta = {
        "file_type": Path(file_path).suffix.lstrip(".").lower(),
        "filename": os.path.basename(file_path),
        "video_id": metadata.get("video_id", ""),
        "subject": metadata.get("subject", ""),
        "subject_id": metadata.get("subject_id", ""),
        "chapter": metadata.get("chapter", ""),
        "chapter_id": metadata.get("chapter_id", ""),
        "part": metadata.get("part", ""),
        "user_id": metadata.get("user_id", ""),
    }
    source_id = add_chunked_to_vector_db(text, meta, source_id=None, persist_directory=chroma_dir)
    result["doc_id"] = source_id
    result["success"] = True
    return result


def process_upload(
    file_path: str,
    metadata: dict[str, Any] | None = None,
    output_audio_dir: str = "output_audio_files",
    output_transcript_dir: str = "output_transcripts",
    chroma_dir: str = "chroma_db",
    download_dir: str = "downloaded_media",
) -> dict[str, Any]:
    """
    Process an uploaded file or URL: video → transcript + PDF + vector DB; PDF/DOCX → vector DB.

    If file_path is an HTTP(S) URL (e.g. YouTube link), it is downloaded first, then processed.

    Args:
        file_path: Path to a local file (video, PDF, DOCX) or a direct/YouTube URL.
        metadata: Optional metadata (video_id, user_id, subject, chapter, etc.).
        output_audio_dir: Directory for extracted audio (video only).
        output_transcript_dir: Directory for transcript PDFs (video only).
        chroma_dir: ChromaDB persist directory.
        download_dir: Directory for files downloaded from URLs (default: downloaded_media).

    Returns:
        Result dict (success, transcript_text or text, pdf_path if video, doc_id).
    """
    if metadata is None:
        metadata = {}

    if is_url(file_path):
        try:
            file_path = download_media(file_path, output_dir=download_dir)
        except Exception as e:
            return {"success": False, "error": f"Download failed: {e}"}

    file_type = _get_file_type(file_path)
    if file_type == "video":
        return process_video(
            file_path,
            metadata,
            output_audio_dir=output_audio_dir,
            output_transcript_dir=output_transcript_dir,
            chroma_dir=chroma_dir,
        )
    if file_type in ("pdf", "docx"):
        return process_document(file_path, metadata, chroma_dir=chroma_dir)

    return {"success": False, "error": f"Unsupported file type: {file_path}"}
