# ADR-0179 EX-1/3/4/5 reconciliation (Claude, at the library)

Reconciles the four sealed-lane extraction PRs ChatGPT opened from the remote
brief (`docs/handoff/CHATGPT-REMOTE-BRIEF.md`) into one coherent
`generate/derivation/extract.py`. Each PR was branched independently off `main`
and rewrote the *same* file + the *same* new test, so they conflict pairwise and
could not be merged as-is — they needed integration, not a fast-forward.

## Disposition

| PR | Sub-phase | Verdict | Action |
|----|-----------|---------|--------|
| #452 | EX-1 word-numbers | **Integrated** | folded in (reuses `WORD_NUMBERS`, factor-words excluded) |
| #453 | EX-3 multi-word units | **Deferred — regressed GB-2** | not integrated; see below |
| #451 | EX-4 list-unit inheritance | **Integrated** | folded in (span-tracked; does not flip real 0024) |
| #454 | EX-5 sentence-final numbers | **Integrated** | folded in (empty unit, span-excluded) |
| #450 | Stream A lookback audit | **Sound** | merged (read-only, feeds GB-3) |

The four EX source PRs are superseded by the integration commit and closed with a
pointer here; their authored content survives in the merged file/tests.

## Why EX-3 (multi-word units) was deferred

The brief required "keep units tight" and "don't regress GB-1/GB-2 tests." EX-3's
greedy lowercase unit span (`[a-z]+(?:\s+[a-z]+)*`) does both wrongs:

- **Regresses GB-2.** `compose_sequential("She picked 6 apples and 4 apples.")`
  expects `10.0`. Greedy units read the first unit as `"apples and"` (it swallows
  the connective up to the next digit), so `_same_unit` sees two distinct units
  and the composer refuses. The existing test `test_same_unit_list_sums` flips
  from pass to fail.
- **Doesn't even recover real multi-word units.** Real gold case 0024 is
  `"20 jumping jacks on Monday, 36 on Tuesday, …"`. Greedy lowercase reads
  `"jumping jacks on"` (stops only at the capital `Monday`), so the intended
  `"jumping jacks"` unit is never produced anyway.

EX-3's own tests pass only because they place the unit at a clause end (`"12
jumping jacks."`) where punctuation halts the greedy run. That is a contrived
shape, not the GSM8K shape. A correct multi-word-unit extractor needs a tighter,
non-connective-crossing rule; tracked as future work, not shipped here.

## Honest note on EX-4 and case 0024

EX-4's PR test asserted it "unblocks 0024" using a *fabricated* input
(`"20, 36, 40 and 50 jumping-jacks"`). The real case interleaves numbers with
temporal phrases (`"36 on Tuesday, 40 on Wednesday"`), so the bare-list regex
never fires and 36/40/50 do not inherit the unit. EX-4 is still a real, safe
orthographic primitive (some GSM8K problems do state a unit once after a bare
list), but it does **not** flip 0024. `TestRealCase0024StillBlocked` pins this so
no future change silently re-claims the unblock without proving 438 end-to-end.

## Verification (run at the library)

- **Serving frozen:** lane-SHA gate 8/8 match; `scripts/generate_claims.py
  --check` OK → serving `3/47/0` byte-identical. wrong=0 held.
- **No new test failures:** the 3 failures present (`0163` pronoun, telemetry
  round-trip, and the now-fixed `ms3` decimal-deferred) all pre-existed on `main`.
- **Sealed practice improved:** `build_search_report` went **4/2/44 → 4/1/45**
  (one wrong eliminated, no correct lost). Case **0025** flipped wrong→refused:
  EX-1 now reads `"three"`, so the completeness check sees a quantity the 6×50
  chain doesn't consume and refuses the spurious `300` (gold is `1200`). Richer
  reading → the gate refuses rather than commits a wrong answer. This is the
  intended direction.

## Drift fixed in passing (cleanup-as-you-find)

`tests/test_adr_0176_ms3_search.py::TestDecimalGroundingGapIsDeferred` asserted
decimals were "currently refused." EX-2 (#447) landed decimal grounding and made
that case resolve to the correct `864`; the test was stale on `main`. Renamed to
`TestDecimalGroundingResolves` and updated to assert the flip.
