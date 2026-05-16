# cross-domain-transfer lane — architectural findings (v1)

## v1 result

| Split | n | transfer_endpoint_recall | A_stored | B_stored | replay |
|---|---|---|---|---|---|
| public/v1 | 10 | **0.0** | 1.0 | 1.0 | 1.0 |
| holdouts/v1 | 8 | **0.0** | 1.0 | 1.0 | 1.0 |

No transfer.  Both A-domain and B-domain premises are independently
stored (storage rate 1.0 on each side); replay is deterministic; the
B-domain endpoint never appears in the probe surface.

## What this confirms (vs. inference-closure)

This lane is inference-closure plus a *prior* teaching pass in a
disjoint semantic subdomain.  v1's result establishes that:

- The A-domain teaching has **no carry-over effect** on B-domain
  competence.  This is consistent with CORE having no structural-
  pattern recogniser — the A-domain chain doesn't shape how the
  B-domain chain is articulated or recalled.
- Whatever fix closes inference-closure's Gap 1 / Gap 2 may close
  this lane's failure too, since B-domain alone is a literal
  inference-closure case.  But it will not *demonstrate transfer* —
  that requires a different signal, captured in v2.

## v2 contract refinement

To actually score transfer (rather than just "B-domain inference
works after A-domain teaching"), v2 of this lane should include a
matched control: same B-domain probe **without** prior A-domain
teaching.  Pass criterion becomes:

  transfer_endpoint_recall_rate(with_A_teaching) >
  transfer_endpoint_recall_rate(without_A_teaching)

That delta is the genuine transfer signal.  v1 leaves this on the
table because the floor is currently zero on both arms — a v1
"transfer = 0 − 0 = 0" result would be uninformative.  When the
inference-closure engineering lands and the B-arm starts producing
non-zero recall, v2's matched-control comparison becomes the
load-bearing measurement.

## Architectural gaps

1. **No structural-pattern recogniser.**  CORE's proposition graph
   has no concept of "the relation pattern `R(x1,x2)→R(x2,x3)` was
   seen N times across these subdomains" — patterns are not
   first-class entities.
2. **No cross-subdomain transfer operator.**  Vault retrieval and
   field propagation are entity-local; nothing maps "structural
   competence in subdomain A" to "expected competence in subdomain
   B."
3. Both gaps are downstream of (and overlap with) inference-closure
   Gap 1 + Gap 2.

## Future directions (recorded here so they're not forgotten)

- **Metaphor as cross-domain transfer with selectivity.**  A
  metaphor is the same shape as this lane's probe with an added
  filter: which relations transfer across the analogy and which do
  not.  Once literal cross-domain transfer works, building
  `metaphor-comprehension` on top is a natural Phase 3 v2 lane
  rather than a separate operator.
- **Narrative as multi-step cross-domain transfer.**  A story is a
  multi-step inference chain bound to a point-of-view (agent /
  intention).  Both substrates (multi-step chaining and POV) need to
  land before a `narrative` lane is meaningful.

## Status

v1 stands as honest-failure baseline.  v2 contract refinement
(matched-control comparison) is the next authoring step once
inference-closure engineering lifts B-arm recall off the floor.
