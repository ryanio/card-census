"""Render the 1200x630 social card: the headline and numbers, and the cover map of real card photos."""
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

# the map: same curve, order and allocation as the page
def gilbert(w, h):
    pts = []
    sgn = lambda v: (v > 0) - (v < 0)
    def gen(x, y, ax, ay, bx, by):
        ww, hh = abs(ax + ay), abs(bx + by); dax, day, dbx, dby = sgn(ax), sgn(ay), sgn(bx), sgn(by)
        if hh == 1:
            for _ in range(ww): pts.append((x, y)); x += dax; y += day
            return
        if ww == 1:
            for _ in range(hh): pts.append((x, y)); x += dbx; y += dby
            return
        ax2, ay2, bx2, by2 = ax // 2, ay // 2, bx // 2, by // 2
        w2, h2 = abs(ax2 + ay2), abs(bx2 + by2)
        if 2 * ww > 3 * hh:
            if w2 % 2 and ww > 2: ax2 += dax; ay2 += day
            gen(x, y, ax2, ay2, bx, by); gen(x + ax2, y + ay2, ax - ax2, ay - ay2, bx, by)
        else:
            if h2 % 2 and hh > 2: bx2 += dbx; by2 += dby
            gen(x, y, bx2, by2, ax2, ay2); gen(x + bx2, y + by2, ax, ay, bx - bx2, by - by2)
            gen(x + (ax - dax) + (bx2 - dbx), y + (ay - day) + (by2 - dby), -bx2, -by2, -(ax - ax2), -(ay - ay2))
    if w >= h: gen(0, 0, w, 0, 0, h)
    else: gen(0, 0, 0, h, w, 0)
    return [(x, h - 1 - y) for x, y in pts] if pts[-1][1] == 0 else pts
def allocate(counts, n):
    total = sum(counts); raw = [x * n / total for x in counts]
    a = [max(1, math.floor(x)) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] - math.floor(raw[i])))
    k = 0
    while sum(a) < n: a[order[k % len(order)]] += 1; k += 1
    while sum(a) > n: a[a.index(max(a))] -= 1
    return a
M = S["map"]; G = [g for g in M["groups"] if g["n"] > 0]
COLS, ROWS = 40, 36
pts = gilbert(COLS, ROWS); N = len(pts); alloc = allocate([g["n"] for g in G], N)
owner = [gi for gi, g in enumerate(G) for _ in range(alloc[gi])]
at = {p: i for i, p in enumerate(pts)}
own = {p: owner[i] for p, i in at.items()}
cells = [[] for _ in G]
for i, o in enumerate(owner): cells[o].append(i)
# the priciest cards get 2x2 to 4x4 tiles inside their own territory, spread apart, as on the page
items, used, centers, placed_t = [], set(), [], [set() for _ in G]
cands, seen_t = [], set()
for gi, g in enumerate(G):
    for t, b, v in g.get("big") or []:
        if t not in seen_t: seen_t.add(t); cands.append((gi, t, b, v))
cands.sort(key=lambda c: -c[3])
n4, n3, n2 = max(1, round(N / 480)), round(N / 130), round(N / 40)
def fits(gi, x, y, sz):
    return x + sz <= COLS and y + sz <= ROWS and all((xx, yy) not in used and own[(xx, yy)] == gi for yy in range(y, y + sz) for xx in range(x, x + sz))
for rank, (gi, t, b, v) in enumerate(cands):
    target = 4 if rank < n4 else 3 if rank < n4 + n3 else 2 if rank < n4 + n3 + n2 else 0
    if not target: break
    cs = cells[gi]; mx = sum(pts[i][0] for i in cs) / len(cs); my = sum(pts[i][1] for i in cs) / len(cs)
    for sz in range(target, 1, -1):
        best, best_score = None, -1e18
        for i in cs:
            x, y = pts[i]
            if not fits(gi, x, y, sz): continue
            cx, cy = x + sz / 2, y + sz / 2
            dmin = min([math.hypot(px - cx, py - cy) for px, py in centers] or [1e9])
            score = min(dmin, 12) * 10 - math.hypot(cx - mx, cy - my)
            if score > best_score: best_score, best = score, (x, y)
        if not best: continue
        x, y = best
        for yy in range(y, y + sz):
            for xx in range(x, x + sz): used.add((xx, yy))
        items.append((x, y, sz, t, b)); placed_t[gi].add(t); centers.append((x + sz / 2, y + sz / 2))
        break
nxt = [[[t for t in g["tiles"] if t not in placed_t[gi]] or g["tiles"], 0] for gi, g in enumerate(G)]
for i, (x, y) in enumerate(pts):
    if (x, y) in used: continue
    q = nxt[owner[i]]; t = q[0][q[1] % len(q[0])] if q[0] else -1; q[1] += 1
    items.append((x, y, 1, t, -1))
tw = (H - 40 * K) / (ROWS * M["h"] / M["w"]); th = tw * M["h"] / M["w"]
ox, oy = W - 40 * K - COLS * tw, 20 * K
gap = max(2, round(tw * 0.08)); cw, ch = round(tw - gap), round(th - gap)
sheets = [Image.open(os.path.join(SITE, f)).convert("RGB") for f in M["files"]]
B = M["big"]; bsheet = Image.open(os.path.join(SITE, B["file"])).convert("RGB")
masks = {}
def mask_for(w, h, r):
    if (w, h) not in masks:
        m = Image.new("L", (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=round(r * 4), fill=255); masks[(w, h)] = m.resize((w, h), Image.LANCZOS)
    return masks[(w, h)]
for x, y, sz, t, b in items:
    w, h = round(sz * tw - gap), round(sz * th - gap)
    if b >= 0: cell = bsheet.crop(((b % B["cols"]) * B["w"], (b // B["cols"]) * B["h"], (b % B["cols"] + 1) * B["w"], (b // B["cols"] + 1) * B["h"]))
    elif t >= 0:
        sh, j = sheets[t // M["per"]], t % M["per"]
        cell = sh.crop(((j % M["cols"]) * M["w"], (j // M["cols"]) * M["h"], (j % M["cols"] + 1) * M["w"], (j // M["cols"] + 1) * M["h"]))
    else: cell = Image.new("RGB", (M["w"], M["h"]), (42, 41, 48))
    img.paste(cell.resize((w, h), Image.LANCZOS), (round(ox + x * tw + gap / 2), round(oy + y * th + gap / 2)), mask_for(w, h, tw * (0.2 if sz > 1 else 0.13)))
    if sz > 1: d.rounded_rectangle([ox + x * tw + gap / 2, oy + y * th + gap / 2, ox + x * tw + gap / 2 + w - 1, oy + y * th + gap / 2 + h - 1], radius=round(tw * 0.2), outline=(205, 204, 210), width=K)
# gutters between territories, wider between franchises, and a faint line around each big card's territory
for wide in (True, False):
    lw = max(3, round(tw * (0.3 if wide else 0.17)))
    for i, (x, y) in enumerate(pts):
        for dx, dy in ((1, 0), (0, 1)):
            j = at.get((x + dx, y + dy))
            if j is None: continue
            a, bb = G[owner[i]], G[owner[j]]
            if a is bb or (a.get("f") == bb.get("f")) == wide: continue
            X, Y = ox + (x + dx) * tw, oy + (y + dy) * th
            d.line([(X, oy + y * th), (X, oy + (y + 1) * th)] if dx else [(ox + x * tw, Y), (ox + (x + 1) * tw, Y)], fill=BG, width=lw)
for i, (x, y) in enumerate(pts):
    if G[owner[i]]["k"] != "s": continue
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        j = at.get((x + dx, y + dy))
        if j is not None and owner[j] == owner[i]: continue
        X, Y = ox + (x + (dx > 0)) * tw, oy + (y + (dy > 0)) * th
        d.line([(X, Y), (X, Y + th)] if dx else [(X, Y), (X + tw, Y)], fill=(112, 110, 118), width=K)
# labels on the biggest territories, skipping any that would collide
def center(cs):
    sx = sum(pts[i][0] for i in cs) / len(cs); sy = sum(pts[i][1] for i in cs) / len(cs)
    i = min(cs, key=lambda i: (pts[i][0] - sx) ** 2 + (pts[i][1] - sy) ** 2)
    return ox + (pts[i][0] + 0.5) * tw, oy + (pts[i][1] + 0.5) * th
tb, ts = font("bsd.ttf", 19, b"ExtraBold"), font("mono.ttf", 11)
placed = []
for gi in sorted(range(len(G)), key=lambda gi: -len(cells[gi])):
    g = G[gi]
    if len(cells[gi]) < 12: continue
    name = (g.get("s") or g.get("f")).upper(); cnt = f"{(g.get('total') or g['n']):,}"
    bw = max(d.textlength(name, font=tb), d.textlength(cnt, font=ts)) + 22 * K; bh = 44 * K
    cx, cy = center(cells[gi]); x0 = min(ox + COLS * tw - bw - 4 * K, max(ox + 4 * K, cx - bw / 2)); y0 = min(oy + ROWS * th - bh - 4 * K, max(oy + 4 * K, cy - bh / 2))
    box = (x0 - 6 * K, y0 - 4 * K, x0 + bw + 6 * K, y0 + bh + 4 * K)
    if any(not (box[2] < p[0] or box[0] > p[2] or box[3] < p[1] or box[1] > p[3]) for p in placed): continue
    placed.append(box)
    fr = g["k"] == "f"
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=4 * K, fill=(17, 18, 20) if fr else (255, 255, 255), outline=(240, 240, 242) if fr else None, width=2 * K if fr else 0)
    d.text((x0 + bw / 2, y0 + 15 * K), name, font=tb, fill=(255, 255, 255) if fr else (17, 18, 20), anchor="mm")
    d.text((x0 + bw / 2, y0 + 33 * K), cnt, font=ts, fill=(210, 208, 215) if fr else (74, 78, 85), anchor="mm")
    if len(placed) >= 7: break

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
img.crop((int(ox) - 2 * K, int(oy) - 2 * K, int(ox + COLS * tw) + 2 * K, int(oy + ROWS * th) + 2 * K)).save(os.path.join(ROOT, "data", "og_map.png"))
print("og.png", os.path.getsize(os.path.join(SITE, "og.png")))
