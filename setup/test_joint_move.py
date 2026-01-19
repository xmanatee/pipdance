#!/usr/bin/env python3
"""Test joint movement using piper_sdk directly."""
from piper_sdk import C_PiperInterface_V2
import time
import math

def main():
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()

    # Enable
    print("Enabling arm...")
    for i in range(100):
        if piper.EnablePiper():
            print(f"Enabled after {i} tries")
            break
        time.sleep(0.01)

    # Set motion control mode
    piper.MotionCtrl_2(0x01, 0x01, 50)  # CAN ctrl, joint mode, 50% speed
    time.sleep(0.5)

    # Read current position
    joints = piper.GetArmJointMsgs()
    j6_initial = joints.joint_state.joint_6
    print(f"Initial J6: {j6_initial} ({j6_initial/1000:.1f} deg)")

    # Move J6 by +5 degrees (5000 mdeg)
    target = j6_initial + 5000
    print(f"\nMoving J6 to {target} ({target/1000:.1f} deg)...")

    # Send joint command for 2 seconds
    for _ in range(400):  # 2 sec at 200Hz
        piper.JointCtrl(
            joints.joint_state.joint_1,
            joints.joint_state.joint_2,
            joints.joint_state.joint_3,
            joints.joint_state.joint_4,
            joints.joint_state.joint_5,
            target
        )
        time.sleep(0.005)

    joints = piper.GetArmJointMsgs()
    j6_after = joints.joint_state.joint_6
    print(f"After move J6: {j6_after} ({j6_after/1000:.1f} deg)")
    print(f"Movement: {(j6_after - j6_initial)/1000:.1f} deg")

    # Move back
    print(f"\nMoving J6 back to {j6_initial}...")
    for _ in range(400):
        piper.JointCtrl(
            joints.joint_state.joint_1,
            joints.joint_state.joint_2,
            joints.joint_state.joint_3,
            joints.joint_state.joint_4,
            joints.joint_state.joint_5,
            j6_initial
        )
        time.sleep(0.005)

    joints = piper.GetArmJointMsgs()
    j6_final = joints.joint_state.joint_6
    print(f"Final J6: {j6_final} ({j6_final/1000:.1f} deg)")

    print("\nDone!")

if __name__ == "__main__":
    main()
