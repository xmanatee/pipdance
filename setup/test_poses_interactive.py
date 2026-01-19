#!/usr/bin/env python3
"""Interactive pose testing - shows each pose and waits for feedback."""
import sys
import math
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from piper import create_arm

POSES_FILE = str(Path(__file__).resolve().parent.parent / "scripts" / "poses.json")

def load_poses():
    with open(POSES_FILE) as f:
        data = json.load(f)
    poses = {}
    for scene in data.get("scenes", []):
        name = scene["name"]
        joints = scene["joint_positions"]
        joints_deg = [float(joints[j]) for j in ["J1", "J2", "J3", "J4", "J5", "J6"]]
        intended = scene.get("intended_look", "")
        poses[name] = {"joints_deg": joints_deg, "intended": intended}
    return poses

def main():
    poses = load_poses()
    pose_names = list(poses.keys())

    print("=" * 60)
    print("  INTERACTIVE POSE TEST")
    print("  Testing each pose one by one")
    print("=" * 60)
    print(f"\nLoaded {len(poses)} poses\n")

    with create_arm(verbose=False) as arm:
        print("[Connected]\n")

        for i, name in enumerate(pose_names):
            pose = poses[name]
            joints_deg = pose["joints_deg"]
            intended = pose["intended"]

            print("-" * 60)
            print(f"POSE {i+1}/{len(poses)}: {name}")
            print(f"Intended: {intended}")
            print(f"Joints: J1={joints_deg[0]:.0f} J2={joints_deg[1]:.0f} J3={joints_deg[2]:.0f} J4={joints_deg[3]:.0f} J5={joints_deg[4]:.0f} J6={joints_deg[5]:.0f}")
            print("-" * 60)

            # Move to pose
            joints_rad = [math.radians(d) for d in joints_deg]
            arm.move_joints(joints_rad, wait=0)

            # Signal ready
            print(f"\n>>> NOW SHOWING: {name}")
            print(">>> POSE_READY")
            sys.stdout.flush()

            # Wait for input
            response = input("\nPress Enter for next pose (or type feedback): ").strip()

            if response.lower() in ['q', 'quit', 'exit']:
                print("\nStopping early.")
                break
            elif response:
                print(f"[Feedback for {name}]: {response}")

        print("\n" + "=" * 60)
        print("  TEST COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    main()
