# Plan

## Goal

A static page that reads like a grading company's pop report, for every tokenized card on OpenSea at once. Pick a subject like Charizard and see how many exist onchain at each grade, by grader, language and year. Then zoom out to questions a collector cares about: which grader hands out the most 10s, how much of the market is vintage, and how far Japanese cards have spread.

## Data source

`GET /api/v2/nfts/group/{group}/facets` returns, for one collection group, every value of nine normalized attributes with the number of matching NFTs: `franchise`, `grader`, `grade`, `subject`, `year`, `set`, `language`, `edition`, `product_type`. Each attribute is also a repeatable filter, and each facet is narrowed by the filters on the other types, so one facet keeps listing all of its own values. `collection_slugs` limits it to up to 10 collections in the group.

`GET /api/v2/nfts/group/{group}` searches the same NFTs with the same filters. It sorts by `price`, `top_offer`, `last_sale`, `last_sale_date`, `created_date`, `received_date`, `listing_created_date`, `best_deal` or `estimated_value`, and returns `display_image_url`, `estimated_value_usd`, `best_listing_price` and `opensea_url`. Use it for one representative image per subject and for "most valuable copy" callouts.

### First probe, 2026-10-13, group `trading_cards`

| Facet | Values | Biggest |
| --- | --- | --- |
| product_type | 3 | Graded Card 646,843, Raw Card 178,592, Sealed Product 81,542 |
| franchise | 12 | Pokemon 528,782, One Piece 72,139, Football 56,030, Baseball 54,064, Basketball 50,759 |
| grader | 41 | PSA 417,825, CGC 223,023, BGS 10,181, CGC-COMIC 5,103, TAG 3,012 |
| grade | 20 | 10: 333,131, 9: 179,812, 8: 49,742 |
| language | 16 | English 511,873, Japanese 174,005, Chinese 4,653 |
| subject | 100 (capped) | Pikachu 18,149, Monkey D. Luffy 16,361, Charizard 14,265, Eevee 6,288 |
| set | 100 (capped) | Topps 13,942, 151 11,362, Panini Prizm 8,691 |
| year | 100 (capped) | 2025 176,320, 2023 145,071, 2024 108,348 |
| edition | 61 | Holo 3,575, 1st Edition 1,521 |

About 907k NFTs in the group. Half of all graded cards are 10s. `subject`, `set` and `year` stop at 100 values per call, so the long tail needs filtered calls, for example `subject` per franchise.

## Views

1. Pop report table. Rows are subjects, columns are grades, cells are counts, with filters for franchise, grader, language and year. The first view on load is Pokemon on PSA, the table collectors already know.
2. Gem rate. Share of 10s by grader, franchise, set and year. It answers whether PSA or CGC is more generous and which sets grade best.
3. Vintage and modern. Count by year for each franchise, with the WOTC era (1999 to 2003) marked for Pokemon.
4. English and Japanese. Language split for each franchise and for the top subjects.
5. Graded, raw and sealed. Product type mix for each franchise.
6. Rarest cards. Subjects or sets with the fewest graded copies at grade 10, with the priciest onchain copy from the search endpoint.

## Crawl budget

All facet calls, cached into `data/facets/*.json`:

- 1 unfiltered call.
- 12 per franchise.
- About 8 per top grader, and 12 x 8 for franchise by grader (gem rate).
- About 100 per top subject, for its grade, grader and language split.
- About 100 per top set and 100 per year bucket.
- About 100 search calls for one image and the priciest copy per top subject.

Roughly 500 calls per refresh. That is cheap enough for the same time-decay schedule PFP Census uses.

## Build and hosting

Copy the PFP Census setup: Python scripts write a static `site/` (one HTML page, JSON, WebP sprites for card art), and a GitHub Pages workflow with a decide step refreshes when the `OPENSEA_API_KEY` secret is set. Card images cannot be hotlinked reliably, so they ship as sprites like the PFP faces.

Design direction: the graded slab as the visual unit, a clear case with a label band showing grader, grade and count. Keep it generic. Don't copy any grading company's label design or logo.

## Open questions

- Which groups exist besides `trading_cards`? The spec gives that one as the example and lists no other values.
- Are grades comparable across graders (BGS 9.5 against PSA 10)? Probably show them per grader and don't merge.
- Grader strings vary (`CGC` and `CGC-COMIC` are separate values). Decide whether to group them in the UI.
- Is there an index or cache cost to the facets endpoint at about 500 calls per refresh? Ask before turning on a frequent schedule.

## Tweets

Drafts go in `TWEETS.md`, which is gitignored and never committed.
