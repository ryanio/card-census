"""Build site/ from data/crawl.json: one page with the summary inline, plus card-photo sprite sheets."""
import hashlib, json, math, os, sys
from PIL import Image
ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); os.makedirs(SITE, exist_ok=True)
CACHE = os.path.join(ROOT, "data", "img"); W, H = int(os.environ.get("CELL_W", 200)), int(os.environ.get("CELL_H", 280))
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
def copy(n):
    v = n.get("estimated_value_usd"); lp = n.get("best_listing_price")
    return {"i": cell(n), "v": round(float(v)) if v not in (None, "", "None") else None, "name": n.get("name") or "", "url": n.get("opensea_url") or "", "c": n.get("collection") or ""}

def dedupe(cs):
    seen, out = set(), []
    for c in cs:
        k = (c["name"], c["v"])
        if k in seen: continue
        seen.add(k); out.append(c)
    return out

A = cr["all"]
pt = dict(A.get("product_type", []))
S = {"at": cr["at"], "group": cr["group"], "n": best_total(A), "graded": pt.get("Graded Card", 0), "raw": pt.get("Raw Card", 0), "sealed": pt.get("Sealed Product", 0),
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
S["top"] = [copy(n) for n in cr["top"]]

# sprite sheets
per = COLS * ROWS; files = []
for k in range(max(1, math.ceil(len(cells) / per))):
    sheet = Image.new("RGBA", (COLS * W, ROWS * H), (0, 0, 0, 0))
    for j, p in enumerate(cells[k * per:(k + 1) * per]):
        sheet.alpha_composite(Image.open(p).convert("RGBA").resize((W, H)), ((j % COLS) * W, (j // COLS) * H))
    fn = f"c{k}.webp"; sheet.save(os.path.join(SITE, fn), "WEBP", quality=78, method=6); files.append(fn)
S["sprite"] = {"cols": COLS, "rows": ROWS, "w": W, "h": H, "files": files}

tpl = open(os.path.join(ROOT, "scripts", "template.html")).read()
page = tpl.replace("/*__SUMMARY__*/", json.dumps(S, separators=(",", ":")).replace("</", "<\\/"))
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
<meta property="og:title" content="Card Census">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Card Census">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE_URL}og.png">
{ga}<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect x='22' y='8' width='56' height='84' rx='8' fill='%23E2483D'/%3E%3C/svg%3E">
"""
open(os.path.join(SITE, "index.html"), "w").write("<!doctype html>\n<html lang=\"en\">\n<head>\n" + meta + head + "\n</head>\n<body>" + body + "\n</body>\n</html>\n")
json.dump(S, open(os.path.join(ROOT, "data", "summary.json"), "w"))
print(f"items={S['n']} subjects={len(S['subjects'])} sets={len(S['sets'])} photos={len(cells)} sheets={len(files)}", file=sys.stderr)
