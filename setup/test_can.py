#!/usr/bin/env python3
"""Test CAN bus connection."""
import sys
import time

# Try slcan0 first (serial adapter), then can0 (native)
CAN_INTERFACES = ["slcan0", "can0"]

print("=== CAN Bus Test ===")
print()

# Test 1: Import
print("[1/3] Importing python-can...")
try:
    import can
    print(f"      Version: {can.__version__}")
except ImportError as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Test 2: Connect
print("[2/3] Connecting to CAN interface...")
bus = None
interface = None
for iface in CAN_INTERFACES:
    try:
        bus = can.interface.Bus(channel=iface, interface="socketcan")
        interface = iface
        print(f"      OK: {iface}")
        break
    except Exception:
        continue

if not bus:
    print(f"      FAIL: No interface found")
    print(f"      Tried: {CAN_INTERFACES}")
    print("      Fix: Run ./can_setup.sh")
    sys.exit(1)

# Test 3: Listen for frames
print(f"[3/3] Listening for CAN frames on {interface} (3s)...")
print("      (Arm must be powered on)")
start = time.time()
count = 0
while time.time() - start < 3.0:
    msg = bus.recv(timeout=0.1)
    if msg:
        count += 1
        if count <= 3:
            print(f"      Frame {count}: ID=0x{msg.arbitration_id:03X} data={msg.data.hex()}")

bus.shutdown()

print()
if count > 0:
    print(f"=== OK: {count} frames received on {interface} ===")
else:
    print(f"=== WARNING: No frames on {interface} (arm off?) ===")
