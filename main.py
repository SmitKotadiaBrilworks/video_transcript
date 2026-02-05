#!/usr/bin/env python3
"""
CLI entrypoint for the video/document transcript pipeline.

Usage:
  python3 main.py <file_path_or_url> [--video-id ID] [--subject SUBJECT] [--chapter CHAPTER] [--chapter-id ID] [--part PART] [--user-id USER_ID] 

  file_path_or_url: Local path (video, PDF, DOCX) or direct link (YouTube, etc.).

Example:
  python3 main.py lesson_01.mp4 --video-id v1 --subject "Physics" --chapter "Motion" --part "1"
  python3 main.py "https://www.youtube.com/watch?v=VIDEO_ID" --video-id v1 --subject "Physics" --chapter "Motion"
  python3 main.py notes.pdf --video-id v2 --subject "Math" --chapter "Algebra"
"""

import argparse
import sys

from src.pipeline import process_upload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process teacher uploads: video (transcribe → PDF) or PDF/DOCX → store in vector DB."
    )
    parser.add_argument("file_path", help="Path to video, PDF, or DOCX file, or URL (e.g. YouTube link)")
    parser.add_argument("--video-id", default="", dest="video_id", help="Video/content ID (stored in vector DB; use when asking for answers from this video only)")
    parser.add_argument("--subject", default="", help="Subject name")
    parser.add_argument("--subject-id", default="", dest="subject_id", help="Subject ID")
    parser.add_argument("--chapter", default="", help="Chapter name")
    parser.add_argument("--chapter-id", default="", dest="chapter_id", help="Chapter ID")
    parser.add_argument("--part", default="", help="Part number or name")
    parser.add_argument("--user-id", default="", dest="user_id", help="Teacher/user ID")
    parser.add_argument(
        "--audio-dir",
        default="output_audio_files",
        help="Directory for extracted audio (video only)",
    )
    parser.add_argument(
        "--transcript-dir",
        default="output_transcripts",
        help="Directory for transcript PDFs (video only)",
    )
    parser.add_argument(
        "--chroma-dir",
        default="chroma_db",
        help="ChromaDB persist directory",
    )
    args = parser.parse_args()

    metadata = {
        "video_id": args.video_id,
        "user_id": args.user_id,
        "subject": args.subject,
        "subject_id": args.subject_id,
        "chapter": args.chapter,
        "chapter_id": args.chapter_id,
        "part": args.part,
    }

    result = process_upload(
        args.file_path,
        metadata=metadata,
        output_audio_dir=args.audio_dir,
        output_transcript_dir=args.transcript_dir,
        chroma_dir=args.chroma_dir,
    )

    if result.get("success"):
        print("Success.")
        if result.get("transcript_text"):
            t = result["transcript_text"]
            print("Transcript (preview):", t[:200] + "..." if len(t) > 200 else t)
        if result.get("pdf_path"):
            print("Transcript PDF:", result["pdf_path"])
        if result.get("text"):
            t = result["text"]
            print("Extracted text (preview):", t[:200] + "..." if len(t) > 200 else t)
        print("Vector DB doc_id:", result.get("doc_id", ""))
        return 0
    else:
        print("Failed:", result.get("error", "Unknown error"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
