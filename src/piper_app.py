#!/usr/bin/env python3
"""
Piper AgileX Arm Controller

Simple interface for controlling the Piper 6-DOF robotic arm.
"""
import time
import math
from dataclasses import dataclass
from typing import Optional

from piper_control import piper_interface, piper_init

# Auto-detect CAN interface
CAN_PORTS = ["slcan0", "can0"]


def deg2rad(d: float) -> float:
    return d * math.pi / 180.0

def rad2deg(r: float) -> float:
    return r * 180.0 / math.pi

def find_can_port() -> str:
    """Find available CAN port."""
    import can
    for port in CAN_PORTS:
        try:
            bus = can.interface.Bus(channel=port, interface="socketcan")
            bus.shutdown()
            return port
        except:
            continue
    raise RuntimeError(f"No CAN interface found (tried {CAN_PORTS})")


@dataclass
class ArmState:
    joints: list[float]  # radians
    gripper: float


class PiperArm:
    """High-level Piper arm controller."""

    def __init__(self, can_port: str = "auto", verbose: bool = True):
        self.can_port = can_port
        self.verbose = verbose
        self._robot: Optional[piper_interface.PiperInterface] = None

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Piper] {msg}")

    def connect(self):
        if self.can_port == "auto":
            self.can_port = find_can_port()
        self._log(f"Connecting to {self.can_port}...")
        self._robot = piper_interface.PiperInterface(can_port=self.can_port)
        piper_init.reset_arm(
            self._robot,
            arm_controller=piper_interface.ArmController.POSITION_VELOCITY,
            move_mode=piper_interface.MoveMode.JOINT,
        )
        piper_init.reset_gripper(self._robot)
        self._log("Connected")

    def disconnect(self):
        if self._robot:
            self._robot.stop()
            self._log("Disconnected")

    @property
    def state(self) -> ArmState:
        return ArmState(
            joints=self._robot.get_joint_positions(),
            gripper=self._robot.get_gripper_state(),
        )

    def move_joints(self, positions: list[float], wait: float = 2.0):
        """Move all joints to positions (radians)."""
        self._robot.command_joint_positions(positions)
        if wait > 0:
            time.sleep(wait)

    def move_joint(self, index: int, angle_deg: float, wait: float = 2.0):
        """Move single joint to angle (degrees)."""
        joints = list(self.state.joints)
        old = rad2deg(joints[index])
        joints[index] = deg2rad(angle_deg)
        self._log(f"Joint {index+1}: {old:+.1f}° → {angle_deg:+.1f}°")
        self.move_joints(joints, wait)

    def move_joint_by(self, index: int, delta_deg: float, wait: float = 2.0):
        """Move single joint by delta (degrees)."""
        joints = list(self.state.joints)
        old = rad2deg(joints[index])
        new = old + delta_deg
        joints[index] = deg2rad(new)
        self._log(f"Joint {index+1}: {old:+.1f}° → {new:+.1f}° ({delta_deg:+.1f}°)")
        self.move_joints(joints, wait)

    def gripper(self, position: float, wait: float = 1.0):
        """Set gripper: 0=open, 1=closed."""
        state = "closing" if position > 0.5 else "opening"
        self._log(f"Gripper {state}...")
        self._robot.command_gripper_position(position)
        if wait > 0:
            time.sleep(wait)

    def open_gripper(self, wait: float = 1.0):
        self.gripper(0.0, wait)

    def close_gripper(self, wait: float = 1.0):
        self.gripper(1.0, wait)

    def home(self, wait: float = 3.0):
        """Move all joints to zero."""
        self._log("Moving to home...")
        self.move_joints([0.0] * 6, wait)

    def print_state(self):
        """Print current joint positions."""
        s = self.state
        print("Joint positions:")
        for i, j in enumerate(s.joints):
            print(f"  Joint {i+1}: {rad2deg(j):+7.2f}°")
        print(f"  Gripper: {s.gripper:.2f}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()


def demo():
    """Demo: move joints and gripper."""
    print("=== Piper Arm Demo ===")
    print()
    print("WARNING: Arm will move! Ensure clear space.")
    print()

    with PiperArm() as arm:  # auto-detect CAN port
        arm.print_state()
        print()

        print("--- Moving Joint 2 by +20° ---")
        arm.move_joint_by(1, 20)
        arm.print_state()
        print()

        print("--- Moving Joint 2 back (-20°) ---")
        arm.move_joint_by(1, -20)
        print()

        print("--- Moving Joint 4 by +30° ---")
        arm.move_joint_by(3, 30)
        print()

        print("--- Moving Joint 4 back (-30°) ---")
        arm.move_joint_by(3, -30)
        print()

        print("--- Gripper test ---")
        arm.close_gripper()
        arm.open_gripper()

    print()
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo()
