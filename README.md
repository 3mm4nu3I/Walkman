# WALKMAN // RED STAR SIGNAL DIRECTORATE

**A lightweight terminal media player for YouTube audio and video, built for an Android phone.**
Python, curses, mpv (JSON IPC) and yt-dlp, running in Termux. It started from one complaint: a
YouTube tab in a browser was eating the phone's RAM. Walkman replaces that tab with a 120×42
terminal UI.

Measured on a Galaxy A50 (25 Oct 2026): ad-free audio at **124–127 kbps** under a 160 kbps cap,
playing alongside another media app.

---

## Engineering highlights

**Bandwidth.** Audio-only mode was over-fetching. The cause was mpv's read-ahead buffer, set to
1000 MB, and no cap on the audio format.
- The fix: a 48 MB buffer (16 MB back-buffer, 30 s read-ahead) for audio, and a format selector
  capped at ≤160 kbps that prefers m4a.
- **[B]** is a data saver that caps at ≤96 kbps.
- The panel shows the **live bitrate** mpv reports, so the cap can be checked rather than assumed.

**Playlists without API quota.** Playlist URLs and searches are expanded through yt-dlp's flat
extraction into an auto-advancing queue. The YouTube Data API key is only needed for interactive
search, and it lives in the OS keyring (`keyring`), not in a file.

**Safe upgrades.** The installer (`walkman_upgrade_1_6.py`) takes these steps in order:
1. Verifies its embedded payloads (zlib + base64) against SHA-256 before touching anything.
2. Backs up the current install and checks the copy byte-for-byte.
3. Compiles the new files and runs an on-device self-test of the 3D engine, which reports ms per
   frame.
4. Installs `walkman-rollback` (newest backup, or `--1.5` for a known-good build) and
   `walkman --safe`.
A corrupt payload aborts with nothing changed.

**Fault isolation.** All art lives in `walkman_art.py` and is imported behind a guard. If that
file is missing or broken, Walkman runs exactly like the previous release, and draw errors are
caught and reported in the status line instead of crashing playback.

**A software 3D renderer in ASCII.** `walkman_art.py` contains a small 3D engine written from
scratch in pure Python:
- Mesh primitives: lathe, prism, box, sphere and a beveled star.
- Outward face orientation and back-face culling.
- Barycentric triangle rasterisation with a z-buffer, and flat Lambert shading mapped to a
  character ramp.
- 3D line segments for thin parts such as antennas.
- A fit-to-viewport scale sampled over the full rotation, and adaptive frame skipping so slow
  phones drop frames instead of lagging the UI.

It drives 19 models (T-34, KV-1, IS-2, T-55, T-72, Vostok, Soyuz, N1, Energia/Buran, Sputnik-1,
Lunokhod-1, Mir, Typhoon, B-59, MiG-21, a red star, a bear in an ushanka, AK-47, RPG-7). Each
frame takes about 2 ms on a desktop CPU.

## Keys

| Key | | Key | |
|---|---|---|---|
| `/` | search or paste a URL | `S` | Soviet channel: autoplay the playlist in `~/.walkman_soviet` |
| `Space` | pause | `N` / `P` | next / previous track |
| `←` `→` / `↑` `↓` | seek / volume | `B` | data saver (≤96 kbps) |
| `V` | video on/off | `D` | download to `RED_STAR_ARCHIVE/` |
| `G` | gallery of 50 ASCII pieces (`I` inverts colours) | `TAB` | Red Star page |
| `H` | 3D hall of machines | `W` | Duga: the Russian Woodpecker radar, with a live 10 Hz tick |
| `O` | B-59, 27 October 1962: the three keys | `K` | Red Choir: animated Kazachok |
| `F` | Fyodor: original line art and aphorisms | `Z` | ambient 3D model on/off |
| `Q` | quit | | |

## Install (Termux)

```bash
pkg install python mpv pulseaudio
pip install yt-dlp python-mpv-jsonipc keyring keyrings.alt
python ~/storage/downloads/walkman_upgrade_1_6.py     # backs up first, then installs
walkman                                               # that's it
```

Something wrong? Run `walkman --safe` (starts without the art), `walkman-rollback`, or
`walkman-rollback --1.5`. Environment switches: `WALKMAN_AMBIENT=off`, `WALKMAN_FYODOR=off`.

## Files

```
walkman_build_v14_1.6.py   the player (installs as ~/walkman.py)
walkman_art.py             3D engine, models and art pages (optional module)
walkman_upgrade_1_6.py     backup-first installer with both files and a known-good 1.5 embedded
walkman_build_v13_1.5.py   previous release, kept for reference (also branch rollback-1.5-working)
WALKMAN_CHANGELOG_*.md     what changed, why, and what was and was not verified
walkmansecure.py, *.bat    the original desktop (Windows) build and its helpers
```

## Verification

- Every page was rendered in a virtual 120×42 terminal (pyte + pty) and driven key by key.
- All 19 models were rendered at 24 angles each.
- The installer was exercised in a simulated Termux home: backup, install, self-test, rollback,
  re-run, and a corrupt payload.
- Then run on the target phone.
- Not covered by automated tests: real mpv and YouTube behaviour. That is confirmed only by
  use on the device.

## Content

The art is machines, symbols and invented figures: no portraits of real people. Historical pages
state their facts plainly. For example, Vasili Arkhipov was the flotilla chief of staff aboard
B-59, not its captain. The Dostoevsky lines are original and labelled as not being quotations.

## How this was built

Walkman is designed, directed, tested on device and operated by **Bram Noffels**. Much of the code
was written with AI coding assistants under that direction. Every release has a changelog stating
what was verified and what was not.

**Author:** Bram Noffels, Antwerp · [github.com/3mm4nu3I](https://github.com/3mm4nu3I) · see also
[Project Hannibal](https://github.com/3mm4nu3I/hannibal-beta-2.0)
