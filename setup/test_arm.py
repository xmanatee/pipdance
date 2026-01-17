#!/usr/bin/env python3
"""
Test Piper arm connection and movement.

WARNING: Arm will move! Ensure clear space around it.
"""
import sys
import time
import math

# Auto-detect: try slcan0 first, then can0
CAN_PORTS = ["slcan0", "can0"]
MOVE_DEGREES = 15

def deg2rad(d): return d * math.pi / 180
def rad2deg(r): return r * 180 / math.pi

def find_can_port():
    """Find working CAN port."""
    import can
    for port in CAN_PORTS:
        try:
            bus = can.interface.Bus(channel=port, interface="socketcan")
            bus.shutdown()
            return port
        except:
            continue
    return None

print("=== Piper Arm Test ===")
print(f"Test move: {MOVE_DEGREES}°")
print()
print("WARNING: Arm will move! Ensure clear space.")
print()

# Step 1: Import
print("[1/6] Importing piper_control...")
try:
    from piper_control import piper_interface, piper_init
    print("      OK")
except ImportError as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 2: Find CAN port
print("[2/6] Finding CAN interface...")
can_port = find_can_port()
if not can_port:
    print(f"      FAIL: No interface found (tried {CAN_PORTS})")
    print("      Fix: Run ./can_setup.sh")
    sys.exit(1)
print(f"      Using: {can_port}")

# Step 3: Connect
print(f"[3/6] Connecting to arm...")
try:
    robot = piper_interface.PiperInterface(can_port=can_port)
    print("      OK")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 4: Initialize
print("[4/6] Initializing arm (enabling motors)...")
try:
    piper_init.reset_arm(
        robot,
        arm_controller=piper_interface.ArmController.POSITION_VELOCITY,
        move_mode=piper_interface.MoveMode.JOINT,
    )
    piper_init.reset_gripper(robot)
    print("      OK")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 5: Read state
print("[5/6] Reading joint positions...")
try:
    joints = robot.get_joint_positions()
    print("      Current positions (degrees):")
    for i, j in enumerate(joints):
        print(f"        Joint {i+1}: {rad2deg(j):+7.2f}°")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 6: Move and gripper test
print(f"[6/6] Motion test...")
try:
    original = list(joints)

    # Move joint 3
    target = list(joints)
    target[2] += deg2rad(MOVE_DEGREES)
    print(f"      Moving Joint 3: {rad2deg(joints[2]):+.1f}° → {rad2deg(target[2]):+.1f}°")
    robot.command_joint_positions(target)
    time.sleep(2.0)

    # Move back
    print(f"      Moving back...")
    robot.command_joint_positions(original)
    time.sleep(2.0)

    # Gripper
    print("      Closing gripper...")
    robot.command_gripper_position(1.0)
    time.sleep(1.5)
    print("      Opening gripper...")
    robot.command_gripper_position(0.0)
    time.sleep(1.5)

    print("      OK")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

try:
    robot.stop()
except:
    pass

print()
print("=== Test Complete ===")
