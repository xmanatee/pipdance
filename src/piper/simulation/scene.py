"""
Genesis scene management for Piper arm simulation.

Handles scene creation, URDF loading, and motor configuration.
"""
import platform
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import genesis as gs


DEFAULT_URDF = (
    Path(__file__).parents[3]
    / "test"
    / "Piper_ros"
    / "src"
    / "piper_description"
    / "urdf"
    / "piper_description_v100.urdf"
)


def get_backend():
    """Get appropriate Genesis backend for current platform."""
    import genesis as gs

    system = platform.system()
    if system == "Darwin":
        return gs.metal
    return gs.cuda


def create_scene(show_viewer: bool = True) -> "gs.Scene":
    """
    Create and configure a Genesis scene.

    Args:
        show_viewer: Whether to show the visualization window

    Returns:
        Configured Genesis scene (not yet built)
    """
    import genesis as gs

    gs.init(backend=get_backend())

    viewer_options = gs.options.ViewerOptions(
        camera_pos=(2.0, -2.0, 1.5),
        camera_lookat=(0.0, 0.0, 0.5),
        res=(1280, 720),
        max_FPS=60,
    )

    scene = gs.Scene(
        show_viewer=show_viewer,
        viewer_options=viewer_options,
    )

    scene.add_entity(gs.morphs.Plane())
    return scene


def load_piper(scene: "gs.Scene", urdf_path: Path | None = None) -> "gs.Entity":
    """
    Load the Piper arm URDF into the scene.

    Args:
        scene: Genesis scene to add the robot to
        urdf_path: Path to URDF file (uses default if None)

    Returns:
        The loaded robot entity
    """
    import genesis as gs

    if urdf_path is None:
        urdf_path = DEFAULT_URDF

    if not urdf_path.exists():
        raise FileNotFoundError(f"URDF not found: {urdf_path}")

    entity = scene.add_entity(
        gs.morphs.URDF(file=str(urdf_path), fixed=True)
    )
    return entity


def configure_motors(entity: "gs.Entity") -> None:
    """
    Configure motor parameters for the Piper arm.

    Sets stiffness (kp), damping (kv), and force limits for
    smooth, stable position control.

    Args:
        entity: The robot entity to configure
    """
    import torch

    arm_joints = [0, 1, 2, 3, 4, 5]

    entity.set_dofs_kp(
        kp=torch.tensor([4500, 4500, 3500, 3500, 2000, 2000]),
        dofs_idx_local=arm_joints,
    )

    entity.set_dofs_kv(
        kv=torch.tensor([450, 450, 350, 350, 200, 200]),
        dofs_idx_local=arm_joints,
    )

    entity.set_dofs_force_range(
        lower=torch.tensor([-50, -50, -40, -40, -20, -20]),
        upper=torch.tensor([50, 50, 40, 40, 20, 20]),
        dofs_idx_local=arm_joints,
    )

    num_dofs = len(entity.get_dofs_position())
    if num_dofs > 6:
        gripper_joints = [6, 7]
        entity.set_dofs_kp(
            kp=torch.tensor([500, 500]),
            dofs_idx_local=gripper_joints,
        )
        entity.set_dofs_kv(
            kv=torch.tensor([50, 50]),
            dofs_idx_local=gripper_joints,
        )
