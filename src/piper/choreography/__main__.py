#!/usr/bin/env python3
"""
CLI entry point for running choreography scripts.

Single arm:
    python -m piper.choreography --poses poses.json --schedule he.md

Dual arm:
    python -m piper.choreography --poses poses.json \\
        --he he.md --she she.md --he-can can0 --she-can can1

Simulation (no hardware required):
    python -m piper.choreography --poses poses.json --schedule he.md --simulation
    python -m piper.choreography --poses poses.json --schedule he.md --simulation --no-viewer

Dry run (validate without moving):
    python -m piper.choreography --poses poses.json --schedule he.md --dry-run
"""
import argparse
import sys
from pathlib import Path

from . import load_choreography, run_choreography, run_choreography_parallel


def main():
    parser = argparse.ArgumentParser(
        description="Run choreography on Piper arm(s)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--poses",
        required=True,
        help="Path to poses JSON file",
    )

    # Single arm mode
    parser.add_argument(
        "--schedule",
        help="Path to schedule markdown file (single arm mode)",
    )
    parser.add_argument(
        "--can",
        default="can0",
        help="CAN interface for single arm (default: can0)",
    )

    # Dual arm mode
    parser.add_argument(
        "--he",
        help="Schedule file for 'he' arm (dual arm mode)",
    )
    parser.add_argument(
        "--she",
        help="Schedule file for 'she' arm (dual arm mode)",
    )
    parser.add_argument(
        "--he-can",
        default="can0",
        help="CAN interface for 'he' arm (default: can0)",
    )
    parser.add_argument(
        "--she-can",
        default="can1",
        help="CAN interface for 'she' arm (default: can1)",
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print without moving arm",
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in Genesis simulation instead of real hardware",
    )
    parser.add_argument(
        "--no-viewer",
        action="store_true",
        help="Run simulation without visualization window",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )

    args = parser.parse_args()

    # Validate mode
    single_mode = args.schedule is not None
    dual_mode = args.he is not None or args.she is not None

    if single_mode and dual_mode:
        parser.error("Cannot use --schedule with --he/--she. Choose single or dual arm mode.")

    if not single_mode and not dual_mode:
        parser.error("Specify --schedule (single arm) or --he/--she (dual arm)")

    if dual_mode and (args.he is None or args.she is None):
        parser.error("Dual arm mode requires both --he and --she")

    verbose = not args.quiet
    poses_path = Path(args.poses)

    if not poses_path.exists():
        print(f"Error: Poses file not found: {poses_path}", file=sys.stderr)
        sys.exit(1)

    try:
        if single_mode:
            run_single(args, poses_path, verbose)
        else:
            run_dual(args, poses_path, verbose)
    except KeyboardInterrupt:
        print("\n[Choreography] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def run_single(args, poses_path: Path, verbose: bool):
    """Run single arm choreography."""
    schedule_path = Path(args.schedule)

    if not schedule_path.exists():
        print(f"Error: Schedule file not found: {schedule_path}", file=sys.stderr)
        sys.exit(1)

    choreo = load_choreography(poses_path, schedule_path)

    if verbose:
        print(f"[Choreography] Loaded {len(choreo.poses)} poses, {len(choreo.checkpoints)} checkpoints")
        if choreo.warnings:
            print("[Choreography] Warnings:")
            for w in choreo.warnings:
                print(f"  - {w}")

    if args.dry_run:
        print("\n[Dry Run] Schedule:")
        for cp in choreo.checkpoints:
            total_ms = int(cp.time_s * 1000)
            mins, rem = divmod(total_ms, 60000)
            secs, ms = divmod(rem, 1000)
            print(f"  {mins:02d}:{secs:02d}.{ms:03d} -> {cp.pose_name}")
        print("\n[Dry Run] Validation complete")
        return

    # Import here to avoid import errors when dry-running on Mac
    from .. import create_arm

    if args.simulation:
        show_viewer = not args.no_viewer
        print(f"[Choreography] Starting simulation (viewer={'on' if show_viewer else 'off'})...")
        with create_arm(adapter="simulation", show_viewer=show_viewer) as arm:
            run_choreography(arm, choreo, dry_run=False, verbose=verbose)
    else:
        print(f"[Choreography] Connecting to arm on {args.can}...")
        with create_arm(can_port=args.can) as arm:
            run_choreography(arm, choreo, dry_run=False, verbose=verbose)


def run_dual(args, poses_path: Path, verbose: bool):
    """Run dual arm choreography in parallel."""
    he_path = Path(args.he)
    she_path = Path(args.she)

    for name, path in [("he", he_path), ("she", she_path)]:
        if not path.exists():
            print(f"Error: {name} schedule file not found: {path}", file=sys.stderr)
            sys.exit(1)

    he_choreo = load_choreography(poses_path, he_path)
    she_choreo = load_choreography(poses_path, she_path)

    if verbose:
        print(f"[he]  Loaded {len(he_choreo.checkpoints)} checkpoints")
        print(f"[she] Loaded {len(she_choreo.checkpoints)} checkpoints")

    if args.dry_run:
        print("\n[Dry Run] 'he' schedule:")
        for cp in he_choreo.checkpoints:
            total_ms = int(cp.time_s * 1000)
            mins, rem = divmod(total_ms, 60000)
            secs, ms = divmod(rem, 1000)
            print(f"  {mins:02d}:{secs:02d}.{ms:03d} -> {cp.pose_name}")

        print("\n[Dry Run] 'she' schedule:")
        for cp in she_choreo.checkpoints:
            total_ms = int(cp.time_s * 1000)
            mins, rem = divmod(total_ms, 60000)
            secs, ms = divmod(rem, 1000)
            print(f"  {mins:02d}:{secs:02d}.{ms:03d} -> {cp.pose_name}")

        print("\n[Dry Run] Validation complete")
        return

    if args.simulation:
        print("Error: --simulation is not yet supported for dual arm mode", file=sys.stderr)
        sys.exit(1)

    # Import here to avoid import errors when dry-running on Mac
    from .. import create_arm

    print(f"[Choreography] Connecting to arms...")
    print(f"  he:  {args.he_can}")
    print(f"  she: {args.she_can}")

    # Note: For dual arms, we need to specify adapter type explicitly
    # since auto-detection might not work with multiple adapters
    with create_arm(adapter="standard", can_port=args.he_can) as he_arm:
        with create_arm(adapter="standard", can_port=args.she_can) as she_arm:
            run_choreography_parallel(
                arms={"he": he_arm, "she": she_arm},
                choreographies={"he": he_choreo, "she": she_choreo},
                dry_run=False,
                verbose=verbose,
            )


if __name__ == "__main__":
    main()
