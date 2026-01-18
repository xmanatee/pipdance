"""
Groove modulation for choreography.

Adds rhythmic oscillations to joint positions based on BPM.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .script import JOINT_ORDER


# Default groove amplitudes in degrees per joint
DEFAULT_GROOVE_AMPLITUDES: Dict[str, float] = {
    "J1": 0.0,   # Base rotation - no groove
    "J2": 2.0,   # Shoulder - main bounce
    "J3": 1.5,   # Elbow - secondary
    "J4": 0.0,   # Forearm - no groove
    "J5": 1.0,   # Wrist - subtle
    "J6": 0.0,   # Gripper - no groove
}


@dataclass
class GrooveConfig:
    """Configuration for groove modulation."""
    bpm: float
    amplitudes_deg: Dict[str, float] = field(default_factory=lambda: DEFAULT_GROOVE_AMPLITUDES.copy())
    phase_offset_s: float = 0.0
    beat_multiplier: float = 1.0


def compute_groove_offset(
    time_s: float,
    bpm: float,
    amplitude_deg: float,
    phase_offset_s: float = 0.0,
    beat_multiplier: float = 1.0,
) -> float:
    """
    Compute groove offset for a single joint at a given time.

    Args:
        time_s: Current time in seconds
        bpm: Beats per minute
        amplitude_deg: Maximum deviation in degrees
        phase_offset_s: Phase offset for audio sync
        beat_multiplier: Frequency multiplier (1.0 = beat, 0.5 = half-beat)

    Returns:
        Offset in degrees to add to joint position
    """
    if amplitude_deg == 0.0 or bpm <= 0.0:
        return 0.0

    frequency_hz = (bpm / 60.0) * beat_multiplier
    phase = 2.0 * math.pi * frequency_hz * (time_s + phase_offset_s)
    return amplitude_deg * math.sin(phase)


def apply_groove_to_joints(
    joints_deg: List[float],
    time_s: float,
    config: GrooveConfig,
    amplitude_scale: float = 1.0,
) -> List[float]:
    """
    Apply groove modulation to joint positions.

    Args:
        joints_deg: Original joint positions in degrees (J1-J6)
        time_s: Current time in seconds
        config: Groove configuration
        amplitude_scale: Additional multiplier for groove amplitude (from groove-x<number>)

    Returns:
        New joint positions with groove applied
    """
    result = joints_deg.copy()
    for i, joint_name in enumerate(JOINT_ORDER):
        amplitude = config.amplitudes_deg.get(joint_name, 0.0) * amplitude_scale
        offset = compute_groove_offset(
            time_s,
            config.bpm,
            amplitude,
            config.phase_offset_s,
            config.beat_multiplier,
        )
        result[i] += offset
    return result


NULL_GROOVE_AMPLITUDES: Dict[str, float] = {joint: 0.0 for joint in JOINT_ORDER}


def create_groove_config(
    bpm: Optional[float],
    phase_offset_s: float = 0.0,
    beat_multiplier: float = 1.0,
) -> GrooveConfig:
    """
    Create a groove configuration from BPM.

    If BPM is None or 0, creates a null groove (all amplitudes 0) that has no effect.

    Args:
        bpm: Beats per minute from schedule (None or 0 for no groove)
        phase_offset_s: Phase offset for audio sync
        beat_multiplier: Frequency multiplier

    Returns:
        Configured GrooveConfig (null groove if no BPM)
    """
    if not bpm:
        return GrooveConfig(
            bpm=0.0,
            amplitudes_deg=NULL_GROOVE_AMPLITUDES.copy(),
            phase_offset_s=0.0,
            beat_multiplier=1.0,
        )

    return GrooveConfig(
        bpm=bpm,
        amplitudes_deg=DEFAULT_GROOVE_AMPLITUDES.copy(),
        phase_offset_s=phase_offset_s,
        beat_multiplier=beat_multiplier,
    )
