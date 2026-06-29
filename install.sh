#!/usr/bin/env bash
# One-liner installer for Assistant Lab
# Usage: curl -fsSL https://raw.githubusercontent.com/OwendoyalAdastra-lang/assistant-lab/main/install.sh | bash
set -euo pipefail

REPO_RAW="${ASSISTANT_LAB_REPO:-https://raw.githubusercontent.com/OwendoyalAdastra-lang/assistant-lab/main}"
INSTALL_DIR="${ASSISTANT_LAB_DIR:-$HOME/assistant-lab}"

FILES=(
  build_your_own_smart_assistant_pygame.py
  assistant_lab_owner_protocol.py
  assistant_lab_host_auth.py
  assistant_lab_chat_log.py
  assistant_lab_chat.py
  assistant_lab_chat_server.py
  assistant_lab_data.py
  assistant_lab_integrity.py
  assistant_lab_settings.py
  assistant_lab_trade.py
  assistant_lab_world.py
  profanity_filter.py
  requirements.txt
  run.sh
)

echo "Installing Assistant Lab to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

for f in "${FILES[@]}"; do
  echo "  -> $f"
  curl -fsSL "$REPO_RAW/$f" -o "$INSTALL_DIR/$f"
done

chmod +x "$INSTALL_DIR/run.sh"

echo "Installing Python dependency (pygame)..."
python3 -m pip install -r "$INSTALL_DIR/requirements.txt" --user

echo ""
echo "Done! Run:"
echo "  cd $INSTALL_DIR"
echo "  ./run.sh server   # terminal 1 — multiplayer chat"
echo "  ./run.sh game     # terminal 2 — play"