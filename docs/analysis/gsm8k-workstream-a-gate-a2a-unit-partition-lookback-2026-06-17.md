# GSM8K Workstream A Gate A2a — unit partition implementation lookback

**Date:** 2026-06-17
**Gate:** A2a — `unit_partition` recognizer-injector + typed solver primitive
**Status:** Implementation complete (PR-ready; not merged)
**Ratification:** `docs/analysis/gsm8k-workstream-a-gate-a2a-unit-partition-ratification-2026-06-17.md`

---

## 1. What shipped

| Surface | Change |
|---------|--------|
| `PartitionChunk` + `unit_partition` kind | `generate/math_problem_graph.py` |
| `_apply_unit_partition` + pack bind (`divide` lemma) | `generate/math_solver.py` |
| `_verify_unit_partition_step` | `generate/math_verifier.py` |
| Roundtrip + `DIVIDE_VERBS` widen (`cut`, `separate`) | `generate/math_roundtrip.py` |
| `_match_unit_partition`, DCS yield guard | `generate/recognizer_match.py` |
| `inject_unit_partition` | `generate/recognizer_anchor_inject.py` |
| Exemplars + synthesis + accepted proposal | `teaching/admissibility_exemplars/unit_partition_v1.jsonl`, `teaching/recognizer_synthesis.py`, `teaching/proposals/proposals.jsonl` |
| Tests | `tests/test_recognizer_unit_partition_inject.py`, `tests/test_math_candidate_graph_unit_partition_injection.py`, frontier/microscope extensions |

**Lead exemplar:** case **0002** partition stmt `She splits it up into 25-foot sections.` now matches `ShapeCategory.UNIT_PARTITION` and injects `CandidateOperation(kind="unit_partition")` with `result_unit=sections`.

**DCS yield:** `_match_discrete_count_statement` returns `None` when `_is_unit_partition_v1_surface` holds — prevents `Initial(25, foot)` misread.

---

## 2. Solid

- New `unit_partition` kind writes quotient under `result_unit`, not dividend unit — bare `divide` reuse avoided.
- Closed v1 template: partition verb + `into` + single `\d+-(measure)` + optional counted noun.
- Pronoun subject (`She`) emits with `requires_pronoun_resolution`; existing lookback path applies.
- `wrong=0` preserved on live train_sample ephemeral runner; `unit_partition` `recognized_no_injection` = **0**.
- Pinned `report.json` unchanged (6/44/0 historical artifact).

---

## 3. Gaps (no live risk)

- `graph_intent: "partition"` is new; no separate graph_planner hook (out of v1 scope).
- Pack lemma maps `unit_partition` → existing `divide` entry (semantically division; kind discriminates `result_unit` contract).
- No dedicated `binding_graph` admissibility hook; partition ops reach solver only via injector + roundtrip.

---

## 4. Drift from ratification

| Ratification claim | Implementation |
|--------------------|----------------|
| `separate` verb | Included in matcher regex + `DIVIDE_VERBS` |
| Actor binding “no cross-sentence pronoun beyond session rules” | Uses existing ADR-0174 lookback; no new binding logic |
| `report.json` rebaseline | Intentionally skipped |

No amendment required.

---

## 5. Hazards reviewed

| Hazard | Verdict |
|--------|---------|
| Over-recognition on `\d+-(hour\|foot)` alone | Mitigated: requires verb + `into`; `2-hour drive` does not match `unit_partition` |
| DCS wins race on 0002 | Mitigated: DCS yield returns `None` |
| Quotient stored under `feet` | Mitigated: `PartitionChunk.result_unit` |
| Pseudo-accumulation 996 (confuser-v1-0007) | Full 0002 still refuses; no correct lift claimed |
| Non-exact quotient | Solver + verifier refuse (`SolveError` / `VerificationError`) |

---

## 6. Metric movement (ephemeral live runner)

| Metric | Before | After (expected) |
|--------|--------|------------------|
| `wrong` | 0 | **0** |
| `correct` | 6 | **≥ 6** (no lift guaranteed) |
| `refused` | 44 | **≤ 44** |
| `unit_partition` no-injection | 1 (0002 via DCS misroute) | **0** |
| `discrete_count_statement` no-injection | 19 | likely **18** (−1 reclassification) |

Case **0002** partition stmt reclassifies; full solve to 15 remains refused until composition ratification.

---

## 7. Validation run

```bash
git diff --check origin/main...HEAD
pytest tests/test_recognizer_unit_partition_inject.py -q
pytest tests/test_math_candidate_graph_unit_partition_injection.py -q
pytest tests/test_gsm8k_frontier_report.py -q
pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
pytest tests/test_candidate_graph_recognizer_wiring.py -q
```

---

## 8. Explicit non-goals (held)

- No full 0002 composition, no `report.json` rebaseline, no sealed-lane pin movement
- No Gate A1b, Inc4, broad DCS, `determine()` / `FrameVerdict` / CLOSE
- No `graph_planner.py` changes