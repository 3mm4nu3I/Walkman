# Walkman — Build v14 / walkmansecure 1.6  ("the art release")

**Date:** 2026-10-25  **Device:** Galaxy A50, Termux
**Install:** `python ~/storage/downloads/walkman_upgrade_1_6.py` → type `walkman`
**Roll back:** `walkman-rollback` (newest backup) · `walkman-rollback --1.5` (known-good 1.5) · `walkman --safe` (no art, nothing to undo)

## Backups taken before any change
- Local snapshot of the verified-running 1.5 (build, installer, changelog): `backup_1_5_working/` — SHA-256 of `walkman.py`
  `0c3fc14d7e4f7600771dde3b358a1f4495e2b2f6ff8dc67e3787d2e5f1dca177`.
- GitHub `3mm4nu3I/walkman`: branch `rollback-1.5-working` → commit `a0e46f4` (a tag push was refused with HTTP 403, so a branch is used).
- The 1.6 installer **backs up the phone first** (`WALKMAN_BACKUP_<timestamp>` in Downloads), verifies the copy byte-for-byte, and only then installs.
- It also writes a known-good 1.5 to `~/.walkman_known_good_1_5.py`.

## New in 1.6
Everything lives in a separate file, `walkman_art.py`, loaded inside try/except. Missing or broken ⇒ Walkman behaves exactly like 1.5.

| Key | What |
|---|---|
| **H** | **3D hall of machines** — real software 3D (z-buffered, lit, rotating), drawn in ASCII. 19 models: T-34, KV-1, IS-2, T-55, T-72, Vostok, Soyuz, N1, Energia/Buran, Sputnik-1, Lunokhod-1, Mir, Typhoon ("Red October"), B-59 (Foxtrot), MiG-21, red star, **bear in an ushanka**, AK-47, RPG-7. ←/→ step, **I** inverse colours, **A** auto. |
| **W** | **Duga** — a whole page for the Russian Woodpecker: the array, a live 10 Hz tick, sky-wave diagram, oscilloscope, verified facts. **ENTER** plays Woodpecker recordings. |
| **O** | **B-59, 27 Oct 1962** — "the three keys" (YES / YES / NO), swinging 3D submarine, sonar ping, anniversary countdown. |
| **K** | **Red Choir** — animated Kazachok squat-kick dance, Kazakh yurt/steppe, dombra player. ENTER = Kazachok, **2** = Kazakh dombra (yt-dlp search, no API quota). |
| **F** | **Fyodor** — 10 pieces of original line art with original aphorisms (clearly marked *not quotations*). He also **appears on his own** in the empty lower half of the main screen every few minutes and dissolves away. |
| **Z** | Toggle the ambient 3D machine now shown on the lower half of the main screen. |

Env switches: `WALKMAN_AMBIENT=off`, `WALKMAN_FYODOR=off`, `WALKMAN_SAFE=1`.

Also: `Player.start_search_queue()` (audio-only queue from a yt-dlp search), adaptive frame skipping so slow phones drop frames instead of lagging the UI, an on-device 3D self-test in the installer (prints ms/frame; disables art if it fails).

## Content notes
- No portraits of real people (same rule as 1.5). B-59 and Arkhipov are told through the boat, the three boxes and the text.
- Arkhipov was **not the captain** (that was Valentin Savitsky): he was the flotilla chief of staff aboard B-59. The page says so.
- "Kazakh dance": the famous Red Army Choir squat-kick is the **Kazachok** (Cossack). Both are on the page.
- Dostoevsky lines are original and labelled as such; only fictional-book titles and a detail or two are borrowed.

## Verified here (headless)
Compiles; installer tested in a simulated Termux home (backup+verify, install, self-test, launcher, rollback tool, `--list`, `--1.5`, re-run, corrupt payload aborts untouched); all 19 models × 24 angles render; every page rendered at 120×42 and keyed through in a pty (H/W/K/O/F/Z, arrows, ENTER, ESC, TAB, G, Q); safe mode and missing-art-module both behave like 1.5.
**Not verified:** real mpv/YouTube/Termux behaviour; real frame rate on the A50 (the engine is ~2 ms/frame on this server, expect roughly 30× slower on the phone).

## Mirrors
GitHub `3mm4nu3I/walkman` · Google Drive WalkmanSecure · OneDrive: not reachable from this session (copy the three files by hand).
