"""Render the 1200x630 social card: the headline and numbers, and the cover map's archipelago of real card photos."""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); FONTS = os.path.join(ROOT, "data", "fonts")
S = json.load(open(os.path.join(ROOT, "data", "summary.json")))
K = 2; W, H = 1200 * K, 630 * K
BG, INK, INK2, PINK = (11, 10, 12), (245, 244, 246), (170, 168, 176), (255, 111, 163)
img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size * K)
    if var: f.set_variation_by_name(var)
    return f

# the map, laid out the way the page does it: one island per franchise, packed into a cluster, each crowned by its priciest card
def allocate(counts, n):
    total = sum(counts); raw = [x * n / total for x in counts]
    a = [max(1, math.floor(x)) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] - math.floor(raw[i])))
    k = 0
    while sum(a) < n: a[order[k % len(order)]] += 1; k += 1
    while sum(a) > n: a[a.index(max(a))] -= 1
    return a
M = S["map"]; G = [g for g in M["groups"] if g["n"] > 0]; B = M["big"]; TH = M["h"] / M["w"]; N = 520
fam = {}
for gi, g in enumerate(G): fam.setdefault(g["f"], []).append(gi)
isl = sorted([{"f": f, "gis": gis, "n": sum(G[gi]["n"] for gi in gis)} for f, gis in fam.items()], key=lambda x: -x["n"])
for x, c in zip(isl, allocate([x["n"] for x in isl], N)): x["cells"] = max(3, c); x["ru"] = math.sqrt(x["cells"] * TH / math.pi) * 1.04
gap, stretch = 1.25, 1.0
isl[0]["ux"], isl[0]["uy"] = 0.0, 0.0
for k in range(1, len(isl)):
    r, best = isl[k]["ru"], None
    for c in isl[:k]:
        for a in range(0, 360, 2):
            t = math.radians(a); x = c["ux"] + (c["ru"] + r + gap) * math.cos(t); y = c["uy"] + (c["ru"] + r + gap) * math.sin(t)
            if any(math.hypot(q["ux"] - x, q["uy"] - y) < q["ru"] + r + gap - 1e-6 for q in isl[:k]): continue
            s = math.hypot(x * stretch, y)
            if best is None or s < best[2]: best = (x, y, s)
    isl[k]["ux"], isl[k]["uy"] = best[0], best[1]
minx = min(x["ux"] - x["ru"] for x in isl); maxx = max(x["ux"] + x["ru"] for x in isl); miny = min(x["uy"] - x["ru"] for x in isl); maxy = max(x["uy"] + x["ru"] for x in isl)
box_w, box_h = 600 * K, 590 * K
tw = min(box_w / (maxx - minx), box_h / (maxy - miny)); th = tw * TH
ox0 = W - 30 * K - (maxx - minx) * tw; oy0 = (H - (maxy - miny) * tw) / 2
sheets = [Image.open(os.path.join(SITE, f)).convert("RGB") for f in M["files"]]; bsheet = Image.open(os.path.join(SITE, B["file"])).convert("RGB")
masks = {}
def mask_for(w, h, r):
    if (w, h) not in masks:
        m = Image.new("L", (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=round(r * 4), fill=255); masks[(w, h)] = m.resize((w, h), Image.LANCZOS)
    return masks[(w, h)]
def tile(t, b):
    if b >= 0: return bsheet.crop(((b % B["cols"]) * B["w"], (b // B["cols"]) * B["h"], (b % B["cols"] + 1) * B["w"], (b // B["cols"] + 1) * B["h"]))
    if t < 0: return Image.new("RGB", (M["w"], M["h"]), (42, 41, 48))
    sh, j = sheets[t // M["per"]], t % M["per"]
    return sh.crop(((j % M["cols"]) * M["w"], (j // M["cols"]) * M["h"], (j % M["cols"] + 1) * M["w"], (j // M["cols"] + 1) * M["h"]))
g_ = max(2, round(tw * 0.09))
def paste(x, y, w, h, t, b, big=False):
    pw, ph = round(w - g_), round(h - g_)
    img.paste(tile(t, b).resize((pw, ph), Image.LANCZOS), (round(x + g_ / 2), round(y + g_ / 2)), mask_for(pw, ph, tw * (0.25 if big else 0.14)))
    if big: d.rounded_rectangle([x + g_ / 2, y + g_ / 2, x + g_ / 2 + pw - 1, y + g_ / 2 + ph - 1], radius=round(tw * 0.25), outline=(225, 224, 230), width=K)
for I in isl:
    cx, cy = ox0 + (I["ux"] - minx) * tw, oy0 + (I["uy"] - miny) * tw; I["cx"], I["cy"], I["r"] = cx, cy, I["ru"] * tw
    cands = sorted([(v, t, b, gi) for gi in I["gis"] for t, b, v in (G[gi].get("big") or [])], reverse=True)
    hero = cands[0] if cands else None
    k = (4 if I["cells"] >= 200 else 3 if I["cells"] >= 60 else 2 if I["cells"] >= 16 else 0) if hero else 0
    ox, oy = cx - (k / 2 if k else 0.5) * tw, cy - (k / 2 if k else 0.5) * th
    R = math.ceil(I["ru"]) + 3
    cand = sorted([(math.hypot(ox + i * tw + tw / 2 - cx, oy + j * th + th / 2 - cy), i, j) for j in range(-R, R + 1) for i in range(-R, R + 1)])[:I["cells"]]
    if k: paste(ox, oy, k * tw, k * th, hero[1], hero[2], big=True)
    rest = [(dd, i, j) for dd, i, j in cand if not (k and 0 <= i < k and 0 <= j < k)]
    rest.sort(key=lambda c: (math.atan2(ox + c[1] * tw + tw / 2 - cx, -(oy + c[2] * th + th / 2 - cy)) + 2 * math.pi) % (2 * math.pi))
    order = sorted([gi for gi in I["gis"] if G[gi]["k"] == "s"], key=lambda gi: -G[gi]["n"]) + [gi for gi in I["gis"] if G[gi]["k"] != "s"]
    share = allocate([G[gi]["n"] for gi in order], len(rest)) if rest else []
    at = 0
    for gi, n in zip(order, share):
        sl = sorted(rest[at:at + n]); at += n
        tiles = [t for t in G[gi]["tiles"] if not hero or t != hero[1]] or G[gi]["tiles"]
        for m, (dd, i, j) in enumerate(sl): paste(ox + i * tw, oy + j * th, tw, th, tiles[m % len(tiles)] if tiles else -1, -1)
# a quiet label inside the bottom of each big island
tb, ts = font("bsd.ttf", 17, b"ExtraBold"), font("mono.ttf", 10)
for I in isl:
    if I["cells"] < 15: continue
    g = next((G[gi] for gi in I["gis"] if G[gi]["k"] == "f"), G[I["gis"][0]])
    name, cnt = g["f"].upper(), f"{(g.get('total') or I['n']):,}"
    bw = max(d.textlength(name, font=tb), d.textlength(cnt, font=ts)) + 24 * K; bh = 40 * K
    x0, y0 = I["cx"] - bw / 2, I["cy"] + I["r"] - bh * 0.75
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bh // 2, fill=(17, 16, 19), outline=(70, 68, 76), width=K)
    d.text((I["cx"], y0 + 15 * K), name, font=tb, fill=(255, 255, 255), anchor="mm"); d.text((I["cx"], y0 + 30 * K), cnt, font=ts, fill=(190, 188, 196), anchor="mm")

# left column: kicker, headline, numbers, byline
L = 64 * K
d.text((L, 56 * K), "CARD CENSUS", font=font("mono.ttf", 17), fill=PINK)
title = font("bsd.ttf", 92, b"Black")
for k, line in enumerate(["EVERY CARD", "ONCHAIN,", "COUNTED"]):
    d.text((L, 84 * K + k * 82 * K), line, font=title, fill=INK)
y = 84 * K + 3 * 82 * K + 26 * K
holo = [(255, 77, 141), (255, 181, 71), (255, 228, 94), (77, 224, 201), (61, 169, 255), (155, 107, 255)]
for i, c in enumerate(holo): d.rectangle([L + i * 30 * K, y, L + (i + 1) * 30 * K, y + 6 * K], fill=c)
num, lab = font("bsd.ttf", 52, b"ExtraBold"), font("ps.ttf", 17, b"Medium")
sub = {s["s"]: s for s in S["subjects"]}; hero = sub.get("Pikachu") or S["subjects"][0]
y += 30 * K
for v, t in [(f"{S['n']:,}", "trading cards onchain"), (f"{hero['n']:,}", f"of them are {hero['s']}s")]:
    d.text((L, y), v, font=num, fill=INK); d.text((L + d.textlength(v, font=num) + 14 * K, y + 24 * K), t, font=lab, fill=INK2); y += 62 * K
d.text((L, H - 56 * K), "By Ryan Ghods  ·  data from the OpenSea API", font=font("mono.ttf", 15), fill=INK2)
img.resize((1200, 630), Image.LANCZOS).save(os.path.join(SITE, "og.png"), optimize=True)
# the map alone, for the map's share card
pad = 6 * K
img.crop((int(min(I["cx"] - I["r"] for I in isl)) - pad, int(min(I["cy"] - I["r"] for I in isl)) - pad, int(max(I["cx"] + I["r"] for I in isl)) + pad, int(max(I["cy"] + I["r"] for I in isl)) + pad)).save(os.path.join(ROOT, "data", "og_map.png"))
print("og.png", os.path.getsize(os.path.join(SITE, "og.png")))
