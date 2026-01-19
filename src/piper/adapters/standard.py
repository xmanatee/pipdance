"""
Standard Piper arm adapter using piper_sdk directly.

Uses the low-level piper_sdk for fast initialization with explicit timeouts.
Requires a socketcan interface (can0 or slcan0).
"""
import math
import time
from typing import Optional

import can
from piper_sdk import C_PiperInterface_V2

from ..base import PiperArmBase


# Standard CAN ports to check
CAN_PORTS = ["slcan0", "can0"]

# Timeouts
ENABLE_TIMEOUT_S = 2.0
ENABLE_RETRY_INTERVAL_S = 0.01


def find_socketcan_port() -> Optional[str]:
    """Find an available socketcan port."""
    for port in CAN_PORTS:
        try:
            bus = can.interface.Bus(channel=port, interface="socketcan")
            bus.shutdown()
            return port
        except Exception:
            continue
    return None


class StandardPiperArm(PiperArmBase):
    """
    Piper arm controller using standard socketcan interface.

    Uses piper_sdk directly for fast, timeout-controlled initialization.
    """

    def __init__(self, can_port: str = "auto", verbose: bool = True):
        """
        Initialize the standard Piper arm adapter.

        Args:
            can_port: CAN interface name ('can0', 'slcan0') or 'auto' to detect
            verbose: Print status messages
        """
        super().__init__(verbose=verbose)
        self.can_port = can_port
        self._piper: Optional[C_PiperInterface_V2] = None

    def _connect(self) -> None:
        if self.can_port == "auto":
            port = find_socketcan_port()
            if not port:
                raise RuntimeError(f"No socketcan interface found (tried {CAN_PORTS})")
            self.can_port = port

        self._log(f"Connecting to {self.can_port}...")
        self._piper = C_PiperInterface_V2(self.can_port)
        self._piper.ConnectPort()

        # Enable arm with timeout
        self._log("Enabling arm...")
        start = time.time()
        enabled = False
        attempts = 0
        while time.time() - start < ENABLE_TIMEOUT_S:
            if self._piper.EnablePiper():
                enabled = True
                break
            attempts += 1
            time.sleep(ENABLE_RETRY_INTERVAL_S)

        if not enabled:
            raise RuntimeError(f"Failed to enable arm after {ENABLE_TIMEOUT_S}s ({attempts} attempts)")

        self._log(f"Enabled after {attempts} attempts")

        # Set motion control mode: CAN control, joint mode, 50% speed
        self._piper.MotionCtrl_2(0x01, 0x01, 50)
        time.sleep(0.1)  # Brief settle time

        self._log("Ready")

    def _disconnect(self) -> None:
        # piper_sdk doesn't have an explicit disconnect, just stop sending
        self._piper = None

    def _get_joints(self) -> list[float]:
        """Get joint positions in radians."""
        joints = self._piper.GetArmJointMsgs()
        # SDK returns millidegrees, convert to radians
        return [
            math.radians(joints.joint_state.joint_1 / 1000.0),
            math.radians(joints.joint_state.joint_2 / 1000.0),
            math.radians(joints.joint_state.joint_3 / 1000.0),
            math.radians(joints.joint_state.joint_4 / 1000.0),
            math.radians(joints.joint_state.joint_5 / 1000.0),
            math.radians(joints.joint_state.joint_6 / 1000.0),
        ]

    def _get_gripper(self) -> float:
        """Get gripper position (0-1 range)."""
        gripper = self._piper.GetArmGripperMsgs()
        # Convert from SDK units (0.001mm) to 0-1 range (0-70mm)
        pos_mm = gripper.gripper_state.grippers_angle / 1000.0
        return max(0.0, min(1.0, pos_mm / 70.0))

    def _send_joint_command(self, positions: list[float], duration: float = 0.0) -> None:
        """Send joint positions in radians.

        Args:
            positions: Target positions in radians
            duration: Ignored (SDK handles timing internally)
        """
        # Convert radians to millidegrees for SDK
        mdeg = [int(math.degrees(p) * 1000) for p in positions]
        self._piper.JointCtrl(*mdeg)

    def _send_gripper_command(self, position: float) -> None:
        """Send gripper position (0-1 range)."""
        # Convert 0-1 to SDK units (0.001mm), range 0-70mm = 0-70000
        pos_um = int(position * 70000)
        # GripperCtrl(position, effort, mode, set_zero)
        # mode 0x01 = enable, effort 1000 = 1 N·m
        self._piper.GripperCtrl(pos_um, 1000, 0x01, 0)
