#!/usr/bin/env bash
# Assistant Lab — quick launcher (game + chat server)
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import pygame" 2>/dev/null; then
  echo "Installing pygame into .venv ..."
  .venv/bin/pip install -r requirements.txt
fi

PY=".venv/bin/python"

case "${1:-game}" in
  server|server-local|local-server)
    echo "Starting chat server on 127.0.0.1:9876 (this Mac/PC only) ..."
    exec "$PY" assistant_lab_chat_server.py --host 127.0.0.1 --port 9876
    ;;
  server-lan|server-public)
    echo "Starting chat server on 0.0.0.0:9876 (others on your Wi-Fi) ..."
    echo "Needs a Host Key — or use owner-run-server.sh if you are the lab owner."
    exec "$PY" assistant_lab_chat_server.py --host 0.0.0.0 --port 9876
    ;;
  game|*)
    echo "Starting Assistant Lab game ..."
    exec "$PY" build_your_own_smart_assistant_pygame.py
    ;;
esac