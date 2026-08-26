---
name: check-ratings
description: Gather every title in the *NEEDS PROPER RATING* collections on both Plex servers, find or estimate a proper US content rating for each, present a review table, and (after approval) apply and lock the ratings in Plex.
---

# /check-ratings

Read `CLAUDE.md` and `reference/rating-guidelines.md` first. The rating rules and
precedence there are binding.

## 1. Gather

```
python scripts/gather.py
```

Produces `data/queue.json`. If a server or library fails to connect, report it
and continue with the rest — do not abort the whole run. Summarize: N items
across M libraries, K unique titles, J already in the cache.

## 2. Dedupe and cache check

Unique key = first available of `tmdb`, `imdb`, `tvdb` id; fallback
`type|normalized-title|year`. Anything already in `data/ratings-cache.json`
is reused (still listed in the review table, marked `cached`) unless the
user asks for a re-check.

## 3. Lookup

```
python scripts/lookup.py
```

Annotates each unique title with TMDB US certification / content rating and
OMDb `Rated`. Titles that come back with a valid US rating are marked
`official-mpaa` or `official-tv` and need no further research.

## 4. Research the misses

For each title with no valid US rating, in this order:

1. **US streamer listings** — web search for the title on Netflix, Hulu,
   Prime Video, Max, Peacock, Paramount+, Apple TV+, Disney+, Tubi. A real
   TV-style rating from a streamer wins over any estimate (`streamer`).
2. **Content research** — IMDb Parents Guide, Common Sense Media, Kids-In-Mind,
   reviews, synopsis. Foreign board ratings are strong hints, not mappings.
3. Estimate per `reference/rating-guidelines.md`. Movies → MPAA style, TV →
   TV style. Mark `estimated` with confidence `high` / `medium` / `low`.

### Model policy (do not ask the user; this is decided)

Research and estimation run in **subagents with `model: "sonnet"`**, in
parallel, ~10 titles per agent, `subagent_type: "general-purpose"`. The
orchestrator never researches titles itself — it only dedupes, dispatches,
assembles the table, and spot-checks. Each subagent gets: the list of titles
(with year, type, current rating, GUIDs, and any TMDB/OMDb results), the full
text of `reference/rating-guidelines.md`, the precedence rules from
`CLAUDE.md`, and must return one JSON object per title:

```json
{"key": "...", "rating": "TV-MA", "source": "streamer|estimated",
 "confidence": "high|medium|low", "rationale": "one line", "evidence_url": "..."}
```

**Calibration:** on the first run that produces estimates (and any time the
model policy changes), the orchestrator independently re-checks ~10 random
`estimated` entries. Report agreement in the review summary. If agreement is
poor, escalate the default to `opus` and note it in `CLAUDE.md`; if it's
consistently excellent, a trial of `haiku` on a sample is worth a try before
switching. Record the outcome of each calibration in `data/calibration.md`.

## 5. Present for review

Write `data/decisions.json` and `data/decisions.md`. Show the user the table:

| Title (Year) | Type | Current | Proposed | Source | Conf. | Rationale | Locations |

Group by source so official hits are easy to skim and estimates get attention.
Then stop and wait for approval. Apply any edits the user makes to
`decisions.json` before continuing.

## 6. Apply

Only after explicit approval:

```
python scripts/apply.py
```

Writes and locks `contentRating` at every location, merges into
`data/ratings-cache.json`, and prints a per-location success/failure list.
Afterwards, re-run `gather.py` and confirm the applied titles have left the
smart collections; report any stragglers.

## 7. Commit

After a successful apply, commit the updated decision history and push:

```
git add data/ratings-cache.json data/calibration.md
git commit -m "check-ratings: <N> titles, <M> locations (<date>)"
git push
```

Only the cache and calibration log change in a normal run; if the skill,
guidelines, or scripts were also edited during the run, include them. Never
stage `.env`, `data/queue.json`, or `data/decisions.*` (they're gitignored,
but don't `git add -A` blindly). If the push fails (offline, auth), report it
and leave the commit local — do not retry in a loop.
