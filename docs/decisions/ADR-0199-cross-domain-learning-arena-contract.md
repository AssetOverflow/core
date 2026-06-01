# ADR-0199: Cross-Domain Learning Arena Contract

**Status:** Proposed
**Date:** 2026-05-31
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `core/reliability_gate/`, `core/capability/`, `evals/<domain>_practice/`, `teaching/`, `contemplation/`
**Depends on:** ADR-0175 (Calibrated Attempt-and-Eliminate Learning), ADR-0091 (Domain Pack Contract v1), ADR-0150 (Autonomous Inter-Session Contemplation), ADR-0151 (Auto-Proposal Pipeline)

---

## 1. Context & Problem Statement

ADR-0175 built a domain-general learning engine and proved it on **one** arena (GSM8K multiplicative math). The machinery is already generic:

- `reliability_gate/floor.py` — `conservative_floor(successes, committed)`, the pinned one-sided Wilson lower bound. `WILSON_Z = 2.576` and `N_MIN = 10` are **already fixed, global, and engine-untouchable**.
- `reliability_gate/ledger.py` — `ClassTally` counts `correct / wrong / refused / t2_verified / t2_agrees_gold` per `class_name` (any capability axis), exposing `reliability` and `t2_precision` as conservative floors.
- `reliability_gate/ceilings.py` / `gate.py` — `Ceilings` (human-set θ per class/action) and `license_for` (`measured ≥ required`).
- `reliability_gate/propose.py` — `propose_from_ledger` → `RatifiableProposal`, the proposal-only seam into the reviewed teaching corridor.
- `capability/domains.py` — the five base subjects already exist as keys: `systems_software`, `mathematics_logic`, `physics`, `hebrew_greek_textual_reasoning`, `philosophy_theology`, each with packs, corpora, and operator claims.

What is **missing** is everything *upstream* of the ledger for four of those five subjects. `propose.py`'s own docstring admits it: *"The attempt/score/ledger half already exists (`evals/gsm8k_math/practice`…)."* That half is bespoke to math. There is no domain-pluggable arena, no shared solver interface, and no reusable gold-tether harness. Each new subject currently implies re-deriving the attempt→score→ledger plumbing by hand — which both wastes the proven infrastructure and risks each subject quietly re-litigating the pinned floor.

This ADR fixes the **contract** by which any base subject plugs into the existing engine, so "get smarter on subject X" reduces to supplying a small, named set of domain-specific parts and nothing else.

## 2. Decision

A subject becomes a learning arena by supplying **exactly four domain-specific pieces** and reusing **all** of the shared engine unchanged. Anything beyond these four is a smell (it usually means intelligence is being pushed into packs instead of the solver — the anti-pattern ADR-0175 §Pivot-2 rejects).

### 2.1 The four-piece domain template

| Piece | What it is | Why it is domain-specific |
|---|---|---|
| **1. `DomainSolver`** | attempts a grounded derivation over the subject's operations and self-checks it | the operations differ per subject; this is where intelligence lives (ADR-0175 Pivot-2) |
| **2. Gold anchor set** | checksum-locked Tier-1 truth, partitioned by capability class | "truth" has a different mechanical form per subject |
| **3. Capability classes** | the per-subject axes the ledger counts over (the G1–G5 analog) | decomposition of the subject into measurable competence |
| **4. Tier-2 verifier** | ≥2 structurally-distinct derivations agree ∧ round-trip ∧ unit/type-consistent ∧ no contradiction | "structurally distinct" means something different in each subject |

Everything else is **shared and reused verbatim**: the pinned `conservative_floor`, `ClassTally`, `Ceilings`/`license_for`, `propose_from_ledger`, the contemplation→auto-proposal pipeline (ADR-0150/0151), and the reviewed-teaching seal.

### 2.2 The interfaces (additive; no change to the gate)

```python
from typing import Protocol, Sequence

class DomainProblem(Protocol):
    problem_id: str
    class_name: str          # capability axis this problem exercises

class Attempt(Protocol):
    committed: bool          # False == refused (safe; not counted against reliability)
    answer: object | None
    derivations: tuple       # the ≥2 structurally-distinct paths, for Tier-2
    trace_sha256: str        # replayable provenance, no raw content beyond hashes

class DomainSolver(Protocol):
    domain_id: str
    def attempt(self, problem: DomainProblem) -> Attempt: ...

class GoldTether(Protocol):
    domain_id: str
    def gold_answer(self, problem_id: str) -> object | None:   # Tier-1 truth, or None if unanchored
    def is_correct(self, attempt: Attempt, problem_id: str) -> bool
    def tier2_agrees_gold(self, attempt: Attempt, problem_id: str) -> bool  # on the anchor set only

def run_practice(
    solver: DomainSolver,
    tether: GoldTether,
    problems: Sequence[DomainProblem],
) -> dict[str, "ClassTally"]:
    """Sealed practice: attempt → gold-tether score → per-class ClassTally.
    The ONLY new per-domain code path. Output feeds propose_from_ledger unchanged.
    """
```

`run_practice` is the generalization of `evals/gsm8k_math/practice`: it is the same attempt→score→ledger fold, parameterized by `(DomainSolver, GoldTether)`. Its output is a `dict[str, ClassTally]` that flows into the **existing** `propose_from_ledger` with no modification.

### 2.3 Three mandates (the load-bearing constraints)

1. **One floor for all subjects.** Every arena uses the single pinned `conservative_floor` (`WILSON_Z`, `N_MIN`). A domain may **not** introduce its own pessimism constant. The only per-domain reliability dials are the θ ceilings (`Ceilings.with_override`, human-set, engine-untouchable) and the anchor set. This is what keeps "earned autonomy" meaning the same thing in physics as in software.
2. **Anchor independence is a design obligation, not an assumption.** The gold tether only catches *correlated self-delusion* (a shared wrong premise making all derivations agree) if the anchor's truth is produced by a path **independent of the solver's derivation**. This is automatic for some subjects and must be engineered for others (§3). An arena ships with an explicit independence argument or it does not ship.
3. **The seal is absolute and shared.** `run_practice` writes only the ledger; promotion is `propose_from_ledger` → reviewed teaching (ADR-0151's append-only `ProposalLog`). No arena, in any subject, may write the serving path or the active teaching corpus. The engine earns the right to *ask*, never to *serve*.

### 2.4 Per-subject instantiation (ranked by verifier strength)

The four-piece template makes the subject ranking objective: **how cheap and strong is the Tier-2 verifier, and is anchor independence automatic?**

| Subject (`domain_id`) | `DomainSolver` core | Tier-2 verifier | Anchor independence | Priority |
|---|---|---|---|---|
| **`systems_software`** | attempt over code transforms | **execution**: tests pass, types check, ≥2 impls agree | automatic — the test is not the code | **1st (hottest loop)** |
| **`physics`** | derivation over quantities (reuses math quantity machinery) | **dimensional/unit consistency** + numeric round-trip | automatic — measured answer ≠ derivation | 2nd |
| **`mathematics_logic`** | the proven operation-chain solver | symbolic re-derivation + round-trip | automatic | 3rd (deepen classes) |
| **`hebrew_greek_textual_reasoning`** | morphological/syntactic parse + attested-usage lookup | cross-translation + concordance agreement on **parse facts** | **must be engineered** (§3) | 4th (subtle) |
| **`philosophy_theology`** | composition over ratified cognition chains | consistency-only at best | gold rarely exists | **practice-internal only** |

Software is first because execution is the strongest, cheapest verifier in the system — you can actually *run* the answer — and the pruning skill the solver learns there transfers. Physics is second because dimensional analysis is a near-free structural Tier-2 check on top of machinery that already exists.

### 2.5 The Hebrew/Greek and philosophy/theology discipline (the honest boundary)

Note the repo **already** separates `hebrew_greek_textual_reasoning` from `philosophy_theology` in `capability/domains.py`. This ADR makes that separation load-bearing:

- The Hebrew/Greek gold tether anchors **only on the mechanically-checkable substrate** — morphology, parsing, attested lexical/grammatical facts (this form is aorist passive 3sg; this root carries this sense per a ratified lexicon). These have an independent source (the lexicon/grammar), satisfying mandate 2.
- It **never** scores interpretation or theological meaning. Those route to `philosophy_theology`, which the table above bounds to **practice-internal pruning only** — no gold, no serving promotion without human ratification.

This is the engineering form of the floor ADR-0175 named in Shay's own words — *"it cannot conjure world-facts from nothing… only God himself."* The engine may earn autonomy over *what a form is*; the *meaning of Scripture* is curated and ratified by humans, never self-authorized. Letting the tether grade theology would be precisely the correlated-self-delusion failure mandate 2 exists to prevent.

## 3. Consequences

### 3.1 Positive

- **One arena, five subjects.** After this contract, a new subject is "supply solver + anchors + classes + θ," not a plumbing rebuild. The proven engine is reused, not re-derived.
- **The subject ranking is objective**, derived from verifier strength rather than enthusiasm — and it points first at software, where the loop is safest and compounds fastest.
- **Autonomy means the same thing everywhere** because the floor is shared and the seal is absolute.
- **Contemplation gains four new things to chew on.** ADR-0150/0151 already convert discovery candidates to proposals; once each subject's arena runs, contemplation produces ratifiable proposals per subject with no new pipeline.

### 3.2 Negative / Risks

- **Pack-volume temptation.** The easiest-feeling move — adding vocabulary per subject — does not compound (ADR-0175 Dead-end-1). Breadth-of-impact under perturbation is the test, not pack size.
- **Anchor non-independence.** The subtle failure: an anchor whose "truth" was produced by the same reasoning the solver uses. Caught only by mandate 2's explicit independence argument and an adversarial test (§4).
- **Theology drift.** The standing risk that a future contributor points the tether at meaning. §2.5 and the domain separation are the guardrail; the proof obligations make a violation fail loudly.
- **Diagnostic mis-routing.** If a refusal does not name its axis (skill / knowledge / ambiguity, ADR-0175 Insight-3), the arena cannot tell "practice more" from "ingest a fact." Diagnostic refusal is a precondition, not an add-on.

## 4. Proof Obligations

Each must **fail loudly** under the violation it names (CLAUDE.md §Schema-Defined Proof Obligations):

- **L-1 (floor reuse).** Every arena's reliability flows through the single pinned `conservative_floor`. Fails if any domain defines its own `WILSON_Z`/`N_MIN`.
- **L-2 (anchor independence).** For each anchored class, a test demonstrates the anchor's truth derives from a source independent of the solver path. Fails if the solver can be shown to author its own gold.
- **L-3 (seal).** `run_practice` writes only `ClassTally`; no serving/corpus mutation. Fails if any arena path reaches the active teaching corpus without `accept_proposal`.
- **L-4 (determinism).** Same problems + same solver/tether ⇒ byte-identical ledger and byte-identical `propose_from_ledger` output.
- **L-5 (Tier-2 independence count).** A Tier-2 "agree" requires ≥2 *structurally-distinct* derivations; a negative test shows two trivially-identical paths do **not** count as agreement.
- **L-6 (theology boundary).** A test asserts the `hebrew_greek_textual_reasoning` tether scores only parse/lexical facts; feeding it an interpretive claim must refuse, not score.

## 5. Execution Plan

| PR | Scope | Gate |
|---|---|---|
| **PR-1 (this)** | ADR-0199 + interfaces (`DomainSolver`/`GoldTether`/`run_practice`) as docs/protocols | review |
| **PR-2** | `run_practice` generalized from `evals/gsm8k_math/practice`; math re-expressed as its first instance (no behavior change) | L-1, L-3, L-4 green; math ledger byte-identical to today |
| **PR-3** | `systems_software` arena: execution verifier + anchor set + classes + θ table | L-1…L-5 on software |
| **PR-4** | `physics` arena: dimensional-consistency verifier, reusing quantity machinery | L-1…L-5 on physics |
| **PR-5** | `hebrew_greek_textual_reasoning` arena: morphology/lexical tether | L-1…L-6, with L-6 the hard gate |
| **PR-6** | Contemplation wiring: per-subject `DiscoveryCandidate` → `propose_from_ledger` (ADR-0150/0151) | proposals appear per subject, review-gated, never auto-accepted |

`philosophy_theology` gets no anchored arena — it stays practice-internal (consistency-only) and human-ratified, by design.

## 6. Cross-References

- ADR-0175 — the engine this contract generalizes; the two regimes, the gold tether, the pinned floor, the seal.
- ADR-0091 — Domain Pack Contract v1; the manifest fields a subject's pack must carry to claim reasoning-capable status (axioms/rules/teaching_chains/eval_lanes/reviewers/known_gaps/provenance).
- ADR-0150 / ADR-0151 — autonomous contemplation and the auto-proposal pipeline; the multiplier that runs once each arena exists.
- ADR-0097 / 0100 / 0101 / 0102 — the reasoning-capable ratifications for the four anchored subjects.
- `core/reliability_gate/{floor,ledger,ceilings,gate,propose}.py`, `core/capability/domains.py` — the shared engine and the subject registry this contract plugs subjects into.