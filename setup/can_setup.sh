#!/bin/bash
# CAN interface activation for Piper arm
# Supports both native CAN and serial (slcan) adapters
set -e

CAN="${1:-can0}"
BITRATE="1000000"

# Auto-detect serial device (ttyUSB0, ttyUSB1, etc.)
find_serial() {
    for dev in /dev/ttyUSB*; do
        [ -e "$dev" ] && echo "$dev" && return 0
    done
    return 1
}

echo "=== CAN Setup ==="
echo ""

# Check for native CAN interface first
if ip link show "$CAN" &>/dev/null; then
    echo "Found native CAN interface: $CAN"
    echo ""
    echo "[1/2] Configuring $CAN..."
    sudo ip link set "$CAN" down 2>/dev/null || true
    sudo ip link set "$CAN" type can bitrate "$BITRATE"
    sudo ip link set "$CAN" up
    echo "      Done"

    echo "[2/2] Verifying..."
    STATE=$(ip -brief link show "$CAN" | awk '{print $2}')
    echo "      State: $STATE"

    echo ""
    echo "=== CAN Ready ==="
    exit 0
fi

# Check for serial adapter (slcan)
echo "No native CAN found, checking for serial adapter..."
SERIAL_DEV=$(find_serial)
if [ -n "$SERIAL_DEV" ]; then
    echo "Found serial device: $SERIAL_DEV"
    echo ""

    # Kill any existing slcand
    sudo killall slcand 2>/dev/null || true
    sleep 0.5

    # Remove old slcan interface if exists
    sudo ip link delete slcan0 2>/dev/null || true

    echo "[1/3] Starting slcand..."
    # -o = open CAN device, -c = close on exit, -s8 = 1Mbps
    sudo slcand -o -c -s8 "$SERIAL_DEV" slcan0
    sleep 1
    echo "      Done"

    echo "[2/3] Bringing up slcan0..."
    sudo ip link set slcan0 up
    echo "      Done"

    echo "[3/3] Verifying..."
    STATE=$(ip -brief link show slcan0 | awk '{print $2}')
    echo "      State: $STATE"

    echo ""
    echo "=== CAN Ready (slcan0) ==="
    echo ""
    echo "NOTE: Use 'slcan0' instead of 'can0' in your scripts"
    echo "Test: candump slcan0"
    exit 0
fi

# Nothing found
echo ""
echo "ERROR: No CAN adapter found!"
echo ""
echo "Check:"
echo "  1. USB-to-CAN adapter is plugged in"
echo "  2. Run: dmesg | tail -10"
echo ""
echo "Expected: ttyUSB0 (serial) or can0 (native)"
exit 1
