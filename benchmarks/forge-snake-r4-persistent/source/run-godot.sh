#!/bin/bash
set -e
BASE=benchmarks/forge-snake-r4-persistent
rm -f "$BASE/godot/godot-import-pose.png" "$BASE/godot/godot-import-pose.png.import"
rm -rf "$BASE/godot/.godot"
cp "$BASE/snake-sectional-r4.glb" "$BASE/godot/snake-sectional-r4.glb"
GODOT=/mnt/c/Users/Moore/Godot/Godot_v4.7.2-stable_win64_console.exe
PROJECT=$(wslpath -w "$PWD/$BASE/godot")
"$GODOT" --headless --editor --path "$PROJECT" --quit > "$BASE/godot/import.log" 2>&1
IMPORT_CODE=$?
"$GODOT" --headless --path "$PROJECT" --script res://check.gd > "$BASE/godot/check.log" 2>&1
CHECK_CODE=$?
"$GODOT" --path "$PROJECT" --rendering-method gl_compatibility --resolution 1280x720 --script res://capture.gd > "$BASE/godot/capture.log" 2>&1
CAPTURE_CODE=$?
python3 - "$BASE" "$IMPORT_CODE" "$CHECK_CODE" "$CAPTURE_CODE" <<'PY2'
from pathlib import Path
import json,sys
(Path(sys.argv[1])/'godot/exit-codes.json').write_text(json.dumps(dict(zip(['import','check','capture'],map(int,sys.argv[2:]))),indent=2))
PY2
