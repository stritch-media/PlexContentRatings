# Calibration log

## 2026-08-25 — first run, Sonnet 5 research subagents (23 titles, 3 agents)

Orchestrator (Fable 5) re-checked all 7 `estimated` entries plus 2 `streamer`
claims by fetching the cited listing pages directly.

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| Amandaland | TV-14, streamer (Amazon "16+") | Amazon 16+ confirmed — but that is an age tier, not a TV rating. Source mislabelled; 16+ w/ foul language + BBFC 15 sitcom → TV-MA | **Corrected** → TV-MA, estimated |
| Jimmy O. Yang: Finally Home | PG-13, estimated | Apple TV: Unrated. Prime Video: 16+ "foul language". Profanity-driven stand-up is R under the guidelines, not PG-13 | **Corrected** → R, estimated |
| There's Something Wrong with the Children | R, estimated | Common Sense: NR, frequent f-word, bloody stabbings, weed → R | Agree |
| The Twelve (AU) | TV-MA, estimated | JustWatch US: not available in US, 18+ | Agree |
| One Night (2023) | TV-MA, estimated | JustWatch page 404; AU MA15+ (sexual violence, self-harm) | Agree |
| Behind the Rage | PG-13, estimated | Kanopy page would not load; no US TV rating found | Agree (unverified) |
| Sword And Scale | TV-MA, estimated | Not re-checked (no listing exists) | Agree on content |
| Have You Seen Andy? | TV-14, streamer (HBO Max via JustWatch) | HBO Max page shows no rating in fetched HTML; Apple says PG. Kept TV-14 | Agree, unverified |
| Streamer claims (Tubi/Apple/Netflix/PBS/Paramount+) | 12 titles | Not individually re-fetched; agents cited direct provider URLs | Trusted |

**Result:** 5/7 estimates agreed; 2 corrected. Both misses were the same
failure mode — treating Amazon's "16+" age tier as a TV rating, and
under-rating profanity-heavy stand-up. Streamer-lookup work was excellent
(15 of 23 titles got a real US rating). **Decision: keep Sonnet as default.**
Added guidance to the skill prompt about Amazon age tiers.

## 2026-08-30 — second run, Sonnet 5 research subagents (8 titles, 2 agents)

Orchestrator (Fable 5) re-checked the 1 `streamer` claim and the 2 weakest
`estimated` entries. IMDb Parents Guide pages returned 403 to the orchestrator
(agents had fetched them successfully), so checks used Tubi / Prime / Shudder.

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| Grave Encounters | TV-MA, streamer (Tubi) | Tubi page shows literal "TV-MA" | Agree, verified |
| Hellbender | PG-13, estimated | Prime 16+ with "violence, foul language"; Sonnet's own note said IMDb profanity "Moderate" (multiple f-words = R per guidelines) | **Corrected** -> R |
| One Cut of the Dead | R, estimated | Prime 16+ "violence, alcohol use"; comedic but persistent dismemberment gore; BBFC 15 / FSK 16 | Agree (PG-13 alt noted) |
| When Evil Lurks, Act of Killing, No Bears, Philadelphia Story, Shop Around the Corner | estimated | Rationale + foreign hints consistent with guidelines | Agree, not re-fetched |

**Result:** 7/8 agreed; 1 corrected. The miss is the same under-rating-profanity
pattern seen on 2026-08-25 (Prime "16+ foul language" should push to R).
Correct age-tier handling this time — no tier was mislabelled as a rating.
**Decision: keep Sonnet as default.**

## 2026-09-08 — Sonnet 5 research subagent (3 titles, 1 agent)

No `estimated` entries this run (2 official via TMDB, 3 `streamer`). Orchestrator
(Fable 5) re-fetched all 3 cited Prime Video US pages.

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| All or Nothing: Manchester City | TV-MA, streamer (Prime) | Page shows literal "TV-MA", 16+ tier, "alcohol use, foul language" | Agree, verified |
| Decades in Sports | TV-14, streamer (Prime) | Page shows literal "TV-14", 13+ tier on episodes | Agree, verified |
| A Beautiful Obsession | TV-MA, streamer (Prime) | Page shows literal "TV-MA", 16+ tier, "foul language" | Agree, verified |

**Result:** 3/3 verified. Age tiers correctly treated as hints, not ratings.
**Decision: keep Sonnet as default.**

## 2026-09-14 — Sonnet 5 research subagent (2 titles, 1 agent)

Both titles came back `estimated` (no MPAA, no literal streamer rating).
Orchestrator (Fable 5) re-checked both by fetching Apple TV US, MUBI, and
searching Shudder/AMC+ listings (Shudder page renders client-side; empty HTML).

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| Rosebush Pruning | R, estimated (medium) | Apple TV US: Unrated. MUBI: generic "MATURE" badge only. BBFC 18 (sexual violence, strong sex, nudity). R is the right US call; NC-17 unlikely for an arthouse MUBI release | Agree, verified |
| Tigers Are Not Afraid | R, estimated (high) | Apple TV US: "Unrated", 15+ tier. Prime 16+. Common Sense: multiple f-words, child-involved violence/gore | Agree, verified |

**Result:** 2/2 agreed. Age tiers (Apple 15+, Prime 16+) and MUBI's "MATURE"
badge were all correctly treated as hints, not ratings. **Decision: keep
Sonnet as default.**

## 2026-09-17 — Sonnet 5 research subagent (1 title, 1 agent)

Only 1 title needed research (2 of 3 had an official US rating from OMDb).
No `estimated` entries this run. Orchestrator (Fable 5) re-fetched the cited
Tubi page and independently verified the Hulu rating.

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| The Thief of Bagdad (1924) | TV-PG, streamer (Tubi) | Tubi page shows literal "TV-PG"; year 1924, dir. Raoul Walsh, starring Douglas Fairbanks — confirmed NOT the 1940 Technicolor remake | Agree, verified |
| Pizza Movie (2026) | n/a — official via OMDb | Hulu press listing confirms TV-MA | Agree, verified |

**Result:** 1/1 agreed. The identified risk on this title was confusing the
1924 silent with the 1940 remake; the agent checked year/director/star on each
Tubi listing before citing it, which is the right habit for remade titles.
Correctly applied precedence rule 2 (real streamer TV rating beats an MPAA
estimate) rather than estimating PG for a pre-1968 film.
**Decision: keep Sonnet as default.**

## 2026-09-21 — Sonnet 5 research subagent (1 title, 1 agent)

No official US rating (TMDB US "NR", OMDb "Not Rated"). No `estimated`
entries. Orchestrator (Opus 5) re-fetched the cited Prime Video US page directly.

| Title | Sonnet said | Check result | Verdict |
|---|---|---|---|
| Valhalla Rising (2009) | TV-MA, streamer (Prime), medium | Prime Video US page shows literal "TV-MA", "nudity, violence, foul language"; confirmed Refn / Mads Mikkelsen film. Agent's medium confidence was only due to needing a text proxy to read the page; raised to high after direct fetch | Agree, verified |

**Result:** 1/1 agreed. Correctly checked for a Blu-ray MPAA rating before
falling through to streamer, and distinguished the literal TV-MA from Prime's
age tiers. **Decision: keep Sonnet as default.**
