#!/usr/bin/env python3
"""
YT Terminal Player - RED STAR EDITION (Secure Build)

Manual requirement: install mpv and ensure `mpv` is on PATH.
Everything else installs automatically on first run.
"""

import html
import json
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

def pip_install(package):
    print(f"Installing {package} (one time only)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

try:
    import curses
except ImportError:
    if platform.system() != "Windows":
        raise
    pip_install("windows-curses")
    import curses

try:
    from python_mpv_jsonipc import MPV, MPVError
except ImportError:
    pip_install("python-mpv-jsonipc")
    from python_mpv_jsonipc import MPV, MPVError

try:
    from yt_dlp import YoutubeDL
except ImportError:
    pip_install("yt-dlp")
    from yt_dlp import YoutubeDL

# --- SECURE CREDENTIAL MANAGER ---
def _load_youtube_api_key():
    env_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        import keyring
    except ImportError:
        pip_install("keyring")
        import keyring
    saved = (keyring.get_password("Walkman Red Star", "youtube_api_key") or "").strip()
    if saved:
        return saved
    key = getpass.getpass("ENTER YOUTUBE API KEY (HIDDEN / ONE TIME): ").strip()
    if not key:
        raise RuntimeError("A YouTube API key is required for text search.")
    keyring.set_password("Walkman Red Star", "youtube_api_key", key)
    return key

YOUTUBE_API_KEY = _load_youtube_api_key()
# ---------------------------------

URL_RE = re.compile(r"^https?://", re.I)
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

def is_url(text):
    return bool(URL_RE.match(text.strip()))

def is_playlist_url(url):
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    return bool(query.get("list"))

def search_youtube(query):
    if not YOUTUBE_API_KEY:
        return None, "No YouTube API key configured"
    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "maxResults": 1,
        "type": "video",
        "key": YOUTUBE_API_KEY,
    })
    request = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/search?" + params,
        headers={"User-Agent": "YT-Terminal-Player/2.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
        items = payload.get("items", [])
        if not items:
            return None, "No videos found"
        video_id = items[0].get("id", {}).get("videoId", "")
        if not VIDEO_ID_RE.match(video_id):
            return None, "Search returned an invalid video ID"
        title = html.unescape(items[0].get("snippet", {}).get("title", video_id))
        return f"https://www.youtube.com/watch?v={video_id}", title
    except Exception as exc:
        return None, f"Search failed: {exc}"

def resolve_media(url, audio_only):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "format": "bestaudio/best" if audio_only else "bestvideo*+bestaudio/best",
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None, None, None, "yt-dlp returned no media information"
        title = html.unescape(info.get("title") or "YouTube media")
        requested = info.get("requested_formats") or []
        if audio_only:
            audio_url = info.get("url") or next(
                (f.get("url") for f in requested if f.get("acodec") != "none"), None
            )
            return None, audio_url, title, None if audio_url else "No audio stream found"

        video_url = next((f.get("url") for f in requested if f.get("vcodec") != "none"), None)
        audio_url = next((f.get("url") for f in requested if f.get("acodec") != "none"), None)
        
        if not requested and info.get("url"):
            video_url = info["url"]
            audio_url = None
        if not video_url:
            return None, None, None, "No video stream found"
        return video_url, audio_url, title, None
    except Exception as exc:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
        return None, None, None, f"Could not resolve media: {clean}"

def expand_playlist(url):
    options = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        return None, f"Could not read playlist: {exc}"

    tracks = []
    for entry in (info or {}).get("entries") or []:
        if not entry:
            continue
        video_id = entry.get("id")
        if video_id and VIDEO_ID_RE.match(video_id):
            title = html.unescape(entry.get("title") or video_id)
            tracks.append((f"https://www.youtube.com/watch?v={video_id}", title))
    return (tracks, None) if tracks else (None, "Playlist is empty, private, or unavailable")

def fmt_time(value):
    total = max(0, int(value or 0))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

def clip(text, width):
    text = str(text).replace("\n", " ")
    return text[:max(0, width)]

class Player:
    def __init__(self):
        if shutil.which("mpv") is None:
            raise RuntimeError("mpv was not found on PATH. Install mpv, then run again.")
        self.mpv = MPV(input_default_bindings=True, osc=True, idle=True, force_window="no")
        self.status = "Press / to enter a URL, playlist, or search phrase"
        self.queue_titles = []
        self.busy = False
        self.video_enabled = True
        self.audio_only = False

    def load_async(self, text, audio_only=False):
        if self.busy:
            self.status = "Already loading..."
            return
        self.busy = True
        self.status = "Searching the signal..."
        threading.Thread(target=self._load, args=(text.strip(), audio_only), daemon=True).start()

    def _load(self, text, audio_only):
        self.audio_only = audio_only
        self.video_enabled = not audio_only
        try:
            self.mpv.vid = "no" if audio_only else "auto"
        except Exception:
            pass
        try:
            if not text:
                return
            if is_url(text):
                if is_playlist_url(text):
                    self.status = "Fetching playlist..."
                    tracks, error = expand_playlist(text)
                    if error:
                        self.status = error
                        return
                    self.mpv.loadfile(tracks[0][0], "replace")
                    for url, _ in tracks[1:]:
                        self.mpv.loadfile(url, "append")
                    self.queue_titles = [title for _, title in tracks]
                    try:
                        mpv_count = int(self.mpv.playlist_count or 0)
                    except Exception:
                        mpv_count = len(tracks)
                    self.status = f"Playlist armed: {len(tracks)} tracks // MPV queue: {mpv_count}"
                else:
                    self.status = "Resolving media streams..."
                    video_url, audio_url, title, error = resolve_media(text, audio_only)
                    if error:
                        self.status = error
                        return
                    if audio_only:
                        self.mpv.loadfile(audio_url, "replace")
                    else:
                        self.mpv.loadfile(video_url, "replace")
                        if audio_url:
                            self.mpv.audio_add(audio_url, "select")
                    self.queue_titles = [title]
                    self.status = f"Playing: {title}"
            else:
                url, title = search_youtube(text)
                if url is None:
                    self.status = title
                    return
                self.status = f"Found: {title} // resolving streams..."
                video_url, audio_url, resolved_title, error = resolve_media(url, audio_only)
                if error:
                    self.status = error
                    return
                if audio_only:
                    self.mpv.loadfile(audio_url, "replace")
                else:
                    self.mpv.loadfile(video_url, "replace")
                    if audio_url:
                        self.mpv.audio_add(audio_url, "select")
                self.queue_titles = [resolved_title or title]
                self.status = f"Playing: {resolved_title or title}"
        except Exception as exc:
            self.status = f"Load error: {exc}"
        finally:
            self.busy = False

    def command(self, name, *args):
        try:
            getattr(self.mpv, name)(*args)
        except Exception as exc:
            self.status = f"mpv: {exc}"

    def toggle_pause(self): self.command("cycle", "pause")
    def next_track(self): self.command("playlist_next", "force")
    def prev_track(self): self.command("playlist_prev", "force")
    def seek(self, seconds): self.command("seek", seconds, "relative")
    def toggle_mute(self): self.command("cycle", "mute")

    def change_volume(self, amount):
        try:
            self.mpv.volume = max(0, min(130, float(self.mpv.volume or 0) + amount))
        except Exception:
            pass

    def toggle_video(self):
        try:
            self.video_enabled = not self.video_enabled
            self.mpv.vid = "auto" if self.video_enabled else "no"
            self.status = "Video enabled" if self.video_enabled else "Audio-only eco mode"
        except Exception as exc:
            self.status = f"Video toggle failed: {exc}"

    def snapshot(self):
        def get(name, fallback=None):
            try:
                value = getattr(self.mpv, name)
                return fallback if value is None else value
            except Exception:
                return fallback
        raw_index = get("playlist_pos", -1)
        index = int(raw_index) if raw_index is not None else -1
        queued = self.queue_titles[index] if 0 <= index < len(self.queue_titles) else None
        return {
            "title": queued or get("media_title", "No media loaded"),
            "paused": bool(get("pause", False)),
            "position": float(get("time_pos", 0) or 0),
            "duration": float(get("duration", 0) or 0),
            "volume": float(get("volume", 0) or 0),
            "muted": bool(get("mute", False)),
            "idle": bool(get("idle_active", True)),
            "index": index + 1 if index >= 0 else 0,
            "count": int(get("playlist_count", 0) or 0),
        }

    def close(self):
        try:
            self.mpv.terminate()
        except Exception:
            pass

def setup_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)

def draw(stdscr, player, input_mode, choose_mode, input_buffer, tick):
    height, width = stdscr.getmaxyx()
    stdscr.erase()
    if height < 30 or width < 100:
        msg = "ENLARGE TERMINAL TO 120 x 40  //  RED STAR DISPLAY REQUIRES 100 x 30"
        try:
            stdscr.addstr(0, 0, msg[:max(1, width - 1)], curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()
        return

    snap = player.snapshot()
    cyan, red, green, yellow = curses.color_pair(1), curses.color_pair(2), curses.color_pair(3), curses.color_pair(4)
    black_red = curses.color_pair(7)
    bright = curses.A_BOLD

    def at(y, x, text, style=0):
        try:
            if 0 <= y < height and 0 <= x < width:
                stdscr.addstr(y, x, str(text)[:max(0, width - x - 1)], style)
        except curses.error:
            pass

    star_frames = ("* + x +", "+ x * x", "x * + *", "+ x + x")
    stars = star_frames[tick % len(star_frames)]
    inner_left, inner_right = 20, width - 21
    for y in range(height - 1):
        texture = "#" if (y + tick // 4) % 2 == 0 else "%"
        at(y, 0, (texture * 18)[:18], red)
        at(y, width - 19, (texture * 18)[:18], red)
    for y in range(1, height - 2):
        at(y, 18, "||", red | bright)
        at(y, width - 21, "||", red | bright)

    left_art = [
        "      /\\      ", "     /  \\     ", "  *** ** ***   ",
        "   \\ ***** /   ", "    *******    ", "  ****   ****  ",
        "     ** **     ", "      /||\\     ", "     /_||_\\    ",
        "       ||      ", "    ___||___   ", "   /___||___\\  ",
        "      /||\\     ", "     /_||_\\    ", "    /__||__\\   ",
        "   /___||___\\  ", "  /____||____\\ ", " [====||||====] ",
        "      /||\\     ", " ____/_||_\\____", "| RED SIGNAL  |",
        "| DIRECTORATE |", "|_____________|",
    ]
    right_art = [
        "   .-========-. ", "  /############\\", " /####      ####\\",
        "|###  _    _ ###|", "|##  (o)  (o) ##|", "|##      >     ##|",
        "|###  .----.  ###|", "|#### '----' ####|", " \\############/ ",
        "  '---.  .---'  ", "      ||||      ", "   ___||||___   ",
        "  /##########\\  ", " /############\\ ", "|###  ORDER  ###|",
        "|###  RHYTHM ###|", "|###  SIGNAL ###|", "|##############|",
        " \\############/ ", "  \\##########/  ", "   '--------'   ",
        "  * RED STAR * ", "  AUDIO BUREAU ",
    ]
    for i, line in enumerate(left_art):
        at(3 + i, 1, line[:17], black_red if i in (2, 20, 21) else red | bright)
    for i, line in enumerate(right_art):
        at(3 + i, width - 18, line[:17], black_red if i in (14, 15, 16, 21) else red | bright)

    panel_w = inner_right - inner_left + 1
    at(0, inner_left, "#" * panel_w, red | bright)
    title = "*** WALKMAN // RED STAR SIGNAL DIRECTORATE // 1983 ***"
    at(1, inner_left + max(0, (panel_w - len(title)) // 2), title, red | bright)
    at(2, inner_left, "=" * panel_w, red | bright)
    at(height - 4, inner_left, "=" * panel_w, red | bright)
    slogan = f" {stars}  MUSIC IS THE ENGINE OF THE NIGHT  {stars} "
    at(height - 3, inner_left + max(0, (panel_w - len(slogan)) // 2), slogan, yellow | bright)
    at(height - 2, 0, "#" * (width - 1), red | bright)

    x = inner_left + 2
    content_w = max(42, panel_w - 4)
    spinner = "|/-\\"[tick % 4] if player.busy else "*"
    at(4, x, f"{spinner}  CENTRAL TRANSMISSION CONTROL", yellow | bright)
    at(5, x, "-" * content_w, red)
    at(7, x, "NOW TRANSMITTING", yellow | bright)
    at(8, x, clip(snap["title"], content_w), bright)

    duration = snap["duration"]
    ratio = min(1.0, snap["position"] / duration) if duration else 0
    bar_width = max(10, content_w - 22)
    filled = int(bar_width * ratio)
    progress = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
    state = "NO MEDIA" if snap["idle"] else ("PAUSED" if snap["paused"] else "PLAYING")
    state_style = red if snap["idle"] else (yellow if snap["paused"] else green)
    at(11, x, f"{progress} {fmt_time(snap['position'])}/{fmt_time(duration)}", cyan)
    at(12, x, f"{state}  VOL {int(snap['volume']):3d}%{'  MUTED' if snap['muted'] else ''}", state_style | bright)
    if snap["count"] > 1:
        at(13, x, f"TRACK {snap['index']}/{snap['count']}  //  {'AUDIO ONLY' if player.audio_only else 'VIDEO + AUDIO'}", red | bright)
    else:
        at(13, x, f"SINGLE TRANSMISSION  //  {'AUDIO ONLY' if player.audio_only else 'VIDEO + AUDIO'}", red | bright)

    at(16, x, "[SPACE] HOLD SIGNAL   [N/P] NEXT/PREVIOUS TRANSMISSION", 0)
    at(17, x, "[ARROWS] SEEK/VOLUME  [M] SILENCE  [V] VIDEO/ECO", 0)
    at(18, x, "[/] NEW DIRECTIVE     [Q] RETURN TO CIVILIAN LIFE", 0)
    at(20, x, "-" * content_w, red)
    if choose_mode:
        at(22, x, "PLAY MODE: [1] VIDEO + AUDIO  [2] AUDIO ONLY  [ESC] CANCEL", yellow | bright)
    elif input_mode:
        at(22, x, "> DIRECTIVE: " + input_buffer + "_", yellow | bright)
    else:
        style = red if any(v in player.status.lower() for v in ("error", "failed", "not found")) else green
        at(22, x, player.status, style | bright)
    at(25, x, "STATE AUDIO NETWORK // CHANNEL SECURE // RED STAR ONLINE", red)
    stdscr.refresh()

def run(stdscr):
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)
    stdscr.timeout(120)
    setup_colors()
    player = Player()
    input_mode = False
    choose_mode = False
    pending_input = ""
    buffer = ""
    tick = 0
    try:
        while True:
            draw(stdscr, player, input_mode, choose_mode, buffer, tick)
            tick += 1
            key = stdscr.getch()
            if key == -1:
                continue
            if choose_mode:
                if key in (ord("1"), ord("2")):
                    choose_mode = False
                    player.load_async(pending_input, audio_only=(key == ord("2")))
                    pending_input = ""
                elif key == 27:
                    choose_mode = False
                    pending_input = ""
                    player.status = "Load cancelled"
                continue
            if input_mode:
                if key in (10, 13, curses.KEY_ENTER):
                    input_mode = False
                    if buffer.strip():
                        pending_input = buffer.strip()
                        choose_mode = True
                    buffer = ""
                elif key == 27:
                    input_mode, buffer = False, ""
                elif key in (8, 127, curses.KEY_BACKSPACE):
                    buffer = buffer[:-1]
                elif 32 <= key <= 126:
                    buffer += chr(key)
                continue
            if key in (ord("q"), ord("Q")): break
            if key == ord(" "): player.toggle_pause()
            elif key in (ord("n"), ord("N")): player.next_track()
            elif key in (ord("p"), ord("P")): player.prev_track()
            elif key in (ord("m"), ord("M")): player.toggle_mute()
            elif key in (ord("v"), ord("V")): player.toggle_video()
            elif key == curses.KEY_LEFT: player.seek(-5)
            elif key == curses.KEY_RIGHT: player.seek(5)
            elif key == curses.KEY_UP: player.change_volume(5)
            elif key == curses.KEY_DOWN: player.change_volume(-5)
            elif key == ord("/"): input_mode, buffer = True, ""
    finally:
        player.close()

def main():
    try:
        curses.wrapper(run)
    except RuntimeError as exc:
        print(f"\nYT Terminal Player: {exc}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()