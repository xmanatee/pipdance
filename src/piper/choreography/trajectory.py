"""
Trajectory compiler for choreography execution.

Compiles choreography checkpoints into waypoints for execution.
When interpolation is "none", waypoints are placed at checkpoint times.
When interpolation is "linear" or "cubic", waypoints are placed at fixed intervals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from .script import Choreography
from .interpolation import EasingType, create_interpolator


@dataclass
class Waypoint:
    """A single point in the trajectory timeline."""
    time_s: float
    joints_deg: List[float]


@dataclass
class Trajectory:
    """Compiled trajectory with waypoints."""
    waypoints: List[Waypoint]
    interval_ms: int
    interpolation: str
    easing: EasingType
    total_duration_s: float

    def __len__(self) -> int:
        return len(self.waypoints)


def compile_trajectory(
    choreography: Choreography,
    *,
    interval_ms: int = 100,
    interpolation: str = "none",
    easing: str = "none",
) -> Trajectory:
    """
    Compile choreography into a trajectory.

    Args:
        choreography: Loaded choreography with poses and checkpoints
        interval_ms: Time between waypoints (only used when interpolation != "none")
        interpolation: "none", "linear", or "cubic"
        easing: "none", "ease_in", "ease_out", "ease_in_out"

    Returns:
        Trajectory with waypoints
    """
    if not choreography.checkpoints:
        return Trajectory(
            waypoints=[],
            interval_ms=0,
            interpolation=interpolation,
            easing=EasingType(easing),
            total_duration_s=0.0,
        )

    easing_type = EasingType(easing)

    times: List[float] = []
    positions: List[List[float]] = []
    for cp in choreography.checkpoints:
        pose = choreography.poses[cp.pose_name]
        times.append(cp.time_s)
        positions.append(pose.joints_deg.copy())

    start_time = times[0]
    end_time = times[-1]

    if interpolation == "none":
        waypoints = [
            Waypoint(time_s=t, joints_deg=pos.copy())
            for t, pos in zip(times, positions)
        ]
        return Trajectory(
            waypoints=waypoints,
            interval_ms=0,
            interpolation=interpolation,
            easing=easing_type,
            total_duration_s=end_time,
        )

    interpolator = create_interpolator(times, positions, interpolation)
    interval_s = interval_ms / 1000.0

    waypoints: List[Waypoint] = []
    current_time = start_time
    while current_time <= end_time:
        joints = interpolator.interpolate(current_time, easing_type)
        waypoints.append(Waypoint(time_s=current_time, joints_deg=joints))
        current_time += interval_s

    if waypoints and abs(waypoints[-1].time_s - end_time) > 0.001:
        joints = interpolator.interpolate(end_time, easing_type)
        waypoints.append(Waypoint(time_s=end_time, joints_deg=joints))

    return Trajectory(
        waypoints=waypoints,
        interval_ms=interval_ms,
        interpolation=interpolation,
        easing=easing_type,
        total_duration_s=end_time,
    )


def compile_dual_trajectory(
    choreographies: Dict[str, Choreography],
    *,
    interval_ms: int = 100,
    interpolation: str = "none",
    easing: str = "none",
) -> Dict[str, Trajectory]:
    """
    Compile dual arm choreographies into synchronized trajectories.

    Args:
        choreographies: Dict mapping label to choreography (e.g., {"he": ..., "she": ...})
        interval_ms: Time between waypoints (only used when interpolation != "none")
        interpolation: "none", "linear", or "cubic"
        easing: Easing type

    Returns:
        Dict mapping label to compiled trajectory
    """
    easing_type = EasingType(easing)

    if interpolation == "none":
        return {
            label: compile_trajectory(choreo, interpolation="none", easing=easing)
            for label, choreo in choreographies.items()
        }

    # For interpolation modes, use global time range for synchronization
    all_times = [
        cp.time_s
        for choreo in choreographies.values()
        for cp in choreo.checkpoints
    ]

    if not all_times:
        return {
            label: Trajectory(
                waypoints=[],
                interval_ms=interval_ms,
                interpolation=interpolation,
                easing=easing_type,
                total_duration_s=0.0,
            )
            for label in choreographies
        }

    global_start = min(all_times)
    global_end = max(all_times)
    interval_s = interval_ms / 1000.0

    result: Dict[str, Trajectory] = {}
    for label, choreo in choreographies.items():
        if not choreo.checkpoints:
            result[label] = Trajectory(
                waypoints=[],
                interval_ms=interval_ms,
                interpolation=interpolation,
                easing=easing_type,
                total_duration_s=0.0,
            )
            continue

        times = [cp.time_s for cp in choreo.checkpoints]
        positions = [choreo.poses[cp.pose_name].joints_deg.copy() for cp in choreo.checkpoints]
        interpolator = create_interpolator(times, positions, interpolation)

        waypoints: List[Waypoint] = []
        current_time = global_start
        while current_time <= global_end:
            clamped_time = max(times[0], min(times[-1], current_time))
            joints = interpolator.interpolate(clamped_time, easing_type)
            waypoints.append(Waypoint(time_s=current_time, joints_deg=joints))
            current_time += interval_s

        if waypoints and abs(waypoints[-1].time_s - global_end) > 0.001:
            clamped_time = max(times[0], min(times[-1], global_end))
            joints = interpolator.interpolate(clamped_time, easing_type)
            waypoints.append(Waypoint(time_s=global_end, joints_deg=joints))

        result[label] = Trajectory(
            waypoints=waypoints,
            interval_ms=interval_ms,
            interpolation=interpolation,
            easing=easing_type,
            total_duration_s=global_end,
        )

    return result
