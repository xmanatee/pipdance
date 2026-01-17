"""
Standard Piper arm adapter using piper_control library.

This adapter uses the official piper_control library which requires
a socketcan interface (can0 or slcan0).
"""
from typing import Optional

import can
from piper_control import piper_interface, piper_init

from ..base import PiperArmBase


# Standard CAN ports to check
CAN_PORTS = ["slcan0", "can0"]


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

    Uses the piper_control library which requires socketcan (can0/slcan0).
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
        self._robot: Optional[piper_interface.PiperInterface] = None

    def _connect(self) -> None:
        if self.can_port == "auto":
            port = find_socketcan_port()
            if not port:
                raise RuntimeError(f"No socketcan interface found (tried {CAN_PORTS})")
            self.can_port = port

        self._log(f"Connecting to {self.can_port}...")
        self._robot = piper_interface.PiperInterface(can_port=self.can_port)
        piper_init.reset_arm(
            self._robot,
            arm_controller=piper_interface.ArmController.POSITION_VELOCITY,
            move_mode=piper_interface.MoveMode.JOINT,
        )
        piper_init.reset_gripper(self._robot)

    def _disconnect(self) -> None:
        if self._robot:
            self._robot.stop()
            self._robot = None

    def _get_joints(self) -> list[float]:
        return list(self._robot.get_joint_positions())

    def _get_gripper(self) -> float:
        return self._robot.get_gripper_state()

    def _send_joint_command(self, positions: list[float]) -> None:
        self._robot.command_joint_positions(positions)

    def _send_gripper_command(self, position: float) -> None:
        self._robot.command_gripper_position(position)
