# Proof-Carrying Coherence Promotion Demo (ADR-0218)

This demo proves one narrow boundary:

```text
A model-style proposer submits a claim, a proof candidate, and
status/confidence garbage.
CORE ignores proposer authority entirely.
CORE fresh-reads curator-certified store state.
CORE recomputes the proof under the pinned deductive engine.
CORE promotes or refuses only through vault-owned certified promotion.
The trace proves the decision.
```

## Public proof spine

```text
proposer proposes
store state grounds
engine recomputes
vault owns the flip
trace proves
```

## What this proves

* A `SPECULATIVE` claim becomes `COHERENT` **iff** it is deductively entailed
  by an already-`COHERENT`, curator-certified premise set — decided by the
  REAL ratified promoter ([`teaching/proof_promotion.py`](../../teaching/proof_promotion.py)),
  not a demo-local reimplementation.
* The only mutation site is
  [`VaultStore.apply_certified_promotion`](../../vault/store.py), which
  independently replay-verifies the certificate under the pinned engine
  (`generate/proof_chain/engine_pin.py`) and fresh-reads live store state
  before flipping anything.  This demo adds **no** vault writer and **no**
  status-transition site: the local arena is reconstructed via the
  persistence path (`VaultStore.from_dict`), and INV-21 / INV-29 scan this
  directory.
* Proposer-attached `proof` / `status` / `confidence` / `certificate` /
  `trace_hash` are data, never authority: the whole proposer block is handed
  to `certify_promotion` as `proposer_payload`, which deletes it unread
  (ADR-0218 §D3.5).  The artifact records the ignored field names; the tests
  prove the decision and the certificate digest are byte-identical with and
  without the garbage.
* A tampered certificate fails byte-for-byte replay re-verification and
  mutates nothing.  A certificate built from a stale store state (a premise
  re-stated `contested` after certification) is refused by the vault's
  live fresh-read — the same honest certificate, the same digest, a
  different live world, no flip.
* Invalid payloads (attempts to smuggle `promoted`, `final_status`,
  `authority_path`, `certificate_digest`, `trace_hash`, `evidence_ledger`,
  …) are rejected by the closed schema *before* any evaluation runs:
  `authority_evaluated: false`, `certificate_digest: null`, no arena is even
  built.
* Every output embeds the certificate's SHA-256 digest and the engine pin,
  and the response `trace_hash` is computed over the whole body — the
  certificate digest therefore folds into the trace hash.

## Honesty ledger — what this does NOT prove

* This demo proves **local deterministic proof-carrying promotion in the
  demo envelope** — fixed fixtures, a throwaway local store arena, a small
  propositional regime.  Nothing more.
* Promotion is from `SPECULATIVE` to `COHERENT` **only**.  No other
  transition is performed or claimed.
* Promotion requires, jointly: live store state, curator-certified readings
  (`reading_certified: true` + the certified form), all-`COHERENT` premises,
  pinned replay verification, and vault-owned mutation.  Remove any one and
  the demo refuses.
* Proposer confidence / status / proof is **not** authority — and saying so
  here is backed by tests, not by trust.
* This does **not** prove autonomous open-world learning.  The premises and
  readings are curator-declared fixture data; the reading (NL→proposition)
  step remains the human-certified hazard surface (ADR-0218 §D2).
* This does **not** prove production runtime integration.  No chat/runtime
  turn path calls promotion; this is a fixture-driven local demo.
* This does **not** prove normative or safety clearance.  It certifies
  entailment over reviewed premises, nothing about whether a claim is safe,
  ethical, or appropriate to act on.
* `REFUTED` does **not** demote in v1.  A refuted claim stays `SPECULATIVE`;
  demotion is a separate authority question ADR-0218 explicitly left open.
* No external side effects occur.  No network, no model API, no subprocess,
  no `eval`/`exec`; the runner writes only inside its own output directory
  (default `out/`, gitignored) and refuses unsafe output roots.

## Running

```bash
python demos/proof_carrying_promotion/run_demo.py            # verify against committed expected artifacts
python demos/proof_carrying_promotion/run_demo.py --json     # machine-readable summary
python demos/proof_carrying_promotion/run_demo.py --write-expected  # explicitly re-pin expected artifacts
```

Each fixture is executed twice and must be byte-identical across runs and
byte-identical to its committed expected artifact.  The eight scenarios:

| scenario | status | proves |
|---|---|---|
| `entailed-promotes` | promoted | entailed-from-COHERENT flips SPECULATIVE→COHERENT through the vault owner |
| `proposer-status-ignored` | refused | proposer "coherent/verified" garbage cannot rescue a non-entailed claim |
| `non-coherent-premise-refuses` | refused | a SPECULATIVE premise poisons a structurally valid entailment |
| `uncertified-reading-refuses` | refused | an uncertified reading fails closed before the engine runs |
| `tampered-certificate-refuses` | refused | a certificate that does not replay byte-for-byte mutates nothing |
| `stale-premise-status-refuses` | refused | live store state outranks a previously-honest certificate |
| `non-sequitur-refuses` | refused | UNKNOWN never promotes; the claim stays SPECULATIVE |
| `invalid-state-smuggling-attempt` | invalid | output fields cannot be supplied; rejection precedes evaluation |

Tests: [`tests/test_proof_carrying_promotion_demo.py`](../../tests/test_proof_carrying_promotion_demo.py).
