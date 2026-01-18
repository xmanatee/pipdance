#!/usr/bin/env python3
"""
CLI entry point for audio analysis.

Local files:
    python -m piper.audio video/la_la_land.mp4

YouTube URLs (auto-downloads to video/):
    python -m piper.audio "https://www.youtube.com/watch?v=VIDEO_ID"
    python -m piper.audio "https://youtu.be/VIDEO_ID"

Output formats:
    python -m piper.audio video.mp4 --format json
    python -m piper.audio video.mp4 --format template --output schedule.md

Visualization:
    python -m piper.audio video.mp4 --visualize

Configuration:
    python -m piper.audio video.mp4 --min-gap 2.0 --threshold 90

Audio-only download (faster, smaller):
    python -m piper.audio "https://youtu.be/VIDEO_ID" --audio-only
"""
import argparse
import sys
from pathlib import Path

from .analysis import analyze_audio, AnalysisConfig
from .formats import format_summary, to_json, to_schedule_template


def main():
    parser = argparse.ArgumentParser(
        description="Analyze audio/video for choreography timing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "input",
        help="Path to audio/video file or YouTube URL",
    )

    parser.add_argument(
        "--format",
        choices=["summary", "json", "template"],
        default="summary",
        help="Output format (default: summary)",
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "--min-gap",
        type=float,
        default=1.5,
        metavar="SECONDS",
        help="Minimum gap between change points in seconds (default: 1.5)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=95.0,
        metavar="PERCENTILE",
        help="Percentile threshold for change detection (default: 95)",
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Show visualization plot (requires matplotlib)",
    )

    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="For YouTube: download audio only (faster, smaller files)",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory to cache downloaded videos (default: video/)",
    )

    args = parser.parse_args()

    input_path = resolve_input(args.input, args.cache_dir, args.audio_only)

    config = AnalysisConfig(
        min_gap_s=args.min_gap,
        percentile_threshold=args.threshold,
    )

    try:
        print(f"[Audio] Analyzing {input_path.name}...", file=sys.stderr)
        analysis = analyze_audio(str(input_path), config)
        print(f"[Audio] Found BPM: {analysis.bpm}, {len(analysis.timestamps)} change points", file=sys.stderr)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing audio: {e}", file=sys.stderr)
        sys.exit(1)

    formatters = {
        "summary": format_summary,
        "json": to_json,
        "template": to_schedule_template,
    }
    output = formatters[args.format](analysis)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output)
        print(f"[Audio] Written to {output_path}", file=sys.stderr)
    else:
        print(output)

    if args.visualize:
        visualize(str(input_path), analysis, config)


def resolve_input(input_str: str, cache_dir: Path | None, audio_only: bool) -> Path:
    """Resolve input to a local file path, downloading if needed."""
    from .downloader import is_youtube_url, download_youtube, DEFAULT_CACHE_DIR

    if is_youtube_url(input_str):
        if cache_dir is None:
            cache_dir = DEFAULT_CACHE_DIR

        try:
            print("[YouTube] Checking cache...", file=sys.stderr)
            path, was_cached = download_youtube(
                input_str,
                cache_dir=cache_dir,
                audio_only=audio_only,
                quiet=False,
            )
            if was_cached:
                print(f"[YouTube] Using cached: {path.name}", file=sys.stderr)
            else:
                print(f"[YouTube] Downloaded: {path.name}", file=sys.stderr)
            return path
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error downloading video: {e}", file=sys.stderr)
            sys.exit(1)

    input_path = Path(input_str)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    return input_path


def visualize(path: str, analysis, config: AnalysisConfig):
    """Show visualization plot."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Error: matplotlib is required for visualization.", file=sys.stderr)
        print("Install with: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    try:
        import librosa
        import numpy as np
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    y, sr = librosa.load(path)

    centroid = librosa.feature.spectral_centroid(
        y=y, sr=sr, hop_length=config.hop_length
    )[0]
    times = librosa.frames_to_time(
        range(len(centroid)), sr=sr, hop_length=config.hop_length
    )

    delta = np.abs(np.diff(centroid))
    delta_times = times[:-1]
    threshold = np.percentile(delta, config.percentile_threshold)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    axes[0].plot(np.linspace(0, len(y) / sr, len(y)), y, alpha=0.7)
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title(f"Audio Analysis: {Path(path).name} (BPM: {analysis.bpm})")
    for ts in analysis.timestamps:
        axes[0].axvline(ts, color="red", alpha=0.5, linestyle="--")

    axes[1].plot(times, centroid)
    axes[1].set_ylabel("Spectral Centroid (Hz)")
    for ts in analysis.timestamps:
        axes[1].axvline(ts, color="red", alpha=0.5, linestyle="--")

    axes[2].plot(delta_times, delta)
    axes[2].axhline(threshold, color="orange", linestyle="--", label=f"{config.percentile_threshold}th percentile")
    axes[2].set_ylabel("Centroid Delta")
    axes[2].set_xlabel("Time (s)")
    axes[2].legend()
    for ts in analysis.timestamps:
        axes[2].axvline(ts, color="red", alpha=0.5, linestyle="--")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
