#!/bin/bash
set -e
export R3_MODE=${1:-preview} R3_TAG=${2:-h} R3_BASELINE=${3:-0} R3_DEVICE=CPU
export WSLENV=R3_MODE:R3_TAG:R3_BASELINE:R3_DEVICE
LOG="benchmarks/forge-snake-r3/logs/render-${R3_MODE}-${R3_TAG}-baseline${R3_BASELINE}.log"
/mnt/c/Users/Moore/Blender/blender-4.5.14-windows-x64/blender.exe -b --python "$(wslpath -w "$PWD/benchmarks/forge-snake-r3/source/render.py")" > "$LOG" 2>&1
rg -q R3_RENDER_COMPLETE "$LOG"
