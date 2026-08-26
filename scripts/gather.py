"""Step 1 -- walk the *NEEDS PROPER RATING* collections and build data/queue.json.

Reads every configured server / library, finds the collection named by
PLEX_COLLECTION, and records one row per Plex location plus a deduplicated
"unique" map keyed by GUID (fallback: type|normalized-title|year).

A failing server or library is reported and skipped; the run still produces a
queue from whatever worked. Exit code is 0 unless no server connected at all.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

import plex_common as pc


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _find_collection(section, wanted_title):
    """Return the collection whose title matches `wanted_title` exactly."""
    collections = section.collections()
    for coll in collections:
        if getattr(coll, "title", None) == wanted_title:
            return coll
    return None


def gather():
    servers = pc.load_servers()
    if not servers:
        print("!! No usable servers configured (check PLEX_SERVER_n_* in .env).")
        return None, 0

    if not pc.LIBRARIES:
        print("!! No libraries configured (set PLEX_LIBRARIES in .env).")
    if not pc.COLLECTION:
        print("!! No collection configured (set PLEX_COLLECTION in .env).")

    rows = []
    servers_scanned = []
    per_location_counts = []
    connected = 0

    for server in servers:
        name = server["name"]
        where = server.get("url") or "(plex.tv discovery)"
        print("\n== Server: %s  [%s]" % (name, where))
        try:
            plex = pc.connect(server)
        except Exception as exc:
            print("   !! FAILED to connect to '%s': %s" % (name, exc))
            continue
        connected += 1
        servers_scanned.append(name)

        for library in pc.LIBRARIES:
            try:
                section = plex.library.section(library)
            except Exception as exc:
                print("   !! [%s / %s] library not available: %s" % (name, library, exc))
                continue

            try:
                collection = _find_collection(section, pc.COLLECTION)
            except Exception as exc:
                print("   !! [%s / %s] could not list collections: %s" % (name, library, exc))
                continue

            if collection is None:
                print("   -- [%s / %s] no such collection %r -- skipping"
                      % (name, library, pc.COLLECTION))
                continue

            try:
                items = collection.items()
            except Exception as exc:
                print("   !! [%s / %s] could not read collection items: %s"
                      % (name, library, exc))
                continue

            count = 0
            skipped_types = 0
            for item in items:
                try:
                    itype = getattr(item, "type", None)
                    if itype not in ("movie", "show"):
                        skipped_types += 1
                        continue
                    ids = pc.extract_ids(item)
                    title = getattr(item, "title", None) or "(untitled)"
                    year = getattr(item, "year", None)
                    rows.append({
                        "server": name,
                        "library": library,
                        "ratingKey": str(getattr(item, "ratingKey", "")),
                        "type": itype,
                        "title": title,
                        "year": year,
                        "current": getattr(item, "contentRating", None) or None,
                        "ids": ids,
                        "key": pc.unique_key(itype, ids, title, year),
                    })
                    count += 1
                except Exception as exc:
                    print("   !! [%s / %s] skipped an item: %s" % (name, library, exc))

            note = ""
            if skipped_types:
                note = "  (%d non-movie/show item(s) skipped)" % skipped_types
            print("   %-10s %-10s %4d item(s)%s" % (name, library, count, note))
            per_location_counts.append((name, library, count))

    if connected == 0:
        return None, 0

    unique = {}
    for row in rows:
        key = row["key"]
        entry = unique.get(key)
        if entry is None:
            entry = {
                "key": key,
                "type": row["type"],
                "title": row["title"],
                "year": row["year"],
                "ids": dict(row["ids"]),
                "current_ratings": [],
                "locations": [],
            }
            unique[key] = entry
        else:
            # Fill in any id another location knew about.
            for source in ("tmdb", "imdb", "tvdb"):
                if not entry["ids"].get(source) and row["ids"].get(source):
                    entry["ids"][source] = row["ids"][source]
            if entry.get("year") is None and row.get("year") is not None:
                entry["year"] = row["year"]
        if row["current"] and row["current"] not in entry["current_ratings"]:
            entry["current_ratings"].append(row["current"])
        entry["locations"].append({
            "server": row["server"],
            "library": row["library"],
            "ratingKey": row["ratingKey"],
        })

    queue = {
        "generated": _iso_now(),
        "servers_scanned": servers_scanned,
        "items": rows,
        "unique": unique,
    }
    return queue, connected


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    print("PlexContentRatings / gather")
    print("project root: %s" % pc.PROJECT_ROOT)
    print("collection:   %r" % pc.COLLECTION)
    print("libraries:    %s" % (", ".join(pc.LIBRARIES) or "(none)"))

    try:
        queue, connected = gather()
    except Exception:
        traceback.print_exc()
        print("\n!! gather failed unexpectedly")
        return 1

    if connected == 0 or queue is None:
        print("\n!! No servers connected -- nothing gathered.")
        return 1

    pc.save_json(pc.QUEUE_PATH, queue)

    cache = pc.load_json(pc.CACHE_PATH, {}) or {}
    unique = queue["unique"]
    cached_keys = [k for k in unique if k in cache]
    new_keys = [k for k in unique if k not in cache]

    print("\n-- Summary ------------------------------------------------")
    print("servers connected : %d (%s)" % (connected, ", ".join(queue["servers_scanned"])))
    print("total locations   : %d" % len(queue["items"]))
    print("unique titles     : %d" % len(unique))
    print("already in cache  : %d" % len(cached_keys))
    print("new to research   : %d" % len(new_keys))
    print("queue written to  : %s" % pc.QUEUE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
