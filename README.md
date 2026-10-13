# Card Census

An onchain pop report: every tokenized trading card on OpenSea, counted by card, grade and grader. Live at [ryanio.github.io/card-census](https://ryanio.github.io/card-census/). Sibling of [PFP Census](https://github.com/ryanio/pfp-census).

Every number comes from [`GET /api/v2/nfts/group/{group}/facets`](https://docs.opensea.io/reference/api-overview), which returns each normalized attribute (franchise, grader, grade, subject, year, set, language, edition, product type) with a count of matching cards. Each facet narrows by the filters on the others, so `subject=Charizard&grader=PSA` returns Charizard's grades on PSA's scale. Card photos and values come from `GET /api/v2/nfts/group/{group}` sorted by `estimated_value`.

## How it works

`scripts/refresh.sh` walks the facets (overall, per franchise, per grader, and for about 300 cards overall and on PSA and CGC), downloads the most valuable copies' photos, and builds `site/`: one HTML page with the data inline and WebP sprite sheets of card photos. The API key is only used by the crawl, never by the page.

## Data

Each fresh crawl commits CSVs to `data/`: `cards.csv` (one row per card: copies, graded, 10s, PSA and CGC counts, gem rate, Japanese share, top copy) and `grades.csv` (every card's grades overall, on PSA and on CGC). `data/history/` keeps an append-only record keyed by crawl time: `totals.csv` (headline numbers per crawl) and `cards.csv` (each card per crawl), so you can chart how the onchain pop changes.

## Refreshing

The `Refresh and deploy` workflow re-crawls twice a day for the first two weeks after `LAUNCH_DATE`, daily through day 45, then weekly on Mondays, when the `OPENSEA_API_KEY` repository secret is set. The built site is deployed straight to Pages and not committed. The Google Analytics tag comes from the `GA_ID` repository variable.

To run it locally:

```sh
pip install "pillow>=11.2"
OPENSEA_API_KEY=... ./scripts/refresh.sh
```
