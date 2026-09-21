"""Pure-stdlib PNG generator demo (numpy + zlib, no Pillow).

Outputs into the same folder:
  01_gradient_testcard.png  - gradient background + colour bars + checkerboard
  02_shapes.png             - geometric composition (circles, strokes, rounded rect)
  03_barchart.png           - simple bar chart drawn from scratch
"""
import zlib
import struct
import os
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 960, 540


def write_png(path, rgb):
    """rgb: (H, W, 3) uint8 array -> PNG file."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def canvas(w=W, h=H):
    yy, xx = np.mgrid[0:h, 0:w]
    return xx.astype(np.float64), yy.astype(np.float64), np.zeros((h, w, 3), np.float64)


# ---------------------------------------------------------------- 1. test card
def testcard():
    x, y, img = canvas()
    # diagonal gradient
    t = (x / W + y / H) / 2
    img[..., 0] = 20 + 60 * t
    img[..., 1] = 30 + 90 * (1 - t)
    img[..., 2] = 70 + 120 * t

    # vertical colour bars (upper third)
    bars = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
            (255, 0, 255), (255, 0, 0), (0, 0, 255), (16, 16, 16)]
    bw = W // len(bars)
    mask = y < H * 0.33
    for i, c in enumerate(bars):
        sel = mask & (x >= i * bw) & (x < (i + 1) * bw)
        img[sel] = c

    # checkerboard footer
    sq = 30
    checker = ((x // sq).astype(int) + (y // sq).astype(int)) % 2 == 0
    sel = (y > H * 0.80) & checker
    img[sel] = [235, 235, 240]
    sel = (y > H * 0.80) & ~checker
    img[sel] = [45, 45, 55]

    # grey ramp band
    sel = (y >= H * 0.33) & (y < H * 0.45)
    img[sel] = np.repeat((x[sel] / W * 255)[:, None], 3, axis=1)

    return write_png(os.path.join(OUT, "01_gradient_testcard.png"),
                     np.clip(img, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ 2. shapes
def shapes():
    x, y, img = canvas()
    img[:] = [14, 16, 24]

    def disc(cx, cy, r, colour, alpha=1.0):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        m = d <= r
        soft = np.clip(r - d, 0, 1)[..., None]
        img[:] = img * (1 - soft * alpha) + np.array(colour) * (soft * alpha)

    def ring(cx, cy, r, width, colour):
        d = np.abs(np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - r)
        soft = np.clip(width - d, 0, 1)[..., None]
        img[:] = img * (1 - soft) + np.array(colour) * soft

    # a few stacked translucent discs
    palette = [(126, 231, 208), (86, 160, 255), (255, 150, 90), (230, 90, 160)]
    for i, c in enumerate(palette):
        disc(240 + i * 105, 250 + (i % 2) * 60, 120, c, 0.55)
    # concentric rings
    for r in range(50, 260, 26):
        ring(720, 270, r, 3, (60, 220, 255))
    # horizon line
    row = slice(430, 434)
    img[row] = [240, 240, 245]

    return write_png(os.path.join(OUT, "02_shapes.png"),
                     np.clip(img, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- 3. bar chart
def barchart():
    x, y, img = canvas()
    img[:] = [250, 250, 252]
    pad_l, pad_b, pad_t = 90, 90, 60
    plot_h = H - pad_b - pad_t

    labels = ["chunk", "embed", "index", "search", "rerank", "gen"]
    values = [42, 68, 55, 91, 37, 76]
    vmax = 100
    n = len(values)
    slot = (W - pad_l - 60) / n
    bar_w = slot * 0.58

    # gridlines
    for g in range(0, vmax + 1, 20):
        gy = H - pad_b - int(plot_h * g / vmax)
        img[gy:gy + 1, pad_l:W - 60] = [225, 228, 235]
        # tick label drawn as simple 5x7 blocks
        draw_text(img, str(g), pad_l - 60, gy - 8, [130, 135, 145], scale=2)

    # bars
    for i, (lab, v) in enumerate(zip(labels, values)):
        bx0 = int(pad_l + i * slot + (slot - bar_w) / 2)
        bx1 = int(bx0 + bar_w)
        h = int(plot_h * v / vmax)
        by0 = H - pad_b - h
        by1 = H - pad_b
        shade = 60 + int(150 * v / vmax)
        for bx in range(bx0, bx1):
            tt = (bx - bx0) / max(1, bar_w - 1)
            img[by0:by1, bx] = [shade, 90 + int(80 * tt), 200 - int(90 * tt)]
        # value label
        draw_text(img, str(v), (bx0 + bx1) // 2 - 16, by0 - 26, [70, 75, 90], scale=3)
        # category label
        draw_text(img, lab, (bx0 + bx1) // 2 - len(lab) * 6, H - pad_b + 16,
                  [90, 95, 110], scale=2)

    # axis
    img[H - pad_b:H - pad_b + 2, pad_l:W - 60] = [80, 85, 100]
    img[pad_t: H - pad_b, pad_l - 2:pad_l] = [80, 85, 100]
    draw_text(img, "PIPELINE STAGE", pad_l, 24, [40, 45, 60], scale=3)

    return write_png(os.path.join(OUT, "03_barchart.png"),
                     np.clip(img, 0, 255).astype(np.uint8))


# tiny 5x7 bitmap font, just what this demo needs
FONT = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000"] * 7,
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
}


def draw_text(img, text, x0, y0, colour, scale=2):
    h, w, _ = img.shape
    cx = x0
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    ys, xs = y0 + gy * scale, cx + gx * scale
                    if 0 <= ys < h - scale and 0 <= xs < w - scale:
                        img[ys:ys + scale, xs:xs + scale] = colour
        cx += 6 * scale


if __name__ == "__main__":
    for fn in (testcard, shapes, barchart):
        size = fn()
        print(f"{fn.__name__:10s} -> {fn.__name__}.png  {size/1024:.1f} KB")
    print("done ->", OUT)
