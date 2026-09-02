"""Generate apple-touch-icon.png (180x180) matching favicon.svg.

Pure standard-library PNG encoder — no external dependencies.
Run at Docker build time:  python3 generate_icon.py
Writes to static/apple-touch-icon.png.
"""
from __future__ import annotations

import struct
import zlib

W = H = 180

BG = (10, 10, 10, 255)           # #0a0a0a  (background)
SKULL = (212, 212, 212, 255)     # #d4d4d4  (skull fill)
BLACK = (10, 10, 10, 255)        # eye sockets / nose / teeth


# ---------------------------------------------------------------------------
# Geometry helpers (coordinates mapped from the 64x64 favicon.svg)
# ---------------------------------------------------------------------------

def inside_ellipse(x: int, y: int, cx: float, cy: float, rx: float, ry: float) -> bool:
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def inside_rounded_rect(x: int, y: int, x0: int, y0: int, x1: int, y1: int, r: int) -> bool:
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    if (x0 + r <= x <= x1 - r) or (y0 + r <= y <= y1 - r):
        return True
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                   (x0 + r, y1 - r), (x1 - r, y1 - r)):
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return True
    return False


def skull_at(x: int, y: int) -> bool:
    """Skull silhouette: cranium dome + jaw (mapped from SVG)."""
    # Cranium dome: SVG path approx = circle centered ~(32, 24) r ~19.5
    if inside_ellipse(x, y, 90, 68, 54, 46):
        return True
    # Jaw: SVG rounded rect from ~(14, 46) to ~(50, 52)
    if inside_rounded_rect(x, y, 44, 100, 136, 146, 16):
        return True
    return False


def black_feature_at(x: int, y: int) -> bool:
    """Eye sockets, nose cavity, teeth separators."""
    # Left eye socket: SVG ellipse (24.5, 28) rx 6 ry 6.5
    if inside_ellipse(x, y, 69, 79, 17, 18):
        return True
    # Right eye socket: SVG ellipse (39.5, 28) rx 6 ry 6.5
    if inside_ellipse(x, y, 111, 79, 17, 18):
        return True
    # Nose cavity: SVG inverted-teardrop near (32, 32–36) → triangle + circle
    if inside_ellipse(x, y, 90, 92, 12, 14):
        return True
    if _inside_triangle(x, y, (78, 90), (102, 90), (90, 108)):
        return True
    # Teeth separators: SVG vertical lines at x 24/28/32/36/40, y 46–50
    for tx in (67, 79, 90, 101, 113):
        if 128 <= y <= 144 and tx - 2 <= x <= tx + 2:
            return True
    return False


def _inside_triangle(x: int, y: int, p1, p2, p3) -> bool:
    def sign(ax, ay, bx, by, cx, cy):
        return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)

    d1 = sign(x, y, p1[0], p1[1], p2[0], p2[1])
    d2 = sign(x, y, p2[0], p2[1], p3[0], p3[1])
    d3 = sign(x, y, p3[0], p3[1], p1[0], p1[1])
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def pixel(x: int, y: int):
    """Return RGBA tuple for pixel (x, y)."""
    # Keep a subtle rounded corner outside; iOS masks anyway
    if black_feature_at(x, y):
        return BLACK
    if skull_at(x, y):
        return SKULL
    return BG


# ---------------------------------------------------------------------------
# Minimal PNG encoder (RGBA, 8-bit, no interlace) — stdlib only
# ---------------------------------------------------------------------------

def encode_png(rows) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    raw = b"".join(
        b"\x00" + b"".join(bytes(px) for px in row) for row in rows
    )
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main() -> None:
    rows = [[pixel(x, y) for x in range(W)] for y in range(H)]
    with open("static/apple-touch-icon.png", "wb") as f:
        f.write(encode_png(rows))
    print("Generated static/apple-touch-icon.png (180x180)")


if __name__ == "__main__":
    main()