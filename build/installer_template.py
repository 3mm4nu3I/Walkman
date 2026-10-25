#!/usr/bin/env python3
"""
Walkman 1.6.1 installer / upgrader  (2026-10-25)   -   the SOYUZ edition

Run in Termux:   python ~/storage/downloads/walkman_upgrade_1_6_1.py

What it does, in order:
  1. BACKS UP the current working setup FIRST. Nothing is changed until the
     backup is written and verified. If the backup fails, the script stops and
     leaves everything exactly as it was.
     Backup goes to:  <Download>/WALKMAN_BACKUP_<timestamp>/
     It saves: walkman.py, walkman_art.py (if any), ~/.walkman_key,
     ~/.walkman_soviet, ~/.bashrc, the `walkman` launcher, RED_STAR_ARCHIVE/Art.
  2. Installs ~/walkman.py (Build v14 / 1.6.1) and ~/walkman_art.py, checks both
     against their SHA-256, compiles them, and runs a headless self-test of the
     3D engine on THIS device (prints ms per frame). If anything fails it rolls
     back / disables the art - the player still runs like 1.5.
  3. Writes known-good copies of Build 1.6 (player + art) and Build 1.5 to ~/.walkman_known_good_1_6*.py / _1_5.py
  4. Installs the `walkman` launcher (starts pulseaudio, runs ~/walkman.py) and
     a `walkman-rollback` command.
  5. Keeps the YouTube API key in the keyring and migrates ~/.walkman_key.
  6. Keeps/creates ~/.walkman_soviet.

ROLLBACK, any time:
     walkman-rollback            restore the newest backup folder's walkman.py
     walkman-rollback --1.6      restore the known-good 1.6 build (player + art)
     walkman-rollback --1.5      restore the known-good 1.5 build
     walkman-rollback --list     list backup folders
SAFE MODE (no art, nothing to undo):   walkman --safe

Optional:  --autostart / --no-autostart   opening Termux launches Walkman
"""
import base64, hashlib, os, shutil, subprocess, sys, time, importlib, py_compile, zlib

HOME = os.path.expanduser("~")
PREFIX = os.environ.get("PREFIX", "")
IS_TERMUX = "com.termux" in PREFIX
TARGET = os.path.join(HOME, "walkman.py")
ART_TARGET = os.path.join(HOME, "walkman_art.py")
KNOWN_GOOD = os.path.join(HOME, ".walkman_known_good_1_5.py")
KNOWN_GOOD_16 = os.path.join(HOME, ".walkman_known_good_1_6.py")
KNOWN_GOOD_16A = os.path.join(HOME, ".walkman_known_good_1_6_art.py")
ROLLBACK_PY = os.path.join(HOME, ".walkman_rollback.py")
KEYFILE = os.path.join(HOME, ".walkman_key")
SOVIETFILE = os.path.join(HOME, ".walkman_soviet")
BASHRC = os.path.join(HOME, ".bashrc")
SERVICE, NAME = "Walkman Red Star", "YOUTUBE_API_KEY"
SOVIET_DEFAULT = "https://youtube.com/playlist?list=PLE2-L24KLxvw"
ARCH = "RED_STAR_ARCHIVE"

# (sha256 of the decompressed bytes, zlib+base64 payload)
SHA_MAIN = "@@SHA_MAIN@@"
SHA_ART = "@@SHA_ART@@"
SHA_V15 = "@@SHA_V15@@"
SHA_V16 = "@@SHA_V16@@"
SHA_V16A = "@@SHA_V16A@@"
B64_MAIN = "@@B64_MAIN@@"
B64_ART = "@@B64_ART@@"
B64_V15 = "@@B64_V15@@"
B64_V16 = "@@B64_V16@@"
B64_V16A = "@@B64_V16A@@"

RED="\033[1;31m"; GRN="\033[1;32m"; YEL="\033[1;33m"; OFF="\033[0m"
def say(m): print(f"{RED}[*]{OFF} {m}")
def ok(m):  print(f"{GRN}[+]{OFF} {m}")
def warn(m):print(f"{YEL}[!]{OFF} {m}")
def die(m): print(f"{RED}[x] {m}{OFF}"); sys.exit(1)

def unpack(b64, sha, what):
    try: data = zlib.decompress(base64.b64decode(b64))
    except Exception: die(f"Embedded {what} is corrupt (cannot decode). Nothing was changed.")
    if hashlib.sha256(data).hexdigest() != sha:
        die(f"Embedded {what} is corrupt (checksum mismatch). Nothing was changed.")
    return data

print(RED + "   *** WALKMAN // RED STAR SIGNAL DIRECTORATE ***" + OFF)
print("        upgrade to Build v14 / 1.6.1  (the Soyuz edition)\n")

# ---------- 0. verify the payloads BEFORE touching anything ----------
MAIN_BYTES = unpack(B64_MAIN, SHA_MAIN, "player build")
ART_BYTES = unpack(B64_ART, SHA_ART, "art module")
V15_BYTES = unpack(B64_V15, SHA_V15, "known-good 1.5")
V16_BYTES = unpack(B64_V16, SHA_V16, "known-good 1.6 player")
V16A_BYTES = unpack(B64_V16A, SHA_V16A, "known-good 1.6 art")

# ---------- 1. BACKUP FIRST ----------
def pick_backup_dir():
    ts = time.strftime("%Y-%m-%d_%H%M%S")
    dl = os.path.join(HOME, "storage", "downloads")
    base = dl if os.path.isdir(dl) else HOME
    stem = os.path.join(base, "WALKMAN_BACKUP_" + ts)
    d, n = stem, 1
    while os.path.exists(d):
        d = f"{stem}_{n}"; n += 1
    os.makedirs(d, exist_ok=False)
    return d

try:
    BK = pick_backup_dir()
except Exception as e:
    die(f"Could not create a backup folder ({e}). Nothing was changed.")

def backup(path, required=False):
    if not os.path.exists(path):
        if required: die(f"Expected file missing, refusing to continue: {path}")
        return
    try:
        dst = os.path.join(BK, os.path.basename(path.rstrip("/")))
        if os.path.isdir(path): shutil.copytree(path, dst)
        else: shutil.copy2(path, dst)
    except Exception as e:
        die(f"Backup of {path} FAILED ({e}). Nothing was changed.")

had_old = os.path.exists(TARGET)
backup(TARGET); backup(ART_TARGET); backup(KEYFILE); backup(SOVIETFILE); backup(BASHRC)
if PREFIX:
    backup(os.path.join(PREFIX, "bin", "walkman"))
    backup(os.path.join(PREFIX, "bin", "walkman-rollback"))
for rel in (os.path.join(ARCH, "Art"), os.path.join(ARCH, "soviet_playlist.txt")):
    p = os.path.join(HOME, rel)
    if not os.path.exists(p): p = os.path.join(os.getcwd(), rel)
    backup(p)
if had_old:
    if not os.path.exists(os.path.join(BK, "walkman.py")) or \
       open(os.path.join(BK, "walkman.py"), "rb").read() != open(TARGET, "rb").read():
        die("Backup verification failed. Nothing was changed.")
    ok(f"Backup written and verified: {BK}")
else:
    ok(f"Backup folder ready (no previous walkman.py found): {BK}")

# ---------- 2. INSTALL ----------
def stage(path, data, label):
    tmp = path + ".new"
    with open(tmp, "wb") as fh: fh.write(data)
    try: py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        os.remove(tmp); die(f"{label} did not compile; your old files are untouched. {e}")
    return tmp

tmp_main = stage(TARGET, MAIN_BYTES, "New player build")
tmp_art = stage(ART_TARGET, ART_BYTES, "Art module")
old_art_existed = os.path.exists(ART_TARGET)
os.replace(tmp_art, ART_TARGET)
os.replace(tmp_main, TARGET)
try:
    py_compile.compile(TARGET, doraise=True); py_compile.compile(ART_TARGET, doraise=True)
    ok("Installed and compiled ~/walkman.py (1.6.1) and ~/walkman_art.py.")
except py_compile.PyCompileError as e:
    if had_old: shutil.copy2(os.path.join(BK, "walkman.py"), TARGET)
    if os.path.exists(os.path.join(BK, "walkman_art.py")): shutil.copy2(os.path.join(BK, "walkman_art.py"), ART_TARGET)
    elif os.path.exists(ART_TARGET): os.remove(ART_TARGET)
    die(f"Post-install check failed; ROLLED BACK to your old version. {e}")

# on-device self-test of the 3D engine
try:
    out = subprocess.run([sys.executable, "-c", "import walkman_art as A; print(A.selftest())"], cwd=HOME,
                         capture_output=True, text=True, timeout=120)
    if out.returncode == 0:
        ok("3D self-test passed on this device: " + out.stdout.strip())
    else:
        raise RuntimeError((out.stderr or out.stdout).strip().splitlines()[-1] if (out.stderr or out.stdout).strip() else "unknown")
except Exception as e:
    warn(f"3D self-test FAILED ({e}). Art disabled; Walkman will run like 1.5.")
    try: os.remove(ART_TARGET)
    except OSError: pass

# known-good copies of 1.5 and 1.6
try:
    with open(KNOWN_GOOD, "wb") as fh: fh.write(V15_BYTES)
    ok("Known-good Build 1.5 saved to ~/.walkman_known_good_1_5.py")
except Exception as e:
    warn(f"Could not write the known-good 1.5 copy ({e}).")
try:
    with open(KNOWN_GOOD_16, "wb") as fh: fh.write(V16_BYTES)
    with open(KNOWN_GOOD_16A, "wb") as fh: fh.write(V16A_BYTES)
    ok("Known-good Build 1.6 saved to ~/.walkman_known_good_1_6.py (+ _art)")
except Exception as e:
    warn(f"Could not write the known-good 1.6 copy ({e}).")

# ---------- 3. LAUNCHER + ROLLBACK COMMAND ----------
ROLLBACK_SRC = r'''#!/usr/bin/env python3
import glob, os, shutil, sys
HOME = os.path.expanduser("~")
dirs = sorted(glob.glob(os.path.join(HOME, "storage", "downloads", "WALKMAN_BACKUP_*")) + glob.glob(os.path.join(HOME, "WALKMAN_BACKUP_*")),
              key=lambda p: os.path.basename(p))
dirs = [d for d in dirs if os.path.exists(os.path.join(d, "walkman.py"))]
if "--list" in sys.argv:
    print("\n".join(dirs) or "no backups found"); sys.exit(0)
if "--1.6" in sys.argv:
    src = os.path.join(HOME, ".walkman_known_good_1_6.py"); sa = os.path.join(HOME, ".walkman_known_good_1_6_art.py")
    if not (os.path.exists(src) and os.path.exists(sa)): print("no known-good 1.6 copy found"); sys.exit(1)
    shutil.copy2(src, os.path.join(HOME, "walkman.py")); shutil.copy2(sa, os.path.join(HOME, "walkman_art.py"))
    print("Restored known-good Build 1.6 (player + art). Start with: walkman"); sys.exit(0)
if "--1.5" in sys.argv:
    src = os.path.join(HOME, ".walkman_known_good_1_5.py")
    if not os.path.exists(src): print("no known-good 1.5 copy found"); sys.exit(1)
    shutil.copy2(src, os.path.join(HOME, "walkman.py"))
    print("Restored known-good Build 1.5 -> ~/walkman.py. Start with: walkman"); sys.exit(0)
if not dirs: print("no backup folders found (try --1.6 or --1.5)"); sys.exit(1)
d = dirs[-1]
shutil.copy2(os.path.join(d, "walkman.py"), os.path.join(HOME, "walkman.py"))
art_b = os.path.join(d, "walkman_art.py")
if os.path.exists(art_b): shutil.copy2(art_b, os.path.join(HOME, "walkman_art.py"))
print("Restored walkman.py from " + d + ". Start with: walkman")
'''
try:
    with open(ROLLBACK_PY, "w", encoding="utf-8", newline="\n") as fh: fh.write(ROLLBACK_SRC)
    ok("Rollback tool written (~/.walkman_rollback.py).")
except Exception as e:
    warn(f"Could not write the rollback tool ({e}).")

if PREFIX:
    launch = os.path.join(PREFIX, "bin", "walkman")
    rb = os.path.join(PREFIX, "bin", "walkman-rollback")
    try:
        with open(launch, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!" + os.path.join(PREFIX, "bin", "bash") + "\n")
            fh.write('if [ "$1" = "--safe" ]; then export WALKMAN_SAFE=1; shift; fi\n')
            fh.write('pulseaudio --check 2>/dev/null || pulseaudio --start --exit-idle-time=-1\n')
            fh.write('mkdir -p "$PREFIX/tmp"\n')
            fh.write('cd "$HOME" && exec python "$HOME/walkman.py" "$@"\n')
        os.chmod(launch, 0o755)
        with open(rb, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!" + os.path.join(PREFIX, "bin", "bash") + "\n")
            fh.write('exec python "$HOME/.walkman_rollback.py" "$@"\n')
        os.chmod(rb, 0o755)
        ok("`walkman` launcher updated - just type:  walkman     (safe mode: walkman --safe)")
        ok("`walkman-rollback` installed.")
    except Exception as e:
        warn(f"Could not write the launchers ({e}); start with: python ~/walkman.py")
else:
    say("Not Termux: start it with  python ~/walkman.py")

# ---------- 4. KEYRING ----------
try:
    import keyring
except ImportError:
    say("Installing keyring...")
    if shutil.which("pkg"):
        subprocess.call(["pkg", "install", "-y", "python-cryptography"])
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "keyring", "keyrings.alt"])
    try: importlib.invalidate_caches(); import keyring
    except Exception as e: warn(f"keyring not available ({e}); Walkman will still ask once."); keyring = None

if keyring:
    try:
        have = (keyring.get_password(SERVICE, NAME) or "").strip()
    except Exception as e:
        warn(f"Keyring not usable ({e})."); have = None
    if have:
        ok("YouTube API key is in the keyring.")
    elif have is not None:
        old = ""
        try: old = open(KEYFILE, encoding="utf-8").read().strip()
        except OSError: pass
        if old:
            try:
                keyring.set_password(SERVICE, NAME, old)
                if (keyring.get_password(SERVICE, NAME) or "").strip() == old:
                    os.remove(KEYFILE); ok("API key moved from ~/.walkman_key into the keyring.")
            except Exception as e: warn(f"Could not move the key ({e}); ~/.walkman_key left in place.")
        else:
            ok("No key saved yet - Walkman asks once and stores it in the keyring.")

# ---------- 5. SOVIET PLAYLIST + ART DIR ----------
os.makedirs(os.path.join(HOME, ARCH, "Art"), exist_ok=True)
if not os.path.exists(SOVIETFILE):
    try:
        with open(SOVIETFILE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# One YouTube playlist (or video) URL. [S] in Walkman autoplays it.\n")
            fh.write(SOVIET_DEFAULT + "\n")
        ok("Soviet playlist set in ~/.walkman_soviet (edit to change).")
    except Exception as e:
        warn(f"Could not write ~/.walkman_soviet ({e}); the built-in default still works.")
else:
    ok("Kept your existing ~/.walkman_soviet.")

# ---------- optional autostart ----------
BEGIN, END = "# >>> walkman autostart >>>\n", "# <<< walkman autostart <<<\n"
AUTO = (BEGIN +
    "# Opening Termux starts Walkman (Q drops to the shell). Off: touch ~/.walkman_noauto\n"
    'if [ -z "$WALKMAN_AUTO_DONE" ] && [ ! -e "$HOME/.walkman_noauto" ] && [ -x "$PREFIX/bin/walkman" ]; then\n'
    "  export WALKMAN_AUTO_DONE=1\n"
    '  if ! { command -v pgrep >/dev/null 2>&1 && pgrep -f "walkman.py" >/dev/null 2>&1; }; then walkman; fi\n'
    "fi\n" + END)
if "--autostart" in sys.argv or "--no-autostart" in sys.argv:
    try: rc = open(BASHRC, encoding="utf-8").read()
    except OSError: rc = ""
    if BEGIN in rc and END in rc:
        rc = rc[:rc.index(BEGIN)] + rc[rc.index(END)+len(END):]
    if "--autostart" in sys.argv:
        rc = rc + ("" if rc.endswith("\n") or not rc else "\n") + AUTO
        ok("Autostart on: opening Termux now launches Walkman.")
    else:
        ok("Autostart removed.")
    open(BASHRC, "w", encoding="utf-8", newline="\n").write(rc)

print()
ok("Done. Start it with:  walkman")
print("    New: [U] SOYUZ launch + a countdown splash (once a day, any key skips).  Also [H] [W] [K] [O] [F] [Z] as in 1.6")
print("    Trouble?  walkman --safe   |   walkman-rollback   |   walkman-rollback --1.6   |   walkman-rollback --1.5")
print(f"    Backup kept at: {BK}")
