#!/bin/bash
# usage: run.sh MODE TAG 'json-params'
export FORGE_MODE=$1 FORGE_TAG=$2 FORGE_PARAMS=${3:-{\}} FORGE_OUTPUT='C:\Users\Moore\forge-r1\out' FORGE_BASE='C:\Users\Moore\forge-r1\pack\fix2\snake-sectional.blend'
export WSLENV=FORGE_MODE:FORGE_TAG:FORGE_PARAMS:FORGE_OUTPUT:FORGE_BASE
"/mnt/c/Users/Moore/Blender/blender-4.5.14-windows-x64/blender.exe" -b --python 'C:\Users\Moore\forge-r1\forge_r1.py' > out-$2.log 2>&1
grep -E "HEAD_EDIT|ATLAS_READY|R1_COUNTS|R1_EXPORTED|R1_DONE|Error|Traceback|Assertion|line [0-9]+" out-$2.log | head -30
