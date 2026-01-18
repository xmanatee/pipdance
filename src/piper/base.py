"""
Piper Arm base classes and utilities.

This module contains shared code for all adapter implementations:
- ArmState dataclass
- deg2rad/rad2deg helpers
- PiperArmBase abstract base class
"""
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


def deg2rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0


def rad2deg(radians: float) -> float:
    """Convert radians to degrees."""
    return radians * 180.0 / math.pi


@dataclass
class ArmState:
    """Current state of the Piper arm."""
    joints: list[float]  # Joint angles in radians (6 joints)
    gripper: float       # Gripper position: 0=open, 1=closed


class PiperArmBase(ABC):
    """
    Abstract base class for Piper arm adapters.

    Provides common high-level API methods. Subclasses implement
    the low-level CAN communication via _connect(), _disconnect(),
    _get_joints(), _get_gripper(), _send_joint_command(), and _send_gripper_command().
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._connected = False

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Piper] {msg}")

    @abstractmethod
    def _connect(self) -> None:
        """Establish connection to the arm."""

    @abstractmethod
    def _disconnect(self) -> None:
        """Close connection to the arm."""

    @abstractmethod
    def _get_joints(self) -> list[float]:
        """Get current joint positions in radians."""

    @abstractmethod
    def _get_gripper(self) -> float:
        """Get current gripper position (0-1)."""

    @abstractmethod
    def _send_joint_command(self, positions: list[float]) -> None:
        """Send joint position command (radians)."""

    @abstractmethod
    def _send_gripper_command(self, position: float) -> None:
        """Send gripper position command (0-1)."""

    def connect(self) -> None:
        """Connect to the arm."""
        self._connect()
        self._connected = True
        self._log("Connected")

    def disconnect(self) -> None:
        """Disconnect from the arm."""
        if self._connected:
            self._disconnect()
            self._connected = False
            self._log("Disconnected")

    @property
    def state(self) -> ArmState:
        """Get current arm state."""
        return ArmState(
            joints=self._get_joints(),
            gripper=self._get_gripper(),
        )

    def move_joints(self, positions: list[float], wait: float = 2.0) -> None:
        """Move all joints to positions (radians)."""
        self._send_joint_command(positions)
        if wait > 0:
            time.sleep(wait)

    def move_joint(self, index: int, angle_deg: float, wait: float = 2.0) -> None:
        """Move single joint to angle (degrees)."""
        joints = self._get_joints()
        old = rad2deg(joints[index])
        joints[index] = deg2rad(angle_deg)
        self._log(f"Joint {index+1}: {old:+.1f}° → {angle_deg:+.1f}°")
        self.move_joints(joints, wait)

    def move_joint_by(self, index: int, delta_deg: float, wait: float = 2.0) -> None:
        """Move single joint by delta (degrees)."""
        joints = self._get_joints()
        old = rad2deg(joints[index])
        new = old + delta_deg
        joints[index] = deg2rad(new)
        self._log(f"Joint {index+1}: {old:+.1f}° → {new:+.1f}° ({delta_deg:+.1f}°)")
        self.move_joints(joints, wait)

    def gripper(self, position: float, wait: float = 1.0) -> None:
        """Set gripper position: 0=open, 1=closed."""
        state = "closing" if position > 0.5 else "opening"
        self._log(f"Gripper {state}...")
        self._send_gripper_command(position)
        if wait > 0:
            time.sleep(wait)

    def open_gripper(self, wait: float = 1.0) -> None:
        """Open the gripper."""
        self.gripper(0.0, wait)

    def close_gripper(self, wait: float = 1.0) -> None:
        """Close the gripper."""
        self.gripper(1.0, wait)

    def home(self, wait: float = 3.0) -> None:
        """Move all joints to zero position."""
        self._log("Moving to home...")
        self.move_joints([0.0] * 6, wait)

    def print_state(self) -> None:
        """Print current joint positions."""
        s = self.state
        print("Joint positions:")
        for i, j in enumerate(s.joints):
            print(f"  Joint {i+1}: {rad2deg(j):+7.2f}°")
        print(f"  Gripper: {s.gripper:.2f}")

    def wait(self, duration: float) -> None:
        """Wait for specified duration. Override for simulation to step physics."""
        if duration > 0:
            time.sleep(duration)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
