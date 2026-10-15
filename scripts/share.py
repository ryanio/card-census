"""Share pages and SEO for the built site.

For each highlight (one per chapter) and the most common cards, write a 1200x630 preview image and a small
page at s/<id>/ whose Open Graph tags carry that image, then send readers on to the matching anchor.
Also fills the highlights strip, the static headline and dek, JSON-LD and sitemap.xml in site/.
"""
import hashlib, html, json, math, os, re, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); FONTS = os.path.join(ROOT, "data", "fonts"); HIRES = os.path.join(ROOT, "data", "hires")
SITE_URL = os.environ.get("SITE_URL", "https://ryanio.github.io/card-census/")
page = open(os.path.join(SITE, "index.html")).read()
S = json.load(open(os.path.join(ROOT, "data", "summary.json")))
SUB = S["subjects"]; os.makedirs(os.path.join(SITE, "s"), exist_ok=True)

num = lambda g: float(g) if re.fullmatch(r"[\d.]+", str(g)) else None
tot = lambda pairs: sum(c for _, c in pairs)
tens = lambda pairs: sum(c for g, c in pairs if (num(g) or 0) >= 10)
psa10 = lambda s: sum(c for g, c in s["psa"] if num(g) == 10)
lang = lambda pairs, name: (dict(pairs).get(name, 0) / tot(pairs)) if tot(pairs) else 0
best = lambda s: max((c for c in s["copies"] if c["v"] is not None), key=lambda c: c["v"], default=None)
WORDS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
def one_in(share):
    if 0.45 <= share <= 0.55: return "half of"
    n = round(1 / share) if share else 0
    return f"one in {WORDS[n]}" if 2 <= n <= 10 and abs(1 / n - share) / share < 0.15 else f"{round(share * 100)}% of"
money = lambda v: f"${v / 1e6:.1f} million" if v >= 1e6 else f"${round(v / 1000) * 1000:,.0f}"
slug = lambda name: "card-" + re.sub(r"[^\w]+", "-", name.lower()).strip("-")

graded = tot(S["grade"]); ten_share = tens(S["grade"]) / graded if graded else 0
G = {g["g"]: g for g in S["graders"]}
gem = lambda g: g["ten"] / g["n"] if g and g["n"] else 0
by_n = sorted(SUB, key=lambda s: -s["n"]); sub = {s["s"]: s for s in SUB}
zard, pika = sub.get("Charizard"), sub.get("Pikachu")
ja_all = lang(S["lang"], "Japanese"); FR = {f["f"]: f for f in S["franchises"]}
V = S["vintage"]; v_share = V["all"] / V["dated"] if V["dated"] else 0
top = [c for c in S["top"] if c["v"] is not None]

H = []
H.append({"id": "tens", "anchor": "tens", "kicker": "Grades", "big": f"{round(ten_share * 100)}%",
          "title": f"{one_in(ten_share).capitalize()} graded cards onchain are 10s",
          "sub": f"PSA {round(gem(G.get('PSA')) * 100)}% · CGC {round(gem(G.get('CGC')) * 100)}%" if G.get("PSA") and G.get("CGC") else "",
          "text": f"{one_in(ten_share).capitalize()} graded trading cards onchain are 10s." + (f" PSA: {round(gem(G['PSA']) * 100)}%. CGC: {round(gem(G['CGC']) * 100)}%." if G.get("PSA") and G.get("CGC") else ""),
          "cards": [c for c in top if c.get("g") == "PSA 10"][:3]})
if zard and pika and pika["n"] > zard["n"]:
    H.append({"id": "cards", "anchor": "cards", "kicker": "Most common", "big": f"{pika['n']:,}", "title": "There are more Pikachus onchain than Charizards",
              "sub": f"{pika['n']:,} to {zard['n']:,}", "text": f"There are more Pikachus onchain than Charizards: {pika['n']:,} to {zard['n']:,}.", "cards": [x for x in (best(pika), best(zard)) if x]})
else:
    t = by_n[0]
    H.append({"id": "cards", "anchor": "cards", "kicker": "Most common", "big": f"{t['n']:,}", "title": f"{t['s']} is the most common card onchain",
              "sub": f"{t['n']:,} cards", "text": f"{t['s']} is the most common trading card onchain, with {t['n']:,} cards.", "cards": [x for x in (best(t),) if x]})
ja_wins = [s for s in by_n[:60] if lang(s["lang"], "Japanese") > lang(s["lang"], "English")]
p_ja = lang(FR["Pokemon"]["lang"], "Japanese") if "Pokemon" in FR else 0
o_ja = lang(FR["One Piece"]["lang"], "Japanese") if "One Piece" in FR else 0
H.append({"id": "japanese", "anchor": "japanese", "kicker": "Language", "big": f"{round(ja_all * 100)}%",
          "title": f"{one_in(ja_all).capitalize()} cards onchain {'is' if one_in(ja_all).startswith('one in') else 'are'} Japanese",
          "sub": f"{round(p_ja * 100)}% of Pokemon, {round(o_ja * 100)}% of One Piece" if p_ja else "",
          "text": f"{one_in(ja_all).capitalize()} tokenized trading cards on OpenSea {'is' if one_in(ja_all).startswith('one in') else 'are'} Japanese.",
          "cards": [x for x in (best(s) for s in ja_wins[:6]) if x and "japanese" in (x["t"] or "").lower()][:3] or [x for x in (best(s) for s in ja_wins[:3]) if x]})
if V["top_n"]:
    H.append({"id": "years", "anchor": "years", "kicker": "Vintage", "big": f"{round(v_share * 100)}%",
              "title": f"Old cards are {round(v_share * 100)}% of what's onchain and {one_in(V['top_old'] / V['top_n']).replace(' of', '')} of the most valuable",
              "sub": f"{V['top_old']} of the {V['top_n']} most valuable graded cards were printed before {V['cut']}",
              "text": f"Cards printed before {V['cut']} are {round(v_share * 100)}% of trading cards onchain, and {V['top_old']} of the {V['top_n']} most valuable.",
              "cards": [c for c in top if c.get("y") and c["y"] < V["cut"]][1:4]})
if top:
    h1 = top[0]
    H.append({"id": "grails", "anchor": "lot-1", "kicker": "Lot 01", "big": f"${h1['v'] / 1000:.0f}K" if h1["v"] < 1e6 else f"${h1['v'] / 1e6:.1f}M",
              "title": f"The most valuable card onchain is worth about {money(h1['v'])}", "sub": f"{h1['t']}, {h1['g']}" if h1.get("g") else h1["t"],
              "text": f"The most valuable trading card onchain is worth about {money(h1['v'])}: {h1['t']}{', ' + h1['g'] if h1.get('g') else ''}.", "cards": [h1], "solo": True})
IS = S.get("issuers") or []
if len(IS) >= 2:
    i0 = IS[0]
    H.append({"id": "vaults", "anchor": "vaults", "kicker": "Who vaults them", "big": f"{round(i0['n'] / S['n'] * 100)}%",
              "title": f"{i0['name']} vaults {round(i0['n'] / S['n'] * 100)}% of the cards onchain",
              "sub": " · ".join(f"{x['name']} {round(x['n'] / S['n'] * 100)}%" for x in IS[1:4]),
              "text": f"{i0['name']} vaults {round(i0['n'] / S['n'] * 100)}% of the trading cards onchain. " + ", ".join(f"{x['name']}: {round(x['n'] / S['n'] * 100)}%" for x in IS[1:4]) + ".",
              "bars": [(x["name"], x["n"] / i0["n"], f"{x['n']:,}") for x in IS[:5]]})
most10 = max(SUB, key=lambda s: tens(s["grade"]))
if most10 is not by_n[0]:
    t0 = by_n[0]
    H.append({"id": "most-tens", "anchor": slug(most10["s"]), "kicker": "Most 10s", "big": f"{tens(most10['grade']):,}", "only": True,
              "title": f"{most10['s']} has more 10s onchain than any other card",
              "sub": f"{tens(most10['grade']):,} of {most10['n']:,} cards graded 10 or higher, against {tens(t0['grade']):,} for {t0['s']}",
              "text": f"{most10['s']} has more 10s onchain than any other card: {tens(most10['grade']):,} of {most10['n']:,} cards are graded 10 or higher.",
              "cards": [x for x in (best(most10),) if x], "solo": True})
FRS = sorted(S["franchises"], key=lambda f: -f["n"]); on_map = S["n"] - (S.get("map") or {}).get("off", 0)
if FRS and os.path.exists(os.path.join(ROOT, "data", "og_map.png")):
    f0 = FRS[0]
    H.append({"id": "map", "anchor": "top", "kicker": "The map", "big": f"{round(f0['n'] / S['n'] * 100)}%", "only": True,
              "title": f"{f0['f']} is {round(f0['n'] / S['n'] * 100)}% of every card onchain",
              "sub": " · ".join(f"{f['f']} {round(f['n'] / S['n'] * 100)}%" for f in FRS[1:4]),
              "text": f"A map of {S['n']:,} trading cards onchain, made of the cards themselves. {f0['f']} is {round(f0['n'] / S['n'] * 100)}% of it.",
              "img": os.path.join(ROOT, "data", "og_map.png")})
ENT = []
for s in by_n[:40]:
    b = best(s)
    ENT.append({"id": slug(s["s"]), "anchor": slug(s["s"]), "kicker": s["f"] or "Trading cards", "title": f"{s['n']:,} {s['s']} cards are onchain",
                "sub": f"{tens(s['grade']):,} graded 10 or higher" + (f", {psa10(s):,} of them PSA 10s" if psa10(s) else ""),
                "text": f"{s['n']:,} {s['s']} cards are onchain. {tens(s['grade']):,} are graded 10 or higher" + (f", {psa10(s):,} of them PSA 10s." if psa10(s) else "."),
                "cards": [x for x in (best(s),) if x] or [c for c in s["copies"] if c.get("u")][:1], "solo": True})

# ---- images ----
K = 2; W, Hh = 1200 * K, 630 * K
BG, INK, INK2, PINK = (11, 10, 12), (245, 244, 246), (170, 168, 176), (255, 111, 163)
HOLO = [(255, 77, 141), (255, 181, 71), (255, 228, 94), (77, 224, 201), (61, 169, 255), (155, 107, 255)]
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size * K)
    if var: f.set_variation_by_name(var)
    return f
def photo(c):
    if c.get("w") and os.path.exists(os.path.join(SITE, c["w"])): return Image.open(os.path.join(SITE, c["w"])).convert("RGBA")
    p = os.path.join(HIRES, hashlib.sha1(c["u"].encode()).hexdigest() + ".png") if c.get("u") else None
    return Image.open(p).convert("RGBA") if p and os.path.exists(p) else None
def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])
def render(h, path):
    img = Image.new("RGB", (W, Hh), BG); d = ImageDraw.Draw(img)
    ims = [p for p in (photo(c) for c in h.get("cards", [])) if p][:(1 if h.get("solo") else 2)]
    if h.get("img"):
        m = Image.open(h["img"]).convert("RGB"); sc = min(520 * K / m.width, 570 * K / m.height); m = m.resize((int(m.width * sc), int(m.height * sc)), Image.LANCZOS)
        img.paste(m, (1180 * K - m.width, (Hh - m.height) // 2))
    if h.get("bars"):
        fb, fs2 = font("bsd.ttf", 30, b"ExtraBold"), font("mono.ttf", 15)
        x0, x1, y = 660 * K, 1150 * K, 120 * K
        for name, frac, label in h["bars"]:
            d.text((x0, y), name.upper(), font=fb, fill=INK); d.text((x1, y + 8 * K), label, font=fs2, fill=INK2, anchor="ra")
            d.rounded_rectangle([x0, y + 44 * K, x0 + max(8 * K, int((x1 - x0) * frac)), y + 62 * K], radius=4 * K, fill=PINK if name == h["bars"][0][0] else (90, 88, 98))
            y += 88 * K
    if ims:
        x0, x1, y0, y1 = 640 * K, 1160 * K, 40 * K, 590 * K
        n = len(ims); gap = 18 * K
        cw = min((x1 - x0 - gap * (n - 1)) / n, (y1 - y0) * 5 / 7); ch = cw * 7 / 5
        ox = x1 - (n * cw + (n - 1) * gap); oy = y0 + ((y1 - y0) - ch) / 2
        for k, im in enumerate(ims):
            case = Image.new("RGBA", (int(cw), int(ch)), (0, 0, 0, 0)); cd = ImageDraw.Draw(case)
            cd.rounded_rectangle([0, 0, int(cw) - 1, int(ch) - 1], radius=14 * K, fill=(33, 32, 38, 255), outline=(58, 56, 64, 255), width=K)
            sc = min(cw * 0.86 / im.width, ch * 0.88 / im.height); fit = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
            case.alpha_composite(fit, ((int(cw) - fit.width) // 2, (int(ch) - fit.height) // 2))
            img.paste(case, (int(ox + k * (cw + gap)), int(oy)), case)
    L, width = 64 * K, 540 * K
    d.text((L, 56 * K), h["kicker"].upper(), font=font("mono.ttf", 18), fill=PINK)
    size = 76
    while size > 40:
        f = font("bsd.ttf", size, b"ExtraBold"); lines = wrap(d, h["title"], f, width)
        if len(lines) <= 4: break
        size -= 4
    y = 92 * K
    for ln in lines: d.text((L, y), ln, font=f, fill=INK); y += int(size * 0.98 * K)
    for i, c in enumerate(HOLO): d.rectangle([L + i * 30 * K, y + 18 * K, L + (i + 1) * 30 * K, y + 24 * K], fill=c)
    if h.get("sub"):
        fs = font("ps.ttf", 22, b"Medium")
        for k, ln in enumerate(wrap(d, h["sub"], fs, width)[:3]): d.text((L, y + 44 * K + k * 32 * K), ln, font=fs, fill=INK2)
    d.text((L, Hh - 58 * K), "CARD CENSUS  ·  ryanio.github.io/card-census", font=font("mono.ttf", 15), fill=INK2)
    img.resize((1200, 630), Image.LANCZOS).save(path, optimize=True)

esc = lambda t: html.escape(t, quote=True)
def share_page(h):
    url, img, dest = f"{SITE_URL}s/{h['id']}/", f"{SITE_URL}s/{h['id']}.png", f"{SITE_URL}#{h['anchor']}"
    t, dsc = esc(h["title"]), esc(h["text"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t} · Card Census</title>
<meta name="description" content="{dsc}">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Card Census">
<meta property="og:title" content="{t}"><meta property="og:description" content="{dsc}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{t}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{t}"><meta name="twitter:description" content="{dsc}"><meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0; url={dest}">
<script>location.replace({json.dumps(dest)})</script>
</head><body style="font-family:system-ui;background:#0B0A0C;color:#F5F4F6"><p><a style="color:#fff" href="{dest}">{t}</a></p></body></html>
"""
for h in H + ENT:
    render(h, os.path.join(SITE, "s", f"{h['id']}.png"))
    os.makedirs(os.path.join(SITE, "s", h["id"]), exist_ok=True)
    open(os.path.join(SITE, "s", h["id"], "index.html"), "w").write(share_page(h))

# ---- page: highlights, share map, static headline and dek, JSON-LD, sitemap ----
light = [{k: h[k] for k in ("id", "anchor", "kicker", "big", "title", "text")} for h in H if not h.get("only")]
page = page.replace("/*__HIGHLIGHTS__*/", json.dumps({"h": light, "c": {e["anchor"]: e["id"] for e in ENT}}, separators=(",", ":")).replace("</", "<\\/"))
hero = zard or by_n[0]
h1 = "Every card onchain, counted"
dek = f"How many {hero['s']}s are there? {hero['n']:,}. Which grader hands out the most 10s? I counted all {S['n']:,} tokenized trading cards on OpenSea, by card, grade and grader, the way collectors read a pop report."
page = page.replace('<h1 id="h1"></h1>', f'<h1 id="h1">{esc(h1)}</h1>').replace('<p class="dek" id="dek"></p>', f'<p class="dek" id="dek">{esc(dek)}</p>')
ld = [{"@context": "https://schema.org", "@type": "Article", "headline": h1 + ": the Card Census", "description": dek, "image": [SITE_URL + "og.png"],
       "author": {"@type": "Person", "name": "Ryan Ghods", "url": "https://github.com/ryanio"}, "datePublished": "2026-10-13", "dateModified": S["at"][:10], "mainEntityOfPage": SITE_URL},
      {"@context": "https://schema.org", "@type": "Dataset", "name": "Card Census", "description": f"Tokenized trading cards on OpenSea counted by card, grade and grader: {S['n']:,} cards, {len(SUB)} cards with their own pop report.",
       "url": SITE_URL, "creator": {"@type": "Person", "name": "Ryan Ghods"}, "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
       "keywords": ["trading cards", "pop report", "PSA", "CGC", "Pokemon", "OpenSea", "onchain"], "dateModified": S["at"][:10], "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": "https://raw.githubusercontent.com/ryanio/card-census/main/data/cards.csv"}, {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": "https://raw.githubusercontent.com/ryanio/card-census/main/data/grades.csv"}]}]
page = page.replace("</head>", '<script type="application/ld+json">' + json.dumps(ld, separators=(",", ":")) + "</script>\n</head>", 1)
open(os.path.join(SITE, "index.html"), "w").write(page)
open(os.path.join(SITE, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE_URL}</loc><lastmod>{S["at"][:10]}</lastmod><changefreq>daily</changefreq></url></urlset>\n')
print(f"share pages: {len(H)} highlights + {len(ENT)} cards")
