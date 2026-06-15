# Salvaged stash keepers — 2026-06-14

Two pieces of **genuinely un-landed work** rescued from the local `git stash`
stack before the stack was pruned. Everything else in the stack (10 entries)
was verified superseded, already-landed, or scratch, and dropped.

These are **preserved, not integrated** — they live here as artifacts so a
deliberate integration can happen later, rather than being wired into the
runtime pack/parser implicitly. Nothing here is registered with a pack
manifest or imported by any runtime path.

## 1. `en_core_math_v1` lexicon vocabulary (`lexicon-en_core_math_v1/`)

- **Source:** stash `On feat/reader-phase2-statements` (2026-05-26), commit `220c1bf`.
- **Status in `main`:** the `en_core_math_v1` pack exists (`compositions/`,
  `frames/`) but has **no `lexicon/` directory** — these 8 files were never landed.
- **Content:** 553 provenance-tagged lemma entries feeding the phase-2 GSM8K
  reader's recognition coverage:

  | file | category | entries |
  |---|---|---|
  | `accumulation_verb.jsonl` | accumulation verbs (add, build, collect…) | 21 |
  | `capacity_verb.jsonl` | capacity verbs (fill, complete, pack…) | 19 |
  | `count_unit_noun.jsonl` | countable unit nouns (apple, bag, book…) | 63 |
  | `currency_unit_noun.jsonl` | currency nouns (dollar, cent, profit…) | 9 |
  | `drain_token.jsonl` | function-word / filler filter | 274 |
  | `proper_noun_entity_female.jsonl` | female entity names | 68 |
  | `proper_noun_entity_male.jsonl` | male entity names | 91 |
  | `time_unit_noun.jsonl` | time unit nouns (day, hour, week…) | 8 |

- **To integrate:** `git mv` into `language_packs/data/en_core_math_v1/lexicon/`,
  then register in the pack manifest with checksums hashing the bytes on disk
  (per CLAUDE.md pack discipline) and add pack tests. Do **not** drop them into
  the live pack dir without manifest registration.
- **Caveat:** the project pivoted (GSM8K serving demoted to diagnostic; deductive
  logic is the flagship). Confirm this vocabulary is still wanted before wiring it.

## 2. `_repeated_volume_candidates` extractor (`stash-0-repeated-volume-extractor.patch`)

- **Source:** stash `On fix/main-red-tests` snapshot of earlier
  `feat/adr-0190-discrete-count-injection` work, commit `9718c73`.
- **Status in `main`:** `def _repeated_volume_candidates` is **absent** from
  `generate/math_candidate_parser.py`. ADR-0190 landed probe-side; this is the
  statement-side companion ("inert until question side") that never landed.
- **Content:** 89-line diff against `generate/math_candidate_parser.py`.
- **To integrate:** `git apply` against the current parser and resolve any drift
  (the patch is against a ~3-week-old base, so a clean apply is not guaranteed).

## Provenance note

Recovered during a stash/worktree cleanup pass. The full triage (12 stashes,
which were dropped and why) is in the session history. Keeper commit SHAs at
salvage time: lexicon `220c1bfd`, extractor `9718c73f`.
