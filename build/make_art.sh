#!/bin/sh
# Rebuild walkman_art.py from its parts (run from anywhere).
cd "$(dirname "$0")" || exit 1
cat src/p1_engine.py src/p2_models.py src/p3_data.py src/p3b_fyodor.py src/p3c_launch.py src/p4_pages.py > ../walkman_art.py \
  && python3 -m py_compile ../walkman_art.py && echo "ART_OK $(sha256sum ../walkman_art.py | cut -c1-16)"
