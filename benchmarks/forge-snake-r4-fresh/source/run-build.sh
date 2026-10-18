#!/bin/bash
set -e
BASE=benchmarks/forge-snake-r4-fresh
/mnt/c/Users/Moore/Blender/blender-4.5.14-windows-x64/blender.exe -b --python "$(wslpath -w "$PWD/$BASE/source/build_r4.py")" > "$BASE/logs/build-reproduce.log" 2>&1
rg -q R4_BUILD_COMPLETE "$BASE/logs/build-reproduce.log"
