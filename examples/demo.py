#!/usr/bin/env python3
"""
Piper Arm Demo

Demonstrates basic arm control with auto-detection.
"""
import sys

# Add src to path for imports
sys.path.insert(0, '/home/pi3/pipdance/src')

from piper import PiperArm


def main():
    print("=== Piper Arm Demo ===")
    print()
    print("WARNING: Arm will move! Ensure clear space.")
    print()

    with PiperArm() as arm:  # auto-detects adapter
        arm.print_state()
        print()

        print("--- Moving Joint 2 by +20° ---")
        arm.move_joint_by(1, 20)
        arm.print_state()
        print()

        print("--- Moving Joint 2 back (-20°) ---")
        arm.move_joint_by(1, -20)
        print()

        print("--- Moving Joint 4 by +30° ---")
        arm.move_joint_by(3, 30)
        print()

        print("--- Moving Joint 4 back (-30°) ---")
        arm.move_joint_by(3, -30)
        print()

        print("--- Gripper test ---")
        arm.close_gripper()
        arm.open_gripper()

    print()
    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
