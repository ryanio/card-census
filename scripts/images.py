"""Download card photos from crawl.json into data/img2 (5:7 cells with transparent padding), sharper copies for the big lots, and small tiles for the cover map."""
import hashlib, io, json, os, sys, urllib.parse, urllib.request, concurrent.futures as cf
from PIL import Image
ROOT = sys.argv[1]; W, H = int(os.environ.get("CELL_W", 200)), int(os.environ.get("CELL_H", 280))
CACHE = os.path.join(ROOT, "data", "img2"); os.makedirs(CACHE, exist_ok=True)
HIRES = os.path.join(ROOT, "data", "hires"); os.makedirs(HIRES, exist_ok=True)
RAW = os.path.join(ROOT, "data", "raw"); os.makedirs(RAW, exist_ok=True)
crawl = json.load(open(os.path.join(ROOT, "data", "crawl.json")))

def url_of(n): return n.get("display_image_url") or n.get("image_url")
def key(u): return hashlib.sha1(u.encode()).hexdigest()
def sized(u):
    p = urllib.parse.urlsplit(u)
    if p.netloc.endswith("seadn.io"):
        q = dict(urllib.parse.parse_qsl(p.query)); q.update({"w": str(H * 2), "auto": "format"})
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ""))
    if u.startswith("ipfs://"): return "https://ipfs.io/ipfs/" + u[7:]
    return u

def trim_box(im):
    """Box around the slab on a flat or softly lit studio background (white sheet, black table), or None.
    Uses rows and columns where at least 2% of pixels differ from the corner color, so shadows and noise don't widen the box."""
    from PIL import ImageChops
    w, h = im.size; px = im.load()
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    bg = tuple(sorted(c[i] for c in corners)[1] for i in range(4))
    if bg[3] < 20: mask = im.getchannel("A").point(lambda a: 255 if a > 20 else 0)
    else:
        diff = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, bg[:3])).convert("L")
        mask = diff.point(lambda v: 255 if v > 40 else 0)
    small = mask.resize((max(1, w // 2), max(1, h // 2)))
    sw, sh = small.size; data = small.tobytes()
    cols = [sum(1 for y in range(sh) if data[y * sw + x]) for x in range(sw)]
    rows = [sum(1 for x in range(sw) if data[y * sw + x]) for y in range(sh)]
    cx = [i for i, c in enumerate(cols) if c > 0.02 * sh]; ry = [i for i, r in enumerate(rows) if r > 0.02 * sw]
    if not cx or not ry: return None
    x0, x1, y0, y1 = cx[0] * 2, (cx[-1] + 1) * 2, ry[0] * 2, (ry[-1] + 1) * 2
    if (x1 - x0) * (y1 - y0) > 0.94 * w * h: return None
    m = round(0.012 * max(w, h))
    return (max(0, x0 - m), max(0, y0 - m), min(w, x1 + m), min(h, y1 + m))
def trim(im):
    """Crop the studio background so the slab fills its cell."""
    b = trim_box(im)
    return im.crop(b) if b else im

def fetch(u):
    path = os.path.join(CACHE, key(u) + ".png")
    if os.path.exists(path) or os.path.exists(path + ".fail"): return os.path.exists(path)
    try:
        raw = os.path.join(RAW, key(u))
        if os.path.exists(raw): data = open(raw, "rb").read()
        else:
            req = urllib.request.Request(sized(u), headers={"user-agent": "Mozilla/5.0 card-census", "accept": "image/webp,image/png,image/avif,image/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=30) as r: data = r.read(25_000_000)
            open(raw, "wb").write(data)
        im = Image.open(io.BytesIO(data)); im.seek(0); im = im.convert("RGBA")
        im.thumbnail((W * 3, H * 3), Image.LANCZOS)
        im = trim(im)
        hi = im.copy(); hi.thumbnail((720, 1008), Image.LANCZOS); hi.save(os.path.join(HIRES, key(u) + ".png"))
        scale = min(W / im.width, H / im.height); im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        cell = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cell.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))
        cell.save(path); return True
    except Exception as e:
        open(path + ".fail", "w").write(str(e)[:200]); return False

urls = [url_of(n) for n in crawl["top"] + crawl.get("sealed", [])] + [url_of(n) for cs in crawl["copies"].values() for n in (cs or [])]
urls = list(dict.fromkeys(u for u in urls if u))
print("images:", len(urls), flush=True)
with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(fetch, urls))
print(f"done ok={sum(res)} fail={len(res) - sum(res)}", flush=True)

# sharper source photos for the lots shown large (cover hero, the vault's first tier, the biggest sealed lots)
BIG = os.path.join(ROOT, "data", "hires_big"); os.makedirs(BIG, exist_ok=True)
def fetch_big(u):
    path = os.path.join(BIG, key(u) + ".png")
    if os.path.exists(path): return True
    try:
        p = urllib.parse.urlsplit(u)
        if p.netloc.endswith("seadn.io"):
            q = dict(urllib.parse.parse_qsl(p.query)); q.update({"w": "1400", "auto": "format"})
            src = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ""))
        else: src = sized(u)
        req = urllib.request.Request(src, headers={"user-agent": "Mozilla/5.0 card-census", "accept": "image/webp,image/png,image/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=40) as r: data = r.read(30_000_000)
        im = Image.open(io.BytesIO(data)); im.seek(0); im = trim(im.convert("RGBA")); im.thumbnail((1100, 1540), Image.LANCZOS); im.save(path); return True
    except Exception as e:
        print("big fail", str(e)[:80]); return False
big = [url_of(n) for n in crawl["top"][:10] + crawl.get("sealed", [])[:6]]
big = list(dict.fromkeys(u for u in big if u))
with cf.ThreadPoolExecutor(8) as ex: rb = list(ex.map(fetch_big, big))
print(f"big ok={sum(rb)} of {len(rb)}", flush=True)

# cover map tiles: small tiles show the card face (a slab's label and plastic cropped off, so the map reads as color),
# and the most valuable cards also get a bigger tile of the whole slab (data/midi) for the center of their island
MINI = os.path.join(ROOT, "data", "tiles"); os.makedirs(MINI, exist_ok=True)
MIDI = os.path.join(ROOT, "data", "midi"); os.makedirs(MIDI, exist_ok=True)
def fetch_mini(u, MW=40, MH=56, out=MINI, w=160, face=True):
    """Write the tile, and next to it a .box file: where the slab sits in the photo, as fractions, for the page's preview."""
    path = os.path.join(out, key(u) + ".png")
    if os.path.exists(path + ".fail") or (os.path.exists(path) and (out != MINI or os.path.exists(path + ".box"))): return os.path.exists(path)
    try:
        raw = os.path.join(RAW, key(u))
        if os.path.exists(raw): data = open(raw, "rb").read()
        else:
            p = urllib.parse.urlsplit(u)
            if p.netloc.endswith("seadn.io"):
                q = dict(urllib.parse.parse_qsl(p.query)); q.update({"w": str(w), "auto": "format"})
                src = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ""))
            else: src = sized(u)
            req = urllib.request.Request(src, headers={"user-agent": "Mozilla/5.0 card-census", "accept": "image/webp,image/png,image/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=30) as r: data = r.read(25_000_000)
        im = Image.open(io.BytesIO(data)); im.seek(0); im = im.convert("RGBA"); im.thumbnail((480, 480), Image.LANCZOS)
        b = trim_box(im) or (0, 0, im.width, im.height)
        open(path + ".box", "w").write(" ".join(f"{v:.3f}" for v in (b[0] / im.width, b[1] / im.height, b[2] / im.width, b[3] / im.height)))
        im = im.crop(b)
        if face and im.width / im.height < 0.66:  # a slab: keep the card window below the label
            im = im.crop((round(im.width * 0.08), round(im.height * 0.235), round(im.width * 0.92), round(im.height * 0.955)))
        r = MW / MH
        if im.width / im.height > r: nw = round(im.height * r); x = (im.width - nw) // 2; im = im.crop((x, 0, x + nw, im.height))
        else: nh = round(im.width / r); y = round((im.height - nh) * (0.5 if face else 0.3)); im = im.crop((0, y, im.width, y + nh))
        bed = Image.new("RGBA", (MW, MH), (27, 26, 32, 255)); bed.alpha_composite(im.resize((MW, MH), Image.LANCZOS)); bed.convert("RGB").save(path)
        return True
    except Exception as e:
        open(path + ".fail", "w").write(str(e)[:200]); return False
mp = crawl.get("map") or {}
nfts = crawl["top"] + crawl.get("sealed", []) + [n for cs in crawl["copies"].values() for n in (cs or [])] + [n for group in (mp.get("subject") or {}, mp.get("franchise") or {}) for ns in group.values() for n in (ns or [])]
mini = list(dict.fromkeys(u for u in (url_of(n) for n in nfts) if u))
with cf.ThreadPoolExecutor(16) as ex: rm = list(ex.map(fetch_mini, mini))
print(f"map tiles ok={sum(rm)} of {len(rm)}", flush=True)
def value(n):
    try: return float(n.get("estimated_value_usd") or 0)
    except (TypeError, ValueError): return 0
big = list(dict.fromkeys(url_of(n) for n in sorted(nfts, key=lambda n: -value(n)) if url_of(n)))[:160]
big += [url_of(n) for ns in (mp.get("franchise") or {}).values() for n in sorted(ns or [], key=lambda n: -value(n))[:2] if url_of(n)]
big = list(dict.fromkeys(big))
with cf.ThreadPoolExecutor(12) as ex: rb = list(ex.map(lambda u: fetch_mini(u, 120, 168, MIDI, 420, face=False), big))
print(f"big map tiles ok={sum(rb)} of {len(rb)}", flush=True)
