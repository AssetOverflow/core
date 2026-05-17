# Phase 5 Corpus — Stratified Mechanism-Isolation (`v2_phase5/cases.jsonl`)

20 hand-curated cases stratified across **five geometric failure-mode
families** so each family reports its own pass rate, refusal rate, and
mechanism-isolation evidence — instead of a single binary verdict over
mixed cases.

**Runner:** `evals/forward_semantic_control/phase5_runner.py`
**Live:** `core demo phase5`
**Report:** `evals/forward_semantic_control/results/phase5_report.json`
**Contract tests:** `tests/test_phase5_corpus.py` (20 tests)
**Narrative:** `docs/evals/phase5_stratified_findings.md`

---

## The five families

| Family | Geometric construction | Threshold-mode expectation | Margin-mode expectation |
|---|---|---|---|
| **A. near_forbidden_correct_endpoint** | Expected blade-score > forbidden by a small margin (0.002 to 0.55) | admit expected | admit if gap ≥ δ=0.4, else refuse |
| **B. near_equal_admissible** | Two admissible candidates within ≤ 0.01 blade-score | admit either (tie-break stable) | refuse (diff < δ by construction) |
| **C. no_admissible_path** | Both candidates score ≤ 0 against blade | honest refusal (`INNER_LOOP_EXHAUSTION`) | honest refusal (`INNER_LOOP_EXHAUSTION`) |
| **D. multi_step_admissibility** | Chain of two Family-A configurations | each step admits expected | each step admits expected |
| **E. heterogeneous_relation** | Chained steps with *different blades* at each step | each step admits under its own blade | each step admits under its own blade |

---

## Case schema

### Single-step case (families A, B, C)

```json
{
  "id": "FSC-P5-A-001",
  "family": "near_forbidden_correct_endpoint",
  "kind": "mechanism_isolation",
  "semantic_pair": "comparison/reason",
  "seed_token": "word",
  "admissible_tokens": ["comparison", "reason"],
  "relation_blade_token": "comparison",
  "expected_endpoint": "comparison",
  "forbidden_token": "reason",
  "admissibility_threshold": 1.3329,
  "rationale": "Sub-margin blade gap (0.0018). Boundary picks ..."
}
```

Family C cases additionally set `"expect_refusal": true` and
`"refusal_reason": "inner_loop_exhaustion"`.

### Chained case (families D, E)

```json
{
  "id": "FSC-P5-D-001",
  "family": "multi_step_admissibility",
  "kind": "chain_isolation",
  "steps": [
    { "seed_token": "spirit", "admissible_tokens": ["define","explain"], "relation_blade_token": "define", "expected_endpoint": "define", "forbidden_token": "explain", "admissibility_threshold": 1.0249 },
    { "seed_token": "define", "admissible_tokens": ["correct","verify"], "relation_blade_token": "correct", "expected_endpoint": "correct", "forbidden_token": "verify", "admissibility_threshold": 1.0 }
  ],
  "rationale": "Two-step chain; each step is an independently mined Family-A configuration ..."
}
```

Family E cases use the same schema with optional `"relation_label"` per step (e.g. `"compare_with"`, `"causes"`) for documentation.

---

## Required field semantics

| Field | Meaning | Notes |
|---|---|---|
| `seed_token` | Pack token that seeds the FieldState | Must be present in the active pack |
| `admissible_tokens` | List of pack tokens forming `AdmissibilityRegion.allowed_indices` | All must be pack-grounded |
| `relation_blade_token` | Pack token whose versor is `AdmissibilityRegion.relation_blade` | Single-token blade only |
| `expected_endpoint` | The token the runner asserts as the correct selection | Must be in `admissible_tokens` |
| `forbidden_token` | The token the boundary leg should emit (mechanism-isolation evidence) | Must be in `admissible_tokens` |
| `admissibility_threshold` | Static threshold for threshold-mode leg | Typically set between expected and forbidden blade-scores |
| `expect_refusal` *(Family C)* | If true, both modes must refuse | |
| `refusal_reason` *(Family C)* | Stable enum value the runner asserts on refusal | Use `"inner_loop_exhaustion"` |

---

## How cases were geometrically mined

The corpus was produced by the offline tool
`evals/forward_semantic_control/phase5_mine.py`, which scans triples
`(seed, admissible_pair, blade)` over a pack subset and reports
candidate geometric configurations for each family. Run it yourself:

```bash
PYTHONPATH=. uv run python evals/forward_semantic_control/phase5_mine.py --family A --limit 25
PYTHONPATH=. uv run python evals/forward_semantic_control/phase5_mine.py --family B --limit 25
PYTHONPATH=. uv run python evals/forward_semantic_control/phase5_mine.py --family C --limit 25
```

The miner is offline only (it imports `chat.runtime.ChatRuntime` for
vocab access, which is too heavy to run inside the contract tests).
Use it to find candidate cases; verify them by hand by running
`uv run python -c "..."` to inspect `cga_inner` scores; commit only
once the geometric construction is confirmed.

---

## When to add cases

**Always add — never edit existing cases — when:**
- A new failure mode is discovered in production / Phase 6 demo.
- A real corpus case surfaces a δ-margin disagreement that should be
  investigated as an ADR-0026 falsification candidate.
- The pack vocabulary expands and a new region geometry becomes
  reachable.

**Do NOT remove cases just because they pass.** They are regression
contracts.

**Do NOT lower a per-family pass-rate assertion to accommodate a
failing case.** That hides the regression. Either fix the
implementation or document the architectural finding in
`docs/evals/phase5_stratified_findings.md`.

---

## Verifying after edit

```bash
# 1. The case-schema and pass predicates must hold:
core test --suite phase5

# 2. The runner must produce the expected report shape:
core demo phase5

# 3. The full chain still passes:
core test --suite adr-0024
```
