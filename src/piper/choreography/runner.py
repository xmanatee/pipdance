"""
Choreography execution - runs choreography on Piper arms using the adapter pattern.
"""
from __future__ import annotations

import math
import time
import threading
from typing import TYPE_CHECKING, Dict, Optional

from .script import Choreography, load_choreography

if TYPE_CHECKING:
    from ..base import PiperArmBase


def run_choreography(
    arm: PiperArmBase,
    choreography: Choreography,
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Run a choreography sequence on a single arm.

    The arm moves between checkpoints, arriving at each pose at the specified time.
    Uses blocking waits between movements.

    Args:
        arm: Connected PiperArmBase instance
        choreography: Loaded choreography with poses and checkpoints
        dry_run: If True, print actions without moving arm
        verbose: Print status messages
    """
    checkpoints = choreography.checkpoints
    poses = choreography.poses

    if not checkpoints:
        if verbose:
            print("[Choreography] No checkpoints to execute")
        return

    if verbose and choreography.warnings:
        print("[Choreography] Warnings:")
        for w in choreography.warnings:
            print(f"  - {w}")

    start_time = time.time()

    for i, cp in enumerate(checkpoints):
        pose = poses[cp.pose_name]
        joints_rad = [math.radians(d) for d in pose.joints_deg]

        # Calculate wait time until this checkpoint
        elapsed = time.time() - start_time
        wait_until = cp.time_s - elapsed

        if wait_until > 0:
            if verbose:
                print(f"[{cp.time_s:6.1f}s] Waiting {wait_until:.1f}s...")
            time.sleep(wait_until)

        if verbose:
            print(f"[{cp.time_s:6.1f}s] -> {cp.pose_name}")

        if not dry_run:
            arm.move_joints(joints_rad, wait=0)

    if verbose:
        total = time.time() - start_time
        print(f"[Choreography] Completed in {total:.1f}s")


def run_choreography_parallel(
    arms: Dict[str, PiperArmBase],
    choreographies: Dict[str, Choreography],
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Run multiple choreographies in parallel on multiple arms.

    Args:
        arms: Dict mapping label to connected arm (e.g., {"he": arm1, "she": arm2})
        choreographies: Dict mapping label to choreography
        dry_run: If True, print actions without moving arms
        verbose: Print status messages
    """
    if set(arms.keys()) != set(choreographies.keys()):
        raise ValueError(
            f"Arms and choreographies must have matching keys. "
            f"Arms: {set(arms.keys())}, Choreographies: {set(choreographies.keys())}"
        )

    threads = []
    errors: Dict[str, Exception] = {}

    def run_one(label: str):
        try:
            arm = arms[label]
            choreo = choreographies[label]

            if verbose:
                print(f"[{label}] Starting choreography ({len(choreo.checkpoints)} checkpoints)")

            run_choreography(
                arm,
                choreo,
                dry_run=dry_run,
                verbose=verbose,
            )
        except Exception as e:
            errors[label] = e

    for label in arms:
        t = threading.Thread(target=run_one, args=(label,), name=f"choreo-{label}")
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if errors:
        error_msgs = [f"{label}: {e}" for label, e in errors.items()]
        raise RuntimeError(f"Choreography errors:\n" + "\n".join(error_msgs))


def load_and_run(
    poses_path: str,
    schedule_path: str,
    arm: Optional[PiperArmBase] = None,
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Convenience function to load and run a choreography.

    If no arm is provided, auto-detects and connects.
    """
    from .. import create_arm

    choreography = load_choreography(poses_path, schedule_path)

    if arm is not None:
        run_choreography(arm, choreography, dry_run=dry_run, verbose=verbose)
    else:
        with create_arm() as arm:
            run_choreography(arm, choreography, dry_run=dry_run, verbose=verbose)
