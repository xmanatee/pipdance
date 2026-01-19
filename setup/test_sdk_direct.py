#!/usr/bin/env python3
"""Test gripper using piper_sdk directly."""
from piper_sdk import C_PiperInterface_V2
import time

def main():
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()

    # Try to enable
    print("Enabling arm...")
    for i in range(100):
        result = piper.EnablePiper()
        if result:
            print(f"Enabled after {i} tries")
            break
        time.sleep(0.01)
    else:
        print("EnablePiper did not return True after 100 tries")

    # Read joint positions
    joints = piper.GetArmJointMsgs()
    print(f"Joint 1: {joints.joint_state.joint_1}")
    print(f"Joint 2: {joints.joint_state.joint_2}")
    print(f"Joint 3: {joints.joint_state.joint_3}")
    print(f"Joint 4: {joints.joint_state.joint_4}")
    print(f"Joint 5: {joints.joint_state.joint_5}")
    print(f"Joint 6: {joints.joint_state.joint_6}")

    # Read gripper
    gripper = piper.GetArmGripperMsgs()
    print(f"Gripper: {gripper}")

    # Initialize gripper like SDK demo
    print("\nInitializing gripper (mode 0x02)...")
    piper.GripperCtrl(0, 1000, 0x02, 0)
    time.sleep(0.5)

    print("Enabling gripper (mode 0x01)...")
    piper.GripperCtrl(0, 1000, 0x01, 0)
    time.sleep(0.5)

    # Test gripper movement
    print("\n=== CLOSING GRIPPER ===")
    for i in range(600):  # 3 seconds at 200Hz
        piper.GripperCtrl(0, 1000, 0x01, 0)
        time.sleep(0.005)

    gripper = piper.GetArmGripperMsgs()
    print(f"After close: {gripper}")

    print("\n=== OPENING GRIPPER ===")
    for i in range(600):  # 3 seconds at 200Hz
        piper.GripperCtrl(50000, 1000, 0x01, 0)  # 50mm open
        time.sleep(0.005)

    gripper = piper.GetArmGripperMsgs()
    print(f"After open: {gripper}")

    print("\nDone!")

if __name__ == "__main__":
    main()
