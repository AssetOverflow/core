# ADR-0174 Phase 3b + Phase 4 — Combined Scope

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Parent ADR:** [ADR-0174 — Held-Hypothesis Comprehension](../decisions/ADR-0174-held-hypothesis-comprehension.md)
**Predecessor PRs:** #416 (Phase 1), #420 (Phase 2), #423 (Phase 3a), #426 (initial-overwrite hazard fix)
**Type:** Combined dispatch pack — Phase 3b is prerequisite for Phase 4 to have anything to operate on

---

## Why combined

Per the 2026-05-28 post-merge diagnostic, layer-by-layer extraction-narrowness fixes do not compound on `train_sample/v1`. Each gsm8k case has 3-5 narrowness layers refusing simultaneously; fixing any single layer admits zero cases because other layers still refuse.

The architectural breakthrough that CAN admit cases is the combination of:

1. **Phase 3b** — compound-clause held hypotheses, so a sentence with multiple anchors produces multiple `Hypothesis` entries in `ProblemReadingState.open_hypotheses` rather than refusing at `_CLAUSE_SPLIT_TOKENS`.
2. **Phase 4** — in-loop `contemplate`, so when constraint elimination leaves `|surviving| ≥ 2` hypotheses, the reader can deterministically consult vault/packs/audit-history to pick the correct interpretation rather than refusing on ambiguity.

Phase 3b without Phase 4 only converts compound-clause sentences from "refuse-at-extraction" to "refuse-at-ambiguous-survival" — no admission lift. Phase 4 without Phase 3b has no `|surviving| ≥ 2` cases to operate on (today's pipeline produces at most 1 survivor per sentence).

Combined, the two phases:
- Admit compound-clause sentences when constraint elimination leaves a unique survivor
- Resolve multi-actor pronoun ambiguity (the defense from PR #423) by consulting gendered-name packs
- Provide the substrate for Phase 5 (legacy parser removal) and any future ADR-0174 evolution

---

## Honest lift expectations

| Phase | Substrate value | Realistic train_sample lift |
|---|---|---|
| 3b alone | Compound-clause held hypotheses | 0 (multi-actor defense refuses, solver gaps prevent admission) |
| 3b + 4 | + in-loop contemplate over name packs | 2-4 cases (cases that admit via single-survivor + gendered-pronoun resolution) |
| 3b + 4 + Phase 5 (solver multi-qty) | + same-actor multi-qty aggregation | 6-8 cases (adds Malcolm/Daniel-style "total of N units" problems) |

**Phase 3b + 4 combined target: +2 to +4 train_sample cases** when paired with the existing solver. The architectural payoff is the substrate, not the score; the score moves come when the solver work in **issue-3 from the post-merge diagnostic** lands alongside.

---

## Architecture overview

```
PARSE
  ├─ sentence has clause_split tokens?
  │    └─ NEW: _try_extract_compound_discrete_count_anchors() → tuple of anchors
  │        (one per clause, shared subject+verb from head clause)
  └─ injector emits one candidate per anchor (Phase 3b)

EMIT
  └─ each candidate → Hypothesis with rank = enumeration order
       (already implemented via hypothesis_from_initial / _from_operation)

ELIMINATE
  └─ eliminate_violating() runs per-hypothesis constraint check
       (Phase 2 — unchanged; Phase 3b just produces more hypotheses for it to act on)

HOLD
  └─ NEW Phase 4: when survivors ≥ 2 (which Phase 3b makes possible),
       invoke contemplate() before declaring ambiguity

CONTEMPLATE (Phase 4 — read-only deterministic search)
  ├─ vault recall (exact CGA) — prior session resolutions
  ├─ pack consult (gendered names, semantic classes, lexicon entries)
  ├─ audit history (prior reader refusals on same token)
  └─ returns Resolution | None — never a guess

ADMIT
  └─ if survivors → 1 after contemplate, admit
  └─ if survivors → 0 (all eliminated), refuse cleanly
  └─ if survivors ≥ 2 after contemplate, refuse with ambiguous_unresolvable trace
```

---

## Phase 3b — Compound-clause held hypotheses

### Files touched

- `generate/recognizer_match.py`
  - New function: `_try_extract_compound_discrete_count_anchors(statement, padded_lower, spec) -> tuple[Mapping, ...] | None`
  - The compound-aware extractor: splits on conjunctive separators (` and `, `, ` followed by digit), requires each clause to match the discrete-count regex shape with shared subject+verb from the head clause
  - Refusal-preferring: if any clause doesn't match the per-clause regex, return None (refuse the whole sentence)
  - Returns a tuple of anchors, all carrying the SAME `subject_role` / `verb_token` / `anchor_kind` from the head clause
- `generate/recognizer_anchor_inject.py`
  - `inject_discrete_count_statement` already iterates `match.parsed_anchors` and builds one candidate per anchor — NO CHANGE needed. Phase 3b lights this up by populating `parsed_anchors` with N entries instead of 1.
- `generate/math_candidate_graph.py`
  - The Phase 2 hypothesis-emission wiring already handles `len(injected) > 1` correctly — it builds one Hypothesis per injection, runs `eliminate_violating`, requires `len(admitted) == len(injected)` for the per_sentence_choices append.
  - **No wiring change required for Phase 3b** — the upstream (extractor producing N anchors) is the only new work.
- `generate/comprehension/state.py`
  - **HYPOTHESIS_CAP raise.** Today `HYPOTHESIS_CAP = 4`. Case 0040 has 5 anchors (`"2 horses, 5 dogs, 7 cats, 3 turtles, and 1 goat"`). Raise to **8** or refuse on cap-exceed with a documented marker. Recommendation: raise to 8 with a comment citing case 0040 as the empirical justification.

### Constraints

- Refusal-preferring discipline: if ANY clause's extraction fails, refuse the whole sentence. Admitting partial state from a recognized-but-incomplete compound is the wrong=0 hazard (same shape as ADR-0167 case-0050 lesson).
- Shared subject + verb: every emitted anchor MUST share the same `subject_role`, `verb_token`, and `anchor_kind`. Compound sentences with mixed verbs/subjects (`He bench presses 15 pounds and does 3 sets`) refuse at the compound extractor.
- Whitelisted verb only: the head clause's verb must be in `_POSSESSION_VERBS` or `_ACQUISITION_VERBS`. Compound extension does NOT widen the verb set (that's separate VE work).
- Pronoun-subject head: when the head clause's subject is a pronoun, the same `requires_pronoun_resolution` marker fires on ALL anchors. The Phase 3a wiring (and its multi-actor defense) operates correctly on multi-anchor compounds.

### Tests

- New `tests/test_adr_0174_phase3b_compound_clause.py`:
  - Pure conjunctive list with proper-noun subject: admits (Malcolm/followers)
  - 5-anchor list with pronoun subject + single-actor antecedent: admits via Phase 3a wiring (Daniel/animals)
  - 5-anchor list with pronoun subject + multi-actor antecedent: refuses via multi-actor defense
  - Mixed-verb compound: refuses at compound extractor (preserves wrong=0)
  - Multiplicative-tail compound (`...and three times as long`): refuses at compound extractor
  - Cap enforcement: 9-anchor compound refuses
  - All-or-nothing: if clause 3 of 5 fails to ground, all 5 dropped (no per_sentence_choices append)

### Acceptance gate

- 0 lift on train_sample admitted as expected
- `wrong=0` invariant preserved
- Case 0050 hazard test passes
- Multi-actor pronoun defense still fires on compound + pronoun cases
- Smoke 67/67, packs 141/141

---

## Phase 4 — In-loop contemplate

### Files touched

- `generate/comprehension/contemplate.py` (NEW module — ~300 lines):
  - `Resolution` dataclass — `kind ∈ {"eliminate", "admit_unknown"}`, `target_hypothesis_id`, `sub_question`, `source ∈ {"vault", "pack", "audit_history"}`, `evidence` tuple.
  - `contemplate(state: ProblemReadingState, residual: tuple[Hypothesis, ...]) -> Resolution | None`
  - Three deterministic adapters, consulted in order:
    1. `_consult_vault(...)` — exact CGA recall over `VaultStore` for prior session evidence
    2. `_consult_packs(...)` — closed-set lookup over loaded packs (initial Phase 4 use case: gendered name pack for pronoun resolution)
    3. `_consult_audit_history(...)` — read-only over reader-refusal log
  - Returns `None` on any ambiguous result (evidence supports multiple hypotheses equally) — refusal-preferring.
- `generate/math_candidate_graph.py`:
  - When `eliminate_violating` returns `len(survivors) >= 2`, invoke `contemplate` before treating as ambiguous-refusal.
  - On successful resolution: apply the `Resolution` (eliminate the indicated hypothesis OR admit a previously-held unknown) and continue admission with the unique survivor.
  - Trace events: `{"layer": "contemplate", "phase": 4, "outcome": "resolved" | "ambiguous_unresolvable", "source": "...", "evidence": [...]}`
- `generate/comprehension/state.py`:
  - No change. The substrate (`open_hypotheses`, `UnknownHeld`) is already in place.

### First concrete Phase 4 use case: gendered pronoun resolution

The multi-actor pronoun hazard defense (PR #423) currently refuses on ambiguity. Phase 4 turns the defense into an admission opportunity:

**Today (multi-actor refusal):**
```
"Alice has 5 marbles. Bob has 3 marbles. She buys 2 marbles."
  → no_antecedent_ambiguous (refuse, candidate_antecedents=[Alice, Bob])
```

**With Phase 4 + gendered names pack:**
```
"Alice has 5 marbles. Bob has 3 marbles. She buys 2 marbles."
  → contemplate("She", residual=[Alice→hypothesis_0, Bob→hypothesis_1])
  → _consult_packs: gendered_names["Alice"] = "female", gendered_names["Bob"] = "male", "She" requires female
  → Resolution(kind="eliminate", target_hypothesis_id=1, source="pack",
               sub_question="which antecedent is female-gendered?")
  → admit hypothesis_0 (Alice + buy 2)
```

The pack consulted is a new closed-set artifact: `language_packs/data/en_core_names_v1/gender.jsonl` (or similar). Building this pack is part of Phase 4 scope — small (~200 entries covering common English first names), reviewed through the standard HITL corridor (ADR-0150/0152), refusal-preferring on unknown names.

### Constraints

- **No LLM, no sampling, no normalization.** `contemplate` is deterministic search over already-ratified evidence. Ambiguous results return `None` and the reader refuses cleanly.
- **Read-only over evidence sources.** No vault writes, no pack mutations, no audit-history modification. Any new evidence proposed by contemplation rides the existing offline HITL corridor.
- **Trust boundary.** Vault recall uses exact CGA (no approximation). Pack consults are closed-set membership checks. Audit history is read-only over an append-only log. No new code execution surfaces.
- **HYPOTHESIS_CAP unchanged.** If 5 hypotheses survive and contemplate eliminates 3, leaving 2 ambiguous, the reader still refuses (no second contemplate pass within the same sentence — bounded by structural assertion).

### Tests

- New `tests/test_adr_0174_phase4_contemplate.py`:
  - Empty residual: contemplate returns None (no-op)
  - Single survivor: contemplate returns None (caller doesn't need to disambiguate)
  - Gendered pronoun + gendered name pack: resolves correctly, returns Resolution
  - Gendered pronoun + unknown name: returns None (refuse cleanly)
  - Multi-actor + same-gender antecedents: returns None (no disambiguation possible)
  - Vault has prior resolution: returns Resolution sourced from vault
  - Determinism: same input → same Resolution byte-identical
  - Trace event shape validated

### Acceptance gate

- ≥ 2 train_sample case lift (the multi-actor cases that resolve via gender pack)
- `wrong=0` invariant preserved
- Case 0050 hazard test passes
- New `en_core_names_v1` pack passes the pack-test discipline (CLAUDE.md §Semantic Pack Discipline)
- Smoke + packs + lanes green

### Open questions (resolve before Phase 4 PR)

1. **Gendered names pack scope.** Initial proposal: ~200 common English first names from Census Bureau / SSA public data, manually reviewed for unambiguous gender. Edge cases (Jordan, Alex, Casey, etc.) are NOT in the pack — they return None from `_consult_packs` and the reader refuses, preserving wrong=0.
2. **Contemplate evidence precedence.** ADR-0174 §Open Q#3 proposed `vault > packs > audit_history`. Confirm against actual evidence formats before Phase 4 wires the adapters.
3. **Pronoun-pack source.** Whether `she/he/they/it` → gender mappings live in `en_core_names_v1` or a separate `en_core_pronouns_v1` pack. Recommendation: separate pack, because pronouns are syntactic and names are semantic — different review pathways.

---

## Sequencing

```
Phase 3b PR
  ├─ extractor + cap raise + tests (parallel-safe)
  └─ no math_candidate_graph wiring change needed

Phase 4 PR (stacks on Phase 3b)
  ├─ contemplate.py + tests (parallel-safe)
  ├─ en_core_names_v1 pack creation + tests (parallel-safe)
  ├─ math_candidate_graph wiring at the |survivors|≥2 site
  └─ acceptance verified across all suites
```

Both PRs are operator-dispatchable; recommend **Opus** for both (wrong=0 hazard surfaces on the extractor and the resolution-vs-refusal decision).

---

## Truth tests

Before any merge:

1. **wrong=0 invariant.** `train_sample/v1` report wrong=0.
2. **Case 0050 canary.** Explicit test passes (memory `feedback-wrong-zero-hazard-case-0050`).
3. **Multi-actor defense preserved.** When `contemplate` can't disambiguate, the existing `no_antecedent_ambiguous` refusal fires (memory `project-adr-0174-multi-actor-pronoun-hazard`).
4. **Determinism.** Two runs of `parse_and_solve` on the same input produce byte-identical reader_trace including contemplate events.
5. **Lift evidence.** At least 1 train_sample case lifts from refused→correct via the combined 3b+4 wiring with a `lookback` and `contemplate` trace event both visible.

---

## What this combined scope DELIBERATELY excludes

- **Solver multi-quantity aggregation.** `Daniel has 2 horses. Daniel has 5 dogs. How many animals?` would need a superordinate-noun pack and solver support — separate ADR scope.
- **Verb expansion.** VE-A/B/C brief covers this. Phase 3b refuses on compound sentences with non-whitelisted verbs; Phase 4 doesn't widen the verb set.
- **Same-actor same-unit cumulative semantics.** Resolved by the PR #426 hazard fix (refuse, not silent overwrite). Cumulative addition requires explicit operation verbs ("buys", "receives") which already work.
- **Question-side pronoun resolution.** Phase 4's contemplate is statement-scoped in this scope. Question-side pronoun resolution is Phase 4.1 follow-up.
- **Per-token apply_word integration.** Phase 5 work — retire legacy parser, move admission into the reader.

---

## Cross-references

- Parent ADR: `docs/decisions/ADR-0174-held-hypothesis-comprehension.md` (Proposed; Phase 1-3a + amendment shipped)
- Predecessor PRs: #416, #420, #423, #426
- Lookback review doctrine: `CLAUDE.md §Lookback Review Discipline`
- Hazards memory: `project-adr-0174-multi-actor-pronoun-hazard`, `feedback-wrong-zero-hazard-case-0050`
- Thesis anchor: `[[thesis-decoding-not-generating]]` — every contemplate resolution must find evidence that already exists; the engine decodes, it does not invent
- HITL corridor: ADR-0150/0152/0155/0161 — Phase 4's pack additions ride this corridor unchanged
