"""
Choreography execution - runs choreography on Piper arms using the adapter pattern.
"""
from __future__ import annotations

import math
import time
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

    for cp in checkpoints:
        pose = poses[cp.pose_name]
        joints_rad = [math.radians(d) for d in pose.joints_deg]

        elapsed = time.time() - start_time
        wait_until = cp.time_s - elapsed

        if wait_until > 0:
            if verbose:
                print(f"[{cp.time_s:6.1f}s] Waiting {wait_until:.1f}s...")
            arm.wait(wait_until)

        if verbose:
            print(f"[{cp.time_s:6.1f}s] -> {cp.pose_name}")

        if not dry_run:
            arm.move_joints(joints_rad, wait=0)

    if verbose:
        total = time.time() - start_time
        print(f"[Choreography] Completed in {total:.1f}s")


def run_dual_choreography(
    arms: Dict[str, PiperArmBase],
    choreographies: Dict[str, Choreography],
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Run dual arm choreography using merged timeline.

    Works with both hardware and simulation adapters. Events from all
    choreographies are merged and executed in time order, using the
    adapter's wait() method between events.

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

    events = []
    for label, choreo in choreographies.items():
        poses = choreo.poses
        for cp in choreo.checkpoints:
            pose = poses[cp.pose_name]
            joints_rad = [math.radians(d) for d in pose.joints_deg]
            events.append((cp.time_s, label, cp.pose_name, joints_rad))

    events.sort(key=lambda e: e[0])

    if not events:
        if verbose:
            print("[Choreography] No events to execute")
        return

    if verbose:
        for label, choreo in choreographies.items():
            if choreo.warnings:
                print(f"[{label}] Warnings:")
                for w in choreo.warnings:
                    print(f"  - {w}")

    first_arm = next(iter(arms.values()))
    start_time = time.time()

    for time_s, label, pose_name, joints_rad in events:
        elapsed = time.time() - start_time
        wait_time = time_s - elapsed

        if wait_time > 0:
            if verbose:
                print(f"[{time_s:6.1f}s] Waiting {wait_time:.1f}s...")
            first_arm.wait(wait_time)

        if verbose:
            print(f"[{time_s:6.1f}s] [{label}] -> {pose_name}")

        if not dry_run:
            arms[label].move_joints(joints_rad, wait=0)

    if verbose:
        total = time.time() - start_time
        print(f"[Choreography] Completed in {total:.1f}s")


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
