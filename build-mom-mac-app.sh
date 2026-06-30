#!/usr/bin/env bash
# Build a zip mom can open on her Mac — Assistant Lab.app + game files
set -euo pipefail
cd "$(dirname "$0")"

OUT="dist/Assistant-Lab-Mac"
rm -rf "$OUT"
mkdir -p "$OUT"

# Game files
GAME_FILES=(
  build_your_own_smart_assistant_pygame.py
  assistant_lab_chat.py
  assistant_lab_chat_log.py
  assistant_lab_chat_server.py
  assistant_lab_data.py
  assistant_lab_host_auth.py
  assistant_lab_integrity.py
  assistant_lab_owner_protocol.py
  assistant_lab_settings.py
  assistant_lab_trade.py
  assistant_lab_world.py
  profanity_filter.py
  launch.py
)

for f in "${GAME_FILES[@]}"; do
  cp "$f" "$OUT/"
done

# App bundle + server IP
cp -R "mom-mac-app/Assistant Lab.app" "$OUT/"
cp mom-mac-app/server-ip.txt "$OUT/"
cp "mom-mac-app/Start Assistant Lab.command" "$OUT/"
chmod +x "$OUT/Assistant Lab.app/Contents/MacOS/run"
chmod +x "$OUT/Start Assistant Lab.command"

cat > "$OUT/README-MOM.txt" << 'EOF'
ASSISTANT LAB — Mac App
=======================

1. Unzip this folder
2. Edit server-ip.txt — put Owen's IP on line 3 (under the # comments)
3. Double-click "Start Assistant Lab.command"  (best — shows errors)
   OR double-click "Assistant Lab.app"

First time Mac may ask:
  Right-click → Open → Open

Chat not connecting?
  - Owen must run family-host.sh on his computer first
  - server-ip.txt must have Owen's current IP (no spaces)
  - Check assistant-lab-last-run.log in this folder

Solo play works without chat — leave server-ip.txt as 127.0.0.1
EOF

mkdir -p dist
ZIP="dist/Assistant-Lab-Mac.zip"
rm -f "$ZIP"
if command -v zip >/dev/null 2>&1; then
  (cd dist && zip -r "Assistant-Lab-Mac.zip" "Assistant-Lab-Mac")
else
  python3 - "$OUT" "$ZIP" <<'PY'
import sys, zipfile
from pathlib import Path
src, dest = Path(sys.argv[1]), Path(sys.argv[2])
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in src.rglob("*"):
        zf.write(path, path.relative_to(src.parent))
PY
fi

echo ""
echo "Built: $ZIP"
echo "Send this zip to mom (AirDrop, email, Google Drive)"
echo "She unzips and double-clicks Assistant Lab.app"