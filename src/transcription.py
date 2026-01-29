"""Transcribe audio using SpeechRecognition (Google Web Speech API)."""

import speech_recognition as sr


def audio_to_text(audio_path: str) -> str | None:
    """
    Transcribe a single audio file using Google Web Speech API.

    Args:
        audio_path: Path to WAV audio file.

    Returns:
        Transcribed text or None on failure.
    """
    recognizer = sr.Recognizer()

    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio.")
    except sr.RequestError as e:
        print(f"Error during speech recognition: {e}")

    return None


def transcribe_long_audio(
    audio_path: str,
    chunk_length_ms: int = 30_000,
    output_dir: str = "output_audio_files",
) -> str:
    """
    Transcribe long audio by splitting into chunks and concatenating results.

    Args:
        audio_path: Path to the full audio file (WAV).
        chunk_length_ms: Chunk length in ms (Google API works best with ~30s).
        output_dir: Directory for temporary chunk files.

    Returns:
        Full transcript text.
    """
    from src.audio_utils import split_audio_into_chunks

    chunks = split_audio_into_chunks(
        audio_path,
        chunk_length_ms=chunk_length_ms,
        output_dir=output_dir,
    )
    parts: list[str] = []
    for path in chunks:
        text = audio_to_text(path)
        if text:
            parts.append(text)
    return " ".join(parts).strip()
