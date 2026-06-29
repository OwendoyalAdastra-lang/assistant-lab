#!/bin/bash
# Mom's Mac — no Command Line Tools needed.
# 1) Install Python from https://www.python.org/downloads/ (click the yellow button)
# 2) Download game zip: https://github.com/OwendoyalAdastra-lang/assistant-lab/archive/refs/heads/main.zip
# 3) Unzip, put this file inside the assistant-lab-main folder
# 4) Double-click mom-mac-play.command
cd "$(dirname "$0")"

PY=""
for candidate in python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; exit(0)" 2>/dev/null; then
    PY="$candidate"
    break
  fi
done

if [[ -z "$PY" ]]; then
  echo ""
  echo "Python not found."
  echo "1. Open Safari → https://www.python.org/downloads/"
  echo "2. Download and install Python (click through the installer)"
  echo "3. Double-click this file again"
  echo ""
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Using: $PY"
echo "Installing pygame (one time, may take a minute)..."
"$PY" -m pip install --user pygame 2>/dev/null || "$PY" -m pip install pygame

echo "Starting Assistant Lab..."
exec "$PY" build_your_own_smart_assistant_pygame.py