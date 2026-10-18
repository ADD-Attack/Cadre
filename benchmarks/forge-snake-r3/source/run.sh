#!/bin/bash
set -e
export R3_MODE=${1:-preview} R3_TAG=${2:-a} R3_PARAMS=${3:-'{}'}
export WSLENV=R3_MODE:R3_TAG:R3_PARAMS
/mnt/c/Users/Moore/Blender/blender-4.5.14-windows-x64/blender.exe -b --python "$(wslpath -w "$PWD/benchmarks/forge-snake-r3/source/build_r3.py")" > "benchmarks/forge-snake-r3/logs/build-${R3_TAG}.log" 2>&1

rg -q R3_FINISHED "benchmarks/forge-snake-r3/logs/build-${R3_TAG}.log"
