#!/usr/bin/env python3
"""Visual test - moves each joint and gripper one by one."""
import sys
import math
import time
sys.path.insert(0, '/home/pi3/pipdance/src')

from piper.adapters.waveshare import WavesharePiperArm

# Movement amount in degrees (10% of typical ~100° range)
MOVE_DEG = 10.0
HOLD_TIME = 1.0  # seconds to hold at moved position

def main():
    print("=" * 50)
    print("  VISUAL TEST - Moving each joint one by one")
    print("=" * 50)
    print()

    arm = WavesharePiperArm(port="auto", verbose=False)
    arm.connect()
    print("[Connected]\n")

    # Get initial position
    initial = list(arm.state.joints)
    initial_gripper = arm.state.gripper

    print("Initial position:")
    for i, j in enumerate(initial):
        print(f"  J{i+1}: {math.degrees(j):+.1f}°")
    print(f"  Gripper: {initial_gripper:.2f}")
    print()

    # Test each joint
    for joint_idx in range(6):
        joint_name = f"J{joint_idx + 1}"
        current_deg = math.degrees(initial[joint_idx])
        target_deg = current_deg + MOVE_DEG

        print(f"--- {joint_name}: {current_deg:+.1f}° → {target_deg:+.1f}° ---")

        # Move to target
        target = list(initial)
        target[joint_idx] = math.radians(target_deg)
        arm.move_joints(target, wait=0)

        # Hold
        print(f"    Holding for {HOLD_TIME}s...")
        time.sleep(HOLD_TIME)

        # Read position
        pos = arm.state.joints
        actual = math.degrees(pos[joint_idx])
        print(f"    Actual: {actual:+.1f}°")

        # Move back
        print(f"    Returning to {current_deg:+.1f}°...")
        arm.move_joints(initial, wait=0)
        time.sleep(0.5)  # Brief pause between joints
        print()

    # Test gripper
    print("--- Gripper ---")

    # Close gripper by 10%
    gripper_target = min(1.0, initial_gripper + 0.1)
    print(f"    Closing: {initial_gripper:.2f} → {gripper_target:.2f}")
    arm.gripper(gripper_target, wait=0)
    time.sleep(HOLD_TIME)

    # Open back
    print(f"    Opening back to {initial_gripper:.2f}")
    arm.gripper(initial_gripper, wait=0)
    time.sleep(0.5)
    print()

    # Final position check
    print("Final position:")
    final = arm.state.joints
    for i, j in enumerate(final):
        diff = math.degrees(j) - math.degrees(initial[i])
        print(f"  J{i+1}: {math.degrees(j):+.1f}° (diff: {diff:+.2f}°)")
    print()

    arm.disconnect()
    print("=" * 50)
    print("  VISUAL TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
