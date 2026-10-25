

# ============================================================== MODELS =====
def _octagon(x0, x1, y0, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def _tank(P):
    m = Mesh()
    L, hw, tw, th = P['L'], P['hw'], P['tw'], P['track_h']
    for s in (1, -1):                       # tracks: dark slab + lighter road wheels
        z0, z1 = (s * hw, s * (hw + tw))
        prism(m, _octagon(-L, L, 0.0, th, 0.35), min(z0, z1), max(z0, z1), 'xy', mat=0.50)
        n = P['wheels']; r = P['wr']
        for i in range(n):
            x = -L + 0.9 + (2 * L - 1.8) * (i / float(n - 1))
            lathe(m, [(-0.07, r), (0.07, r)], seg=7, axis='z', at=(x, r + 0.05, s * (hw + tw + 0.07)), mat=0.95,
                  caps=(s < 0, s > 0))
        for x in (-L + 0.35, L - 0.35):     # sprocket / idler
            lathe(m, [(-0.07, r * 0.8), (0.07, r * 0.8)], seg=7, axis='z', at=(x, th * 0.62, s * (hw + tw + 0.07)),
                  mat=1.0, caps=(s < 0, s > 0))
    prism(m, P['hull'], -hw, hw, 'xy', mat=0.85)
    ty = P['hull_top']
    if P.get('turret_box'):
        bx, by, bz = P['turret_box']
        box(m, P['tx'], ty + by, 0, bx, by, bz, mat=0.9)
    else:
        lathe(m, P['turret'], seg=10, axis='y', at=(P['tx'], ty, 0), squash=P['tsq'], mat=0.92, caps=(False, True))
    gy = ty + P['gun_h']
    lathe(m, [(P['gx0'], P['gr0']), (P['gx0'] + 0.45, P['gr0'] * 0.8), (P['gx1'], P['gr1'])], seg=7, axis='x',
          at=(0, gy, 0), mat=1.0, caps=(False, True))
    if P.get('brake'):
        lathe(m, [(P['gx1'] - 0.55, P['gr1'] * 1.9), (P['gx1'], P['gr1'] * 1.9)], seg=7, axis='x', at=(0, gy, 0), mat=1.0)
    if P.get('extractor'):
        lathe(m, [(P['gx0'] + 1.55, P['gr1'] * 1.7), (P['gx0'] + 2.2, P['gr1'] * 1.7)], seg=7, axis='x', at=(0, gy, 0), mat=1.0)
    lathe(m, [(0, 0.2), (0.14, 0.2)], seg=7, axis='y', at=(P['tx'] - 0.38, ty + P['cup_y'], 0.3), mat=1.0)   # cupola
    return m


def tank_t34():
    return _tank(dict(L=3.0, hw=1.1, tw=0.5, track_h=0.85, wheels=5, wr=0.42,
        hull=[(-3.0, 0.35), (3.0, 0.35), (3.0, 0.55), (2.25, 1.15), (-2.6, 1.15), (-3.0, 0.9)], hull_top=1.15,
        turret=[(0, 1.0), (0.14, 1.02), (0.5, 0.82), (0.66, 0.45), (0.72, 0)], tsq=(1.18, 0.95), tx=0.35,
        gx0=1.0, gx1=3.9, gr0=0.2, gr1=0.07, gun_h=0.36, cup_y=0.55))


def tank_kv1():
    return _tank(dict(L=3.2, hw=1.15, tw=0.55, track_h=0.95, wheels=6, wr=0.4,
        hull=[(-3.2, 0.3), (3.2, 0.3), (3.2, 0.8), (2.7, 1.3), (-3.0, 1.3), (-3.2, 1.0)], hull_top=1.3,
        turret_box=(0.95, 0.42, 0.85), tx=-0.15,
        gx0=0.8, gx1=3.7, gr0=0.16, gr1=0.075, gun_h=0.44, cup_y=0.82))


def tank_is2():
    return _tank(dict(L=3.3, hw=1.1, tw=0.5, track_h=0.9, wheels=6, wr=0.4, brake=True,
        hull=[(-3.3, 0.35), (3.3, 0.35), (3.3, 0.5), (1.9, 1.3), (-3.1, 1.3), (-3.3, 1.0)], hull_top=1.3,
        turret=[(0, 0.95), (0.1, 0.97), (0.38, 0.8), (0.52, 0.42), (0.56, 0)], tsq=(1.25, 1.0), tx=-0.25,
        gx0=0.8, gx1=5.0, gr0=0.22, gr1=0.095, gun_h=0.3, cup_y=0.5))


def tank_t55():
    return _tank(dict(L=3.2, hw=1.2, tw=0.5, track_h=0.85, wheels=5, wr=0.46, extractor=True,
        hull=[(-3.2, 0.4), (3.2, 0.4), (3.2, 0.62), (2.5, 1.18), (-2.8, 1.18), (-3.2, 0.9)], hull_top=1.18,
        turret=[(0, 1.05), (0.1, 1.08), (0.36, 0.9), (0.5, 0.5), (0.55, 0)], tsq=(1.12, 1.0), tx=0.0,
        gx0=1.0, gx1=4.4, gr0=0.19, gr1=0.065, gun_h=0.3, cup_y=0.48))


def tank_t72():
    return _tank(dict(L=3.4, hw=1.3, tw=0.5, track_h=0.85, wheels=6, wr=0.4, extractor=True,
        hull=[(-3.4, 0.4), (3.4, 0.4), (3.4, 0.6), (2.6, 1.12), (-3.1, 1.12), (-3.4, 0.85)], hull_top=1.12,
        turret=[(0, 1.12), (0.1, 1.14), (0.3, 0.96), (0.42, 0.5), (0.46, 0)], tsq=(1.08, 1.0), tx=-0.1,
        gx0=1.0, gx1=4.7, gr0=0.2, gr1=0.08, gun_h=0.26, cup_y=0.42))


def _booster(m, x, z, h, r, tip):
    lathe(m, [(0, r * 1.15), (0.6, r), (tip, r), (h, 0)], seg=10, axis='y', at=(x, 0, z), mat=1.0, caps=(False, False))
    lathe(m, [(-0.6, r * 0.6), (0, r * 1.0)], seg=8, axis='y', at=(x, 0, z), mat=0.6, caps=(False, False))   # nozzle skirt


def _r7_core(m, kind):
    lathe(m, [(0, 1.45), (27, 1.45)], seg=12, axis='y', mat=0.95, caps=(False, False))
    lathe(m, [(-1.2, 0.9), (0, 1.45)], seg=10, axis='y', mat=0.6, caps=(False, False))
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        _booster(m, 2.75 * math.cos(a), 2.75 * math.sin(a), 19.5, 1.28, 14.0)


def rocket_vostok():
    m = Mesh()
    _r7_core(m, 'v')
    lathe(m, [(27, 1.45), (27.2, 1.2), (33, 1.2), (36.5, 1.05), (39.5, 0.6), (41.5, 0)], seg=12, axis='y', mat=1.0, caps=(False, False))
    return m


def rocket_soyuz():
    m = Mesh()
    _r7_core(m, 's')
    lathe(m, [(27, 1.45), (27.2, 1.3), (31, 1.3), (32, 1.5), (40, 1.5), (43.5, 1.0), (46, 0.4), (47, 0)], seg=12, axis='y', mat=1.0, caps=(False, False))
    m.line((0, 47, 0), (0, 56, 0), 1.0)                                 # launch escape tower
    for k in range(3):
        a = k * 2 * math.pi / 3
        m.line((0.15 * math.cos(a), 47, 0.15 * math.sin(a)), (0.6 * math.cos(a), 51, 0.6 * math.sin(a)), 0.8)
    lathe(m, [(51, 0.55), (53.5, 0.5), (55, 0.2), (56, 0)], seg=8, axis='y', mat=1.0, caps=(False, False))
    return m


def rocket_n1():
    m = Mesh()
    prof = [(0, 9.0), (2, 8.4), (3, 8.0), (28, 5.8), (29.5, 5.4), (30, 5.4), (46, 3.9), (47, 3.7), (47.5, 3.7),
            (60, 2.7), (60.5, 2.6), (68, 2.6), (72, 1.6), (74, 0)]
    lathe(m, prof, seg=14, axis='y', mat=0.95, caps=(False, False))
    for i in range(10):                                          # first-stage engine bells
        a = 2 * math.pi * i / 10
        lathe(m, [(-2.2, 0.95), (0, 0.5)], seg=6, axis='y', at=(7.0 * math.cos(a), 0, 7.0 * math.sin(a)), mat=0.6, caps=(False, False))
    lathe(m, [(-2.0, 1.6), (0, 0.8)], seg=8, axis='y', mat=0.6, caps=(False, False))
    m.line((0, 74, 0), (0, 86, 0), 1.0)
    lathe(m, [(78, 0.9), (82, 0.7), (84, 0)], seg=8, axis='y', mat=1.0, caps=(False, False))
    return m


def rocket_buran():
    m = Mesh()
    lathe(m, [(0, 4.0), (58, 4.0)], seg=14, axis='y', mat=0.9, caps=(False, False))        # Energia core
    lathe(m, [(-2, 2.4), (0, 4.0)], seg=10, axis='y', mat=0.6, caps=(False, False))
    for sx in (1, -1):
        for sz in (1, -1):
            lathe(m, [(0, 1.95), (30, 1.95), (35, 1.5), (38, 0)], seg=10, axis='y', at=(sx * 5.3, 0, sz * 5.3), mat=1.0, caps=(False, False))
    ox = 6.6                                                                                 # orbiter on the core's side
    lathe(m, [(14, 1.7), (30, 1.9), (42, 1.7), (50, 1.1), (54, 0.4), (55, 0)], seg=10, axis='y', at=(ox, 0, 0), mat=1.0, caps=(False, False))
    for s_ in (1, -1):
        prism(m, [(0, 0), (s_ * 7.0, 0), (s_ * 0.6, 20.0)], -0.14, 0.14, 'xz', at=(ox, 14.0, 0), mat=0.8)
    return m


def sputnik():
    m = Mesh()
    sphere(m, 1.0, seg=14, rings=9, mat=1.0)
    for k, ln in enumerate((3.4, 3.4, 2.8, 2.8)):
        phi = math.pi / 4 + k * math.pi / 2
        c, s_ = math.cos(phi), math.sin(phi)
        p0 = (0.5, 0.86 * c, 0.86 * s_)
        p1 = (0.5 - ln * 0.92, (0.86 + ln * 0.38) * c, (0.86 + ln * 0.38) * s_)
        m.line(p0, p1, 1.0)
    return m


def lunokhod():
    m = Mesh()
    prism(m, [(-1.3, 0.0), (1.3, 0.0), (1.0, 1.0), (-1.0, 1.0)], -0.95, 0.95, 'xy', at=(0, 0.55, 0), mat=0.85)     # tub
    lathe(m, [(-1.3, 0.0), (-1.2, 0.55), (-0.6, 0.95), (0.6, 0.95), (1.2, 0.55), (1.3, 0.0)], seg=12, axis='x', at=(0, 1.55, 0),
          squash=(1.0, 1.55), mat=1.0, caps=(True, True))                                                              # convex lid
    for s in (1, -1):
        for x in (-1.1, -0.37, 0.37, 1.1):
            lathe(m, [(-0.16, 0.36), (0.16, 0.36)], seg=8, axis='z', at=(x, 0.36, s * 1.35), mat=0.8, caps=(s < 0, s > 0))
    m.line((0.4, 2.2, 0.3), (0.4, 3.4, 0.3), 1.0)                                    # antenna mast
    m.line((0.4, 3.4, 0.3), (0.8, 3.5, 0.9), 0.8); m.line((0.4, 3.4, 0.3), (0.0, 3.5, -0.3), 0.8)
    lathe(m, [(0, 0.14), (0.3, 0.14)], seg=6, axis='x', at=(1.45, 0.95, 0.35), mat=1.0)     # camera
    return m


def mir():
    m = Mesh()
    lathe(m, [(-3.5, 0.62), (3.5, 0.62)], seg=10, axis='x', mat=0.95)                      # core block
    sphere(m, 0.85, at=(3.8, 0, 0), seg=10, rings=6, mat=1.0)                              # docking node
    for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        ax = 'y' if dy else 'z'
        sign = dy or dz
        lathe(m, [(0.9, 0.55), (4.6, 0.55)] if sign > 0 else [(-4.6, 0.55), (-0.9, 0.55)], seg=9, axis=ax, at=(3.8, 0, 0), mat=0.9)
    lathe(m, [(0.9, 0.5), (3.6, 0.5)], seg=9, axis='x', at=(3.8, 0, 0), mat=0.9)              # docking port / Soyuz
    lathe(m, [(-3.5, 0.62), (-5.2, 0.4)], seg=9, axis='x', mat=0.8)
    for (x, z) in ((-1.0, 0), (1.5, 0)):                                                    # solar arrays on the core
        box(m, x, 0, 2.2, 0.55, 0.03, 1.8, mat=0.85)
        box(m, x, 0, -2.2, 0.55, 0.03, 1.8, mat=0.85)
    box(m, 3.8, 5.8, 0, 0.55, 1.1, 0.03, mat=0.85)
    box(m, 3.8, -5.8, 0, 0.55, 1.1, 0.03, mat=0.85)
    box(m, 3.8, 0, 5.8, 0.55, 0.03, 1.1, mat=0.85)
    box(m, 3.8, 0, -5.8, 0.55, 0.03, 1.1, mat=0.85)
    m.line((-3.5, 0.6, 0), (-3.5, 2.2, 0.5), 1.0)
    return m


def sub_typhoon():
    m = Mesh()
    L = 9.0
    hull = [(-L, 0), (-L + 0.5, 0.55), (-L + 1.5, 1.05), (-L * 0.55, 1.4), (-0.5, 1.45), (L * 0.6, 1.35), (L * 0.85, 1.0), (L * 0.95, 0.55), (L, 0)]
    for z in (1.65, -1.65):                                                      # twin pressure hulls
        lathe(m, hull, seg=12, axis='x', at=(0, 0, z), mat=0.9, caps=(False, False))
    box(m, 0.4, 1.35, 0, 7.3, 0.22, 1.6, mat=0.75)                               # missile deck between hulls
    for i in range(10):                                                          # missile hatches
        for z in (0.5, -0.5):
            box(m, -5.0 + i * 0.85, 1.6, z, 0.28, 0.04, 0.28, mat=0.45)
    prism(m, [(-1.6, 0), (1.6, 0), (1.2, 1.5), (-1.2, 1.5)], -0.8, 0.8, 'xy', at=(1.8, 1.5, 0), mat=1.0)    # sail
    for sgn in (1, -1):                                                          # tail fins
        prism(m, [(0, 0), (1.5, 0), (0.9, 1.4)], -0.1, 0.1, 'xy', at=(-L + 1.0, 0.0, sgn * 1.65), mat=0.8)
    for z in (1.65, -1.65):
        lathe(m, [(-0.5, 0.25), (0, 0.55)], seg=7, axis='x', at=(-L - 0.1, 0.0, z), mat=0.6, caps=(True, False))
    return m


def sub_b59():
    m = Mesh()
    L = 9.0
    hull = [(-L, 0), (-L + 0.6, 0.45), (-L + 2.0, 0.85), (-L * 0.4, 0.98), (L * 0.3, 0.98), (L * 0.75, 0.85), (L * 0.93, 0.5), (L, 0)]
    lathe(m, hull, seg=12, axis='x', mat=0.92, caps=(False, False))
    box(m, 0.2, 0.98, 0, 7.4, 0.12, 0.45, mat=0.7)                          # casing deck
    prism(m, [(-1.0, 0), (1.0, 0), (0.7, 1.7), (-0.5, 1.7)], -0.28, 0.28, 'xy', at=(1.0, 1.0, 0), mat=1.0)   # sail
    m.line((0.5, 2.7, 0.0), (0.5, 3.9, 0.0), 1.0)                          # periscope
    m.line((0.1, 2.7, 0.0), (0.1, 3.6, 0.0), 1.0)
    prism(m, [(0, 0), (1.3, 0), (0.6, 1.1)], -0.1, 0.1, 'xy', at=(-L + 0.9, 0.7, 0), mat=0.8)   # rudder
    box(m, -L + 1.2, 0.0, 0, 0.9, 0.05, 1.6, mat=0.8)                      # stern planes
    box(m, L * 0.62, 0.35, 0, 0.5, 0.05, 1.2, mat=0.8)                      # bow planes
    for z in (0.0, 0.6, -0.6):
        lathe(m, [(-0.4, 0.15), (0, 0.4)], seg=6, axis='x', at=(-L - 0.1, 0.0, z), mat=0.6, caps=(True, False))
    return m


def mig21():
    m = Mesh()
    lathe(m, [(-7, 0.25), (-6, 0.55), (-3, 0.75), (1.5, 0.8), (4.5, 0.72), (6.5, 0.45), (8.2, 0.25), (9.2, 0)], seg=10, axis='x',
          mat=0.95, caps=(True, False))
    lathe(m, [(6.5, 0.55), (7.2, 0.5)], seg=10, axis='x', mat=0.5, caps=(False, False))     # intake lip
    for s in (1, -1):                                                                       # delta wings (plan view)
        pts = [(0.0, 0.0), (-3.6, 0.0), (-3.0, 3.8), (-1.3, 3.8)]
        prism(m, [(a, s * b) for a, b in pts], -0.07, 0.07, 'xz', at=(1.9, 0.0, 0), mat=0.85)
    prism(m, [(0, 0), (-2.6, 0), (-1.6, 2.2), (-0.7, 2.2)], -0.06, 0.06, 'xy', at=(-3.4, 0.55, 0), mat=0.9)   # fin
    return m


def red_star():
    m = Mesh()
    star3d(m, 1.0, 0.42, 0.34)
    return m


def bear_ushanka():
    m = Mesh()
    sphere(m, 1.0, at=(0, 1.25, 0), seg=14, rings=9, squash=(1.1, 1.0), ystretch=1.6, axis='x', mat=0.85)      # body
    sphere(m, 0.72, at=(1.95, 1.85, 0), seg=14, rings=9, mat=0.9)                                              # head
    sphere(m, 0.34, at=(2.55, 1.68, 0), seg=10, rings=7, ystretch=1.25, squash=(0.9, 0.9), axis='x', mat=1.0)  # snout
    sphere(m, 0.1, at=(2.9, 1.74, 0), seg=6, rings=4, mat=0.3)                                                  # nose
    for z in (0.5, -0.5):
        sphere(m, 0.2, at=(1.75, 2.5, z), seg=8, rings=6, mat=0.85)                                             # ears
        sphere(m, 0.1, at=(2.52, 1.95, z * 0.5), seg=6, rings=4, mat=0.35)                                      # eyes
    for x in (1.0, -1.0):
        for z in (0.6, -0.6):
            lathe(m, [(0, 0.33), (1.2, 0.33), (1.3, 0.0)], seg=8, axis='y', at=(x, 0.0, z), mat=0.8, caps=(True, False))
    sphere(m, 0.25, at=(-1.75, 1.45, 0), seg=8, rings=6, mat=0.85)                                             # tail
    # the ushanka: fur crown, turned-up brim, tied-down ear flaps, red-star badge
    lathe(m, [(2.35, 0.7), (2.7, 0.66), (2.95, 0.5), (3.05, 0.0)], seg=14, axis='y', at=(1.9, 0, 0), squash=(1.05, 1.0), mat=1.15, caps=(True, False))
    lathe(m, [(2.28, 0.76), (2.5, 0.76)], seg=14, axis='y', at=(1.9, 0, 0), squash=(1.05, 1.0), mat=0.7)
    for z in (0.8, -0.8):
        box(m, 1.9, 1.95, z, 0.3, 0.42, 0.07, mat=1.1)
    star3d(m, 0.2, 0.085, 0.07, mat=1.35, at=(2.68, 2.62, 0), plane='yz')
    return m


def ak47():
    m = Mesh()
    box(m, 0.0, 0.0, 0.0, 1.15, 0.27, 0.17, mat=0.9)                                    # receiver
    lathe(m, [(1.1, 0.075), (3.6, 0.075)], seg=7, axis='x', at=(0, 0.14, 0), mat=1.0)  # barrel
    lathe(m, [(1.1, 0.07), (2.7, 0.07)], seg=7, axis='x', at=(0, 0.42, 0), mat=0.95)   # gas tube
    box(m, 1.95, 0.14, 0.0, 0.85, 0.2, 0.16, mat=0.8)                                  # handguard
    box(m, 3.35, 0.3, 0.0, 0.06, 0.18, 0.04, mat=1.0)                                  # front sight
    prism(m, [(-1.15, 0.27), (-3.2, 0.1), (-3.2, -0.5), (-1.15, -0.2)], -0.13, 0.13, 'xy', mat=0.75)   # stock
    prism(m, [(-0.55, -0.27), (-0.25, -0.27), (-0.5, -1.15), (-0.85, -1.15)], -0.12, 0.12, 'xy', mat=0.8)  # pistol grip
    for i, (x, y) in enumerate(((0.45, -0.55), (0.6, -1.0), (0.82, -1.45), (1.1, -1.85))):               # curved magazine
        box(m, x, y, 0.0, 0.26, 0.26, 0.13, mat=0.9)
    return m


def rpg7():
    m = Mesh()
    lathe(m, [(-2.9, 0.34), (-2.3, 0.2), (-1.8, 0.14), (2.0, 0.14)], seg=9, axis='x', mat=0.9, caps=(False, True))   # tube with flared rear
    lathe(m, [(2.0, 0.1), (2.5, 0.26), (3.1, 0.33), (3.7, 0.22), (4.1, 0.0)], seg=10, axis='x', mat=1.05, caps=(True, False))  # warhead
    for k in range(4):
        a = k * math.pi / 2
        m.line((1.6, 0.14 * math.cos(a), 0.14 * math.sin(a)), (1.0, 0.5 * math.cos(a), 0.5 * math.sin(a)), 0.8)
    prism(m, [(0.0, 0.0), (0.3, 0.0), (0.1, -0.9), (-0.2, -0.9)], -0.1, 0.1, 'xy', at=(-0.4, -0.12, 0), mat=0.8)   # pistol grip
    prism(m, [(0.0, 0.0), (0.3, 0.0), (0.25, -0.7), (-0.05, -0.7)], -0.1, 0.1, 'xy', at=(0.9, -0.12, 0), mat=0.8)  # foregrip
    box(m, 0.2, 0.32, 0.0, 0.3, 0.12, 0.07, mat=1.0)                                   # optical sight
    box(m, -0.9, 0.2, 0.0, 0.12, 0.08, 0.05, mat=1.0)                                  # rear sight
    return m


def soyuz_craft():
    m = Mesh()
    lathe(m, [(-4.6, 1.36), (-2.3, 1.36)], seg=12, axis='x', mat=0.9, caps=(True, False))                  # instrument / service module
    lathe(m, [(-5.5, 0.45), (-4.6, 0.8)], seg=9, axis='x', mat=0.6, caps=(False, False))                   # main engine bell
    lathe(m, [(-2.3, 1.05), (-1.9, 1.1), (-0.9, 0.95), (0.0, 0.6), (0.4, 0.38)], seg=12, axis='x', mat=1.0, caps=(False, True))   # descent module
    lathe(m, [(0.4, 0.3), (0.9, 0.3)], seg=8, axis='x', mat=0.7, caps=(False, False))                      # hatch tunnel
    sphere(m, 1.12, at=(1.95, 0, 0), seg=14, rings=9, mat=1.0)                                              # orbital module
    m.line((3.05, 0, 0), (4.1, 0, 0), 1.0)                                                                  # docking probe
    for s in (1, -1):                                                                                       # two solar wings
        box(m, -3.4, 0, s * 3.3, 0.85, 0.03, 1.7, mat=0.85)
        m.line((-3.4, 0, s * 1.36), (-3.4, 0, s * 1.6), 0.8)
    m.line((1.0, 1.0, 0), (1.2, 2.0, 0.4), 0.8)                                                             # antenna
    return m


# key, display name, spec lines, tilt, spin speed, builder
MODEL_DEFS = [
    ("t34", "T-34", ["USSR 1940  //  76.2 mm gun, later 85 mm  //  sloped armour, wide tracks", "among the most produced tanks of WWII (80,000+ T-34s of all types)"], 0.42, 1.0, tank_t34),
    ("kv1", "KV-1", ["USSR 1939  //  76.2 mm gun  //  about 45 tonnes", "the heavy tank that shrugged off most German tank guns in 1941"], 0.42, 1.0, tank_kv1),
    ("is2", "IS-2", ["USSR 1943  //  122 mm D-25T gun with muzzle brake", "heavy tank built to crack fortified positions - about 3,400 made"], 0.40, 1.0, tank_is2),
    ("t55", "T-55", ["USSR 1958  //  100 mm D-10T gun  //  low dome turret", "with the T-54, over 100,000 built - one of the most produced tanks ever"], 0.42, 1.0, tank_t55),
    ("t72", "T-72", ["USSR 1973  //  125 mm smoothbore  //  autoloader", "20,000+ built; the long gun, low dome and six road wheels"], 0.42, 1.0, tank_t72),
    ("vostok", "VOSTOK 8K72K", ["R-7 family  //  four tapered strap-on boosters round a core", "the rocket that lifted the first human into orbit, 12 April 1961"], 0.12, 1.2, rocket_vostok),
    ("soyuz", "SOYUZ", ["R-7 lineage  //  flying since 1957  //  with launch-escape tower", "the most-launched rocket family in history"], 0.12, 1.2, rocket_soyuz),
    ("soyuzcraft", "SOYUZ SPACECRAFT", ["orbital, descent and service modules  //  two solar wings  //  first crewed flight 23 April 1967", "docked with an Apollo in orbit, 17 July 1975 - press [U] for the launch"], 0.35, 1.0, soyuz_craft),
    ("n1", "N1", ["USSR 1969-72  //  30 NK-15 engines in the first stage", "four launches, none reached orbit - the Soviet Moon rocket"], 0.14, 1.2, rocket_n1),
    ("buran", "ENERGIA / BURAN", ["Buran flew once, uncrewed: 15 Nov 1988, two orbits, automatic landing", "Energia core with four strap-ons and the orbiter on its side"], 0.16, 1.1, rocket_buran),
    ("sputnik", "SPUTNIK-1", ["4 Oct 1957  //  58 cm sphere  //  83.6 kg", "beeped on 20.005 and 40.002 MHz for about three weeks - the whole world could hear it"], 0.30, 1.3, sputnik),
    ("lunokhod", "LUNOKHOD-1", ["landed 17 Nov 1970 in Mare Imbrium  //  eight wheels", "the first remote-controlled rover on another world"], 0.45, 1.0, lunokhod),
    ("mir", "MIR", ["1986-2001  //  fifteen years in orbit", "the first modular space station - brought down over the Pacific, March 2001"], 0.35, 0.8, mir),
    ("typhoon", "TYPHOON  /  'RED OCTOBER'", ["Project 941 Akula  //  largest submarines ever built  //  20 missiles", "'Red October' itself is fiction - a boat of this class in Clancy's novel"], 0.30, 0.9, sub_typhoon),
    ("b59", "B-59  (FOXTROT)", ["Project 641  //  Caribbean, 27 October 1962  //  one nuclear torpedo", "press [O] for the night it stayed in the water"], 0.28, 1.0, sub_b59),
    ("mig21", "MIG-21", ["USSR 1959  //  delta wing, Mach 2  //  10,000+ built", "the fighter half the world flew"], 0.40, 1.0, mig21),
    ("star", "RED STAR", ["five points, one beveled star", "spinning forever, as requested"], 0.0, 1.4, red_star),
    ("bear", "BEAR IN USHANKA", ["ear flaps down, red star up", "winter is a state of mind and it has a hat"], 0.28, 0.9, bear_ushanka),
    ("ak47", "AK-47", ["USSR 1949  //  simple, rugged, forgiving of mud and neglect", "among the most produced firearms ever made"], 0.35, 1.0, ak47),
    ("rpg7", "RPG-7", ["USSR 1961  //  reusable shoulder-fired launcher", "one of the most widely used infantry weapons in the world"], 0.35, 1.0, rpg7),
]


# per-model stylisation: (screen roll, x/z fattening) - rockets are drawn chunky and leaning so they read at 80 columns
STYLE = {
    "vostok": (0.50, (1.9, 1.0, 1.9)), "soyuz": (0.50, (1.9, 1.0, 1.9)), "n1": (0.48, (1.5, 1.0, 1.5)),
    "buran": (0.50, (1.5, 1.0, 1.5)), "mir": (0.0, (1.0, 1.0, 1.0)),
}
_MODEL_CACHE = {}


def get_model(i):
    """Build (lazily) and cache model i -> (name, specs, tilt, speed, mesh, roll)."""
    i %= len(MODEL_DEFS)
    if i not in _MODEL_CACHE:
        key, name, specs, tilt, speed, builder = MODEL_DEFS[i]
        roll, fat = STYLE.get(key, (0.0, (1.0, 1.0, 1.0)))
        mesh = builder().normalize(fat)
        _MODEL_CACHE[i] = (name, specs, tilt, speed, mesh, roll)
    return _MODEL_CACHE[i]
