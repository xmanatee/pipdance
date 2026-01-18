"""
Choreography module for Piper arm.

Usage:
    from piper import create_arm
    from piper.choreography import load_choreography, compile_trajectory, run_trajectory

    choreo = load_choreography("poses.json", "schedule.md")
    trajectory = compile_trajectory(choreo)

    with create_arm() as arm:
        run_trajectory(arm, trajectory)

    # With interpolation for smooth motion:
    trajectory = compile_trajectory(choreo, interpolation="cubic", interval_ms=100)

CLI:
    python -m piper.choreography --poses poses.json --schedule he.md
    python -m piper.choreography --poses poses.json --schedule he.md --interpolation cubic
"""
from .script import (
    Choreography,
    Checkpoint,
    Pose,
    load_choreography,
    load_poses,
    parse_schedule,
    JOINT_ORDER,
    JOINT_MAX_SPEED_DEG,
)
from .trajectory import (
    Trajectory,
    Waypoint,
    compile_trajectory,
    compile_dual_trajectory,
    shift_trajectory_times,
)
from .interpolation import (
    EasingType,
    linear_interpolate,
    apply_easing,
    interpolate_joints,
    CubicSplineInterpolator,
    LinearInterpolator,
    create_interpolator,
)
from .runner import (
    run_trajectory,
    run_dual_trajectory,
)
from .groove import (
    GrooveConfig,
    DEFAULT_GROOVE_AMPLITUDES,
    NULL_GROOVE_AMPLITUDES,
    create_groove_config,
    compute_groove_offset,
    apply_groove_to_joints,
)
from .startup import (
    STARTUP_DURATION_S,
    STARTUP_SETTLE_S,
    STARTUP_J6_OFFSET,
    create_startup_waypoints,
    prepend_startup_sequence,
)

__all__ = [
    # Data structures
    "Choreography",
    "Checkpoint",
    "Pose",
    "Trajectory",
    "Waypoint",
    "EasingType",
    "GrooveConfig",
    # Loading/compiling
    "load_choreography",
    "load_poses",
    "parse_schedule",
    "compile_trajectory",
    "compile_dual_trajectory",
    "shift_trajectory_times",
    # Interpolation
    "linear_interpolate",
    "apply_easing",
    "interpolate_joints",
    "CubicSplineInterpolator",
    "LinearInterpolator",
    "create_interpolator",
    # Groove
    "create_groove_config",
    "compute_groove_offset",
    "apply_groove_to_joints",
    "DEFAULT_GROOVE_AMPLITUDES",
    "NULL_GROOVE_AMPLITUDES",
    # Execution
    "run_trajectory",
    "run_dual_trajectory",
    # Startup
    "STARTUP_DURATION_S",
    "STARTUP_SETTLE_S",
    "STARTUP_J6_OFFSET",
    "create_startup_waypoints",
    "prepend_startup_sequence",
    # Constants
    "JOINT_ORDER",
    "JOINT_MAX_SPEED_DEG",
]
