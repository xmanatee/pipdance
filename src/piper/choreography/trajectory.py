"""
Trajectory compiler for choreography execution.

Compiles choreography checkpoints into waypoints for execution.
When interpolation is "none", waypoints are placed at checkpoint times.
When interpolation is "linear" or "cubic", waypoints are placed at fixed intervals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional

from .script import Choreography, Checkpoint
from .interpolation import EasingType, create_interpolator
from .groove import apply_groove_to_joints, create_groove_config


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
    groove_bpm: Optional[float] = None

    def __len__(self) -> int:
        return len(self.waypoints)


def _interpolate_groove_amplitude(
    time_s: float,
    checkpoints: List[Checkpoint],
) -> float:
    """
    Interpolate groove amplitude for a given time between checkpoints.

    Uses linear interpolation between checkpoint groove amplitudes.
    """
    if not checkpoints:
        return 1.0

    # Before first checkpoint
    if time_s <= checkpoints[0].time_s:
        return checkpoints[0].groove_amplitude

    # After last checkpoint
    if time_s >= checkpoints[-1].time_s:
        return checkpoints[-1].groove_amplitude

    # Find surrounding checkpoints
    for i in range(len(checkpoints) - 1):
        if checkpoints[i].time_s <= time_s <= checkpoints[i + 1].time_s:
            t0 = checkpoints[i].time_s
            t1 = checkpoints[i + 1].time_s
            a0 = checkpoints[i].groove_amplitude
            a1 = checkpoints[i + 1].groove_amplitude

            if t1 == t0:
                return a0

            ratio = (time_s - t0) / (t1 - t0)
            return a0 + ratio * (a1 - a0)

    return 1.0


def compile_trajectory(
    choreography: Choreography,
    *,
    interval_ms: int = 100,
    interpolation: str = "none",
    easing: str = "none",
) -> Trajectory:
    """
    Compile choreography into a trajectory.

    Groove is automatically applied when BPM is specified in the choreography.
    Per-checkpoint groove amplitude comes from groove-x<number> suffix in schedule.

    Args:
        choreography: Loaded choreography with poses and checkpoints
        interval_ms: Time between waypoints (only used when interpolation != "none")
        interpolation: "none", "linear", or "cubic"
        easing: "none", "ease_in", "ease_out", "ease_in_out"

    Returns:
        Trajectory with waypoints
    """
    groove = create_groove_config(choreography.bpm, choreography.groove_phase)
    easing_type = EasingType(easing)

    if not choreography.checkpoints:
        return Trajectory(
            waypoints=[],
            interval_ms=0,
            interpolation=interpolation,
            easing=easing_type,
            total_duration_s=0.0,
            groove_bpm=choreography.bpm,
        )

    times = [cp.time_s for cp in choreography.checkpoints]
    positions = [choreography.poses[cp.pose_name].joints_deg.copy() for cp in choreography.checkpoints]
    end_time = times[-1]

    if interpolation == "none":
        waypoints = [
            Waypoint(
                time_s=cp.time_s,
                joints_deg=apply_groove_to_joints(pos, cp.time_s, groove, cp.groove_amplitude),
            )
            for cp, pos in zip(choreography.checkpoints, positions)
        ]
        return Trajectory(
            waypoints=waypoints,
            interval_ms=0,
            interpolation=interpolation,
            easing=easing_type,
            total_duration_s=end_time,
            groove_bpm=choreography.bpm,
        )

    interpolator = create_interpolator(times, positions, interpolation)
    interval_s = interval_ms / 1000.0

    waypoints: List[Waypoint] = []
    current_time = times[0]
    while current_time <= end_time:
        joints = interpolator.interpolate(current_time, easing_type)
        amp_scale = _interpolate_groove_amplitude(current_time, choreography.checkpoints)
        joints = apply_groove_to_joints(joints, current_time, groove, amp_scale)
        waypoints.append(Waypoint(time_s=current_time, joints_deg=joints))
        current_time += interval_s

    if waypoints and abs(waypoints[-1].time_s - end_time) > 0.001:
        joints = interpolator.interpolate(end_time, easing_type)
        amp_scale = _interpolate_groove_amplitude(end_time, choreography.checkpoints)
        joints = apply_groove_to_joints(joints, end_time, groove, amp_scale)
        waypoints.append(Waypoint(time_s=end_time, joints_deg=joints))

    return Trajectory(
        waypoints=waypoints,
        interval_ms=interval_ms,
        interpolation=interpolation,
        easing=easing_type,
        total_duration_s=end_time,
        groove_bpm=choreography.bpm,
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

    Groove is automatically applied when BPM is specified in each choreography.
    Per-checkpoint groove amplitude comes from groove-x<number> suffix in schedule.

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
    all_times = [cp.time_s for choreo in choreographies.values() for cp in choreo.checkpoints]

    if not all_times:
        return {
            label: Trajectory(
                waypoints=[],
                interval_ms=interval_ms,
                interpolation=interpolation,
                easing=easing_type,
                total_duration_s=0.0,
                groove_bpm=choreo.bpm,
            )
            for label, choreo in choreographies.items()
        }

    global_start = min(all_times)
    global_end = max(all_times)
    interval_s = interval_ms / 1000.0

    result: Dict[str, Trajectory] = {}
    for label, choreo in choreographies.items():
        groove = create_groove_config(choreo.bpm, choreo.groove_phase)

        if not choreo.checkpoints:
            result[label] = Trajectory(
                waypoints=[],
                interval_ms=interval_ms,
                interpolation=interpolation,
                easing=easing_type,
                total_duration_s=0.0,
                groove_bpm=choreo.bpm,
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
            amp_scale = _interpolate_groove_amplitude(clamped_time, choreo.checkpoints)
            joints = apply_groove_to_joints(joints, current_time, groove, amp_scale)
            waypoints.append(Waypoint(time_s=current_time, joints_deg=joints))
            current_time += interval_s

        if waypoints and abs(waypoints[-1].time_s - global_end) > 0.001:
            clamped_time = max(times[0], min(times[-1], global_end))
            joints = interpolator.interpolate(clamped_time, easing_type)
            amp_scale = _interpolate_groove_amplitude(clamped_time, choreo.checkpoints)
            joints = apply_groove_to_joints(joints, global_end, groove, amp_scale)
            waypoints.append(Waypoint(time_s=global_end, joints_deg=joints))

        result[label] = Trajectory(
            waypoints=waypoints,
            interval_ms=interval_ms,
            interpolation=interpolation,
            easing=easing_type,
            total_duration_s=global_end,
            groove_bpm=choreo.bpm,
        )

    return result


def shift_trajectory_times(trajectory: Trajectory, offset_s: float) -> Trajectory:
    """
    Shift all waypoint times by offset.

    Args:
        trajectory: The trajectory to shift
        offset_s: Time offset in seconds to add to all waypoints

    Returns:
        New trajectory with shifted times
    """
    shifted_waypoints = [
        Waypoint(time_s=wp.time_s + offset_s, joints_deg=wp.joints_deg.copy())
        for wp in trajectory.waypoints
    ]

    return Trajectory(
        waypoints=shifted_waypoints,
        interval_ms=trajectory.interval_ms,
        interpolation=trajectory.interpolation,
        easing=trajectory.easing,
        total_duration_s=trajectory.total_duration_s + offset_s,
        groove_bpm=trajectory.groove_bpm,
    )
