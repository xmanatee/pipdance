# pipdance

Piper AgileX 6-DOF robotic arm controller via Raspberry Pi.

## Quick Reference

```bash
# SSH to Pi
ssh pi3@192.168.2.3   # password: pi3

# On Pi: activate CAN and test
./can_setup.sh
source ~/piper-venv/bin/activate
python test_arm.py
```

## Architecture

```
Mac ──ethernet──► Raspberry Pi ──USB──► USB-to-CAN ──► Piper Arm
     (Internet       (runs Python       (included      (6-DOF,
      Sharing)        control code)      with arm)      24V power)
```

## Key Details

| Item | Value |
|------|-------|
| Pi hostname | `raspi` |
| Pi credentials | `pi3` / `pi3` |
| Pi IP | `192.168.2.3` |
| CAN interface | `can0` |
| CAN bitrate | `1000000` (fixed) |
| Python venv | `~/piper-venv` |
| SDK | `piper_control` (high-level) or `piper_sdk` (low-level) |

## macOS Sequoia Fix

"No route to host" → Enable terminal in Privacy & Security → Local Network

## File Structure

- `setup/setup_pi.sh` - One-time Pi setup (installs deps)
- `setup/can_setup.sh` - CAN activation (run each boot)
- `setup/test_can.py` - Test CAN without arm
- `setup/test_arm.py` - Test arm control
- `src/piper_app.py` - Sample application with `PiperArm` class

## Common Tasks

### Deploy code to Pi
```bash
scp -r src/ pi3@192.168.2.3:~/pipdance/
```

### Run on Pi
```bash
ssh pi3@192.168.2.3
source ~/piper-venv/bin/activate
cd ~/pipdance
python src/piper_app.py
```

### CAN troubleshooting
```bash
./can_setup.sh              # Activate CAN
candump can0                # See raw frames (arm must be on)
ip -details link show can0  # Check interface status
```

## SDK Usage

```python
from src.piper_app import PiperArm, deg_to_rad

with PiperArm("can0") as arm:
    print(arm.state.joint_positions)
    arm.move_joint_relative(2, deg_to_rad(30))  # Joint 3, +30°
    arm.close_gripper()
```

See [README.md](./README.md) for full documentation.
