#!/usr/bin/env python3
"""
Test gripper control following the exact SDK pattern.

Based on piper_sdk analysis:
1. Motor enable (0x471): byte0=motor_num (0xFF=all, 7=gripper), byte1=enable_flag (0x02=enable)
2. Gripper ctrl (0x159): bytes0-3=position (0.001mm), bytes4-5=effort (unsigned), byte6=mode, byte7=set_zero

SDK gripper demo pattern:
1. EnablePiper() - enable all motors
2. GripperCtrl(0, 1000, 0x02, 0) - init with mode 0x02 (disable + clear error)
3. GripperCtrl(0, 1000, 0x01, 0) - enable with mode 0x01
4. Loop: GripperCtrl(position, 1000, 0x01, 0)
"""
import sys
import time
import can
sys.path.insert(0, '/home/pi3/pipdance/src')

from piper.adapters.waveshare import WavesharePiperArm

def send_motor_enable(bus, motor_num=0xFF, enable=True):
    """Send motor enable command. motor_num: 1-6=joints, 7=gripper, 0xFF=all"""
    enable_flag = 0x02 if enable else 0x01
    bus.send(can.Message(
        arbitration_id=0x471,
        data=bytes([motor_num, enable_flag, 0, 0, 0, 0, 0, 0]),
        is_extended_id=False,
    ))

def send_gripper_ctrl(bus, position_um, effort=1000, mode=0x01, set_zero=0x00):
    """Send gripper control. position_um in 0.001mm, effort in 0.001N·m (0-5000)"""
    pos_bytes = position_um.to_bytes(4, 'big', signed=True)
    effort_bytes = effort.to_bytes(2, 'big', signed=False)  # UNSIGNED
    bus.send(can.Message(
        arbitration_id=0x159,
        data=pos_bytes + effort_bytes + bytes([mode, set_zero]),
        is_extended_id=False,
    ))

def send_motion_ctrl(bus, ctrl_mode=0x01, move_mode=0x01, speed=50):
    """Send motion control command."""
    bus.send(can.Message(
        arbitration_id=0x151,
        data=bytes([ctrl_mode, move_mode, speed, 0, 0, 0, 0, 0]),
        is_extended_id=False,
    ))

def main():
    arm = WavesharePiperArm(port="auto", verbose=True)
    arm.connect()

    print(f"Initial gripper: {arm.state.gripper:.3f}")

    # Step 1: Enable all motors (like SDK EnablePiper)
    print("\n1. Enabling all motors...")
    for _ in range(50):
        send_motor_enable(arm._bus, 0xFF, True)  # Enable all
        send_motion_ctrl(arm._bus)
        time.sleep(0.01)

    # Step 2: Initialize gripper with mode 0x02 (like SDK GripperCtrl(0, 1000, 0x02, 0))
    print("2. Initializing gripper (mode 0x02 = disable + clear error)...")
    for _ in range(50):
        send_motor_enable(arm._bus, 0xFF, True)
        send_motion_ctrl(arm._bus)
        send_gripper_ctrl(arm._bus, 0, 1000, mode=0x02)
        time.sleep(0.01)

    # Step 3: Enable gripper with mode 0x01 (like SDK GripperCtrl(0, 1000, 0x01, 0))
    print("3. Enabling gripper (mode 0x01 = enable)...")
    for _ in range(50):
        send_motor_enable(arm._bus, 0xFF, True)
        send_motion_ctrl(arm._bus)
        send_gripper_ctrl(arm._bus, 0, 1000, mode=0x01)
        time.sleep(0.01)

    print(f"After init: gripper={arm.state.gripper:.3f}")

    # Step 4: Close gripper (position=0)
    print("\n>>> CLOSING GRIPPER (5 seconds)...")
    start = time.time()
    while time.time() - start < 5.0:
        send_motor_enable(arm._bus, 0xFF, True)
        send_motion_ctrl(arm._bus)
        send_gripper_ctrl(arm._bus, 0, 1000, mode=0x01)  # pos=0 (closed)
        time.sleep(0.005)

    print(f"After close: gripper={arm.state.gripper:.3f}")

    # Step 5: Open gripper (position=50000 = 50mm, like SDK demo)
    print("\n>>> OPENING GRIPPER (5 seconds)...")
    start = time.time()
    while time.time() - start < 5.0:
        send_motor_enable(arm._bus, 0xFF, True)
        send_motion_ctrl(arm._bus)
        send_gripper_ctrl(arm._bus, 50000, 1000, mode=0x01)  # pos=50mm
        time.sleep(0.005)

    print(f"After open: gripper={arm.state.gripper:.3f}")

    arm.disconnect()
    print("\nDone - did the gripper open and close?")

if __name__ == "__main__":
    main()
