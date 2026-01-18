"""
Output formatters for audio analysis results.
"""
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analysis import AudioAnalysis


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS.mmm."""
    total_ms = int(seconds * 1000)
    mins, rem = divmod(total_ms, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{mins:02d}:{secs:02d}.{ms:03d}"


def format_duration(seconds: float) -> str:
    """Format duration as M:SS.mmm or MM:SS.mmm."""
    total_ms = int(seconds * 1000)
    mins, rem = divmod(total_ms, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{mins}:{secs:02d}.{ms:03d}"


def format_summary(analysis: "AudioAnalysis") -> str:
    """
    Human-readable console output.

    Args:
        analysis: AudioAnalysis results

    Returns:
        Formatted summary string
    """
    lines = [
        f"Audio Analysis: {analysis.source}",
        f"Duration: {format_duration(analysis.duration_s)}",
        f"BPM: {analysis.bpm}",
        f"Sample Rate: {analysis.sample_rate} Hz",
        f"Change points: {len(analysis.timestamps)}",
        "",
        "Timestamps:",
    ]

    for ts in analysis.timestamps:
        lines.append(f"  {format_timestamp(ts)}")

    return "\n".join(lines)


def to_json(analysis: "AudioAnalysis") -> str:
    """
    JSON export.

    Args:
        analysis: AudioAnalysis results

    Returns:
        JSON string
    """
    data = {
        "source": analysis.source,
        "bpm": analysis.bpm,
        "duration_s": round(analysis.duration_s, 3),
        "sample_rate": analysis.sample_rate,
        "timestamps": [round(t, 3) for t in analysis.timestamps],
    }
    return json.dumps(data, indent=2)


def to_schedule_template(analysis: "AudioAnalysis") -> str:
    """
    Markdown schedule template with POSE placeholders.

    Args:
        analysis: AudioAnalysis results

    Returns:
        Markdown schedule template string
    """
    lines = [
        "# Dance Schedule",
        f"# BPM: {int(analysis.bpm)}",
        "",
    ]

    for ts in analysis.timestamps:
        lines.append(f"{format_timestamp(ts)} - POSE")

    return "\n".join(lines)
