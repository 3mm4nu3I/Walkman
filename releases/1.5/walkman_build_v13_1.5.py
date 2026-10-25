#!/usr/bin/env python3
"""
YT Terminal Player - RED STAR EDITION (Build v13 / walkmansecure 1.5)

Changelog
  1.4   (2026-10-21)  Restored is_url() + [TAB] Red Star page, snappier ESC.
  1.4.1 (2026-10-22)  YouTube API key kept in the keyring ("Walkman Red Star").
  1.5   (2026-10-25)
    - AUDIO BANDWIDTH: audio-only was greedy. The mpv read-ahead buffer was
      1000 MB (it pre-pulled far more of the stream than needed). Audio now uses
      a 48 MB buffer and caps the stream to <=160 kbps (m4a preferred). New
      [B] DATA SAVER drops that to <=96 kbps. The panel shows the live kbps so
      you can see what it is actually pulling.
    - GALLERY: replaced the single morphing emblem with a gallery of 50 distinct
      Soviet pieces (hammer & sickle, red star, AK, RPG, tanks, rockets, Sputnik,
      the bear in an ushanka, and more). [I] inverts the poster colours,
      LEFT/RIGHT step through pieces, [A] toggles auto-advance (3 s each).
      Any *.txt art you drop in RED_STAR_ARCHIVE/Art is loaded in too.
    - SIDES: the side panels now rotate through several art sets.
    - [S] SOVIET: one key autoplays the Soviet playlist (audio-only), taken from
      ~/.walkman_soviet if present, else the built-in default playlist, else a
      built-in set of classics found via yt-dlp search (no API quota used).
      Full playlists are expanded into a queue that auto-advances.
    - No portraits of real people (by request this build draws only symbols,
      hardware and the bear).
"""

import html
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import getpass
import time

# --- PRE-INIT TERMINAL RESIZE ---
def force_terminal_size():
    try:
        if platform.system() == "Windows": os.system("mode con cols=120 lines=42")
        else: sys.stdout.write("\x1b[8;42;120t"); sys.stdout.flush()
    except Exception: pass

ARCHIVE_DIR = "RED_STAR_ARCHIVE"
AUDIO_DIR = os.path.join(ARCHIVE_DIR, "Audio")
VIDEO_DIR = os.path.join(ARCHIVE_DIR, "Video")
ART_DIR = os.path.join(ARCHIVE_DIR, "Art")
for d in (AUDIO_DIR, VIDEO_DIR, ART_DIR): os.makedirs(d, exist_ok=True)

# Soviet playlist: ~/.walkman_soviet (one URL per file) overrides this default.
SOVIET_PLAYLIST_DEFAULT = "https://youtube.com/playlist?list=PLE2-L24KLxvw"
SOVIET_LINK_FILE = os.path.expanduser("~/.walkman_soviet")
SOVIET_FALLBACK = [
    "Katyusha Red Army Choir", "Kalinka Red Army Choir", "Soviet Anthem instrumental",
    "Polyushko Pole", "The Sacred War Red Army Choir", "Moscow Nights Podmoskovnye Vechera",
    "Smuglyanka", "Den Pobedy", "Oy to ne vecher", "Ochi Chyornye",
]

def pip_install(package):
    print(f"Installing {package} (one time only)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

try: import curses
except ImportError:
    if platform.system() != "Windows": raise
    pip_install("windows-curses")
    import curses

try: from python_mpv_jsonipc import MPV, MPVError
except ImportError:
    pip_install("python-mpv-jsonipc")
    from python_mpv_jsonipc import MPV, MPVError

try: from yt_dlp import YoutubeDL
except ImportError:
    pip_install("yt-dlp")
    from yt_dlp import YoutubeDL

def detect_active_browser():
    user_home = os.path.expanduser("~")
    if platform.system() == "Windows":
        browsers = [
            ("brave", os.path.join(user_home, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")),
            ("chrome", os.path.join(user_home, "AppData", "Local", "Google", "Chrome", "User Data")),
            ("edge", os.path.join(user_home, "AppData", "Local", "Microsoft", "Edge", "User Data")),
            ("firefox", os.path.join(user_home, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")),
        ]
    else:
        browsers = [
            ("brave", os.path.join(user_home, ".config", "BraveSoftware", "Brave-Browser")),
            ("chrome", os.path.join(user_home, ".config", "google-chrome")),
            ("firefox", os.path.join(user_home, ".mozilla", "firefox")),
        ]
    for name, path in browsers:
        if os.path.exists(path):
            try:
                if os.listdir(path): return name
            except Exception: pass
    return None

AUTO_DETECTED_BROWSER = detect_active_browser()

def _keyring_key():
    """YouTube API key: env var, else the keyring ("Walkman Red Star"), else a one-time hidden prompt saved to the keyring."""
    import getpass
    val = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if val:
        return val
    try:
        import keyring
    except ImportError:
        pip_install("keyring")
        import keyring
    service, name = "Walkman Red Star", "YOUTUBE_API_KEY"
    try:
        val = (keyring.get_password(service, name) or "").strip()
    except Exception:
        val = ""
    if val:
        return val
    legacy = os.path.expanduser("~/.walkman_key")
    try:
        with open(legacy, encoding="utf-8") as fh:
            val = fh.read().strip()
    except OSError:
        val = ""
    if not val:
        try:
            val = getpass.getpass("ENTER YOUTUBE API KEY (HIDDEN): ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""
    if val:
        try:
            keyring.set_password(service, name, val)
            if (keyring.get_password(service, name) or "").strip() == val and os.path.exists(legacy):
                os.remove(legacy)
        except Exception as exc:
            print(f"Could not save the key to the keyring ({exc}); using it for this session only.")
    return val

YOUTUBE_API_KEY = _keyring_key()
URL_RE = re.compile(r"^https?://", re.I)
def is_url(text): return bool(URL_RE.match(text.strip()))
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

def read_soviet_link():
    env = os.environ.get("WALKMAN_SOVIET_PLAYLIST", "").strip()
    if env: return env
    for p in (SOVIET_LINK_FILE, os.path.join(ARCHIVE_DIR, "soviet_playlist.txt")):
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"): return line
        except OSError:
            pass
    return SOVIET_PLAYLIST_DEFAULT

# =====================================================================
#  THE GALLERY  -  50 individual Red Star pieces (generic symbols only)
# =====================================================================
SOVIET_ART = [
("RED STAR", r'''
        *
       ***
      *****
  *************
   ***********
    *********
    *********
   ***   ***
  **       **
'''),
("HAMMER & SICKLE", r'''
          __
         (  `-._
          `-._  `-._
     __       `-.   `.
    /  |   _____  `.   |
   /   |  /     `-. |  |
  |  O |_|        |_|  |
   \   |            __/
    \__|       ___/
       `._____/
       ========
'''),
("EMBLEM IN WHEAT", r'''
     .  __  .
    (( /  ) ))
   . )(  (  )( .
  (( (| H+S |) ))
   ) )|     |( (
  (( (|_____|) ))
   ) /_______\ (
  ((/ * CCCP * \))
   `._________.'
'''),
("AK-47", r'''
   ___
  /  _|______________
 |  (_|_._._._._._.-. \
 |     |===========| | |
  \____|           |_|/
   /  /             \
  |__|  * RED ARMY *
'''),
("AK (FOLDING STOCK)", r'''
  [####]___________
  |  o |===========|----.
  |____|           |    |
   |  |  _______    `--.|
   |__| |       |      ||
        |_______|   ___||
                   (____)
'''),
("RPG-7", r'''
        /\
       /  \
      / () \
     |  ||  |
      \ || /
   _____||_____________
  (______________o_____)===
       |   |
      (|   |)  * PROTIVOTANK *
'''),
("PPSh-41", r'''
        _____
   ____/     \____________
  |   |  ()   |===========|--.
  |   |_______|           |  |
   \___________           |  |
      /  /    |___________|  |
     |__|      * 1941 *   `--'
'''),
("MOSIN-NAGANT", r'''
  ()==[]==================================>---
       ||            |  |
      (__)          (|  |)
                     * VINTOVKA *
'''),
("T-34 TANK", r'''
            ___
          _/ * \__
   ______/_______\__________
  | T-34                     |===
  |__________________________|
   O  O  O  O  O  O  O  O  O
  (__)(__)(__)(__)(__)(__)(__)
'''),
("IS-2 HEAVY TANK", r'''
            ______
       ____/  **  \____
   ___/______________  \_________
  |  IS-2              |          |==---
  |____________________|__________|
   (O)(O)(O)(O)(O)(O)(O)(O)(O)
  [==========================]
'''),
("KATYUSHA", r'''
   >>======
   >>======
   >>======     * BM-13 *
   >>======
  ___________
  |  o   o  |
  |_________|
   O       O
  (_)     (_)
'''),
("SOYUZ LAUNCH", r'''
        /\
       /  \
      |    |
      | CC |
      | CP |
      |    |
     /|    |\
    / |    | \
   /__|    |__\
      |    |
      \vvvv/
       \vv/
      ((()))
     (((((((
'''),
("SPUTNIK", r'''
       .   |   .
     \     |     /
      \  __o__  /
   ----( ( O ) )----
      /  `---'  \
     /     |     \
       .   |   .
    * PERVYI SPUTNIK *
'''),
("VOSTOK CAPSULE", r'''
        _____
      -'     '-
     / /-----\ \
    | | () () | |
    | |  ___  | |
     \ \_____/ /
      -._____.-
      /|     |\
     | |-----| |
      \_|___|_/
'''),
("COSMONAUT", r'''
        ______
      -'  __  '-
     /  -'  '-  \
    |  | CCCP |  |
    |  |  ..  |  |
     \  '-__-'  /
      '-.____.-'
       /|    |\
      ( |    | )
       \|____|/
'''),
("MiG FIGHTER", r'''
            ^
           /|
     _____/_|_____
  <=(____________o___>====-
         \ | /
          \|/   * KRASNYI *
'''),
("SUBMARINE", r'''
            |
           _|_
     _____/___\__________
  __/                    \__
 (   O     O     O     O    )
  \________________________/
     \__/        \__/
'''),
("CRUISER AURORA", r'''
     |    |    |
    _|_  _|_  _|_
  __|___|___|___|________
  \   AVRORA            /
   \____________________/
  ~~~~~~~~~~~~~~~~~~~~~~~~~~
   ~~~~  1917  ~~~~~~~~~~
'''),
("KREMLIN TOWER", r'''
         *
        /|\
        |_|
       |   |
       | + |
      |     |
      | [#] |
      |     |
     |_______|
     |  | |  |
     |__|_|__|
'''),
("ONION DOMES", r'''
    .    .    .
   (|)  (|)  (|)
   /#\  /@\  /#\
  |###||@@@||###|
  |###||@@@||###|
  |___||___||___|
  [===============]
   * KRASNAYA PL *
'''),
("MAUSOLEUM", r'''
   ________________
  |________________|
   |______________|
    |____________|
     |  L E N  |
     |__________|
  ==================
   * 1924 *
'''),
("FACTORY", r'''
   ||   ||   ||
   ||   ||   ||    ~ ~ ~
  _||_ _||_ _||_
 |####|####|####|
 |####|####|####|
 |_[]_|_[]_|_[]_|
  * PYATILETKA *
'''),
("TRACTOR", r'''
        ______
       |  __  |___
       | |  | |   |
    ___|_|__|_|___|
   /   O      ()   \
  | O ( ) ___ ( )   |
   \__(_)/   \(_)__/
    * KOLKHOZ *
'''),
("GEAR / COG", r'''
       _   _   _
      | |_| |_| |
    _ |       | _
   |_|  _____  |_|
   | | |     | | |
   |_| |_____| |_|
    _ |       | _
   |_||_   _ _|_|_|
      | |_| |_| |
      * TRUD *
'''),
("WHEAT SHEAF", r'''
    \ | /  \ | /
   \ \|/    \|/ /
    \ | | || | /
     \| | || |/
      | | || |
      \_|_||_/
       `-----'
     * UROZHAI *
'''),
("SICKLE & WHEAT", r'''
    .-""-.   \ | /
   /      \   \|/
  |   __   |   ||
   \ (  )  /   ||
    `|  |-'    ||
     |  |______||
     |         _|
      `-------'
'''),
("CLENCHED FIST", r'''
      _____
     | | | |
    _| | | |_
   | | | | | |
   |         |
   |  ROT   |
    \  FRONT|
     |______|
       |  |
'''),
("RED FLAG", r'''
  |`-._
  |    `-._
  | H+S    `|
  |  CCCP  .|
  |    _.-'
  |_.-'
  |
  |
  |
 _|_
'''),
("BANNER", r'''
   ______________
  |   * CCCP *   |
  |  __________  |>
  | | WORKERS  | |>
  | | UNITE !  | |>
  |  ----------  |>
  |______________|
       |    |
'''),
("ORDER MEDAL", r'''
      __*__
     /  |  \
    | ( O ) |
     \__|__/
    //  |  \
   ((   |   ))
    \  |  //
     `--+--'
   * GEROI *
'''),
("HAMMER", r'''
    _________
   |_________|
       | |
       | |
       | |
       | |
       |_|
   * MOLOT *
'''),
("SICKLE", r'''
     .-""""-.
   .'        '.
  /            \
 |   .------.   |
  \  |      |
   '.|      |
     |      |
     |______|____
          * SERP *
'''),
("ANVIL", r'''
        ________
    ___/        \
   /              |
   \____      ___/
       |     |
       |     |
      /_______\
    * KUZNITSA *
'''),
("BEAR IN USHANKA", r'''
      .--.--.
     ( o  o )
     /  ()  \
    | [####] |     <- krasnaya ushanka
     \  --  /
     /`----'\
    ( /    \ )
     ||    ||
    (__)  (__)
    * MISHKA *
'''),
("BALALAIKA", r'''
        /\
       /  \
      / || \
     /  ||  \
    /   ||   \
   /____||____\
   |  o  O  o |
   |__________|
    * MUSIKA *
'''),
("ACCORDION", r'''
   ___/\/\/\/\___
  | o |/\/\/\| o |
  | o |\/\/\/| o |
  | o |/\/\/\| o |
  |___|\/\/\/|___|
    * GARMON *
'''),
("MATRYOSHKA", r'''
       .-""-.
      / .--. \
     | ( oo ) |
     |  \__/  |
    |  .----.  |
    | ( CCCP ) |
    |  `----'  |
     \________/
'''),
("USHANKA", r'''
     ________
   .'  ____  '.
  /  .'    '.  \
 |  | ( * ) |  |
 |  |______|  |
  \__________/
  |__________|
   * SHAPKA *
'''),
("SAMOVAR", r'''
        _
       (_)
      __|__
     /     \
    | CCCP  |==D
    |       |
     \_____/
     /     \
    |_______|
     * CHAI *
'''),
("RADIO TOWER", r'''
       (( * ))
        \ | /
         \|/
         /|\
        / | \
       /  |  \
      / /-|-\ \
     /_/__|__\_\
      * SIGNAL *
'''),
("SATELLITE DISH", r'''
      __________
     /          \
    |   ______   |
    |  /      \  |
    | |   o----+--  ) ) )
    |  \______/  |
     \__________/
         |  |
        /____\
'''),
("ICBM", r'''
        /\
       /CC\
      / CP \
      |    |
      |    |
      | () |
      |    |
     /|    |\
    /_|    |_\
       |  |
      (vvvv)
'''),
("GRENADE F-1", r'''
        _||_
       |_==_|
      .-####-.
     /########\
    |##########|
    |###F-1####|
    |##########|
     \########/
      `-####-'
'''),
("TURRET STAR", r'''
      _________
     / *     * \
    |  _______  |
    | | ***** | |
    | |  ***  | |
    | |_______| |
     \_________/
    [===========]
'''),
("GLOBE & STAR", r'''
        *
      .---.
    .'     '.
   / CCCP    \
  | =-------= |
  | --====--- |
   \  SSSR   /
    '.     .'
      '---'
'''),
("DOVE OF PEACE", r'''
        __
      _/  \__
    _/       '-._
   /   (o)       '-.
   \      \      _.-'
    '-.    \  _/
       '-.__\/
          /||\
     * MIR * MIR *
'''),
("TORCH", r'''
       )))
      (((((
       )))
        |
       |#|
       |#|
      /###\
     |#####|
      \###/
   * SVOBODA *
'''),
("STATE EMBLEM", r'''
      .-"""-.
    .' * *** '.
   / \ | H+S | /\
  |   \|_____|/   |
  |)  ( globe )  (|
   \   '-----'   /
    '.  CCCP   .'
      '-------'
'''),
("CCCP BANNER", r'''
  ================
  |              |
  |   C C C P    |
  |              |
  |  * 1922 *    |
  |              |
  ================
       |    |
'''),
("1917 LAUREL STAR", r'''
         *
        ***
    \  *****  /
   (|  *****  |)
    |   ***   |
    (\  * *  /)
     \ 1917 /
      '----'
'''),
]

def _norm_art(raw):
    lines = raw.strip("\n").split("\n")
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0].strip(): lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    strip = [len(l) - len(l.lstrip(" ")) for l in lines if l.strip()]
    lead = min(strip) if strip else 0
    return [l[lead:] for l in lines]

def load_gallery():
    gallery = [(name, _norm_art(art)) for name, art in SOVIET_ART]
    try:
        for fn in sorted(os.listdir(ART_DIR)):
            if fn.lower().endswith(".txt"):
                try:
                    with open(os.path.join(ART_DIR, fn), encoding="utf-8", errors="replace") as fh:
                        art = _norm_art(fh.read())
                    if art: gallery.append((os.path.splitext(fn)[0].upper(), art))
                except OSError:
                    pass
    except OSError:
        pass
    return gallery

GALLERY = load_gallery()

# =====================================================================
#  ROTATING SIDE PANELS
# =====================================================================
SIDE_LEFT_SETS = [
    [ "      /\\      ", "     /  \\     ", "  *** ** ***   ", "    *******    ", "  ****   ****  ",
      "     ** **     ", "      /||\\     ", "     /_||_\\    ", "       ||      ", "    ___||___   ",
      "   /___||___\\  ", "      /||\\     ", "    /__||__\\   ", "  /____||____\\ ", " [===||||===] ",
      "      /||\\     ", " ___/_||_\\___ ", "| RED SIGNAL |", "| DIRECTORATE|", "|___________|" ],
    [ "    _______    ", "   | C C C P |  ", "   |_________|  ", "       |||      ", "      /|||\\     ",
      "     / ||| \\    ", "    |  |||  |   ", "    |  |||  |   ", "    |__|||__|   ", "       |||      ",
      "     __|||__    ", "    |#######|   ", "    |#######|   ", "    |__###__|   ", "       |||      ",
      "      (|||)     ", "   * MAYAK *   ", "   TRANSMIT    ", "   STATION 1   ", "   ~~~~~~~~~~  " ],
    [ "       **       ", "      ****      ", "   ***HAMMER*** ", "    &  SICKLE   ", "   OF THE       ",
      "   WORKERS      ", "   ===========  ", "    | | | | |   ", "    | | | | |   ", "    |_______|   ",
      "   ___________  ", "  | PROLETARII| ", "  |   VSEKH   | ", "  |   STRAN   | ", "  | SOEDIN... | ",
      "  |___________|", "       |||      ", "      (|||)     ", "   * TRUD *    ", "   ~~~~~~~~~~  " ],
]
SIDE_RIGHT_SETS = [
    [ "   .-=======-.  ", "  /##########\\ ", " |### ORDER ###|", " |## RHYTHM ##| ", " |## SIGNAL ##| ",
      "  \\##########/ ", "   '--------'   ", "      ||||      ", "   ___||||___   ", "  /##########\\  ",
      " |###AUDIO###| ", " |###BUREAU##| ", "  \\##########/ ", "   \\########/   ", "    '------'    ",
      "   * RED *     ", "   * STAR *    ", "   ~~~~~~~~~~  ", "   1 9 8 3     ", "   ~~~~~~~~~~  " ],
    [ "        /\\      ", "       /CC\\     ", "      / CP \\    ", "      |    |    ", "      |    |    ",
      "      | () |    ", "      |    |    ", "     /|    |\\   ", "    /_|    |_\\  ", "       |  |     ",
      "      (vvvv)    ", "     ((((((     ", "    ( ( (( (    ", "   * VOSTOK *  ", "   TO ORBIT    ",
      "   ~~~~~~~~~~  ", "   P O E H A L I", "   ~~~~~~~~~~  ", "   * 1961 *    ", "   ~~~~~~~~~~  " ],
    [ "      (( * ))   ", "       \\ | /    ", "        \\|/     ", "        /|\\     ", "       / | \\    ",
      "      /  |  \\   ", "     / /-|-\\ \\  ", "    /_/__|__\\_\\ ", "       SIGNAL   ", "   ___________  ",
      "  | DX  WATCH | ", "  | 7.015 MHz | ", "  | CQ CQ CQ  | ", "  |___________|", "       |||      ",
      "      (|||)     ", "   * ETHER *   ", "   LISTENING   ", "   ~~~~~~~~~~  ", "   . _ . _ .   " ],
]

# ---------------- RED STAR PAGE (TAB) : rotating emblem ----------------
STAR_HS = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⢿⢹⣿⡆
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⣼⡿⠇⠈⣿⣧
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢦⣄⣀⣀⣀⣀⣀⣀⣀⣛⣋⡸⠀⠀⠀⠀⠸⣿⣧⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠿⣿⣛⠛⠛⠋⢻⠛⠓⠀⠀⠀⠀⠀⠻⠛⠛⠛⠛⠛⠛⣻⣿⣿⠿⠋⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢹⣷⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣾⡿⠋⠉
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣷⣥⡀⠀⠀⠀⠀⠀⠀⠀⣤⣾⡿⠟⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣶⣶⠁⠀⠀⣠⣴⣦⡄⠀⠀⠈⣿⣇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⡾⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⠃⢀⣤⣾⡿⠛⠛⢿⣷⣤⡀⢹⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠘⠳⣦⣄⡀
⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣴⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣶⣿⠟⠁⠀⠀⠀⠀⠉⠻⣿⣦⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣦⡠⣄⡀
⠀⠀⠀⠀⠀⠀⣠⣾⢫⣿⣿⠟⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢈⠻⣿⣷⡌⢿⣦⡀
⠀⠀⠀⠀⣀⣼⣿⠁⣾⠟⢋⣴⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠋⠁⠀⠀⠀⠀⠀⠀⢤⡀⠀⠀⠀⠀⠀⠀⠈⠛⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣷⣌⠻⣿⠈⣿⣷⣤⡀
⠀⠀⠀⣼⢻⣿⡿⠐⣣⣾⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠳⣶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣷⣮⡁⢻⣿⡇⣷⡀
⠀⠀⣼⡏⢸⣿⣧⣾⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣷⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⢿⣿⣾⣿⡇⢸⣿
⠀⢰⣿⣧⢸⣿⡿⢋⣴⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣷⣌⠻⣿⡇⣾⣿⡇
⠀⢸⣿⣿⢸⣏⣴⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣷⣌⠃⣿⣿⡧
⢠⠸⣿⣿⢠⣾⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣘⢿⣿⣦⣿⣿⠇⢀
⣸⡀⢻⣿⣾⡿⢃⣶⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡌⠻⣿⣿⡿⢀⣿
⣿⣇⠀⣿⡟⢁⣾⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⠟⠁⠙⢿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⡄⠹⣿⠃⣸⣿
⢹⣿⣆⠸⢁⣾⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠃⠀⠀⠀⠀⠙⢿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⡆⠛⣠⣿⡿
⠸⣿⣿⡄⣸⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⣾⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡼⣿⣿⣀⣿⣿⠇
⡆⠹⣿⣷⣿⣿⠃⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣦⡀⠀⠀⠀⢀⣿⣿⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡀⢻⣿⣿⣿⠏⢠
⢻⣄⠙⣿⣿⡇⢀⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠹⣿⣿⣿⣦⡀⢀⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠘⣿⡿⠋⣠⣾
⠸⣿⣷⡈⢻⡇⢸⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣴⣿⣿⣿⣶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⢠⡟⣠⣾⣿⠇
⠀⠹⣿⣿⣦⡀⢸⣿⣿⢸⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⡿⠿⠀⠙⠿⣿⣿⣿⣿⣶⣦⣤⣤⣤⣴⣶⣿⣿⣿⣿⣿⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⣠⡞⢸⣿⣿⢀⣼⣿⣿⠏
⠀⠀⣿⠿⣿⣿⣜⣿⣿⠀⢿⣆⠀⠀⠀⠀⠀⢀⣴⣿⣿⡟⠀⠀⠀⠀⠀⠀⠙⠻⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⣰⣿⠃⣼⣿⣣⣾⣿⠟⣡⠆
⠀⠀⠘⣦⡌⠛⢿⣿⣿⡄⢸⣿⣆⠀⠀⠀⢰⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠙⠛⠛⠛⠛⠉⠉⠀⠈⠻⣿⣿⣿⡷⠀⠀⠀⠀⣠⣿⡏⢀⣿⣿⠿⠋⢁⣴⠏
⠀⠀⠀⠘⣿⣷⣤⣉⠻⢷⡘⣿⣿⡤⣄⠀⠘⠛⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠋⠀⠀⠀⣠⢆⣿⣿⠇⠸⢛⣁⣤⣾⣿⠏
⠀⠀⠀⠀⠈⠻⣿⣿⣿⣶⣄⠹⣿⣿⡘⢷⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⠇⣼⣿⢏⣠⣶⣿⣿⡿⠟⠁
⠀⠀⠀⠀⠀⠀⠈⣽⠻⢿⣿⣿⣯⣿⣧⡈⢿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⠃⣼⣿⣿⣿⣿⠿⠛⣩⠄
⠀⠀⠀⠀⠀⠀⠀⠈⠳⣦⣤⣈⡉⠙⠛⠛⠂⠛⢿⣿⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⡿⠟⠁⠚⠋⣉⣁⣠⣤⣴⠟⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠿⣿⣿⣿⣿⣿⣿⣶⣾⣿⡿⠿⠗⣲⣀⣤⣴⣶⡶⠶⣦⣤⣤⡶⠶⣶⣶⣦⣤⣐⡒⠻⠿⠿⣷⣾⣿⣿⣿⣿⣿⣿⠿⠛⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢯⣉⡉⠉⠉⠉⣁⣀⣤⣶⣾⣿⣿⠟⠋⣡⣴⡾⠛⠉⠙⠻⣶⣤⡉⠻⢿⣿⣿⣷⣶⣤⣄⣀⣉⣉⣉⣉⣥⠖
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⣿⡿⠟⠋⢁⣴⣾⠟⠉⠀⠀⠀⠀⠀⠀⠙⢿⣷⣄⠉⠛⠻⢿⣿⣿⣿⣿⡿⠟⠋
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⢼⣿⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⡿⠆
"""

def get_cleaned_braille(raw):
    lines = raw.strip("\n").split("\n")
    cleaned_lines = [l.replace('\u2800', ' ') for l in lines]
    min_lead = min((len(l) - len(l.lstrip(' ')) for l in cleaned_lines if l.strip(' ')), default=0)
    return [l[min_lead:] for l in cleaned_lines]

STAR_LINES = get_cleaned_braille(STAR_HS)

def search_youtube(query, max_results=10):
    if not YOUTUBE_API_KEY: return None, "No YouTube API key configured"
    params = urllib.parse.urlencode({"part": "snippet", "q": query, "maxResults": max_results, "type": "video", "key": YOUTUBE_API_KEY})
    request = urllib.request.Request("https://www.googleapis.com/youtube/v3/search?" + params, headers={"User-Agent": "YT-Terminal-Player/13.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response: payload = json.load(response)
        items = payload.get("items", [])
        if not items: return None, "No videos found"
        results = []
        for item in items:
            video_id = item.get("id", {}).get("videoId", "")
            if VIDEO_ID_RE.match(video_id):
                title = html.unescape(item.get("snippet", {}).get("title", video_id))
                results.append((f"https://www.youtube.com/watch?v={video_id}", title))
        return results if results else (None, "Search returned invalid data")
    except Exception as exc: return None, f"Search failed: {exc}"

def apply_auth_options(options):
    global AUTO_DETECTED_BROWSER
    if AUTO_DETECTED_BROWSER:
        try: options["cookiesfrombrowser"] = (AUTO_DETECTED_BROWSER,)
        except Exception: pass
    return options

def ytdlp_flat(target):
    """Flat-list a playlist URL or a ytsearchN: query into [(url, title)] without using the API key."""
    opts = apply_auth_options({"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True, "ignoreerrors": True})
    try:
        with YoutubeDL(opts) as ydl: info = ydl.extract_info(target, download=False)
    except Exception:
        return []
    entries = (info or {}).get("entries")
    if entries is None and info:
        entries = [info]
    out = []
    for e in entries or []:
        if not e: continue
        vid = e.get("id")
        title = html.unescape(e.get("title") or vid or "track")
        url = e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid and VIDEO_ID_RE.match(str(vid)) else None)
        if url and not str(url).startswith("http"):
            url = f"https://www.youtube.com/watch?v={vid}" if vid and VIDEO_ID_RE.match(str(vid)) else None
        if url: out.append((url, title))
    return out

def resolve_media(url, audio_only, resolution=720, saver=False):
    if audio_only:
        cap = 96 if saver else 160
        format_str = f"bestaudio[ext=m4a][abr<={cap}]/bestaudio[abr<={cap}]/bestaudio/best"
    elif resolution:
        format_str = f"bestvideo[height<={resolution}]+bestaudio/best/best"
    else:
        format_str = "bestvideo*+bestaudio/best"
    options = apply_auth_options({"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True, "format": format_str})
    try:
        with YoutubeDL(options) as ydl: info = ydl.extract_info(url, download=False)
        if not info: return None, None, None, "yt-dlp returned no media information"
        if info.get("entries"):  # a playlist slipped through; take first
            info = next((e for e in info["entries"] if e), None)
            if not info: return None, None, None, "Playlist entry was empty"
        title = html.unescape(info.get("title") or "YouTube media")
        requested = info.get("requested_formats") or []
        if audio_only:
            audio_url = info.get("url") or next((f.get("url") for f in requested if f.get("acodec") != "none"), None)
            return None, audio_url, title, None if audio_url else "No audio stream found"
        video_url = next((f.get("url") for f in requested if f.get("vcodec") != "none"), None)
        audio_url = next((f.get("url") for f in requested if f.get("acodec") != "none"), None)
        if not requested and info.get("url"):
            video_url = info["url"]; audio_url = None
        if not video_url: return None, None, None, "No video stream found"
        return video_url, audio_url, title, None
    except Exception as exc:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
        return None, None, None, f"Could not resolve media: {clean}"

def fmt_time(value):
    total = max(0, int(value or 0))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

class Player:
    def __init__(self):
        if shutil.which("mpv") is None: raise RuntimeError("mpv was not found on PATH.")
        self.mpv = MPV(input_default_bindings=True, osc=True, idle=True, ao="pulse", ipc_socket="/data/data/com.termux/files/usr/tmp/walkman.sock")
        self.status = "Press / to search, [S] for the Soviet channel"
        self.playlist = []
        self.current_index = -1
        self.busy = False
        self.video_enabled = True
        self.audio_only = False
        self.resolution = 720
        self.saver = False
        self.search_results = []
        self.awaiting_search_selection = False
        self._apply_cache()

    def _apply_cache(self):
        # The old build read ahead 1000 MB; that is what made audio-only greedy.
        try:
            self.mpv.command("set", "cache", "yes")
            if self.audio_only:
                self.mpv.command("set", "demuxer-max-bytes", "48M")
                self.mpv.command("set", "demuxer-max-back-bytes", "16M")
                self.mpv.command("set", "demuxer-readahead-secs", "30")
                self.mpv.command("set", "cache-secs", "60")
            else:
                self.mpv.command("set", "demuxer-max-bytes", "200M")
                self.mpv.command("set", "demuxer-max-back-bytes", "64M")
                self.mpv.command("set", "demuxer-readahead-secs", "20")
                self.mpv.command("set", "cache-secs", "40")
        except Exception: pass

    def load_async(self, text, audio_only=False):
        if self.busy: return
        self.busy = True
        self.audio_only = audio_only
        self.video_enabled = not audio_only
        self.status = "Searching the signal..."
        threading.Thread(target=self._load, args=(text.strip(),), daemon=True).start()

    def start_soviet(self):
        if self.busy: return
        self.busy = True
        self.audio_only = True
        self.video_enabled = False
        self.status = "Opening the Soviet channel..."
        threading.Thread(target=self._build_soviet, daemon=True).start()

    def _build_soviet(self):
        try:
            self.mpv.command("stop")
            link = read_soviet_link()
            queue = []
            if link:
                self.status = "Expanding the Soviet playlist..."
                queue = ytdlp_flat(link)
            if not queue:
                self.status = "Playlist unreachable - tuning the classics..."
                for phrase in SOVIET_FALLBACK:
                    try:
                        r = ytdlp_flat("ytsearch1:" + phrase)
                        if r: queue.append(r[0])
                    except Exception: pass
            if not queue:
                self.status = "Soviet channel empty (put a link in ~/.walkman_soviet)"
                return
            self.playlist = queue
            self.current_index = 0
            self._apply_cache()
            self._play_current()
        except Exception as e:
            self.status = f"Soviet channel error: {e}"
        finally:
            self.busy = False

    def load_recommendations(self):
        if self.busy: return
        self.busy = True
        self.mpv.command("stop")
        self.status = "Fetching recommendations..."
        def _fetch_recs():
            try:
                res = search_youtube("top music hits 2026", max_results=10)
                if isinstance(res, tuple) and res[0] is None: self.status = res[1]
                else:
                    self.search_results = res
                    self.awaiting_search_selection = True
                    self.status = "Select recommendation..."
            except Exception as e: self.status = f"Recommendations error: {e}"
            finally: self.busy = False
        threading.Thread(target=_fetch_recs, daemon=True).start()

    def _load(self, text):
        try:
            if not text: return
            if is_url(text):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
                if q.get("list") or "/playlist" in text:
                    self.mpv.command("stop")
                    self.status = "Expanding playlist..."
                    queue = ytdlp_flat(text)
                    if not queue:
                        self.status = "Playlist is empty or unavailable"
                        return
                    self.playlist = queue; self.current_index = 0
                    self._apply_cache(); self._play_current()
                    return
                self.playlist = [(text, "Resolving URL...")]
                self.current_index = 0
                self._apply_cache()
                self._play_current()
            else:
                self.mpv.command("stop")
                results = search_youtube(text, max_results=10)
                if isinstance(results, tuple) and results[0] is None:
                    self.status = results[1]; return
                self.search_results = results
                self.awaiting_search_selection = True
                self.status = "Select your target..."
        except Exception as exc: self.status = f"Load error: {exc}"
        finally: self.busy = False

    def select_search_result(self, index):
        if not self.awaiting_search_selection or index < 0 or index >= len(self.search_results): return
        self.awaiting_search_selection = False
        self.playlist = [self.search_results[index]]
        self.search_results = []
        self.current_index = 0
        self.busy = True
        self._apply_cache()
        threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def download_current(self):
        if self.current_index < 0 or self.current_index >= len(self.playlist):
            self.status = "Nothing playing to download."
            return
        url, title = self.playlist[self.current_index]
        self.status = f"Archiving: {title[:20]}..."
        def _dl():
            out_dir = AUDIO_DIR if self.audio_only else VIDEO_DIR
            fmt = "bestaudio/best" if self.audio_only else "bestvideo+bestaudio/best"
            opts = apply_auth_options({"format": fmt, "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"), "quiet": True})
            try:
                with YoutubeDL(opts) as ydl: ydl.download([url])
                self.status = f"Archive Complete: {title[:15]}"
            except Exception as e: self.status = f"Archive failed: {e}"
        threading.Thread(target=_dl, daemon=True).start()

    def _play_current(self):
        if self.current_index < 0 or self.current_index >= len(self.playlist): return
        url, title = self.playlist[self.current_index]
        self.status = f"Resolving streams: {title}"
        video_url, audio_url, resolved_title, error = resolve_media(url, self.audio_only, self.resolution, self.saver)
        if error:
            self.status = f"Error: {error}"
            self.mpv.command("stop")
            return
        self.playlist[self.current_index] = (url, resolved_title or title)
        self.mpv.vid = "no" if self.audio_only else "auto"
        if self.audio_only: self.mpv.loadfile(audio_url, "replace")
        else:
            self.mpv.loadfile(video_url, "replace")
            if audio_url: self.mpv.audio_add(audio_url, "select")
        self.status = f"Playing: {resolved_title or title}"

    def _play_current_and_unbusy(self):
        try: self._play_current()
        finally: self.busy = False

    def update_queue(self):
        if self.awaiting_search_selection: return
        if not self.busy and getattr(self.mpv, 'idle_active', False) and self.current_index >= 0:
            if self.current_index < len(self.playlist) - 1:
                self.current_index += 1
                self.busy = True
                threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def next_track(self):
        if self.busy or self.current_index < 0 or self.current_index >= len(self.playlist) - 1: return
        self.current_index += 1; self.busy = True
        threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def prev_track(self):
        if self.busy or self.current_index <= 0: return
        self.current_index -= 1; self.busy = True
        threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def toggle_saver(self):
        self.saver = not self.saver
        self.status = f"Data saver {'ON (<=96 kbps)' if self.saver else 'OFF (<=160 kbps)'}"
        if self.audio_only and self.current_index >= 0 and not self.busy:
            self.busy = True
            threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def toggle_pause(self):
        try: self.mpv.command("cycle", "pause")
        except: pass
    def toggle_mute(self):
        try: self.mpv.command("cycle", "mute")
        except: pass
    def change_volume(self, amount):
        try: self.mpv.volume = max(0, min(130, float(self.mpv.volume or 0) + amount))
        except: pass
    def seek(self, seconds):
        try: self.mpv.command("seek", seconds, "relative")
        except: pass

    def toggle_video(self):
        if self.current_index < 0: return
        self.video_enabled = not self.video_enabled
        self.audio_only = not self.video_enabled
        self.status = "Reloading stream with new video settings..."
        self.mpv.command("stop")
        self.busy = True
        self._apply_cache()
        threading.Thread(target=self._play_current_and_unbusy, daemon=True).start()

    def snapshot(self):
        def get(name, fallback=None):
            try:
                v = getattr(self.mpv, name)
                return fallback if v is None else v
            except: return fallback
        q_title = "No media loaded"
        if 0 <= self.current_index < len(self.playlist): q_title = self.playlist[self.current_index][1]
        return {
            "title": q_title, "paused": bool(get("pause", False)), "position": float(get("time_pos", 0) or 0),
            "duration": float(get("duration", 0) or 0), "volume": float(get("volume", 0) or 0), "muted": bool(get("mute", False)),
            "idle": bool(get("idle_active", True)), "index": self.current_index + 1 if self.current_index >= 0 else 0,
            "count": len(self.playlist), "abr": float(get("audio_bitrate", 0) or 0),
        }
    def close(self):
        try: self.mpv.terminate()
        except: pass

def setup_colors():
    if not curses.has_colors(): return
    curses.start_color()
    try: curses.use_default_colors()
    except: pass
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_YELLOW)
    curses.init_pair(11, curses.COLOR_RED, curses.COLOR_RED)
    curses.init_pair(13, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(15, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(17, curses.COLOR_RED, -1)          # gallery normal: red glyph
    curses.init_pair(18, curses.COLOR_YELLOW, curses.COLOR_RED)   # gallery inverse: gold on red

def draw_transparent_text(stdscr, text, start_y, start_x, height, width, color_pair):
    for c, char in enumerate(text):
        if char != ' ':
            sy, sx = start_y, start_x + c
            if 0 <= sy < height and 0 <= sx < width - 1:
                try: stdscr.addch(sy, sx, char, color_pair | curses.A_BOLD)
                except: pass

def draw_side_art(stdscr, tick, height, width, red, black_red, bright):
    def at(y, x, text, style=0):
        try:
            if 0 <= y < height and 0 <= x < width:
                stdscr.addstr(y, x, str(text)[:max(0, width - x - 1)], style)
        except: pass
    inner_left, inner_right = 20, width - 21
    for y in range(height - 1):
        texture = "#" if (y + tick // 4) % 2 == 0 else "%"
        at(y, 0, (texture * 18)[:18], red)
        at(y, width - 19, (texture * 18)[:18], red)
    for y in range(1, height - 2):
        at(y, 18, "||", red | bright)
        at(y, width - 21, "||", red | bright)
    rot = (tick // 150)   # ~12 s per set
    left_art = SIDE_LEFT_SETS[rot % len(SIDE_LEFT_SETS)]
    right_art = SIDE_RIGHT_SETS[rot % len(SIDE_RIGHT_SETS)]
    for i, line in enumerate(left_art): at(3 + i, 1, line[:17], red | bright)
    for i, line in enumerate(right_art): at(3 + i, width - 18, line[:17], red | bright)
    return inner_left, inner_right

# ---------------- RED STAR PAGE (TAB) ----------------
def build_star_pts(angle, outer_r, inner_r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + (i * math.pi / 5) - angle
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((math.cos(a) * r, math.sin(a) * r))
    return pts

def is_inside_star(rx, ry, pts):
    inside = False
    j = 9
    for i in range(10):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > ry) != (yj > ry)) and (rx < (xj - xi) * (ry - yi) / (yj - yi + 1e-6) + xi):
            inside = not inside
        j = i
    return inside

def draw_star_text(stdscr, text, sy, start_x, height, width, y_center, x_center, pts, is_shadow):
    for c, char in enumerate(text):
        if char == ' ': continue
        sx = start_x + c
        if 0 <= sy < height and 0 <= sx < width - 1:
            on_gold = is_inside_star((sx - x_center) * 0.5, sy - y_center, pts)
            if is_shadow: color = curses.color_pair(16) if on_gold else curses.color_pair(15)
            else: color = curses.color_pair(14) if on_gold else curses.color_pair(13)
            try: stdscr.addch(sy, sx, char, color | curses.A_BOLD)
            except: pass

def draw_star_page(stdscr, player, tick):
    height, width = stdscr.getmaxyx()
    gold_bg, red_bg = curses.color_pair(10), curses.color_pair(11)
    y_center, x_center = height // 2, width // 2
    outer_r = min(height, width // 2) * 0.45
    pts = build_star_pts(tick * 0.03, outer_r, outer_r * 0.382)
    for y in range(height):
        cx, run_color, run_len = 0, None, 0
        for x in range(width - 1):
            color = gold_bg if is_inside_star((x - x_center) * 0.5, y - y_center, pts) else red_bg
            if color == run_color: run_len += 1
            else:
                if run_color is not None:
                    try: stdscr.addstr(y, cx, " " * run_len, run_color)
                    except: pass
                    cx += run_len
                run_color, run_len = color, 1
        if run_color is not None:
            try: stdscr.addstr(y, cx, " " * run_len, run_color)
            except: pass
    def centred(text, row, shadow=False):
        text = f" {text} "
        sx0 = max(0, x_center - len(text) // 2)
        for c, char in enumerate(text):
            sx = sx0 + c
            if 0 <= row < height and 0 <= sx < width - 1:
                on_gold = is_inside_star((sx - x_center) * 0.5, row - y_center, pts)
                if shadow: color = curses.color_pair(16) if on_gold else curses.color_pair(15)
                else: color = curses.color_pair(14) if on_gold else curses.color_pair(13)
                try: stdscr.addch(row, sx, char, color | curses.A_BOLD)
                except: pass
    art_h, art_w = len(STAR_LINES), max(len(l) for l in STAR_LINES)
    start_y, start_x = max(0, y_center - art_h // 2 - 4), x_center - art_w // 2
    for r, line in enumerate(STAR_LINES): draw_star_text(stdscr, line, start_y + r + 1, start_x + 2, height, width, y_center, x_center, pts, True)
    for r, line in enumerate(STAR_LINES): draw_star_text(stdscr, line, start_y + r, start_x, height, width, y_center, x_center, pts, False)
    centred("Hi comrade, relax and have fun", height - 9)
    snap = player.snapshot()
    if not snap["idle"]:
        state = "PAUSED" if snap["paused"] else "TRANSMITTING"
        centred(f"{state}: {str(snap['title'])[:max(10, width - 30)]}  {fmt_time(snap['position'])}/{fmt_time(snap['duration'])}", height - 5)
    centred("[TAB] RETURN   [SPACE] HOLD SIGNAL   [ARROWS] SEEK/VOL   [Q] QUIT", height - 3, True)

def draw_gallery(stdscr, player, tick, gidx, invert, auto):
    height, width = stdscr.getmaxyx()
    red, yellow, cyan, bright = curses.color_pair(2), curses.color_pair(4), curses.color_pair(1), curses.A_BOLD
    inner_left, inner_right = draw_side_art(stdscr, tick, height, width, red, curses.color_pair(7), bright)
    panel_w = inner_right - inner_left + 1
    x = inner_left + 2
    content_w = max(42, panel_w - 4)
    n = len(GALLERY)
    shown = (tick // 37) % n if auto else gidx % n
    name, art = GALLERY[shown]
    y_center = height // 2
    x_center = (inner_left + inner_right) // 2
    art_color = curses.color_pair(18) if invert else curses.color_pair(17)
    sy = max(4, y_center - len(art) // 2 - 1)
    aw = max((len(l) for l in art), default=0)
    sx = x_center - aw // 2
    for r, line in enumerate(art):
        if invert:
            # poster block: fill the whole art line cell band in red, gold glyphs
            for c, char in enumerate(line):
                yy, xx = sy + r, sx + c
                if 0 <= yy < height and inner_left < xx < inner_right:
                    try: stdscr.addch(yy, xx, char if char != ' ' else ' ', art_color | bright)
                    except: pass
        else:
            draw_transparent_text(stdscr, line, sy + r, sx, height, width, art_color)
    # header + footer
    def at(y, xx, text, style=0):
        try:
            if 0 <= y < height and 0 <= xx < width: stdscr.addstr(y, xx, str(text)[:max(0, width - xx - 1)], style)
        except: pass
    at(0, inner_left, "#" * panel_w, red | bright)
    title = f"*  RED STAR GALLERY  //  {shown + 1:02d}/{n:02d}  //  {name}"
    at(1, inner_left + max(0, (panel_w - len(title)) // 2), title[:content_w], yellow | bright)
    at(2, inner_left, "=" * panel_w, red | bright)
    at(height - 4, inner_left, "=" * panel_w, red | bright)
    snap = player.snapshot()
    at(height - 3, x, f"PLAYING: {str(snap['title'])[:content_w-10]}", yellow | bright)
    mode = "AUTO" if auto else "MANUAL"
    at(height - 2, x, f"[<>] STEP  [A] {mode}  [I] {'INVERSE' if invert else 'NORMAL'}  [G/TAB] BACK  [SPACE] HOLD", cyan | bright)

def draw_page_1(stdscr, player, input_mode, choose_mode, input_buffer, tick):
    height, width = stdscr.getmaxyx()
    snap = player.snapshot()
    cyan, red, green, yellow = curses.color_pair(1), curses.color_pair(2), curses.color_pair(3), curses.color_pair(4)
    black_red, bright = curses.color_pair(7), curses.A_BOLD
    def at(y, x, text, style=0):
        try:
            if 0 <= y < height and 0 <= x < width: stdscr.addstr(y, x, str(text)[:max(0, width - x - 1)], style)
        except: pass
    inner_left, inner_right = draw_side_art(stdscr, tick, height, width, red, black_red, bright)
    panel_w = inner_right - inner_left + 1
    x = inner_left + 2
    content_w = max(42, panel_w - 4)
    at(0, inner_left, "#" * panel_w, red | bright)
    at(1, inner_left + max(0, (panel_w - 54) // 2), "*** WALKMAN // RED STAR SIGNAL DIRECTORATE // 1983 ***", red | bright)
    at(2, inner_left, "=" * panel_w, red | bright)
    at(height - 4, inner_left, "=" * panel_w, red | bright)
    at(height - 3, inner_left + max(0, (panel_w - 38) // 2), f" *  MUSIC IS THE ENGINE OF THE NIGHT  * ", yellow | bright)
    at(height - 2, 0, "#" * (width - 1), red | bright)
    if player.awaiting_search_selection:
        at(4, x, "*  TARGET SELECTION MATRIX (10 ITEMS)", yellow | bright)
        at(5, x, "-" * content_w, red)
        for i, (url, res_title) in enumerate(player.search_results):
            num_str = f"[{i+1}]" if i < 9 else "[0]"
            at(7 + i, x, f"{num_str} {str(res_title)[:content_w-6]}", cyan | bright)
        at(18, x, "[1-9, 0] SELECT TARGET    [ESC] ABORT", yellow | bright)
        at(20, x, "-" * content_w, red)
        at(22, x, "AWAITING DIRECTIVE...", yellow | bright)
        return
    spinner = "|/-\\"[tick % 4] if player.busy else "*"
    at(4, x, f"{spinner}  CENTRAL TRANSMISSION CONTROL", yellow | bright)
    at(5, x, "-" * content_w, red)
    at(7, x, "NOW TRANSMITTING", yellow | bright)
    at(8, x, str(snap["title"])[:content_w], bright)
    duration = snap["duration"]
    ratio = min(1.0, snap["position"] / duration) if duration else 0
    bar_width = max(10, content_w - 22)
    progress = "[" + "#" * int(bar_width * ratio) + "-" * (bar_width - int(bar_width * ratio)) + "]"
    state = "NO MEDIA" if snap["idle"] else ("PAUSED" if snap["paused"] else "PLAYING")
    at(11, x, f"{progress} {fmt_time(snap['position'])}/{fmt_time(duration)}", cyan)
    at(12, x, f"{state}  VOL {int(snap['volume']):3d}%", (yellow if snap["paused"] else green) | bright)
    # bandwidth readout
    kbps = int(snap["abr"] / 1000) if snap["abr"] else 0
    mode = "AUDIO ONLY" if player.audio_only else "VIDEO + AUDIO"
    cap = "SAVER <=96k" if player.saver else "<=160k"
    band = f"{kbps}kbps" if kbps else "--"
    at(13, x, f"TRACK {snap['index']}/{snap['count']}  //  {mode}  //  {band} ({cap if player.audio_only else 'video'})", red | bright)
    at(15, x, "[SPACE] HOLD   [N/P] NEXT/PREV   [ARROWS] SEEK/VOL", 0)
    at(16, x, "[/] SEARCH     [S] SOVIET CHANNEL   [R] RECOMMEND", 0)
    at(17, x, "[G] GALLERY    [B] DATA SAVER       [D] DOWNLOAD", 0)
    at(18, x, "[TAB] RED STAR [V] VIDEO/ECO        [Q] QUIT", 0)
    at(20, x, "-" * content_w, red)
    if choose_mode: at(22, x, "MODE: [1] VIDEO  [2] AUDIO  [3] AUDIO + GALLERY  [ESC] CANCEL", yellow | bright)
    elif input_mode: at(22, x, "> DIRECTIVE: " + input_buffer + "_", yellow | bright)
    else: at(22, x, player.status, (red if "error" in player.status.lower() else green) | bright)

def run(stdscr):
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)
    stdscr.timeout(80)
    setup_colors()
    player = Player()
    input_mode = choose_mode = gallery_mode = star_page = False
    gallery_invert = False
    gallery_auto = True
    gallery_idx = 0
    pending_input, buffer = "", ""
    tick = 0
    try:
        while True:
            height, width = stdscr.getmaxyx()
            stdscr.erase()
            if star_page:
                draw_star_page(stdscr, player, tick)
            elif height < 40 or width < 120:
                try: stdscr.addstr(0, 0, "ENLARGE TERMINAL TO 120 x 42 TO FIT THE RED STAR SIGNAL", curses.color_pair(2) | curses.A_BOLD)
                except: pass
            elif gallery_mode:
                draw_gallery(stdscr, player, tick, gallery_idx, gallery_invert, gallery_auto)
            else:
                draw_page_1(stdscr, player, input_mode, choose_mode, buffer, tick)
            stdscr.refresh()
            player.update_queue()
            tick += 1
            key = stdscr.getch()
            if key == -1: continue

            if star_page:
                if key in (9, 27, curses.KEY_BTAB): star_page = False; curses.flushinp()
                elif key in (ord("q"), ord("Q")): break
                elif key == ord(" "): player.toggle_pause()
                elif key in (ord("m"), ord("M")): player.toggle_mute()
                elif key == curses.KEY_LEFT: player.seek(-5)
                elif key == curses.KEY_RIGHT: player.seek(5)
                elif key == curses.KEY_UP: player.change_volume(5)
                elif key == curses.KEY_DOWN: player.change_volume(-5)
                continue

            if gallery_mode:
                n = len(GALLERY)
                if key in (ord("g"), ord("G"), 9, 27): gallery_mode = False; curses.flushinp()
                elif key in (ord("q"), ord("Q")): break
                elif key in (ord("i"), ord("I")): gallery_invert = not gallery_invert
                elif key in (ord("a"), ord("A")): gallery_auto = not gallery_auto
                elif key == curses.KEY_RIGHT:
                    if gallery_auto: gallery_idx = (tick // 37) % n
                    gallery_auto = False; gallery_idx = (gallery_idx + 1) % n
                elif key == curses.KEY_LEFT:
                    if gallery_auto: gallery_idx = (tick // 37) % n
                    gallery_auto = False; gallery_idx = (gallery_idx - 1) % n
                elif key == ord(" "): player.toggle_pause()
                elif key in (ord("m"), ord("M")): player.toggle_mute()
                elif key in (ord("n"), ord("N")): player.next_track()
                elif key in (ord("p"), ord("P")): player.prev_track()
                continue

            if player.awaiting_search_selection:
                if ord('1') <= key <= ord('9'): player.select_search_result(key - ord('1')); curses.flushinp()
                elif key == ord('0'): player.select_search_result(9); curses.flushinp()
                elif key == 27:
                    player.awaiting_search_selection = False
                    player.search_results = []
                    curses.flushinp()
                continue

            if choose_mode:
                if key in (ord("1"), ord("2"), ord("3")):
                    choose_mode = False
                    gallery_mode = (key == ord("3"))
                    player.load_async(pending_input, audio_only=(key in (ord("2"), ord("3"))))
                    pending_input = ""
                    curses.flushinp()
                elif key == 27:
                    choose_mode, pending_input, player.status = False, "", "Load cancelled"
                    curses.flushinp()
                continue

            if input_mode:
                if key in (10, 13, curses.KEY_ENTER):
                    input_mode = False
                    if buffer.strip(): pending_input, choose_mode = buffer.strip(), True
                    buffer = ""
                    curses.flushinp()
                elif key == 27: input_mode, buffer = False, ""; curses.flushinp()
                elif key in (8, 127, curses.KEY_BACKSPACE): buffer = buffer[:-1]
                elif 32 <= key <= 126: buffer += chr(key)
                continue

            if key in (ord("q"), ord("Q")): break
            elif key == 9: star_page = True; curses.flushinp()
            elif key == ord(" "): player.toggle_pause()
            elif key in (ord("m"), ord("M")): player.toggle_mute()
            elif key in (ord("v"), ord("V")): player.toggle_video()
            elif key in (ord("g"), ord("G")): gallery_mode = True; curses.flushinp()
            elif key in (ord("s"), ord("S")): player.start_soviet()
            elif key in (ord("b"), ord("B")): player.toggle_saver()
            elif key in (ord("n"), ord("N")): player.next_track()
            elif key in (ord("p"), ord("P")): player.prev_track()
            elif key in (ord("r"), ord("R")): player.load_recommendations()
            elif key in (ord("d"), ord("D")): player.download_current()
            elif key == curses.KEY_LEFT: player.seek(-5)
            elif key == curses.KEY_RIGHT: player.seek(5)
            elif key == curses.KEY_UP: player.change_volume(5)
            elif key == curses.KEY_DOWN: player.change_volume(-5)
            elif key == ord("/"):
                input_mode, buffer = True, ""
                curses.flushinp()
    finally:
        player.close()

def main():
    force_terminal_size()
    os.environ.setdefault("ESCDELAY", "25")
    try: curses.wrapper(run)
    except RuntimeError as exc:
        print(f"\nYT Terminal Player: {exc}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
