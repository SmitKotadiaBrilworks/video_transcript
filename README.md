# Video Transcript Pipeline

Python pipeline for teacher uploads: **video**, **PDF**, or **DOCX** → extract/transcribe → PDF (for video) → store in vector DB with metadata.

## Requirements

- **Python 3.10+**
- **ffmpeg** (for video → audio extraction)

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg
```

## Install

```bash
pip install -r requirements.txt
```

Use **`python3`** to run (not `python` on systems where only `python3` is installed):

```bash
python3 main.py path/to/video.mp4 --subject "Physics" ...
```

## Supported Uploads

| Type      | Flow                                                                                                                                       |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Video** | Extract audio (pydub) → Transcribe (SpeechRecognition / Google Web Speech API) → Create transcript PDF → Store text + metadata in ChromaDB |
| **PDF**   | Extract text (pypdf) → Store text + metadata in ChromaDB                                                                                   |
| **DOCX**  | Extract text (python-docx) → Store text + metadata in ChromaDB                                                                             |

**Note:** Legacy `.doc` is not supported; use `.docx` only.

## Usage

### CLI

```bash
# Video: transcribe → PDF → vector DB
python main.py path/to/lesson.mp4 --subject "Physics" --subject-id 1 --chapter "Motion" --chapter-id 2 --part "1" --user-id teacher_01

# PDF or DOCX: extract text → vector DB
python main.py path/to/notes.pdf --subject "Math" --subject-id 1 --chapter "Algebra" --chapter-id 3
python main.py path/to/handout.docx --subject "Chemistry" --subject-id 2 --chapter "Reactions" --chapter-id 1
```

### From Python

```python
from src.pipeline import process_upload

metadata = {"user_id": "teacher_01", "subject": "Physics", "subject_id": "1", "chapter": "Motion", "chapter_id": "2", "part": "1"}

# Video
result = process_upload("lesson.mp4", metadata=metadata)
# result: {"success": True, "transcript_text": "...", "pdf_path": "output_transcripts/lesson_transcript.pdf", "doc_id": "..."}

# PDF or DOCX
result = process_upload("notes.pdf", metadata=metadata)
# result: {"success": True, "text": "...", "doc_id": "..."}
```

## Project Layout

```
video_transcript/
├── main.py                 # CLI entrypoint
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── audio_utils.py      # Extract audio from video (pydub), split into chunks
│   ├── transcription.py    # Audio → text (SpeechRecognition / Google)
│   ├── document_utils.py   # PDF/DOCX text extraction
│   ├── pdf_generator.py    # Transcript text → PDF (reportlab)
│   ├── vector_store.py     # ChromaDB: add documents with metadata
│   └── pipeline.py         # process_upload() routes by file type
├── output_audio_files/     # Extracted/chunked audio (video only)
├── output_transcripts/     # Generated transcript PDFs
└── chroma_db/              # ChromaDB persistence
```

## Transcription

- Uses **SpeechRecognition** with **Google Web Speech API** (free, no API key).
- Long audio is split into ~30s chunks; each chunk is transcribed and results are concatenated.

## Vector DB (ChromaDB)

- Stored under `chroma_db/` by default.
- Metadata stored per document: `file_type`, `filename`, `subject`, `subject_id`, `chapter`, `chapter_id`, `part`, `user_id`.

## License

MIT
