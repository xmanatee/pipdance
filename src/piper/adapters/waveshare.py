"""
Waveshare Piper arm adapter using custom CAN protocol.

This adapter communicates directly with the Piper arm via the Waveshare
USB-CAN-A adapter, bypassing piper_control's socketcan requirement.
"""
import time
from typing import Optional

import can

from ..base import PiperArmBase, deg2rad, rad2deg
from ..can import WaveshareBus, find_waveshare_port


class WavesharePiperArm(PiperArmBase):
    """
    Piper arm controller using Waveshare USB-CAN-A adapter.

    Communicates directly via CAN protocol without requiring socketcan.
    """

    # CAN message IDs (from piper_sdk protocol)
    ARM_FEEDBACK_ID_BASE = 0x2A1  # Joint feedback messages 0x2A1-0x2A3
    ARM_COMMAND_ID_BASE = 0x151   # Joint command messages 0x151-0x153
    GRIPPER_FEEDBACK_ID = 0x2A5
    GRIPPER_COMMAND_ID = 0x155
    ARM_ENABLE_ID = 0x050
    ARM_MODE_ID = 0x051

    def __init__(self, port: str = "auto", verbose: bool = True):
        """
        Initialize the Waveshare Piper arm adapter.

        Args:
            port: Serial port (e.g., '/dev/ttyUSB0') or 'auto' to detect
            verbose: Print status messages
        """
        super().__init__(verbose=verbose)
        self.port = port
        self._bus: Optional[WaveshareBus] = None
        self._joints = [0.0] * 6  # Cached joint positions (radians)
        self._gripper = 0.0       # Cached gripper position

    def _connect(self) -> None:
        if self.port == "auto":
            port = find_waveshare_port()
            if not port:
                raise RuntimeError("No Waveshare USB-CAN-A found. Check connection.")
            self.port = port

        self._log(f"Connecting via {self.port}...")
        self._bus = WaveshareBus(channel=self.port, bitrate=1000000)
        self._enable_arm()

    def _disconnect(self) -> None:
        if self._bus:
            self._bus.shutdown()
            self._bus = None

    def _enable_arm(self) -> None:
        """Send enable command to arm."""
        # Enable message: ID 0x050, data specifies mode
        # Mode 2 = position/velocity control
        enable_msg = can.Message(
            arbitration_id=self.ARM_ENABLE_ID,
            data=bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            is_extended_id=False,
        )
        self._bus.send(enable_msg)
        time.sleep(0.1)

        # Set mode to joint position control
        mode_msg = can.Message(
            arbitration_id=self.ARM_MODE_ID,
            data=bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            is_extended_id=False,
        )
        self._bus.send(mode_msg)
        time.sleep(0.5)

    def _read_feedback(self, timeout: float = 0.5) -> bool:
        """Read joint feedback from arm."""
        deadline = time.time() + timeout
        received = set()

        while time.time() < deadline and len(received) < 4:
            msg = self._bus.recv(timeout=0.1)
            if not msg:
                continue

            # Joint feedback messages (0x2A1-0x2A3, each has 2 joints)
            if 0x2A1 <= msg.arbitration_id <= 0x2A3:
                idx = (msg.arbitration_id - 0x2A1) * 2
                if len(msg.data) >= 8:
                    # Each joint is int32 in 0.001 degree units
                    j1 = int.from_bytes(msg.data[0:4], 'little', signed=True) / 1000.0
                    j2 = int.from_bytes(msg.data[4:8], 'little', signed=True) / 1000.0
                    self._joints[idx] = deg2rad(j1)
                    if idx + 1 < 6:
                        self._joints[idx + 1] = deg2rad(j2)
                received.add(msg.arbitration_id)

            # Gripper feedback
            elif msg.arbitration_id == self.GRIPPER_FEEDBACK_ID:
                if len(msg.data) >= 4:
                    pos = int.from_bytes(msg.data[0:4], 'little', signed=True)
                    self._gripper = pos / 70000.0  # Normalize to 0-1
                received.add(msg.arbitration_id)

        return len(received) > 0

    def _get_joints(self) -> list[float]:
        self._read_feedback()
        return list(self._joints)

    def _get_gripper(self) -> float:
        self._read_feedback()
        return self._gripper

    def _send_joint_command(self, positions: list[float]) -> None:
        # Convert to millidegrees
        pos_mdeg = [int(rad2deg(p) * 1000) for p in positions]

        # Send in 3 messages (2 joints each)
        for i in range(3):
            j1 = pos_mdeg[i * 2]
            j2 = pos_mdeg[i * 2 + 1] if i * 2 + 1 < 6 else 0

            data = j1.to_bytes(4, 'little', signed=True) + j2.to_bytes(4, 'little', signed=True)
            msg = can.Message(
                arbitration_id=self.ARM_COMMAND_ID_BASE + i,
                data=data,
                is_extended_id=False,
            )
            self._bus.send(msg)
            time.sleep(0.01)

    def _send_gripper_command(self, position: float) -> None:
        # Gripper position: 0-70000 range
        pos = int(position * 70000)
        data = pos.to_bytes(4, 'little', signed=True) + bytes([0, 0, 0, 0])
        msg = can.Message(
            arbitration_id=self.GRIPPER_COMMAND_ID,
            data=data,
            is_extended_id=False,
        )
        self._bus.send(msg)
