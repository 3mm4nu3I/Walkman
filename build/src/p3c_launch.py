

# ====================================================== SOYUZ LAUNCH (1.6.1) =====
# A pure frame generator: launch_frame(t, W, H, st) -> rows of (char, colour-code) cells.
# Colour codes: R red-bold, r red, Y yellow-bold, W white-bold, w white, C cyan-bold, c cyan, G green-bold.
T_IGN, T_LIFT, T_BSEP, T_TOWER, T_CORE, T_ORBIT, T_END = 8.0, 10.0, 22.0, 27.0, 33.0, 39.0, 56.0
_CLOCK = ((T_LIFT, 0.0), (T_BSEP, 118.0), (T_TOWER, 160.0), (T_CORE, 290.0), (T_ORBIT, 530.0))

ROCKET_TOP = ["/\\", "||", "/||\\"]                                  # launch-escape tower
ROCKET_FAIR = ["/  \\", "/    \\", "|    |", "|----|"]                  # payload fairing
ROCKET_STAGE3 = ["|    |", "|CCCP|", "|    |", "/======\\"]
ROCKET_CORE = ["|      |", "|      |", "|      |", "|      |", "|      |", "/__||__\\"]
CAPSULE = [" .--. ", "( () )", " '--' ", " /||\\ ", "/_||_\\"]               # spacecraft once the fairing is gone
BOOST_L = ["  /|", " / |", "/  |", "|  |", "|  |", "|  |", "|__|", "/__\\"]   # left strap-on, drawn beside the core
BOOST_R = ["|\\  ", "| \\ ", "|  \\", "|  |", "|  |", "|  |", "|__|", "/__\\"]

LAUNCH_FACTS = [
    ("4 October 1957", "Sputnik 1 rides an R-7 into orbit: the first artificial satellite."),
    ("12 April 1961", "Vostok 1 from Baikonur, Site 1: Yuri Gagarin orbits Earth once, 108 minutes."),
    ("R-7 'Semyorka'", "Four strap-on boosters round a core: 20 main combustion chambers lit together."),
    ("23 April 1967", "Soyuz 1 flies. Vladimir Komarov did not come home; the design flew on."),
    ("17 July 1975", "Soyuz 19 docks with Apollo in orbit: the handshake in space."),
    ("The family today", "Boosters drop away about two minutes in; the third stage finishes the job near T+9."),
]
LAUNCH_NOTE = "Time-lapsed and stylised. Event times are approximate crewed-Soyuz values."


def _tplus(t):
    if t < T_LIFT: return None
    for (t0, c0), (t1, c1) in zip(_CLOCK, _CLOCK[1:]):
        if t < t1: return c0 + (c1 - c0) * (t - t0) / (t1 - t0)
    return _CLOCK[-1][1]


def _cell_put(g, y, x, text, code):
    if not (0 <= y < len(g)): return
    row = g[y]
    for i, ch in enumerate(text):
        if ch != ' ' and 0 <= x + i < len(row): row[x + i] = (ch, code)


def _sprite(g, y, x, rows, code):
    for i, r in enumerate(rows): _cell_put(g, y + i, x, r, code)


def _centered(rows, cx):
    """x offset for each row so that its centre sits on column cx."""
    return [cx - len(r) // 2 for r in rows]


def _flame(g, cx, y0, length, half, t, hot=True):
    """A flickering plume hanging below row y0."""
    for k in range(length):
        w = max(0, half - (k * half) // max(1, length - 1) if length > 1 else half)
        for dx in range(-w, w + 1):
            rnd = ((dx * 73 + k * 31 + int(t * 14) * 17) % 7)
            ch = "VWv|!"[rnd % 5] if abs(dx) < w or w == 0 else "'`."[rnd % 3]
            code = "Y" if (abs(dx) <= w // 2 and k < length - 1) else "R"
            _cell_put(g, y0 + k, cx + dx, ch, code if hot else "r")


def _stars(g, W, H, n, t):
    for i in range(n):
        x = (i * 37 + 11) % max(1, W - 2) + 1
        y = (i * 13 + 5) % max(1, H - 6)
        if ((i * 7 + int(t * 2)) % 9) == 0: continue          # twinkle
        _cell_put(g, y, x, "*" if i % 5 == 0 else ".", "W" if i % 5 == 0 else "w")


def _ground(g, W, H, base_y, alt, t, pre):
    gy = base_y + 1 + int(alt)
    if gy < H:
        for x in range(W): _cell_put(g, gy, x, "=" if x % 4 else "#", "G" if x % 4 else "r")
    # pad lattice towers
    cx = W // 2
    for side in (-1, 1):
        x = cx + side * 14
        for k in range(1, 12):
            y = gy - k
            if 0 <= y < H:
                _cell_put(g, y, x - 1, "|", "r"); _cell_put(g, y, x + 1, "|", "r")
                _cell_put(g, y, x, "X" if k % 2 else "-", "r")
        if pre:                                              # service arms hug the rocket until liftoff
            for k in (4, 7, 10):
                y = gy - k
                if 0 <= y < H:
                    a0, a1 = (x + 2, cx - 9) if side < 0 else (cx + 9, x - 2)
                    if a1 >= a0: _cell_put(g, y, a0, "=" * (a1 - a0 + 1), "r")
    # clouds of steam and dust
    if T_IGN - 1 <= t < T_END:
        age = t - (T_IGN - 1)
        for i in range(34):
            dx = ((i * 29) % 41) - 20
            if abs(dx) > 3 + age * 2.2: continue
            y = gy - ((i * 3) % 4) - int(age * 0.25 * ((i % 3) + 1) / 2.0)
            _cell_put(g, y, cx + dx, "o" if i % 3 == 0 else (":" if i % 3 == 1 else "."), "w")


def _speed_lines(g, W, H, alt, strength):
    for i in range(18):
        x = (i * 17 + 3) % max(1, W - 2) + 1
        if abs(x - W // 2) < 7: continue
        y = (i * 5 + int(alt * 3)) % H
        _cell_put(g, y, x, "|" if strength > 0.6 else ":", "w")


def _debris(g, W, H, cx, base_y, dt, rows, side, code, fall=1.0):
    if dt < 0: return
    dx = int(side * (2 + dt * 3.2))
    dy = int(dt * 2.0 + dt * dt * 1.6 * fall)
    for i, r in enumerate(rows):
        _cell_put(g, base_y - len(rows) + 1 + i + dy, cx + dx - len(r) // 2, r, code)


def _earth(g, W, H, t):
    cx, R, cy = W // 2, 70.0, H + 62.0
    for x in range(W):
        u = (x - cx) / 2.0
        if abs(u) >= R: continue
        y = int(round(cy - math.sqrt(R * R - u * u)))
        _cell_put(g, y, x, "~", "C")
        for k in range(1, 6):
            if y + k >= H: break
            n = ((x // 4 + int(t * 0.8)) * 7 + k * 5) % 13
            if n < 3: _cell_put(g, y + k, x, "#", "G")
            elif n < 6 and k < 4: _cell_put(g, y + k, x, ".", "c")


def launch_frame(t, W, H, st=None):
    g = [[None] * W for _ in range(H)]
    cx = W // 2
    base_y = H - 4                                           # row of the engine skirt on the pad
    a = max(0.0, t - T_LIFT)
    alt = 0.35 * a * a if t >= T_LIFT else 0.0
    rise = min(4, int(alt * 0.5))
    ry = base_y - rise                                       # row of the engine skirt now
    pre = t < T_LIFT - 0.4
    _stars(g, W, H, int(min(60, alt * 1.4)), t)
    if t >= T_ORBIT:                                         # ------------------------------ orbit
        _stars(g, W, H, 60, t)
        _earth(g, W, H, t)
        W3, H3 = min(W - 4, 56), max(8, H - 11)
        got = None
        try:
            idx = [d[0] for d in MODEL_DEFS].index("soyuzcraft")
            name, specs, tilt, speed, mesh, roll = get_model(idx)
            if st is not None: got = _frame(st, "launch3d", int(t * 12), mesh, (t - T_ORBIT) * 0.45, tilt, W3, H3, roll)
            else: got = render3d(mesh, (t - T_ORBIT) * 0.45, tilt, W3, H3, roll)
        except Exception:
            got = None
        if got:
            lx = (W - W3) // 2
            for y, row in enumerate(got):
                for x, c in enumerate(row):
                    if c: g[1 + y][lx + x] = (c[0], ("r", "R", "Y")[c[1]]) if 1 + y < H else None
        return g
    if t >= T_LIFT: _speed_lines(g, W, H, alt, min(1.0, a / 6.0))
    _ground(g, W, H, base_y, alt, t, pre)
    # --- layers of the stack, built bottom-up from the skirt row ry
    on_boost = t < T_BSEP
    on_tower = t < T_TOWER
    on_core = t < T_CORE
    top_y = ry
    def stack(block, code):
        nonlocal top_y
        top_y -= len(block) - 1
        for i, r in enumerate(block): _cell_put(g, top_y + i, cx - len(r) // 2, r, code)
        top_y -= 1
    core_top_y = None
    if on_core:
        stack(ROCKET_CORE, "R")
        core_top_y = top_y + 1
    stack(ROCKET_STAGE3, "R")
    s3_y = top_y + 1
    if on_tower:
        stack(ROCKET_FAIR, "R"); stack(ROCKET_TOP, "Y")
    else:
        stack(CAPSULE, "Y")
    # CCCP in yellow for flair
    for i in range(len(ROCKET_STAGE3)):
        if ROCKET_STAGE3[i] == "|CCCP|": _cell_put(g, s3_y + i, cx - 2, "CCCP", "Y")
    # strap-ons beside the core
    if on_boost and on_core:
        by = ry - len(BOOST_L) + 1
        for i in range(len(BOOST_L)):
            _cell_put(g, by + i, cx - 4 - len(BOOST_L[i]), BOOST_L[i], "R")
            _cell_put(g, by + i, cx + 4, BOOST_R[i], "R")
    # flames
    if t >= T_IGN:
        grow = min(1.0, (t - T_IGN) / 2.2)
        if on_boost and on_core:
            n = max(1, int(5 * grow))
            _flame(g, cx, ry + 1, n, 2, t)
            _flame(g, cx - 6, ry + 1, max(1, int(4 * grow)), 1, t)
            _flame(g, cx + 6, ry + 1, max(1, int(4 * grow)), 1, t)
        elif on_core:
            _flame(g, cx, ry + 1, 5, 2, t)
        else:
            _flame(g, cx, ry + 1, 3, 1, t)
    # separations: debris falls away behind the climbing stack
    _debris(g, W, H, cx, ry, t - T_BSEP, BOOST_L, -1, "r")
    _debris(g, W, H, cx, ry, t - T_BSEP, BOOST_R, 1, "r")
    _debris(g, W, H, cx, ry - 8, t - T_TOWER, ["/\\", "||", "||"], -1, "r", 0.6)
    _debris(g, W, H, cx, ry - 8, t - T_TOWER, ["/  \\", "/    \\", "|    |"], 1, "r", 0.6)
    _debris(g, W, H, cx, ry, t - T_CORE, ROCKET_CORE, 0, "r", 1.4)
    return g


def _launch_caption(t):
    if t < T_IGN:
        n = max(1, 10 - int(t / (T_IGN / 10.0)))
        return "T-%02d" % n, "COUNTDOWN"
    if t < T_LIFT: return "T-00", "ZAZHIGANIE  -  IGNITION"
    tp = _tplus(t)
    m, s = int(tp // 60), int(tp % 60)
    if t < T_LIFT + 3.0: ev = "POYEKHALI!   (\"Let's go!\")"
    elif t < T_BSEP: ev = "STAGE I:  four strap-ons and the core burn together"
    elif t < T_TOWER: ev = "BOOSTERS AWAY   -   core burns on"
    elif t < T_CORE: ev = "ESCAPE TOWER + FAIRING JETTISONED"
    elif t < T_ORBIT: ev = "STAGE III   -   last push to orbit"
    else: ev = "IN ORBIT   -   solar wings open, antennas out"
    return "T+%02d:%02d" % (m, s), ev


def draw_launch(stdscr, player, tick, st, side):
    S = _styles()
    il, ir, pw, h, w = _chrome(stdscr, side, tick, "*  SOYUZ  //  СОЮЗ  //  BAIKONUR  //  POYEKHALI!  *",
                               "[R] RESTART  [ENTER] SPACE SONGS  [2] GAGARIN  [U/TAB] BACK  [SPACE] HOLD", player)
    now = time.time()
    if now - st.get("lt_seen", 0) > 1.5: st["lt0"] = now                      # newly opened: start at T-10
    st["lt_seen"] = now
    t = (now - st.get("lt0", now)) % T_END
    Wc, Hc = min(pw - 2, 76), 24
    g = launch_frame(t, Wc, Hc, st)
    top, left = 3, il + (pw - Wc) // 2
    cmap = {"R": S["red"] | S["B"], "r": S["red"], "Y": S["yel"] | S["B"], "W": S["white"] | S["B"], "w": S["white"],
            "C": S["cyan"] | S["B"], "c": S["cyan"], "G": S["grn"] | S["B"]}
    for y, row in enumerate(g):
        for x, cell in enumerate(row):
            if cell: _putc(stdscr, top + y, left + x, cell[0], cmap.get(cell[1], 0))
    clock, ev = _launch_caption(t)
    _put(stdscr, 3, il + 3, clock, S["yel"] | S["B"])
    _put(stdscr, 4, il + 3, ev[:pw - 6], S["white"] | S["B"] if "POYEKHALI" in ev else S["cyan"] | S["B"])
    if t >= T_ORBIT:
        _put(stdscr, top + Hc - 1, _center_x(il, ir, 40), "ORBIT  -  the Soyuz spacecraft, in three modules", S["yel"] | S["B"])
    head, line = LAUNCH_FACTS[int(now / 6.0) % len(LAUNCH_FACTS)]
    _put(stdscr, top + Hc + 1, il + 2, head, S["yel"] | S["B"])
    _put(stdscr, top + Hc + 2, il + 2, line[:pw - 4], S["red"] | S["B"])
    _put(stdscr, top + Hc + 4, il + 2, LAUNCH_NOTE[:pw - 4], S["cyan"])
    if st.get("msg"): _put(stdscr, top + Hc + 6, il + 2, st["msg"][:pw - 4], S["grn"] | S["B"])


def splash(stdscr):
    """About four seconds of countdown and liftoff on start-up; any key skips. Once per day unless WALKMAN_SPLASH=always."""
    mode = os.environ.get("WALKMAN_SPLASH", "on").lower()
    if mode in ("off", "0", "no"): return
    h, w = stdscr.getmaxyx()
    if h < 40 or w < 120: return
    flag = os.path.join(os.path.expanduser("~"), ".walkman_splash_day")
    today = datetime.date.today().isoformat()
    if mode != "always":
        try:
            if open(flag).read().strip() == today: return
        except Exception: pass
    try:
        with open(flag, "w") as fh: fh.write(today)
    except Exception: pass
    S = _styles()
    cmap = {"R": S["red"] | S["B"], "r": S["red"], "Y": S["yel"] | S["B"], "W": S["white"] | S["B"], "w": S["white"],
            "C": S["cyan"] | S["B"], "c": S["cyan"], "G": S["grn"] | S["B"]}
    Wc, Hc = 76, 24
    t0 = time.time()
    while True:
        el = time.time() - t0
        t = 5.2 + el * 2.0
        if t > T_LIFT + 3.2: break
        stdscr.erase()
        g = launch_frame(t, Wc, Hc, None)
        top, left = (h - Hc) // 2 - 1, (w - Wc) // 2
        for y, row in enumerate(g):
            for x, cell in enumerate(row):
                if cell: _putc(stdscr, top + y, left + x, cell[0], cmap.get(cell[1], 0))
        title = "WALKMAN 1.6.1   //   SOYUZ EDITION"
        _put(stdscr, top - 1, (w - len(title)) // 2, title, S["yel"] | S["B"])
        clock, ev = _launch_caption(t)
        _put(stdscr, top + Hc, (w - len(clock)) // 2, clock, S["yel"] | S["B"])
        _put(stdscr, top + Hc + 1, (w - len(ev)) // 2, ev, S["white"] | S["B"])
        _put(stdscr, h - 2, (w - 22) // 2, "any key: skip", S["red"])
        stdscr.refresh()
        try:
            if stdscr.getch() != -1: break
        except Exception: break
