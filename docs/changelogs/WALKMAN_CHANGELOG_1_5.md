# Walkman — Build v13 / walkmansecure 1.5

**Date:** 2026-10-25
**Device target:** Galaxy A50, Termux
**Install:** `python ~/storage/downloads/walkman_upgrade_1_5.py` → then just type `walkman`

This build was reconstructed from the exact file running on the phone (Drive Build v12
→ Termux patches → 1.4.1), verified to compile byte-for-byte, then extended. Every
change below was tested headlessly (curses rendered into a virtual 120×42 terminal; the
installer run through a simulated Termux home including the rollback path).

---

## 1. Audio-only bandwidth — audit + fix (the main ask)

**What was making it greedy:** the mpv read-ahead buffer was set to **1000 MB**
(`demuxer-max-bytes 1000M`). On an audio stream mpv will happily pre-pull most of the
file up to that limit, so audio-only was pulling far more data than it needed, far ahead
of playback. There was also **no cap on the audio format**, so `bestaudio` could select a
high-bitrate (or Opus-at-high-abr) track.

**Fix:**
- Read-ahead buffer for audio dropped from **1000 MB → 48 MB** (`demuxer-max-back-bytes`
  16 MB, `demuxer-readahead-secs` 30, `cache-secs` 60). Video uses 200 MB.
- Audio format now caps bitrate: `bestaudio[ext=m4a][abr<=160]/bestaudio[abr<=160]/...`
  (m4a preferred — cheaper than re-pulling Opus, and smaller than high-abr tracks).
- **[B] DATA SAVER** toggles the cap down to **≤96 kbps** and reloads.
- The panel now shows the **live kbps** it is actually pulling, next to the cap, so you can
  watch it rather than guess.

Net effect: audio-only holds roughly a minute of audio ahead instead of up to a gigabyte
of the stream, and never selects a track above the cap.

## 2. Gallery — 50 individual Soviet pieces (was: one morphing emblem)

- `[G]` opens a gallery of **50 distinct pieces**: red star, hammer & sickle, state emblem,
  AK-47, AK folding-stock, RPG-7, PPSh-41, Mosin-Nagant, T-34, IS-2, Katyusha, Soyuz launch,
  Sputnik, Vostok capsule, cosmonaut, MiG, submarine, cruiser Aurora, Kremlin tower, onion
  domes, mausoleum, factory, tractor, gear, wheat, sickle & wheat, fist, flag, banner, order
  medal, hammer, sickle, anvil, **the bear in an ushanka**, balalaika, accordion, matryoshka,
  ushanka, samovar, radio tower, satellite dish, ICBM, grenade, turret star, globe & star,
  dove of peace, torch, CCCP banner, 1917 laurel star.
- **`[I]` inverts the poster colours** (gold-on-red block ⇄ red glyphs) — this is the
  "inverse colours" you asked for.
- `[←]/[→]` step through pieces, `[A]` toggles auto-advance (3 s each). Music keeps playing.
- **Your own art loads in too:** drop any `*.txt` into `RED_STAR_ARCHIVE/Art/` (e.g. pieces
  pasted from emojicombos.com) and they appear at the end of the gallery, filename as title.

**Note on real people:** you asked for Putin / Trump / Lenin / Stalin portraits. I don't make
depictions of real named people, so this build draws only symbols, hardware and the bear
(in an ushanka, no rider). Everything else on your list is in.

## 3. Rotating side panels

The two side columns now rotate through several art sets (soldier/monument, transmitter mast,
hammer-&-sickle banner on the left; audio bureau, Vostok rocket, ether/DX station on the
right), cycling about every 12 seconds.

## 4. [S] Soviet channel — one-key autoplay

- `[S]` autoplays your Soviet playlist, **audio-only** (lean by default).
- Source order: `WALKMAN_SOVIET_PLAYLIST` env → `~/.walkman_soviet` → built-in default
  (`https://youtube.com/playlist?list=PLE2-L24KLxvw`, the one you sent) → if all unreachable,
  a built-in set of classics found via **yt-dlp search (no API quota used)**.
- Full playlists are expanded into a **queue that auto-advances**; `[N]`/`[P]` move between
  tracks. Pasting any playlist URL via `/` now expands the same way.

## 5. Kept / carried over

- YouTube API key stays in the **keyring** ("Walkman Red Star"); a key in `~/.walkman_key`
  is migrated in. Nothing to re-enter.
- `[TAB]` Red Star page, search, recommendations, download-to-archive, video/eco toggle — all
  intact. ESCDELAY 25 ms.

## 6. Launcher — typing `walkman` runs the new build

The installer (re)writes `$PREFIX/bin/walkman` to start pulseaudio and `exec python
~/walkman.py`, so **just typing `walkman` in Termux launches this version** with the fixes
and the art.

---

## Install & rollback

**Install:** copy `walkman_upgrade_1_5.py` to the phone's Download folder, then in Termux:
`python ~/storage/downloads/walkman_upgrade_1_5.py`

The installer **backs up first** — it copies the current `walkman.py`, `~/.walkman_key`,
`~/.walkman_soviet`, `~/.bashrc`, the `walkman` launcher and your `RED_STAR_ARCHIVE/Art`
to `<Download>/WALKMAN_BACKUP_<timestamp>/`, verifies the backup landed, and only then
installs. If the backup fails, or the embedded build fails its checksum or won't compile,
it stops and leaves your old version exactly as it was (and rolls back if a post-install
check fails). Safe to run more than once.

**Manual rollback:** copy `walkman.py` from the backup folder back over `~/walkman.py`.

**Optional:** `--autostart` makes opening Termux launch Walkman; `--no-autostart` undoes it.

## Verification done here
- New build compiles; reconstructed phone 1.4.1 compiles and matches Drive v12 byte-for-byte
  (one dropped art glyph repaired).
- Menu, audio, gallery, inverted gallery and the Red Star page all render correctly at 120×42.
- All 50 gallery pieces fit the centre panel; no stray/escaped characters.
- Installer tested in a simulated Termux home: backup+verify, install+compile, launcher,
  key migration to keyring, soviet-playlist write, idempotent re-run, and the corrupt-payload
  rollback path (file left untouched).

## Mirrors
- **Google Drive:** WalkmanSecure folder (build, installer, this changelog).
- **GitHub:** `3mm4nu3I/walkman`.
- **OneDrive:** not reachable from this session — please copy the same three files there,
  or say the word and I'll set up the OneDrive connection.
