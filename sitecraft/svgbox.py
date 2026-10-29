"""量出一段 SVG 線條圖的外框（不需要瀏覽器）。

場景插畫要把各類別的物件「放在」桌面、窗台上，得先知道每個物件實際畫在哪裡。
支援 path（M L H V C S Q T A Z，大小寫）、circle、ellipse、rect、line，以及元素上的
translate / scale / rotate。曲線用取樣點估計，誤差在一兩個單位內，對排版夠用。
"""
from __future__ import annotations

import math
import re

_TAG = re.compile(r"<(path|circle|ellipse|rect|line)\b([^>]*)/?>")
_ATTR = re.compile(r"([\w-]+)\s*=\s*(['\"])(.*?)\2")
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _matrix(transform: str):
    """transform 屬性轉成 2x3 矩陣 (a b c d e f)。"""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def mul(p, q):
        a, b, c, d, e, f = p
        A, B, C, D, E, F = q
        return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)

    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", transform or ""):
        v = [float(x) for x in _NUM.findall(args)]
        if name == "translate":
            q = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            q = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            r = math.radians(v[0])
            cx, cy = (v[1], v[2]) if len(v) > 2 else (0, 0)
            cs, sn = math.cos(r), math.sin(r)
            q = (cs, sn, -sn, cs, cx - cs * cx + sn * cy, cy - sn * cx - cs * cy)
        elif name == "matrix" and len(v) == 6:
            q = tuple(v)
        else:
            continue
        m = mul(m, q)
    return m


def _arc_points(x1, y1, rx, ry, phi, large, sweep, x2, y2, n=16):
    if rx == 0 or ry == 0:
        return [(x2, y2)]
    rx, ry = abs(rx), abs(ry)
    p = math.radians(phi)
    cp, sp = math.cos(p), math.sin(p)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    out = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cp * x - sp * y + cx, sp * x + cp * y + cy))
    return out


def _path_points(d: str):
    toks = _CMD.findall(d)
    pts, i = [], 0
    x = y = sx = sy = 0.0
    lc = None  # 上一個控制點（S/T 用）
    cmd = None
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                pts.append((x, y))
                lc = None
                continue
        if cmd is None:
            break
        rel = cmd.islower()
        C = cmd.upper()
        need = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[C]
        if i + need > len(toks):
            break
        v = [float(t) for t in toks[i:i + need]]
        i += need
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == "M":
            x, y = v[0] + ox, v[1] + oy
            sx, sy = x, y
            pts.append((x, y))
            cmd = "l" if rel else "L"
            lc = None
        elif C == "L":
            x, y = v[0] + ox, v[1] + oy
            pts.append((x, y))
            lc = None
        elif C == "H":
            x = v[0] + (x if rel else 0)
            pts.append((x, y))
            lc = None
        elif C == "V":
            y = v[0] + (y if rel else 0)
            pts.append((x, y))
            lc = None
        elif C in "CS":
            if C == "C":
                c1 = (v[0] + ox, v[1] + oy)
                c2, e = (v[2] + ox, v[3] + oy), (v[4] + ox, v[5] + oy)
            else:
                c1 = (2 * x - lc[0], 2 * y - lc[1]) if lc else (x, y)
                c2, e = (v[0] + ox, v[1] + oy), (v[2] + ox, v[3] + oy)
            for k in range(1, 13):
                t = k / 12
                u = 1 - t
                pts.append((u ** 3 * x + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * e[0],
                            u ** 3 * y + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * e[1]))
            lc = c2
            x, y = e
        elif C in "QT":
            if C == "Q":
                c1, e = (v[0] + ox, v[1] + oy), (v[2] + ox, v[3] + oy)
            else:
                c1 = (2 * x - lc[0], 2 * y - lc[1]) if lc else (x, y)
                e = (v[0] + ox, v[1] + oy)
            for k in range(1, 13):
                t = k / 12
                u = 1 - t
                pts.append((u * u * x + 2 * u * t * c1[0] + t * t * e[0], u * u * y + 2 * u * t * c1[1] + t * t * e[1]))
            lc = c1
            x, y = e
        elif C == "A":
            e = (v[5] + ox, v[6] + oy)
            pts.extend(_arc_points(x, y, v[0], v[1], v[2], int(v[3]), int(v[4]), e[0], e[1]))
            x, y = e
            lc = None
    return pts


def bbox(svg: str) -> tuple[float, float, float, float]:
    """回傳 (x, y, w, h)；什麼都沒有就回整個 200x200。"""
    xs, ys = [], []
    for tag, attrs in _TAG.findall(svg):
        a = {k: v for k, _, v in _ATTR.findall(attrs)}
        f = lambda k, d=0.0: float(a.get(k, d))  # noqa: E731
        if tag == "path":
            pts = _path_points(a.get("d", ""))
        elif tag == "circle":
            cx, cy, r = f("cx"), f("cy"), f("r")
            pts = [(cx + r * math.cos(t / 8 * math.pi), cy + r * math.sin(t / 8 * math.pi)) for t in range(16)]
        elif tag == "ellipse":
            cx, cy, rx, ry = f("cx"), f("cy"), f("rx"), f("ry")
            pts = [(cx + rx * math.cos(t / 12 * math.pi), cy + ry * math.sin(t / 12 * math.pi)) for t in range(24)]
        elif tag == "rect":
            x, y, w, h = f("x"), f("y"), f("width"), f("height")
            pts = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        else:
            pts = [(f("x1"), f("y1")), (f("x2"), f("y2"))]
        m = _matrix(a.get("transform", ""))
        for px, py in pts:
            xs.append(m[0] * px + m[2] * py + m[4])
            ys.append(m[1] * px + m[3] * py + m[5])
    if not xs:
        return (0.0, 0.0, 200.0, 200.0)
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
