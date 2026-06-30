#!/bin/bash
# If the .app closes too fast, double-click THIS file instead (opens Terminal).
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
LOG="$DIR/assistant-lab-last-run.log"
echo "=== Assistant Lab ===" | tee -a "$LOG"
echo "Log file: $LOG"
echo ""

PY="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
[[ -x "$PY" ]] || PY="python3"

"$PY" -m pip install --user pygame-ce 2>/dev/null || "$PY" -m pip install pygame-ce 2>/dev/null || true

if [[ -f server-ip.txt ]]; then
  IP=$(grep -v '^#' server-ip.txt | grep -v '^[[:space:]]*$' | head -1 | tr -d '[:space:]')
  export ASSISTANT_LAB_CHAT_HOST="$IP"
fi
export ASSISTANT_LAB_CHAT_PORT=9876

echo "Chat server: ${ASSISTANT_LAB_CHAT_HOST:-solo}"
echo "Starting game..."
"$PY" build_your_own_smart_assistant_pygame.py 2>&1 | tee -a "$LOG"
echo ""
echo "Game closed. Log saved to:"
echo "  $LOG"
read -r -p "Press Enter to close this window..."