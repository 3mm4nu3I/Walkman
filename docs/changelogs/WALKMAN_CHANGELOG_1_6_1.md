# Walkman — Build v14 / walkmansecure 1.6.1  ("Soyuz edition")

**Date:** 2026-10-25  **Device:** Galaxy A50, Termux
**Install:** `python ~/storage/downloads/walkman_upgrade_1_6_1.py` → type `walkman`
**Roll back:** `walkman-rollback` (newest backup) · `walkman-rollback --1.6` (known-good 1.6, player + art) · `walkman-rollback --1.5` · `walkman --safe` (no art, nothing to undo)

## Backups taken before any change
- GitHub branch `rollback-1.6-working` → commit `e23d050` (the 1.6 that was confirmed running on the phone), alongside `rollback-1.5-working` → `a0e46f4`.
- `releases/1.6/` and `releases/1.5/` in the repo hold the exact 1.6 and 1.5 files (SHA-256 below).
- The installer backs up the phone first (`WALKMAN_BACKUP_<timestamp>` in Downloads), verifies the copy byte for byte, then installs. It also writes known-good 1.6 (`~/.walkman_known_good_1_6.py` + `_art`) and known-good 1.5 (`~/.walkman_known_good_1_5.py`).

## New in 1.6.1
| Key | What |
|---|---|
| **U** | **Soyuz.** A Baikonur launch in ASCII: T-10 countdown, ignition (ZAZHIGANIE), liftoff ("Poyekhali!"), strap-on separation, escape tower and fairing away, third stage, then a rotating 3D Soyuz spacecraft over the Earth's limb. A mission clock shows T+ time. `R` restarts, `ENTER` plays Soviet space songs, `2` plays the Gagarin launch audio (yt-dlp search, no API quota). Six rotating fact lines. |
| splash | A four-second countdown and liftoff when Walkman starts, **once per day**; any key skips. `WALKMAN_SPLASH=off` disables, `=always` shows it every start. |
| hall | A **3D Soyuz spacecraft** (orbital, descent and service modules, two solar wings): 20 machines now. |
| main screen | Soyuz, the spacecraft and Vostok join the ambient rotation. Menu line now reads `[U] SOYUZ`. |
| installer | Embeds known-good 1.6 as well as 1.5; `walkman-rollback --1.6`. |

Everything new lives in `walkman_art.py` (plus a three-line splash hook in the player), inside try/except. Missing or broken art means Walkman behaves like 1.5; draw errors go to the status line.

## Facts on the Soyuz page (and the caveat)
Sputnik 1, 4 Oct 1957, on an R-7. Vostok 1, 12 Apr 1961, Baikonur Site 1, Gagarin, one orbit of 108 minutes. R-7 family: four strap-ons round a core, 20 main combustion chambers. Soyuz 1, 23 Apr 1967 (Komarov was killed; the page says so plainly). Soyuz 19 docked with Apollo, 17 Jul 1975. The sequence is **time-lapsed and stylised**; event times (boosters about T+2:00, tower and fairing about T+2:40, orbit about T+9) are approximate crewed-Soyuz values and the page says so. No portraits of real people.

## Verified here (headless, 120×42 virtual terminal)
- Compiles; `selftest()` renders all 20 models and six launch frames (1.6 ms per frame here).
- Launch page keyed through (`u`, `r`, `ENTER`, `2`, `ESC`, `TAB`), plus every 1.6 page; splash shows once, skips on a key, and the once-a-day flag is respected.
- Safe mode and a missing art module both behave like 1.5.
- Installer in a simulated Termux home: backup and verify, install, self-test, launcher, `walkman-rollback` (`--list`, newest, `--1.6`, `--1.5`), re-run, and a corrupt payload aborting before anything is touched.
- `build/make_art.sh` and `build/make_installer.py` reproduce the shipped files byte for byte.

**Not verified:** real mpv/YouTube/Termux behaviour and the real frame rate on the A50 (the engine is about 2 ms per frame on a server; expect roughly 30× slower on the phone — frame skipping keeps the UI responsive). Whether Termux's font draws the Cyrillic page title (`СОЮЗ`) is also untested.

## SHA-256
```
walkman_build_v14_1.6.1.py   6453f1eff8f347a3ef615b1ed7664959d12cbaa8daab1765ce73aba1fbd9d1a7
walkman_art.py               e159a0bf5e0e8d1be137001b898fb110fb55038d8aad5e13c4ac79405136cbf9
walkman_upgrade_1_6_1.py     777a657196725626443688c024d53b42df13fe10e131534fec6bc82893394be2
releases/1.6 player          c571a44c82617e03c109f9c0e6729c7be9703326a807ccbbea254e98b748797c
releases/1.6 art             c8d2fb8d4f2780ddd5dcf83ffcac54f6c362a9cfcb81efb3d51cb1f1b3faf275
releases/1.5 player          0c3fc14d7e4f7600771dde3b358a1f4495e2b2f6ff8dc67e3787d2e5f1dca177
```

## Mirrors
GitHub `3mm4nu3I/walkman` · Google Drive (WalkmanSecure and the master bundle) · the laptop (`WALKMAN_STANDALONE` and Downloads) · the A50 via the installer · OneDrive: see the bundle's `00_START_HERE.md` for status.
