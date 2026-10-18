#!/bin/bash
set -e
BASE=benchmarks/forge-snake-r4-fresh
rm -f "$BASE/godot/godot-import-pose.png" "$BASE/godot/godot-import-pose.png.import"
cp "$BASE/snake-sectional-r4-fresh.glb" "$BASE/godot/snake-sectional-r4-fresh.glb"
GODOT=/mnt/c/Users/Moore/Godot/Godot_v4.7.2-stable_win64_console.exe
PROJECT=$(wslpath -w "$PWD/$BASE/godot")
"$GODOT" --headless --editor --path "$PROJECT" --quit > "$BASE/godot/import.log" 2>&1
"$GODOT" --headless --path "$PROJECT" --script res://check.gd > "$BASE/godot/check.log" 2>&1
"$GODOT" --path "$PROJECT" --rendering-method gl_compatibility --resolution 1280x720 --script res://capture.gd > "$BASE/godot/capture.log" 2>&1
