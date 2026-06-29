#!/bin/bash
# Mom's Mac — multiplayer (connects to Owen's server).
# Owen: run assistant-lab-owner/family-host.sh on your Chromebook first.
# Edit mom-server-address.txt — put Owen's IP on line 1 (he will tell you).
cd "$(dirname "$0")"

PY=""
for candidate in python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; exit(0)" 2>/dev/null; then
    PY="$candidate"
    break
  fi
done

if [[ -z "$PY" ]]; then
  echo "Install Python first: https://www.python.org/downloads/"
  read -r -p "Press Enter..."
  exit 1
fi

SERVER_IP="127.0.0.1"
if [[ -f mom-server-address.txt ]]; then
  SERVER_IP=$(head -1 mom-server-address.txt | tr -d '[:space:]')
fi

if [[ "$SERVER_IP" == "127.0.0.1" || -z "$SERVER_IP" ]]; then
  echo ""
  echo "Multiplayer needs Owen's server IP."
  echo "1. Owen starts the family server on his computer"
  echo "2. Owen gives you his IP (example: 100.115.92.196)"
  echo "3. Open mom-server-address.txt in TextEdit"
  echo "   Replace 127.0.0.1 with Owen's IP, save"
  echo "4. Double-click this file again"
  echo ""
  read -r -p "Press Enter..."
  exit 1
fi

echo "Using Python: $PY"
echo "Connecting to Owen's server: $SERVER_IP:9876"
"$PY" -m pip install --user pygame 2>/dev/null || "$PY" -m pip install pygame

export ASSISTANT_LAB_CHAT_HOST="$SERVER_IP"
export ASSISTANT_LAB_CHAT_PORT="9876"
exec "$PY" build_your_own_smart_assistant_pygame.py