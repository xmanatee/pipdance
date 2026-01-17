# pipdance

Piper AgileX 6-DOF robotic arm controller via Raspberry Pi.

## Hardware

### Components
| Component | Details |
|-----------|---------|
| Raspberry Pi | Pi 3 or better (Pi 4 recommended for high-rate control) |
| Piper Arm | AgileX PiPER 6-DOF robotic arm |
| USB-to-CAN | Standard (gs_usb) or Waveshare USB-CAN-A |
| Power | 24V adapter (included) for arm, microUSB for Pi |

### Wiring
```
Mac ──ethernet──► Raspberry Pi ──USB──► USB-to-CAN ──CAN_H/CAN_L──► Piper Arm
     (via MOKiN)       │                    │
                    microUSB              24V power
                    (power)               adapter
```

**CAN cable colors:** Yellow = CAN_H, Blue = CAN_L, Red = VCC, Black = GND

## Raspberry Pi

| Property | Value |
|----------|-------|
| Hostname | `raspi` |
| User / Pass | `pi3` / `pi3` |
| IP (ethernet) | `192.168.2.3` |
| WiFi | `MikePhone` / `HardPassword` |

**SSH:** `ssh pi3@192.168.2.3`

## Quick Start

### 1. Setup Pi (one-time)
```bash
# On Mac, copy files to Pi
scp -r src/ setup/ examples/ pi3@192.168.2.3:~/pipdance/

# On Pi, run setup
ssh pi3@192.168.2.3
cd ~/pipdance/setup
chmod +x *.sh
./setup_pi.sh
```

### 2. Activate CAN (each boot, standard adapter only)
```bash
./can_setup.sh
```

### 3. Test connection
```bash
source ~/piper-venv/bin/activate
cd ~/pipdance
python setup/test.py --test detect   # Test adapter detection
python setup/test.py --test connect  # Test arm connection
python setup/test.py --test move     # Test arm movement
```

## Usage

```python
from piper import PiperArm

with PiperArm() as arm:  # auto-detects adapter
    arm.print_state()
    arm.move_joint_by(1, 20)  # Move joint 2 by +20°
    arm.close_gripper()
```

### Specify Adapter Explicitly

```python
from piper import create_arm

# Standard socketcan adapter (can0/slcan0)
arm = create_arm("standard")

# Waveshare USB-CAN-A adapter
arm = create_arm("waveshare")

# Auto-detect (default)
arm = create_arm("auto")
```

### API Reference

```python
# Connection
arm.connect()
arm.disconnect()

# State
arm.state               # ArmState(joints=[...], gripper=0.5)
arm.print_state()       # Print formatted state

# Joint control (6 joints, 0-indexed)
arm.move_joints([0.0, 0.1, ...], wait=2.0)  # Move all joints (radians)
arm.move_joint(1, 45.0, wait=2.0)           # Move joint 2 to 45° (degrees)
arm.move_joint_by(1, 10.0, wait=2.0)        # Move joint 2 by +10° (degrees)
arm.home(wait=3.0)                          # All joints to zero

# Gripper
arm.gripper(0.5, wait=1.0)  # Set position (0=open, 1=closed)
arm.open_gripper()
arm.close_gripper()
```

## Mac Setup (Ethernet via Internet Sharing)

**Hardware:** Mac → MOKiN USB-C hub → Pi (ethernet + microUSB power)

1. System Settings → General → Sharing → Internet Sharing
   - Share from: **Wi-Fi**
   - To: **AX88179A** + **USB 10/100/1000 LAN** (both)
2. Allow `dhcp6d` firewall prompt
3. **macOS Sequoia:** Privacy & Security → Local Network → Enable terminal app

## CAN Configuration

- **Bitrate:** 1,000,000 (fixed, cannot change)

### Adapter Types

| Adapter | Interface | Detection |
|---------|-----------|-----------|
| **Standard (gs_usb)** | `can0` or `slcan0` | Auto-detected first |
| **Waveshare USB-CAN-A** | `/dev/ttyUSB*` | Auto-detected second |

The `PiperArm()` function auto-detects the adapter type. Standard socketcan is preferred when available.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `can0` not found | Run `./can_setup.sh` or replug USB-to-CAN adapter |
| "Message NOT sent" | Check CAN wiring, power cycle arm |
| No CAN frames | Verify CAN_H/CAN_L connections, arm powered |
| Import errors | Activate venv: `source ~/piper-venv/bin/activate` |
| Pi unreachable | Check Mac Internet Sharing, Local Network permission |
| Waveshare: no ttyUSB | Replug adapter, check `dmesg \| tail` |
| Waveshare: no frames | Ensure arm power on, verify wiring |
| No adapter detected | Both socketcan and Waveshare unavailable |

## File Structure

```
pipdance/
├── README.md                   # This file
├── CLAUDE.md                   # AI assistant context
├── src/piper/                  # Main package
│   ├── __init__.py            # PiperArm, create_arm, auto-detection
│   ├── base.py                # ArmState, PiperArmBase, deg2rad/rad2deg
│   ├── adapters/
│   │   ├── standard.py        # Uses piper_control (socketcan)
│   │   └── waveshare.py       # Custom CAN protocol
│   └── can/
│       └── waveshare_bus.py   # python-can interface for Waveshare
├── setup/
│   ├── setup_pi.sh            # One-time Pi setup
│   ├── can_setup.sh           # CAN activation (run each boot)
│   └── test.py                # Unified test script
└── examples/
    └── demo.py                # Demo with auto-detection
```

## Resources

- [piper_sdk (official)](https://github.com/agilexrobotics/piper_sdk)
- [piper_control (wrapper)](https://github.com/Reimagine-Robotics/piper_control)
- [piper-kit (CLI + API)](https://github.com/threeal/piper-kit)
- [Piper Manual (PDF)](https://static.generation-robots.com/media/agilex-piper-user-manual.pdf)

## Fallback Access

[Raspberry Pi Connect](https://connect.raspberrypi.com/) - browser-based access when local network fails
