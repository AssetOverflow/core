# ADR-0174 Phase 3b + Phase 4 — Skeleton Pack

Skeleton artifacts ready to drop into the live tree once the operator
starts implementation per `docs/handoff/ADR-0174-PHASE-3B-4-COMBINED-SCOPE.md`.

Everything in this directory is **inert** — nothing is collected by
pytest, nothing is imported by runtime code. Move files to their
target locations when ready to wire.

## Contents

| Skeleton file | Target location | Purpose |
|---|---|---|
| `test_adr_0174_phase3b_compound_clause.py` | `tests/test_adr_0174_phase3b_compound_clause.py` | Phase 3b acceptance tests |
| `test_adr_0174_phase4_contemplate.py` | `tests/test_adr_0174_phase4_contemplate.py` | Phase 4 acceptance tests |
| `en_core_names_v1/gender.jsonl` | `language_packs/data/en_core_names_v1/gender.jsonl` | Gendered-name pack data |
| `en_core_names_v1/manifest.json` | `language_packs/data/en_core_names_v1/manifest.json` | Pack manifest (checksum verified) |

## Implementer workflow

1. Read the combined scope: `docs/handoff/ADR-0174-PHASE-3B-4-COMBINED-SCOPE.md`
2. Branch off main (or off the merged ADR-0174 Phase 3a base if it lands first)
3. Move the test files into `tests/` — they will run RED until you implement
4. Move the pack into `language_packs/data/`
5. Implement Phase 3b extractor → tests turn GREEN one at a time
6. Implement Phase 4 contemplate + pack loader → remaining tests turn GREEN
7. Run smoke + packs + lanes + train_sample; verify wrong=0 and acceptance lift

## Pack notes

`en_core_names_v1/gender.jsonl` is a **starter** with 30 unambiguously-
gendered English first names. Coverage:

- Names commonly appearing in GSM8K problems (Alice, Bob, Sam, Tom, John, Mary, etc.)
- Both genders evenly represented
- Deliberately excludes ambiguous-gender names (Jordan, Alex, Casey, Pat, Taylor, Morgan, Sam-as-Samantha)

Expansion path: standard HITL corridor (ADR-0150/0152/0155/0161) via
`core teaching propose-from-exemplars` once Phase 4 reads from this
pack and produces refusal evidence on uncovered names.

## Test-skeleton conventions

The skeleton tests use `@pytest.mark.skip(reason="Phase 3b/4 not yet
implemented")` decorators on every test. Imports are inside test
bodies so collection succeeds before the target modules exist. When
implementing, remove the skip decorator and the lazy-import pattern.
