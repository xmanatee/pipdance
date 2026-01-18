"""
Simulation stepper for Genesis physics.

Handles stepping the simulation while maintaining real-time pacing.
Must run in the main thread due to Genesis viewer requirements.
"""
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import genesis as gs


class SimulationStepper:
    """
    Steps the Genesis simulation with real-time pacing.

    Unlike a background thread approach, this stepper runs in the main thread
    because Genesis viewer can only be updated from the thread that created it.

    Handles the mismatch between physics dt and display rate by stepping
    multiple times per frame to maintain real-time correspondence.
    """

    def __init__(
        self,
        scene: "gs.Scene",
        entity: "gs.Entity",
        target_fps: float = 60.0,
    ):
        self._scene = scene
        self._entity = entity
        self._target_fps = target_fps
        self._frame_time = 1.0 / target_fps

        # Get physics timestep from scene
        self._physics_dt = float(scene.dt)

        # Calculate how many physics steps per display frame for real-time
        # If dt=1/240 and target_fps=60, need 4 steps per frame
        self._steps_per_frame = max(1, int(round(self._frame_time / self._physics_dt)))

        self._arm_joints = [0, 1, 2, 3, 4, 5]
        self._gripper_joints = [6, 7]

        # Cache whether gripper exists (check once at init)
        num_dofs = len(entity.get_dofs_position())
        self._has_gripper = num_dofs > max(self._gripper_joints)

        self._target_joints = [0.0] * 6
        self._target_gripper = 0.0

    @property
    def physics_dt(self) -> float:
        """Physics timestep in seconds."""
        return self._physics_dt

    @property
    def steps_per_frame(self) -> int:
        """Number of physics steps per display frame."""
        return self._steps_per_frame

    def start(self) -> None:
        """No-op for compatibility (main-thread stepping)."""
        pass

    def stop(self) -> None:
        """No-op for compatibility (main-thread stepping)."""
        pass

    def set_targets(
        self,
        joints: list[float] | None = None,
        gripper: float | None = None,
    ) -> None:
        """
        Set target positions for joints and/or gripper.

        Args:
            joints: Target joint positions in radians (6 values)
            gripper: Target gripper position (0=open, 1=closed)
        """
        if joints is not None:
            self._target_joints = list(joints)
        if gripper is not None:
            self._target_gripper = gripper

    def get_current_joints(self) -> list[float]:
        """Get current joint positions from the entity."""
        import torch

        pos = self._entity.get_dofs_position()
        if isinstance(pos, torch.Tensor):
            pos = pos.cpu().numpy()
        return [float(pos[i]) for i in self._arm_joints]

    def get_current_gripper(self) -> float:
        """Get current gripper position (mapped to 0-1)."""
        if not self._has_gripper:
            return 0.0

        import torch

        pos = self._entity.get_dofs_position()
        if isinstance(pos, torch.Tensor):
            pos = pos.cpu().numpy()

        g1 = float(pos[self._gripper_joints[0]])
        g2 = float(pos[self._gripper_joints[1]])
        avg = (g1 + g2) / 2.0
        return min(1.0, max(0.0, avg / 0.04))

    def _apply_controls(self) -> None:
        """Apply current joint and gripper targets to the entity."""
        import torch

        targets = torch.tensor(self._target_joints, dtype=torch.float32)
        self._entity.control_dofs_position(targets, dofs_idx_local=self._arm_joints)

        if self._has_gripper:
            gripper_pos = self._target_gripper * 0.04
            gripper_targets = torch.tensor(
                [gripper_pos, gripper_pos], dtype=torch.float32
            )
            self._entity.control_dofs_position(
                gripper_targets, dofs_idx_local=self._gripper_joints
            )

    def _step_physics(self) -> None:
        """Step physics simulation for one display frame."""
        for _ in range(self._steps_per_frame):
            self._scene.step()

    def step_for_duration(self, duration: float) -> None:
        """
        Step the simulation for the given duration in real-time.

        Steps multiple physics substeps per display frame to maintain
        correspondence between wall-clock time and simulation time.

        Args:
            duration: Time in seconds to simulate
        """
        if duration <= 0:
            return

        start = time.perf_counter()
        end = start + duration

        while time.perf_counter() < end:
            frame_start = time.perf_counter()

            self._apply_controls()
            self._step_physics()

            elapsed = time.perf_counter() - frame_start
            sleep_time = self._frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def step_once(self) -> None:
        """Step the simulation for one display frame worth of physics."""
        self._apply_controls()
        self._step_physics()
