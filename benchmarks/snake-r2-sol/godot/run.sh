#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
fixture=$(mktemp -d /tmp/snake-r2-godot.XXXXXX)
cp "$here/project.godot" "$here/check.gd" "$here/capture.gd" "$fixture/"
cp "$here/../snake-sectional-r2.glb" "$fixture/"
godot --headless --editor --path "$fixture" --import --quit > "$here/import.log" 2>&1
godot --headless --path "$fixture" --script check.gd > "$here/check.log" 2>&1
LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s '-screen 0 1280x720x24' godot --path "$fixture" --rendering-method gl_compatibility --audio-driver Dummy --script capture.gd > "$here/capture.log" 2>&1
cp "$fixture/godot-import-pose.png" "$here/"
printf 'Fresh fixture retained at %s\n' "$fixture"
