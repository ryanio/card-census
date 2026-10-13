#!/bin/sh
# Full refresh: walk the trading_cards facets, fetch card photos, build site/ and the social card.
# Needs OPENSEA_API_KEY in the environment.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
: "${OPENSEA_API_KEY:?set OPENSEA_API_KEY}"
age=$(( $(date +%s) - $(cat data/crawled_at 2>/dev/null || echo 0) ))
if [ -n "$CRAWL_MAX_AGE" ] && [ -f data/crawl.json ] && [ "$age" -lt "$CRAWL_MAX_AGE" ]; then
  echo "reusing crawl from $((age / 60)) minutes ago"
else
  python3 scripts/crawl.py "$ROOT"
  date +%s > data/crawled_at
fi
python3 scripts/images.py "$ROOT"
mkdir -p data/fonts
for f in "ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf:bsd.ttf" "ofl/publicsans/PublicSans%5Bwght%5D.ttf:ps.ttf" "ofl/ibmplexmono/IBMPlexMono-Medium.ttf:mono.ttf"; do
  [ -f "data/fonts/${f##*:}" ] || curl -sfL -o "data/fonts/${f##*:}" "https://raw.githubusercontent.com/google/fonts/main/${f%%:*}"
done
rm -rf site
python3 scripts/build.py "$ROOT"
python3 scripts/og.py "$ROOT"
python3 scripts/share.py "$ROOT"
python3 scripts/export.py "$ROOT"
