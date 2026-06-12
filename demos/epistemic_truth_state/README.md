# Epistemic Truth-State Authority Demo

This demo proves one narrow boundary:

```text
A model-style proposer submits a claim, sealed evidence references, and an
optional bounded-inference block.
CORE alone assigns the typed epistemic state.
The output is a deterministic, replayable evidence artifact.
The proposer never controls its own truth-state.
```

## Public proof spine

```text
model proposes
substrate decides
trace proves
state is typed
```

## What this proves

* A model-style proposer can submit a claim without gaining authority over its
  epistemic standing.
* The proposer supplies evidence references only. CORE resolves those references
  against the sealed local corpus in
  [`evidence_corpus.json`](evidence_corpus.json), requiring a matching
  `content_sha256` before any evidence can count.
* CORE alone assigns the typed state, drawn from the canonical taxonomy in
  [`core/epistemic_state.py`](../../core/epistemic_state.py) — `verified`,
  `evidenced`, `inferred`, `contradicted`, `undetermined`, `scope_boundary`.
  There is no parallel enum.
* CORE derives `normative_clearance`, the `evidence_ledger`, the
  `authority_path`, and a fresh `trace_hash` itself.  The corpus seal
  (`corpus_sha256`) is pinned into every evaluated trace.
* Any proposer-supplied `proposed_state` or `trace_hash` is recorded as ignored
  and never read by the decision path.
* Invalid payloads fail at the typed boundary *before* any state evaluation
  runs.
* `verified` requires two or more corpus records that explicitly match the
  claim's subject and predicate and come from distinct provenance roots —
  corroboration the proposer cannot fabricate through the request schema.
* `inferred` is decided by a real entailment proof, not by reference counting.
  The cited premises (fact records contribute their `subject__predicate` atom;
  rule records their committed formula) must *propositionally entail* the
  claim's atom under
  [`generate/proof_chain/entail.py`](../../generate/proof_chain/entail.py) —
  the sound-and-complete ROBDD decision procedure — cross-checked against the
  independent truth-table oracle in
  [`evals/deductive_logic/oracle.py`](../../evals/deductive_logic/oracle.py)
  (no shared code).  The ROBDD proof keys and the oracle verdict are both in
  the trace; if the two procedures ever disagreed, the demo refuses outright.
  Citing records that merely *exist* yields `undetermined`, never `inferred` —
  the committed scenario `unrelated-premise-still-undetermined` exercises
  exactly that attack.

## What this does not prove

* It is not the runtime epistemic-state tagger; it is a local demo over fixed
  fixtures.
* It assigns epistemic truth-state only.  It runs **no** normative / safety /
  ethics clearance pass, so `normative_clearance` is `unassessable` on every
  non-invalid output — including `verified`.  This demo never positively clears
  a claim and makes no safety guarantee.
* It does not call a network, a model API, a subprocess, or any side-effecting
  tool.  It evaluates JSON and returns JSON.
* The entailment leg is propositional only (atoms are `subject__predicate`
  pairs); quantified or predicate-logic structure is out of regime and refuses
  upstream in the engine.
* It does not claim broader epistemic coverage than the small local envelope and
  the deterministic rules encoded in `authority.py`.

## Why proposer state is not authority

A model can *say* a claim is verified.  Saying so is data, not standing.  The
closed schema makes `assigned_state`, `status`, `evidence_ledger`,
`authority_path`, `trace_hash`, and `normative_clearance` impossible to supply
at the root — any attempt is an unexpected property and the payload is rejected.
The only state-bearing fields the proposer may include (`proposed_state`,
`trace_hash`, both inside `proposer`) are accepted by the schema purely so the
demo can prove CORE *ignores* them: they are echoed back as
`proposer_state_ignored` / `proposer_trace_hash_ignored` and never read by
`assign_epistemic_state`.

## Relation to #687 and #688

```text
#687 -> authority over claims (System 1 proposal -> CORE verifies/refuses/asks)
#688 -> authority over proposed tool actions (proposer suggests, CORE licenses)
this -> authority over epistemic state assignment (proposer claims, CORE types it)
```

Each layer keeps the same doctrine: a model-style proposer contributes typed
data, CORE alone decides, and the decision is a deterministic trace artifact
with no proposer-held authority and no execution path.

## The seven scenarios

* `verified-supported-claim` — two matching corpus records with distinct
  provenance roots → `verified`, `verified_by_matching_evidence` (clearance
  `unassessable`).
* `evidenced-but-not-verified-claim` — one supporting record → `evidenced`,
  `evidence_present_but_not_verifying`.
* `inferred-from-bounded-evidence` — two fact premises plus a ratified rule
  record propositionally entail the claim's atom → `inferred`,
  `entailed_from_resolved_premises`, with the ROBDD entailment trace
  (`entailment_check_key: "T"`), the independent oracle verdict, and
  `inference_basis` IDs.
* `unrelated-premise-still-undetermined` — a claim with no support citing a
  resolvable but logically unrelated record as a premise → the engine decides
  `unknown`, the state is `undetermined`.  `inferred` cannot be minted by
  citing records that merely exist.
* `undetermined-insufficient-evidence` — no relevant evidence → `undetermined`,
  `insufficient_evidence`, with an explicit `question`.
* `refused-outside-scope` — claim declared outside the local envelope →
  status `refused`, `scope_boundary`, `outside_epistemic_envelope`; the corpus
  is never consulted.
* `invalid-state-smuggling-attempt` — root-level `assigned_state` / `status` /
  `evidence_ledger` / `authority_path` / `trace_hash` injection → status
  `invalid`, `authority_evaluated: false`, every smuggled property listed in
  `invalid_reason`.

## Honesty ledger

* Real: closed recursive schema validation, canonical-enum state assignment via
  `core.epistemic_state`, sealed-corpus evidence resolution by content hash,
  sound-and-complete ROBDD entailment with independent-oracle cross-check on
  the inference leg, deterministic trace hashing over the response minus
  `trace_hash`, corpus seal pinning, evidence-ledger derivation,
  expected-artifact pinning, double-run byte-identical determinism,
  output-directory hardening.
* Simulated: the proposer side is static fixture data standing in for a
  model-style proposer; the evidence corpus is committed local fixture evidence,
  not retrieved from the live vault.
* Honest non-claim: `normative_clearance` is `unassessable` on every
  non-invalid output, including `verified`, because this demo runs no
  safety/ethics verdict pass and therefore has no basis to clear anything.
* Defensive path: the `entailment_oracle_disagreement` refusal exists and is
  tested (by forcing a fake oracle verdict in tests); it has never fired on
  real input and is expected never to — both procedures are sound and complete
  over the propositional regime.
* Not claimed: runtime integration, serving integration, real evidence
  retrieval, a safety guarantee, or any coverage beyond this local envelope.

## Example commands

```bash
python demos/epistemic_truth_state/run_demo.py
python demos/epistemic_truth_state/run_demo.py --json
python demos/epistemic_truth_state/run_demo.py --update-expected
pytest -q tests/test_epistemic_truth_state_demo.py
```
