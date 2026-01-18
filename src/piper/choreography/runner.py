"""
Trajectory execution - runs compiled trajectories on Piper arms.
"""
from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Dict, Optional

from .trajectory import Trajectory, Waypoint

if TYPE_CHECKING:
    from ..base import PiperArmBase


def run_trajectory(
    arm: PiperArmBase,
    trajectory: Trajectory,
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Execute a compiled trajectory on a single arm.

    Sends position commands at each waypoint time using high-resolution timing.

    Args:
        arm: Connected PiperArmBase instance
        trajectory: Compiled trajectory with waypoints
        dry_run: If True, print actions without moving arm
        verbose: Print status messages
    """
    waypoints = trajectory.waypoints

    if not waypoints:
        if verbose:
            print("[Trajectory] No waypoints to execute")
        return

    if verbose:
        if trajectory.interval_ms > 0:
            print(f"[Trajectory] Executing {len(waypoints)} waypoints over {trajectory.total_duration_s:.1f}s")
            print(f"[Trajectory] Interval: {trajectory.interval_ms}ms, Interpolation: {trajectory.interpolation}, Easing: {trajectory.easing.value}")
        else:
            print(f"[Trajectory] Executing {len(waypoints)} waypoints over {trajectory.total_duration_s:.1f}s")

    start_time = time.perf_counter()

    last_print_time = 0.0
    for wp in waypoints:
        elapsed = time.perf_counter() - start_time
        wait_time = wp.time_s - elapsed

        if not dry_run:
            joints_rad = [math.radians(d) for d in wp.joints_deg]
            arm.move_joints(joints_rad, wait=0)
            if wait_time > 0:
                arm.wait(wait_time)
        elif wait_time > 0:
            time.sleep(wait_time)

        if verbose and (wp.time_s - last_print_time >= 1.0 or wp == waypoints[-1]):
            actual_elapsed = time.perf_counter() - start_time
            print(f"[{wp.time_s:6.1f}s] Waypoint (elapsed: {actual_elapsed:.2f}s)")
            last_print_time = wp.time_s

    if verbose:
        total = time.perf_counter() - start_time
        print(f"[Trajectory] Completed in {total:.2f}s")


def run_dual_trajectory(
    arms: Dict[str, PiperArmBase],
    trajectories: Dict[str, Trajectory],
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    """
    Execute dual arm trajectories with synchronized timing.

    Both arms receive position commands at the same waypoint times
    for synchronized motion.

    Args:
        arms: Dict mapping label to connected arm
        trajectories: Dict mapping label to compiled trajectory
        dry_run: If True, print actions without moving arms
        verbose: Print status messages
    """
    if set(arms.keys()) != set(trajectories.keys()):
        raise ValueError(
            f"Arms and trajectories must have matching keys. "
            f"Arms: {set(arms.keys())}, Trajectories: {set(trajectories.keys())}"
        )

    total_waypoints = max(len(t.waypoints) for t in trajectories.values()) if trajectories else 0
    total_duration = max(t.total_duration_s for t in trajectories.values()) if trajectories else 0.0

    if total_waypoints == 0:
        if verbose:
            print("[Trajectory] No waypoints to execute")
        return

    first_arm = next(iter(arms.values()))

    if verbose:
        for label, traj in trajectories.items():
            print(f"[{label}] {len(traj.waypoints)} waypoints")
        print(f"[Trajectory] Duration: {total_duration:.1f}s")

    start_time = time.perf_counter()

    iterators = {
        label: iter(traj.waypoints)
        for label, traj in trajectories.items()
    }
    current_waypoints: Dict[str, Optional[Waypoint]] = {
        label: next(it, None)
        for label, it in iterators.items()
    }

    last_print_time = 0.0

    while any(wp is not None for wp in current_waypoints.values()):
        next_time = min(
            wp.time_s
            for wp in current_waypoints.values()
            if wp is not None
        )

        elapsed = time.perf_counter() - start_time
        wait_time = next_time - elapsed

        for label, wp in list(current_waypoints.items()):
            if wp is not None and abs(wp.time_s - next_time) < 0.001:
                if not dry_run:
                    joints_rad = [math.radians(d) for d in wp.joints_deg]
                    arms[label].move_joints(joints_rad, wait=0)
                current_waypoints[label] = next(iterators[label], None)

        if not dry_run and wait_time > 0:
            first_arm.wait(wait_time)
        elif dry_run and wait_time > 0:
            time.sleep(wait_time)

        if verbose and (next_time - last_print_time >= 1.0):
            actual_elapsed = time.perf_counter() - start_time
            print(f"[{next_time:6.1f}s] Sync point (elapsed: {actual_elapsed:.2f}s)")
            last_print_time = next_time

    if verbose:
        total = time.perf_counter() - start_time
        print(f"[Trajectory] Completed in {total:.2f}s")
