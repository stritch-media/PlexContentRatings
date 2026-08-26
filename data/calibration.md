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
