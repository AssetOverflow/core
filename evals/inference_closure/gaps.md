# inference-closure lane — architectural findings (v1)

## Resolution — 2026-05-17 lane re-run

After the typed deterministic operators (ADR-0018: `transitive_walk`,
`multi_relation_walk`, `path_recall` in `generate/operators.py`) and
their pipeline wiring (`_maybe_transitive_walk` + `_fold_walk_into_surface`
in `core/cognition/pipeline.py`) landed, this lane passes:

| Split | n | derived_recall_rate | premises_stored | replay | overall |
|---|---|---|---|---|---|
| public/v1  | 20 | **1.0** | 1.0 | 1.0 | ✓ |
| holdouts/v1 | 12 | **1.0** | 1.0 | 1.0 | ✓ |

Gap 1 (no transitive composition) and Gap 2 (no path-recall) are both
closed.  The probe for `wisdom is light`, `light is truth`,
`What is wisdom?` now produces
`wisdom is defined as ... — wisdom is truth (via wisdom light truth)`,
and the chain endpoint `truth` is folded into the user-facing surface.

Historic finding preserved below.

## Original v1 result (now superseded)

| Split | n | derived_recall_rate | premises_stored_rate | replay_determinism | overall_pass |
|---|---|---|---|---|---|
| public/v1 | 20 | **0.0** | 1.0 | 1.0 | False |
| holdouts/v1 | 12 | **0.0** | 1.0 | 1.0 | False |

This is the **expected v1 outcome** documented in
`docs/capability_roadmap.md` Phase 3: lanes may fail v1 honestly, and
each failure becomes either a closed engineering gap or a documented
architectural deferral.

## What v1 confirms

- **Foundation intact.** Every premise emits a `PackMutationProposal`
  (M3 = 1.0); every (premises, probe) sequence is replay-deterministic
  by trace_hash (M4 = 1.0).  The work that landed in Phase 2
  (symbolic-logic v1+v2) — storage and replay — holds at this depth.
- **No inference operator.** Across all 32 cases (20 public + 12
  holdouts) covering five relation families (`is`, `precedes`,
  `grounds`, `causes`, `belongs_to`), the probe response surface
  never references the derived entailment token.  Both `surface`
  and `walk_surface` are template-driven definitions/disclaimers, not
  derivations.

## Concrete probe trace

For `INF-DEV-001` — premises `wisdom is light`, `light is truth`,
probe `What is wisdom?` — the runtime produces:

```
PREMISE 'What is wisdom?'          surface='wisdom is defined as ...'  vault=0
PREMISE 'Actually wisdom is light' surface='Light write.'              vault=9
PREMISE 'What is light?'           surface='light is defined as ...'   vault=5
PREMISE 'Actually light is truth.' surface='Truth thought — λαμβάνω…'  vault=9
PROBE   'What is wisdom?'
  surface              = 'wisdom is defined as ...'
  articulation_surface = 'wisdom is defined as ...'
  walk_surface         = 'Wisdom does not with.'
  vault_hits           = 9
```

The probe retrieves 9 vault entries (so the premises **are** in
recall reach) but the realizer template emits a generic definition
stub.  The transitive entailment (`truth`) appears in neither
`surface` nor `walk_surface`.

## Architectural gaps (where the inference closure step is missing)

The roadmap pre-identified two suspects.  v1 evidence narrows it to
both:

### Gap 1 — `generate/graph_planner.py` has no transitive composition

When the premise `wisdom is light` is taught, a proposition-graph
node is created.  When `light is truth` is taught, a second node is
created.  No edge composition step runs that would emit a derived
node `wisdom is truth`.  The articulation target planner picks a
single node to articulate; it has no mechanism for chained traversal.

**Engineering shape** (out of scope for v1, in scope for v2):
- Extend `graph_from_intent()` to detect a probe whose form is
  "what does A R?" / "what is A?" and walk outgoing R-edges of A.
- Extend `plan_articulation()` to optionally compose a multi-node
  surface when the walk produces a single deterministic chain.

### Gap 2 — `field/propagate.py` has no derivable-but-not-asserted recall path

Vault retrieval scores `cga_inner(query, stored_versor)` and returns
the top-K direct matches.  There is no path-based recall that says
"return X if there is a relation-chain from the query entity to X."
The 9 vault hits for the probe include the premise versors but not a
derivation versor (none exists).

**Engineering shape** (also v2 candidate, may overlap with Gap 1):
- A path-recall operator over the relation-typed edges of vault
  entries.  Preserves exact-CGA semantics: the chain composition is
  deterministic, not approximate.

## Pass criterion review

The pass thresholds in `contract.md` (`derived_recall_rate >= 0.50`,
`premises_stored_rate >= 0.95`, `replay_determinism >= 0.95`) are
unchanged.  v1's failure is uniform on the derived-recall metric —
exactly what the contract was built to detect.

## What stands today

- The lane exists as a permanent regression and progress signal.
- Foundation guarantees (storage, replay) are independently scored
  and remain at 1.0 — closing the inference gap will not cost them.
- Structural-zero frontier baseline recorded
  (`baselines/v1_structural_zero.json`): frontier LLMs do not emit
  the typed signals these sub-metrics score by construction.

## Phase 3 exit posture

This lane satisfies the roadmap's v1 expectation: "v1 results with
honest scores (which may be failing — that's acceptable for v1)."
Phase 3 exit requires at least two lanes passing v1 by phase exit;
inference-closure's gap-1 / gap-2 engineering work, if undertaken,
flips this lane from failing v1 to passing v2 and contributes to
that count.  Until then it stands as load-bearing evidence of the
specific engineering work needed.
