"""Download video/audio from YouTube or direct URLs for pipeline processing."""

import os
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


# Domains that yt-dlp handles well (YouTube, etc.)
YT_DLP_DOMAINS = (
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "vimeo.com",
    "dailymotion.com",
    "facebook.com",
    "fb.watch",
    "twitter.com",
    "x.com",
)


def is_url(path: str) -> bool:
    """Return True if path looks like an HTTP(S) URL."""
    s = (path or "").strip()
    return s.startswith("http://") or s.startswith("https://")


def _is_yt_dlp_domain(url: str) -> bool:
    """Return True if URL is from a domain best handled by yt-dlp."""
    try:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").lower().lstrip("www.")
        return any(domain in netloc for domain in YT_DLP_DOMAINS)
    except Exception:
        return False


def _download_with_yt_dlp(url: str, output_dir: str) -> str:
    """Download with yt-dlp; returns path to the downloaded file (video/audio)."""
    import yt_dlp

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(output_dir, "%(id)s.%(ext)s")
    opts = {
        "outtmpl": outtmpl,
        "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as first_err:
        # Retry with minimal format if best-format extraction fails (e.g. n-challenge)
        opts["format"] = "best"
        opts.pop("merge_output_format", None)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception:
            raise first_err
    if not info:
        raise ValueError("yt-dlp could not extract video info")
    # Path from requested_downloads (merge output) or build from id/ext
    requested = info.get("requested_downloads") or []
    if requested and isinstance(requested[0], dict):
        filepath = requested[0].get("filepath")
        if filepath and os.path.isfile(filepath):
            return filepath
    vid = info.get("id") or "video"
    ext = (info.get("ext") or "mp4").lower()
    if ext not in ("mp4", "webm", "mkv", "m4a"):
        ext = "mp4"
    candidate = os.path.join(output_dir, f"{vid}.{ext}")
    if os.path.isfile(candidate):
        return candidate
    # Fallback: newest file in output_dir with video/audio ext
    exts = (".mp4", ".webm", ".mkv", ".m4a")
    for f in sorted(Path(output_dir).iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.suffix.lower() in exts:
            return str(f)
    raise FileNotFoundError("yt-dlp did not produce a recognizable file")


def _download_direct_url(url: str, output_dir: str) -> str:
    """Download from direct media URL (e.g. .mp4 link). Returns path to file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    parsed = urlparse(url)
    name = os.path.basename(parsed.path or "video").strip() or "video"
    if not re.search(r"\.(mp4|webm|mkv|mov|avi|m4a|mp3|wav)$", name, re.I):
        name = name + ".mp4"
    path = os.path.join(output_dir, name)
    # Avoid overwriting; make unique if needed
    if os.path.isfile(path):
        base, ext = os.path.splitext(name)
        for i in range(1, 100):
            path = os.path.join(output_dir, f"{base}_{i}{ext}")
            if not os.path.isfile(path):
                break
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; video_transcript/1.0)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(path, "wb") as f:
            f.write(resp.read())
    return path


def download_media(url: str, output_dir: str = "downloaded_media") -> str:
    """
    Download video/audio from a URL to a local file.

    - YouTube / youtu.be / Vimeo / etc.: uses yt-dlp (requires ffmpeg for merge).
    - Direct links (e.g. .mp4): downloaded with urllib.

    Args:
        url: HTTP(S) URL to the video or page (e.g. YouTube watch URL).
        output_dir: Directory to save the file (default: downloaded_media).

    Returns:
        Path to the downloaded file (e.g. .mp4).

    Raises:
        ValueError: Unsupported URL or download failure.
    """
    url = (url or "").strip()
    if not is_url(url):
        raise ValueError("Not a valid URL")
    if _is_yt_dlp_domain(url):
        return _download_with_yt_dlp(url, output_dir)
    return _download_direct_url(url, output_dir)
