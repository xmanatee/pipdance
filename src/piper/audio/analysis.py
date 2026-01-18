"""
Audio analysis for choreography timing.

Provides BPM estimation and brightness-based change point detection
for creating synchronized dance schedules.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AudioAnalysis:
    """Results of audio analysis."""
    source: str
    bpm: float
    duration_s: float
    sample_rate: int
    timestamps: List[float] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for analysis."""
    min_gap_s: float = 1.5
    percentile_threshold: float = 95.0
    hop_length: int = 512


def _load_librosa():
    """Lazy import librosa with clear error message."""
    try:
        import librosa
        return librosa
    except ImportError:
        raise ImportError(
            "librosa is required for audio analysis.\n"
            "Install with: pip install librosa"
        )


def _load_numpy():
    """Lazy import numpy with clear error message."""
    try:
        import numpy as np
        return np
    except ImportError:
        raise ImportError(
            "numpy is required for audio analysis.\n"
            "Install with: pip install numpy"
        )


def analyze_audio(path: str, config: Optional[AnalysisConfig] = None) -> AudioAnalysis:
    """
    Analyze audio file for BPM and change points.

    Args:
        path: Path to audio or video file
        config: Analysis configuration (uses defaults if not provided)

    Returns:
        AudioAnalysis with BPM, duration, and suggested timestamps
    """
    librosa = _load_librosa()

    if config is None:
        config = AnalysisConfig()

    y, sr = librosa.load(path)
    duration_s = len(y) / sr

    bpm = estimate_bpm(y, sr)
    timestamps = detect_change_points(y, sr, config)

    return AudioAnalysis(
        source=path,
        bpm=bpm,
        duration_s=duration_s,
        sample_rate=sr,
        timestamps=timestamps,
    )


def estimate_bpm(y, sr: int) -> float:
    """
    Estimate tempo using librosa beat tracking.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate

    Returns:
        Estimated BPM (rounded to 1 decimal place)
    """
    librosa = _load_librosa()
    np = _load_numpy()

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0])
    return round(tempo, 1)


def detect_change_points(y, sr: int, config: AnalysisConfig) -> List[float]:
    """
    Detect brightness jump timestamps using spectral centroid delta.

    Identifies moments where the spectral brightness changes significantly,
    which often correspond to musical transitions suitable for pose changes.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate
        config: Analysis configuration

    Returns:
        List of timestamps in seconds
    """
    librosa = _load_librosa()
    np = _load_numpy()

    centroid = librosa.feature.spectral_centroid(
        y=y, sr=sr, hop_length=config.hop_length
    )[0]

    delta = np.abs(np.diff(centroid))
    threshold = np.percentile(delta, config.percentile_threshold)

    frames = np.where(delta > threshold)[0]
    times = librosa.frames_to_time(frames, sr=sr, hop_length=config.hop_length)

    filtered = _filter_min_gap(times.tolist(), config.min_gap_s)
    return filtered


def _filter_min_gap(times: List[float], min_gap_s: float) -> List[float]:
    """Filter timestamps to ensure minimum gap between consecutive points."""
    if not times:
        return []

    result = [times[0]]
    for t in times[1:]:
        if t - result[-1] >= min_gap_s:
            result.append(t)
    return result


def get_beat_times(y, sr: int) -> List[float]:
    """
    Get individual beat timestamps.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate

    Returns:
        List of beat timestamps in seconds
    """
    librosa = _load_librosa()

    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return beat_times.tolist()
