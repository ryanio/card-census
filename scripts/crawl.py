"""Walk the trading_cards group facets the way a pop report reads: subject by grade, per grader. Writes data/crawl.json."""
import json, os, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osapi import get
ROOT = sys.argv[1]; GROUP = os.environ.get("GROUP", "trading_cards")
OUT = os.path.join(ROOT, "data", "crawl.json"); os.makedirs(os.path.dirname(OUT), exist_ok=True)

def facets(types=None, **filters):
    params = [(k, v) for k, vs in filters.items() for v in (vs if isinstance(vs, list) else [vs])]
    params += [("facet_types", t) for t in (types or [])]
    s, b = get(f"/nfts/group/{GROUP}/facets", params)
    if s != 200 or not b: return None
    return {f["type"]: [[v["value"], v["count"]] for v in f["values"]] for f in b.get("facets", [])}

KEEP = ("name", "collection", "contract", "identifier", "display_image_url", "image_url", "estimated_value_usd", "best_listing_price", "opensea_url")
def search(limit=4, by_value=True, **filters):
    """Up to `limit` cards, most valuable first (or the API's default order), following the cursor past 100."""
    out, cursor = [], None
    while len(out) < limit:
        params = [(k, v) for k, v in filters.items()] + [("limit", min(100, limit - len(out)))]
        if by_value: params += [("sort_by", "estimated_value"), ("sort_direction", "desc")]
        if cursor: params.append(("next", cursor))
        s, b = get(f"/nfts/group/{GROUP}", params)
        if s != 200 or not b: break
        out += [{k: n.get(k) for k in KEEP} for n in b.get("nfts", [])]
        cursor = b.get("next")
        if not cursor or not b.get("nfts"): break
    return out[:limit]

def pmap(fn, items, workers=6):
    with cf.ThreadPoolExecutor(workers) as ex: return dict(zip(items, ex.map(fn, items)))

t0 = time.time()
ALL = facets()
franchises = [v for v, n in ALL["franchise"] if n >= 1000]
graders = [v for v, n in ALL["grader"] if n >= 2000 and v.lower() not in ("raw", "not graded")]
FR = pmap(lambda f: facets(franchise=f), franchises)
GR = pmap(lambda g: facets(types=["grade", "franchise"], grader=g), graders)
fg_keys = [(f, g) for f in franchises[:6] for g in ("PSA", "CGC")]
FG = {f"{f}|{g}": v for (f, g), v in pmap(lambda k: facets(types=["grade"], franchise=k[0], grader=k[1]), fg_keys).items()}
subjects = [v for v, _ in ALL["subject"]]
for f in franchises:
    subjects += [v for v, _ in (FR[f] or {}).get("subject", [])[:30]]
subjects = list(dict.fromkeys(subjects))
print(f"{len(franchises)} franchises, {len(graders)} graders, {len(subjects)} subjects", flush=True)
SUB = pmap(lambda s: facets(subject=s), subjects)
SUBG = {f"{s}|{g}": v for (s, g), v in pmap(lambda k: facets(types=["grade"], subject=k[0], grader=k[1]), [(s, g) for s in subjects for g in ("PSA", "CGC")]).items()}
sets = [v for v, _ in ALL["set"]]
for f in franchises:
    sets += [v for v, _ in (FR[f] or {}).get("set", [])[:15]]
sets = list(dict.fromkeys(sets))
SET = pmap(lambda x: facets(types=["grade", "franchise", "year", "grader"], set=x), sets)
TOP = search(limit=40, product_type="Graded Card")
SEALED = search(limit=16, product_type="Sealed Product")
COPIES = pmap(lambda s: search(limit=4, subject=s), subjects)
# photos for the cover map: a territory for every card with 1,500+ copies, and a mix of the priciest and the
# API's default order for the rest of each franchise, roughly one photo per 750 cards
own_n = lambda s: next((c for v, c in (SUB[s] or {}).get("subject", []) if v == s), 0)
MAP_SUB = pmap(lambda s: search(limit=min(100, max(8, -(-own_n(s) // 450))), subject=s), [s for s in subjects if own_n(s) >= 1500])
fr_n = dict(ALL["franchise"])
def fr_photos(f):
    k = min(800, max(30, -(-fr_n[f] // 750)))
    return search(limit=k // 2, franchise=f) + search(limit=k - k // 2, by_value=False, franchise=f)
MAP_FR = pmap(fr_photos, franchises)
# the issuers that vault the cards: every collection seen in the photos above, counted with collection_slugs
seen = [n.get("collection") for n in TOP + SEALED + [n for v in list(COPIES.values()) + list(MAP_SUB.values()) + list(MAP_FR.values()) for n in (v or [])]]
slugs = [c for c in dict.fromkeys(seen) if c and seen.count(c) >= 3]
def issuer(slug):
    s, b = get(f"/collections/{slug}", [])
    return {"slug": slug, "name": (b or {}).get("name") if s == 200 else slug, "facets": facets(types=["product_type", "franchise", "grader"], collection_slugs=slug)}
ISSUERS = list(pmap(issuer, slugs).values())
json.dump({"group": GROUP, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "all": ALL, "franchise": FR, "grader": GR, "fg": FG,
           "subjects": subjects, "subject": SUB, "subject_grader": SUBG, "sets": sets, "set": SET, "top": TOP, "sealed": SEALED, "copies": COPIES,
           "map": {"subject": MAP_SUB, "franchise": MAP_FR}, "issuers": ISSUERS}, open(OUT, "w"))
missing = sum(1 for v in list(SUB.values()) + list(SUBG.values()) + list(SET.values()) if v is None)
print(f"done in {time.time() - t0:.0f}s, {len(subjects)} subjects, {len(sets)} sets, missing={missing}", flush=True)
