# cross-domain-transfer eval lane

## What it measures

Whether competence on a relation pattern taught in **semantic
subdomain A** transfers to the **same relation pattern in semantic
subdomain B**, where A and B share no entities.

Setup per case:

  Teach phase (subdomain A):
    R(x1, x2), R(x2, x3)  — A-domain entities only.
  Probe phase (subdomain B):
    "What does y1 R?"     — B-domain entities only,
                            never used in teaching.
  Premise pre-loading in B:
    R(y1, y2), R(y2, y3)  — taught at probe time so the model
                            has the B-domain premises in vault.

Pass = the probe answer references `y3` (the derived endpoint in
subdomain B).

The discriminator vs the inference-closure lane: here the model has
also seen the *same relation pattern* applied to A-domain entities
first.  If transfer happens, the second-application latency / hit
rate should improve.  Today the working hypothesis is that no
transfer happens because no structural-pattern recogniser exists.

## Subdomain partition (drawn from en_core_cognition_v1)

| Domain A (taught first) | Domain B (probed) |
|---|---|
| `cognition.wisdom` / `epistemic.judgment` cluster: wisdom, judgment, decision | `cognition.illumination` / `perception.clarity` cluster: light, clarity, recognition |
| `cognition.knowledge` / `reason.*` cluster: knowledge, reason, inference | `cognition.creation` / `formation.origin` cluster: creation, order, structure |
| `cognition.language.*` cluster: word, meaning, symbol | `memory.*` / `recognition.*` cluster: memory, recall, recognition |

## Sub-metrics

- `M1. transfer_endpoint_hit`     — endpoint `y3` appears in probe
  surface or walk_surface.
- `M2. domain_b_vault_grounded`   — at least one B-domain premise
  fires a `pack_mutation_proposal` (confirms B premises stored).
- `M3. domain_a_premises_stored`  — every A-domain teaching turn
  fires a proposal (regression gate for storage).
- `M4. replay_determinism`        — two fresh runs match by
  trace_hash on the whole (A-teach, B-teach, probe) sequence.

A case passes when M1 AND M2 AND M3 AND M4 hold.

## Overall pass thresholds (v1)

- `transfer_endpoint_recall_rate` (M1) ≥ 0.50
- `premises_stored_rate` (M2 ∧ M3) ≥ 0.95
- `replay_determinism` ≥ 0.95

## v1 working hypothesis

The same architectural gaps that surfaced in inference-closure
(`graph_planner.py` has no transitive composition;
`field/propagate.py` has no path-recall) apply here.  Additionally,
**no structural-pattern recogniser exists** that would let the
A-domain teaching shape behaviour in subdomain B.  v1 is expected
to score `transfer_endpoint_recall_rate ≈ 0`.

The value of the lane in v1 is to baseline transfer at zero so that
any future pack-design or graph-planner work that produces real
transfer is visible against this regression line.

## Anti-overfitting

- A-domain and B-domain entity sets are disjoint (verified at
  authoring time).
- The relation `R` is drawn from the existing lexicon — not invented
  for the lane.
- Holdouts uses subdomain pairings disjoint from the public split.
