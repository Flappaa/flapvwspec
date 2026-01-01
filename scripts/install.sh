#!/usr/bin/env bash
set -euo pipefail

# Installer helper for vlinker-cli
# - installs Python deps into system or venv
# - installs udev rules
# Run as normal user; parts requiring root will use sudo

REQ_FILE="$(dirname "$0")/../requirements.txt"
UDEV_RULE="$(dirname "$0")/../udev/99-vlinker.rules"

echo "Installing Python dependencies (system-wide). Use a venv for isolation if desired."
if [ -f "$REQ_FILE" ]; then
  python3 -m pip install --upgrade pip
  python3 -m pip install -r "$REQ_FILE"
else
  echo "No requirements.txt found at $REQ_FILE"
fi

if [ -f "$UDEV_RULE" ]; then
  echo "Installing udev rule to /etc/udev/rules.d/"
  sudo cp "$UDEV_RULE" /etc/udev/rules.d/
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  echo "udev rule installed. You may need to unplug/replug the device."
else
  echo "No udev rule found at $UDEV_RULE"
fi

echo "Creating CLI symlink /usr/local/bin/vlinker (requires sudo)"
SCRIPT_PATH="$(pwd)/vlinker_cli.py"
if [ -f "$SCRIPT_PATH" ]; then
  sudo ln -sf "$SCRIPT_PATH" /usr/local/bin/vlinker
  sudo chmod +x "$SCRIPT_PATH"
  echo "Installed /usr/local/bin/vlinker"
else
  echo "vlinker_cli.py not found in current directory. Run this script from repository root." >&2
fi

echo "Install complete."
