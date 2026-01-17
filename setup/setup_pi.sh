#!/bin/bash
# Raspberry Pi setup for Piper AgileX arm control
set -e

echo "=== Piper Pi Setup ==="
echo ""

echo "[1/4] Updating system packages..."
sudo apt update
sudo apt upgrade -y
echo "      Done"

echo "[2/4] Installing system dependencies..."
sudo apt install -y python3-pip python3-venv can-utils git ethtool
echo "      Done"

echo "[3/4] Creating Python venv at ~/piper-venv..."
if [ ! -d "$HOME/piper-venv" ]; then
    python3 -m venv "$HOME/piper-venv"
    echo "      Created"
else
    echo "      Already exists"
fi

echo "[4/4] Installing Python packages..."
source "$HOME/piper-venv/bin/activate"
pip install --upgrade pip
pip install "python-can>=3.3.4" piper_sdk piper_control
echo "      Done"

echo ""
echo "=== Verifying ==="
python -c "import can; print(f'python-can: {can.__version__}')"
python -c "import piper_sdk; print('piper_sdk: OK')"
python -c "from piper_control import piper_interface; print('piper_control: OK')"

echo ""
echo "=== Setup Complete ==="
echo "Next: Connect USB-to-CAN adapter, then run ./can_setup.sh"
