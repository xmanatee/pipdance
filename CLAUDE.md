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
scp -r src/ setup/ examples/ pi3@192.168.2.3:~/pipdance/
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
```

### CAN setup (standard adapter, each boot)
```bash
./setup/can_setup.sh
candump can0                   # Verify frames (arm must be powered)
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No route to host" (macOS Sequoia) | Privacy & Security → Local Network → enable terminal |
| `can0` not found | Run `./can_setup.sh` or replug adapter |
| No CAN frames | Check wiring, ensure arm is powered |
| Import errors | Activate venv: `source ~/piper-venv/bin/activate` |

See [README.md](./README.md) for hardware details and full API reference.
