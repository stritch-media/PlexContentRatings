# PlexContentRatings

Not a software product. This is a Claude-driven workflow for filling in missing
or bogus **content ratings** on two Plex servers, with small Python helper
scripts to talk to Plex. The user (Kyle) runs `/check-ratings` here; Claude does
the research and judgment; the scripts do the reading/writing against Plex.

## The setup

| Server               | Libraries                          |
|----------------------|------------------------------------|
| Appbox               | 4K Movies, Movies, 4K TV Shows, TV Shows |
| Kyle's Plex Server   | 4K Movies, Movies, 4K TV Shows, TV Shows |

Each of the 8 libraries has a **smart collection** named `*NEEDS PROPER RATING*`
(literal asterisks in the name). It is filter-based, so an item drops out of the
collection on its own once a valid rating is written — the scripts never need to
edit collection membership.

Titles repeat across libraries and servers (4K + regular, both servers). Every
unique title is researched **once**; the decision fans out to every Plex
location on apply.

## Rating rules (US-based user)

**TV shows** — always the US TV Parental Guidelines format, applied at the
show level: `TV-Y`, `TV-Y7`, `TV-G`, `TV-PG`, `TV-14`, `TV-MA`. Never
`TV-Y7-FV` — "FV" is a content descriptor; use plain `TV-Y7`.

**Movies** — MPAA (`G`, `PG`, `PG-13`, `R`, `NC-17`) *or* US TV format. Which
one is decided by this precedence, stop at the first hit:

1. **Official US MPAA rating** exists (TMDB US certification, IMDb `Rated`,
   MPAA/FilmRatings) → use it.
2. **A US streamer has assigned a TV-style rating** (Netflix, Hulu, Prime
   Video, Max, Peacock, Paramount+, Apple TV+, Disney+, Tubi, etc.). Common for
   streaming originals and for unrated films acquired by streamers. The user
   explicitly prefers a real streamer TV rating over an estimated MPAA rating
   → use it.
3. **Nothing US-official anywhere** → estimate in **MPAA style**. Any foreign
   board rating (BBFC, FSK, ACB, CBFC, Eirin, KMRB, etc.) is a *strong hint*
   but not a mechanical mapping — still research the actual content
   (synopsis, IMDb Parents Guide, Common Sense Media, reviews) before deciding.

**TV precedence:** official US TV rating (TMDB content_ratings `US`, TVDB,
network/streamer listing) → otherwise research and estimate in TV style,
foreign ratings as hints.

**Never write** `NR`, `Not Rated`, `Unrated`, `TBD`, or a non-US value
(`de/16`, `gb/15`, ...). Replacing those is the whole point.

Estimation criteria and a foreign-rating hint table live in
`reference/rating-guidelines.md`. Read it before estimating.

## Workflow (`/check-ratings`)

The skill at `.claude/skills/check-ratings/SKILL.md` is the entry point. Steps:

1. `python scripts/gather.py` → `data/queue.json`. Connects to both servers,
   walks all 8 libraries, dumps every item in the collection with title, year,
   type, current `contentRating`, ratingKey, library, server, and GUIDs
   (`tmdb://`, `imdb://`, `tvdb://`).
2. Dedupe on GUID (fallback: normalized title + year + type). Skip anything
   already present in `data/ratings-cache.json`.
3. For each new unique title: `python scripts/lookup.py` pulls TMDB / OMDb
   ratings; Claude does web research for anything that comes back without a US
   rating (streamer pages first, then content research).
4. Claude writes `data/decisions.json` and a readable `data/decisions.md`
   table: title, year, type, proposed rating, source (`official-mpaa`,
   `official-tv`, `streamer`, `estimated`), confidence, one-line rationale,
   and the list of Plex locations it applies to.
5. **User reviews and approves** (may edit individual entries). Nothing is
   written to Plex before approval.
6. `python scripts/apply.py` writes and **locks** `contentRating` at every
   location, then merges the decisions into `data/ratings-cache.json`.
7. Commit `data/ratings-cache.json` (+ `calibration.md`) and push to the
   private GitHub repo (`stritch-media/PlexContentRatings`) so the decision
   history is backed up.

The cache is permanent memory across runs: a title decided once is never
re-researched. If the user overrides a rating, update the cache entry too.

## Files

```
CLAUDE.md
.env                       Plex token, server URLs, API keys (gitignored)
.env.example               Template for .env
requirements.txt           plexapi, requests, python-dotenv
scripts/
  plex_common.py           Server connection + library/collection helpers
  gather.py                Step 1 — build data/queue.json
  lookup.py                Step 3 — TMDB/OMDb lookup for the queue
  apply.py                 Step 6 — write + lock ratings from decisions.json
reference/
  rating-guidelines.md     MPAA + TV Parental Guidelines criteria, foreign hints
data/
  queue.json               Current run's gathered items (regenerated each run)
  decisions.json / .md     Current run's proposed ratings (awaiting approval)
  ratings-cache.json       Permanent: GUID → decided rating, source, date
```

## Plex API notes

- Library: `python-plexapi`. Each server has its **own token**
  (`PLEX_SERVER_n_TOKEN`). Connect with `PlexServer(url, token)`; fall back to
  `MyPlexAccount(token=token).resource(name).connect()` if that server's URL
  is blank.
- Content rating is free text in Plex. Write + lock with
  `item.editContentRating("TV-MA", locked=True)`. Locking stops the metadata
  agent from overwriting it on refresh.
- Modern-agent libraries expose `item.guids` (list of `tmdb://`, `imdb://`,
  `tvdb://`). Legacy-agent items only have a single `item.guid` string — parse
  the id out of it.
- Collections: `library.collection("*NEEDS PROPER RATING*").items()`.
- Show-level rating is what Plex displays for a series; episodes are left
  alone unless the user asks otherwise.

## Model policy

The user wants the cheapest model that gives good results, chosen
automatically — never ask which model to use.

- **Research/estimation subagents: `model: "sonnet"`** (Sonnet 5). Multi-step
  web research + a rating judgment is squarely in its range; Haiku 4.5 is
  weaker at chained web research, Opus/Fable are overkill.
- **Orchestrator** (the session model) only dedupes, dispatches, builds the
  review table, and spot-checks. It does not research titles itself.
- **Calibration** results live in `data/calibration.md`. Escalate to `opus`
  only if spot-checks show real disagreement; trial `haiku` only after Sonnet
  has proven consistently accurate. Any change to the default is recorded
  here and in the skill.

## Working style for this project

- The user is not a Python dev and is not here to maintain code; keep scripts
  small, dependency-light, and loud about errors (print which server/library
  failed and continue).
- Batch the research: do lookups for the whole queue, then research the misses,
  then present one review table. Don't drip-feed titles one at a time.
- When estimating, always give the rationale — the user wants to be able to
  sanity-check a guess at a glance.
- Never apply to Plex without the user's explicit go-ahead on the decisions
  table.
