#!/usr/bin/env bash
set -euo pipefail

# Build helper: create a single-file executable via PyInstaller
# Requires PyInstaller installed in the environment.

APP= vlinker
SCRIPT=../vlinker_cli.py

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller not found. Install with: python3 -m pip install pyinstaller" >&2
  exit 1
fi

pushd "$(dirname "$0")" >/dev/null
echo "Building single-file executable (may take a while)..."
pyinstaller --onefile --name vlinker "$SCRIPT"
echo "Build output in dist/vlinker"
popd >/dev/null
