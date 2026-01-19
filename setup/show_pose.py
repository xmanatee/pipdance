#!/usr/bin/env python3
"""Show a single pose by name."""
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
    if len(sys.argv) < 2:
        poses = load_poses()
        print("Available poses:")
        for name in poses.keys():
            print(f"  - {name}")
        print("\nUsage: python show_pose.py <pose_name>")
        return

    pose_name = sys.argv[1]
    poses = load_poses()

    if pose_name not in poses:
        print(f"Unknown pose: {pose_name}")
        print(f"Available: {', '.join(poses.keys())}")
        return

    pose = poses[pose_name]
    joints_deg = pose["joints_deg"]
    intended = pose["intended"]

    print(f"Pose: {pose_name}")
    print(f"Intended: {intended}")
    print(f"Joints: J1={joints_deg[0]:.0f} J2={joints_deg[1]:.0f} J3={joints_deg[2]:.0f} J4={joints_deg[3]:.0f} J5={joints_deg[4]:.0f} J6={joints_deg[5]:.0f}")

    with create_arm(verbose=False) as arm:
        joints_rad = [math.radians(d) for d in joints_deg]
        arm.move_joints(joints_rad, wait=0)
        print(f"\n>>> Now showing: {pose_name}")

if __name__ == "__main__":
    main()
