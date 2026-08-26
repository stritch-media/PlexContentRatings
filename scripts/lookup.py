"""Step 3 -- annotate data/queue.json with TMDB and OMDb rating data.

For every unique title in the queue that is not already in
data/ratings-cache.json (or all of them with --all), fetch:

  * TMDB movie release_dates / tv content_ratings (US certs + foreign hints)
  * OMDb Rated / Plot / Genre / Country / Language

and write the result back into queue.json under unique[key]["lookup"], plus a
computed unique[key]["official"] when a valid US rating was found.

Flags:
  --all     re-look-up every unique title, even cached ones
  --test    run against a small built-in queue of known titles; writes nothing
            unless --out is given
  --out P   write the resulting queue to path P instead of data/queue.json
"""

from __future__ import annotations

import argparse
import time
import traceback

import requests

import plex_common as pc

TMDB_BASE = "https://api.themoviedb.org/3"
OMDB_BASE = "https://www.omdbapi.com/"
TIMEOUT = 15
TRIES = 3
POLITE_SLEEP = 0.25

# TMDB release types
RELEASE_TYPE_LABELS = {
    1: "Premiere",
    2: "Theatrical (limited)",
    3: "Theatrical",
    4: "Digital",
    5: "Physical",
    6: "TV",
}
# Order in which movie US certs are trusted: theatrical first, then the rest.
MOVIE_TYPE_PRIORITY = [3, 2, 1, 5, 4, 6]


class LookupError_(Exception):
    """A recoverable per-title lookup failure."""


def _get_json(url, params, label):
    """GET with a short retry on 429 / 5xx / connection errors."""
    delay = 1.0
    last = "unknown error"
    for attempt in range(1, TRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
        else:
            if resp.status_code == 429 or resp.status_code >= 500:
                last = "HTTP %d" % resp.status_code
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        pass
            elif not resp.ok:
                raise LookupError_("%s: HTTP %d" % (label, resp.status_code))
            else:
                try:
                    return resp.json()
                except ValueError as exc:
                    raise LookupError_("%s: bad JSON (%s)" % (label, exc))
        if attempt < TRIES:
            time.sleep(delay)
            delay *= 2
    raise LookupError_("%s: %s (after %d tries)" % (label, last, TRIES))


# --- TMDB --------------------------------------------------------------------

def tmdb_get(path, params=None, label=None):
    if not pc.TMDB_API_KEY:
        raise LookupError_("TMDB_API_KEY is not set in .env")
    query = dict(params or {})
    query["api_key"] = pc.TMDB_API_KEY
    return _get_json(TMDB_BASE + path, query, label or ("tmdb " + path))


def tmdb_resolve_id(entry):
    """Return (tmdb_id, matched_by) for a queue entry, or (None, reason)."""
    ids = entry.get("ids") or {}
    kind = entry.get("type")
    if ids.get("tmdb"):
        return ids["tmdb"], "guid"

    result_key = "tv_results" if kind == "show" else "movie_results"

    if ids.get("imdb"):
        data = tmdb_get("/find/%s" % ids["imdb"],
                        {"external_source": "imdb_id"}, "tmdb find imdb")
        results = data.get(result_key) or []
        if results:
            return str(results[0].get("id")), "find-imdb"

    if ids.get("tvdb") and kind == "show":
        data = tmdb_get("/find/%s" % ids["tvdb"],
                        {"external_source": "tvdb_id"}, "tmdb find tvdb")
        results = data.get("tv_results") or []
        if results:
            return str(results[0].get("id")), "find-tvdb"

    title = entry.get("title") or ""
    year = entry.get("year")
    if kind == "show":
        params = {"query": title}
        if year:
            params["first_air_date_year"] = year
        data = tmdb_get("/search/tv", params, "tmdb search tv")
    else:
        params = {"query": title}
        if year:
            params["year"] = year
        data = tmdb_get("/search/movie", params, "tmdb search movie")
    results = data.get("results") or []
    if results:
        return str(results[0].get("id")), "search"
    return None, "no-match"


def tmdb_movie(tmdb_id):
    data = tmdb_get("/movie/%s" % tmdb_id,
                    {"append_to_response": "release_dates"}, "tmdb movie")
    us_certs = []
    foreign = {}
    for block in ((data.get("release_dates") or {}).get("results") or []):
        iso = (block.get("iso_3166_1") or "").upper()
        for rel in (block.get("release_dates") or []):
            cert = (rel.get("certification") or "").strip()
            if not cert:
                continue
            rtype = rel.get("type")
            if iso == "US":
                us_certs.append({
                    "certification": cert,
                    "type": rtype,
                    "type_label": RELEASE_TYPE_LABELS.get(rtype, "Unknown"),
                    "note": rel.get("note") or "",
                    "release_date": rel.get("release_date") or "",
                })
            else:
                foreign.setdefault(iso, [])
                if cert not in foreign[iso]:
                    foreign[iso].append(cert)
    return {
        "tmdb_id": str(data.get("id")) if data.get("id") else str(tmdb_id),
        "title": data.get("title"),
        "release_date": data.get("release_date"),
        "overview": data.get("overview"),
        "genres": [g.get("name") for g in (data.get("genres") or []) if g.get("name")],
        "original_language": data.get("original_language"),
        "production_countries": [
            c.get("iso_3166_1") for c in (data.get("production_countries") or [])
            if c.get("iso_3166_1")
        ],
        "us_certifications": us_certs,
        "foreign_certifications": foreign,
    }


def tmdb_show(tmdb_id):
    data = tmdb_get("/tv/%s" % tmdb_id,
                    {"append_to_response": "content_ratings"}, "tmdb tv")
    us_rating = None
    foreign = {}
    for block in ((data.get("content_ratings") or {}).get("results") or []):
        iso = (block.get("iso_3166_1") or "").upper()
        rating = (block.get("rating") or "").strip()
        if not rating:
            continue
        if iso == "US":
            if not us_rating:
                us_rating = rating
        else:
            foreign.setdefault(iso, [])
            if rating not in foreign[iso]:
                foreign[iso].append(rating)
    return {
        "tmdb_id": str(data.get("id")) if data.get("id") else str(tmdb_id),
        "title": data.get("name"),
        "first_air_date": data.get("first_air_date"),
        "overview": data.get("overview"),
        "genres": [g.get("name") for g in (data.get("genres") or []) if g.get("name")],
        "original_language": data.get("original_language"),
        "origin_country": data.get("origin_country") or [],
        "networks": [n.get("name") for n in (data.get("networks") or []) if n.get("name")],
        "us_content_rating": us_rating,
        "foreign_content_ratings": foreign,
    }


# --- OMDb --------------------------------------------------------------------

def omdb_lookup(entry):
    if not pc.OMDB_API_KEY:
        raise LookupError_("OMDB_API_KEY is not set in .env")
    ids = entry.get("ids") or {}
    params = {"apikey": pc.OMDB_API_KEY}
    if ids.get("imdb"):
        params["i"] = ids["imdb"]
    else:
        params["t"] = entry.get("title") or ""
        if entry.get("year"):
            params["y"] = entry["year"]
        params["type"] = "series" if entry.get("type") == "show" else "movie"
    data = _get_json(OMDB_BASE, params, "omdb")
    if str(data.get("Response", "")).lower() != "true":
        return {"error": data.get("Error") or "not found"}
    return {
        "Rated": data.get("Rated"),
        "Plot": data.get("Plot"),
        "Genre": data.get("Genre"),
        "Country": data.get("Country"),
        "Language": data.get("Language"),
        "imdbID": data.get("imdbID"),
        "Title": data.get("Title"),
        "Year": data.get("Year"),
    }


# --- Official rating decision ------------------------------------------------

def _sorted_us_certs(us_certs):
    def rank(cert):
        rtype = cert.get("type")
        try:
            return MOVIE_TYPE_PRIORITY.index(rtype)
        except ValueError:
            return len(MOVIE_TYPE_PRIORITY)
    return sorted(us_certs or [], key=rank)


def compute_official(entry, lookup):
    """Pick the best official US rating from the TMDB/OMDb payloads."""
    tmdb = lookup.get("tmdb") or {}
    omdb = lookup.get("omdb") or {}
    omdb_rated = pc.normalize_rating(omdb.get("Rated")) if not omdb.get("error") else None

    if entry.get("type") == "show":
        tv_rating = pc.normalize_rating(tmdb.get("us_content_rating"))
        if tv_rating:
            return _official(tv_rating, "tmdb")
        if omdb_rated and omdb_rated in pc.VALID_TV:
            return _official(omdb_rated, "omdb")
        return None

    certs = _sorted_us_certs(tmdb.get("us_certifications"))
    normalized = [(c, pc.normalize_rating(c.get("certification"))) for c in certs]

    # 1. MPAA cert from a theatrical release type.
    for cert, norm in normalized:
        if norm in pc.VALID_MPAA and cert.get("type") in (2, 3):
            return _official(norm, "tmdb")
    # 2. Any other MPAA-style US cert.
    for _cert, norm in normalized:
        if norm in pc.VALID_MPAA:
            return _official(norm, "tmdb")
    # 3. OMDb Rated when it is MPAA-style.
    if omdb_rated and omdb_rated in pc.VALID_MPAA:
        return _official(omdb_rated, "omdb")
    # 4. TV-style US cert (streamer ratings usually land on type 4 Digital).
    for _cert, norm in normalized:
        if norm in pc.VALID_TV:
            return _official(norm, "tmdb")
    # 5. OMDb Rated when it is TV-style.
    if omdb_rated and omdb_rated in pc.VALID_TV:
        return _official(omdb_rated, "omdb")
    return None


def _official(rating, via):
    return {
        "rating": rating,
        "source": "official-mpaa" if rating in pc.VALID_MPAA else "official-tv",
        "via": via,
    }


def foreign_hints(lookup):
    """Return a compact 'GB:15 DE:16' string of foreign board ratings."""
    tmdb = lookup.get("tmdb") or {}
    foreign = tmdb.get("foreign_certifications") or tmdb.get("foreign_content_ratings") or {}
    parts = []
    for iso in sorted(foreign):
        values = foreign[iso]
        if values:
            parts.append("%s:%s" % (iso, values[0]))
    return " ".join(parts)


# --- Driver ------------------------------------------------------------------

def lookup_entry(entry):
    """Return the lookup payload for one queue entry. Never raises."""
    lookup = {}
    try:
        tmdb_id, matched_by = tmdb_resolve_id(entry)
        if not tmdb_id:
            lookup["tmdb"] = {"error": "no TMDB match (%s)" % matched_by}
        else:
            if matched_by == "search":
                lookup["matched_by"] = "search"
            elif matched_by != "guid":
                lookup["matched_by"] = matched_by
            time.sleep(POLITE_SLEEP)
            if entry.get("type") == "show":
                lookup["tmdb"] = tmdb_show(tmdb_id)
            else:
                lookup["tmdb"] = tmdb_movie(tmdb_id)
            if not (entry.get("ids") or {}).get("tmdb"):
                entry.setdefault("ids", {})["tmdb"] = str(tmdb_id)
            time.sleep(POLITE_SLEEP)
    except LookupError_ as exc:
        lookup["tmdb"] = {"error": str(exc)}
    except Exception as exc:
        lookup["tmdb"] = {"error": "%s: %s" % (type(exc).__name__, exc)}

    try:
        omdb = omdb_lookup(entry)
        lookup["omdb"] = omdb
        if not omdb.get("error") and omdb.get("imdbID") and not (entry.get("ids") or {}).get("imdb"):
            entry.setdefault("ids", {})["imdb"] = omdb["imdbID"]
    except LookupError_ as exc:
        lookup["omdb"] = {"error": str(exc)}
    except Exception as exc:
        lookup["omdb"] = {"error": "%s: %s" % (type(exc).__name__, exc)}

    if lookup.get("tmdb", {}).get("error") and lookup.get("omdb", {}).get("error"):
        lookup["error"] = "tmdb: %s | omdb: %s" % (
            lookup["tmdb"]["error"], lookup["omdb"]["error"])
    return lookup


def _test_queue():
    """A tiny in-memory queue of known titles for --test."""
    entries = [
        {"key": "tmdb:603", "type": "movie", "title": "The Matrix", "year": 1999,
         "ids": {"tmdb": "603", "imdb": None, "tvdb": None},
         "current_ratings": [], "locations": [], "_expect": "R"},
        {"key": "tmdb:66732", "type": "show", "title": "Stranger Things", "year": 2016,
         "ids": {"tmdb": "66732", "imdb": None, "tvdb": None},
         "current_ratings": [], "locations": [], "_expect": "TV-14"},
        {"key": "tmdb:545609", "type": "movie", "title": "Extraction", "year": 2020,
         "ids": {"tmdb": "545609", "imdb": None, "tvdb": None},
         "current_ratings": [], "locations": [], "_expect": "(streamer TV cert?)"},
        {"key": "movie|bladerunner2049|2017", "type": "movie",
         "title": "Blade Runner 2049", "year": 2017,
         "ids": {"tmdb": None, "imdb": None, "tvdb": None},
         "current_ratings": [], "locations": [], "_expect": "R (via search)"},
    ]
    return {
        "generated": "(test)",
        "servers_scanned": [],
        "items": [],
        "unique": {e["key"]: e for e in entries},
    }


def _print_table(rows):
    if not rows:
        return
    headers = ("Title", "Year", "Type", "Official", "Foreign hints")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    widths[0] = min(widths[0], 44)
    widths[4] = min(widths[4], 40)

    def fmt(cells):
        out = []
        for i, cell in enumerate(cells):
            text = str(cell)
            if len(text) > widths[i]:
                text = text[: widths[i] - 1] + "…"
            out.append(text.ljust(widths[i]))
        return "  ".join(out).rstrip()

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TMDB/OMDb lookup for the rating queue")
    parser.add_argument("--all", action="store_true",
                        help="look up every unique title, including cached ones")
    parser.add_argument("--test", action="store_true",
                        help="run against a small built-in queue of known titles")
    parser.add_argument("--out", default=None,
                        help="write the resulting queue here instead of data/queue.json")
    args = parser.parse_args(argv)

    print("PlexContentRatings / lookup")
    if args.test:
        queue = _test_queue()
        cache = {}
        out_path = args.out  # may be None -> write nothing
        print("mode: --test (built-in queue; data/queue.json untouched)")
    else:
        queue = pc.load_json(pc.QUEUE_PATH, None)
        if not queue or not isinstance(queue, dict) or "unique" not in queue:
            print("!! No usable %s -- run gather.py first." % pc.QUEUE_PATH)
            return 1
        cache = pc.load_json(pc.CACHE_PATH, {}) or {}
        out_path = args.out or pc.QUEUE_PATH

    unique = queue.get("unique") or {}
    if args.all or args.test:
        todo = list(unique.keys())
    else:
        todo = [k for k in unique if k not in cache and "lookup" not in unique[k]]

    print("unique titles: %d   to look up: %d" % (len(unique), len(todo)))
    if not todo:
        print("Nothing to do.")
        return 0

    rows = []
    errors = 0
    with_official = 0
    for index, key in enumerate(todo, 1):
        entry = unique[key]
        label = "%s (%s)" % (entry.get("title"), entry.get("year") or "?")
        print("[%d/%d] %s" % (index, len(todo), label), flush=True)
        try:
            lookup = lookup_entry(entry)
        except Exception as exc:  # belt and braces -- never kill the run
            lookup = {"error": "%s: %s" % (type(exc).__name__, exc)}
        entry["lookup"] = lookup
        if lookup.get("error"):
            errors += 1
            entry["official"] = None
            print("      !! %s" % lookup["error"])
        else:
            official = compute_official(entry, lookup)
            entry["official"] = official
            if official:
                with_official += 1
        rows.append((
            entry.get("title"),
            entry.get("year") or "-",
            entry.get("type"),
            (entry.get("official") or {}).get("rating") or "-",
            foreign_hints(lookup),
        ))

    print("\n-- Summary ------------------------------------------------")
    print("looked up            : %d" % len(todo))
    print("with official US rtg : %d" % with_official)
    print("needing research     : %d" % (len(todo) - with_official))
    if errors:
        print("lookup errors        : %d" % errors)
    print()
    _print_table(rows)

    if args.test:
        print()
        for key in todo:
            entry = unique[key]
            official = (entry.get("official") or {}).get("rating") or "-"
            source = (entry.get("official") or {}).get("source") or "-"
            via = (entry.get("official") or {}).get("via") or "-"
            print("EXPECT %-22s -> got %-6s (%s via %s)  [%s]" % (
                entry.get("_expect"), official, source, via, entry.get("title")))
            certs = (entry.get("lookup", {}).get("tmdb") or {}).get("us_certifications")
            if certs:
                detail = ", ".join(
                    "%s/type %s %s" % (c["certification"], c["type"], c["type_label"])
                    for c in certs)
                print("       US certs: %s" % detail)
            tv = (entry.get("lookup", {}).get("tmdb") or {}).get("us_content_rating")
            if tv:
                print("       US content rating: %s" % tv)
            omdb = entry.get("lookup", {}).get("omdb") or {}
            print("       OMDb Rated: %s" % (omdb.get("Rated") or omdb.get("error")))

    if out_path:
        pc.save_json(out_path, queue)
        print("\nqueue written to: %s" % out_path)
    else:
        print("\n(no file written)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
