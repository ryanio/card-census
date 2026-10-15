"""Build site/ from data/crawl.json: one page with the summary inline, plus card-photo sprite sheets."""
import hashlib, json, math, os, re, sys
from PIL import Image, ImageStat
ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); os.makedirs(SITE, exist_ok=True)
HIRES = os.path.join(ROOT, "data", "hires"); os.makedirs(os.path.join(SITE, "w"), exist_ok=True)
CACHE = os.path.join(ROOT, "data", "img2"); W, H = int(os.environ.get("CELL_W", 200)), int(os.environ.get("CELL_H", 280))
COLS, ROWS = 10, 6
cr = json.load(open(os.path.join(ROOT, "data", "crawl.json")))

def num(g):
    try: return float(g)
    except (TypeError, ValueError): return None
def grades(pairs):
    out = sorted([[g, c] for g, c in (pairs or []) if num(g) is not None], key=lambda x: num(x[0]))
    return out
def tens(pairs): return sum(c for g, c in (pairs or []) if (num(g) or 0) >= 10)
def tot(pairs): return sum(c for _, c in (pairs or []))
def own(f, typ, name):
    return next((c for v, c in (f or {}).get(typ, []) if v == name), 0)
def best_total(f, skip=None):
    # the facet named by the filter ignores that filter, so it can't bound the filtered total
    return max([tot(v) for k, v in (f or {}).items() if k != skip] or [0])
def top(pairs, k, minc=1): return [[v, c] for v, c in (pairs or []) if c >= minc][:k]
def langs(pairs):
    fix = {"Engllish": "English"}; acc = {}
    for v, c in pairs or []:
        v = fix.get(v, v)
        if v.lower() in ("psa", "europe"): continue
        acc[v] = acc.get(v, 0) + c
    return sorted(acc.items(), key=lambda x: -x[1])

# sprites: one cell per unique card photo
def img_path(u):
    if not u: return None
    p = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest() + ".png")
    return p if os.path.exists(p) else None
cells, index = [], {}
def cell(n):
    u = n.get("display_image_url") or n.get("image_url"); p = img_path(u)
    if not p: return -1
    if u not in index: index[u] = len(cells); cells.append(p)
    return index[u]
GRADE = re.compile(r"\b(PSA|CGC|BGS|SGC|TAG|Beckett|ACE)\s?(10|[1-9](?:\.5)?)(\s?(?:Pristine|Black Label|Gem Mint|Perfect|Auto(?:graph)?))?(?![\d.])", re.I)
def smart_word(w):
    if any(ch.isdigit() for ch in w) or "." in w or "/" in w: return w.lower() if w.isupper() and not ("." in w or "/" in w) else w
    return w.capitalize() if w.isupper() and len(w) > 2 else w
def clean(name):
    n = (name or "").split(" | ")[0].strip()
    chip = ""
    g = GRADE.search(n)
    if g:
        who = "Beckett" if g.group(1).lower() == "beckett" else g.group(1).upper()
        chip = f"{who} {g.group(2)}" + (f" {g.group(3).strip().title()}" if g.group(3) else "")
        n = n[:g.start()] + n[g.end():]
    n = re.sub(r"\s+-\s+|\s+-$|^-\s+", " ", n); n = re.sub(r"\s{2,}", " ", n).strip(" -,")
    letters = [c for c in n if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7: n = " ".join(smart_word(w) for w in n.split(" "))
    return n, chip
def year_of(name):
    m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", name or "")
    return int(m.group(1)) if m else None
def copy(n):
    v = n.get("estimated_value_usd"); lp = n.get("best_listing_price")
    t, chip = clean(n.get("name"))
    u = n.get("display_image_url") or n.get("image_url") or ""
    return {"i": cell(n), "v": round(float(v)) if v not in (None, "", "None") else None, "name": n.get("name") or "", "t": t, "g": chip, "y": year_of(n.get("name")),
            "u": u, "url": n.get("opensea_url") or "", "c": n.get("collection") or ""}

def dedupe(cs):
    seen, out = set(), []
    for c in cs:
        k = (re.sub(r"[^a-z0-9]", "", (c["t"] + c["g"]).lower()), c["v"])
        if k in seen: continue
        seen.add(k); out.append(c)
    return out

A = cr["all"]
pt = dict(A.get("product_type", []))
S = {"v": re.sub(r"[^0-9]", "", cr["at"])[:14], "at": cr["at"], "group": cr["group"], "n": best_total(A), "graded": pt.get("Graded Card", 0), "raw": pt.get("Raw Card", 0), "sealed": pt.get("Sealed Product", 0),
     "grade": grades(A.get("grade")), "lang": langs(A.get("language")), "years": sorted([[int(y), c] for y, c in A.get("year", []) if str(y).isdigit()]),
     "graders": [], "franchises": [], "subjects": [], "sets": [], "top": []}
for g, f in cr["grader"].items():
    if not f: continue
    gd = grades(f.get("grade")); S["graders"].append({"g": g, "n": tot(gd), "ten": tens(gd), "dist": gd, "fr": top(f.get("franchise"), 4)})
S["graders"].sort(key=lambda x: -x["n"])
for fname, f in cr["franchise"].items():
    if not f: continue
    fpt = dict(f.get("product_type", []))
    psa, cgc = cr["fg"].get(f"{fname}|PSA") or {}, cr["fg"].get(f"{fname}|CGC") or {}
    S["franchises"].append({"f": fname, "n": own(f, "franchise", fname) or best_total(f, "franchise"), "graded": fpt.get("Graded Card", 0), "raw": fpt.get("Raw Card", 0), "sealed": fpt.get("Sealed Product", 0),
        "lang": langs(f.get("language"))[:6], "years": sorted([[int(y), c] for y, c in f.get("year", []) if str(y).isdigit()]),
        "grade": grades(f.get("grade")), "psa": [tens(psa.get("grade")), tot(psa.get("grade"))], "cgc": [tens(cgc.get("grade")), tot(cgc.get("grade"))],
        "subjects": [v for v, _ in f.get("subject", [])[:12]]})
S["franchises"].sort(key=lambda x: -x["n"])
for s in cr["subjects"]:
    f = cr["subject"].get(s)
    if not f: continue
    psa, cgc = cr["subject_grader"].get(f"{s}|PSA") or {}, cr["subject_grader"].get(f"{s}|CGC") or {}
    gd = grades(f.get("grade"))
    S["subjects"].append({"s": s, "f": (f.get("franchise") or [["", 0]])[0][0], "n": max(own(f, "subject", s), best_total(f, "subject")), "graded": tot(gd), "grade": gd,
        "psa": grades(psa.get("grade")), "cgc": grades(cgc.get("grade")), "lang": langs(f.get("language"))[:5],
        "years": sorted([[int(y), c] for y, c in f.get("year", []) if str(y).isdigit()], key=lambda x: -x[1])[:8],
        "sets": top(f.get("set"), 6), "graders": top(f.get("grader"), 5), "copies": dedupe([copy(n) for n in (cr["copies"].get(s) or [])])})
S["subjects"].sort(key=lambda x: -x["n"])
for x in cr["sets"]:
    f = cr["set"].get(x)
    if not f: continue
    gd = grades(f.get("grade"))
    S["sets"].append({"x": x, "n": tot(gd), "ten": tens(gd), "f": (f.get("franchise") or [["", 0]])[0][0], "y": (f.get("year") or [["", 0]])[0][0]})
S["sets"].sort(key=lambda x: -x["n"])
S["top"] = dedupe([copy(n) for n in cr["top"]])
# issuers: the platforms that vault and tokenize the cards, with chain-specific collections merged (Beezie - Flow, Beezie - Base)
iss = {}
for it in cr.get("issuers") or []:
    f = it.get("facets") or {}; pt = dict(f.get("product_type", []))
    name = re.sub(r"\.io$", "", (it.get("name") or it["slug"]).split(" - ")[0].strip())
    x = iss.setdefault(name, {"name": name, "slugs": [], "n": 0, "graded": 0, "raw": 0, "sealed": 0, "fr": {}})
    x["slugs"].append(it["slug"]); x["n"] += tot(f.get("product_type")); x["graded"] += pt.get("Graded Card", 0); x["raw"] += pt.get("Raw Card", 0); x["sealed"] += pt.get("Sealed Product", 0)
    for v, c in f.get("franchise", []): x["fr"][v] = x["fr"].get(v, 0) + c
S["issuers"] = sorted([dict(x, fr=sorted(x["fr"].items(), key=lambda kv: -kv[1])[:4]) for x in iss.values() if x["n"]], key=lambda x: -x["n"])
# franchise champions: the most valuable copy found for each franchise with at least 2,000 cards
S["champs"] = []
for fr in S["franchises"]:
    if fr["n"] < 2000: continue
    best = max((c for s in S["subjects"] if s["f"] == fr["f"] for c in s["copies"] if c["v"] is not None), key=lambda c: c["v"], default=None)
    if best: S["champs"].append({"f": fr["f"], "c": best})
# vintage: share of all dated cards printed before 2004, and among the most valuable graded cards
dated = [c for c in S["top"] if c["y"]]
S["vintage"] = {"cut": 2004, "all": sum(c for y, c in S["years"] if y < 2004), "dated": sum(c for _, c in S["years"]),
                "top_n": len(dated), "top_old": sum(1 for c in dated if c["y"] < 2004)}
# high-res, background-trimmed images for the cards shown large
def hires_file(c, name, FW=600, FH=840):
    u = c.get("u")
    if not u: return None
    h = hashlib.sha1(u.encode()).hexdigest() + ".png"
    p = os.path.join(ROOT, "data", "hires_big", h) if FW > 600 and os.path.exists(os.path.join(ROOT, "data", "hires_big", h)) else os.path.join(HIRES, h)
    if not os.path.exists(p): return None
    im = Image.open(p).convert("RGBA")
    sc = min(FW / im.width, FH / im.height); im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
    cell = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); cell.alpha_composite(im, ((FW - im.width) // 2, (FH - im.height) // 2))
    cell.save(os.path.join(SITE, "w", name), "WEBP", quality=82, method=6); return "w/" + name
for k, c in enumerate(S["top"][:16]): c["w"] = hires_file(c, f"t{k}.webp", *((900, 1260) if k == 0 else (800, 1120) if k < 4 else (600, 840)))
for k, ch in enumerate(S["champs"]): ch["c"]["w"] = hires_file(ch["c"], f"f{k}.webp")
S["sealed"] = dedupe([copy(n) for n in cr.get("sealed", [])])
S["sealed_n"] = S["sealed_total"] = dict(A.get("product_type", [])).get("Sealed Product", 0)
for k, c in enumerate(S["sealed"][:10]): c["w"] = hires_file(c, f"s{k}.webp", *((960, 960) if k < 2 else (600, 600)))

# cover map: territories in the order they run along the curve (franchises by size, each one's long tail, then its big cards),
# with small photo tiles; tile captions go to map.json, which the page loads after first paint
MINI, MW, MH, MCOLS, MBIG = os.path.join(ROOT, "data", "tiles"), 40, 56, 32, 1500
mcells, mindex, mmeta, murls, mvals = [], {}, [], [], []
def short(u): return (u or "").replace("https://i2c.seadn.io/", "~i/").replace("https://opensea.io/assets/", "~a/")
def mcell(n):
    u = n.get("display_image_url") or n.get("image_url")
    p = u and os.path.join(MINI, hashlib.sha1(u.encode()).hexdigest() + ".png")
    if not p or not os.path.exists(p): return -1
    if u not in mindex:
        mindex[u] = len(mcells); mcells.append(p); murls.append(u)
        t, chip = clean(n.get("name")); v = n.get("estimated_value_usd"); v = round(float(v)) if v not in (None, "", "None") else None
        box = [float(x) for x in open(p + ".box").read().split()] if os.path.exists(p + ".box") else [0, 0, 1, 1]
        mmeta.append([t, chip, v, short(u), short(n.get("opensea_url")), box]); mvals.append(v or 0)
    return mindex[u]
def tiles_of(ns): return list(dict.fromkeys(i for i in (mcell(n) for n in ns) if i >= 0))
MP = cr.get("map") or {}
groups, by_f = [], {}
for s in S["subjects"]: by_f.setdefault(s["f"], []).append(s)
for fr in S["franchises"]:
    f, named = fr["f"], []
    big = [s for s in by_f.get(f, []) if s["n"] >= MBIG]
    for s in big:
        t = tiles_of((MP.get("subject", {}).get(s["s"]) or []) + (cr["copies"].get(s["s"]) or []))
        if t: named.append({"k": "s", "s": s["s"], "f": f, "n": s["n"], "ten": tens(s["grade"]), "tiles": t})
    names = [s["s"].lower() for s in big]
    pool = (MP.get("franchise", {}).get(f) or []) + [n for s in by_f.get(f, []) if s["n"] < MBIG for n in (cr["copies"].get(s["s"]) or [])]
    rest = [n for n in pool if not any(x in (n.get("name") or "").lower() for x in names)] or pool
    # the long tail first, then the big cards, which puts Pokemon's big cards near the middle of the line: the top of the map
    groups.append({"k": "f", "f": f, "n": max(0, fr["n"] - sum(g["n"] for g in named)), "total": fr["n"], "ten": tens(fr["grade"]), "tiles": tiles_of(rest)})
    groups += named
# the most valuable cards get a bigger photo, which the page draws across 2x2 to 4x4 cells
MIDI, BW, BH, BCOLS = os.path.join(ROOT, "data", "midi"), 120, 168, 10
def has_big(t):
    p = os.path.join(MIDI, hashlib.sha1(murls[t].encode()).hexdigest() + ".png")
    if not (mvals[t] > 0 and os.path.exists(p)): return False
    # skip photos where the slab is lost in a dark studio backdrop: most of the tile should have something in it
    return ImageStat.Stat(Image.open(p).convert("L").point(lambda v: 255 if v > 45 else 0)).mean[0] / 255 > 0.5
bset = sorted({t for g in groups for t in g["tiles"] if has_big(t)}, key=lambda t: -mvals[t])[:90]
for f in {g["f"] for g in groups}:  # and each franchise's priciest card, wherever it ranks overall
    best = max((t for g in groups if g["f"] == f for t in g["tiles"] if has_big(t)), key=lambda t: mvals[t], default=None)
    if best is not None and best not in bset: bset.append(best)
bindex = {t: k for k, t in enumerate(bset)}
for g in groups: g["big"] = sorted([[t, bindex[t], mvals[t]] for t in g["tiles"] if t in bindex], key=lambda c: -c[2])
bsheet = Image.new("RGB", (BCOLS * BW, max(1, math.ceil(len(bset) / BCOLS)) * BH), (27, 26, 32))
for k, t in enumerate(bset): bsheet.paste(Image.open(os.path.join(MIDI, hashlib.sha1(murls[t].encode()).hexdigest() + ".png")).convert("RGB"), ((k % BCOLS) * BW, (k // BCOLS) * BH))
bsheet.save(os.path.join(SITE, "mb.webp"), "WEBP", quality=78, method=6)
mper, mfiles = MCOLS * MCOLS, []
for k in range(math.ceil(len(mcells) / mper)):
    chunk = mcells[k * mper:(k + 1) * mper]
    sheet = Image.new("RGB", (MCOLS * MW, math.ceil(len(chunk) / MCOLS) * MH), (27, 26, 32))
    for j, p in enumerate(chunk): sheet.paste(Image.open(p).convert("RGB"), ((j % MCOLS) * MW, (j // MCOLS) * MH))
    fn = f"m{k}.webp"; sheet.save(os.path.join(SITE, fn), "WEBP", quality=74, method=6); mfiles.append(fn)
S["map"] = {"w": MW, "h": MH, "cols": MCOLS, "per": mper, "files": mfiles, "groups": groups, "big": {"w": BW, "h": BH, "cols": BCOLS, "file": "mb.webp"},
            "off": S["n"] - sum(fr["n"] for fr in S["franchises"])}
json.dump({"m": mmeta}, open(os.path.join(SITE, "map.json"), "w"), separators=(",", ":"))

# sprite sheets for the card thumbnails, which are drawn at 26 to 34px, so cells about twice that are enough
SW, SH = 72, 100
per = COLS * ROWS; files = []
for k in range(max(1, math.ceil(len(cells) / per))):
    sheet = Image.new("RGBA", (COLS * SW, ROWS * SH), (0, 0, 0, 0))
    for j, p in enumerate(cells[k * per:(k + 1) * per]):
        sheet.alpha_composite(Image.open(p).convert("RGBA").resize((SW, SH), Image.LANCZOS), ((j % COLS) * SW, (j // COLS) * SH))
    fn = f"c{k}.webp"; sheet.save(os.path.join(SITE, fn), "WEBP", quality=78, method=6); files.append(fn)
S["sprite"] = {"cols": COLS, "rows": ROWS, "w": SW, "h": SH, "files": files}

tpl = open(os.path.join(ROOT, "scripts", "template.html")).read()
# the page gets a slimmer summary: each copy drops its raw name and the common URL prefixes, which the page restores
slim = lambda c: {k: (short(v) if k in ("u", "url") else v) for k, v in c.items() if k != "name"}
PS = dict(S, subjects=[dict(s, copies=[slim(c) for c in s["copies"]]) for s in S["subjects"]])
page = tpl.replace("/*__SUMMARY__*/", json.dumps(PS, separators=(",", ":")).replace("</", "<\\/"))
SITE_URL = os.environ.get("SITE_URL", "https://ryanio.github.io/card-census/")
GA_ID = os.environ.get("GA_ID", "").strip()
head_end = page.index("</style>") + len("</style>")
head, body = page[:head_end], page[head_end:]
head = head.replace('<meta charset="utf-8">\n', "")
desc = f"{S['n']:,} tokenized trading cards on OpenSea, counted by card, grade and grader. An onchain pop report."
ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>\n<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{GA_ID}");</script>\n' if GA_ID else "")
meta = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Card Census">
<meta property="og:locale" content="en_US">
<meta property="og:image:alt" content="A map of every trading card onchain, made of the cards' own photos">
<meta name="twitter:image:alt" content="A map of every trading card onchain, made of the cards' own photos">
<meta name="theme-color" content="#0B0A0C">
<meta name="author" content="Ryan Ghods">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:title" content="Every card onchain, counted: the Card Census">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Every card onchain, counted: the Card Census">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE_URL}og.png">
{ga}<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect x='22' y='8' width='56' height='84' rx='8' fill='%23E2483D'/%3E%3C/svg%3E">
"""
open(os.path.join(SITE, "index.html"), "w").write("<!doctype html>\n<html lang=\"en\">\n<head>\n" + meta + head + "\n</head>\n<body>" + body + "\n</body>\n</html>\n")
json.dump(S, open(os.path.join(ROOT, "data", "summary.json"), "w"))
print(f"items={S['n']} subjects={len(S['subjects'])} sets={len(S['sets'])} photos={len(cells)} sheets={len(files)}", file=sys.stderr)
