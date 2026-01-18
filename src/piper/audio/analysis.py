"""
Audio analysis for choreography timing.

Provides BPM estimation and multi-feature change point detection
for creating synchronized dance schedules.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DetectionMode(Enum):
    """Detection mode for timestamp identification."""
    SPECTRAL = "spectral"      # Spectral centroid delta (brightness changes)
    ONSETS = "onsets"          # Note/attack detection (percussion, drums)
    BEATS = "beats"            # Beat positions only (rhythmic dance)
    ENSEMBLE = "ensemble"      # Multi-feature weighted combination
    COMBINED = "combined"      # Ensemble + beat-aligned


@dataclass
class AudioAnalysis:
    """Results of audio analysis."""
    source: str
    bpm: float
    duration_s: float
    sample_rate: int
    timestamps: List[float] = field(default_factory=list)
    detection_mode: str = "combined"
    beat_times: List[float] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for analysis."""
    min_gap_s: float = 1.5
    percentile_threshold: float = 95.0
    hop_length: int = 512
    mode: DetectionMode = DetectionMode.COMBINED
    snap_to_beats: bool = True
    beat_snap_tolerance_s: float = 0.15
    weight_spectral: float = 0.4
    weight_contrast: float = 0.3
    weight_onset: float = 0.3


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
    beat_times = get_beat_times(y, sr)

    if config.mode == DetectionMode.SPECTRAL:
        timestamps = detect_change_points(y, sr, config)
    elif config.mode == DetectionMode.ONSETS:
        timestamps = detect_onsets(y, sr, config)
    elif config.mode == DetectionMode.BEATS:
        timestamps = _filter_min_gap(beat_times, config.min_gap_s)
    elif config.mode == DetectionMode.ENSEMBLE:
        timestamps = detect_ensemble(y, sr, config)
    elif config.mode == DetectionMode.COMBINED:
        timestamps = detect_ensemble(y, sr, config)
        timestamps = snap_to_beats(timestamps, beat_times, config.beat_snap_tolerance_s)
    else:
        timestamps = detect_change_points(y, sr, config)

    if config.snap_to_beats and config.mode != DetectionMode.COMBINED:
        timestamps = snap_to_beats(timestamps, beat_times, config.beat_snap_tolerance_s)

    return AudioAnalysis(
        source=path,
        bpm=bpm,
        duration_s=duration_s,
        sample_rate=sr,
        timestamps=timestamps,
        detection_mode=config.mode.value,
        beat_times=beat_times,
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


def detect_onsets(y, sr: int, config: AnalysisConfig) -> List[float]:
    """
    Detect note onsets using librosa's onset detection.

    Best for percussion, drums, and sharp attacks.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate
        config: Analysis configuration

    Returns:
        List of onset timestamps in seconds
    """
    librosa = _load_librosa()

    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, hop_length=config.hop_length
    )
    times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=config.hop_length)
    return _filter_min_gap(times.tolist(), config.min_gap_s)


def detect_spectral_contrast_changes(y, sr: int, config: AnalysisConfig) -> List[float]:
    """
    Detect changes in spectral contrast.

    Captures timbral changes across frequency bands, useful for
    detecting transitions between different instruments or sections.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate
        config: Analysis configuration

    Returns:
        List of timestamps in seconds
    """
    librosa = _load_librosa()
    np = _load_numpy()

    contrast = librosa.feature.spectral_contrast(
        y=y, sr=sr, hop_length=config.hop_length
    )
    contrast_mean = np.mean(contrast, axis=0)
    delta = np.abs(np.diff(contrast_mean))
    threshold = np.percentile(delta, config.percentile_threshold)

    frames = np.where(delta > threshold)[0]
    times = librosa.frames_to_time(frames, sr=sr, hop_length=config.hop_length)
    return _filter_min_gap(times.tolist(), config.min_gap_s)


def detect_ensemble(y, sr: int, config: AnalysisConfig) -> List[float]:
    """
    Detect timestamps using weighted voting from multiple features.

    Combines spectral centroid, spectral contrast, and onset detection
    with configurable weights. A timestamp is selected if it appears
    in multiple detectors or has strong support from weighted voting.

    Args:
        y: Audio time series (numpy array)
        sr: Sample rate
        config: Analysis configuration

    Returns:
        List of timestamps in seconds
    """
    np = _load_numpy()

    spectral_times = detect_change_points(y, sr, config)
    contrast_times = detect_spectral_contrast_changes(y, sr, config)
    onset_times = detect_onsets(y, sr, config)

    all_times = set(spectral_times + contrast_times + onset_times)

    tolerance = config.min_gap_s / 2
    scored_times = []

    for t in sorted(all_times):
        score = 0.0
        if _has_nearby(t, spectral_times, tolerance):
            score += config.weight_spectral
        if _has_nearby(t, contrast_times, tolerance):
            score += config.weight_contrast
        if _has_nearby(t, onset_times, tolerance):
            score += config.weight_onset
        scored_times.append((t, score))

    threshold = max(config.weight_spectral, config.weight_contrast, config.weight_onset)
    selected = [t for t, score in scored_times if score >= threshold]

    return _filter_min_gap(selected, config.min_gap_s)


def _has_nearby(target: float, times: List[float], tolerance: float) -> bool:
    """Check if any time in the list is within tolerance of target."""
    for t in times:
        if abs(t - target) <= tolerance:
            return True
    return False


def snap_to_beats(
    times: List[float], beat_times: List[float], tolerance: float
) -> List[float]:
    """
    Snap timestamps to nearest beat if within tolerance.

    Args:
        times: List of timestamps to snap
        beat_times: List of beat timestamps
        tolerance: Maximum distance to snap (seconds)

    Returns:
        List of timestamps, snapped to beats where possible
    """
    if not beat_times:
        return times

    result = []
    for t in times:
        nearest_beat = min(beat_times, key=lambda b: abs(b - t))
        if abs(nearest_beat - t) <= tolerance:
            result.append(nearest_beat)
        else:
            result.append(t)
    return result
