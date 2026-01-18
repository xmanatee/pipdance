#!/usr/bin/env python3
"""Test the WavesharePiperArm adapter with a small movement."""
import sys
import math
sys.path.insert(0, '/home/pi3/pipdance/src')

from piper.adapters.waveshare import WavesharePiperArm

def main():
    print("=== Testing WavesharePiperArm Adapter ===\n")

    arm = WavesharePiperArm(port="auto", verbose=True)

    print("Connecting...")
    arm.connect()

    print("\n--- Initial Position ---")
    joints = arm.state.joints
    joints_deg = [math.degrees(j) for j in joints]
    for i, j in enumerate(joints_deg):
        print(f"  J{i+1}: {j:.2f}°")

    # Move J6 by +5 degrees
    target = list(joints)
    target[5] = joints[5] + math.radians(5)

    print(f"\n--- Moving J6 from {joints_deg[5]:.2f}° to {math.degrees(target[5]):.2f}° ---")
    arm.move_joints(target, wait=0)  # Don't add extra wait, _send_joint_command already waits

    print("\n--- Position After Move ---")
    new_joints = arm.state.joints
    new_joints_deg = [math.degrees(j) for j in new_joints]
    for i, j in enumerate(new_joints_deg):
        print(f"  J{i+1}: {j:.2f}°")

    delta = new_joints_deg[5] - joints_deg[5]
    print(f"\nJ6 movement: {delta:.2f}° (expected: ~5°)")

    # Move back
    print(f"\n--- Moving J6 back to {joints_deg[5]:.2f}° ---")
    arm.move_joints(joints, wait=0)

    print("\n--- Final Position ---")
    final_joints = arm.state.joints
    final_joints_deg = [math.degrees(j) for j in final_joints]
    for i, j in enumerate(final_joints_deg):
        print(f"  J{i+1}: {j:.2f}°")

    delta2 = final_joints_deg[5] - joints_deg[5]
    print(f"\nJ6 difference from initial: {delta2:.2f}° (should be ~0°)")

    arm.disconnect()
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
