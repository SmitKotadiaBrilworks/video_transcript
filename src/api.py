"""FastAPI APIs for video/PDF/DOCX transcription and question answering."""

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.answer_generator import ask_question
from src.pipeline import process_upload


app = FastAPI(
    title="Video Transcript & QA API",
    description=(
        "APIs for:\n"
        "- Video transcription (file or URL)\n"
        "- PDF / DOCX transcription\n"
        "- Question answering over stored transcripts using ChromaDB + Gemini\n"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadMetadata(BaseModel):
    video_id: Optional[str] = None
    user_id: Optional[str] = None
    subject: Optional[str] = None
    subject_id: Optional[str] = None
    chapter: Optional[str] = None
    chapter_id: Optional[str] = None
    part: Optional[str] = None


class QARequest(BaseModel):
    question: str
    video_id: Optional[str] = None
    n_context: int = 6


@app.post("/api/transcribe", summary="Transcribe video / PDF / DOCX (file or URL)")
async def transcribe(
    file: Optional[UploadFile] = File(
        default=None, description="Uploaded video/PDF/DOCX file (optional if url is provided)"
    ),
    url: Optional[str] = Form(
        default=None, description="Remote URL (YouTube, direct .mp4, PDF, DOCX, etc.)"
    ),
    video_id: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    subject: Optional[str] = Form(default=None),
    subject_id: Optional[str] = Form(default=None),
    chapter: Optional[str] = Form(default=None),
    chapter_id: Optional[str] = Form(default=None),
    part: Optional[str] = Form(default=None),
):
    """
    Transcribe a video, PDF, or DOCX from an uploaded file or URL.

    - If `file` is provided, it is saved to disk and processed.
    - If `url` is provided, it is downloaded (for video/PDF/DOCX) and processed.
    - The pipeline automatically:
        - Extracts audio from video and transcribes it.
        - Creates a transcript PDF for videos.
        - Extracts text from PDFs/DOCX.
        - Stores text in ChromaDB with metadata (video_id, subject, chapter, etc.).
    """
    if not file and not url:
        raise HTTPException(status_code=400, detail="Either 'file' or 'url' must be provided.")

    # Build metadata dict
    metadata: dict[str, Any] = {
        "video_id": video_id or "",
        "user_id": user_id or "",
        "subject": subject or "",
        "subject_id": subject_id or "",
        "chapter": chapter or "",
        "chapter_id": chapter_id or "",
        "part": part or "",
    }

    file_path: str
    if file is not None:
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "upload").name
        dest = uploads_dir / safe_name
        content = await file.read()
        dest.write_bytes(content)
        file_path = str(dest)
    else:
        file_path = url or ""

    result = process_upload(file_path, metadata=metadata)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transcription failed."))
    return result


@app.post("/api/qa", summary="Question answering over stored transcripts")
async def qa(payload: QARequest):
    """
    Ask a question and get an answer generated from stored transcripts.

    - Uses ChromaDB to retrieve the most relevant passages.
    - Uses Gemini to generate a precise, educational answer.
    - If `video_id` is provided, only passages from that video's vector data are used.
    """
    result = ask_question(
        question=payload.question,
        n_context=payload.n_context,
        video_id=payload.video_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Answer generation failed."))
    return result

