import json, os, time, urllib.request, urllib.error, urllib.parse, threading

BASE = "https://api.opensea.io/api/v2"
_KEY = os.environ.get("OPENSEA_API_KEY")
_lock = threading.Lock()
_last = [0.0]
MIN_GAP = 0.12  # ~8 req/s across threads

def get(path, params=None, tries=6):
    assert _KEY, "OPENSEA_API_KEY missing"
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(tries):
        with _lock:
            wait = _last[0] + MIN_GAP - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        req = urllib.request.Request(url, headers={"x-api-key": _KEY, "accept": "application/json", "user-agent": "card-census/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(min(30, 2 ** attempt + 1))
                continue
            try:
                body = json.loads(e.read())
            except Exception:
                body = None
            return e.code, body
        except Exception as e:
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            return 0, {"error": str(e)}
