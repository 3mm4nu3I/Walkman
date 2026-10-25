# -*- coding: utf-8 -*-
"""
walkman_art.py  -  Walkman Build v14 / 1.6 art module  (Red Star Signal Directorate)

Everything here is optional: walkman.py imports this inside try/except, so if this
file is missing or broken the player simply behaves like 1.5.

  * a tiny software 3D engine (z-buffered, flat-shaded, rendered as ASCII)
  * 3D hall of machines: tanks, rockets, Sputnik, Lunokhod, Mir, submarines, MiG, star
  * full pages: DUGA (the Woodpecker), B-59 (27 Oct 1962), Red Choir, Fyodor
  * ambient 3D + rare "Fyodor" apparitions on the main screen
Real people are never drawn; the art is machines, symbols and invented figures.
"""
import math, time, random, datetime, os

try:
    import curses
except Exception:           # pragma: no cover
    curses = None

# ============================================================ 3D ENGINE ====
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Mesh:
    """Triangles with a brightness multiplier ('mat') plus optional 3D line segments."""
    def __init__(self):
        self.v, self.f, self.m, self.lines = [], [], [], []

    def add(self, verts, faces, mat=1.0, center=None):
        n = len(verts)
        if center is None:
            center = (sum(p[0] for p in verts) / n, sum(p[1] for p in verts) / n, sum(p[2] for p in verts) / n)
        base = len(self.v)
        self.v.extend(verts)
        for a, b, c in faces:
            A, B, C = verts[a], verts[b], verts[c]
            nrm = _cross(_sub(B, A), _sub(C, A))
            fc = ((A[0] + B[0] + C[0]) / 3 - center[0], (A[1] + B[1] + C[1]) / 3 - center[1], (A[2] + B[2] + C[2]) / 3 - center[2])
            if _dot(nrm, fc) < 0: b, c = c, b          # make every face point outward
            self.f.append((base + a, base + b, base + c))
            self.m.append(mat)

    def line(self, p0, p1, mat=1.0):
        self.lines.append((p0, p1, mat))

    def normalize(self, fat=(1.0, 1.0, 1.0)):
        if fat != (1.0, 1.0, 1.0):
            fx, fy, fz = fat
            self.v = [(p[0] * fx, p[1] * fy, p[2] * fz) for p in self.v]
            self.lines = [((a[0] * fx, a[1] * fy, a[2] * fz), (b[0] * fx, b[1] * fy, b[2] * fz), mt) for a, b, mt in self.lines]
        pts = list(self.v)
        for p0, p1, _ in self.lines: pts.append(p0); pts.append(p1)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        r = max(math.sqrt((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) for p in pts) or 1.0
        self.v = [((p[0] - c[0]) / r, (p[1] - c[1]) / r, (p[2] - c[2]) / r) for p in self.v]
        self.lines = [(((a[0] - c[0]) / r, (a[1] - c[1]) / r, (a[2] - c[2]) / r),
                       ((b[0] - c[0]) / r, (b[1] - c[1]) / r, (b[2] - c[2]) / r), mt) for a, b, mt in self.lines]
        allp = list(self.v)
        for a, b, _ in self.lines: allp.append(a); allp.append(b)
        self.rxz = max(math.sqrt(p[0] ** 2 + p[2] ** 2) for p in allp) or 1.0     # spin radius
        self.ymax = max(abs(p[1]) for p in allp) or 1.0
        return self


def _map(axis, t, u, w, at):
    if axis == 'y': p = (u, t, w)
    elif axis == 'x': p = (t, u, w)
    else: p = (u, w, t)
    return (p[0] + at[0], p[1] + at[1], p[2] + at[2])


def lathe(m, prof, seg=10, axis='y', at=(0, 0, 0), squash=(1.0, 1.0), mat=1.0, caps=(True, True)):
    """Solid of revolution. prof = [(t, radius), ...] along the axis."""
    verts, rings = [], []
    for t, r in prof:
        if r < 1e-6:
            verts.append(_map(axis, t, 0, 0, at)); rings.append([len(verts) - 1] * seg)
        else:
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                verts.append(_map(axis, t, r * math.cos(a) * squash[0], r * math.sin(a) * squash[1], at))
                ring.append(len(verts) - 1)
            rings.append(ring)
    faces = []
    for i in range(len(rings) - 1):
        for k in range(seg):
            a0, a1 = rings[i][k], rings[i][(k + 1) % seg]
            b0, b1 = rings[i + 1][k], rings[i + 1][(k + 1) % seg]
            if a0 != a1: faces.append((a0, a1, b1))
            if b0 != b1: faces.append((a0, b1, b0))
    for which, ring_i in ((0, 0), (1, len(rings) - 1)):
        if caps[which] and prof[ring_i][1] > 1e-6:
            verts.append(_map(axis, prof[ring_i][0], 0, 0, at)); ci = len(verts) - 1
            for k in range(seg): faces.append((ci, rings[ring_i][k], rings[ring_i][(k + 1) % seg]))
    m.add(verts, faces, mat)


def sphere(m, r, at=(0, 0, 0), seg=12, rings=8, squash=(1.0, 1.0), ystretch=1.0, mat=1.0, axis='y'):
    prof = []
    for i in range(rings + 1):
        th = math.pi * i / rings
        prof.append((r * ystretch * math.cos(th), r * math.sin(th)))
    lathe(m, prof, seg=seg, axis=axis, at=at, squash=squash, mat=mat, caps=(False, False))


def prism(m, poly, c0, c1, plane='xy', at=(0, 0, 0), mat=1.0):
    """Extrude a CONVEX polygon. plane xy -> extrude along z, xz -> along y, yz -> along x."""
    def P(a, b, c):
        if plane == 'xy': q = (a, b, c)
        elif plane == 'xz': q = (a, c, b)
        else: q = (c, a, b)
        return (q[0] + at[0], q[1] + at[1], q[2] + at[2])
    n = len(poly)
    verts = [P(a, b, c0) for a, b in poly] + [P(a, b, c1) for a, b in poly]
    faces = []
    for i in range(1, n - 1):
        faces.append((0, i, i + 1)); faces.append((n, n + i, n + i + 1))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j)); faces.append((i, n + j, n + i))
    m.add(verts, faces, mat)


def box(m, cx, cy, cz, hx, hy, hz, mat=1.0):
    prism(m, [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)], cz - hz, cz + hz, 'xy', mat=mat)


def star3d(m, R=1.0, r=0.42, depth=0.38, mat=1.0, at=(0, 0, 0), plane='xy'):
    """Beveled five-pointed star (front and back are shallow pyramids). plane 'yz' faces +x."""
    def P(a, b, c):
        q = (a, b, c) if plane == 'xy' else (c, a, b)
        return (q[0] + at[0], q[1] + at[1], q[2] + at[2])
    rim = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = R if i % 2 == 0 else r
        rim.append(P(rr * math.cos(a), -rr * math.sin(a), 0.0))
    verts = rim + [P(0, 0, depth), P(0, 0, -depth)]
    faces = []
    for i in range(10):
        j = (i + 1) % 10
        faces.append((10, i, j)); faces.append((11, j, i))
    m.add(verts, faces, mat, center=at)


# --------------------------------------------------------------- render ----
RAMP = ".:-=+*#%@"
LIGHT = (-0.42, 0.62, 0.66)
_ln = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _ln for c in LIGHT)


_FIT = {}


def _fit(mesh, ax, roll, W, H):
    key = (id(mesh), round(ax, 3), round(roll, 3), W, H)
    if key in _FIT: return _FIT[key]
    cb, sb, cr, sr = math.cos(ax), math.sin(ax), math.cos(roll), math.sin(roll)
    pts = list(mesh.v)
    for a, b, _ in mesh.lines: pts.append(a); pts.append(b)
    mx = my = 1e-9
    for k in range(16):
        ay = k * math.pi / 8
        ca, sa = math.cos(ay), math.sin(ay)
        for x, y, z in pts:
            x1 = x * ca + z * sa; z1 = -x * sa + z * ca
            y2 = y * cb - z1 * sb
            xr = abs(x1 * cr - y2 * sr); yr = abs(x1 * sr + y2 * cr)
            if xr > mx: mx = xr
            if yr > my: my = yr
    sc = 0.97 * min(W / (4.0 * mx), H / (2.0 * my))
    _FIT[key] = sc
    return sc


def render3d(mesh, ay, ax, W, H, roll=0.0, ambient=0.16):
    """Return rows of (char, level) cells (None = empty). level 0..2 = dark..bright."""
    ca, sa, cb, sb = math.cos(ay), math.sin(ay), math.cos(ax), math.sin(ax)
    cr, sr = math.cos(roll), math.sin(roll)

    def rot(p):
        x, y, z = p
        x1 = x * ca + z * sa; z1 = -x * sa + z * ca
        y2 = y * cb - z1 * sb; z2 = y * sb + z1 * cb
        return (x1 * cr - y2 * sr, x1 * sr + y2 * cr, z2)

    pts = [rot(p) for p in mesh.v]
    scale = _fit(mesh, ax, roll, W, H)
    cx, cy = W / 2.0, H / 2.0
    sx = [cx + p[0] * scale * 2.0 for p in pts]
    sy = [cy - p[1] * scale for p in pts]
    zbuf = [[-1e9] * W for _ in range(H)]
    out = [[None] * W for _ in range(H)]
    Lx, Ly, Lz = LIGHT
    nramp = len(RAMP)
    for fi, (a, b, c) in enumerate(mesh.f):
        A, B, C = pts[a], pts[b], pts[c]
        ux, uy, uz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
        vx, vy, vz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
        nx = uy * vz - uz * vy; ny = uz * vx - ux * vz; nz = ux * vy - uy * vx
        if nz <= 0: continue
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        if ln < 1e-12: continue
        lam = (nx * Lx + ny * Ly + nz * Lz) / ln
        shade = ambient + (1 - ambient) * (lam if lam > 0 else 0.0)
        shade *= mesh.m[fi]
        if shade > 1: shade = 1.0
        x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b], sy[b], sx[c], sy[c]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9: continue
        xmin = max(0, int(min(x0, x1, x2))); xmax = min(W - 1, int(max(x0, x1, x2)))
        ymin = max(0, int(min(y0, y1, y2))); ymax = min(H - 1, int(max(y0, y1, y2)))
        if xmin > xmax or ymin > ymax: continue
        ch = RAMP[min(nramp - 1, int(shade * (nramp - 0.01)))]
        lvl = 0 if shade < 0.38 else (1 if shade < 0.66 else 2)
        za, zb, zc = A[2], B[2], C[2]
        d1, d2, d3, d4 = (y1 - y2), (x2 - x1), (y2 - y0), (x0 - x2)
        for py in range(ymin, ymax + 1):
            fy = py + 0.5 - y2
            row, zrow = out[py], zbuf[py]
            for px in range(xmin, xmax + 1):
                fx = px + 0.5 - x2
                l0 = (d1 * fx + d2 * fy) / den
                if l0 < -0.02: continue
                l1 = (d3 * fx + d4 * fy) / den
                if l1 < -0.02: continue
                l2 = 1.0 - l0 - l1
                if l2 < -0.02: continue
                z = l0 * za + l1 * zb + l2 * zc
                if z > zrow[px]:
                    zrow[px] = z; row[px] = (ch, lvl)
    # 3D line segments (antennas, tower rods) with a depth test
    for p0, p1, mt in mesh.lines:
        a, b = rot(p0), rot(p1)
        xa, ya = cx + a[0] * scale * 2.0, cy - a[1] * scale
        xb, yb = cx + b[0] * scale * 2.0, cy - b[1] * scale
        steps = int(max(abs(xb - xa), abs(yb - ya))) + 1
        for s in range(steps + 1):
            t = s / float(steps)
            px, py = int(xa + (xb - xa) * t), int(ya + (yb - ya) * t)
            if 0 <= px < W and 0 <= py < H:
                z = a[2] + (b[2] - a[2]) * t + 0.03
                if z > zbuf[py][px]:
                    zbuf[py][px] = z
                    dx, dy = abs(xb - xa) / 2.0, abs(yb - ya)
                    ch = '|' if dy > 2 * dx else ('-' if dx > 2 * dy else ('/' if (xb - xa) * (yb - ya) < 0 else '\\'))
                    out[py][px] = (ch, 2 if mt >= 1 else 1)
    return out


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


# key, display name, spec lines, tilt, spin speed, builder
MODEL_DEFS = [
    ("t34", "T-34", ["USSR 1940  //  76.2 mm gun, later 85 mm  //  sloped armour, wide tracks", "among the most produced tanks of WWII (80,000+ T-34s of all types)"], 0.42, 1.0, tank_t34),
    ("kv1", "KV-1", ["USSR 1939  //  76.2 mm gun  //  about 45 tonnes", "the heavy tank that shrugged off most German tank guns in 1941"], 0.42, 1.0, tank_kv1),
    ("is2", "IS-2", ["USSR 1943  //  122 mm D-25T gun with muzzle brake", "heavy tank built to crack fortified positions - about 3,400 made"], 0.40, 1.0, tank_is2),
    ("t55", "T-55", ["USSR 1958  //  100 mm D-10T gun  //  low dome turret", "with the T-54, over 100,000 built - one of the most produced tanks ever"], 0.42, 1.0, tank_t55),
    ("t72", "T-72", ["USSR 1973  //  125 mm smoothbore  //  autoloader", "20,000+ built; the long gun, low dome and six road wheels"], 0.42, 1.0, tank_t72),
    ("vostok", "VOSTOK 8K72K", ["R-7 family  //  four tapered strap-on boosters round a core", "the rocket that lifted the first human into orbit, 12 April 1961"], 0.12, 1.2, rocket_vostok),
    ("soyuz", "SOYUZ", ["R-7 lineage  //  flying since 1957  //  with launch-escape tower", "the most-launched rocket family in history"], 0.12, 1.2, rocket_soyuz),
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


# ============================================================ 2D ART DATA ===
# ---- Duga: the Woodpecker array (built procedurally, 74 x 14) --------------
def _build_duga():
    W, H = 74, 14
    g = [[' '] * W for _ in range(H)]
    rnd = random.Random(1976)
    for _ in range(30):                                   # night sky
        g[rnd.randrange(0, 5)][rnd.randrange(W)] = rnd.choice(".*+'`")
    x0, x1 = 11, 62
    n = x1 - x0 + 1
    def rail(y):
        for i in range(n): g[y][x0 + i] = '#' if i in (0, n - 1) else '='
    def bars(y, ch):
        for i in range(n): g[y][x0 + i] = '|' if i % 2 == 0 else ch
    def rungs(y):
        for i in range(n): g[y][x0 + i] = '+' if i % 2 == 0 else '-'
    rail(1)
    for tier_top in (2, 6, 10):
        bars(tier_top, 'X'); rungs(tier_top + 1); bars(tier_top + 2, 'X')
        if tier_top < 10: rail(tier_top + 3)
    for cx in (5, W - 6):                                 # lattice pylons
        for y in range(0, 12):
            hw = 1 + y // 4
            g[y][cx - hw] = '/'; g[y][cx + hw] = '\\'
            for k in range(-hw + 1, hw):
                g[y][cx + k] = 'x' if (k + y) % 2 == 0 else ' '
    for x in range(W):                                    # the Zone: pines and grass
        g[12][x] = rnd.choice('^^^A^ ') if g[12][x] == ' ' else g[12][x]
        g[13][x] = rnd.choice('"\'",.') if g[13][x] == ' ' else g[13][x]
    return [''.join(r) for r in g]

DUGA_ART = _build_duga()

DUGA_FACTS = [
    'DUGA ("arc")  -  Soviet over-the-horizon radar, NATO name STEEL YARD',
    "Receivers at Chernobyl-2, transmitters at Liubech-1, both in Ukraine",
    "Antenna array about 700 m long and 150 m high",
    "On air July 1976 - December 1989; pulses at 10 Hz (16 and 20 Hz rarely)",
    "Signals of 7-19 MHz bounced off the ionosphere to watch for missile launches",
    "Radio hams named it THE RUSSIAN WOODPECKER; thousands of complaints followed",
    "Today the array still stands inside the Chernobyl Exclusion Zone",
]
DUGA_DEDICATION = "DUGA :: the owner's 2nd love, 3rd wife and 5th cousin (his words, not ours)"

# ---- Red Choir dancers (7 rows x 11 cols) ---------------------------------
DANCER = {
    "stand": ["   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  / |=| \\  ", "    | |    ", "    | |    ", "   _| |_   "],
    "squat": ["           ", "           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  <(   )>  ", "  _/___\\_  "],
    "kickR": ["           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  <(   )___", "  _/__\\_   ", "           "],
    "kickL": ["           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "___(   )>  ", "   _/__\\_  ", "           "],
    "arms":  ["   _/^\\_   ", "\\  ( o_o ) /", " \\ /|=|\\ / ", "   |=|     ", "   | |     ", "   | |     ", "  _| |_    "],
}
DANCE_SEQ = ["squat", "kickR", "squat", "kickL", "squat", "kickR", "squat", "kickL", "arms", "squat"]
DOMBRA_PLAYER = ["    _/^\\_      ", "   ( o_o )     ", "   /|===|\\-------o", "   >(___)<     ", "   _/___\\_     "]
YURT = ["        /\\        ", "       /__\\       ", "     .'    '.     ", "    /  .--.  \\    ", "   /___|    |___\\   ", "       |____|       "]

# ---- B-59 / the three keys --------------------------------------------------
KEY_BOX = [
    ("CAPTAIN", "V. SAVITSKY", "YES"),
    ("POLITICAL OFFICER", "I. MASLENNIKOV", "YES"),
    ("FLOTILLA STAFF CHIEF", "V. ARKHIPOV", "NO"),
]
B59_STORY = [
    "27 Oct 1962, off Cuba. Soviet submarine B-59 (Project 641, NATO 'Foxtrot')",
    "is hunted by eleven US destroyers and the carrier USS Randolph. They drop",
    "practice depth charges to force her up. Batteries low, air conditioning",
    "dead, cut off from Moscow - they could not know if war had begun.",
    "Captain Savitsky wants to fire the nuclear torpedo. Launch needed the",
    "captain and the political officer; aboard B-59 the flotilla chief of staff,",
    "Vasili Arkhipov, was a third voice. Two said yes. Arkhipov said no.",
    "B-59 surfaced among the American ships and was sent home.",
]

# ---- Fyodor: original line art + original aphorisms (NOT quotations) --------
# Art rows <= 9, width <= 40 so a piece fits the main-screen apparition box.
FYODOR = [
    ("THE CANDLE",
     ["          )           ",
      "         ( )     ~o~  ",
      "         .|.          ",
      "        / | \\         ",
      "        | # |         ",
      "        | # |  ,      ",
      "       .| # |. |      ",
      "     __|_###_|_|__    ",
      "    (______________)  "],
     "A conscience is a candle: it burns best when you stop shielding it."),
    ("THE BOOKSHELF CAT",
     ["        /\\_/\\    z     ",
      "       ( -.- )  z      ",
      "        > ^ <          ",
      " .----------------------.",
      " | THE BROTHERS KARAMAZOV |",
      " '------------------------'",
      "   | CRIME AND PUNISHMENT |",
      "  .------------------------.",
      "  | NOTES FROM UNDERGROUND |"],
     "The cat has read all of it and declines to comment."),
    ("730 STEPS",
     ["                    ______",
      "                   |  ||  |",
      "              _____|  ||  |",
      "          ____|    |__||__|",
      "      ____|   7 3 0         ",
      "  ____|    steps, counted   ",
      "_|                          "],
     "Count the steps before the theory climbs them."),
    ("THE WHEEL",
     ["        .-'''''-.        ",
      "      .' 0  32  15 '.    ",
      "     / 19  .-----.  4 \\   ",
      "    | 21  ( . o . ) 2  |  ",
      "     \\ 25  '-----' 17 /   ",
      "      '. 34   6   27 .'    ",
      "        '-.......-'        "],
     "Red or black - the wheel keeps no opinion of you."),
    ("THE SPIRE",
     ["           +           ",
      "           |           ",
      "          /|\\          ",
      "          /_\\          ",
      "         /   \\         ",
      "        /_____\\        ",
      "   _____|  +  |_____   ",
      "  |_|_|_|_____|_|_|_|  ",
      "   ~  snow on the Neva ~ "],
     "A city built on a swamp by decree, dreaming in fever."),
    ("UNDERGROUND",
     ["  hats  hats  hats  hats  ",
      "=============  ===========",
      "            ||            ",
      "      ______||______      ",
      "     |  .---.  rent |     ",
      "     | ( o_o )  due |     ",
      "     |  /|=|\\  tea  |     ",
      "     |___\\_/_______|     "],
     "Even the underground man pays rent."),
    ("THREE BROTHERS",
     ["     )                    ",
      "    (_)         )         ",
      "     |         (_)        ",
      "     |#|        |#|    )  ",
      "     |#|        |#|   (_) ",
      "     |#|        |#|   |#| ",
      "   DMITRI       IVAN ALYOSHA"],
     "Three brothers, one father, zero agreement."),
    ("THE SAMOVAR",
     ["         ___         ",
      "        (___)        ",
      "      ._|_|_|_.      ",
      "     /  ~~~~~  \\     ",
      "  [] |  ~~~~~  | []  ",
      "     |_________|     ",
      "    /___________\\    ",
      "   [A][K][Q][J][10]  "],
     "Tea first. The metaphysics can wait until it cools."),
    ("THE LIT WINDOW",
     [" .------------------. ",
      " | .----.   .----. | ",
      " | |  o |   |    | | ",
      " | | /|\\ |   |    | | ",
      " | |_/_\\_|   |____| | ",
      " '------------------' ",
      "   *  .   *    .  *   "],
     "Kindness will always be diagnosed by the people it embarrasses."),
    ("THE DEBT",
     ["  .---------------------------.",
      " /     I.O.U.  500 RUBLES      \\",
      "|    payable: by the deadline   |",
      "|          signed:  F.M.        |",
      " \\_____________________________/",
      "                    /           ",
      "                   /   pen      "],
     "Deadline: the mother of masterpieces."),
]
FYODOR_TAG = "- after F.M.D., in his manner (not a quotation)"


# ================================================================ PAGES =====
PAGE_KEYS = {"h": "hall", "w": "duga", "k": "choir", "o": "b59", "f": "fyodor"}
MENU_LINE = "[H] 3D HALL  [W] DUGA  [K] RED CHOIR  [O] B-59  [F] FYODOR  [Z] 3D ON/OFF"
AMBIENT_KEYS = ("t34", "bear", "is2", "typhoon", "ak47", "sputnik", "t72", "b59", "star", "rpg7", "mir", "lunokhod", "bear", "mig21", "kv1", "t55")


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
_DRAW = {"hall": draw_hall, "duga": draw_duga, "b59": draw_b59, "choir": draw_choir, "fyodor": draw_fyodor}


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
    return {"models": n, "ms_per_frame": round(ms, 1), "build_s": round(t1 - t0, 2)}
