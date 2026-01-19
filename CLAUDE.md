# pipdance

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Piper AgileX 6-DOF robotic arm controller via Raspberry Pi. Dual-arm dance choreography for [The Robot Rave Hackathon](https://therobotrave.com/).

## Quick Reference

```bash
ssh pi3@192.168.2.3                    # SSH to Pi (password: pi3)
source ~/piper-venv/bin/activate       # Activate venv
./setup/can_setup.sh                   # Setup CAN (each boot)
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

## Quick Commands

Source the commands file: `source commands.sh`

| Command | Description |
|---------|-------------|
| `piper-sim` | Run dual-arm simulation locally |
| `piper-deploy` | Copy files to Pi |
| `piper-run` | Deploy and run on Pi |
| `piper-dry` | Validate choreography |

## Choreography

**Poses JSON** (`scripts/poses.json`):
```json
{"scenes": [{"name": "stand", "joint_positions": {"J1": 0, "J2": 90, "J3": -5, "J4": 0, "J5": 0, "J6": 0}}]}
```

**Schedule Markdown** (`scripts/he.md`):
```markdown
00:00.000 - stand
00:06.500 - left_down
```
Timestamps = when arm **arrives** at pose. Format: `MM:SS.mmm` (milliseconds mandatory).

**Run choreography:**
```bash
# Single arm
python -m piper.choreography --poses scripts/poses.json --schedule scripts/he.md

# Dual arm
python -m piper.choreography --poses scripts/poses.json --he scripts/he.md --she scripts/she.md
```

## Dual-Arm Setup

```bash
./setup/can_setup.sh --dual            # Setup both CAN interfaces
python -m piper.choreography --poses scripts/poses.json \
    --he scripts/he.md --she scripts/she.md \
    --he-can can0 --she-can can1
```

**Sync accuracy:** ±30-50ms with parallel mode (default).

## Troubleshooting

See [README.md](./README.md#troubleshooting) for common issues and fixes.

**Quick fixes:**
- "No route to host" (macOS Sequoia) → Privacy & Security → Local Network → enable terminal
- `can0` not found → Run `./can_setup.sh` or replug adapter
- Import errors → Activate venv: `source ~/piper-venv/bin/activate`
