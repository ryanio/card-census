"""Download card photos from crawl.json into data/img, fitted into 5:7 cells with transparent padding."""
import hashlib, io, json, os, sys, urllib.parse, urllib.request, concurrent.futures as cf
from PIL import Image
ROOT = sys.argv[1]; W, H = int(os.environ.get("CELL_W", 200)), int(os.environ.get("CELL_H", 280))
CACHE = os.path.join(ROOT, "data", "img"); os.makedirs(CACHE, exist_ok=True)
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

def fetch(u):
    path = os.path.join(CACHE, key(u) + ".png")
    if os.path.exists(path) or os.path.exists(path + ".fail"): return os.path.exists(path)
    try:
        req = urllib.request.Request(sized(u), headers={"user-agent": "Mozilla/5.0 card-census", "accept": "image/webp,image/png,image/avif,image/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=30) as r: data = r.read(25_000_000)
        im = Image.open(io.BytesIO(data)); im.seek(0); im = im.convert("RGBA")
        im.thumbnail((W * 2, H * 2), Image.LANCZOS)
        scale = min(W / im.width, H / im.height); im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        cell = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cell.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))
        cell.save(path); return True
    except Exception as e:
        open(path + ".fail", "w").write(str(e)[:200]); return False

urls = [url_of(n) for n in crawl["top"]] + [url_of(n) for cs in crawl["copies"].values() for n in (cs or [])]
urls = list(dict.fromkeys(u for u in urls if u))
print("images:", len(urls), flush=True)
with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(fetch, urls))
print(f"done ok={sum(res)} fail={len(res) - sum(res)}", flush=True)
