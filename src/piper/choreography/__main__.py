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
    python -m piper.choreography --poses poses.json \\
        --he he.md --she she.md --simulation

Dry run (validate without moving):
    python -m piper.choreography --poses poses.json --schedule he.md --dry-run
"""
import argparse
import sys
from pathlib import Path

from . import load_choreography
from .script import Checkpoint
from .trajectory import compile_trajectory, compile_dual_trajectory
from .runner import run_trajectory, run_dual_trajectory
from .startup import prepend_startup_sequence, STARTUP_DURATION_S, STARTUP_J6_OFFSET


def format_timestamp(cp: Checkpoint) -> str:
    """Format checkpoint time as MM:SS.mmm."""
    total_ms = int(cp.time_s * 1000)
    mins, rem = divmod(total_ms, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{mins:02d}:{secs:02d}.{ms:03d}"


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
    parser.add_argument(
        "--startup",
        action="store_true",
        help="Enable 7-second startup sequence (gripper wiggle) before choreography",
    )

    # Trajectory options
    parser.add_argument(
        "--interpolation",
        choices=["none", "linear", "cubic"],
        default="none",
        help="Interpolation: none (checkpoints only), linear, cubic (default: none)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=100,
        metavar="MS",
        help="Waypoint interval in milliseconds for interpolated modes (default: 100)",
    )
    parser.add_argument(
        "--easing",
        choices=["none", "ease_in", "ease_out", "ease_in_out"],
        default="none",
        help="Easing function for interpolated modes (default: none)",
    )

    args = parser.parse_args()

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
        if choreo.bpm:
            groove_info = f", phase={choreo.groove_phase}s" if choreo.groove_phase else ""
            print(f"[Choreography] BPM: {choreo.bpm}{groove_info}")
        if choreo.warnings:
            print("[Choreography] Warnings:")
            for w in choreo.warnings:
                print(f"  - {w}")

    # Compile to trajectory (groove auto-applied when BPM is set)
    trajectory = compile_trajectory(
        choreo,
        interval_ms=args.interval,
        interpolation=args.interpolation,
        easing=args.easing,
    )

    startup_duration = 0.0
    if args.startup:
        first_pose = choreo.poses[choreo.checkpoints[0].pose_name]
        trajectory = prepend_startup_sequence(trajectory, first_pose.joints_deg)
        startup_duration = STARTUP_DURATION_S
        if verbose:
            print(f"[Startup] Enabled ({STARTUP_DURATION_S:.0f}s gripper wiggle)")

    if verbose:
        if args.interpolation == "none":
            print(f"[Trajectory] {len(trajectory)} waypoints (checkpoint mode)")
        else:
            print(f"[Trajectory] {len(trajectory)} waypoints at {args.interval}ms intervals ({args.interpolation})")

    if args.dry_run:
        if args.startup:
            print("\n[Dry Run] Startup sequence:")
            print(f"  00:00.000 -> (starting pose)")
            print(f"  00:03.000 -> (settled)")
            print(f"  00:04.000 -> J6 +{int(STARTUP_J6_OFFSET)}° (left)")
            print(f"  00:05.000 -> J6 (center)")
            print(f"  00:06.000 -> J6 -{int(STARTUP_J6_OFFSET)}° (right)")
            print(f"  00:07.000 -> J6 (center) - GO!")
        print("\n[Dry Run] Schedule:")
        for cp in choreo.checkpoints:
            groove_suffix = f" groove-x{cp.groove_amplitude}" if cp.groove_amplitude != 1.0 else ""
            print(f"  {format_timestamp(cp)} -> {cp.pose_name}{groove_suffix}")
        print(f"\n[Dry Run] Would execute {len(trajectory)} waypoints")
        print(f"  Interpolation: {args.interpolation}")
        if args.interpolation != "none":
            print(f"  Interval: {args.interval}ms")
            print(f"  Easing: {args.easing}")
        if choreo.bpm:
            phase_info = f", phase={choreo.groove_phase}s" if choreo.groove_phase else ""
            print(f"  Groove: {choreo.bpm} BPM{phase_info}")
        if args.startup:
            print(f"  Startup: {STARTUP_DURATION_S:.0f}s")
        print("\n[Dry Run] Validation complete")
        return

    # Import here to avoid import errors when dry-running on Mac
    from .. import create_arm

    if args.simulation:
        show_viewer = not args.no_viewer
        print(f"[Choreography] Starting simulation (viewer={'on' if show_viewer else 'off'})...")
        with create_arm(adapter="simulation", show_viewer=show_viewer) as arm:
            run_trajectory(arm, trajectory, dry_run=False, verbose=verbose, startup_duration_s=startup_duration)
    else:
        print(f"[Choreography] Connecting to arm on {args.can}...")
        with create_arm(can_port=args.can) as arm:
            run_trajectory(arm, trajectory, dry_run=False, verbose=verbose, startup_duration_s=startup_duration)


def run_dual(args, poses_path: Path, verbose: bool):
    """Run dual arm choreography using merged timeline."""
    he_path = Path(args.he)
    she_path = Path(args.she)

    for name, path in [("he", he_path), ("she", she_path)]:
        if not path.exists():
            print(f"Error: {name} schedule file not found: {path}", file=sys.stderr)
            sys.exit(1)

    he_choreo = load_choreography(poses_path, he_path)
    she_choreo = load_choreography(poses_path, she_path)
    choreographies = {"he": he_choreo, "she": she_choreo}

    if verbose:
        for label, choreo in choreographies.items():
            bpm_info = f" (BPM: {choreo.bpm})" if choreo.bpm else ""
            print(f"[{label}]  Loaded {len(choreo.checkpoints)} checkpoints{bpm_info}")

    # Compile trajectories (groove auto-applied when BPM is set)
    trajectories = compile_dual_trajectory(
        choreographies,
        interval_ms=args.interval,
        interpolation=args.interpolation,
        easing=args.easing,
    )

    startup_duration = 0.0
    if args.startup:
        for label, choreo in choreographies.items():
            first_pose = choreo.poses[choreo.checkpoints[0].pose_name]
            trajectories[label] = prepend_startup_sequence(trajectories[label], first_pose.joints_deg)
        startup_duration = STARTUP_DURATION_S
        if verbose:
            print(f"[Startup] Enabled ({STARTUP_DURATION_S:.0f}s gripper wiggle)")

    if verbose:
        for label, traj in trajectories.items():
            if args.interpolation == "none":
                print(f"[{label}] {len(traj)} waypoints (checkpoint mode)")
            else:
                print(f"[{label}] {len(traj)} waypoints at {args.interval}ms intervals ({args.interpolation})")

    if args.dry_run:
        if args.startup:
            print("\n[Dry Run] Startup sequence (both arms):")
            print(f"  00:00.000 -> (starting pose)")
            print(f"  00:03.000 -> (settled)")
            print(f"  00:04.000 -> J6 +{int(STARTUP_J6_OFFSET)}° (left)")
            print(f"  00:05.000 -> J6 (center)")
            print(f"  00:06.000 -> J6 -{int(STARTUP_J6_OFFSET)}° (right)")
            print(f"  00:07.000 -> J6 (center) - GO!")

        print("\n[Dry Run] 'he' schedule:")
        for cp in he_choreo.checkpoints:
            groove_suffix = f" groove-x{cp.groove_amplitude}" if cp.groove_amplitude != 1.0 else ""
            print(f"  {format_timestamp(cp)} -> {cp.pose_name}{groove_suffix}")

        print("\n[Dry Run] 'she' schedule:")
        for cp in she_choreo.checkpoints:
            groove_suffix = f" groove-x{cp.groove_amplitude}" if cp.groove_amplitude != 1.0 else ""
            print(f"  {format_timestamp(cp)} -> {cp.pose_name}{groove_suffix}")

        print(f"\n[Dry Run] Would execute trajectories:")
        for label, traj in trajectories.items():
            choreo = choreographies[label]
            groove_status = ""
            if traj.groove_bpm:
                phase_info = f", phase={choreo.groove_phase}s" if choreo.groove_phase else ""
                groove_status = f", groove={traj.groove_bpm} BPM{phase_info}"
            print(f"  [{label}] {len(traj)} waypoints{groove_status}")
        print(f"  Interpolation: {args.interpolation}")
        if args.interpolation != "none":
            print(f"  Interval: {args.interval}ms")
            print(f"  Easing: {args.easing}")
        if args.startup:
            print(f"  Startup: {STARTUP_DURATION_S:.0f}s")

        print("\n[Dry Run] Validation complete")
        return

    if args.simulation:
        from ..simulation.dual import create_dual_simulation_arms

        show_viewer = not args.no_viewer
        print(f"[Choreography] Starting dual simulation (viewer={'on' if show_viewer else 'off'})...")

        he_arm, she_arm = create_dual_simulation_arms(show_viewer=show_viewer, verbose=verbose)
        with he_arm, she_arm:
            arms = {"he": he_arm, "she": she_arm}
            run_dual_trajectory(arms, trajectories, verbose=verbose, startup_duration_s=startup_duration)
    else:
        from .. import create_arm

        print(f"[Choreography] Connecting to arms...")
        print(f"  he:  {args.he_can}")
        print(f"  she: {args.she_can}")

        with create_arm(adapter="standard", can_port=args.he_can) as he_arm:
            with create_arm(adapter="standard", can_port=args.she_can) as she_arm:
                arms = {"he": he_arm, "she": she_arm}
                run_dual_trajectory(arms, trajectories, verbose=verbose, startup_duration_s=startup_duration)


if __name__ == "__main__":
    main()
