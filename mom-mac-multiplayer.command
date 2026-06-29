#!/bin/bash
# Mom's Mac — multiplayer (connects to Owen's server).
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

SERVER_IP=""
if [[ -f mom-server-address.txt ]]; then
  SERVER_IP=$(head -1 mom-server-address.txt | tr -d '[:space:]')
fi

if [[ -z "$SERVER_IP" || "$SERVER_IP" == "127.0.0.1" ]]; then
  echo ""
  echo "=== Owen's server address ==="
  echo "Owen will text you a number like: 100.115.92.196"
  echo ""
  read -r -p "Type Owen's IP here and press Enter: " SERVER_IP
  SERVER_IP=$(echo "$SERVER_IP" | tr -d '[:space:]')
  if [[ -z "$SERVER_IP" ]]; then
    echo "No IP entered. Ask Owen for his server number."
    read -r -p "Press Enter..."
    exit 1
  fi
  echo "$SERVER_IP" > mom-server-address.txt
  echo "Saved to mom-server-address.txt for next time."
fi

echo ""
echo "Connecting to Owen's server: $SERVER_IP:9876"
"$PY" -m pip install --user pygame 2>/dev/null || "$PY" -m pip install pygame

export ASSISTANT_LAB_CHAT_HOST="$SERVER_IP"
export ASSISTANT_LAB_CHAT_PORT="9876"
exec "$PY" build_your_own_smart_assistant_pygame.py