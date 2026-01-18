# pipdance

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Piper AgileX 6-DOF robotic arm controller via Raspberry Pi.

## Quick Reference

```bash
# SSH to Pi
ssh pi3@192.168.2.3   # password: pi3

# On Pi: activate CAN and test
cd ~/pipdance/setup
./can_setup.sh
source ~/piper-venv/bin/activate
python test.py
```

## Architecture

```
Mac ──ethernet──► Raspberry Pi ──USB──► USB-to-CAN ──► Piper Arm
     (editing &      (runs Python       (standard or    (6-DOF,
      SSH only)       control code)      Waveshare)      24V power)
```

**Adapter pattern:** `PiperArmBase` (abstract) → `StandardPiperArm` (socketcan) or `WavesharePiperArm` (serial). Auto-detection prefers standard socketcan.

## Key Details

| Item | Value |
|------|-------|
| Pi credentials | `pi3` / `pi3` |
| Pi IP | `192.168.2.3` |
| CAN interface | `can0` (standard) or `/dev/ttyUSB*` (Waveshare) |
| CAN bitrate | `1000000` (fixed) |
| Python venv | `~/piper-venv` |

## macOS Sequoia Fix

"No route to host" → Enable terminal in Privacy & Security → Local Network

## Commands

### Deploy to Pi (from Mac)
```bash
scp -r src/ setup/ examples/ scripts/ pi3@192.168.2.3:~/pipdance/
```

### Run on Pi
```bash
ssh pi3@192.168.2.3
source ~/piper-venv/bin/activate
cd ~/pipdance

# Tests
python setup/test.py --test detect   # Adapter detection only
python setup/test.py --test connect  # Connection + state read
python setup/test.py --test move     # Small movement test
python setup/test.py --test all      # All tests

# Demo
python examples/demo.py

# Choreography (single arm)
python -m piper.choreography --poses scripts/poses.json --schedule scripts/he.md

# Choreography (dual arm)
python -m piper.choreography --poses scripts/poses.json --he scripts/he.md --she scripts/she.md

# Choreography (dual arm with explicit CAN interfaces)
python -m piper.choreography --poses scripts/poses.json --he scripts/he.md --she scripts/she.md \
    --he-can can0 --she-can can1

# Dry run (validate without moving)
python -m piper.choreography --poses scripts/poses.json --schedule scripts/he.md --dry-run
```

### CAN setup (standard adapter, each boot)
```bash
# Single arm
./setup/can_setup.sh
candump can0                   # Verify frames (arm must be powered)

# Dual arm (two USB-CAN adapters)
./setup/can_setup.sh --dual
candump can0 &                 # Terminal 1
candump can1                   # Terminal 2
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No route to host" (macOS Sequoia) | Privacy & Security → Local Network → enable terminal |
| `can0` not found | Run `./can_setup.sh` or replug adapter |
| No CAN frames | Check wiring, ensure arm is powered |
| Import errors | Activate venv: `source ~/piper-venv/bin/activate` |

## Choreography Module

The `piper.choreography` module enables timed pose sequences using the adapter pattern.

### File Formats

**Poses JSON** (`scripts/poses.json`):
```json
{
  "scenes": [
    {"name": "stand", "joint_positions": {"J1": 0, "J2": 90, "J3": -5, "J4": 0, "J5": 0, "J6": 0}}
  ]
}
```

**Schedule Markdown** (`scripts/he.md`):
```markdown
# Comments start with #
00:00.000 - stand
00:06.500 - left_down
01:42.250 - kiss
```
Each line specifies when the arm should **arrive** at that pose.
Timestamps use `MM:SS.mmm` format (milliseconds are mandatory, exactly 3 digits).

### Python API
```python
from piper import create_arm
from piper.choreography import load_choreography, run_choreography

choreo = load_choreography("scripts/poses.json", "scripts/he.md")
with create_arm() as arm:
    run_choreography(arm, choreo)
```

See [README.md](./README.md) for hardware details and full API reference.

## Dual-Arm Setup

### Hardware Requirements

Two separate CAN interfaces are recommended for dual-arm operation:
- **Two USB-CAN adapters**: Creates can0 + can1 (or ttyUSB0 + ttyUSB1)
- **Dual CAN HAT**: MCP2515-based HAT with two channels

### Setup Process

```bash
# 1. Connect both USB-CAN adapters
# 2. Run dual setup script
./setup/can_setup.sh --dual

# 3. Verify both arms
candump can0 &
candump can1
# (Both should show CAN frames when arms are powered)

# 4. Run choreography
python -m piper.choreography --poses scripts/poses.json \
    --he scripts/he.md --she scripts/she.md \
    --he-can can0 --she-can can1
```

### Synchronization Options

| Option | Description |
|--------|-------------|
| `--no-parallel` | Disable parallel command sending (sequential mode) |

**Expected sync accuracy**: ±30-50ms with parallel mode (default), ±50-100ms without.

### Troubleshooting Dual-Arm

| Symptom | Fix |
|---------|-----|
| Only one CAN interface appears | Unplug/replug second adapter, check `dmesg` |
| Arms out of sync | Ensure separate CAN buses, try `--no-parallel` to diagnose |
| High timing drift | Disable background services, use Ethernet instead of WiFi |
