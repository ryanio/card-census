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

def search(limit=4, **filters):
    params = [(k, v) for k, v in filters.items()] + [("sort_by", "estimated_value"), ("sort_direction", "desc"), ("limit", limit)]
    s, b = get(f"/nfts/group/{GROUP}", params)
    if s != 200 or not b: return []
    keep = ("name", "collection", "contract", "identifier", "display_image_url", "image_url", "estimated_value_usd", "best_listing_price", "opensea_url")
    return [{k: n.get(k) for k in keep} for n in b.get("nfts", [])]

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
json.dump({"group": GROUP, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "all": ALL, "franchise": FR, "grader": GR, "fg": FG,
           "subjects": subjects, "subject": SUB, "subject_grader": SUBG, "sets": sets, "set": SET, "top": TOP, "sealed": SEALED, "copies": COPIES}, open(OUT, "w"))
missing = sum(1 for v in list(SUB.values()) + list(SUBG.values()) + list(SET.values()) if v is None)
print(f"done in {time.time() - t0:.0f}s, {len(subjects)} subjects, {len(sets)} sets, missing={missing}", flush=True)
