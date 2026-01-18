"""
Audio analysis module for choreography timing.

Usage:
    from piper.audio import analyze_audio, AudioAnalysis, AnalysisConfig, DetectionMode

    # Default (combined mode: ensemble + beat-aligned)
    analysis = analyze_audio("video.mp4")
    print(f"BPM: {analysis.bpm}")
    print(f"Timestamps: {analysis.timestamps}")

    # Spectral centroid detection only
    config = AnalysisConfig(mode=DetectionMode.SPECTRAL)
    analysis = analyze_audio("video.mp4", config)

    # Multi-feature ensemble without beat snapping
    config = AnalysisConfig(mode=DetectionMode.ENSEMBLE, snap_to_beats=False)
    analysis = analyze_audio("video.mp4", config)

YouTube download:
    from piper.audio import download_youtube, is_youtube_url

    if is_youtube_url(url):
        path, cached = download_youtube(url)
        analysis = analyze_audio(str(path))

CLI:
    python -m piper.audio video.mp4                    # Default: combined mode
    python -m piper.audio video.mp4 --mode spectral   # Spectral only
    python -m piper.audio video.mp4 --mode ensemble   # Ensemble (snaps by default)
    python -m piper.audio video.mp4 --format template --output schedule.md
"""
from .analysis import (
    AudioAnalysis,
    AnalysisConfig,
    DetectionMode,
    analyze_audio,
    estimate_bpm,
    detect_change_points,
    detect_onsets,
    detect_spectral_contrast_changes,
    detect_ensemble,
    snap_to_beats,
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
    "DetectionMode",
    "analyze_audio",
    "estimate_bpm",
    "detect_change_points",
    "detect_onsets",
    "detect_spectral_contrast_changes",
    "detect_ensemble",
    "snap_to_beats",
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
