"""Generate precise, educational answers from vector DB context using Google Gemini."""

import os
from typing import Any

from src.vector_store import query_vector_db


LEARNING_PORTAL_SYSTEM_PROMPT = """You are an expert teaching assistant for a learning portal. Your role is to answer student questions based ONLY on the provided course material (transcripts and documents).

Rules:
- Answer precisely and clearly using only the context given below. Do not add information that is not in the context.
- Use a structured, educational tone suitable for students (clear explanations, step-by-step when helpful).
- If the context does not contain enough information to answer the question, say so clearly and suggest what topic to review.
- Keep answers focused and concise but complete enough for learning.
- You may cite the source (e.g. "From the chapter on Motion...") when it helps clarity."""


def get_context_from_vector_db(
    question: str,
    n_results: int = 6,
    video_id: str | None = None,
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Get the most relevant passages from the vector DB for a question.

    If video_id is provided, only chunks from that video (metadata video_id) are searched.

    Returns:
        (list of passage texts, list of metadata dicts).
    """
    where = {"video_id": video_id} if video_id else None
    result = query_vector_db(
        query_text=question,
        n_results=n_results,
        where=where,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    return documents, metadatas


def build_context_block(documents: list[str], metadatas: list[dict]) -> str:
    """Build a single context string from passages and their metadata."""
    parts = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
        filename = (meta or {}).get("filename", "Unknown")
        subject = (meta or {}).get("subject", "")
        chapter = (meta or {}).get("chapter", "")
        source = f"[Source {i}: {filename}"
        if subject or chapter:
            source += f" — {subject}"
            if chapter:
                source += f", {chapter}"
        source += "]\n"
        parts.append(source + (doc or ""))
    return "\n\n---\n\n".join(parts)


def generate_answer_with_gemini(
    question: str,
    context_text: str,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """
    Use Google Gemini to generate a precise answer from the given context.

    Args:
        question: The student's question.
        context_text: Relevant passages from the vector DB (course material).
        api_key: Gemini API key. If None, uses env var GEMINI_API_KEY.
        model: Gemini model name (default gemini-2.5-flash).

    Returns:
        Generated answer text.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key required. Set GEMINI_API_KEY environment variable or pass api_key=..."
        )

    from google import genai

    client = genai.Client(api_key=api_key)

    full_prompt = f"""{LEARNING_PORTAL_SYSTEM_PROMPT}

---

## Course material (use only this to answer):

{context_text}

---

## Student's question:

{question}

---

Provide a precise, clear answer suitable for a learning portal based only on the course material above."""

    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
    )
    return (response.text or "").strip()


def ask_question(
    question: str,
    n_context: int = 6,
    video_id: str | None = None,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
) -> dict[str, Any]:
    """
    Answer a question using vector DB context + Google Gemini (learning portal).

    If video_id is provided, the answer is generated only from that video's vector data.

    1. Retrieves relevant passages from the vector DB (optionally filtered by video_id).
    2. Sends question + passages to Gemini to generate a precise answer.

    Returns:
        dict with keys: answer, passages_used (list of dicts with text, metadata), success, error.
    """
    result = {"answer": "", "passages_used": [], "success": False, "error": None}
    try:
        documents, metadatas = get_context_from_vector_db(
            question,
            n_results=n_context,
            video_id=video_id,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )
        if not documents:
            if video_id:
                result["answer"] = (
                    f"No relevant course material found for video_id '{video_id}'. "
                    "Make sure the video was uploaded with this video_id and try rephrasing your question."
                )
            else:
                result["answer"] = "No relevant course material found. Please make sure videos or documents have been uploaded and try rephrasing your question."
            result["success"] = True
            return result

        result["passages_used"] = [
            {"text": doc, "metadata": meta} for doc, meta in zip(documents, metadatas)
        ]
        context_text = build_context_block(documents, metadatas)
        answer = generate_answer_with_gemini(
            question, context_text, api_key=api_key, model=model
        )
        result["answer"] = answer
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result
