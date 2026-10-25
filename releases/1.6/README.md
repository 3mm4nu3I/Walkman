# Walkman 1.6 — known good

The release that was confirmed running on the Galaxy A50 on 25 Oct 2026 (GitHub commit `12f0be9`, branch `rollback-1.6-working` at `e23d050`).

- `walkman_build_v14_1.6.py` → install as `~/walkman.py`
- `walkman_art_1.6.py` → install as `~/walkman_art.py`
- `walkman_upgrade_1_6.py` → the original 1.6 installer (self-contained)

SHA-256: player `c571a44c…8797c`, art `c8d2fb8d…f1faf275`, installer `2725a6b1…7b2ab795`.
The 1.6.1 installer embeds these two files; `walkman-rollback --1.6` restores them.
