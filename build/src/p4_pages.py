

# ================================================================ PAGES =====
PAGE_KEYS = {"h": "hall", "w": "duga", "k": "choir", "o": "b59", "f": "fyodor", "u": "launch"}
MENU_LINE = "[H] HALL [W] DUGA [K] CHOIR [O] B-59 [F] FYODOR [U] SOYUZ [Z] 3D"
AMBIENT_KEYS = ("t34", "bear", "soyuz", "is2", "typhoon", "ak47", "sputnik", "t72", "soyuzcraft", "b59", "star", "rpg7", "mir", "lunokhod", "bear", "vostok", "mig21", "kv1", "t55")


def init_colors():
    if curses is None or not curses.has_colors(): return
    try: curses.init_pair(19, curses.COLOR_WHITE, -1)
    except Exception: pass


def new_state():
    return {"idx": 0, "inv": False, "auto": True, "fy_idx": 0, "t0": time.time(), "amb": os.environ.get("WALKMAN_AMBIENT", "on").lower() not in ("off", "0", "no"),
            "fy": Fyodor(), "amb_i": 0, "amb_cache": None, "amb_tick": -99, "msg": ""}


def _put(stdscr, y, x, text, style=0):
    try:
        h, w = stdscr.getmaxyx()
        if 0 <= y < h and 0 <= x < w and text:
            stdscr.addstr(y, x, str(text)[:max(0, w - x - 1)], style)
    except Exception: pass


def _putc(stdscr, y, x, ch, style=0):
    try:
        h, w = stdscr.getmaxyx()
        if 0 <= y < h - 0 and 0 <= x < w - 1: stdscr.addch(y, x, ch, style)
    except Exception: pass


def _styles():
    B = curses.A_BOLD
    return dict(red=curses.color_pair(2), yel=curses.color_pair(4), cyan=curses.color_pair(1), grn=curses.color_pair(3),
                white=curses.color_pair(19), B=B)


def _blit3d(stdscr, grid, top, left, inv, clip_l=0, clip_r=10 ** 6):
    S = _styles()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if not cell: continue
            ch, lvl = cell
            if inv:
                st = (curses.color_pair(7), curses.color_pair(18) | S["B"], curses.color_pair(13) | S["B"])[lvl]
            else:
                st = (S["red"], S["red"] | S["B"], S["yel"] | S["B"])[lvl]
            if clip_l <= left + x < clip_r: _putc(stdscr, top + y, left + x, ch, st)


def _chrome(stdscr, side, tick, title, controls, player):
    S = _styles()
    h, w = stdscr.getmaxyx()
    il, ir = side(stdscr, tick, h, w, S["red"], curses.color_pair(7), S["B"])
    pw = ir - il + 1
    _put(stdscr, 0, il, "#" * pw, S["red"] | S["B"])
    _put(stdscr, 1, il + max(0, (pw - len(title)) // 2), title[:pw], S["yel"] | S["B"])
    _put(stdscr, 2, il, "=" * pw, S["red"] | S["B"])
    _put(stdscr, h - 4, il, "=" * pw, S["red"] | S["B"])
    try:
        snap = player.snapshot()
        _put(stdscr, h - 3, il + 2, "PLAYING: " + str(snap["title"])[:pw - 14], S["yel"] | S["B"])
    except Exception: pass
    _put(stdscr, h - 2, il + 2, controls[:pw - 3], S["cyan"] | S["B"])
    return il, ir, pw, h, w


def _center_x(il, ir, width): return (il + ir) // 2 - width // 2


def _frame(st, key, tick, mesh, ay, ax, W, H, roll, minskip=1):
    """render3d with adaptive frame skipping: slow phones re-use the last frame instead of lagging the UI."""
    cache = st.setdefault("_c", {})
    c = cache.get(key)
    sig = (id(mesh), W, H)
    if c and c[0] == sig and tick - c[1] < c[3]: return c[2]
    t0 = time.time()
    g = render3d(mesh, ay, ax, W, H, roll)
    dt = time.time() - t0
    skip = max(minskip, 1 if dt < 0.045 else (2 if dt < 0.11 else 3))
    cache[key] = (sig, tick, g, skip)
    return g


# ----------------------------------------------------------------- hall ------
def draw_hall(stdscr, player, tick, st, side):
    S = _styles()
    n = len(MODEL_DEFS)
    idx = (tick // 190) % n if st["auto"] else st["idx"] % n
    name, specs, tilt, speed, mesh, roll = get_model(idx)
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  3D HALL OF MACHINES  //  %02d/%02d  //  %s" % (idx + 1, n, name),
                               "[<>] STEP  [A] %s  [I] %s  [H/TAB] BACK  [SPACE] HOLD" % ("AUTO" if st["auto"] else "MANUAL", "INVERSE" if st["inv"] else "NORMAL"), player)
    W, H = min(pw - 4, 76), max(10, h - 12)
    grid = _frame(st, "hall", tick, mesh, tick * 0.055 * speed, tilt, W, H, roll)
    _blit3d(stdscr, grid, 3, il + (pw - W) // 2, st["inv"])
    _put(stdscr, h - 8, _center_x(il, ir, len(name)), name, S["yel"] | S["B"])
    for i, line in enumerate(specs[:2]):
        _put(stdscr, h - 7 + i, _center_x(il, ir, len(line[:pw - 2])), line[:pw - 2], S["red"] | S["B"])
    if MODEL_DEFS[idx][0] == "sputnik" and int(time.time() * 2) % 2 == 0:
        _put(stdscr, 4, il + 3, "BEEP  20.005 MHz", S["yel"] | S["B"])


# ----------------------------------------------------------------- duga ------
def draw_duga(stdscr, player, tick, st, side):
    S = _styles()
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  ДУГА  //  DUGA  //  STEEL YARD  //  THE RUSSIAN WOODPECKER  *",
                               "[ENTER] PLAY WOODPECKER RECORDINGS  [W/TAB] BACK  [SPACE] HOLD", player)
    t = time.time()
    ticking = int(t * 10) % 2 == 0
    lx = _center_x(il, ir, 74)
    sweep = int(t * 7) % 22
    for r, line in enumerate(DUGA_ART):
        gold = abs((13 - r) - sweep) <= 0 or abs((13 - r) - sweep) == 1 and r % 2 == 0
        for c, ch in enumerate(line):
            if ch == ' ': continue
            if r < 5 and ch in ".*+'`": style = S["white"]
            elif r >= 12: style = S["grn"]
            elif gold and ch in "=|X+-#": style = S["yel"] | S["B"]
            else: style = S["red"] | S["B"]
            _putc(stdscr, 4 + r, lx + c, ch, style)
    _put(stdscr, 3, il + 3, "[ TICK ]" if ticking else "[      ]", (S["yel"] | S["B"]) if ticking else S["red"])
    _put(stdscr, 3, ir - 20, "10 Hz  7-19 MHz", S["cyan"] | S["B"])
    # sky-wave diagram: transmitter -> ionosphere -> target
    top = 18
    x_a, x_b = lx + 8, lx + 66
    span = x_b - x_a
    for k in range(span + 1):
        u = k / float(span)
        y = 4 - int(round(4.0 * math.sin(math.pi * u)))
        _putc(stdscr, top + y, x_a + k, '.', S["red"])
    _put(stdscr, top, _center_x(il, ir, 30), "~ ~ ~  I O N O S P H E R E  ~ ~ ~", S["cyan"] | S["B"])
    for k in range(8):
        u = ((t * 0.7) + k / 8.0) % 1.0
        y = 4 - int(round(4.0 * math.sin(math.pi * u)))
        _putc(stdscr, top + y, x_a + int(u * span), '@', S["yel"] | S["B"])
    _put(stdscr, top + 4, lx + 1, "[DUGA]", S["yel"] | S["B"])
    _put(stdscr, top + 4, lx + 67, "[LAUNCH]", S["yel"] | S["B"])
    _put(stdscr, top + 5, lx + 1, "=" * 74, S["grn"])
    # oscilloscope strip: one spike per pulse, scrolling
    off = int(t * 45)
    scope = "".join('|' if (i + off) % 9 == 0 else '_' for i in range(74))
    for i, ch in enumerate(scope):
        _putc(stdscr, top + 6, lx + i, ch, (S["yel"] | S["B"]) if ch == '|' else S["red"])
    for i, line in enumerate(DUGA_FACTS):
        _put(stdscr, top + 8 + i, il + 2, line[:pw - 3], S["white"] | S["B"] if i == 0 else S["red"] | S["B"])
    _put(stdscr, top + 16, _center_x(il, ir, len(DUGA_DEDICATION)), DUGA_DEDICATION[:pw - 2], S["yel"] | S["B"])


# ----------------------------------------------------------------- B-59 ------
def _countdown_text():
    today = datetime.date.today()
    ann = datetime.date(today.year, 10, 27)
    if today > ann: ann = datetime.date(today.year + 1, 10, 27)
    d = (ann - today).days
    yrs = ann.year - 1962
    if d == 0: return "TODAY is the %dth anniversary - 27 October" % yrs
    if d == 1: return "TOMORROW is the %dth anniversary - 27 October" % yrs
    return "%d days to the %dth anniversary - 27 October" % (d, yrs)


def draw_b59(stdscr, player, tick, st, side):
    S = _styles()
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  27 OCTOBER 1962  //  B-59  //  THE THREE KEYS  *",
                               "[O/TAB] BACK  [SPACE] HOLD  [I] INVERSE", player)
    name, specs, tilt, speed, mesh, roll = get_model([d[0] for d in MODEL_DEFS].index("b59"))
    W, H = min(pw - 4, 76), 11
    grid = _frame(st, "b59", tick, mesh, 0.85 * math.sin(tick * 0.035), tilt, W, H, roll)       # gentle swing: always broadside-ish
    _blit3d(stdscr, grid, 3, il + (pw - W) // 2, st["inv"])
    # sonar ping: concentric dots around the hull, every ~3 s
    ph = (time.time() % 3.0)
    if ph < 1.2:
        rr = int(ph * 14)
        _put(stdscr, 3 + H // 2, il + (pw // 2) - rr * 2, "(" * 1, S["cyan"] | S["B"])
        _put(stdscr, 3 + H // 2, il + (pw // 2) + rr * 2, ")" * 1, S["cyan"] | S["B"])
        _put(stdscr, 3, il + 2, "PING", S["cyan"] | S["B"])
    elif 1.2 <= ph < 1.5:
        _put(stdscr, 3, il + 2, "* THUD *  practice depth charge", S["yel"] | S["B"])
    # three boxes
    bw = 24
    gx = _center_x(il, ir, bw * 3 + 2)
    top = 15
    blink = int(time.time() * 2) % 2 == 0
    for i, (role, who, vote) in enumerate(KEY_BOX):
        x = gx + i * (bw + 1)
        no = (vote == "NO")
        sty = (S["yel"] | S["B"]) if (no and blink) else (S["white"] | S["B"] if no else S["red"] | S["B"])
        lines = ["+" + "-" * (bw - 2) + "+", "|" + role[:bw - 2].center(bw - 2) + "|", "|" + who[:bw - 2].center(bw - 2) + "|",
                 "|" + " " * (bw - 2) + "|", "|" + vote.center(bw - 2) + "|", "+" + "-" * (bw - 2) + "+"]
        for r, ln in enumerate(lines): _put(stdscr, top + r, x, ln, sty)
    _put(stdscr, top + 7, _center_x(il, ir, 38), "A LAUNCH NEEDED THEM ALL. ONE SAID NO.", S["yel"] | S["B"])
    for i, line in enumerate(B59_STORY):
        _put(stdscr, top + 9 + i, il + 2, line[:pw - 3], S["red"] | S["B"])
    _put(stdscr, top + 18, il + 2, "Arkhipov was not the captain - he was the flotilla chief of staff.", S["cyan"])
    _put(stdscr, top + 19, _center_x(il, ir, 52), _countdown_text(), S["yel"] | S["B"])


# ---------------------------------------------------------------- choir ------
def draw_choir(stdscr, player, tick, st, side):
    S = _styles()
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  RED CHOIR  //  КАЗАЧОК  //  with a Kazakh yurt, kalpak and dombra  *",
                               "[ENTER] KAZACHOK  [2] KAZAKH DOMBRA  [K/TAB] BACK  [SPACE] HOLD", player)
    cx = (il + ir) // 2
    # sun, mountains, eagle
    sun_y = 5
    for i, ln in enumerate(["  \\ | /  ", " -- O -- ", "  / | \\  "]): _put(stdscr, sun_y + i, il + 6, ln, S["yel"] | S["B"])
    mtn = "      /\\    /\\/\\        /\\       /\\/\\    /\\        /\\/\\     /\\    "
    mtn2 = "     /  \\  /    \\  /\\  /  \\  /\\/    \\  /  \\  /\\  /    \\ /  \\   "
    _put(stdscr, 9, il + 2, mtn[:pw - 3], S["white"])
    _put(stdscr, 10, il + 2, mtn2[:pw - 3], S["white"])
    ex = (tick // 2) % (pw + 12) - 6
    eagle = ["\\_ _/" if (tick // 5) % 2 == 0 else "~v~  "][0]
    _put(stdscr, 6 + int(2 * math.sin(tick / 12.0)), il + ex, eagle, S["yel"] | S["B"])
    for i, ln in enumerate(YURT): _put(stdscr, 11 + i, il + 4, ln, S["red"] | S["B"])
    _put(stdscr, 11, il + 26, "KAZAKHSTAN STEPPE  -  shanyrak, kalpak, dombra", S["cyan"] | S["B"])
    # the choir: dombra player + dancers
    base = 20
    for r, ln in enumerate(DOMBRA_PLAYER): _put(stdscr, base + 2 + r, il + 2, ln, S["red"] | S["B"])
    step = tick // 4
    n_d = 5
    x0 = il + 20
    for i in range(n_d):
        pose = DANCE_SEQ[(step + i * 3) % len(DANCE_SEQ)]
        art = DANCER[pose]
        for r, ln in enumerate(art):
            sty = (S["yel"] | S["B"]) if r < 2 and pose != "squat" or (pose == "squat" and r == 2) else (S["red"] | S["B"])
            _put(stdscr, base + r, x0 + i * 12, ln, sty)
    _put(stdscr, base + 7, il + 1, ("=#" * 60)[:pw - 2], S["red"] | S["B"])
    caption = "squat . kick . squat . kick  -  the Kazachok, faster every verse"
    _put(stdscr, base + 9, _center_x(il, ir, len(caption)), caption, S["yel"] | S["B"])
    for i, ln in enumerate(["The Red Army Choir (Alexandrov Ensemble) was founded in 1928.",
                            "Kazachok: the squat-and-kick dance, arms folded across the chest.",
                            "Dombra: the two-string Kazakh lute - the steppe's own folk song."]):
        _put(stdscr, base + 10 + i, il + 2, ln[:pw - 3], S["cyan"] | S["B"] if i == 0 else S["cyan"])
    if st.get("msg"): _put(stdscr, base + 14, il + 2, st["msg"][:pw - 3], S["grn"] | S["B"])


# --------------------------------------------------------------- fyodor ------
def _dissolve(art, progress, seed):
    """Return art with cells hidden/glitched according to progress 0..1."""
    out = []
    for y, line in enumerate(art):
        row = []
        for x, ch in enumerate(line):
            if ch == ' ': row.append(' '); continue
            r = ((x * 73856093) ^ (y * 19349663) ^ (seed * 83492791)) % 1000 / 1000.0
            if r < progress - 0.25: row.append(ch)
            elif r < progress: row.append(random.choice(".:;'`,"))
            else: row.append(' ')
        out.append(''.join(row))
    return out


class Fyodor:
    """Rare ghostly visitations on the main screen (set WALKMAN_FYODOR=off to disable)."""
    DUR = 9.0

    def __init__(self):
        self.enabled = os.environ.get("WALKMAN_FYODOR", "on").lower() not in ("off", "0", "no")
        self.next_at = time.time() + random.uniform(80, 200)
        self.t0 = 0.0; self.idx = None
        self.order = list(range(len(FYODOR))); random.shuffle(self.order); self.pos = 0

    def trigger(self):
        self.idx = self.order[self.pos % len(self.order)]; self.pos += 1
        self.t0 = time.time()

    def update(self):
        now = time.time()
        if self.idx is None:
            if self.enabled and now >= self.next_at: self.trigger()
        elif now - self.t0 > self.DUR:
            self.idx = None; self.next_at = now + random.uniform(150, 420)

    def active(self): return self.idx is not None

    def draw(self, stdscr, il, ir, top, rows):
        S = _styles()
        title, art, caption = FYODOR[self.idx]
        age = time.time() - self.t0
        prog = min(1.0, age / 2.0, (self.DUR - age) / 2.0)
        prog = max(0.0, prog) * 1.25
        shown = _dissolve(art, prog, self.idx)
        aw = max(len(l) for l in art)
        x = (il + ir) // 2 - aw // 2
        ay = top + 1 + max(0, (8 - len(art)) // 2)
        _put(stdscr, top, (il + ir) // 2 - len(title) // 2, title if prog > 0.6 else "", S["yel"] | S["B"])
        for r, ln in enumerate(shown):
            for c, ch in enumerate(ln):
                if ch != ' ': _putc(stdscr, ay + r, x + c, ch, (S["white"] if prog < 1.0 else S["red"]) | S["B"])
        if prog > 0.9:
            _put(stdscr, top + 10, (il + ir) // 2 - len(caption) // 2, caption, S["yel"] | S["B"])
            _put(stdscr, top + 11, (il + ir) // 2 - len(FYODOR_TAG) // 2, FYODOR_TAG, S["cyan"])


def draw_fyodor(stdscr, player, tick, st, side):
    S = _styles()
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  FYODOR  //  Ф. М. Д.  //  %02d/%02d  *" % (st["fy_idx"] % len(FYODOR) + 1, len(FYODOR)),
                               "[<>] STEP  [F/TAB] BACK  [SPACE] HOLD  (he visits the main screen on his own)", player)
    rnd = random.Random(tick // 3)
    for _ in range(40):                                       # snow over Petersburg
        sx = rnd.randrange(il + 1, ir - 1); sy = (rnd.randrange(3, h - 6) + tick // 2) % (h - 9) + 3
        _putc(stdscr, sy, sx, rnd.choice(".*'"), S["white"])
    title, art, caption = FYODOR[st["fy_idx"] % len(FYODOR)]
    aw = max(len(l) for l in art)
    big = art
    ay = 8
    x = (il + ir) // 2 - aw // 2
    for r, ln in enumerate(big):
        for c, ch in enumerate(ln):
            if ch != ' ': _putc(stdscr, ay + r * 1, x + c, ch, S["red"] | S["B"])
    _put(stdscr, 5, (il + ir) // 2 - len(title) // 2, title, S["yel"] | S["B"])
    _put(stdscr, ay + len(art) + 3, (il + ir) // 2 - len(caption) // 2, caption, S["yel"] | S["B"])
    _put(stdscr, ay + len(art) + 5, (il + ir) // 2 - len(FYODOR_TAG) // 2, FYODOR_TAG, S["cyan"])


# ---------------------------------------------------------- main-screen extras
def draw_main_extras(stdscr, tick, st, il, ir):
    """Called after the main page: ambient 3D machine, and Fyodor's rare visits."""
    h, w = stdscr.getmaxyx()
    fy = st["fy"]
    fy.update()
    if fy.active():
        fy.draw(stdscr, il, ir, 24, 12)
        return
    if not st["amb"]: return
    S = _styles()
    n = len(AMBIENT_KEYS)
    keys = [d[0] for d in MODEL_DEFS]
    which = keys.index(AMBIENT_KEYS[(tick // 300) % n])
    W, H = min(ir - il - 4, 72), max(8, h - 5 - 25 - 1)
    name_, specs_, tilt, speed, mesh, roll = get_model(which)
    grid = _frame(st, "amb", tick, mesh, tick * 0.05 * speed, tilt, W, H, roll, minskip=2)
    _blit3d(stdscr, grid, 25, il + (ir - il + 1 - W) // 2, False)
    nm = get_model(which)[0]
    _put(stdscr, 24, il + 2, "[Z] hide   " + nm, S["red"])


# ------------------------------------------------------------ public API -----
_DRAW = {"hall": draw_hall, "duga": draw_duga, "b59": draw_b59, "choir": draw_choir, "fyodor": draw_fyodor, "launch": draw_launch}


def draw(page, stdscr, player, tick, st, side):
    _DRAW[page](stdscr, player, tick, st, side)


def handle_key(page, key, st, player, tick):
    """Return a page name to switch to, None to go back to the main screen, 'quit', or the same page."""
    if key in (ord("q"), ord("Q")): return "quit"
    if key in (27, 9, curses.KEY_BTAB): return None
    ch = chr(key).lower() if 0 <= key < 256 else ""
    if ch in PAGE_KEYS:
        return None if PAGE_KEYS[ch] == page else PAGE_KEYS[ch]
    if ch == "g": return None
    if key == ord(" "): player.toggle_pause()
    elif ch == "m": player.toggle_mute()
    elif ch == "n": player.next_track()
    elif ch == "p": player.prev_track()
    elif key == curses.KEY_UP: player.change_volume(5)
    elif key == curses.KEY_DOWN: player.change_volume(-5)
    elif ch == "i": st["inv"] = not st["inv"]
    elif page == "hall":
        n = len(MODEL_DEFS)
        if ch == "a": st["auto"] = not st["auto"]
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            if st["auto"]: st["idx"] = (tick // 190) % n
            st["auto"] = False
            st["idx"] = (st["idx"] + (1 if key == curses.KEY_RIGHT else -1)) % n
    elif page == "fyodor" and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
        st["fy_idx"] = (st["fy_idx"] + (1 if key == curses.KEY_RIGHT else -1)) % len(FYODOR)
    elif key == curses.KEY_LEFT: player.seek(-5)
    elif key == curses.KEY_RIGHT: player.seek(5)
    elif page == "duga" and key in (10, 13, curses.KEY_ENTER):
        _play(player, st, "Russian Woodpecker radio signal 10 Hz shortwave recording", 4, "Tuning the Woodpecker...")
    elif page == "choir" and key in (10, 13, curses.KEY_ENTER):
        _play(player, st, "Alexandrov Red Army Choir Kazachok", 5, "Kazachok!")
    elif page == "choir" and ch == "2":
        _play(player, st, "Kazakh dombra kui traditional", 5, "Dombra...")
    elif page == "launch" and ch == "r": st["lt0"] = time.time()
    elif page == "launch" and key in (10, 13, curses.KEY_ENTER):
        _play(player, st, "Soviet space songs Zemlya v illyuminatore", 5, "Cosmos songs...")
    elif page == "launch" and ch == "2":
        _play(player, st, "Gagarin Poyekhali 12 April 1961 launch audio", 3, "Poyekhali...")
    return page


def _play(player, st, phrase, n, msg):
    fn = getattr(player, "start_search_queue", None)
    if fn: fn(phrase, n); st["msg"] = msg
    else: st["msg"] = "search-play not available in this build"


def selftest():
    """Headless check used by the installer: build + render every model once, report ms/frame."""
    t0 = time.time(); n = 0
    for i in range(len(MODEL_DEFS)):
        name, specs, tilt, speed, mesh, roll = get_model(i)
        grid = render3d(mesh, 0.7, tilt, 72, 26, roll)
        if not any(any(row) for row in grid): raise RuntimeError("model %s rendered empty" % name)
        n += 1
    t1 = time.time()
    name, specs, tilt, speed, mesh, roll = get_model(0)
    for k in range(5): render3d(mesh, 0.1 * k, tilt, 76, 30, roll)
    ms = (time.time() - t1) / 5.0 * 1000.0
    for page_art in (DUGA_ART, DANCER["stand"], FYODOR[0][1]): assert page_art
    for tt in (3.0, 9.0, 15.0, 24.0, 30.0, 42.0):
        fr = launch_frame(tt, 76, 24, None)
        if not any(any(r) for r in fr): raise RuntimeError("launch frame empty at t=%s" % tt)
    return {"models": n, "ms_per_frame": round(ms, 1), "build_s": round(t1 - t0, 2)}
