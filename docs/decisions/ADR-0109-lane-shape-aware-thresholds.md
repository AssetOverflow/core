# ADR-0109 — Lane-Shape-Aware Thresholds (ADR-0106 Amendment)

**Status:** Proposed
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Amends:** ADR-0106
**Depends on:** ADR-0106, ADR-0107
**Reserves:** ADR-0110 (math expert-demo re-attempt under this amendment)

---

## Context

ADR-0106 §1.2 prescribed a single set of threshold metrics — taken from
the cognition pack's eval shape — applied uniformly across every lane
attached to a ratified domain:

```text
surface_groundedness  >= 0.95
term_capture_rate     >= 0.85
intent_accuracy       >= 0.95
versor_closure_rate   == 1.0
```

ADR-0107 surfaced that this is wrong in practice. Each lane reports its
own native metric shape:

| Lane | Native metrics |
|---|---|
| cognition eval | `surface_groundedness`, `term_capture_rate`, `intent_accuracy`, `versor_closure_rate` |
| `elementary_mathematics_ood` | `accuracy`, `by_construction`, `passed`, `total` |
| `inference_closure` | `all_pass_rate`, `derived_recall_rate`, `premises_stored_rate`, `replay_determinism`, `overall_pass` |
| `fabrication_control` | `fabricated`, `refused`, by-class refusal counts |
| `foundational_physics_ood` | `accuracy` (shape-equivalent to math OOD) |
| `hebrew_fluency` / `koine_greek_fluency` | `accuracy`, by-construction pass rates |

Enforcing cognition-shape keys uniformly causes every non-cognition
lane to fail the gate by absence-of-key, not by substance. The
ADR-0106 contract is technically correct (no domain passes a contract
written against keys it doesn't produce) but operationally useless.

ADR-0109 amends ADR-0106 to make threshold rules lane-shape-aware,
without weakening the contract's discipline.

---

## Decision

### 1. Lane-shape registry

Introduce an explicit, code-pinned mapping from lane id → lane shape →
threshold rule. The registry lives in `core/capability/expert_demo.py`
(or a sibling module if scope grows). A lane not registered fails
the expert-demo gate fail-closed; introducing a new shape requires an
ADR citing this one.

### 2. Initial shapes

ADR-0109 v1 ships five shapes covering every lane currently attached to
a ratified pack:

#### `cognition_shape`

Threshold (unchanged from ADR-0106 §1.2):

- `surface_groundedness >= 0.95`
- `term_capture_rate >= 0.85`
- `intent_accuracy >= 0.95`
- `versor_closure_rate == 1.0`

Applies to: cognition eval lane only.

#### `accuracy_shape`

Threshold:

- `accuracy >= 0.95` on both public and holdout
- `accuracy` interpreted as `passed / total` when `accuracy` key
  absent and `passed` + `total` are present (deterministic fallback)

Applies to: `elementary_mathematics_ood`, `foundational_physics_ood`,
`hebrew_fluency`, `koine_greek_fluency`, and other domain-specific
positive-coverage lanes that report a single accuracy scalar.

#### `inference_shape`

Threshold:

- `all_pass_rate >= 0.95`
- `replay_determinism == 1.0`
- `overall_pass == true`

Applies to: `inference_closure`.

#### `refusal_shape`

Threshold:

- Total `fabricated` count across all by-class buckets == 0
- Every by-class bucket reports `refused == n` (every case refused)

Applies to: `fabrication_control`. Replaces ADR-0106 §1.3's
`passed_rate >= 1.0` check, which presumed a key the lane doesn't
actually emit.

#### `symbolic_logic_shape`

Threshold:

- `accuracy >= 0.95` (re-uses `accuracy_shape` rule)

Applies to: `symbolic_logic` (the v1 closest-fit lane for
`systems_software` per ADR-0101).

### 3. Registry resolution rule

The lane-shape registry is consulted by id, not by metric introspection.
A lane named `inference_closure` always resolves to `inference_shape`;
the registry cannot be tricked by a lane emitting accuracy-shaped keys
under a different lane id. This preserves ADR-0106 §1.1.4's
domain-aware invariant.

### 4. Unknown lanes are fail-closed

If a manifest references a lane id that the registry doesn't recognise,
`evaluate_expert_demo` returns `passed=False` with reason
`"lane <id> has no registered shape — introduce via ADR amendment"`.
This is intentional: adding lanes silently broadens the gate; the ADR
process is the change-control mechanism.

### 5. No effect on ADR-0106 §1.1, §1.3 reviewer-signature
   requirements, §1.4 signature scoping, or §1.5 replay byte-equality

ADR-0109 amends §1.2 only. The reviewer-signed claim, the signer's
`eval` scope requirement, the cross-domain bleed refusal, and the
evidence-digest reproducibility invariant all remain unchanged.

The `derive_evidence_digest` canonicalisation (sorted keys, compact
separators, full lane metrics included) is unchanged. A claim signed
under ADR-0106 metric assumptions remains replay-equivalent under
ADR-0109; the gate's *acceptance* changes, the *digest input* does not.

---

## Invariants

### `lane_shape_explicit`

Every lane id referenced by any ratified pack's manifest must resolve
to a registered shape. A pytest gate iterates `DOMAIN_PACKS`, collects
all `eval_lanes[].lane` values, and asserts each resolves.

### `shape_thresholds_are_named`

Each shape carries a documented minimum per metric. No implicit defaults.
A new shape is introduced only by amending this ADR (or a successor).

### `unknown_lane_fails_closed`

A claim citing a lane id absent from the registry produces
`ExpertDemoVerdict(passed=False, reason=...)`. Tested by a fixture
that asserts this exact behaviour.

### `cognition_shape_unchanged_under_amendment`

A claim signed against cognition-shape thresholds before ADR-0109
remains valid under ADR-0109. This is enforced by holding the
`cognition_shape` thresholds bit-identical to ADR-0106 §1.2 and by a
test that verifies `derive_evidence_digest` is stable across the
amendment.

---

## Acceptance evidence

Accepted when:

- `core/capability/expert_demo.py` carries the registered shapes,
  resolution function, and the rewritten `_meets_thresholds` that
  dispatches by shape.
- `tests/test_lane_shape_thresholds.py` covers the four invariants
  above.
- README "Accepted reasoning-capable domains" preface notes the
  shape-aware gating.
- No domain row's `expert_demo` field flips by this PR — the math row
  remains at `reasoning-capable` (ADR-0107's deferral stands; ADR-0110
  is the re-attempt under this amended contract).
- ADR-0106 status remains Accepted (this ADR amends, doesn't supersede).

---

## Consequences

- The expert-demo contract becomes operationally testable for the
  first time without forcing every domain into cognition-shape
  evidence.
- Adding a new domain or a new lane shape becomes an explicit ADR
  step. The registry is the change-control surface.
- ADR-0110 can proceed to attempt `mathematics_logic` promotion under
  rules that match the math lanes' actual outputs. Promotion still
  requires `inference_closure` to pass (`all_pass_rate >= 0.95` per
  the new `inference_shape` rule) — independent of metric-shape work.
- Three of the four ratified domains
  (`physics`, `systems_software`, `hebrew_greek_textual_reasoning`)
  can also be evaluated for expert-demo without further amendment
  once their attached lanes carry results meeting their shape's
  thresholds.

---

## Out of scope

- This ADR does not investigate or fix `inference_closure`. ADR-0110
  must verify that lane passes before promoting math.
- This ADR does not change which lanes are attached to which domains.
- This ADR does not amend the reviewer registry schema. The
  `expert_demo_claims` block from ADR-0106 is sufficient under
  ADR-0109; only the threshold-resolution logic changes.
- Multi-reviewer governance (the ADR-0105 candidate frontier item)
  remains orthogonal and future work.
