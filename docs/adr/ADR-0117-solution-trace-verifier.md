# ADR-0117 — `SolutionTrace` Verifier

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114, ADR-0114a, ADR-0115, ADR-0116

---

## Context

ADR-0116 shipped the solver and emitted `SolutionTrace` records with
per-step `before_value` / `after_value` / `pack_lemma_id`, byte-
deterministic `canonical_bytes()`. The solver itself enforces
correctness at construction time, but the solver could be buggy,
tampered with after the fact, or replaced by a different
implementation. ADR-0114a Obligation #3 requires that **every
correct answer ship with a replay-equal trace**, and that requirement
is only load-bearing if a **verifier independent of the solver** can
reproduce the answer from the trace.

ADR-0117 ships that verifier.

---

## Decision

### `generate/math_verifier.py`

Exposes `verify(graph, trace) -> VerifierVerdict`. Pure function;
same `(graph, trace)` always returns a byte-equal verdict.

The verifier runs six named checks in order, accumulating each one's
result in `verdict.checks`:

| Check name | What it verifies |
|---|---|
| `graph_canonical_hash_matches` | `trace.graph_canonical_hash` equals a fresh `sha256(graph.canonical_bytes())` |
| `pack_id_matches` | `trace.pack_id == "en_arithmetic_v1"` |
| `pack_lemmas_resolve` | The arithmetic pack loads and provides every required lemma |
| `step_pack_lemma_ids_match_bindings` | Every step's `pack_lemma_id` equals the resolved binding for its `operation_kind` |
| `step_replay_matches_before_after` | Replaying each step from the graph's initial state reproduces every `before_value`, `after_value`, `target_before`, `target_after` byte-equal |
| `answer_value_reproduces` | The verifier's resolved `Unknown` equals `trace.answer_value` |

`VerifierVerdict.passed` is `True` only if every check held. On
failure, `reason` names the first failed check; `checks` holds the
full per-check record for audit.

### Independence from the solver

The verifier imports **only** the operation-semantics constants and
the pack resolver from `math_solver`. It does NOT call `solve()`. It
re-derives every value the trace claims using a fresh state machine
that lives in `_verify_step`. If a solver bug produced a wrong
`after_value`, the verifier catches it. If a tamperer rewrote
`answer_value` post-solve, the verifier catches it. If the input
graph's bytes were edited but the trace was not re-signed, the
`graph_canonical_hash` check catches it.

The verifier deliberately re-implements the operation semantics
documented in ADR-0116 rather than importing the solver's apply
function. This is **belt-and-suspenders for adversarial replacement
of the solver**.

### What a tampered trace looks like

| Tamper | Verdict |
|---|---|
| Mutate `before_value` of step N | `step_replay_matches_before_after: step N declares before_value=X, verifier computed Y` |
| Mutate `after_value` of step N | `step_replay_matches_before_after: step N declares after_value=X, verifier computed Y` |
| Mutate `operand.value` of step N | `step_replay_matches_before_after` (cascades through `after_value`) |
| Mutate `pack_lemma_id` of step N | `step_pack_lemma_ids_match_bindings: step N declares ...` |
| Mutate `graph_canonical_hash` | `graph_canonical_hash_matches: trace declares X but graph hashes to Y` |
| Mutate `answer_value` | `answer_value_reproduces: verifier resolved X, trace declared Y` |
| Mutate `pack_id` | `pack_id_matches: trace declares X, expected en_arithmetic_v1` |
| Mutate `target_before` / `target_after` of transfer step | `step_replay_matches_before_after: step N declares target_*=X, verifier computed Y` |

Every named tamper class is pinned by a test in
`tests/test_math_verifier.py`.

---

## Invariants

### `adr_0117_solver_traces_verify`

For every case in `evals/gsm8k_parser_dev/cases.jsonl`, the
verifier accepts the solver's own trace with `verdict.passed=True`.
Tested parametrized over all 50 cases.

### `adr_0117_tampered_trace_rejected`

For each named tamper class, a mutated `SolutionTrace` produces
`verdict.passed=False` with a reason naming the offending check.
Pinned by seven `TestTamperDetection` cases.

### `adr_0117_verifier_independent_of_solver`

The verifier does not invoke `solve()` and re-derives every value
from `graph` + `trace` alone. Inspected by import structure: the
verifier imports `_resolve_pack_lemmas`, `REQUIRED_PACK_ID`, and the
typed dataclasses, but NOT `solve` itself.

### `adr_0117_determinism`

Two `verify(graph, trace)` calls produce byte-equal
`VerifierVerdict.canonical_bytes()`. Tested directly.

---

## ADR-0114a obligation discharge update

ADR-0116 discharged Obligation #3 at **solver fidelity** (the solver
itself emits a trace that, when replayed in-process, reproduces the
answer). ADR-0117 now discharges Obligation #3 at **verifier
fidelity**: a third party with only the graph + trace and a
re-installation of the arithmetic pack reproduces the answer
byte-equal.

| Obligation | Status |
|---|---|
| #1 Sealed-holdout discipline | Substrate present; per-lane enforcement deferred to ADR-0119 |
| #2 OOD surface variation | In flight (delegated to Codex, ADR-0118a) |
| #3 Replay-equal trace | **Discharged at verifier fidelity** (was solver-fidelity under ADR-0116) |
| #4 Typed refusal | Discharged at solver layer (ADR-0116) |
| #5 Reasoning-isolation perturbation suite | Future ADR |
| #6 Compositional-depth curve | Measurement-only at promotion |
| #7 Frontier-baseline comparison | Deferred to ADR-0119 |
| #8 Adversarial generation | Deferred to ADR-0119 |
| #9 Determinism | Discharged at solver + verifier layers |
| #10 Operation provenance via pack | Discharged in full (ADR-0116); verifier re-checks |

Five obligations now have load-bearing implementations:
**#3 (now at verifier fidelity), #4, #9, #10**, plus the in-flight
#2 from Codex's ADR-0118a work.

---

## Acceptance evidence

Accepted when:

- `generate/math_verifier.py` exports `verify`, `VerifierVerdict`,
  `VerificationError`
- `tests/test_math_verifier.py` (62 cases) is green
- Verifier passes all 50 dev-set solver traces
- Every named tamper class is caught by the test suite
- Smoke suite is green
- ADR linked from `docs/decisions/README.md` index and frontier

---

## Consequences

- The promise "every correct answer reproduces from disk
  byte-for-byte" is now mechanically verifiable by anyone — including
  a reviewer who does not trust the solver. The trace + the graph +
  the pack are sufficient.
- The audit story strengthens: ADR-0114a Obligation #3 is no longer
  an in-process invariant; it's a cross-process invariant. A future
  `expert` promotion (ADR-0120) can require that every "correct" row
  in its evidence bundle ship with a verifier verdict, not just a
  solver outcome.
- The verifier is the substrate for ADR-0119's GSM8K eval lane:
  every case's answer goes through `verify()` before scoring. A
  problem with a wrong trace (replay drift) is treated as a `wrong`
  outcome, not `correct` — closing the loophole where a buggy solver
  could produce coincidentally-correct answers via wrong steps.

---

## Out of scope

- Stepped-realizer prose (ADR-0118) — distinct concern; consumes
  the same trace.
- GSM8K eval lane (ADR-0119) — uses this verifier as scoring
  substrate.
- Multi-pack verifier (verifier currently checks `en_arithmetic_v1`
  hardcoded; future domains may have their own operator packs).
- Property-based fuzzing the verifier against adversarial traces.
  Could be a follow-up if real-world traces ever produce surprises.
