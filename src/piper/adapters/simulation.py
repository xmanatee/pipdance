"""
Simulation adapter using Genesis physics engine.

Enables choreography testing without physical hardware by running
the robot in a simulated environment.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from ..base import PiperArmBase
from ..simulation import (
    create_scene,
    load_piper,
    configure_motors,
    SimulationStepper,
    DEFAULT_URDF,
)

if TYPE_CHECKING:
    import genesis as gs


class SimulationPiperArm(PiperArmBase):
    """
    Piper arm controller using Genesis physics simulation.

    Steps the simulation in the main thread during wait periods,
    as Genesis viewer requires main-thread updates.
    """

    def __init__(
        self,
        urdf_path: str | Path | None = None,
        show_viewer: bool = True,
        verbose: bool = True,
    ):
        """
        Initialize the simulation adapter.

        Args:
            urdf_path: Path to URDF file (uses default if None)
            show_viewer: Whether to show the visualization window
            verbose: Print status messages
        """
        super().__init__(verbose=verbose)
        self._urdf_path = Path(urdf_path) if urdf_path else None
        self._show_viewer = show_viewer

        self._scene: "gs.Scene | None" = None
        self._entity: "gs.Entity | None" = None
        self._stepper: SimulationStepper | None = None

    def _connect(self) -> None:
        self._log("Initializing Genesis simulation...")

        self._scene = create_scene(show_viewer=self._show_viewer)
        self._entity = load_piper(self._scene, self._urdf_path)
        self._scene.build()

        configure_motors(self._entity)

        self._stepper = SimulationStepper(
            scene=self._scene,
            entity=self._entity,
            target_fps=60.0,
        )
        self._stepper.start()

        urdf_name = (self._urdf_path or DEFAULT_URDF).name
        viewer_status = "with viewer" if self._show_viewer else "headless"
        dt_ms = self._stepper._physics_dt * 1000
        steps = self._stepper._steps_per_frame
        self._log(f"Simulation ready ({urdf_name}, {viewer_status})")
        self._log(f"Physics: dt={dt_ms:.2f}ms, {steps} steps/frame for real-time")

    def _disconnect(self) -> None:
        if self._stepper:
            self._stepper.stop()
            self._stepper = None

        self._entity = None
        self._scene = None

    def _get_joints(self) -> list[float]:
        if not self._stepper:
            return [0.0] * 6
        return self._stepper.get_current_joints()

    def _get_gripper(self) -> float:
        if not self._stepper:
            return 0.0
        return self._stepper.get_current_gripper()

    def _send_joint_command(self, positions: list[float]) -> None:
        if self._stepper:
            self._stepper.set_targets(joints=positions)

    def _send_gripper_command(self, position: float) -> None:
        if self._stepper:
            self._stepper.set_targets(gripper=position)

    def move_joints(self, positions: list[float], wait: float = 2.0) -> None:
        """Move all joints to positions (radians), stepping simulation during wait."""
        self._send_joint_command(positions)
        if wait > 0 and self._stepper:
            self._stepper.step_for_duration(wait)

    def gripper(self, position: float, wait: float = 1.0) -> None:
        """Set gripper position, stepping simulation during wait."""
        state = "closing" if position > 0.5 else "opening"
        self._log(f"Gripper {state}...")
        self._send_gripper_command(position)
        if wait > 0 and self._stepper:
            self._stepper.step_for_duration(wait)

    def wait(self, duration: float) -> None:
        """Wait by stepping the simulation for the given duration."""
        if duration > 0 and self._stepper:
            self._stepper.step_for_duration(duration)
