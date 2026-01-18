#!/bin/bash
# CAN interface activation for Piper arm(s)
# Supports native CAN, serial (slcan), and dual-arm configurations
#
# Usage:
#   ./can_setup.sh           # Single arm (auto-detect)
#   ./can_setup.sh can0      # Single arm on can0
#   ./can_setup.sh --dual    # Dual arm (can0 + can1)
#
set -e

BITRATE="1000000"

# Setup a single native CAN interface
setup_native_can() {
    local CAN="$1"
    if ip link show "$CAN" &>/dev/null; then
        echo "  Configuring $CAN..."
        sudo ip link set "$CAN" down 2>/dev/null || true
        sudo ip link set "$CAN" type can bitrate "$BITRATE"
        sudo ip link set "$CAN" up
        STATE=$(ip -brief link show "$CAN" | awk '{print $2}')
        echo "  $CAN: $STATE"
        return 0
    fi
    return 1
}

# Auto-detect serial devices
find_serials() {
    ls /dev/ttyUSB* 2>/dev/null || true
}

# Setup slcan from serial device
setup_slcan() {
    local SERIAL_DEV="$1"
    local SLCAN_NAME="$2"

    echo "  Setting up $SLCAN_NAME from $SERIAL_DEV..."

    # Remove old interface if exists
    sudo ip link delete "$SLCAN_NAME" 2>/dev/null || true

    # -o = open CAN device, -c = close on exit, -s8 = 1Mbps
    sudo slcand -o -c -s8 "$SERIAL_DEV" "$SLCAN_NAME"
    sleep 0.5
    sudo ip link set "$SLCAN_NAME" up

    STATE=$(ip -brief link show "$SLCAN_NAME" | awk '{print $2}')
    echo "  $SLCAN_NAME: $STATE"
}

# ========== Main ==========

# Dual-arm mode
if [ "$1" = "--dual" ]; then
    echo "=== Dual CAN Setup ==="
    echo ""

    # Kill any existing slcand processes
    sudo killall slcand 2>/dev/null || true
    sleep 0.5

    # Try native CAN first (can0 + can1)
    if ip link show can0 &>/dev/null && ip link show can1 &>/dev/null; then
        echo "Found dual native CAN interfaces"
        echo ""
        setup_native_can "can0"
        setup_native_can "can1"
        echo ""
        echo "=== Dual CAN Ready ==="
        echo "  he:  can0"
        echo "  she: can1"
        echo ""
        echo "Test: candump can0 & candump can1"
        exit 0
    fi

    # Try serial adapters (ttyUSB0 + ttyUSB1)
    SERIALS=($(find_serials))
    if [ ${#SERIALS[@]} -ge 2 ]; then
        echo "Found ${#SERIALS[@]} serial adapters"
        echo ""
        setup_slcan "${SERIALS[0]}" "slcan0"
        setup_slcan "${SERIALS[1]}" "slcan1"
        echo ""
        echo "=== Dual CAN Ready ==="
        echo "  he:  slcan0 (${SERIALS[0]})"
        echo "  she: slcan1 (${SERIALS[1]})"
        echo ""
        echo "Use: --he-can slcan0 --she-can slcan1"
        exit 0
    fi

    # Mixed mode: one native, one serial
    if ip link show can0 &>/dev/null && [ ${#SERIALS[@]} -ge 1 ]; then
        echo "Found mixed CAN setup (native + serial)"
        echo ""
        setup_native_can "can0"
        setup_slcan "${SERIALS[0]}" "slcan0"
        echo ""
        echo "=== Dual CAN Ready ==="
        echo "  he:  can0"
        echo "  she: slcan0 (${SERIALS[0]})"
        echo ""
        echo "Use: --he-can can0 --she-can slcan0"
        exit 0
    fi

    echo ""
    echo "ERROR: Need 2 CAN adapters for dual mode!"
    echo ""
    echo "Options:"
    echo "  - Two USB-to-CAN adapters (creates can0/can1 or ttyUSB0/ttyUSB1)"
    echo "  - Dual CAN HAT (MCP2515, creates can0/can1)"
    echo ""
    exit 1
fi

# Single-arm mode
CAN="${1:-can0}"
echo "=== CAN Setup ==="
echo ""

# Check for native CAN interface first
if ip link show "$CAN" &>/dev/null; then
    echo "Found native CAN interface: $CAN"
    echo ""
    setup_native_can "$CAN"
    echo ""
    echo "=== CAN Ready ==="
    exit 0
fi

# Check for serial adapter (slcan)
echo "No native CAN found, checking for serial adapter..."
SERIALS=($(find_serials))
if [ ${#SERIALS[@]} -ge 1 ]; then
    SERIAL_DEV="${SERIALS[0]}"
    echo "Found serial device: $SERIAL_DEV"
    echo ""

    # Kill any existing slcand
    sudo killall slcand 2>/dev/null || true
    sleep 0.5

    setup_slcan "$SERIAL_DEV" "slcan0"

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
echo ""
echo "For dual-arm setup: ./can_setup.sh --dual"
exit 1
