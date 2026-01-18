"""
Waveshare Piper arm adapter using custom CAN protocol.

This adapter communicates directly with the Piper arm via the Waveshare
USB-CAN-A adapter, bypassing piper_control's socketcan requirement.
"""
import threading
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

    # CAN message IDs (from piper_sdk protocol v2)
    ARM_JOINT_FEEDBACK_ID_BASE = 0x2A5  # Joint feedback: 0x2A5 (J1-2), 0x2A6 (J3-4), 0x2A7 (J5-6)
    ARM_JOINT_CTRL_ID_BASE = 0x155      # Joint control: 0x155 (J1-2), 0x156 (J3-4), 0x157 (J5-6)
    ARM_MOTION_CTRL_1 = 0x150           # Motion control 1 (emergency stop, drag teach, etc.)
    ARM_MOTION_CTRL_2 = 0x151           # Motion control 2 (ctrl_mode, move_mode, speed rate)
    GRIPPER_FEEDBACK_ID = 0x2A8
    GRIPPER_COMMAND_ID = 0x159          # Gripper control
    ARM_MOTOR_ENABLE_ID = 0x471         # Motor enable command

    # Default inter-message delay (seconds)
    # 10ms is conservative; 2-5ms may work for low-latency applications
    DEFAULT_MSG_DELAY = 0.01

    def __init__(
        self,
        port: str = "auto",
        verbose: bool = True,
        msg_delay: Optional[float] = None,
        can_port: Optional[str] = None,  # Alias for port (compatibility with choreography module)
    ):
        """
        Initialize the Waveshare Piper arm adapter.

        Args:
            port: Serial port (e.g., '/dev/ttyUSB0') or 'auto' to detect
            verbose: Print status messages
            msg_delay: Inter-message delay in seconds (default: 0.01)
                       Lower values (0.002-0.005) improve latency but may
                       cause dropped messages on slower systems.
            can_port: Alias for port (for compatibility)
        """
        super().__init__(verbose=verbose)
        # can_port is for compatibility with choreography module
        # If can_port looks like a CAN interface (can0, slcan0), ignore it and use auto-detect
        if can_port and not can_port.startswith(("can", "slcan")):
            self.port = can_port
        else:
            self.port = port
        self.msg_delay = msg_delay if msg_delay is not None else self.DEFAULT_MSG_DELAY
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
        """Initialize arm for CAN control.

        Note: The arm requires continuous command sending during movement.
        This just does initial setup; actual enable happens in _send_command_set.
        """
        # Read initial joint positions
        self._read_feedback(timeout=0.5)

        # Send a few enable + mode commands to prepare the arm
        for _ in range(10):
            self._bus.send(can.Message(
                arbitration_id=self.ARM_MOTOR_ENABLE_ID,
                data=bytes([0x07, 0x02, 0, 0, 0, 0, 0, 0]),
                is_extended_id=False,
            ))
            self._bus.send(can.Message(
                arbitration_id=self.ARM_MOTION_CTRL_2,
                data=bytes([0x01, 0x01, 0x32, 0, 0, 0, 0, 0]),
                is_extended_id=False,
            ))
            time.sleep(0.02)
        time.sleep(0.1)

    def _read_feedback(self, timeout: float = 0.5) -> bool:
        """Read joint feedback from arm.

        Reads feedback messages until we have all 3 joint feedback IDs.
        """
        deadline = time.time() + timeout
        received = set()

        while time.time() < deadline and len(received) < 3:
            msg = self._bus.recv(timeout=0.05)
            if not msg:
                continue
            if self._process_feedback_msg(msg):
                if 0x2A5 <= msg.arbitration_id <= 0x2A7:
                    received.add(msg.arbitration_id)

        return len(received) >= 3

    def _process_feedback_msg(self, msg) -> bool:
        """Process a single feedback message. Returns True if it was a feedback msg."""
        if not msg:
            return False

        # Joint feedback messages (0x2A5-0x2A7, each has 2 joints)
        if 0x2A5 <= msg.arbitration_id <= 0x2A7:
            idx = (msg.arbitration_id - 0x2A5) * 2
            if len(msg.data) >= 8:
                j1 = int.from_bytes(msg.data[0:4], 'big', signed=True) / 1000.0
                j2 = int.from_bytes(msg.data[4:8], 'big', signed=True) / 1000.0
                self._joints[idx] = deg2rad(j1)
                if idx + 1 < 6:
                    self._joints[idx + 1] = deg2rad(j2)
            return True

        # Gripper feedback (0x2A8)
        elif msg.arbitration_id == self.GRIPPER_FEEDBACK_ID:
            if len(msg.data) >= 4:
                pos = int.from_bytes(msg.data[0:4], 'big', signed=True)
                self._gripper = pos / 70000.0
            return True

        return False

    def _get_joints(self) -> list[float]:
        self._read_feedback()
        return list(self._joints)

    def _get_gripper(self) -> float:
        self._read_feedback()
        return self._gripper

    def _send_command_set(self, pos_mdeg: list[int], speed_pct: int = 30) -> None:
        """Send full command set: enable + motion_ctrl + joint positions.

        The Piper arm requires all three command types sent together continuously.
        """
        # Enable all motors (0x471)
        self._bus.send(can.Message(
            arbitration_id=self.ARM_MOTOR_ENABLE_ID,
            data=bytes([0x07, 0x02, 0, 0, 0, 0, 0, 0]),
            is_extended_id=False,
        ))

        # Motion control (0x151): CAN mode, joint mode, speed%
        self._bus.send(can.Message(
            arbitration_id=self.ARM_MOTION_CTRL_2,
            data=bytes([0x01, 0x01, speed_pct, 0, 0, 0, 0, 0]),
            is_extended_id=False,
        ))

        # Joint positions (0x155-0x157)
        for i in range(3):
            j1 = pos_mdeg[i * 2]
            j2 = pos_mdeg[i * 2 + 1] if i * 2 + 1 < 6 else 0
            data = j1.to_bytes(4, 'big', signed=True) + j2.to_bytes(4, 'big', signed=True)
            self._bus.send(can.Message(
                arbitration_id=self.ARM_JOINT_CTRL_ID_BASE + i,
                data=data,
                is_extended_id=False,
            ))

    def _send_joint_command(self, positions: list[float], duration: float = 2.0, speed_pct: int = 30) -> None:
        """Send joint command continuously until target reached or timeout.

        Uses a background thread to read feedback while sending commands.

        Args:
            positions: Target joint positions in radians
            duration: Maximum time to send commands (seconds)
            speed_pct: Movement speed percentage (1-100)
        """
        pos_mdeg = [int(rad2deg(p) * 1000) for p in positions]
        stop_flag = threading.Event()

        def feedback_reader():
            while not stop_flag.is_set():
                msg = self._bus.recv(timeout=0.05)
                if msg:
                    self._process_feedback_msg(msg)

        reader_thread = threading.Thread(target=feedback_reader, daemon=True)
        reader_thread.start()

        start = time.time()
        while time.time() - start < duration:
            self._send_command_set(pos_mdeg, speed_pct)
            time.sleep(0.005)  # 5ms interval like SDK

        stop_flag.set()
        reader_thread.join(timeout=0.5)

    def _send_gripper_command(self, position: float) -> None:
        # Gripper position: 0-70000 range, big-endian
        pos = int(position * 70000)
        data = pos.to_bytes(4, 'big', signed=True) + bytes([0, 0, 0, 0])
        msg = can.Message(
            arbitration_id=self.GRIPPER_COMMAND_ID,
            data=data,
            is_extended_id=False,
        )
        self._bus.send(msg)
