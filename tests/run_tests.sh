#!/bin/sh
# Headless checks for Walkman 1.6.1. Needs: python3, pip install pyte pillow
# Renders every page in a virtual 120x42 terminal and drives it key by key.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
T="$(mktemp -d)"; cp "$HERE"/_*.py "$HERE"/preview_models.py "$T"/
cp "$ROOT/walkman_build_v14_1.6.1.py" "$T/walkman.py"; cp "$ROOT/walkman_art.py" "$T/"
mkdir -p "$T/src"; cp "$HERE/preview_models.py" "$T/src/preview.py"
cd "$T"
python3 -c "import walkman_art as A; print('selftest', A.selftest())"
echo "--- splash (first run of the day) ---";  WALKMAN_SPLASH=on python3 _splash_test.py | tail -4
echo "--- every page, keyed through ---"
WALKMAN_SPLASH=off python3 _interactive.py "u|r|ENTER|2|ESC|h|RIGHT|RIGHT|RIGHT|RIGHT|RIGHT|RIGHT|RIGHT|ESC|w|ESC|k|ESC|o|ESC|f|ESC|z|z|q" | tail -8
echo "--- safe mode ---"; WALKMAN_SAFE=1 python3 _interactive.py "u|h|q" | tail -2
echo "temp dir: $T"
