# Walkman roadmap

## Done
- Terminal YouTube audio/video player (Python, curses, mpv JSON IPC, yt-dlp) for Termux on a Galaxy A50.
- 1.5: audio bandwidth fixed and measured (124–127 kbps on the device under a 160 kbps cap), gallery, Soviet channel.
- 1.6: optional art module with a from-scratch 3D ASCII renderer, six pages, backup-first installer, rollback and safe mode.
- 1.6.1: Soyuz launch page, spacecraft model, once-a-day splash, known-good 1.6 in the installer, reproducible build and tests in the repo.

## Open
1. Measure the real frame rate of the 3D pages on the A50 and tune the frame-skip thresholds from the numbers.
2. Check how Termux's font draws the Cyrillic page titles; add an ASCII fallback if it does not.
3. Repo hygiene: `yt-dlp.exe` (17 MB) is committed. It could be dropped from the tree and fetched by the Windows updater instead.
4. Turn `tests/run_tests.sh` into a CI job (it needs only `python3`, `pyte` and `pillow`).
5. Bring the Windows desktop copies (`walkmansecure.py`, `.bat` files) up to the 1.6.x feature set, or retire them.
6. Anything the owner wants from the "last upgrade" — not yet specified.

Not planned: portraits of real people, anything that needs a paid API.
