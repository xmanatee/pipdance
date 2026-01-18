#!/usr/bin/env python3
"""Movement test for Waveshare adapter - moves J6 by 5 degrees."""
import sys
import time
import threading
sys.path.insert(0, '/home/pi3/pipdance/src')

import can
from piper.can import WaveshareBus, find_waveshare_port

def read_joints(bus, timeout=1.0):
    """Read joint positions with threaded reader."""
    joints = [None] * 6
    received = set()

    start = time.time()
    while time.time() - start < timeout and len(received) < 3:
        msg = bus.recv(timeout=0.1)
        if msg and 0x2A5 <= msg.arbitration_id <= 0x2A7:
            idx = (msg.arbitration_id - 0x2A5) * 2
            if len(msg.data) >= 8:
                j1 = int.from_bytes(msg.data[0:4], 'big', signed=True) / 1000.0
                j2 = int.from_bytes(msg.data[4:8], 'big', signed=True) / 1000.0
                joints[idx] = j1
                if idx + 1 < 6:
                    joints[idx + 1] = j2
                received.add(msg.arbitration_id)

    return joints if len(received) >= 3 else None

def send_command_with_feedback(bus, target_joints_deg, duration=2.0, speed_pct=30):
    """Send commands while reading feedback in background."""
    pos_mdeg = [int(j * 1000) for j in target_joints_deg]
    final_joints = [0.0] * 6
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            msg = bus.recv(timeout=0.05)
            if msg and 0x2A5 <= msg.arbitration_id <= 0x2A7:
                idx = (msg.arbitration_id - 0x2A5) * 2
                if len(msg.data) >= 8:
                    j1 = int.from_bytes(msg.data[0:4], 'big', signed=True) / 1000.0
                    j2 = int.from_bytes(msg.data[4:8], 'big', signed=True) / 1000.0
                    final_joints[idx] = j1
                    if idx + 1 < 6:
                        final_joints[idx + 1] = j2

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    start = time.time()
    while time.time() - start < duration:
        # Enable
        bus.send(can.Message(
            arbitration_id=0x471,
            data=bytes([0x07, 0x02, 0, 0, 0, 0, 0, 0]),
            is_extended_id=False,
        ))
        # Motion ctrl
        bus.send(can.Message(
            arbitration_id=0x151,
            data=bytes([0x01, 0x01, speed_pct, 0, 0, 0, 0, 0]),
            is_extended_id=False,
        ))
        # Joint positions
        for i in range(3):
            j1 = pos_mdeg[i * 2]
            j2 = pos_mdeg[i * 2 + 1] if i * 2 + 1 < 6 else 0
            data = j1.to_bytes(4, 'big', signed=True) + j2.to_bytes(4, 'big', signed=True)
            bus.send(can.Message(
                arbitration_id=0x155 + i,
                data=data,
                is_extended_id=False,
            ))
        time.sleep(0.005)

    stop.set()
    reader_thread.join(timeout=0.5)

    return final_joints

def main():
    port = find_waveshare_port()
    if not port:
        print("ERROR: No Waveshare adapter found")
        return

    print(f"Using port: {port}")
    bus = WaveshareBus(channel=port, bitrate=1000000)

    # Initial enable sequence
    print("\nInitializing arm...")
    for _ in range(10):
        bus.send(can.Message(arbitration_id=0x471, data=bytes([0x07, 0x02, 0,0,0,0,0,0]), is_extended_id=False))
        bus.send(can.Message(arbitration_id=0x151, data=bytes([0x01, 0x01, 0x32, 0,0,0,0,0]), is_extended_id=False))
        time.sleep(0.02)
    time.sleep(0.1)

    # Read initial position
    print("\n=== Reading initial position ===")
    initial = read_joints(bus)
    if not initial:
        print("ERROR: Failed to read initial position")
        bus.shutdown()
        return

    print("Initial joints:")
    for i, j in enumerate(initial):
        print(f"  J{i+1}: {j:.2f}°")

    # Calculate target: move J6 by +5 degrees
    target = list(initial)
    target[5] = initial[5] + 5.0  # J6 += 5 degrees

    print(f"\n=== Moving J6 from {initial[5]:.2f}° to {target[5]:.2f}° ===")
    print("(This should be a ~5 degree movement)")

    # Send movement command
    final = send_command_with_feedback(bus, target, duration=2.0, speed_pct=30)

    print("\n=== Final position ===")
    print("Final joints:")
    for i, j in enumerate(final):
        print(f"  J{i+1}: {j:.2f}°")

    # Check movement
    delta = final[5] - initial[5]
    print(f"\n=== Result ===")
    print(f"J6 movement: {delta:.2f}° (expected: ~5°)")

    if abs(delta - 5.0) < 2.0:
        print("SUCCESS: Movement detected and verified!")
    elif abs(delta) > 0.5:
        print(f"PARTIAL: Movement detected but not exact ({delta:.2f}° instead of 5°)")
    else:
        print("ISSUE: No significant movement detected")

    # Now move back
    print(f"\n=== Moving J6 back to {initial[5]:.2f}° ===")
    final2 = send_command_with_feedback(bus, initial, duration=2.0, speed_pct=30)

    print("Final joints after return:")
    for i, j in enumerate(final2):
        print(f"  J{i+1}: {j:.2f}°")

    delta2 = final2[5] - initial[5]
    print(f"\nJ6 difference from initial: {delta2:.2f}° (should be ~0°)")

    bus.shutdown()
    print("\n=== Test complete ===")

if __name__ == "__main__":
    main()
