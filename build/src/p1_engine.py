# -*- coding: utf-8 -*-
"""
walkman_art.py  -  Walkman Build v14 / 1.6.1 art module (Soyuz edition)  (Red Star Signal Directorate)

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
