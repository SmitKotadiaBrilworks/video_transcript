"""Extract audio from video files using pydub (requires ffmpeg)."""

import os
from pathlib import Path

from pydub import AudioSegment


def extract_audio_from_video(
    video_path: str,
    output_dir: str = "output_audio_files",
    output_format: str = "wav",
) -> str:
    """
    Extract audio from a video file and save as WAV (or other format).

    Args:
        video_path: Path to the video file.
        output_dir: Directory to save the extracted audio.
        output_format: Output format (wav recommended for speech recognition).

    Returns:
        Path to the extracted audio file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    base = Path(video_path).stem
    out_path = os.path.join(output_dir, f"{base}_audio.{output_format}")

    # Load video and export audio
    audio = AudioSegment.from_file(video_path)
    audio.export(out_path, format=output_format)
    return out_path


def split_audio_into_chunks(
    audio_path: str,
    chunk_length_ms: int = 30_000,
    output_dir: str = "output_audio_files",
) -> list[str]:
    """
    Split audio into chunks (e.g. 30 seconds) for APIs with length limits.

    Args:
        audio_path: Path to the audio file.
        chunk_length_ms: Length of each chunk in milliseconds (default 30 sec).
        output_dir: Directory to save chunks.

    Returns:
        List of paths to chunk files.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    base = Path(audio_path).stem

    audio = AudioSegment.from_file(audio_path)
    chunks: list[str] = []
    start = 0
    i = 0
    while start < len(audio):
        chunk = audio[start : start + chunk_length_ms]
        out_path = os.path.join(output_dir, f"{base}_segment_{i}.wav")
        chunk.export(out_path, format="wav")
        chunks.append(out_path)
        start += chunk_length_ms
        i += 1
    return chunks
