# Benign Inner-Loop Corpus (`inner_loop_benign/cases.jsonl`)

10 cases that drive the **EXHAUSTION_CEILING ≤ 0.05** gate in the
corpus-observation lane (`inner_loop_runner.py`). This corpus is
intentionally *benign* — every case is constructed so the inner-loop
should comfortably admit, not refuse.

If the chain refuses cases here, the chain has regressed. (Or a pack
token's geometry has shifted under Cl(4,1) signature — see below.)

**Runner:** `evals/forward_semantic_control/inner_loop_runner.py`
**Report:** `evals/forward_semantic_control/results/phase5_benign_inner_loop_report.json`
**Gate:** `EXHAUSTION_CEILING = 0.05` (per-condition exhaustion rate must not exceed)
**Phase:** Authored in ADR-0024 Phase 5 to replace the *adversarial-by-accident* v1/dev corpus.

---

## Why this corpus exists

The original FSC v1/dev corpus used a `prime → chain_tokens` shape
that probes *teaching-driven walks* (ADR-0022 / 0023), not
inner-loop admissibility (ADR-0024). The EXHAUSTION_CEILING gate was
designed against benign corpus, but the v1/dev corpus is not benign
— it asks the inner-loop questions about teaching, not admissibility.
Phase 5 authored this *honestly benign* corpus to give the gate a
fair denominator.

---

## Case schema

```json
{
  "id": "FSC-BENIGN-001",
  "kind": "single_token_admit",
  "prime": ["What grounds reason?", "Reason is grounded in truth."],
  "prompt": "What grounds reason?",
  "expected_endpoint": "truth",
  "chain_tokens": ["truth"],
  "grounding_note": "Single-token region; expected token's self cga_inner ≈ 1.17 ≫ threshold 0.25."
}
```

The runner builds an `AdmissibilityRegion` from `chain_tokens` (outer
product over each token's versor) and the FieldState from the
priming sequence. With `chain_tokens` of size 1, the region admits
only that token's index; the inner-loop verifies its blade-score is
positive (against itself).

---

## The Cl(4,1) signature quirk this corpus reveals

23 of the 85 tokens in `en_core_cognition_v1` have **negative
self-`cga_inner`** under Cl(4,1) (Lorentzian signature). Most-negative
examples: `mean=-2.01`, `verify=-1.33`, `context=-1.15`,
`corrects=-0.74`.

A single-token region with `chain_tokens=[tok]` where
`cga_inner(versor(tok), versor(tok)) < 0` will **always exhaust** in
threshold-mode under any positive threshold, even though the case is
"benign" by naive English semantics. This is a geometric fact about
Cl(4,1), not a regression.

The 10 cases in this corpus were drawn from the 62-token subset with
**self-`cga_inner > 0.25`**. The case for `correction` was rejected
during authoring (it has `self-cga_inner = -0.036`) and replaced
with `beginning` (`self-cga_inner ≈ 1.36`).

If you add a case here, verify the expected token's self-score
first:

```bash
PYTHONPATH=. uv run python -c "
import numpy as np
from algebra.cga import cga_inner
from chat.runtime import ChatRuntime
vocab = ChatRuntime().session.vocab
for tok in ['<your-expected-token>']:
    v = np.asarray(vocab.get_versor(tok), dtype=np.float32)
    print(f'{tok}: self cga_inner = {float(cga_inner(v,v)):.4f}')
"
```

If the value is ≤ 0.25, the case will exhaust under the operational
threshold `t=0.25` — pick a different token, or use a multi-token
chain whose outer product realigns the blade.

---

## Expected results

| Condition | exhaustion_rate | pass_rate |
|---|---|---|
| boundary_only | 0.00 | 1.00 |
| null_control | 0.00 | 1.00 |
| inner_loop_t0 (threshold=0.0) | 0.00 | 1.00 |
| inner_loop_tpos (threshold=0.25) | 0.00 | 1.00 |

If any of these exceeds the 0.05 ceiling, see "When to add cases" below.

---

## When to add cases

**Add cases when:**
- A new pack ships with new tokens whose semantic role isn't covered.
- A user-reported regression isolates to a benign case the corpus
  doesn't cover.

**Always:**
- Verify self-`cga_inner > 0.25` for the expected token BEFORE adding
  the case (see snippet above).
- Pick a `prime` sequence whose final field state lands the
  admissible region in a positive blade-score region. Run the case
  once via the runner before committing.

**Never:**
- Lower `EXHAUSTION_CEILING` to accommodate a failing case. The gate
  is load-bearing — a real exhaustion here means the inner-loop is
  refusing on a benign corpus.

---

## Verifying after edit

```bash
# Run the full inner_loop_runner against this corpus:
PYTHONPATH=. uv run python -c "
import json
from evals.forward_semantic_control.inner_loop_runner import run_lane, EXHAUSTION_CEILING
cases = [json.loads(l) for l in open('evals/forward_semantic_control/public/inner_loop_benign/cases.jsonl')]
report = run_lane(cases)
for label in ('boundary_only','null_control','inner_loop_t0','inner_loop_tpos'):
    pc = report.metrics['per_condition'][label]
    flag = 'OK' if pc['exhaustion_rate'] <= EXHAUSTION_CEILING else 'OVER'
    print(f'{label:18s}: exhaustion={pc[\"exhaustion_rate\"]:.4f} ({flag})')
"
```
