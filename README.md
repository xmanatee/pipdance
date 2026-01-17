# pipdance

Piper AgileX 6-DOF robotic arm controller via Raspberry Pi.

## Hardware

### Components
| Component | Details |
|-----------|---------|
| Raspberry Pi | Pi 3 or better (Pi 4 recommended for high-rate control) |
| Piper Arm | AgileX PiPER 6-DOF robotic arm |
| USB-to-CAN | Included with Piper arm |
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
# On Mac, copy setup files to Pi
scp -r setup/ pi3@192.168.2.3:~/pipdance/

# On Pi, run setup
ssh pi3@192.168.2.3
cd ~/pipdance/setup
chmod +x *.sh
./setup_pi.sh
```

### 2. Activate CAN (each boot)
```bash
./can_setup.sh
```

### 3. Test connection
```bash
source ~/piper-venv/bin/activate
python test_can.py      # Test CAN bus
python test_arm.py      # Test arm control (arm must be powered)
```

## Mac Setup (Ethernet via Internet Sharing)

**Hardware:** Mac → MOKiN USB-C hub → Pi (ethernet + microUSB power)

1. System Settings → General → Sharing → Internet Sharing
   - Share from: **Wi-Fi**
   - To: **AX88179A** + **USB 10/100/1000 LAN** (both)
2. Allow `dhcp6d` firewall prompt
3. **macOS Sequoia:** Privacy & Security → Local Network → Enable terminal app

## SDK Options

| Package | Level | Install | Use Case |
|---------|-------|---------|----------|
| `piper_sdk` | Low | `pip install piper_sdk` | Direct CAN control, full access |
| `piper_control` | High | `pip install piper_control` | Simpler API, recommended |
| `piper-kit` | High | `pip install piper-kit` | CLI tools + Python API |

## CAN Configuration

- **Bitrate:** 1,000,000 (fixed, cannot change)
- **Interface:** `can0` (default)
- **Activation:** `sudo ip link set can0 up type can bitrate 1000000`

### Verify CAN
```bash
ip -details link show can0   # Check interface
candump can0                  # See raw CAN frames (arm must be on)
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `can0` not found | Run `./can_setup.sh` or replug USB-to-CAN adapter |
| "Message NOT sent" | Check CAN wiring, power cycle arm |
| No CAN frames | Verify CAN_H/CAN_L connections, arm powered |
| Import errors | Activate venv: `source ~/piper-venv/bin/activate` |
| Pi unreachable | Check Mac Internet Sharing, Local Network permission |

## File Structure

```
pipdance/
├── README.md           # This file
├── CLAUDE.md           # AI assistant context
├── setup/
│   ├── setup_pi.sh     # One-time Pi setup
│   ├── can_setup.sh    # CAN activation (run each boot)
│   ├── test_can.py     # Test CAN connection
│   └── test_arm.py     # Test arm control
└── src/
    └── piper_app.py    # Sample application
```

## Resources

- [piper_sdk (official)](https://github.com/agilexrobotics/piper_sdk)
- [piper_control (wrapper)](https://github.com/Reimagine-Robotics/piper_control)
- [piper-kit (CLI + API)](https://github.com/threeal/piper-kit)
- [Piper Manual (PDF)](https://static.generation-robots.com/media/agilex-piper-user-manual.pdf)

## Fallback Access

[Raspberry Pi Connect](https://connect.raspberrypi.com/) - browser-based access when local network fails
