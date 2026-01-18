"""
Choreography module for Piper arm.

Usage:
    from piper import create_arm
    from piper.choreography import load_choreography, run_choreography

    choreo = load_choreography("poses.json", "schedule.md")

    with create_arm() as arm:
        run_choreography(arm, choreo)

CLI:
    python -m piper.choreography --poses poses.json --schedule he.md
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
from .runner import (
    run_choreography,
    run_dual_choreography,
    load_and_run,
)

__all__ = [
    # Data structures
    "Choreography",
    "Checkpoint",
    "Pose",
    # Loading functions
    "load_choreography",
    "load_poses",
    "parse_schedule",
    # Execution functions
    "run_choreography",
    "run_dual_choreography",
    "load_and_run",
    # Constants
    "JOINT_ORDER",
    "JOINT_MAX_SPEED_DEG",
]
