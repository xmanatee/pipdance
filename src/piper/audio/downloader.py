"""
YouTube video downloader for audio analysis.

Downloads videos/audio from YouTube URLs, with caching to avoid re-downloads.
"""
import re
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "video"


def _load_yt_dlp():
    """Lazy import yt-dlp with clear error message."""
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        raise ImportError(
            "yt-dlp is required for YouTube downloads.\n"
            "Install with: pip install yt-dlp"
        )


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL."""
    youtube_patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=',
        r'(https?://)?(www\.)?youtu\.be/',
        r'(https?://)?(www\.)?youtube\.com/shorts/',
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None


def download_youtube(
    url: str,
    cache_dir: Optional[Path] = None,
    audio_only: bool = False,
    quiet: bool = False,
) -> Tuple[Path, bool]:
    """
    Download YouTube video/audio with caching.

    Args:
        url: YouTube URL
        cache_dir: Directory to save downloaded files (default: video/)
        audio_only: If True, download audio only (smaller files)
        quiet: Suppress yt-dlp output

    Returns:
        Tuple of (path to downloaded file, was_cached)
    """
    yt_dlp = _load_yt_dlp()

    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)

    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    for ext in ['.mp4', '.webm', '.mkv', '.m4a', '.mp3']:
        cached = cache_dir / f"{video_id}{ext}"
        if cached.exists():
            return cached, True

    output_template = str(cache_dir / f"{video_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'quiet': quiet,
        'no_warnings': quiet,
    }

    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if audio_only:
            downloaded = cache_dir / f"{video_id}.mp3"
        else:
            ext = info.get('ext', 'mp4')
            downloaded = cache_dir / f"{video_id}.{ext}"

    for ext in ['.mp4', '.webm', '.mkv', '.m4a', '.mp3']:
        possible = cache_dir / f"{video_id}{ext}"
        if possible.exists():
            return possible, False

    return downloaded, False


def get_video_title(url: str) -> Optional[str]:
    """Get video title without downloading."""
    yt_dlp = _load_yt_dlp()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('title')
