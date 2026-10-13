"""Render the 1200x630 social card: the question headline and a grid of the most valuable slabs."""
import json, os, sys
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
sub = {s["s"]: s for s in S["subjects"]}
hero = sub.get("Charizard") or S["subjects"][0]
L = 64 * K
d.text((L, 56 * K), "CARD CENSUS", font=font("mono.ttf", 17), fill=PINK)
title = font("bsd.ttf", 84, b"Black")
for k, line in enumerate(["EVERY CARD", "ONCHAIN,", "COUNTED"]):
    d.text((L, 86 * K + k * 76 * K), line, font=title, fill=INK)
y = 86 * K + 3 * 76 * K + 26 * K
holo = [(255, 77, 141), (255, 181, 71), (255, 228, 94), (77, 224, 201), (61, 169, 255), (155, 107, 255)]
for i, c in enumerate(holo): d.rectangle([L + i * 30 * K, y, L + (i + 1) * 30 * K, y + 6 * K], fill=c)
num, lab = font("bsd.ttf", 52, b"ExtraBold"), font("ps.ttf", 17, b"Medium")
y += 30 * K
for v, t in [(f"{S['n']:,}", "trading cards counted"), (f"{hero['n']:,}", f"of them are {hero['s']}s")]:
    d.text((L, y), v, font=num, fill=INK); d.text((L + d.textlength(v, font=num) + 14 * K, y + 24 * K), t, font=lab, fill=INK2); y += 62 * K
d.text((L, H - 56 * K), "By Ryan Ghods  ·  data from the OpenSea API", font=font("mono.ttf", 15), fill=INK2)
# slab grid from the sprite, distinct cards only
sp = S["sprite"]; per = sp["cols"] * sp["rows"]; sheets = {}
seen, picks = set(), []
for c in S["top"]:
    if c["i"] < 0 or c["v"] is None or (c["name"], c["v"]) in seen: continue
    seen.add((c["name"], c["v"])); picks.append(c)
    if len(picks) == 6: break
cw, ch, gap = 150 * K, 210 * K, 16 * K
x0, y0 = W - 40 * K - 3 * cw - 2 * gap, (H - 2 * ch - gap) // 2
for k, c in enumerate(picks):
    f = sp["files"][c["i"] // per]; sheets.setdefault(f, Image.open(os.path.join(SITE, f)).convert("RGBA"))
    j = c["i"] % per; cell = sheets[f].crop(((j % sp["cols"]) * sp["w"], (j // sp["cols"]) * sp["h"], (j % sp["cols"] + 1) * sp["w"], (j // sp["cols"] + 1) * sp["h"]))
    x, yy = x0 + (k % 3) * (cw + gap), y0 + (k // 3) * (ch + gap)
    frame = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=12 * K, fill=(30, 29, 34, 255), outline=(58, 56, 64, 255), width=K)
    frame.alpha_composite(cell.resize((cw - 4 * K, ch - 4 * K), Image.LANCZOS), (2 * K, 2 * K))
    img.paste(frame, (x, yy), frame)
img.resize((1200, 630), Image.LANCZOS).save(os.path.join(SITE, "og.png"), optimize=True)
print("og.png", os.path.getsize(os.path.join(SITE, "og.png")))
