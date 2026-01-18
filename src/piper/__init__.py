"""
Piper AgileX Arm Controller

Simple interface for controlling the Piper 6-DOF robotic arm.
Supports both standard socketcan and Waveshare USB-CAN-A adapters.

Usage:
    from piper import PiperArm

    with PiperArm() as arm:  # auto-detects adapter
        arm.print_state()
        arm.move_joint_by(1, 10)  # Move joint 2 by 10 degrees
        arm.close_gripper()

Or specify adapter explicitly:
    from piper import create_arm

    arm = create_arm("waveshare")  # or "standard"
"""
from typing import Literal, Optional

from .base import PiperArmBase, ArmState, deg2rad, rad2deg


__all__ = [
    "PiperArm",
    "create_arm",
    "detect_adapter",
    "PiperArmBase",
    "ArmState",
    "deg2rad",
    "rad2deg",
]


AdapterType = Literal["auto", "standard", "waveshare", "simulation"]


def detect_adapter() -> Optional[str]:
    """
    Detect available CAN adapter.

    Returns:
        'standard' if socketcan is available (checked first)
        'waveshare' if Waveshare USB-CAN-A is found
        None if no adapter found
    """
    try:
        from .adapters.standard import find_socketcan_port
        if find_socketcan_port():
            return "standard"
    except ImportError:
        pass

    try:
        from .can import find_waveshare_port
        if find_waveshare_port():
            return "waveshare"
    except ImportError:
        pass

    return None


def create_arm(adapter: AdapterType = "auto", **kwargs) -> PiperArmBase:
    """
    Create a Piper arm controller with the specified adapter.

    Args:
        adapter: Adapter type - 'auto', 'standard', 'waveshare', or 'simulation'
        **kwargs: Additional arguments passed to the adapter constructor

    Returns:
        Configured PiperArmBase instance

    Raises:
        RuntimeError: If no adapter is found (when adapter='auto')
        ValueError: If invalid adapter type is specified
    """
    if adapter == "auto":
        detected = detect_adapter()
        if not detected:
            raise RuntimeError(
                "No CAN adapter found. "
                "Ensure can0/slcan0 is active or Waveshare USB-CAN-A is connected."
            )
        adapter = detected

    if adapter == "standard":
        from .adapters import StandardPiperArm
        return StandardPiperArm(**kwargs)
    elif adapter == "waveshare":
        from .adapters import WavesharePiperArm
        return WavesharePiperArm(**kwargs)
    elif adapter == "simulation":
        from .adapters import SimulationPiperArm
        return SimulationPiperArm(**kwargs)
    else:
        raise ValueError(f"Unknown adapter type: {adapter}")


# Convenience alias
PiperArm = create_arm
