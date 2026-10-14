# Plan

## Status

Built from the first snapshot: 907,093 cards, 308 cards with their own pop report, 186 sets. Not announced yet. Tweet drafts live in `TWEETS.md`, which is gitignored.

## Before posting

1. Set `LAUNCH_DATE` in `.github/workflows/pages.yml` to the day you post, so the refresh schedule counts from launch.
2. Add the API key secret so the workflow can refresh (run it yourself; the value never prints):
   ```sh
   ~/.claude/skills/onepassword/scripts/op-sa run --env-file ~/.config/op/opensea.env -- sh -c 'printf %s "$OPENSEA_API_KEY" | gh secret set OPENSEA_API_KEY -R ryanio/card-census'
   ```
3. Run `gh workflow run pages.yml -R ryanio/card-census` about an hour before posting and update the numbers in `TWEETS.md`.

## Known limits

- A facet value list stops at 100 entries, so only cards in the overall top 100 or a franchise's top 30 get their own report. Everything is still in the totals.
- Grades are compared on each grader's own scale. A 10 means 10 or higher, including 10.5 (CGC Pristine, BGS Black Label). BGS calls 9.5 Gem Mint, so its share of 10s reads low.
- Values are OpenSea's estimated value, not sales.
- The same card can be listed more than once (two issuers, or the same slab in two places). The cover wall and each card's copies drop repeats by name and value.

## Later

- A set lookup next to the card lookup, using the per-set facets already in the crawl.
- Pop history: keep a dated snapshot of each card's grade counts to show what got tokenized this week.

## Data in the repo

Each fresh crawl writes CSVs to `data/` and appends to `data/history/`. The workflow commits them once per UTC day, from that day's first run. Runs drop to weekly at day 30, so the data commits do too.
