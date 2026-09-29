#!/usr/bin/env python3
"""
YT Terminal Player - compact, low-overhead terminal YouTube player.

Manual requirement: install mpv and ensure `mpv` is on PATH.
Everything else installs automatically on first run.

Controls:
  /          URL, playlist URL, or search phrase
  Space      pause/resume
  n / p      next/previous
  Left/Right seek -5/+5 seconds
  Up/Down    volume +5/-5
  m          mute
  v          video on/off (audio-only uses fewer resources)
  q          quit
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


# Kept in-script as requested. An environment variable overrides it if present.
YOUTUBE_API_KEY = os.environ.get(
    "YOUTUBE_API_KEY", "AIzaSyCnoMnhj1_RFNyvdPgRcSzTi2oVJQxvyzE"
)
URL_RE = re.compile(r"^https?://", re.I)
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def is_url(text):
    return bool(URL_RE.match(text.strip()))


def is_playlist_url(url):
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    return parsed.path.rstrip("/").endswith("/playlist") and bool(query.get("list"))


def search_youtube(query):
    """Search YouTube Data API v3 and return the first playable video."""
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
    """Resolve direct stream URLs, preserving separate audio when necessary."""
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

        video_url = next(
            (f.get("url") for f in requested if f.get("vcodec") != "none"), None
        )
        audio_url = next(
            (f.get("url") for f in requested if f.get("acodec") != "none"), None
        )
        # A progressive format has both tracks in one URL.
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
                    self.status = f"Playlist armed: {len(tracks)} tracks"
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
    curses.init_pair(2, curses.COLOR_MAGENTA, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)


def draw(stdscr, player, input_mode, choose_mode, input_buffer, tick):
    height, width = stdscr.getmaxyx()
    stdscr.erase()
    if height < 15 or width < 52:
        stdscr.addstr(0, 0, "Resize terminal to at least 52 x 15")
        stdscr.refresh()
        return

    panel = min(width - 2, 84)
    snap = player.snapshot()
    cyan = curses.color_pair(1)
    magenta = curses.color_pair(2)
    green = curses.color_pair(3)
    yellow = curses.color_pair(4)
    red = curses.color_pair(5)

    def put(y, text, style=0):
        try:
            stdscr.addstr(y, 1, clip(text, panel), style)
        except curses.error:
            pass

    border = "=" * panel
    spinner = "|/-\\"[tick % 4] if player.busy else "*"
    put(0, border, cyan)
    put(1, f" {spinner} YT TERMINAL PLAYER // NIGHT DRIVE EDITION", magenta | curses.A_BOLD)
    put(2, border, cyan)
    put(3, " NOW TRANSMITTING", yellow | curses.A_BOLD)
    put(4, " " + clip(snap["title"], panel - 2), curses.A_BOLD)

    duration = snap["duration"]
    ratio = min(1.0, snap["position"] / duration) if duration else 0
    bar_width = max(10, panel - 26)
    filled = int(bar_width * ratio)
    progress = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
    state = "NO MEDIA" if snap["idle"] else ("PAUSED" if snap["paused"] else "PLAYING")
    state_style = magenta if snap["idle"] else (yellow if snap["paused"] else green)
    put(6, f" {progress} {fmt_time(snap['position'])}/{fmt_time(duration)}", cyan)
    put(7, f" {state}  VOL {int(snap['volume']):3d}%{'  MUTED' if snap['muted'] else ''}", state_style | curses.A_BOLD)
    if snap["count"] > 1:
        put(8, f" TRACK {snap['index']}/{snap['count']}  //  {'AUDIO ONLY' if player.audio_only else 'VIDEO + AUDIO'}", magenta)
    else:
        put(8, f" SINGLE TRANSMISSION  //  {'AUDIO ONLY' if player.audio_only else 'VIDEO + AUDIO'}", magenta)

    put(10, " [SPACE] pause  [N/P] track  [ARROWS] seek/volume  [M] mute", 0)
    put(11, " [V] video/eco  [/] new signal  [Q] quit", 0)
    put(12, "-" * panel, cyan)
    if choose_mode:
        put(13, " PLAY MODE: [1] VIDEO + AUDIO    [2] AUDIO ONLY    [ESC] CANCEL", yellow | curses.A_BOLD)
    elif input_mode:
        put(13, "> " + input_buffer + "_", yellow | curses.A_BOLD)
    else:
        style = red if any(x in player.status.lower() for x in ("error", "failed", "not found")) else green
        put(13, " " + player.status, style)
    put(14, border, cyan)
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
