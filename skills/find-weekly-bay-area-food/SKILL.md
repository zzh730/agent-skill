---
name: find-weekly-bay-area-food
description: Find fresh Bay Area restaurant recommendations from RedNote, require five of five independently authored recommendation posts per venue, annotate literal 避雷 or 踩雷 mentions, validate on live Google Maps, deduplicate prior picks, and persist results. Use for recurring or one-off requests such as weekly Bay Area food discovery, 小红书湾区探店, new restaurant monitoring, or deduplicated restaurant recommendations.
---

# Find Weekly Bay Area Food

Find only newly discovered, currently operating Bay Area restaurants. Treat “小红书” as the OpenCLI `rednote` site on `rednote.com`, never as `xiaohongshu`, unless the user explicitly requests the China-domain service.

## Workflow

1. Establish the run date in `America/Los_Angeles`.
2. Run the required OpenCLI preflight:
   - `opencli doctor`
   - `opencli list -f yaml`; confirm `rednote/search` is `cookie`, browser-backed, and on `www.rednote.com`.
   - `opencli rednote -h` and `opencli rednote search -h`.
   - `opencli rednote whoami -f json`.
3. If RedNote is not authenticated, stop without searching or writing state. Report the exact login command: `opencli rednote login --window foreground --site-session persistent`.
4. Search RedNote at most twice per run:
   - Start with `湾区 新店 美食 <current year> <current month>`.
   - Use the second search only to narrow an overly broad result, for example `Bay Area new restaurant <current month> <current year>` plus missing city names.
5. Keep posts from roughly the last 45 days. Prefer explicit new openings; allow a recent discovery only when the post gives a clear venue name and useful food details. Drop housing, events, home cooking, non-Bay-Area places, and posts without an identifiable restaurant.
6. Validate each candidate against exactly five independently authored RedNote review posts about the same venue:
   - Read each full note, not only its search-result title or snippet.
   - Record title, date, URL, whether the post is an overall recommendation, a concise assessment, and every exact occurrence of `避雷` or `踩雷` in the title or body.
   - Count a mixed review as recommended only when the author still recommends the restaurant overall; preserve dish, price, service, or wait-time caveats separately.
   - Keep the candidate only when more than four of the five posts are overall recommendations. Because exactly five posts are required, this means `5/5`.
   - If fewer than five independent readable posts are available, drop the candidate rather than extrapolating.
   - Do not automatically drop a restaurant because `避雷` or `踩雷` appears. Add an `avoidance_summary`, and make the user-facing warning begin with `有人避雷：` while explaining what the author warned against and linking that post.
   - Do not invent details hidden only in an unread image; inspect the image when needed.
7. Validate every surviving candidate on live Google Maps:
   - Search by exact restaurant name and city.
   - Confirm the address is in the nine-county Bay Area: Alameda, Contra Costa, Marin, Napa, San Francisco, San Mateo, Santa Clara, Solano, or Sonoma.
   - Confirm the listing is operating and is the same venue as the RedNote post.
   - Record the current rating, review count, canonical Maps URL or place ID, address, and validation date.
   - Drop ratings below `3.0`; keep `3.0` exactly.
8. Build a JSON array using the schema below and pass it to `scripts/dedupe_and_store.py`. The script is the authority for the five-post requirement, recommendation threshold, avoidance annotation, rating filtering, cross-run deduplication, storage, and report creation.
9. Return only the script's newly added restaurants. If none remain, say that no new qualifying restaurants were found this week. Include all five RedNote source links, the `5/5` recommendation count, any `有人避雷` annotation, Google rating and review count, city/address, dishes, and other caveats.

## Candidate schema

```json
[
  {
    "name": "Restaurant name",
    "city": "City",
    "address": "Full Google Maps address",
    "google_rating": 4.4,
    "google_review_count": 127,
    "google_maps_url": "https://www.google.com/maps/place/...",
    "google_place_id": "optional stable place id",
    "rednote_url": "https://www.rednote.com/search_result/...",
    "rednote_title": "Post title",
    "rednote_published_at": "YYYY-MM-DD",
    "cuisine": "Thai",
    "recommended_dishes": ["dish one", "dish two"],
    "discovery_type": "new_opening",
    "summary": "Why it is worth considering",
    "warning": "Optional non-avoidance caveat",
    "avoidance_summary": "Required when any post contains 避雷 or 踩雷",
    "rednote_review_posts": [
      {
        "title": "Review title",
        "author": "Distinct review author",
        "published_at": "YYYY-MM-DD",
        "url": "https://www.rednote.com/search_result/...",
        "recommended": true,
        "assessment": "Why this is or is not an overall recommendation",
        "avoidance_terms": []
      }
    ]
  }
]
```

Provide exactly five objects in `rednote_review_posts`, each with a distinct URL. Set `avoidance_terms` to the exact matched terms from `避雷` and `踩雷`; do not paraphrase a general criticism as one of these terms. Use `new_opening` or `recent_discovery` for `discovery_type`.

## Persist results

Run:

```bash
python3 scripts/dedupe_and_store.py \
  --input /absolute/path/to/candidates.json \
  --run-date YYYY-MM-DD
```

By default, the script writes:

- History: `~/.codex/data/bay-area-food/restaurants.jsonl`
- Weekly report: `~/.codex/data/bay-area-food/reports/YYYY-MM-DD.md`

The script deduplicates by Google place ID first, then normalized restaurant name plus address, then normalized name plus city. Never bypass the history check or manually append to the history file.

## Reliability rules

- Treat RedNote as discovery evidence and Google Maps as the authority for location, operating status, rating, and review count.
- Do not report indicative search snippets as verified Maps data.
- Never treat likes, saves, or search rank as a recommendation vote; classify each full post on its own words.
- Require five distinct RedNote post URLs and five overall recommendations before persisting a restaurant.
- Preserve negative RedNote warnings even when a restaurant passes. If a post literally contains `避雷` or `踩雷`, label the result `有人避雷` and retain the source link.
- Do not recommend the same venue twice under spelling, punctuation, or capitalization variants.
- Do not overwrite or reset the history file. On parsing or validation errors, stop before appending.
- End with a compact search summary listing RedNote queries and the number of Google Maps venues checked.
