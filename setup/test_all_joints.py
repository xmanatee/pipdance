#!/usr/bin/env python3
"""Test all 6 joints one by one using piper_sdk."""
from piper_sdk import C_PiperInterface_V2
import time

MOVE_DEG = 10  # degrees to move each joint
MOVE_MDEG = MOVE_DEG * 1000

def main():
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()

    print("=" * 50)
    print("  TESTING ALL 6 JOINTS")
    print("=" * 50)

    # Enable
    print("\nEnabling arm...")
    for i in range(100):
        if piper.EnablePiper():
            print(f"Enabled after {i} tries")
            break
        time.sleep(0.01)

    # Set motion control
    piper.MotionCtrl_2(0x01, 0x01, 30)  # CAN ctrl, joint mode, 30% speed
    time.sleep(0.3)

    # Get initial positions
    joints = piper.GetArmJointMsgs()
    initial = [
        joints.joint_state.joint_1,
        joints.joint_state.joint_2,
        joints.joint_state.joint_3,
        joints.joint_state.joint_4,
        joints.joint_state.joint_5,
        joints.joint_state.joint_6,
    ]
    print(f"\nInitial positions (deg):")
    for i, j in enumerate(initial):
        print(f"  J{i+1}: {j/1000:.1f}°")

    # Test each joint
    for joint_idx in range(6):
        joint_name = f"J{joint_idx + 1}"
        current = initial[joint_idx]
        target = current + MOVE_MDEG

        print(f"\n--- {joint_name}: {current/1000:.1f}° → {target/1000:.1f}° ---")

        # Build target positions (only change one joint)
        targets = list(initial)
        targets[joint_idx] = target

        # Move to target
        for _ in range(300):  # 1.5 sec
            piper.JointCtrl(*targets)
            time.sleep(0.005)

        # Read position
        joints = piper.GetArmJointMsgs()
        actual = [
            joints.joint_state.joint_1,
            joints.joint_state.joint_2,
            joints.joint_state.joint_3,
            joints.joint_state.joint_4,
            joints.joint_state.joint_5,
            joints.joint_state.joint_6,
        ][joint_idx]
        moved = (actual - current) / 1000
        print(f"    Moved: {moved:.1f}° (expected: {MOVE_DEG}°)")

        # Move back
        print(f"    Returning...")
        for _ in range(300):
            piper.JointCtrl(*initial)
            time.sleep(0.005)

    # Final check
    print("\n" + "=" * 50)
    joints = piper.GetArmJointMsgs()
    final = [
        joints.joint_state.joint_1,
        joints.joint_state.joint_2,
        joints.joint_state.joint_3,
        joints.joint_state.joint_4,
        joints.joint_state.joint_5,
        joints.joint_state.joint_6,
    ]
    print("Final positions vs initial:")
    all_ok = True
    for i in range(6):
        diff = (final[i] - initial[i]) / 1000
        status = "OK" if abs(diff) < 1.0 else "DRIFT"
        if abs(diff) >= 1.0:
            all_ok = False
        print(f"  J{i+1}: diff={diff:+.1f}° [{status}]")

    print("=" * 50)
    print("  ALL JOINTS TEST " + ("PASSED" if all_ok else "FAILED"))
    print("=" * 50)

if __name__ == "__main__":
    main()
