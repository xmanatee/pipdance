"""Startup sequence - gripper wiggle to signal choreography start."""
from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .trajectory import Trajectory, Waypoint

STARTUP_DURATION_S = 7.0
STARTUP_SETTLE_S = 3.0  # time for arm to settle into initial position
STARTUP_J6_OFFSET = 60.0  # degrees relative to starting position
J6_INDEX = 5  # J6 is 6th joint (0-indexed)


def create_startup_waypoints(
    starting_joints: List[float],
    interval_ms: int,
) -> List["Waypoint"]:
    """
    Create waypoints for startup sequence.

    Sequence:
    - t=0-3: arm settles into starting position
    - t=4: J6 turns left (+60°)
    - t=5: J6 returns to center
    - t=6: J6 turns right (-60°)
    - t=7: J6 returns to center (GO!)

    Args:
        starting_joints: The starting joint positions (6 values in degrees)
        interval_ms: Time between waypoints in milliseconds (0 for checkpoint mode)

    Returns:
        List of waypoints for the startup sequence
    """
    from .trajectory import Waypoint

    start_j6 = starting_joints[J6_INDEX]

    key_times = [0.0, STARTUP_SETTLE_S, 4.0, 5.0, 6.0, 7.0]
    key_j6_positions = [
        start_j6,                      # t=0: start
        start_j6,                      # settled
        start_j6 + STARTUP_J6_OFFSET,  # t=4: left
        start_j6,                      # t=5: center
        start_j6 - STARTUP_J6_OFFSET,  # t=6: right
        start_j6,                      # t=7: center (GO!)
    ]

    if interval_ms <= 0:
        waypoints = []
        for t, j6 in zip(key_times, key_j6_positions):
            joints = starting_joints.copy()
            joints[J6_INDEX] = j6
            waypoints.append(Waypoint(time_s=t, joints_deg=joints))
        return waypoints

    from .interpolation import create_interpolator, EasingType

    positions = []
    for j6 in key_j6_positions:
        joints = starting_joints.copy()
        joints[J6_INDEX] = j6
        positions.append(joints)

    interpolator = create_interpolator(key_times, positions, "linear")
    interval_s = interval_ms / 1000.0

    waypoints: List[Waypoint] = []
    current_time = 0.0
    while current_time < STARTUP_DURATION_S:
        joints = interpolator.interpolate(current_time, EasingType.NONE)
        waypoints.append(Waypoint(time_s=current_time, joints_deg=joints))
        current_time += interval_s

    final_joints = starting_joints.copy()
    if not waypoints or abs(waypoints[-1].time_s - STARTUP_DURATION_S) > 0.001:
        waypoints.append(Waypoint(time_s=STARTUP_DURATION_S, joints_deg=final_joints))

    return waypoints


def prepend_startup_sequence(
    trajectory: "Trajectory",
    starting_joints: List[float],
) -> "Trajectory":
    """
    Prepend startup sequence to trajectory, shifting all times by STARTUP_DURATION_S.

    Args:
        trajectory: The original trajectory
        starting_joints: The starting joint positions for the startup sequence

    Returns:
        New trajectory with startup sequence prepended
    """
    from .trajectory import Trajectory, shift_trajectory_times

    shifted = shift_trajectory_times(trajectory, STARTUP_DURATION_S)
    startup_waypoints = create_startup_waypoints(starting_joints, trajectory.interval_ms)

    combined_waypoints = startup_waypoints + shifted.waypoints

    return Trajectory(
        waypoints=combined_waypoints,
        interval_ms=trajectory.interval_ms,
        interpolation=trajectory.interpolation,
        easing=trajectory.easing,
        total_duration_s=shifted.total_duration_s,
        groove_bpm=trajectory.groove_bpm,
    )
