import genesis as gs
import numpy as np
import torch

def main():
    # Initialize using Metal backend for macOS Apple Silicon
    gs.init(backend=gs.metal) 

    # Corrected Scene initialization
    scene = gs.Scene(
        show_viewer    = True, # Replaced 'viewer' with 'show_viewer'
        viewer_options = gs.options.ViewerOptions(
            camera_pos    = (2.0, -2.0, 1.5),
            camera_lookat = (0.0, 0.0, 0.5),
            res           = (1280, 720),
            max_FPS       = 60,
        ),
    )

    # Add a simple plane and the built-in Franka robot for testing
    # (Since we haven't linked your Piper URDF folder yet)
    scene.add_entity(gs.morphs.Plane())
    piper = scene.add_entity(gs.morphs.URDF(file='./Piper_ros/src/piper_description/urdf/piper_description_v100.urdf', fixed=True))
    piper2 = scene.add_entity(gs.morphs.URDF(file='./Piper_ros/src/piper_description/urdf/piper_description_v100.urdf', fixed=True))

    # Build and Run
    scene.build()
    # 1. Identify your joint indices (usually [0, 1, 2, 3, 4, 5] for Piper)
    arm_joints = [0, 1, 2, 3, 4, 5]

    # 2. Set the "Strength" of the motors (KP = Stiffness, KV = Damping)
    # These values are good starting points for the Piper arm
    piper.set_dofs_kp(kp=torch.tensor([4500, 4500, 3500, 3500, 2000, 2000]), dofs_idx_local=arm_joints)
    piper.set_dofs_kv(kv=torch.tensor([450, 450, 350, 350, 200, 200]), dofs_idx_local=arm_joints)

    # 3. Set the force limit (Safety)
    piper.set_dofs_force_range(
        lower = torch.tensor([-50, -50, -40, -40, -20, -20]),
        upper = torch.tensor([50, 50, 40, 40, 20, 20]),
        dofs_idx_local = arm_joints
    )

    # Simple loop to keep simulation alive
    t = 0
    while True:
        # Use a sine wave to create a smooth back-and-forth motion
        angle = 0.5 * np.sin(t) 
        targets = torch.tensor([angle, 0, 0, 0, 0, 0], device='cpu')
        
        piper.control_dofs_position(targets, dofs_idx_local=arm_joints)
        scene.step()
        t += 0.01

if __name__ == "__main__":
    main()

