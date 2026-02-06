"""FastAPI APIs for video/PDF/DOCX transcription and question answering."""

import logging
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.answer_generator import ask_question
from src.pipeline import process_upload

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class TranscribeByUrlRequest(BaseModel):
    """JSON body for URL-only transcribe (no file upload)."""
    url: str
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


def _run_transcribe(file_path: str, metadata: dict[str, Any]):
    """Shared transcribe logic."""
    result = process_upload(file_path, metadata=metadata)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transcription failed."))
    return result


def _get_body(data: dict[str, Any]):
    file = data.get("file")
    url = data.get("url")
    video_id = data.get("video_id")
    subject = data.get("subject")
    chapter = data.get("chapter")
    subject_id = data.get("subject_id")
    chapter_id = data.get("chapter_id")
    part = data.get("part")
    user_id = data.get("user_id")
    
    return file, url, video_id, subject, chapter, subject_id, chapter_id, part, user_id

@app.post("/api/transcribe")
async def transcribe(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    video_id: Optional[str] = Form(default=None),
    subject: Optional[str] = Form(default=None),
    chapter: Optional[str] = Form(default=None),
    subject_id: Optional[str] = Form(default=None),
    chapter_id: Optional[str] = Form(default=None),
    part: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
):
    content_type = request.headers.get("content-type", "")
    logger.info(f"content_type: {content_type}")

    if "application/json" in content_type:
        body = await request.json()

        file, url, video_id, subject, chapter, subject_id, chapter_id, part, user_id = _get_body(body)

    else:
        body = await request.form()
        logger.info(f"body: {body}")

        file, url, video_id, subject, chapter, subject_id, chapter_id, part, user_id = _get_body(body)

    logger.info(
        "transcribe request: url=%s video_id=%s subject=%s chapter=%s",
        url, video_id, subject, chapter
    )

    if not file and not url:
        raise HTTPException(status_code=400, detail="Either file or url required")

    metadata: dict[str, Any] = {
        "video_id": video_id or "",
        "user_id": user_id or "",
        "subject": subject or "",
        "subject_id": subject_id or "",
        "chapter": chapter or "",
        "chapter_id": chapter_id or "",
        "part": part or "",
    }

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

    return _run_transcribe(file_path, metadata)


# @app.post("/api/transcribe/url", summary="Transcribe from URL only (JSON body)")
# async def transcribe_by_url(payload: TranscribeByUrlRequest):
#     """
#     Transcribe from a remote URL only. Send JSON body: {"url": "...", "video_id": "...", "subject": "...", ...}.
#     Use this from Postman with Body → raw → JSON to avoid form-data issues.
#     """
#     metadata: dict[str, Any] = {
#         "video_id": payload.video_id or "",
#         "user_id": payload.user_id or "",
#         "subject": payload.subject or "",
#         "subject_id": payload.subject_id or "",
#         "chapter": payload.chapter or "",
#         "chapter_id": payload.chapter_id or "",
#         "part": payload.part or "",
#     }
#     return _run_transcribe(payload.url, metadata)


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

