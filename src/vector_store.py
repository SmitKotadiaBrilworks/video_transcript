"""Store documents and metadata in ChromaDB vector database."""

import os
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[str]:
    """
    Split text into overlapping chunks so queries return relevant passages, not full docs.

    Args:
        text: Full document text.
        chunk_size: Target characters per chunk (default 500).
        overlap: Overlap between consecutive chunks (default 80).

    Returns:
        List of chunk strings.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Prefer breaking at sentence end (., !, ?) or space
        if end < len(text):
            for sep in (". ", "! ", "? ", " "):
                last = chunk.rfind(sep)
                if last > chunk_size // 2:
                    chunk = chunk[: last + len(sep)].strip()
                    end = start + len(chunk)
                    break
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end
    return chunks


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
        doc_id = str(uuid.uuid4())

    collection.add(
        documents=[text.strip()],
        metadatas=[safe_meta],
        ids=[doc_id],
    )
    return doc_id


def add_chunked_to_vector_db(
    text: str,
    metadata: dict[str, Any],
    source_id: str | None = None,
    chunk_size: int = 500,
    overlap: int = 80,
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
) -> str:
    """
    Chunk text into passages and store each chunk in the vector DB.

    Queries then return the most relevant chunks (passages) instead of full documents.

    Args:
        text: Full document text (transcript or extracted PDF/DOCX).
        metadata: Metadata for all chunks (subject, chapter, filename, etc.).
        source_id: Optional ID for this upload; if None, one is generated.
        chunk_size: Characters per chunk (default 500).
        overlap: Overlap between chunks (default 80).
        persist_directory: ChromaDB persist path.
        collection_name: Collection name.

    Returns:
        The source_id (one per upload; chunks get ids like source_id_chunk_0).
    """
    if not text or not text.strip():
        raise ValueError("Cannot add empty text to vector store.")

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise ValueError("Chunking produced no chunks.")

    if source_id is None:
        source_id = str(uuid.uuid4())

    collection = get_or_create_collection(persist_directory, collection_name)
    total_chunks = len(chunks)

    # Chroma expects metadata values to be str, int, float, or bool
    base_meta = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            base_meta[k] = v
        else:
            base_meta[k] = str(v)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        ids.append(f"{source_id}_chunk_{i}")
        documents.append(chunk)
        meta = {**base_meta, "chunk_index": i, "total_chunks": total_chunks, "source_id": source_id}
        metadatas.append(meta)

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return source_id


def query_vector_db(
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
):
    """
    Ask a question and get the most relevant documents (semantic search).

    ChromaDB embeds your query and finds documents whose embeddings are closest.
    Use where to filter by metadata (e.g. {"video_id": "v123"} to get only that video's chunks).

    Args:
        query_text: Your question or search phrase.
        n_results: Max number of documents to return (default 5).
        where: Optional metadata filter, e.g. {"video_id": "v123"}. Only matching chunks are searched.
        persist_directory: ChromaDB persist path.
        collection_name: Collection name.

    Returns:
        dict with keys: ids, documents, metadatas, distances (lower = more similar).
    """
    collection = get_or_create_collection(persist_directory, collection_name)
    kwargs = {
        "query_texts": [query_text],
        "n_results": min(n_results, collection.count()),
    }
    if where:
        kwargs["where"] = where
    result = collection.query(**kwargs)
    # query() returns lists of lists (one per query); we have one query
    return {
        "ids": result["ids"][0] if result["ids"] else [],
        "documents": result["documents"][0] if result["documents"] else [],
        "metadatas": result["metadatas"][0] if result["metadatas"] else [],
        "distances": result["distances"][0] if result.get("distances") and result["distances"] else [],
    }


def list_all_documents(
    persist_directory: str = "chroma_db",
    collection_name: str = "teacher_content",
):
    """
    List all documents stored in the vector DB with their metadata.

    Shows how ChromaDB stores data: each doc has an id, text (document), and metadata.

    Returns:
        dict with keys: ids, documents, metadatas, count.
    """
    collection = get_or_create_collection(persist_directory, collection_name)
    count = collection.count()
    if count == 0:
        return {"ids": [], "documents": [], "metadatas": [], "count": 0}
    result = collection.get(
        include=["documents", "metadatas"],
    )
    return {
        "ids": result["ids"],
        "documents": result["documents"],
        "metadatas": result["metadatas"],
        "count": count,
    }
