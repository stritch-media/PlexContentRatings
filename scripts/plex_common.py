"""Shared helpers for the PlexContentRatings scripts.

Path resolution is always relative to this file, so every script works no
matter what directory it is run from. Only stdlib + plexapi + python-dotenv
are used here.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# --- Console -----------------------------------------------------------------

# Titles routinely contain non-ASCII characters; the default Windows console
# codepage raises UnicodeEncodeError on them.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # pragma: no cover - old / redirected streams
        pass


# --- Paths -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

QUEUE_PATH = DATA_DIR / "queue.json"
DECISIONS_PATH = DATA_DIR / "decisions.json"
DECISIONS_MD_PATH = DATA_DIR / "decisions.md"
CACHE_PATH = DATA_DIR / "ratings-cache.json"

ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


# --- Environment -------------------------------------------------------------

def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip()


LIBRARIES = [part.strip() for part in _env("PLEX_LIBRARIES").split(",") if part.strip()]
COLLECTION = _env("PLEX_COLLECTION")
TMDB_API_KEY = _env("TMDB_API_KEY")
OMDB_API_KEY = _env("OMDB_API_KEY")


def load_servers() -> list:
    """Read PLEX_SERVER_n_{NAME,URL,TOKEN} from the environment.

    Scans n = 1, 2, 3 ... and stops at the first missing NAME. A server whose
    token is blank is skipped with a loud warning. Token values are never
    printed.
    """
    servers = []
    n = 1
    while True:
        name = _env("PLEX_SERVER_%d_NAME" % n)
        if not name:
            break
        url = _env("PLEX_SERVER_%d_URL" % n)
        token = _env("PLEX_SERVER_%d_TOKEN" % n)
        if not token:
            print(
                "!! WARNING: server '%s' (PLEX_SERVER_%d) has no token set in %s "
                "-- skipping it. Fill in PLEX_SERVER_%d_TOKEN."
                % (name, n, ENV_PATH.name, n),
                flush=True,
            )
        else:
            servers.append({"name": name, "url": url, "token": token})
        n += 1
    return servers


# --- Connections -------------------------------------------------------------

_CONNECTIONS = {}


def connect(server):
    """Return a connected PlexServer for `server`, cached by server name.

    Uses the direct URL when one is configured, otherwise discovers the server
    through plex.tv by name.
    """
    name = server["name"]
    if name in _CONNECTIONS:
        return _CONNECTIONS[name]

    from plexapi.server import PlexServer

    url = server.get("url") or ""
    token = server.get("token") or ""
    if url:
        plex = PlexServer(url, token)
    else:
        from plexapi.myplex import MyPlexAccount

        plex = MyPlexAccount(token=token).resource(name).connect()

    _CONNECTIONS[name] = plex
    return plex


# --- Ratings -----------------------------------------------------------------

VALID_MPAA = {"G", "PG", "PG-13", "R", "NC-17"}
VALID_TV = {"TV-Y", "TV-Y7", "TV-Y7-FV", "TV-G", "TV-PG", "TV-14", "TV-MA"}
VALID_RATINGS = VALID_MPAA | VALID_TV

# Compact key ("PG-13" -> "PG13") -> canonical form.
_RATING_LOOKUP = {re.sub(r"[^A-Z0-9]", "", r.upper()): r for r in VALID_RATINGS}


def normalize_rating(value):
    """Return the canonical US rating for `value`, or None if it is not one.

    Accepts sloppy input ("tv14", "pg 13", "nc17", "US/PG-13"). Rejects NR /
    Not Rated / Unrated / TBD / blank and any non-US country-prefixed value
    such as "gb/15".
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if "/" in text:
        prefix, _, rest = text.partition("/")
        # "us/pg-13" is fine; "gb/15", "de/16" are not.
        if prefix.strip().lower() not in ("us", "usa"):
            return None
        text = rest.strip()

    # "Rated R", "MPAA: R"
    text = re.sub(r"^\s*(rated|mpaa|mpa)\s*[:\-]?\s*", "", text, flags=re.IGNORECASE)

    key = re.sub(r"[^A-Z0-9]", "", text.upper())
    if not key:
        return None
    return _RATING_LOOKUP.get(key)


def is_tv_rating(value) -> bool:
    return normalize_rating(value) in VALID_TV


def is_mpaa_rating(value) -> bool:
    return normalize_rating(value) in VALID_MPAA


# --- Ids ---------------------------------------------------------------------

_AGENT_TO_KEY = {
    "themoviedb": "tmdb",
    "tmdb": "tmdb",
    "imdb": "imdb",
    "thetvdb": "tvdb",
    "tvdb": "tvdb",
}

_GUID_RE = re.compile(r"^(?:com\.plexapp\.agents\.)?([a-z0-9]+)://(.+)$")


def _absorb_guid(ids, raw) -> None:
    """Parse one guid string into `ids` (modern and legacy formats)."""
    try:
        text = str(raw or "").strip().lower()
    except Exception:
        return
    if not text:
        return
    text = text.split("?", 1)[0]  # drop ?lang=en
    match = _GUID_RE.match(text)
    if not match:
        return
    agent, value = match.group(1), match.group(2)
    key = _AGENT_TO_KEY.get(agent)
    if not key:
        return  # plex://movie/... and friends carry no external id
    value = value.split("/")[0].strip()  # thetvdb://73244/1/1
    if not value:
        return
    if key == "imdb":
        if not re.fullmatch(r"tt\d+", value):
            return
    elif not value.isdigit():
        return
    if not ids.get(key):
        ids[key] = value


def extract_ids(item) -> dict:
    """Return {"tmdb": .., "imdb": .., "tvdb": ..} for a Plex item (values may be None)."""
    ids = {"tmdb": None, "imdb": None, "tvdb": None}
    try:
        guids = list(getattr(item, "guids", None) or [])
    except Exception:
        guids = []
    for guid in guids:
        try:
            _absorb_guid(ids, getattr(guid, "id", None))
        except Exception:
            continue
    if not any(ids.values()):
        try:
            _absorb_guid(ids, getattr(item, "guid", None))
        except Exception:
            pass
    return ids


_ARTICLES = ("the ", "a ", "an ")


def normalize_title(title) -> str:
    """Lowercase, drop a leading article, drop punctuation and whitespace."""
    text = str(title or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    for article in _ARTICLES:
        if text.startswith(article):
            text = text[len(article):]
            break
    return text.replace(" ", "")


def unique_key(kind, ids, title, year) -> str:
    """Stable identity for a title across libraries and servers."""
    ids = ids or {}
    for source in ("tmdb", "imdb", "tvdb"):
        value = ids.get(source)
        if value:
            return "%s:%s" % (source, value)
    return "%s|%s|%s" % (kind, normalize_title(title), year if year else "")


# --- JSON --------------------------------------------------------------------

def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print("!! WARNING: could not read %s: %s" % (path, exc), flush=True)
        return default


def save_json(path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
