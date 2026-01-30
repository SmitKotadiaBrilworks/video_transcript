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
├── main.py                 # CLI: process uploads (video/PDF/DOCX)
├── query_chroma.py         # CLI: query ChromaDB or list all docs with metadata
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── audio_utils.py      # Extract audio from video (pydub), split into chunks
│   ├── transcription.py   # Audio → text (SpeechRecognition / Google)
│   ├── document_utils.py   # PDF/DOCX text extraction
│   ├── pdf_generator.py    # Transcript text → PDF (reportlab)
│   ├── vector_store.py    # ChromaDB: add/query chunks with metadata
│   ├── answer_generator.py # Gemini: precise answers from vector DB context (learning portal)
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
- **Chunking:** Transcripts and documents are split into ~500-character passages (with overlap). Queries return the **most relevant passages**, not full transcripts.
- Metadata per chunk: `file_type`, `filename`, `subject`, `subject_id`, `chapter`, `chapter_id`, `part`, `user_id`, `chunk_index`, `total_chunks`, `source_id`.

### Query ChromaDB (ask a question → get relevant passages)

ChromaDB embeds your question and returns the **most similar documents** (semantic search). Use `query_chroma.py`:

```bash
# Ask a question → returns related documents from all stored docs
python3 query_chroma.py --query "How does motion work?"
python3 query_chroma.py -q "What happens when you push something?" --n-results 3

# List all stored documents and their metadata (see how data is stored)
python3 query_chroma.py --list
python3 query_chroma.py -l --json   # raw JSON output
```

- **`--ask "question"`**: **Learning portal mode.** Retrieves relevant passages from the vector DB, then uses **Google Gemini** to generate a **precise, educational answer** based only on that material. Requires `GEMINI_API_KEY` (get one at [Google AI Studio](https://aistudio.google.com/app/apikey)).
- **`--query "question"`**: Raw semantic search — returns the most similar **passages (chunks)** by meaning (no Gemini). Each result includes metadata and distance (lower = more similar).
- **`--list`**: Shows every chunk in the DB with its metadata and a passage preview.

**Generate an answer (Gemini + vector DB):**

```bash
python3 query_chroma.py --ask "What is work in physics?"
python3 query_chroma.py -a "How does motion work?" --n-context 8
```

**Where to add your Gemini API key** (get one at [Google AI Studio](https://aistudio.google.com/app/apikey)):

| Option                         | Where                                                                                                                          | Use when                                                                                                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`.env` file** (recommended)  | In the project root, create a file named `.env` with one line: `GEMINI_API_KEY=your_actual_key`                                | You want the key loaded automatically and not committed to git (`.env` is in `.gitignore`). Copy from `.env.example`: `cp .env.example .env` then edit `.env`. |
| **Terminal (current session)** | Run in the same terminal before the script: `export GEMINI_API_KEY=your_actual_key`                                            | Quick test; key is not saved.                                                                                                                                  |
| **Shell profile**              | Add `export GEMINI_API_KEY=your_actual_key` to `~/.bashrc` or `~/.zshrc`, then run `source ~/.bashrc` (or reopen the terminal) | You want the key set in every new terminal.                                                                                                                    |
| **CLI flag**                   | Run: `python3 query_chroma.py --ask "..." --api-key your_actual_key`                                                           | One-off run without saving the key anywhere.                                                                                                                   |

### From Python

```python
from src.vector_store import query_vector_db, list_all_documents
from src.answer_generator import ask_question

# Generate a precise answer from course material (Gemini + vector DB)
result = ask_question("What is work in physics?", n_context=6)
# result["answer"], result["success"], result["passages_used"], result["error"]

# Semantic search only (no Gemini)
result = query_vector_db("How does motion work?", n_results=5)
# result["documents"], result["metadatas"], result["ids"], result["distances"]

# Inspect all stored data with metadata
data = list_all_documents()
# data["ids"], data["documents"], data["metadatas"], data["count"]
```
