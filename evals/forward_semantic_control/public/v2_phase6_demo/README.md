# Phase 6 Corpus — Comparative Demo (`v2_phase6_demo/cases.jsonl`)

8 focused cases that drive the **three head-to-head conditions** of
the Phase 6 comparative demo. The "head-to-head" is between CORE
(inner-loop + margin + rotor admissibility enabled) and an in-system
baseline (the same codebase with those mechanisms disabled — an
ADR-0023 ablation).

**Runner:** `evals/forward_semantic_control/phase6_demo.py`
**Live:** `core demo phase6`
**Report:** `evals/forward_semantic_control/results/phase6_demo_report.json`
**Contract tests:** `tests/test_phase6_demo.py` (17 tests)
**Narrative:** `docs/evals/phase6_comparative_demo.md`

---

## The three conditions

| Condition | Cases | What it proves |
|---|---|---|
| **C1 `replay_determinism`** | 2 | Both baseline AND CORE produce byte-identical trace hashes across 5 reruns. CORE additionally folds refusal_reason into the hash, so refusal events themselves are replayable. |
| **C2 `traced_rejection`** | 3 | When the boundary picks the *forbidden* token, baseline emits it with `admitted=False` (silent emit). CORE overrides, the rejection appears in `rejected_attempts`, and the selection difference is causally attributable to the inner-loop. |
| **C3 `coherent_refusal`** | 3 | When no candidate is admissible, baseline emits an inadmissible candidate. CORE raises `InnerLoopExhaustion` with a typed `RefusalReason` carrying evidence. Typed refusal is *new* in CORE. |

---

## Why the baseline is in-system, not a transformer LLM

| Concern | In-system baseline | Transformer LLM |
|---|---|---|
| Deterministic | Yes | No (sampling temperature, top-k, etc.) |
| CI-enforceable | Yes (17 contract tests) | No |
| Apples-to-apples | Yes (same field state, vocab, persona) | No (different corpus, training, etc.) |
| Attributable | Yes (only the chain toggled) | No (any difference could be from any layer) |

A transformer comparison would tell us nothing about whether the
ADR-0024 chain mechanisms are doing real work — only that two
unrelated systems produce different outputs. The honest comparison is
the ablation.

---

## Case schema

Same single-step shape as Phase 5 Family A / C, with one additional
required field: `condition`.

```json
{
  "id": "FSC-P6-C2-001",
  "condition": "traced_rejection",
  "kind": "mechanism_isolation",
  "seed_token": "word",
  "admissible_tokens": ["question", "meaning"],
  "relation_blade_token": "question",
  "expected_endpoint": "question",
  "forbidden_token": "meaning",
  "admissibility_threshold": 1.3706,
  "rationale": "Boundary geometrically prefers 'meaning' (forbidden); ..."
}
```

C3 cases additionally set `"expect_refusal": true` and
`"refusal_reason": "inner_loop_exhaustion"`.

### `condition` field values

| Value | What it controls |
|---|---|
| `"replay_determinism"` | Runs 5 reruns under both baseline and CORE; pass iff both hash sets are singletons. |
| `"traced_rejection"` | Asserts boundary emits forbidden AND CORE corrects-or-refuses AND CORE rejection in trace. |
| `"coherent_refusal"` | Asserts baseline is NOT a typed refusal AND CORE IS a typed `INNER_LOOP_EXHAUSTION`. |

---

## When to add cases

**Add new cases when:**
- A new boundary-vs-blade divergence pattern is discovered.
- A new geometric construction surfaces a refusal mode not exercised
  by C1/C2/C3 cases.
- Phase 5 surfaces a regression that should also be pinned at the
  comparative demo layer for narrative impact.

**Do NOT add cases that always pass.** This corpus is small by design
— each case must surface a *specific* baseline-vs-CORE asymmetry.

**Do NOT relax C2/C3 predicates when a case ages out.** If a C2 case
stops surfacing "boundary picks forbidden" (because the underlying
geometry shifted), the case has aged out — add a NEW case that
surfaces the failure mode, then archive the old one.

---

## Verifying after edit

```bash
# 1. Contract tests pin the case-aggregate behaviour:
core test --suite phase6

# 2. Live demo produces an investor-readable table:
core demo phase6

# 3. The headline metric MUST be all_three_conditions_pass=true:
core demo list-results --json | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['reports'])" | grep all_three_conditions_pass
```
