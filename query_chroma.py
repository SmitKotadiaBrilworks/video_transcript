#!/usr/bin/env python3
"""
Query ChromaDB: ask a question → get relevant passages, or generate an answer with Gemini (learning portal).

Usage:
  # Get a precise answer from course material using Google Gemini (learning portal)
  python3 query_chroma.py --ask "What is work in physics?"
  export GEMINI_API_KEY=your_key   # or use --api-key

  # Raw passages only (semantic search, no Gemini)
  python3 query_chroma.py --query "How does motion work?"

  # List all stored chunks with their metadata
  python3 query_chroma.py --list
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from src.vector_store import list_all_documents, query_vector_db

# Load .env so GEMINI_API_KEY is available (if not set in shell)
load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query ChromaDB: semantic search or list all stored docs with metadata."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ask", "-a",
        metavar="QUESTION",
        help="Generate a precise answer using vector DB + Google Gemini (learning portal).",
    )
    group.add_argument(
        "--query", "-q",
        metavar="QUESTION",
        help="Return only the most relevant passages (chunks), no Gemini.",
    )
    group.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all stored chunks with their metadata.",
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=5,
        help="Number of passages for --query (default: 5).",
    )
    parser.add_argument(
        "--n-context",
        type=int,
        default=6,
        help="Number of passages to send to Gemini for --ask (default: 6).",
    )
    parser.add_argument(
        "--chroma-dir",
        default="chroma_db",
        help="ChromaDB persist directory.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API key (default: GEMINI_API_KEY env var).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of pretty-printed summary.",
    )
    args = parser.parse_args()

    if args.ask is not None:
        from src.answer_generator import ask_question
        result = ask_question(
            question=args.ask,
            n_context=args.n_context,
            api_key=args.api_key,
            persist_directory=args.chroma_dir,
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0
        if not result["success"]:
            print("Error:", result.get("error", "Unknown error"), file=sys.stderr)
            return 1
        print("=== Answer (from course material via Gemini) ===\n")
        print(result["answer"])
        if result.get("passages_used"):
            print("\n--- Sources used ---")
            for i, p in enumerate(result["passages_used"][:3], 1):
                fn = (p.get("metadata") or {}).get("filename", "?")
                print(f"  {i}. {fn}")
        return 0

    if args.list:
        data = list_all_documents(persist_directory=args.chroma_dir)
        if args.json:
            print(json.dumps(data, indent=2, default=str))
            return 0
        print("=== ChromaDB: All stored passages (chunks) with metadata ===\n")
        print(f"Total chunks: {data['count']}\n")
        for i, (doc_id, doc_text, meta) in enumerate(
            zip(data["ids"], data["documents"], data["metadatas"]), 1
        ):
            filename = (meta or {}).get("filename", "")
            chunk_idx = (meta or {}).get("chunk_index")
            total = (meta or {}).get("total_chunks")
            label = f"passage {chunk_idx + 1} of {total}" if chunk_idx is not None and total is not None else "full doc"
            print(f"--- Chunk {i} (id: {doc_id}) | from: {filename} [{label}] ---")
            print("Metadata:", json.dumps(meta, indent=2, default=str))
            preview = (doc_text or "")[:300] + "..." if len(doc_text or "") > 300 else (doc_text or "")
            print("Passage:", preview)
            print()
        return 0

    # --query
    result = query_vector_db(
        args.query,
        n_results=args.n_results,
        persist_directory=args.chroma_dir,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    print("=== ChromaDB: Most relevant passages (chunks) for your question ===\n")
    print("Your question:", args.query)
    print()
    if not result["documents"]:
        print("No passages found.")
        return 0
    for i, (doc_id, doc_text, meta, dist) in enumerate(
        zip(
            result["ids"],
            result["documents"],
            result["metadatas"],
            result.get("distances") or [None] * len(result["ids"]),
        ),
        1,
    ):
        filename = (meta or {}).get("filename", "")
        chunk_idx = (meta or {}).get("chunk_index")
        total = (meta or {}).get("total_chunks")
        label = f"chunk {chunk_idx + 1} of {total}" if chunk_idx is not None and total is not None else "full doc"
        print(f"--- Passage {i} (distance: {dist}) | from: {filename} [{label}] ---")
        print("Metadata:", json.dumps(meta, indent=2, default=str))
        # Show full chunk (it's a short passage, ~500 chars)
        print("Passage:", doc_text or "")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
