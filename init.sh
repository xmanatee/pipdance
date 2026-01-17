sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip can-utils git

python3 -m venv ~/piper-venv
source ~/piper-venv/bin/activate

pip3 install --upgrade pip
pip3 install "python-can>=3.3.4" piper_sdk
# optional: if you want the higher-level wrapper
pip3 install piper_control
