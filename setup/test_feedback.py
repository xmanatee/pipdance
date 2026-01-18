#!/usr/bin/env python3
"""Diagnostic test for Waveshare CAN feedback reading."""
import sys
import time
import threading
sys.path.insert(0, '/home/pi3/pipdance/src')

from piper.can import WaveshareBus, find_waveshare_port

def main():
    port = find_waveshare_port()
    if not port:
        print("ERROR: No Waveshare adapter found")
        return

    print(f"Using port: {port}")
    bus = WaveshareBus(channel=port, bitrate=1000000)

    joints = [0.0] * 6
    msg_count = [0]

    print("\n=== Reading feedback for 3 seconds ===")
    print("(Watching for CAN IDs 0x2A5-0x2A7)\n")

    start = time.time()
    while time.time() - start < 3.0:
        msg = bus.recv(timeout=0.1)
        if msg:
            if 0x2A5 <= msg.arbitration_id <= 0x2A7:
                idx = (msg.arbitration_id - 0x2A5) * 2
                if len(msg.data) >= 8:
                    j1 = int.from_bytes(msg.data[0:4], 'big', signed=True) / 1000.0
                    j2 = int.from_bytes(msg.data[4:8], 'big', signed=True) / 1000.0
                    joints[idx] = j1
                    if idx + 1 < 6:
                        joints[idx + 1] = j2
                msg_count[0] += 1
                print(f"  ID=0x{msg.arbitration_id:03X} -> J{idx+1}={j1:.1f}° J{idx+2}={j2:.1f}°")
            else:
                print(f"  ID=0x{msg.arbitration_id:03X} (other)")

    print(f"\nReceived {msg_count[0]} joint feedback messages")
    print(f"\nFinal joint positions:")
    for i, j in enumerate(joints):
        print(f"  J{i+1}: {j:.2f}°")

    # Now test with command sending
    print("\n=== Testing feedback during commands ===")
    print("Sending enable + motion commands for 2 seconds...\n")

    stop = threading.Event()
    feedback_joints = [0.0] * 6
    feedback_count = [0]

    def reader():
        while not stop.is_set():
            msg = bus.recv(timeout=0.05)
            if msg and 0x2A5 <= msg.arbitration_id <= 0x2A7:
                idx = (msg.arbitration_id - 0x2A5) * 2
                if len(msg.data) >= 8:
                    j1 = int.from_bytes(msg.data[0:4], 'big', signed=True) / 1000.0
                    j2 = int.from_bytes(msg.data[4:8], 'big', signed=True) / 1000.0
                    feedback_joints[idx] = j1
                    if idx + 1 < 6:
                        feedback_joints[idx + 1] = j2
                feedback_count[0] += 1

    # Start reader thread
    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    # Send commands (hold current position)
    import can
    pos_mdeg = [int(j * 1000) for j in joints]

    start = time.time()
    while time.time() - start < 2.0:
        # Enable
        bus.send(can.Message(
            arbitration_id=0x471,
            data=bytes([0x07, 0x02, 0, 0, 0, 0, 0, 0]),
            is_extended_id=False,
        ))
        # Motion ctrl
        bus.send(can.Message(
            arbitration_id=0x151,
            data=bytes([0x01, 0x01, 30, 0, 0, 0, 0, 0]),
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

    print(f"Received {feedback_count[0]} feedback messages during commands")
    print(f"\nFeedback joint positions:")
    for i, j in enumerate(feedback_joints):
        print(f"  J{i+1}: {j:.2f}°")

    bus.shutdown()
    print("\n=== Test complete ===")

if __name__ == "__main__":
    main()
