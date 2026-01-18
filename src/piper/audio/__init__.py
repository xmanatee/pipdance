"""
Audio analysis module for choreography timing.

Usage:
    from piper.audio import analyze_audio, AudioAnalysis

    analysis = analyze_audio("video.mp4")
    print(f"BPM: {analysis.bpm}")
    print(f"Change points: {analysis.timestamps}")

YouTube download:
    from piper.audio import download_youtube, is_youtube_url

    if is_youtube_url(url):
        path, cached = download_youtube(url)
        analysis = analyze_audio(str(path))

CLI:
    python -m piper.audio video.mp4
    python -m piper.audio "https://youtu.be/VIDEO_ID"
    python -m piper.audio video.mp4 --format template --output schedule.md
"""
from .analysis import (
    AudioAnalysis,
    AnalysisConfig,
    analyze_audio,
    estimate_bpm,
    detect_change_points,
    get_beat_times,
)
from .formats import (
    format_summary,
    to_json,
    to_schedule_template,
    format_timestamp,
)
from .downloader import (
    download_youtube,
    is_youtube_url,
    extract_video_id,
    get_video_title,
)

__all__ = [
    "AudioAnalysis",
    "AnalysisConfig",
    "analyze_audio",
    "estimate_bpm",
    "detect_change_points",
    "get_beat_times",
    "format_summary",
    "to_json",
    "to_schedule_template",
    "format_timestamp",
    "download_youtube",
    "is_youtube_url",
    "extract_video_id",
    "get_video_title",
]
