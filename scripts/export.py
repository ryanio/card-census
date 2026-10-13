"""Write the census as CSV: the latest snapshot plus an append-only history keyed by crawl time."""
import csv, json, os, sys
ROOT = sys.argv[1]; D = os.path.join(ROOT, "data"); H = os.path.join(D, "history"); os.makedirs(H, exist_ok=True)
S = json.load(open(os.path.join(D, "summary.json"))); AT = S["at"]
num = lambda g: float(g) if str(g).replace(".", "", 1).isdigit() else None
tot = lambda pairs: sum(c for _, c in pairs)
tens = lambda pairs: sum(c for g, c in pairs if (num(g) or 0) >= 10)
ten_exact = lambda pairs: sum(c for g, c in pairs if num(g) == 10)
lang = lambda pairs, n: round(dict(pairs).get(n, 0) / tot(pairs), 4) if tot(pairs) else 0
best = lambda s: max((c for c in s["copies"] if c["v"] is not None), key=lambda c: c["v"], default=None)
def write(name, header, rows):
    with open(os.path.join(D, name), "w", newline="") as f: w = csv.writer(f); w.writerow(header); w.writerows(rows)
def append(name, header, rows):
    path = os.path.join(H, name); fresh = not os.path.exists(path)
    if not fresh:
        with open(path) as f:
            if any(line.startswith(AT + ",") for line in f): return 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if fresh: w.writerow(header)
        w.writerows(rows)
    return len(rows)
cards = []
for s in S["subjects"]:
    b = best(s)
    cards.append([s["s"], s["f"], s["n"], s["graded"], tens(s["grade"]), ten_exact(s["psa"]), tot(s["psa"]), ten_exact(s["cgc"]), tot(s["cgc"]),
                  round(tens(s["grade"]) / s["graded"], 4) if s["graded"] else "", lang(s["lang"], "Japanese"), b["v"] if b else "", b["t"] if b else "", b["g"] if b else "", b["url"] if b else ""])
write("cards.csv", ["card", "franchise", "copies", "graded", "graded_10_plus", "psa_10", "psa_graded", "cgc_10", "cgc_graded", "gem_rate", "japanese_share", "top_copy_usd", "top_copy", "top_copy_grade", "top_copy_url"], cards)
grades = []
for s in S["subjects"]:
    for who, pairs in (("all", s["grade"]), ("PSA", s["psa"]), ("CGC", s["cgc"])):
        grades += [[s["s"], who, g, c] for g, c in pairs]
write("grades.csv", ["card", "grader", "grade", "count"], grades)
G = {g["g"]: g for g in S["graders"]}
graded = tot(S["grade"])
total_row = [AT, S["n"], graded, tens(S["grade"]), S["raw"], S.get("sealed_n", 0), round(G["PSA"]["ten"] / G["PSA"]["n"], 4) if "PSA" in G else "", round(G["CGC"]["ten"] / G["CGC"]["n"], 4) if "CGC" in G else "",
             lang(S["lang"], "Japanese"), S["top"][0]["v"] if S["top"] else "", len(S["subjects"])]
a = append("totals.csv", ["at", "cards", "graded", "graded_10_plus", "raw", "sealed", "psa_10_share", "cgc_10_share", "japanese_share", "top_card_usd", "cards_with_report"], [total_row])
b = append("cards.csv", ["at", "card", "franchise", "copies", "graded", "graded_10_plus", "psa_10", "top_copy_usd"], [[AT] + [r[0], r[1], r[2], r[3], r[4], r[5], r[11]] for r in cards])
print(f"export: {len(cards)} cards, {len(grades)} grade rows; history +{a} totals, +{b} cards at {AT}")
