"""Store documents and metadata in ChromaDB vector database."""

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


def get_or_create_collection(
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
):
    """
    Get or create a ChromaDB collection for teacher content.

    Args:
        persist_directory: Directory to persist the database.
        collection_name: Name of the collection.

    Returns:
        ChromaDB collection.
    """
    Path(persist_directory).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Teacher uploads: video transcripts, PDFs, docs"},
    )


def add_to_vector_db(
    text: str,
    metadata: dict[str, Any],
    doc_id: str | None = None,
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
) -> str:
    """
    Add a document (text) and metadata to the vector store.

    Args:
        text: Document text to embed and store.
        metadata: Metadata dict (e.g. user_id, subject, subject_id, chapter, chapter_id, part, file_type).
        doc_id: Optional unique ID; if None, one is generated.
        persist_directory: ChromaDB persist path.
        collection_name: Collection name.

    Returns:
        The document ID used.
    """
    if not text or not text.strip():
        raise ValueError("Cannot add empty text to vector store.")

    collection = get_or_create_collection(persist_directory, collection_name)

    # Chroma expects metadata values to be str, int, float, or bool
    safe_meta = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            safe_meta[k] = v
        else:
            safe_meta[k] = str(v)

    if doc_id is None:
        import uuid
        doc_id = str(uuid.uuid4())

    collection.add(
        documents=[text.strip()],
        metadatas=[safe_meta],
        ids=[doc_id],
    )
    return doc_id
