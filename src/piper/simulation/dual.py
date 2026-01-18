"""
Dual arm simulation support for Genesis physics engine.

Creates two Piper arms sharing a single scene, enabling synchronized
dual-arm choreography testing without physical hardware.
"""
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..base import PiperArmBase
from .scene import create_scene, configure_motors, DEFAULT_URDF
from .stepper import GRIPPER_RANGE_M

if TYPE_CHECKING:
    import genesis as gs


class DualSimulationStepper:
    """
    Shared stepper for dual arm simulation.

    Manages a single Genesis scene with two robot entities.
    When stepping, both robots advance together.
    """

    def __init__(
        self,
        scene: "gs.Scene",
        entities: dict[str, "gs.Entity"],
        target_fps: float = 60.0,
    ):
        self._scene = scene
        self._entities = entities
        self._target_fps = target_fps
        self._frame_time = 1.0 / target_fps

        self._physics_dt = float(scene.dt)
        self._steps_per_frame = max(1, int(round(self._frame_time / self._physics_dt)))

        self._arm_joints = [0, 1, 2, 3, 4, 5]
        self._gripper_joints = [6, 7]

        self._targets: dict[str, dict] = {}
        for label, entity in entities.items():
            num_dofs = len(entity.get_dofs_position())
            self._targets[label] = {
                "joints": [0.0] * 6,
                "gripper": 0.0,
                "has_gripper": num_dofs > max(self._gripper_joints),
            }

    @property
    def physics_dt(self) -> float:
        return self._physics_dt

    @property
    def steps_per_frame(self) -> int:
        return self._steps_per_frame

    def set_targets(
        self,
        label: str,
        joints: list[float] | None = None,
        gripper: float | None = None,
    ) -> None:
        """Set target positions for a specific arm."""
        if label not in self._targets:
            raise ValueError(f"Unknown arm label: {label}")

        if joints is not None:
            self._targets[label]["joints"] = list(joints)
        if gripper is not None:
            self._targets[label]["gripper"] = gripper

    def get_current_joints(self, label: str) -> list[float]:
        """Get current joint positions for a specific arm."""
        import torch

        entity = self._entities[label]
        pos = entity.get_dofs_position()
        if isinstance(pos, torch.Tensor):
            pos = pos.cpu().numpy()
        return [float(pos[i]) for i in self._arm_joints]

    def get_current_gripper(self, label: str) -> float:
        """Get current gripper position for a specific arm."""
        if not self._targets[label]["has_gripper"]:
            return 0.0

        import torch

        entity = self._entities[label]
        pos = entity.get_dofs_position()
        if isinstance(pos, torch.Tensor):
            pos = pos.cpu().numpy()

        g1 = float(pos[self._gripper_joints[0]])
        g2 = float(pos[self._gripper_joints[1]])
        avg = (g1 + g2) / 2.0
        return min(1.0, max(0.0, avg / GRIPPER_RANGE_M))

    def _apply_controls(self) -> None:
        """Apply targets to all entities."""
        import torch

        for label, entity in self._entities.items():
            target = self._targets[label]

            joint_targets = torch.tensor(target["joints"], dtype=torch.float32)
            entity.control_dofs_position(joint_targets, dofs_idx_local=self._arm_joints)

            if target["has_gripper"]:
                gripper_pos = target["gripper"] * GRIPPER_RANGE_M
                gripper_targets = torch.tensor(
                    [gripper_pos, gripper_pos], dtype=torch.float32
                )
                entity.control_dofs_position(
                    gripper_targets, dofs_idx_local=self._gripper_joints
                )

    def _step_physics(self) -> None:
        """Step physics simulation for one display frame."""
        for _ in range(self._steps_per_frame):
            self._scene.step()

    def step_for_duration(self, duration: float) -> None:
        """Step the simulation for the given duration in real-time."""
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
        """Step the simulation for one display frame."""
        self._apply_controls()
        self._step_physics()


class DualSimulationArm(PiperArmBase):
    """
    Simulation arm that shares a scene/stepper with another arm.

    Uses a shared DualSimulationStepper so that wait() on either arm
    advances both arms in the simulation.
    """

    def __init__(
        self,
        shared_stepper: DualSimulationStepper,
        label: str,
        verbose: bool = True,
    ):
        super().__init__(verbose=verbose)
        self._stepper = shared_stepper
        self._label = label

    def _connect(self) -> None:
        self._log(f"Simulation arm '{self._label}' ready")

    def _disconnect(self) -> None:
        pass

    def _get_joints(self) -> list[float]:
        return self._stepper.get_current_joints(self._label)

    def _get_gripper(self) -> float:
        return self._stepper.get_current_gripper(self._label)

    def _send_joint_command(self, positions: list[float]) -> None:
        self._stepper.set_targets(self._label, joints=positions)

    def _send_gripper_command(self, position: float) -> None:
        self._stepper.set_targets(self._label, gripper=position)

    def move_joints(self, positions: list[float], wait: float = 2.0) -> None:
        """Move joints, stepping shared simulation during wait."""
        self._send_joint_command(positions)
        if wait > 0:
            self._stepper.step_for_duration(wait)

    def gripper(self, position: float, wait: float = 1.0) -> None:
        """Set gripper, stepping shared simulation during wait."""
        state = "closing" if position > 0.5 else "opening"
        self._log(f"Gripper {state}...")
        self._send_gripper_command(position)
        if wait > 0:
            self._stepper.step_for_duration(wait)

    def wait(self, duration: float) -> None:
        """Wait by stepping the shared simulation."""
        if duration > 0:
            self._stepper.step_for_duration(duration)


def create_dual_simulation_arms(
    show_viewer: bool = True,
    separation: float = 1.20,
    urdf_path: Path | None = None,
    verbose: bool = True,
) -> tuple[DualSimulationArm, DualSimulationArm]:
    """
    Create two simulation arms sharing one scene.

    The arms are positioned facing each other:
    - "he" at (-separation/2, 0, 0)
    - "she" at (separation/2, 0, 0), rotated 180° to face "he"

    Args:
        show_viewer: Whether to show the visualization window
        separation: Distance between the two arms in meters
        urdf_path: Path to URDF file (uses default if None)
        verbose: Print status messages

    Returns:
        tuple: (he_arm, she_arm) - both PiperArmBase compatible
    """
    import genesis as gs

    if verbose:
        print("[DualSim] Initializing Genesis simulation...")

    scene = create_scene(show_viewer=show_viewer)

    if urdf_path is None:
        urdf_path = DEFAULT_URDF

    if not urdf_path.exists():
        raise FileNotFoundError(f"URDF not found: {urdf_path}")

    he_entity = scene.add_entity(
        gs.morphs.URDF(
            file=str(urdf_path),
            fixed=True,
            pos=(-separation / 2, 0, 0),
        )
    )

    she_entity = scene.add_entity(
        gs.morphs.URDF(
            file=str(urdf_path),
            fixed=True,
            pos=(separation / 2, 0, 0),
            euler=(0, 0, 180),
        )
    )

    scene.build()

    configure_motors(he_entity)
    configure_motors(she_entity)

    stepper = DualSimulationStepper(
        scene=scene,
        entities={"he": he_entity, "she": she_entity},
        target_fps=60.0,
    )

    he_arm = DualSimulationArm(stepper, "he", verbose=verbose)
    she_arm = DualSimulationArm(stepper, "she", verbose=verbose)

    if verbose:
        dt_ms = stepper.physics_dt * 1000
        steps = stepper.steps_per_frame
        print(f"[DualSim] Ready: 2 arms, separation={separation}m")
        print(f"[DualSim] Physics: dt={dt_ms:.2f}ms, {steps} steps/frame")

    return he_arm, she_arm
