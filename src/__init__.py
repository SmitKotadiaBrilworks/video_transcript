"""Video transcript pipeline: video/doc/pdf upload → transcript → PDF → vector DB."""

from src.pipeline import process_upload

__all__ = ["process_upload"]
