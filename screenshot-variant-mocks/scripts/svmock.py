"""svmock: helpers for compositing UI variants onto real device screenshots.

Import from a per-project generator:
    import sys; sys.path.insert(0, "<skill-dir>/scripts")
    import svmock as S

The rule: measure the real screenshot, erase only the region under test, redraw it
with the product's real fonts and tokens, keep everything else as captured pixels.
"""
import base64, hashlib, io, os
from PIL import Image, ImageDraw, ImageFont

# ---------- loading / measuring ----------
def load(path):
    return Image.open(path).convert("RGBA")

def is_bg(px, thresh=60):
    return sum(px[:3]) <= thresh

def bands(img, x0, x1, y0, y1, step=6, thresh=75):
    """Vertical scan: list of (y, 'dark'|'content') transitions across columns x0..x1.
    Use to find where covers/cards end and caption bands begin."""
    p = img.convert("RGB").load(); out, prev = [], None
    for y in range(y0, y1):
        dark = all(sum(p[x, y]) < thresh for x in range(x0, x1, step))
        if dark != prev:
            out.append((y, "dark" if dark else "content")); prev = dark
    return out

def segments(img, y, min_w=40, thresh=60):
    """Horizontal scan at row y: list of (x0, x1) non-background runs (tile columns)."""
    p = img.convert("RGB").load(); W = img.width; segs, start = [], None
    for x in range(W):
        nb = sum(p[x, y]) > thresh
        if nb and start is None: start = x
        if not nb and start is not None:
            if x - start >= min_w: segs.append((start, x))
            start = None
    if start is not None and W - start >= min_w: segs.append((start, W))
    return segs

def text_box(img, box, lo=45, hi=230, tol=15):
    """Bounding box of neutral-grey text pixels inside box=(x0,y0,x1,y1). None if empty."""
    p = img.convert("RGB").load(); x0, y0, x1, y1 = box; xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = p[x, y]
            if lo < r < hi and abs(r - g) < tol and abs(r - b) < tol:
                xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None

def font_px_for_width(font_path, text, measured_w, lo=8.0, hi=80.0):
    """Binary-search the font pixel size whose rendered width matches a measured text width."""
    for _ in range(30):
        mid = (lo + hi) / 2
        w = ImageFont.truetype(font_path, mid).getlength(text)
        lo, hi = (mid, hi) if w < measured_w else (lo, mid)
    return round((lo + hi) / 2, 2)

def density(font_px, sp):
    """px per dp/pt, from a measured font pixel size and the token size in sp/pt."""
    return font_px / sp

# ---------- drawing ----------
def erase(img, box, color):
    ImageDraw.Draw(img).rectangle(box, fill=tuple(color[:3]) + (255,))

def fit(text, font, w, force_ellipsis=False, tracking=0.0):
    """Single-line truncation with an ellipsis, like TextOverflow.Ellipsis / lineLimit(1)."""
    def width(t): return font.getlength(t) + tracking * max(0, len(t) - 1)
    if not force_ellipsis and width(text) <= w: return text
    t = text
    while t and width(t.rstrip() + "…") > w: t = t[:-1]
    return t.rstrip() + "…"

def cap_height(font):
    return -font.getbbox("H", anchor="ls")[1]

def draw_tracked(img, x, baseline, text, font, fill, tracking):
    d = ImageDraw.Draw(img)
    for ch in text:
        d.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch) + tracking

def stable_index(key, n):
    """Deterministic pick (same entity -> same asset), mirrors md5-based backend assignment."""
    return int(hashlib.md5(str(key).encode()).hexdigest(), 16) % n

def circle(src, size, ss=4):
    """Circle-crop an image (path or PIL) to size px with supersampled antialiasing."""
    im = (Image.open(src) if isinstance(src, str) else src).convert("RGBA")
    S = size * ss
    side = min(im.size); im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                                      (im.width + side) // 2, (im.height + side) // 2)).resize((S, S), Image.LANCZOS)
    m = Image.new("L", (S, S), 0); ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0)); out.paste(im, (0, 0), m)
    return out.resize((size, size), Image.LANCZOS)

def initials(name, max_letters=2):
    parts, cur = [], ""
    for ch in name:
        if ch.isalpha(): cur += ch
        elif cur: parts.append(cur); cur = ""
    if cur: parts.append(cur)
    return "".join(p[0] for p in parts[:max_letters]).upper() or "?"

def disc(size, bg, text=None, font_path=None, fg=(185, 185, 185), glyph_font=None, glyph=None, ss=4):
    """Neutral disc with initials or an icon glyph. Below ~20dp use one letter: two are illegible."""
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, S - 1, S - 1), fill=tuple(bg[:3]) + (255,))
    if text:
        f = ImageFont.truetype(font_path, int(S * (0.44 if len(text) == 1 else 0.38)))
        d.text((S / 2, S / 2 + S * 0.03), text, font=f, fill=fg, anchor="mm")
    if glyph:
        d.text((S / 2, S / 2), glyph, font=ImageFont.truetype(glyph_font, int(S * 0.72)), fill=fg, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)

def placeholder_photo(key, size, ss=4):
    """Neutral silhouette placeholder. Label it as a placeholder wherever it is shown."""
    tones = [((92, 98, 112), (60, 64, 74)), ((116, 104, 92), (74, 66, 58)), ((90, 108, 98), (58, 70, 63)),
             ((108, 92, 106), (70, 58, 68)), ((96, 104, 118), (62, 68, 80))]
    top, bot = tones[stable_index(key, len(tones))]; S = size * ss
    t = Image.new("RGBA", (S, S)); d = ImageDraw.Draw(t)
    for y in range(S):
        k = y / S; d.line([(0, y), (S, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)) + (255,))
    light = tuple(min(255, c + 70) for c in top) + (255,)
    d.ellipse((S * .32, S * .18, S * .68, S * .54), fill=light); d.ellipse((S * .12, S * .60, S * .88, S * 1.25), fill=light)
    return circle(t, size, 1) if ss == 1 else circle(t.resize((S, S)), size)

def ring(img, ringw, color):
    S = img.width + 2 * ringw
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, S - 1, S - 1), fill=tuple(color[:3]) + (255,))
    out.alpha_composite(img, (ringw, ringw)); return out

def clip_below(layer, y_limit):
    """Drop anything drawn at or below y_limit (e.g. under a floating mini player)."""
    full = Image.new("RGBA", layer.size, (0, 0, 0, 0)); full.paste(layer.crop((0, 0, layer.width, y_limit)), (0, 0)); return full

# ---------- boards ----------
def rounded(im, r=30, border=(40, 40, 40)):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    o = Image.new("RGBA", im.size, (0, 0, 0, 0)); o.paste(im, (0, 0), m)
    ImageDraw.Draw(o).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, outline=border, width=4); return o

def board(cells, title, note, path, font_medium, font_book, cols=None, gap=36, pad=60):
    """cells: [(PIL image, title, subtitle)]. Writes a dark comparison board PNG."""
    cols = cols or len(cells); cw = max(c[0].width for c in cells); ch = max(c[0].height for c in cells); lh = 100
    rows = (len(cells) + cols - 1) // cols
    B = Image.new("RGBA", (pad * 2 + cols * cw + (cols - 1) * gap, pad + 150 + rows * (lh + ch + gap) + pad), (20, 20, 20, 255))
    d = ImageDraw.Draw(B)
    d.text((pad, pad), title, font=ImageFont.truetype(font_medium, 52), fill=(245, 245, 245))
    d.text((pad, pad + 72), note, font=ImageFont.truetype(font_book, 30), fill=(150, 150, 150))
    for i, (im, t, s) in enumerate(cells):
        r, c = divmod(i, cols); x = pad + c * (cw + gap); y = pad + 150 + r * (lh + ch + gap)
        d.text((x, y + 7), t, font=ImageFont.truetype(font_medium, 34), fill=(240, 240, 240))
        d.text((x, y + 51), s, font=ImageFont.truetype(font_book, 24), fill=(150, 150, 150))
        B.alpha_composite(im.convert("RGBA"), (x, y + lh))
    B.convert("RGB").save(path, optimize=True); return path

# ---------- viewer assets ----------
def web_copy(src, dst, max_w=1080, quality=86):
    """JPEG copy for the HTML viewer (keeps the viewer light). Returns dst."""
    im = Image.open(src).convert("RGB")
    if im.width > max_w: im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True); im.save(dst, "JPEG", quality=quality, optimize=True); return dst

def data_uri(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    return f"data:image/{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()
