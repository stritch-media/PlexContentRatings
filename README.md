# PlexContentRatings

A small toolchain that finds every movie and show in Plex with a missing or
bogus content rating, works out the correct US rating, and writes it back.

It runs against two Plex servers and eight libraries. Since August 2026 it has
resolved 63 unique titles across 94 library locations.

## The problem

Plex pulls content ratings from its metadata agents, and the result is messy.
Streaming originals come through as `NR` or `Not Rated`. Foreign releases
show up as `de/16` or `gb/15`. Older films and documentaries often have
nothing at all. Parental controls and library filters key off this field, so
a bad value means a title is either hidden from everyone or visible to kids.

Fixing it by hand means opening each title, searching a few sites, deciding on
a rating, typing it in, and locking it so the next metadata refresh does not
undo the work. Across two servers and thousands of titles that is not
sustainable.

## How it works

Each library has a smart collection called `*NEEDS PROPER RATING*` whose
filter catches every item with an invalid rating. Because it is filter based,
a title drops out of the collection on its own once a valid rating is written.
The scripts never have to manage collection membership.

The pipeline runs in four steps:

1. **Gather.** `scripts/gather.py` connects to every configured server, walks
   each library's collection, and writes `data/queue.json`. Titles are
   deduplicated across servers and libraries by TMDB, IMDb, or TVDB ID, with a
   title and year fallback for legacy agent items. A server that fails to
   connect is reported and skipped so one outage does not stop the run.
2. **Lookup.** `scripts/lookup.py` checks TMDB and OMDb for an official US
   certification. Anything that comes back with a real MPAA or TV rating needs
   no further work.
3. **Research and decide.** For the rest, Claude Code research agents check US
   streamer listings first (a real TV-MA from Netflix beats any guess), then
   fall back to content research and an estimate under the rules in
   `reference/rating-guidelines.md`. Every decision carries a source, a
   confidence level, and a one line rationale.
4. **Review and apply.** The proposed ratings land in a review table. Nothing
   touches Plex until the table is approved. `scripts/apply.py` then writes
   and locks `contentRating` at every location and merges the decisions into
   `data/ratings-cache.json`, which is permanent memory across runs.

The precedence rules, the rating guidelines, and the research procedure all
live in plain text files (`CLAUDE.md`, `reference/`, and the skill under
`.claude/skills/`). Changing how a rating gets decided means editing a
document, not code.

## Rating rules in brief

- TV shows always get a US TV Parental Guidelines rating (`TV-Y` through
  `TV-MA`), applied at the show level.
- Movies get the official MPAA rating if one exists. If not, a US streamer's
  TV style rating wins over any estimate. Only when neither exists does the
  tool estimate, in MPAA style, using foreign board ratings as hints rather
  than mechanical mappings.
- `NR`, `Not Rated`, `Unrated`, `TBD`, and non US values are never written.
  Replacing those is the whole point.

The full criteria, including a foreign rating hint table and how to weigh
language, violence, sex, and fright separately, are in
`reference/rating-guidelines.md`.

## Calibration

Research runs on a cheaper model, and the orchestrating session spot checks a
sample of the estimates on each run. Disagreements and the fixes they led to
are logged in `data/calibration.md`. Several of the rules in the skill came
directly from those misses, for example treating Amazon's "16+" age tier as if
it were a TV rating, or under rating profanity heavy stand up specials.

## Running it

```
pip install -r requirements.txt
cp .env.example .env     # fill in Plex tokens and API keys
python scripts/gather.py
python scripts/lookup.py
# research and build data/decisions.json (the /check-ratings skill does this)
python scripts/apply.py
```

`.env` holds one token per Plex server plus TMDB and OMDb keys. It is
gitignored and token values are never printed. Each script resolves paths from
its own location, so the working directory does not matter.

The research step is driven by the `/check-ratings` skill in Claude Code. The
three Python scripts work on their own, but without the skill you are doing
the research by hand and writing `data/decisions.json` yourself.

## Layout

```
CLAUDE.md                      Project rules and workflow for the agent
.claude/skills/check-ratings/  The /check-ratings skill (the entry point)
scripts/
  plex_common.py               Server config, connections, ID extraction, rating normalization
  gather.py                    Build the queue from every server and library
  lookup.py                    TMDB and OMDb lookup for the queue
  apply.py                     Write and lock ratings, update the cache
reference/
  rating-guidelines.md         MPAA and TV criteria, foreign rating hints
data/
  ratings-cache.json           Every decision made so far, with source and rationale
  calibration.md               Spot check log and the rule changes that came from it
```

## A note on how this was built

The Python was written with Claude Code. The rating rules, the precedence
order, the streamer first research procedure, the decision to lock ratings
after writing, and the review gate before anything touches Plex are the parts
I designed, and they are the parts that make the tool actually work on a real
library. The scripts are deliberately small and loud about errors so they are
easy to reason about when something goes wrong.
