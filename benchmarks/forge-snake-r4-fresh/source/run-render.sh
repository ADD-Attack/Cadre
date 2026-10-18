#!/bin/bash
set -e
export R4_MODE=${1:-preview} R4_TAG=${2:-b} R4_BASELINE=${3:-0}
export WSLENV=R4_MODE:R4_TAG:R4_BASELINE
/mnt/c/Users/Moore/Blender/blender-4.5.14-windows-x64/blender.exe -b --python "$(wslpath -w "$PWD/benchmarks/forge-snake-r4-fresh/source/render_r4.py")" > "benchmarks/forge-snake-r4-fresh/logs/render-${R4_MODE}-${R4_TAG}-baseline${R4_BASELINE}.log" 2>&1
rg -q R4_RENDER_COMPLETE "benchmarks/forge-snake-r4-fresh/logs/render-${R4_MODE}-${R4_TAG}-baseline${R4_BASELINE}.log"
