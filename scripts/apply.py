"""Step 6 -- write and lock contentRating in Plex from data/decisions.json.

Every rating is validated before anything is touched: an invalid rating, or a
TV show given an MPAA-style rating, aborts the whole run with a list of the
offending entries. Nothing is written to Plex unless the entire decision set is
clean.

Flags:
  --dry-run      print what would change and touch nothing
  --only KEY     apply only this decision key (repeatable)
"""

from __future__ import annotations

import argparse
import traceback
from datetime import date

import plex_common as pc


def _locations_for(decision, queue_unique):
    locations = decision.get("locations")
    if locations:
        return locations
    entry = (queue_unique or {}).get(decision.get("key")) or {}
    return entry.get("locations") or []


def validate(decisions):
    """Return (clean_decisions, problems)."""
    problems = []
    clean = []
    for index, decision in enumerate(decisions):
        label = "%s (%s)" % (decision.get("title") or "?", decision.get("year") or "?")
        key = decision.get("key")
        if not key:
            problems.append("#%d %s: missing 'key'" % (index, label))
            continue
        raw = decision.get("rating")
        rating = pc.normalize_rating(raw)
        if not rating:
            problems.append("%s [%s]: invalid rating %r" % (label, key, raw))
            continue
        kind = decision.get("type")
        if kind == "show" and rating not in pc.VALID_TV:
            problems.append(
                "%s [%s]: show given non-TV rating %r (shows must use TV-Y..TV-MA)"
                % (label, key, rating))
            continue
        if kind not in ("movie", "show"):
            problems.append("%s [%s]: unknown type %r" % (label, key, kind))
            continue
        normalized = dict(decision)
        normalized["rating"] = rating
        clean.append(normalized)
    return clean, problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Apply decided content ratings to Plex")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would change; touch nothing")
    parser.add_argument("--only", action="append", default=[], metavar="KEY",
                        help="apply only this decision key (repeatable)")
    args = parser.parse_args(argv)

    print("PlexContentRatings / apply")
    print("decisions: %s" % pc.DECISIONS_PATH)

    doc = pc.load_json(pc.DECISIONS_PATH, None)
    if not doc or not isinstance(doc, dict) or not doc.get("decisions"):
        print("!! No usable %s -- nothing to apply." % pc.DECISIONS_PATH)
        return 1

    decisions = doc["decisions"]
    if args.only:
        wanted = set(args.only)
        decisions = [d for d in decisions if d.get("key") in wanted]
        missing = wanted - {d.get("key") for d in decisions}
        for key in sorted(missing):
            print("!! --only %s: no such decision" % key)
        if not decisions:
            print("!! Nothing selected.")
            return 1

    clean, problems = validate(decisions)
    if problems:
        print("\n!! ABORTING -- %d invalid decision(s), nothing was written:" % len(problems))
        for problem in problems:
            print("   - %s" % problem)
        return 1

    queue = pc.load_json(pc.QUEUE_PATH, {}) or {}
    queue_unique = queue.get("unique") or {}

    servers = {s["name"]: s for s in pc.load_servers()}
    cache = pc.load_json(pc.CACHE_PATH, {}) or {}

    applied = 0
    failed = 0
    skipped = 0

    for decision in clean:
        key = decision["key"]
        rating = decision["rating"]
        label = "%s (%s)" % (decision.get("title") or "?", decision.get("year") or "?")
        locations = _locations_for(decision, queue_unique)
        print("\n%s [%s] -> %s" % (label, key, rating))
        if not locations:
            print("   -- no Plex locations known -- skipped")
            skipped += 1
            continue

        applied_locations = []
        for location in locations:
            server_name = location.get("server")
            library = location.get("library")
            rating_key = location.get("ratingKey")
            where = "%s / %s / ratingKey %s" % (server_name, library, rating_key)

            if args.dry_run:
                print("   DRY-RUN would set %s on %s" % (rating, where))
                continue

            server = servers.get(server_name)
            if not server:
                print("   FAIL %s: server not configured or has no token" % where)
                failed += 1
                continue
            try:
                plex = pc.connect(server)
            except Exception as exc:
                print("   FAIL %s: connect failed: %s" % (where, exc))
                failed += 1
                continue
            try:
                item = plex.fetchItem(int(rating_key))
                item.editContentRating(rating, locked=True)
                item.reload()
                current = getattr(item, "contentRating", None)
                if current == rating:
                    print("   OK   %s  (%s)" % (where, item.title))
                    applied += 1
                    applied_locations.append({
                        "server": server_name,
                        "library": library,
                        "ratingKey": str(rating_key),
                    })
                else:
                    print("   FAIL %s: contentRating is %r after write (wanted %r)"
                          % (where, current, rating))
                    failed += 1
            except Exception as exc:
                print("   FAIL %s: %s: %s" % (where, type(exc).__name__, exc))
                failed += 1

        if args.dry_run:
            skipped += 1
            continue

        if applied_locations:
            cache[key] = {
                "title": decision.get("title"),
                "year": decision.get("year"),
                "type": decision.get("type"),
                "rating": rating,
                "source": decision.get("source"),
                "confidence": decision.get("confidence"),
                "rationale": decision.get("rationale"),
                "decided": date.today().isoformat(),
                "locations_applied": applied_locations,
            }

    if not args.dry_run:
        pc.save_json(pc.CACHE_PATH, cache)

    print("\n-- Tally --------------------------------------------------")
    print("decisions  : %d" % len(clean))
    print("applied    : %d location(s)" % applied)
    print("failed     : %d location(s)" % failed)
    print("skipped    : %d decision(s)" % skipped)
    if args.dry_run:
        print("(dry run -- nothing was written to Plex or the cache)")
    else:
        print("cache      : %s" % pc.CACHE_PATH)
    return 1 if failed else 0


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
