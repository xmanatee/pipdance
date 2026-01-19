#!/usr/bin/env python3
"""
Unified test script for Piper arm.

Tests adapter detection and basic arm functionality.
"""
import sys
import argparse

# Add src to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from piper import PiperArm, detect_adapter
from piper.adapters.standard import find_socketcan_port
from piper.can import find_waveshare_port


def test_detection():
    """Test adapter detection."""
    print("=== Adapter Detection ===")
    print()

    # Check socketcan
    socketcan_port = find_socketcan_port()
    if socketcan_port:
        print(f"[OK] Standard socketcan found: {socketcan_port}")
    else:
        print("[--] Standard socketcan: not found")

    # Check Waveshare
    waveshare_port = find_waveshare_port()
    if waveshare_port:
        print(f"[OK] Waveshare USB-CAN-A found: {waveshare_port}")
    else:
        print("[--] Waveshare USB-CAN-A: not found")

    print()

    # Auto-detect
    detected = detect_adapter()
    if detected:
        print(f"[OK] Auto-detected adapter: {detected}")
    else:
        print("[!!] No adapter detected")
        return False

    return True


def test_connection(adapter: str = "auto"):
    """Test arm connection and state reading."""
    print(f"=== Connection Test (adapter={adapter}) ===")
    print()

    try:
        with PiperArm(adapter=adapter) as arm:
            print("[OK] Connected successfully")
            print()
            arm.print_state()
            return True
    except Exception as e:
        print(f"[!!] Connection failed: {e}")
        return False


def test_movement(adapter: str = "auto"):
    """Test arm movement (small movements only)."""
    print(f"=== Movement Test (adapter={adapter}) ===")
    print()
    print("WARNING: Arm will make small movements!")
    print()

    try:
        with PiperArm(adapter=adapter) as arm:
            print("Initial state:")
            arm.print_state()
            print()

            print("Moving Joint 2 by +5°...")
            arm.move_joint_by(1, 5, wait=1.5)
            arm.print_state()
            print()

            print("Moving Joint 2 by -5°...")
            arm.move_joint_by(1, -5, wait=1.5)
            arm.print_state()
            print()

            print("Testing gripper...")
            arm.close_gripper(wait=0.5)
            arm.open_gripper(wait=0.5)
            print()

            print("[OK] Movement test complete")
            return True
    except Exception as e:
        print(f"[!!] Movement test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Piper arm")
    parser.add_argument(
        "--adapter",
        choices=["auto", "standard", "waveshare"],
        default="auto",
        help="Adapter to use (default: auto)",
    )
    parser.add_argument(
        "--test",
        choices=["detect", "connect", "move", "all"],
        default="connect",
        help="Test to run (default: connect)",
    )
    args = parser.parse_args()

    print("=" * 40)
    print("Piper Arm Test")
    print("=" * 40)
    print()

    success = True

    if args.test in ["detect", "all"]:
        if not test_detection():
            success = False
        print()

    if args.test in ["connect", "all"]:
        if not test_connection(args.adapter):
            success = False
        print()

    if args.test in ["move", "all"]:
        if not test_movement(args.adapter):
            success = False
        print()

    print("=" * 40)
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 40)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
