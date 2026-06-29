#!/usr/bin/env bash
# Assistant Lab — quick launcher (game + chat server)
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c "import pygame" 2>/dev/null; then
  echo "Installing pygame..."
  python3 -m pip install -r requirements.txt --user
fi

case "${1:-game}" in
  server)
    echo "Starting chat server on 0.0.0.0:9876 ..."
    exec python3 assistant_lab_chat_server.py --host 0.0.0.0 --port 9876
    ;;
  game|*)
    echo "Starting Assistant Lab game ..."
    exec python3 build_your_own_smart_assistant_pygame.py
    ;;
esac