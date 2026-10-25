# Walkman changelog

Newest first. Detail, checksums and what was and was not verified are in `docs/changelogs/`.

## 1.6.1 — 2026-10-25 — Soyuz edition
`[U]` Baikonur launch sequence (countdown, ignition, liftoff, separations, orbit) with a 3D Soyuz spacecraft; once-a-day start-up splash; 20 machines in the hall; installer keeps known-good 1.6 and 1.5 (`walkman-rollback --1.6`). Reproducible build scripts and headless tests added to the repo. → [details](docs/changelogs/WALKMAN_CHANGELOG_1_6_1.md)

## 1.6 — 2026-10-25 — art release
`walkman_art.py`: software 3D ASCII renderer; hall of 19 machines; pages for Duga, B-59 (27 Oct 1962), Red Choir, Fyodor; ambient 3D on the main screen; backup-first installer with self-test and rollback. → [details](docs/changelogs/WALKMAN_CHANGELOG_1_6.md) · files in `releases/1.6/`

## 1.5 — 2026-10-25
Audio bandwidth fix (1000 MB read-ahead to 48 MB, ≤160 kbps cap, `[B]` data saver, live kbps), 50-piece gallery, Soviet autoplay channel. → [details](docs/changelogs/WALKMAN_CHANGELOG_1_5.md) · files in `releases/1.5/`

## 1.4.1 — 2026-10-22
YouTube API key kept in the OS keyring.

## 1.4 — 2026-10-21
`is_url()` restored, `[TAB]` Red Star page, snappier ESC.

## Earlier
`walkmansecure` 1.0 to 1.2 and the Windows desktop build are kept as they were (`walkmansecure.py`, the `.bat` files, `yt-dlp.exe`).
