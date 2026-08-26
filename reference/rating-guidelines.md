# Rating guidelines for estimation

Use these when no official US rating (MPAA, US TV, or US streamer) exists.
Rate the *most intense content present*, not the average tone. When torn
between two ratings, note both in the rationale and pick the one a US
streamer would most likely assign.

## US TV Parental Guidelines (shows; also streamer-applied movie ratings)

| Rating     | Audience              | Typical content ceiling |
|------------|-----------------------|-------------------------|
| TV-Y       | All children          | Designed for ages 2–6. Nothing frightening. |
| TV-Y7      | Ages 7+               | Mild fantasy/comedic violence, may scare under-7s. `TV-Y7-FV` if fantasy violence is more intense/combative (action cartoons). |
| TV-G       | General audience      | Little or no violence, no strong language, little or no sexual dialogue. |
| TV-PG      | Parental guidance     | Some suggestive dialogue (D), infrequent coarse language (L — "damn", "hell", occasional "ass"/"bitch"), some sexual situations (S), moderate violence (V). |
| TV-14      | Parents strongly cautioned | Intense suggestive dialogue, strong coarse language (frequent "shit", "asshole", rare or bleeped "fuck"), intense sexual situations (implied, non-explicit), intense violence without extended gore. |
| TV-MA      | Mature audiences      | Graphic violence/gore, explicit or frequent "fuck", explicit sexual content or nudity, hard drug use shown in detail. |

Rough streamer habits: Netflix rates anything with more than a couple of
f-bombs or any nudity TV-MA; most adult-skewing dramas land TV-MA; teen
dramas TV-14; family animation TV-Y7 or TV-PG; documentaries usually TV-14
or TV-MA depending on subject; anime with fan-service or blood is TV-MA,
shonen action is usually TV-14, kids' anime TV-Y7.

## MPAA (movies with no official rating anywhere)

| Rating | Guidance |
|--------|----------|
| G      | Nothing offensive. No nudity, sex, drug use; minimal violence; no language beyond very mild. |
| PG     | Some material may not suit young children. Mild language (a few "damn"/"hell", possibly one "shit"), brief mild violence, no drug use, brief non-sexual nudity at most. |
| PG-13  | Moderate violence (can be intense but not gory/persistent), one non-sexual "fuck" (two is borderline), sexual references and brief sensuality, brief non-sexual nudity, drug use without glorification. |
| R      | Persistent strong language, strong violence/gore, sexual content, nudity, drug use. Most films with multiple f-bombs or any sexual nudity are R. |
| NC-17  | Explicit sexual content beyond R; extremely graphic violence. Rare — only use when the film is clearly built around explicit content. |

When a film is direct-to-video, an indie, or a foreign release with no US
rating, MPAA style is the default — but check US streamers first; a real
TV-style rating from Netflix/Hulu/etc. beats any estimate.

**Pre-1968 films** often carry `Approved` / `Passed` (Hays Code era) on
IMDb/OMDb. That is not a usable rating — treat it as unrated and estimate
in MPAA style. Most land at G or PG; check for a later re-rating (TCM,
Criterion, streamer listings) first.

## Foreign ratings as hints (not mappings)

These suggest a neighborhood. Confirm with actual content research —
boards differ a lot on language vs. violence vs. sex sensitivity (BBFC is
strict on language, FSK lenient on nudity, Japan lenient on violence, etc.).

| Board (country)      | Rating        | Usually near (movie / TV) |
|----------------------|---------------|---------------------------|
| BBFC (UK)            | U             | G / TV-G |
|                      | PG            | PG / TV-PG |
|                      | 12 / 12A      | PG-13 / TV-14 |
|                      | 15            | R (soft) or PG-13 (hard) / TV-14 or TV-MA |
|                      | 18            | R / TV-MA |
| FSK (Germany)        | 0 / 6         | G–PG / TV-G–TV-PG |
|                      | 12            | PG-13 / TV-14 |
|                      | 16            | R or PG-13 / TV-14 or TV-MA |
|                      | 18            | R / TV-MA |
| ACB (Australia)      | G / PG        | G / PG |
|                      | M             | PG-13 / TV-14 |
|                      | MA15+         | R / TV-MA |
|                      | R18+          | R–NC-17 / TV-MA |
| CBFC (India)         | U             | G–PG |
|                      | UA / UA13+    | PG–PG-13 / TV-PG–TV-14 |
|                      | UA16+ / A     | PG-13–R / TV-14–TV-MA |
| Eirin (Japan)        | G             | G–PG |
|                      | PG12          | PG-13 / TV-14 |
|                      | R15+          | R / TV-MA |
|                      | R18+          | R–NC-17 / TV-MA |
| KMRB (South Korea)   | All / 12      | G–PG-13 / TV-G–TV-14 |
|                      | 15            | PG-13–R / TV-14–TV-MA |
|                      | 19 (R)        | R / TV-MA |
| Canada (provincial)  | G / PG        | G / PG |
|                      | 14A           | PG-13 / TV-14 |
|                      | 18A / R       | R / TV-MA |
| Netherlands (Kijkwijzer) | AL/6/9    | G–PG |
|                      | 12            | PG-13 / TV-14 |
|                      | 16 / 18       | R / TV-MA |
| Brazil (ClassInd)    | L / 10        | G–PG |
|                      | 12 / 14       | PG-13 / TV-14 |
|                      | 16 / 18       | R / TV-MA |

**Streamer age tiers are not ratings.** Prime Video's `7+ / 13+ / 16+ / 18+`,
Apple TV's `13+`, and similar age badges are advisory tiers, not TV
Parental Guidelines ratings. Only `TV-xx` / MPAA text counts as `streamer`
source; an age tier is a hint for an `estimated` decision (16+ with "foul
language" on a comedy special or sitcom usually means TV-MA / R territory).

Many Plex agents write these as `gb/15`, `de/16`, `au/MA15+`, etc. in the
content rating field — those values are what the smart collection is
catching and must be replaced.

## Rationale format

One line, content-first, e.g.:

- `Streamer: Netflix lists TV-MA (language, sexual content).`
- `Estimated R: pervasive language, graphic violence per IMDb Parents Guide; BBFC 18 agrees.`
- `Estimated TV-14: horror-comedy, moderate gore, bleeped language; FSK 16.`
- `Estimated TV-PG (low confidence): little info available; family-oriented reality series.`
