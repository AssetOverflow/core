# Runtime Contracts

This document freezes the runtime contracts used by chat, telemetry, memory,
and future teaching work.  It exists to prevent contract drift between tests,
runtime code, and future cognitive pipeline work.

## Field invariant

CORE state is a versor field.  Runtime code must preserve the core closure
contract:

```text
versor_condition(F) < 1e-6
```

If a propagation path violates this invariant, fix the operator path or the
explicit closure boundary that owns the transition. Do not hide violations by
changing tests or silently downgrading the invariant.

## ChatResponse contract

`ChatResponse.surface`
: The selected user-facing response. This is the exact string returned by
  `ChatRuntime.respond()` and should match what the user receives.

`ChatResponse.walk_surface`
: The manifold/token-walk evidence surface. It is trace evidence for what the
  field traversal produced. It is not necessarily the user-facing response.

`ChatResponse.articulation_surface`
: The proposition/realizer surface. This is the structured linguistic
  realization of the current proposition or proposition graph.

Current selection policy:

```text
surface = determination_surface     (when accrue_realized_knowledge AND the turn
                                      DETERMINED an answer over realized knowledge)
surface = _UNKNOWN_DOMAIN_SURFACE    (when the unknown-domain gate fired)
surface = articulation_surface       (otherwise — the default)
walk_surface        = retained telemetry/evidence (always)
articulation_surface = retained always (the determination surface does not replace it)
```

### Unknown-domain gate honour

When `vault/decompose.py::UnknownDomainGate` fires, ChatRuntime returns
the safety stub `_UNKNOWN_DOMAIN_SURFACE` ("I don't have field
coordinates for that yet.") and `vault_hits == 0`.
`CognitiveTurnPipeline` honours that stub: the user-facing `surface`
remains the gate's response and is *not* overridden by the realizer's
fallback articulation.  The realizer's surface always survives in
`walk_surface` as evidence — only the user-facing selection is
gated.  This closes `evals/calibration/gaps.md` Finding 2.

Future realizer work may change the selection policy, but must update this
document and the contract tests in the same PR.

### Determination surface (Step B-2)

When `accrue_realized_knowledge` is enabled and a question turn is **Determined**
over realized knowledge (`generate.determine.determine` returns a `Determined`),
the user-facing `surface` is the rendered determination
(`generate.determine.render_determination`) — the engine answers *from what it
accrued in the conversation*.  The basis is rendered **honestly**: SPECULATIVE
grounds (today's only case) read as "as I was told", never "verified"; D0 only
asserts `answer=True`, so the surface is an affirmation, never a fabricated or
asserted-False string.

The realizer's `articulation_surface` is **retained unchanged** as evidence — the
determination is a user-facing *selection*, exactly like the unknown-domain gate,
not a rewrite of the realizer output.  An **Undetermined** turn (refused,
open-world) keeps the default articulation surface — the honest "I don't know".
With the flag off, this path is never taken and the surface is unchanged.  This is
selection only: it adds no field op, no normalization, and proposes no learning
(`accrue_in_turn` writes SESSION memory through the INV-21 vault writer; the HITL
teaching path is untouched).

### Refusal contract (ADR-0024 Phase 2)

When the inner-loop admissibility check leaves no admissible destination
for the next step, the generation walk in `generate/stream.py` raises
`generate.exhaustion.InnerLoopExhaustion`, a typed subclass of
`ValueError` carrying:

```text
reason            : RefusalReason     (machine-readable taxonomy)
region_label      : str               (which AdmissibilityRegion blocked)
step_index        : int               (-1 = pre-walk empty intersection;
                                       >=0 = in-walk per-step exhaustion)
rejected_attempts : tuple[(int, str, float), ...]  (per-step evidence)
```

Reason codes are minimal in Phase 2: a single `INNER_LOOP_EXHAUSTION`
covers both raise sites. Phase 4 (rotor-frame admissibility, ADR-0025)
is expected to add a second reason for rotor exhaustion.

`CognitiveTurnResult.refusal_reason` carries the stable string value of
the `RefusalReason` when a turn refuses, and the empty string otherwise.
`compute_trace_hash` folds `refusal_reason` into the payload only when
non-empty, preserving byte-identical hashes for non-refused turns
relative to pre-Phase-2 (determinism invariant). When the field is
non-empty, it becomes load-bearing in replay equality.

Backward compatibility: `InnerLoopExhaustion` is a `ValueError`, so
every pre-Phase-2 `except ValueError` handler in `chat/runtime.py`,
eval lanes, and tests continues to catch it without modification.

Residual silent path (out of scope for Phase 2, future ADR):
`ChatRuntime.respond()` and `arespond()` still convert any `ValueError`
to the empty string for their public `str` return contract, so a real
turn that refuses today produces `surface == ""` with
`refusal_reason == ""` — the typed evidence is unread between the
raise site and the result. The plumbing on `CognitiveTurnResult`,
`compute_trace_hash`, and `CognitiveTurnPipeline` is in place so a
future ADR can wire materialisation (e.g. propagate the typed
exception to `ChatResponse.refusal_reason` or catch at the pipeline
seam) without re-deriving the contract.

### Ranked-with-margin contract (ADR-0026 / Phase 3)

The static `admissibility_threshold` documented above (ADR-0024 Phase 2)
is supplemented by a scale-invariant margin gate (ADR-0026 Phase 3).
The runtime selects mode via `RuntimeConfig.admissibility_mode`:

```text
RuntimeConfig.admissibility_mode    : "threshold" | "margin"   (default: "threshold")
RuntimeConfig.admissibility_margin  : float                    (default: 0.4)
```

In **threshold mode** (back-compat, ADR-0024):

```text
admit iff cga_inner(versor(candidate), relation_blade) > admissibility_threshold
```

In **margin mode** (ADR-0026):

```text
rank candidates by cga_inner(versor(candidate), relation_blade), descending,
  stable tie-break by candidate index
admit iff (single candidate)
       or (score(top) > 0  AND  score(top) - score(second) >= admissibility_margin)
```

`generate.admissibility.rank_candidates_by_blade` returns the ranked
list with deterministic tie-break, and `generate.admissibility.check_margin`
returns a typed `MarginVerdict` (`admitted`, `top`, `second`, `gap`,
`reason`).  The selection invariant is that the *score difference* is
the gate, not the absolute score — making the gate robust to per-blade
norm variation that defeated static threshold tuning on the
Phase 4 characterization corpus (see
`docs/evals/phase5_stratified_findings.md`).

Refusal in margin mode is materialised through the same
`InnerLoopExhaustion` mechanism as threshold mode, with
`RefusalReason.INNER_LOOP_EXHAUSTION` carrying the full ranked
candidate list as evidence so the failure mode is "no candidate has
margin over its successor" rather than "no candidate exceeded
threshold T."

The default δ = 0.4 was selected from the minimum observed margin in
the Phase 3 v2 corpus (0.456) and is *falsifiable*: any case
surfacing a blade-gap below δ where margin-mode refusal is the wrong
behavior must be reported as an ADR-0026 falsification rather than
silently patched per case.  Phase 5's 20-case stratified corpus does
not falsify δ = 0.4.

### Rotor admissibility contract (ADR-0025 / Phase 4)

The destination-side admissibility documented above (token-side blade
alignment, ADR-0024 / Phase 3) is complemented by a rotor-side check:
when a region carries a non-null `frame_versor`, the inner loop
additionally verifies that the rotor's effect on the current field
stays within the frame's admissible cone:

```text
F'    = versor_apply(V, F_current)
score = cga_inner(F', frame_versor)
admit iff score > 0
```

`generate.rotor_admissibility.check_rotor_admissibility` performs
this pure semantic check. It lives at the same generation/propagation
seam as the inner loop — in `generate/rotor_admissibility.py`, a
sibling-but-separate module to `generate/admissibility.py` — **not**
in `algebra/versor.py` (admissibility is a pack-semantic test, not a
closure invariant) and **not** in `field/propagate.py` (forbidden
normalization/repair site). The placement is the load-bearing
architectural decision in ADR-0025.

Refusal is materialised through the same `InnerLoopExhaustion`
mechanism as destination-side refusal, but with
`RefusalReason.ROTOR_REJECTION` instead of `INNER_LOOP_EXHAUSTION`,
so the trace names the axis that ran out. In threshold mode, a step
that exhausts after *any* rotor rejection is reported under
`ROTOR_REJECTION`; pure destination exhaustion stays
`INNER_LOOP_EXHAUSTION`. In margin mode, the rotor check runs on the
top-ranked admissible candidate after destination margin admits; on
rotor refusal the typed exception carries the full destination
ranking plus the rejected rotor's score as evidence.

The `versor_condition(F) < 1e-6` invariant remains the algebra
layer's responsibility on actual propagation. `check_rotor_admissibility`
does not mutate field state and does not enforce closure — it only
asks whether applying `V` to `F` would leave the field in the
frame's half-space.

## TurnEvent contract

`TurnEvent.surface`
: Exact emitted user-facing response for the turn.

`TurnEvent.walk_surface`
: Exact manifold/token-walk evidence surface for the turn.

`TurnEvent.articulation_surface`
: Exact proposition/realizer surface for the turn.

`TurnEvent.vault_hits`
: Actual count of recall hits applied during generation. Never hardcode this.

`TurnEvent.flagged`
: Mirrors `IdentityScore.flagged` for filtering and trace inspection.

## Identity contract

Identity checks are telemetry/gating signals. A flagged identity score must not
silently erase useful generation unless an explicit hard-block policy is
configured and tested.

Canonical call style:

```python
IdentityCheck().check(trajectory, manifold)
```

Legacy constructor injection:

```python
IdentityCheck(manifold=manifold).check(trajectory)
```

is supported temporarily and emits `DeprecationWarning`. New code must not use
it.

## Memory and teaching contract

Session memory can be immediate and local to the running context.

Reviewed memory must be explicit: user corrections or teaching examples become
reviewed memory only through the reviewed teaching loop.

Pack mutation is proposal-only until reviewed. Runtime correction capture must
not directly rewrite language packs, frames, identity axes, or operator code.

Identity manifold mutation by user prompt or correction is forbidden.

## Testing policy

Tests should protect load-bearing behavior:

- versor closure
- deterministic replay
- runtime response/telemetry contracts
- memory correctness
- identity protection
- teaching/correction safety
- articulation contract

Avoid tests that preserve stale constructors, private helper shapes, or exact
formatting that is not part of a documented contract.

## Epistemic surface (ADR-0021)

CORE exposes a typed `epistemic_status` on the teaching and lexicon
surfaces.  The status is a **position in the revision graph**, not a
source-trust tier:

| Status        | Meaning                                                                                  |
|---------------|------------------------------------------------------------------------------------------|
| `COHERENT`    | Fits current field geometry; no incoherence with reviewed claims detected at admission. |
| `CONTESTED`   | Incoherent with at least one reviewed claim; review pending; not load-bearing.           |
| `SPECULATIVE` | Proposed; not yet reviewed for coherence; admissible only as a candidate.                |
| `FALSIFIED`   | Incoherent under accumulated evidence; eligible for Stage-3 inversion; retained.         |

### Non-hardening invariant

No reviewed claim or proposition-graph edge ever becomes unrevisable.
No `final`, `frozen`, `axiom`, or `permanent` flag exists or may be
added on the runtime data model.  The closest such property in the
architecture is the *mathematical* closure check
`versor_condition(F) < 1e-6` — never an epistemic seal on a claim.
The invariant is enforced by `tests/test_epistemic_invariants.py`.

### Curator review rule

`epistemic_status` transitions are computed from coherence with the
existing reviewed field — not asserted by source authority.  At v1 the
judgment is curator-mediated, with one rule:

> The curator's only admissible reasoning is *geometric*: does the
> claim cohere with already-reviewed claims, or does it produce
> incoherence?  Source credentials, popularity, or institutional
> position must not be invoked as justification.

### Schema surfaces

| Surface                                 | Field                                  | Default at creation   |
|-----------------------------------------|----------------------------------------|-----------------------|
| `teaching.PackMutationProposal`         | `epistemic_status: EpistemicStatus`    | `SPECULATIVE`         |
| `teaching.ReviewedTeachingExample`      | `epistemic_status: EpistemicStatus`    | `SPECULATIVE`         |
| `language_packs.schema.LexicalEntry`    | `epistemic_status: str`                | `"coherent"` (seed)   |
| `core.cognition.trace.compute_trace_hash` | `teaching_epistemic_status: str`     | `""` if no proposal   |

Promotion of a proposal's status uses the immutable updater
`PackMutationProposal.with_status(...)` — original is never mutated.

The status of the load-bearing proposal in a turn is folded into
`trace_hash` so replay detects when a downstream surface was produced
under a different epistemic frame than at the time of recall.

## Test organization target

Future test moves should follow this taxonomy:

| Area | Destination |
|---|---|
| versor closure, holonomy, motors, null cone, energy physics | `tests/algebra/` or `tests/physics/` |
| chat runtime, config, async runtime, identity gate telemetry | `tests/runtime/` |
| articulation, proposition, surface assembly, future pipeline | `tests/cognition/` |
| correction capture, reviewed memory, consolidation | `tests/teaching/` |
| language pack loading and seed pack invariants | `tests/packs/` |

Do not reorganize tests as a standalone churn PR unless it directly reduces
contract ambiguity or unlocks a cognitive subsystem.

## Formation trust boundaries

The Formation Pipeline (see `docs/formation_pipeline_plan.md`) introduces six
trust boundaries between the world and the manifold.  Every boundary has a
content-addressed input and output; every rejection produces an audit record.
No silent failures.

| # | Boundary | Input | Output | Trust contract |
|---|---|---|---|---|
| 1 | Mining → Smelting | URLs / files | `OreBundle` | Untrusted text in; untrusted entries out.  No code execution from sources; no dynamic imports; source URLs sandboxed; SHA-256 captured per entry. |
| 2 | Smelting → Forge | `OreBundle` + extracted candidates | `Candidate*` lists | Untrusted candidates in.  The Forge is the *only* validator.  Identity-override patterns and path-traversal in source SHAs are rejected at the Forge, not here. |
| 3 | Forge → Compose | `Candidate*` lists | `ValidatedTripleSet` | Every candidate runs through `teaching.relation_parse.parse_triple`, identity-axis screening, source allow-list, pack collision check, and the cross-reference rule.  Output entries carry `EpistemicStatus.SPECULATIVE`.  No pack mutation. |
| 4 | Compose → Compile/Run | `ValidatedTripleSet` | `CourseYAML` → `FormationPlan` | Deterministic, byte-stable composition.  No mutation of the language pack manifest. |
| 5 | Run → Ratify | `FormationPlan` | `list[CognitiveTurnResult]` | The runner is a thin shim over `CognitiveTurnPipeline.run()`.  It cannot invent operators; it can only invoke existing ones.  Hard-halts on `versor_condition(F) >= 1e-6`.  No identity-manifold mutation, ever. |
| 6 | Ratify → Promote | `MasteryReport` (self-sealed) | reviewed teaching apply | Promotion requires a self-sealed `MasteryReport` whose SHA verifies, whose prerequisites are present in the `MasteredCoursesIndex`, and whose triples are submitted through `teaching/review.py` — the existing reviewed apply path.  ADR-0021's "one mutation path" invariant is preserved. |

Content-addressing rules (binding across the whole pipeline):

- All hashed payloads are canonical JSON (sorted keys, tight separators,
  UTF-8, no NaN/Infinity).  Floats are forbidden in hashed payloads; encode
  numerics as strings or integers.
- `MasteryReport.report_sha256` is self-sealing: SHA over the payload with
  `report_sha256` blanked, then written back into the field.  Verifiers
  reverse the process.
- No pickle.  Pickle defeats replay determinism and is a code-execution
  surface.

See `formation/hashing.py`, `formation/cache.py`, and `formation/forge.py`
for the implementation of each rule.

---

## Expert-Demo Promotion Contract (ADR-0106 + ADR-0109)

Adds a domain-aware, reviewer-signed promotion gate to the capability
ledger surface (`ledger_report()`). Distinct from the runtime/turn
contracts above: this contract governs *what the ledger is allowed to
claim about a domain*, not what the runtime does on any single turn.

Per ADR-0108, the contract has been demonstrated end-to-end —
refused once (ADR-0107), amended once (ADR-0109), succeeded against
`mathematics_logic` (ADR-0110), and succeeded against `physics`
without further contract change (ADR-0111).

### Surface

`ledger_report()` returns a `domains` list. Each row carries:

```text
status                ∈ {blocked, seeded, grounded, reasoning-capable, audit-passed}
predicates.audit_passed   bool
audit_passed_reason       str  (one-line legibility for operators)
```

A row carries `audit_passed=True` iff **all** of:

1. `reasoning_capable == True` (the ADR-0091 nine-predicate gate).
2. A signed `ExpertDemoClaim` exists in `docs/reviewers.yaml` for the
   domain.
3. The signer named in `claim.signed_by` has `eval` scope for the
   domain per `ReviewerRegistry.can_review` (ADR-0092).
4. Every lane in `claim.evidence_lanes` is attached to at least one of
   the domain's ratified packs (no cross-domain bleed).
5. Every named lane's public + holdout metrics meet the threshold for
   that lane's registered shape (ADR-0109; see §"Lane-shape registry"
   below).
6. The canonical evidence-bundle SHA-256 reproduces `claim.claim_digest`
   byte-for-byte.

Any failure leaves the row at `reasoning-capable` with
`audit_passed_reason` populated.

### Schema

`docs/reviewers.yaml` additively gains an `audit_passed_claims` block:

```yaml
audit_passed_claims:
  - domain_id: mathematics_logic
    evidence_lanes:
      - elementary_mathematics_ood
      - inference_closure
      - fabrication_control
    evidence_revision: "adr-0110:reviewed:2026-05-22"
    signed_by: shay-j
    claim_digest: "94d74781..."
```

The block is optional; absence yields zero promotions. Schema
validation is loud: unknown signer ids, malformed digests, and
duplicate `domain_id` values are all rejected at load time
(`core.capability.reviewers.load_reviewer_registry`).

### Lane-shape registry (ADR-0109)

Threshold rules dispatch by lane shape, not uniformly. Registry in
`core/capability/expert_demo.py`:

| Lane id | Shape | Threshold |
|---|---|---|
| `cognition` | `cognition_shape` | surface_groundedness ≥ 0.95, term_capture_rate ≥ 0.85, intent_accuracy ≥ 0.95, versor_closure_rate == 1.0 |
| `elementary_mathematics_ood` | `accuracy_shape` | accuracy ≥ 0.95 (passed/total fallback) |
| `foundational_physics_ood` | `accuracy_shape` | same |
| `symbolic_logic` | `symbolic_logic_shape` | same as `accuracy_shape` |
| `hebrew_fluency` | `accuracy_shape` | same |
| `koine_greek_fluency` | `accuracy_shape` | same |
| `inference_closure` | `inference_shape` | all_pass_rate ≥ 0.95, replay_determinism == 1.0, overall_pass == True |
| `fabrication_control` | `refusal_shape` | every `by_class` bucket: refused == n, fabricated == 0 |

**Unknown lane ids fail closed** with reason
`lane <id> has no registered shape — introduce via ADR amendment`.
Adding a lane to the audit-passed surface requires an explicit registry
entry, which requires an ADR amendment.

### Replay invariant

`core.capability.audit_passed.derive_evidence_digest` is deterministic
in field order (sorted keys, compact separators). Re-running it
against the on-disk lane results at the same `evidence_revision`
reproduces `claim_digest` byte-for-byte. Drift in any lane result
demotes the row back to `reasoning-capable` until re-signed.

### Fail-closed registry

If `docs/reviewers.yaml` fails to parse,
`reporting._load_registry_for_expert_demo` returns an empty registry
(zero reviewers, zero claims) rather than raising. Every domain row
falls back to `audit_passed=false`. A broken registry must never
silently grant `audit_passed=true`.

### Trust boundary

- Pack mutation remains proposal-only (ADR-0029/0064 discipline).
- A reviewer signature in `audit_passed_claims` does not authorize
  pack mutation — only a ledger-row promotion. The two paths remain
  separate.
- `evidence_revision` may be a labeled string (e.g.
  `adr-0110:reviewed:2026-05-22`) or a raw git sha. The load-bearing
  invariant is replay byte-equality, not git-sha format.

---

## GSM8K Math Capability Lane (Phase 5 substrate — ADR-0119 + sub-phases)

Established by ADR-0119 through ADR-0119.8. The lane sits on the
parser → solver → verifier → realizer pipeline (ADR-0115 through
ADR-0118) and adds a scoring runner and a formal lane shape.

### Lane shape: `gsm8k_capability_shape`

Registered in `LANE_SHAPE_REGISTRY` as `LANE_SHAPE_REGISTRY["gsm8k_math"] =
"gsm8k_capability_shape"` (ADR-0119.8; `core/capability/expert_demo.py`).

The checker (`_check_gsm8k_capability_shape`) is distinct from the existing
five shapes because the metric keys and composition rule differ.

**Required metrics:**

| Key | Type | Meaning |
|---|---|---|
| `cases_total` | int | Total cases scored; must be > 0 |
| `correct` | int | Answer matches ground truth AND verifier passes |
| `wrong` | int | Verifier passed but answer mismatched, OR realizer failed |
| `refused` | int | ParseError or SolveError (typed refusal) |
| `overall_pass` | bool | `wrong == 0 AND correct + refused == cases_total` |

**Gate conditions (all must hold):**

| Condition | Reason |
|---|---|
| `cases_total > 0` | Non-empty input |
| `wrong == 0` | ADR-0114a Obligation #4: zero confabulation |
| `correct + refused == cases_total` | Outcome accounting completeness |
| `overall_pass` is true (when present) | Runner self-consistency |

The gate passes an all-refused result (0 correct, 0 wrong, N refused)
intentionally. Whether that qualifies for `expert` promotion is ADR-0120's
job (it sets the minimum correct_rate); this shape layer verifies only
runner self-consistency.

**Current measurements on main (2026-05-23):**

| Split | cases_total | correct | wrong | refused | gate |
|---|---|---|---|---|---|
| dev (CORE-original) | 50 | 50 | 0 | 0 | ✓ |
| public (CORE-original) | 150 | 150 | 0 | 0 | ✓ |
| holdout (real GSM8K test, sealed) | 1,319 | 0 | 0 | 1,319 | ✓ |
| adversarial suite | 38 | 5 | 0 | 33 | ✓ |

### Empty-expected_unit sentinel rule

GSM8K answers are pure numbers with no unit. The runner (ADR-0119.3,
extended in ADR-0119.7) implements:

> An empty `expected_unit` means the case carries no unit-level
> expectation; the runner skips the unit comparison and grades on
> answer value alone.

This is minimal extension to the outcome rules; the `wrong == 0`
discipline is preserved.

### Seal discipline (ADR-0119.1 + ADR-0119.7)

The real GSM8K test set is age-encrypted at
`evals/gsm8k_math/holdouts/v1/cases.jsonl.age` (420,486 bytes; 1,319
cases). Three invariants govern seal discipline:

1. **Plaintext never on disk.** `scripts/seal_gsm8k_test.py` holds the
   plaintext in memory only during encryption; only ciphertext is written.
2. **CORE_HOLDOUT_KEY required to decrypt.** The runner raises a typed
   error when the env var is absent. Tests that require decryption skip
   (do not fail) without the key. No CI workflow sets the key.
3. **Development team operates blind.** The recipient identity lives
   outside the repo at `~/.config/core/holdout_keys/repo_holdout.txt`
   (per ADR-0119.1). A release event signed by a reviewer is required
   to open the lane.

Re-encryption and re-seal events go through their own ADR amendment.

### Adversarial suite contract

`evals/gsm8k_math/adversarial/generator.py` generates 38 cases across 12
families designed to exploit weak grammar / solver coverage. The gate
from ADR-0119.5 and ADR-0114a Obligation #8:

> **Misparse rate must be zero on the adversarial suite.** A misparse
> is defined as `outcome == "wrong"` on the adversarial runner output —
> CORE ran to completion and emitted a wrong answer (confabulation).
> Refused rate may be arbitrarily high; that is the safe failure mode.

The `subtle_in_grammar` family (4 cases, all `correct`) proves the gate
is not trivially satisfied by refusing everything.

### Evidence location

- Lane runner: `evals/gsm8k_math/runner.py`
- Lane shape checker: `core/capability/expert_demo.py`
- Adversarial: `evals/gsm8k_math/adversarial/`
- Depth-curve harness: `evals/gsm8k_math/scoring/depth_curve.py`
- Frontier baseline: `evals/gsm8k_math/baselines/`
- Sealed holdout: `evals/gsm8k_math/holdouts/v1/cases.jsonl.age`
- ADR chain: ADR-0119, ADR-0119.1 through ADR-0119.8
