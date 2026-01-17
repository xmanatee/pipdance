# pipdance

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
     (Internet       (runs Python       (standard or    (6-DOF,
      Sharing)        control code)      Waveshare)      24V power)
```

## Key Details

| Item | Value |
|------|-------|
| Pi hostname | `raspi` |
| Pi credentials | `pi3` / `pi3` |
| Pi IP | `192.168.2.3` |
| CAN interface | `can0` (standard) or `/dev/ttyUSB*` (Waveshare) |
| CAN bitrate | `1000000` (fixed) |
| Python venv | `~/piper-venv` |

## macOS Sequoia Fix

"No route to host" → Enable terminal in Privacy & Security → Local Network

## File Structure

```
pipdance/
├── src/piper/                 # Main package
│   ├── __init__.py           # PiperArm, create_arm, auto-detection
│   ├── base.py               # ArmState, PiperArmBase, deg2rad/rad2deg
│   ├── adapters/
│   │   ├── standard.py       # Uses piper_control (socketcan)
│   │   └── waveshare.py      # Custom CAN protocol
│   └── can/
│       └── waveshare_bus.py  # python-can interface for Waveshare
├── setup/
│   ├── setup_pi.sh           # One-time Pi setup
│   ├── can_setup.sh          # CAN activation (run each boot)
│   └── test.py               # Unified test script
└── examples/
    └── demo.py               # Demo with auto-detection
```

## Common Tasks

### Deploy code to Pi
```bash
scp -r src/ setup/ examples/ pi3@192.168.2.3:~/pipdance/
```

### Run on Pi
```bash
ssh pi3@192.168.2.3
source ~/piper-venv/bin/activate
cd ~/pipdance
python examples/demo.py
```

### Test adapter detection
```bash
python setup/test.py --test detect
```

### CAN troubleshooting
```bash
./setup/can_setup.sh         # Activate CAN (standard adapter)
candump can0                  # See raw frames (arm must be on)
ip -details link show can0    # Check interface status
```

## SDK Usage

```python
from piper import PiperArm

with PiperArm() as arm:  # auto-detects adapter
    arm.print_state()
    arm.move_joint_by(1, 20)  # Joint 2, +20°
    arm.close_gripper()

# Or specify adapter explicitly
from piper import create_arm

arm = create_arm("waveshare")  # or "standard"
arm.connect()
arm.print_state()
arm.disconnect()
```

See [README.md](./README.md) for full documentation.
