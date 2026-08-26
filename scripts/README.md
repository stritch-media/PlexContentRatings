# scripts/

Three small scripts plus a shared helper module. They read `.env` from the
project root and write into `data/`. Every path is resolved from the script
file's location, so it does not matter what directory you run them from.

```
python scripts/gather.py
python scripts/lookup.py
python scripts/apply.py
```

Dependencies: `plexapi`, `requests`, `python-dotenv` (`pip install -r requirements.txt`).

## plex_common.py

Shared helper module, not run directly. Provides:

- `PROJECT_ROOT`, `DATA_DIR`, `QUEUE_PATH`, `DECISIONS_PATH`, `DECISIONS_MD_PATH`,
  `CACHE_PATH`
- `load_servers()` — reads `PLEX_SERVER_1_*`, `PLEX_SERVER_2_*`, ... until a
  `_NAME` is missing. A server with a blank token is skipped with a warning.
- `connect(server)` — `PlexServer(url, token)` when a URL is set, otherwise
  `MyPlexAccount(token=...).resource(name).connect()`. Connections are cached
  per server name.
- `extract_ids(item)` — `{"tmdb", "imdb", "tvdb"}` from `item.guids`, falling
  back to parsing the legacy `item.guid` string.
- `unique_key(type, ids, title, year)` — `tmdb:603` / `imdb:tt0133093` /
  `tvdb:73244`, else `movie|thematrix|1999`.
- `normalize_rating(value)` — canonical `G PG PG-13 R NC-17 TV-Y TV-Y7 TV-Y7-FV
  TV-G TV-PG TV-14 TV-MA`, or `None`. Rejects NR / Not Rated / Unrated / TBD /
  blank and foreign values such as `gb/15`.
- `load_json(path, default)` / `save_json(path, obj)` — UTF-8, indent 2.

## gather.py

Walks every configured server and library, finds the collection named by
`PLEX_COLLECTION` (exact title match), and writes `data/queue.json`.

No flags. A failing server or library is printed and skipped; the run still
completes. Exit code is non-zero only if **no** server connected.

`data/queue.json`:

```json
{
  "generated": "2026-08-25T18:00:00+00:00",
  "servers_scanned": ["Appbox", "Kyle's Plex Server"],
  "items": [
    {"server": "...", "library": "Movies", "ratingKey": "12345",
     "type": "movie", "title": "...", "year": 1999, "current": null,
     "ids": {"tmdb": "603", "imdb": null, "tvdb": null}, "key": "tmdb:603"}
  ],
  "unique": {
    "tmdb:603": {
      "key": "tmdb:603", "type": "movie", "title": "...", "year": 1999,
      "ids": {...}, "current_ratings": [],
      "locations": [{"server": "...", "library": "...", "ratingKey": "..."}]
    }
  }
}
```

## lookup.py

Reads `data/queue.json` and `data/ratings-cache.json`, annotates each unique
title with TMDB and OMDb data, and writes the queue back in place under
`unique[key]["lookup"]` and `unique[key]["official"]`.

| Flag | Meaning |
|------|---------|
| *(none)* | look up entries that are neither cached nor already annotated |
| `--all` | look up every unique title again |
| `--test` | run a built-in queue (The Matrix, Stranger Things, Extraction, and a search-only title) against the live APIs; writes nothing |
| `--out PATH` | write the resulting queue to `PATH` instead of `data/queue.json` |

`official` is `{"rating", "source", "via"}` where `source` is `official-mpaa`
or `official-tv` and `via` is `tmdb` or `omdb`, or `null` when nothing official
was found (those titles are the ones Claude researches). Per-title failures are
recorded as `"lookup": {"error": "..."}` and never abort the run.

## apply.py

Reads `data/decisions.json`, validates it, then writes and **locks**
`contentRating` at every Plex location, verifying each write with a `reload()`.
Successful decisions are merged into `data/ratings-cache.json`.

| Flag | Meaning |
|------|---------|
| `--dry-run` | print what would change; touch neither Plex nor the cache |
| `--only KEY` | apply only this decision key; repeatable |

Validation happens before anything is touched. If any rating fails
`normalize_rating`, or a `show` is given an MPAA-style rating, the whole run
aborts and lists the offenders. Exit code is non-zero if any location failed.

`data/decisions.json`:

```json
{
  "generated": "2026-08-25T18:00:00+00:00",
  "decisions": [
    {
      "key": "tmdb:603",
      "title": "The Matrix",
      "year": 1999,
      "type": "movie",
      "rating": "R",
      "source": "official-mpaa",
      "confidence": "high",
      "rationale": "TMDB US theatrical certification R.",
      "locations": [
        {"server": "Appbox", "library": "Movies", "ratingKey": "12345"}
      ]
    }
  ]
}
```

`locations` may be omitted — `apply.py` then pulls them from `data/queue.json`
by `key`. `source` is one of `official-mpaa`, `official-tv`, `streamer`,
`estimated`; `confidence` is `high` / `medium` / `low`.
