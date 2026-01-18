"""
Trajectory execution - runs compiled trajectories on Piper arms.

Supports parallel command sending for improved dual-arm synchronization.
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .trajectory import Trajectory, Waypoint

if TYPE_CHECKING:
    from ..base import PiperArmBase


def run_trajectory(
    arm: PiperArmBase,
    trajectory: Trajectory,
    *,
    dry_run: bool = False,
    verbose: bool = True,
    startup_duration_s: float = 0.0,
) -> None:
    """
    Execute a compiled trajectory on a single arm.

    Sends position commands at each waypoint time using high-resolution timing.

    Args:
        arm: Connected PiperArmBase instance
        trajectory: Compiled trajectory with waypoints
        dry_run: If True, print actions without moving arm
        verbose: Print status messages
        startup_duration_s: If > 0, print countdown during startup phase
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
    countdown_printed = set()

    for wp in waypoints:
        elapsed = time.perf_counter() - start_time
        wait_time = wp.time_s - elapsed

        if not dry_run:
            joints_rad = [math.radians(d) for d in wp.joints_deg]
            arm.move_joints(joints_rad, wait=0)
            arm._send_gripper_command(wp.gripper)
            if wait_time > 0:
                arm.wait(wait_time)
        elif wait_time > 0:
            time.sleep(wait_time)

        if verbose and startup_duration_s > 0 and wp.time_s <= startup_duration_s:
            for countdown_val in range(int(startup_duration_s), 0, -1):
                threshold = startup_duration_s - countdown_val
                if wp.time_s >= threshold and countdown_val not in countdown_printed:
                    print(f"[Startup] {countdown_val}...")
                    countdown_printed.add(countdown_val)
            if wp.time_s >= startup_duration_s and 0 not in countdown_printed:
                print("[Startup] GO!")
                countdown_printed.add(0)

        in_startup = startup_duration_s > 0 and wp.time_s <= startup_duration_s
        if verbose and not in_startup and (wp.time_s - last_print_time >= 1.0 or wp == waypoints[-1]):
            actual_elapsed = time.perf_counter() - start_time
            print(f"[{wp.time_s:6.1f}s] Waypoint (elapsed: {actual_elapsed:.2f}s)")
            last_print_time = wp.time_s

    if verbose:
        total = time.perf_counter() - start_time
        print(f"[Trajectory] Completed in {total:.2f}s")


def _send_arm_commands(
    arm: PiperArmBase,
    joints_rad: List[float],
    gripper: float,
) -> None:
    """Send joint and gripper commands to a single arm (for threading)."""
    arm.move_joints(joints_rad, wait=0)
    arm._send_gripper_command(gripper)


def run_dual_trajectory(
    arms: Dict[str, PiperArmBase],
    trajectories: Dict[str, Trajectory],
    *,
    dry_run: bool = False,
    verbose: bool = True,
    startup_duration_s: float = 0.0,
    parallel: bool = True,
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
        startup_duration_s: If > 0, print countdown during startup phase
        parallel: If True, send commands to arms in parallel (improves sync ~30ms)
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
        if parallel:
            print("[Trajectory] Parallel command mode enabled")

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
    countdown_printed = set()

    executor = ThreadPoolExecutor(max_workers=len(arms)) if parallel and not dry_run else None

    try:
        while any(wp is not None for wp in current_waypoints.values()):
            next_time = min(
                wp.time_s
                for wp in current_waypoints.values()
                if wp is not None
            )

            elapsed = time.perf_counter() - start_time
            wait_time = next_time - elapsed

            pending_commands: List[Tuple[str, Waypoint]] = []
            for label, wp in list(current_waypoints.items()):
                if wp is not None and abs(wp.time_s - next_time) < 0.001:
                    pending_commands.append((label, wp))
                    current_waypoints[label] = next(iterators[label], None)

            if not dry_run and pending_commands:
                if parallel and executor:
                    futures = []
                    for label, wp in pending_commands:
                        joints_rad = [math.radians(d) for d in wp.joints_deg]
                        future = executor.submit(
                            _send_arm_commands,
                            arms[label],
                            joints_rad,
                            wp.gripper,
                        )
                        futures.append(future)
                    for future in futures:
                        future.result()
                else:
                    for label, wp in pending_commands:
                        joints_rad = [math.radians(d) for d in wp.joints_deg]
                        arms[label].move_joints(joints_rad, wait=0)
                        arms[label]._send_gripper_command(wp.gripper)

            if not dry_run and wait_time > 0:
                first_arm.wait(wait_time)
            elif dry_run and wait_time > 0:
                time.sleep(wait_time)

            if verbose and startup_duration_s > 0 and next_time <= startup_duration_s:
                for countdown_val in range(int(startup_duration_s), 0, -1):
                    threshold = startup_duration_s - countdown_val
                    if next_time >= threshold and countdown_val not in countdown_printed:
                        print(f"[Startup] {countdown_val}...")
                        countdown_printed.add(countdown_val)
                if next_time >= startup_duration_s and 0 not in countdown_printed:
                    print("[Startup] GO!")
                    countdown_printed.add(0)

            in_startup = startup_duration_s > 0 and next_time <= startup_duration_s
            if verbose and not in_startup and (next_time - last_print_time >= 1.0):
                actual_elapsed = time.perf_counter() - start_time
                print(f"[{next_time:6.1f}s] Sync point (elapsed: {actual_elapsed:.2f}s)")
                last_print_time = next_time

    finally:
        if executor:
            executor.shutdown(wait=False)

    if verbose:
        total = time.perf_counter() - start_time
        print(f"[Trajectory] Completed in {total:.2f}s")
