#!/usr/bin/env bash
set -euo pipefail
# R2_ROOT must contain the shipped R1 packed source as r1-baseline.blend.
# The R1 source came from C:\Users\Moore\forge-r1\out\snake-sectional-r1.blend.
: "${R2_ROOT:?Set R2_ROOT to a writable build directory containing r1-baseline.blend}"
: "${BLENDER:?Set BLENDER to Blender 4.5.14 executable}"
here=$(cd -- "$(dirname -- "$0")" && pwd)
cp "$here/build_r2.py" "$here/weather.py" "$R2_ROOT/"
R2_MODE=final R2_TAG=final "$BLENDER" -b --python "$R2_ROOT/build_r2.py"
