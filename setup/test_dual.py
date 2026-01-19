#!/usr/bin/env python3
"""
Quick dual-arm test for Waveshare adapters.

Tests both arms can connect, read state, and make small movements.
"""
import sys
import time

sys.path.insert(0, '/home/pi3/pipdance/src')

from piper import create_arm
from piper.can import find_all_waveshare_ports


def test_dual_waveshare():
    """Test both Waveshare adapters."""
    print("=" * 50)
    print("Dual-Arm Waveshare Test")
    print("=" * 50)
    print()

    # Detect ports
    print("[1/4] Detecting Waveshare ports...")
    ports = find_all_waveshare_ports()
    print(f"      Found: {ports}")

    if len(ports) < 2:
        print(f"\n[FAIL] Need 2 Waveshare adapters, found {len(ports)}")
        print("       Check: ls /dev/ttyUSB*")
        return False

    he_port, she_port = ports[0], ports[1]
    print(f"      he:  {he_port}")
    print(f"      she: {she_port}")
    print()

    # Connect both arms
    print("[2/4] Connecting to both arms...")
    try:
        he_arm = create_arm(adapter="waveshare", can_port=he_port)
        he_arm._connect()
        print(f"      [OK] he arm connected")
    except Exception as e:
        print(f"      [FAIL] he arm: {e}")
        return False

    try:
        she_arm = create_arm(adapter="waveshare", can_port=she_port)
        she_arm._connect()
        print(f"      [OK] she arm connected")
    except Exception as e:
        print(f"      [FAIL] she arm: {e}")
        he_arm._disconnect()
        return False
    print()

    # Read initial state
    print("[3/4] Reading arm states...")
    try:
        print("      --- HE ARM ---")
        he_arm.print_state()
        he_j2_initial = he_arm._joint_positions[1] if he_arm._joint_positions else None

        print("      --- SHE ARM ---")
        she_arm.print_state()
        she_j2_initial = she_arm._joint_positions[1] if she_arm._joint_positions else None
    except Exception as e:
        print(f"      [FAIL] State read: {e}")
        he_arm._disconnect()
        she_arm._disconnect()
        return False
    print()

    # Small movement test
    print("[4/4] Movement test (J2 +5° then -5°)...")
    print("      WARNING: Both arms will move slightly!")
    print()

    try:
        print("      Moving both arms J2 +5°...")
        he_arm.move_joint_by(1, 5)
        she_arm.move_joint_by(1, 5)
        time.sleep(1.5)

        print("      Reading positions...")
        he_arm.print_state()
        she_arm.print_state()

        print("      Moving both arms J2 -5°...")
        he_arm.move_joint_by(1, -5)
        she_arm.move_joint_by(1, -5)
        time.sleep(1.5)

        print("      Final positions:")
        he_arm.print_state()
        she_arm.print_state()

        print("      [OK] Movement test complete")
    except Exception as e:
        print(f"      [FAIL] Movement: {e}")
        he_arm._disconnect()
        she_arm._disconnect()
        return False

    # Cleanup
    he_arm._disconnect()
    she_arm._disconnect()

    print()
    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_dual_waveshare()
    sys.exit(0 if success else 1)
