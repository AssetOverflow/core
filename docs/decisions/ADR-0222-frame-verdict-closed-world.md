# ADR-0222: FrameVerdict — Frame-General Closed-World Verdict

**Status:** Proposed (design-only). Implementation is gated behind two preconditions:
(a) the ProofWriter-OWA refusal floor has landed — **met** (`evals/proofwriter_owa/`,
PR #779) — and (b) ratification of *this* ADR. The design PR ships **only this
document**; no runtime type, no entry point, no lane, no `answer=False` path, and
no change to `generate/determine/determine.py` lands until the implementation
plan in §10 is authorized.
**Date:** 2026-06-15
**Domains:** `generate/frame_verdict/` (proposed, new), `generate/proof_chain/`,
`sensorium/environment/`, `core/response_governance/`, `core/epistemic_disclosure/`,
`evals/proofwriter_cwa/` (proposed, future)
**Depends on:** ADR-0211 (Conformal Falsification Bench — perceptual closed-frame
verdict), ADR-0206 (response governance / `ReachLevel` / `shape_surface`), ADR-0201/0202
(ROBDD canonicalizer), ADR-0203–0205 (`proof_chain` entailment), ADR-0175 (calibrated
learning / serving gate), ADR-0218 (proof-carrying promotion). Builds on INV-25/INV-27
(independent gold + transitive-import disjointness), INV-29 (status-transition allowlist),
INV-30 (open-world `determine` never asserts False), and the merged Step-3 brief pack
(#777, brief B4).
**Authors:** drafted by agent for architect review (Joshua Shay ratifies). This draft
incorporates an adversarial review pass (6 independent skeptics against real source);
the soundness corrections it produced are folded in and flagged inline as **[adv]**.

---

## 1. Context

CORE's open-world determination gear is sound by a hard firewall: `determine()`
(`generate/determine/determine.py`) constructs only `Determined(answer=True)` or
returns `Undetermined(reason=…)`. **Absence of a fact never refutes it.** INV-30
(`tests/test_architectural_invariants.py`) mechanically enforces this: an AST scan
over the whole source tree fails the build if *any* `Determined(…)` construction
sets `answer` to anything but the literal `True` — there are exactly three sites,
all in `determine.py`, all `answer=True`, and `test_determine_construction_sites_are_visible`
pins the count. (The adversarial review ran the real `_determined_constructions`
predicate against the proposed type and confirmed it returns `[]` — see §11.)

This is correct for the open world. But three real capabilities need a sound
**closed-world "No"** — an *entailed negation*:

- **ProofWriter-CWA / FOLIO** two-sided labels (`{True, Unknown, False}`) where the
  fact set is declared complete and `False` is a real answer, not a refusal.
- **Perceptual falsification** (ADR-0211): an `ExpectedObservationFrame` is a closed,
  completely-enumerated expectation; an expected slot observed with a *contradicting
  identity* refutes the conformance of the observation to the expectation.
- Future **audio / vision** frames, which converge on the same envelope.

INV-30's own error message names this gap verbatim: *"a closed-world assert-False
capability must use a distinct result type **and** entry point, never this one."*

The hazard this ADR guards is a `wrong=0`-class soundness breach: a closed-world
`False` leaking into the open-world runtime would assert `not Q` from what is really
just *absence of Q* — exactly the contamination INV-30 exists to prevent. The OWA
floor (#779) is the dual gate from the other side: it fails if the open-world engine
ever asserts `True` on a gold `Unknown`/`False`. FrameVerdict must be built **on top
of** both floors, never around them.

### 1.1 What already exists (the anti-reinvent inventory)

A frame-general closed-world verdict is **not a new solver**. Every soundness-bearing
decision it needs already exists and is sound-by-construction:

| Need | Existing producer | Verdict it emits |
|---|---|---|
| Propositional entailed-`False` | `generate/proof_chain/entail.py::evaluate_entailment_with_trace` | `Entailment.REFUTED` when `(⋀premises) → ¬query` is an ROBDD tautology, with an `EntailmentTrace` proof |
| Inconsistent premises (≠ False) | same, via `generate/logic_canonical.py::CanonicalProposition.is_contradiction` | `Entailment.REFUSED(INCONSISTENT_PREMISES)` — declines (*ex falso quodlibet*), never asserts |
| Out-of-regime (ungrounded ∀/predicate) | same | `Entailment.REFUSED(OUT_OF_REGIME_OR_MALFORMED)` |
| Perceptual frame conformance | `sensorium/environment/falsification.py::compare_expected_to_observation` | `verdict = "SUPPORTED" \| "FALSIFIED"` — a *set-comparison* of one actual frame to one expected frame, with a structural `FalsificationResidual{matched, missing, unexpected, changed}`. **[adv]** This refutes a hypothesis-scoped expectation by set-inequality; it is **not** itself a proof of `¬query` — only the `changed` sub-case is a positively-observed contradiction (see §5.2). |
| Independent text gold (3-way) | `evals/proofwriter_owa/oracle.py::label` (aliased `owa_label` in `score.py`) | `"True" \| "Unknown" \| "False"` — disjoint from the engine (INV-25/27) |

The genuinely missing pieces are narrow and three: **(1)** a single frame-general
*envelope* type with a lane-scoped entry point distinct from `determine()`; **(2)** the
explicit **closed-frame context** that licenses asserting the negation (no runtime
module builds one today for text); and **(3)** a **firewall** (proposed **INV-31**)
that fails loudly if a closed-world verdict reaches the open-world runtime. The `False`
*decision itself* is delegated to the producers above — it is never re-implemented here.

---

## 2. Decision

Introduce **`FrameVerdict`**: a single, frame-general, closed-world verdict type that

1. is a **distinct dataclass** (never `Determined`, no `answer: bool` field), so the
   INV-30 call-name scan cannot fire on it and it cannot masquerade as an open-world
   answer;
2. is produced **only** at a lane-scoped entry point that takes an explicit
   **`ClosedFrame`**, never a `SessionContext` — structurally unable to read open-world
   session memory;
3. asserts `entailed_false` **only from a positive proof of the negation** (an ROBDD
   refutation, or a perceptual `changed`-slot contradiction), **never from absence** —
   neither textual non-provability nor a missing/extra observation;
4. delegates every soundness decision to existing producers (§1.1) — it is a
   convergent envelope, not a solver;
5. carries honest standing via the existing `_basis(grounds)` rule, never minting
   COHERENT/verified, never writing `epistemic_status` (INV-29);
6. reaches a user surface **only** through the existing response-governance gate
   (`govern_response` → `shape_surface`, `choose_served_disposition`), default-dark —
   no parallel servability object;
7. is firewalled from the open-world runtime by **INV-31**, a *two-part* firewall
   (transitive import containment **and** a typed data-flow guard) specified in §8 with
   per-scan non-vacuity anchors.

The spine stays modality-neutral (cf. `project-spine-modality-neutral-convergence`):
text-CWA and perceptual falsification converge **at the front** via a `frame_kind`
discriminator — the same idiom as `RealizedRecord.structure_kind` — not via a spine
rewrite. The shared object is the **output envelope + governance path + replay digest**;
the **input signature differs by frame** (§6).

---

## 3. Type shape

> **Proposed — does not yet exist.** This lands in implementation **PR-1** *together
> with* INV-31, never after it. It is shown here as an illustrative fenced block, not
> an importable module, to keep this PR design-only.

```python
from dataclasses import dataclass
from enum import Enum, unique

@unique
class FrameKind(str, Enum):
    TEXT = "text"              # a declared-complete CWA fact set (ProofWriter-CWA, FOLIO)
    PERCEPTION = "perception"  # an ADR-0211 ExpectedObservationFrame vs an ObservationFrame
    # AUDIO = "audio"; VISION = "vision"  # reserved — they converge identically

@unique
class WorldAssumption(str, Enum):
    OPEN = "open"                      # absence ⇒ undetermined; entailed_false is ILLEGAL here
    CLOSED = "closed"                  # frame declared complete
    BOUNDED_CLOSED = "bounded_closed"  # complete only within a declared scope

@unique
class FrameVerdictKind(str, Enum):
    ENTAILED_TRUE  = "entailed_true"   # the frame proves query
    ENTAILED_FALSE = "entailed_false"  # the frame proves ¬query (positive refutation)
    UNDETERMINED   = "undetermined"    # neither query nor ¬query proven — within-frame refusal
    CONTRADICTION  = "contradiction"   # the frame's own premises are inconsistent — NOT a False
    SCOPE_BOUNDARY = "scope_boundary"  # out of decidable regime / frame not licensed complete

@dataclass(frozen=True, slots=True)
class ClosedWorldProof:
    """Modality-blind, content-addressed proof envelope. Text and perception carry
    the SAME shape; only `producer`, `outcome`, and the keys differ."""
    producer: str                # "proof_chain.entail" | "sensorium.falsification"
    outcome: str                 # the producer's own literal: REFUTED/ENTAILED/UNKNOWN | FALSIFIED/SUPPORTED
    proof_keys: tuple[str, ...]  # entail: (conjunction_key, query_key, refutation_check_key)
                                 # perception: (FalsificationRun.trace_hash,)  -- the FULL run witness
    proof_sha256: str            # sha256_json over the canonical proof payload

@dataclass(frozen=True, slots=True)
class FrameVerdict:
    """A closed-world verdict. DISTINCT from generate/determine/Determined:
    no `answer: bool`, a 5-way `verdict` enum instead, a distinct name, and a
    distinct entry point. INV-30's call-name scan cannot match it; it can never
    be confused with an open-world answer."""
    frame_id: str                  # content-addressed id of the explicit closed frame
    frame_kind: FrameKind
    world_assumption: WorldAssumption
    query: str                     # the proposition under test (canonical key). NOTE [adv]: for
                                   # perception this is the FRAME-CONFORMANCE proposition keyed by
                                   # expected_id ("the observation conforms to this expected frame"),
                                   # NOT an arbitrary asked proposition — see §5.2.
    verdict: FrameVerdictKind      # the two-sided result — NOT a bool, NOT named `answer`
    basis: str                     # _basis(grounds): "as_told" | "verified" (never hardcoded)
    proof: ClosedWorldProof        # the replayable refutation/entailment/falsification evidence
    evidence: tuple[str, ...]      # content-addressed refs (grounds replay_hashes / _reject_unsafe_unit-
                                   # screened merge_keys) — never raw payloads or efferent traces
    trace_hash: str                # sha256_json deterministic replay digest of the whole verdict

    def __post_init__(self) -> None:
        # [adv] Admissibility invariant — makes §12 obligation 2 non-vacuous: entailed_false
        # may exist ONLY with a positive-refutation proof. A mismatched (verdict, proof) pair
        # fails loudly at construction, so a mutation test can trip it.
        if self.verdict is FrameVerdictKind.ENTAILED_FALSE:
            if self.proof.outcome not in {"REFUTED", "FALSIFIED"} or not self.proof.proof_sha256:
                raise ValueError("entailed_false requires a positive-refutation proof")
```

Notes binding the shape to existing contracts:

- **No `answer` field, distinct name.** INV-30's predicate keys *only* on the literal
  call name `Determined` and the `answer` argument. `FrameVerdict` matches neither;
  a two-sided enum cannot be smuggled as `answer=True`.
- **`basis ∈ {as_told, verified}`**, computed by the **existing** `_basis(grounds)` rule
  over the grounds' `epistemic_status`. Today every realized record is SPECULATIVE →
  `as_told`. A proofless verdict can never claim `verified`. The proof-backing lives in
  `proof`, *orthogonally* — so a sound refutation over `as_told` grounds is honestly
  "I was *told* these facts; from them, ¬query is *proven*." **[adv]** `_basis` currently
  lives inside `determine.py`; PR-1 lifts it to a shared `generate/epistemic_basis.py`
  so neither package depends on the other's internals (§8).
- **No `epistemic_status` field.** Standing is read-only via `basis` + the grounds' own
  stored status; `FrameVerdict` never *writes* an `epistemic_status` key, keeping INV-29's
  `{vault/store.py}` allowlist untouched.
- **`proof` and `trace_hash` are content-addressed and replay-stable** (`sha256_json`,
  order-invariant). **[adv]** For perception, `proof_keys` carries the **full
  `FalsificationRun.trace_hash`** (which binds `expected_sha256 + actual_trace_hash +
  verdict`), **not** `residual_sha256` alone — the residual hash does not bind the
  expected/actual frame identities and two different `(expected, actual)` pairs can share
  a residual delta. No clock, no RNG, no LLM, no probabilistic confidence, no tolerance.
- **`evidence` carries only content-addressed references** (grounds' `replay_hash`,
  perception units' `merge_key` — all already `_reject_unsafe_unit`-screened), never raw
  modality payloads or efferent traces, matching ADR-0211's discipline.

### 3.1 The closed-frame context

```python
@dataclass(frozen=True, slots=True)
class ClosedFrame:
    """The EXPLICIT closed-world context that licenses asserting a negation. The
    entry point takes THIS, never a SessionContext — so it structurally cannot read
    open-world session memory where absence ≠ false."""
    frame_id: str
    frame_kind: FrameKind
    world_assumption: WorldAssumption     # must be CLOSED or BOUNDED_CLOSED — OPEN ⇒ refuse
    propositions: tuple[str, ...]         # text: the COMPLETE enumerated fact set incl. declared
                                          #       negations/disjointness (content-addressed)
    expected_frame_ref: str | None        # perception: id of the ExpectedObservationFrame (ADR-0211)
    frame_sha256: str
```

A `ClosedFrame` is **constructed explicitly by the lane / scenario**, never defaulted
from `SessionContext` or `VaultStore`. There is no "the session is closed" mode. If a
caller supplies `world_assumption == OPEN`, or omits the closure declaration, the entry
point returns `SCOPE_BOUNDARY` (refusal), never `entailed_false`. This is the dual of
INV-30: the open-world path lacks the completeness license and so may only assert True
or refuse; the closed-world path may assert False **only because it was handed an
explicit, declared-complete frame and a positive proof of the negation.**

---

## 4. Entry points

```text
OPEN  WORLD (unchanged):  determine(question, ctx: SessionContext) -> Determined | Undetermined
                          # asserts answer=True or refuses. NEVER FrameVerdict. NEVER answer=False.

CLOSED WORLD (new):       evaluate_frame_verdict(frame: ClosedFrame, query: str) -> FrameVerdict
                          # lives in NEW top-level-isolated package generate/frame_verdict/.
                          # Takes a ClosedFrame, never a SessionContext. Returns FrameVerdict,
                          # never Determined. For perception, `query` is synthesized as the
                          # frame-conformance proposition keyed by expected_id (§5.2).
```

Hard rules (enforced by INV-31, §8):

- `determine()` and `generate/determine/determine.py` are **untouched**. The function's
  return union stays `Determined | Undetermined`; its three `Determined(answer=True)`
  sites stay exactly three. No `answer=False` branch is ever added anywhere.
- `evaluate_frame_verdict` is the **only** constructor of `FrameVerdict`, and lives in a
  package the open-world runtime spine does **not** transitively import.
- The two paths share the **front-end reader** (`comprehend` → `realize`, the same
  `RealizedRecord` grounds shape) but diverge at context establishment and entry point.
  Reusing the reader is sanctioned; reusing the *entry point* is forbidden. **[adv]**
  Because the reader is shared, INV-31 must firewall the *data flow*, not only the module
  imports: a `ClosedFrame`-derived grounds must be unable to enter `determine()`, and the
  disclosure gate must refuse to render a `FrameVerdict` through an open-world disposition
  (§8 Part B).

---

## 5. Semantics — the verdict table

The single load-bearing rule: **a closed frame licenses `False`, and `entailed_false`
is produced only from a *positive proof of the negation*.** "The world is closed" is
realized by the frame *declaring* its closure facts (disjointness, expected-set
completeness), which the existing sound producers then consume — **not** by an unsound
"not-provable ⇒ false" (text) or "not-observed ⇒ false" (perception) leap.

### 5.1 Text frame (`frame_kind = text`)

`evaluate_frame_verdict` lowers the `ClosedFrame.propositions` + `query` to the
propositional regime and calls the *existing* `evaluate_entailment_with_trace(premises,
query)`:

| `entail.py` outcome | `FrameVerdict.verdict` | Rationale |
|---|---|---|
| `ENTAILED` (`(⋀prem) → query` taut.) | `entailed_true` | the frame proves query |
| `REFUTED` (`(⋀prem) → ¬query` taut.) | `entailed_false` | the frame **proves** ¬query — sound closed-world No |
| `UNKNOWN` | `undetermined` | neither proven — within-frame refusal (NOT False) |
| `REFUSED(INCONSISTENT_PREMISES)` | `contradiction` | the frame's own premises clash — decline, *ex falso* |
| `REFUSED(OUT_OF_REGIME_OR_MALFORMED)` | `scope_boundary` | ungrounded ∀/predicate — not decidable here |

The `EntailmentTrace` (with `refutation_check_key` — the ROBDD key of `(⋀prem)→¬query`)
becomes the `ClosedWorldProof`; `producer="proof_chain.entail"`, `outcome="REFUTED"`.
*(Adversarial review confirmed `REFUTED` is a genuine `(⋀prem)→¬query` tautology — a
real positive proof — and that `UNKNOWN`/`INCONSISTENT_PREMISES` stay strictly out of
`entailed_false`.)*

### 5.2 Perception frame (`frame_kind = perception`)  **[adv — fully revised]**

ADR-0211 has **no `query` and no `¬query` proof**: a `FalsificationRun` is a *set
comparison* of one actual frame to one hypothesis-scoped `ExpectedObservationFrame`. So
the perception convergence must (a) name the proposition it decides, and (b) refuse to
launder absence/over-observation into `entailed_false`.

**The perception query is frame-conformance**, keyed by the expected frame:
`query = "observation conforms to expected frame " + expected_id`. Under *that specific*
proposition, the residual decomposes (it is **not** a bare `SUPPORTED/FALSIFIED` map):

| Residual condition (from `FalsificationResidual`) | `FrameVerdict.verdict` | Why |
|---|---|---|
| `SUPPORTED` (`matched == expected`, none missing/changed/unexpected) | `entailed_true` | the conformance proposition is positively observed |
| `changed ≠ ()` (a declared-expected slot observed with a **contradicting** `merge_key`) | `entailed_false` | a **positively observed** contradiction of a declared expectation — sound No |
| `missing ≠ ()` only (an expected slot received **no** observation) | `undetermined` | absence, not contradiction — the perception analogue of NAF (deferred, see §5.3) |
| `unexpected ≠ ()` only (an extra slot appeared) | `undetermined` | over-observation ("saw more than expected") — not a refutation of any expected slot |
| whole actual frame absent (`_missing_actual_run`, `actual_frame_id="__missing_observation_frame__"`) | `scope_boundary` | observed nothing — a coverage gap, never a proof of ¬query |
| `_canonical_refs` conflicting-slot raise (`ExpectedObservationFrame` ill-formed) | `scope_boundary` | the frame is not a licensed complete expectation |

`ClosedWorldProof` for an `entailed_false`: `producer="sensorium.falsification"`,
`outcome="FALSIFIED"`, `proof_keys=(FalsificationRun.trace_hash,)`, and the adapter
asserts `changed ≠ ()` before emitting `entailed_false` (the `__post_init__` invariant of
§3 is the backstop). Perception is **binary-native** (ADR-0211 v1 emits only
`SUPPORTED`/`FALSIFIED`), so in v1 it inhabits the subset
`{entailed_true, entailed_false, undetermined, scope_boundary}` of the verdict alphabet;
a query the expected frame under-determines is routed to `scope_boundary`, never forced.

### 5.3 The rules that keep `entailed_false` sound (both frames)

1. **Positive proof only.** `entailed_false` requires either an ROBDD `REFUTED` proof
   (text) or a `changed`-slot contradiction (perception). There is **no** `entailed_false`
   from textual non-provability, from a missing observation, or from an extra observation.
2. **`contradiction` is not `False`.** Inconsistent frame premises yield `contradiction`
   (decline), never `entailed_false`. The design must not collapse `REFUTED` and
   `INCONSISTENT_PREMISES` — different facts about the world (and, per §7, they must stay
   distinguishable *at the disclosure layer*, not only upstream).
3. **`undetermined` stays `undetermined` outside a complete frame.** Under
   `bounded_closed`, anything outside the declared bound is `undetermined`/`scope_boundary`,
   never `False`. This is exactly the OWA discipline (`label` returns `Unknown` from
   absence, `False` only from declared disjointness).

> **Deferred (separately ratifiable):** *negation-as-failure* in both frames — text
> "declared-complete ⇒ unprovable is false" **and** perception "observation-complete ⇒
> a missing expected slot is false." This is the single riskiest soundness hinge —
> "the frame/observation is truly complete" is a strong, easy-to-get-wrong claim — so v1
> omits it on **both** sides. When pursued, each must carry an explicit, machine-checkable
> completeness witness and its own `wrong=0` proof; the text side must still route through
> `entail` (the completeness facts become premises), and the perception side must carry an
> observation-completeness license, never a bare absence leap.

---

## 6. Modality convergence

```mermaid
flowchart TD
    subgraph FRONT[shared front-end reader]
      R[comprehend → realize\nRealizedRecord grounds]
    end
    R --> K{frame_kind\n+ explicit ClosedFrame}
    K -->|text: propositions + query| T[evaluate_entailment_with_trace\nENTAILED / REFUTED / UNKNOWN / REFUSED]
    K -->|perception: expected vs actual| P[compare_expected_to_observation\nresidual decompose §5.2]
    K -.->|audio / vision\n(reserved)| F[same envelope,\ndifferent frame evidence]
    T --> V[FrameVerdict\nverdict + ClosedWorldProof + trace_hash]
    P --> V
    V --> G[core/epistemic_disclosure\nchoose_served_disposition → govern_response → shape_surface]
    G --> U[user surface\ndefault-dark]
```

The discriminator `frame_kind` partitions substrates **at the front**, exactly as
`RealizedRecord.structure_kind` already partitions meaning-graph vs binding-graph
substrates. **[adv]** What is *shared* across frames is the **output envelope, the
governance/disclosure path, and the replay digest**. The **input signature differs by
frame**: text takes `(propositions, query)`; perception takes `(expected_frame,
actual_frame)` and *synthesizes* the frame-conformance query (§5.2). A new modality adds
a `FrameKind` member and a producer adapter — never a new verdict alphabet, never a spine
rewrite. The render integration lives entirely in `core/epistemic_disclosure` (§8), so
`chat/runtime.py` never imports the closed-world package.

---

## 7. Standing & servability (no parallel object, default-dark)  **[adv — revised]**

`FrameVerdict` produces a typed verdict and **commits/serves nothing itself** — the
discipline of `ConverseEstimate`, which returns a candidate and lets the gate + disclosure
layer decide. A wrong served closed-world verdict must always be a *disclosed* wrong.

Two distinct axes carry standing and must not be conflated:

- **`basis`** (`teaching.epistemic.EpistemicStatus` → `as_told`/`verified`), computed by
  `_basis(grounds)`. This is the *grounds' standing*.
- **`EpistemicState`** (`core.epistemic_state`, the 15-member governance taxonomy). For
  the *limitation* verdicts, a `FrameVerdict` is lowered to a `LimitationAssessment` whose
  state is derived by the **existing** `limitation.py::_KIND_TO_STATE`. `_basis` does
  **not** produce an `EpistemicState`; the two enums are orthogonal.

Mapping onto the **existing** closed sets (no fourth taxonomy):

| `FrameVerdict.verdict` | Is it a limitation? | `LimitationKind` / `ResolutionAction` | `ServedDisposition` | Notes |
|---|---|---|---|---|
| `entailed_true` | no — a committed **answer** ("Yes") | — | `COMMIT` | surface carries the `as_told`/`verified` basis honestly; produced `EpistemicState` is a PR-4 reconcile obligation (do **not** stamp `EVIDENCED`, which is `RECONCILE`/un-produced drift) |
| `entailed_false` | **no — a committed answer ("No")**, not a block | — | `COMMIT` | **[adv]** the genuinely-missing piece is a *grounded-negative renderer* (PR-4); `render_determination` only renders affirmations. It is **not** a `contradiction` and must **not** reuse `LimitationKind=contradiction` |
| `contradiction` (inconsistent frame) | yes | `contradiction` / `report_contradiction` → `CONTRADICTED` | `REPORT` | the **only** verdict that is a real contradiction; carries `blocking_reason="frame_inconsistent"` |
| `undetermined` | yes | `hard_boundary` / `refuse_known_boundary` → `UNDETERMINED` | `REFUSE` | within-frame refusal |
| `scope_boundary` | yes | `scope_boundary` / `refuse_known_boundary` → `SCOPE_BOUNDARY` | `EXPLAIN` | out-of-regime / unlicensed frame |

This resolves the two governance findings from review: `entailed_false` (a proven "No")
no longer collapses onto the `contradiction` triple (they were colliding on every typed
field of `LimitationAssessment`), and a proven negative is correctly typed as a *committed
answer* rather than a `CONTRADICTED` *block*. The closed `LimitationKind` set has no
"soundly-refuted" member **because `entailed_false` is not a limitation** — the open
question for ratification (§14) is only whether the grounded-negative answer is served as
`COMMIT`-with-negative-surface (recommended) or warrants a new closed-set member.

Binding rules:

- **Stays STRICT.** A closed-world verdict is *absolute* (proof-backed), not a statistical
  estimate — it never rides the `APPROXIMATE` rung. `govern_response` is called with **no**
  `license_decision`, returns `STRICT_POLICY`, and `shape_surface` is the byte-identical
  identity transform. Serving SHAs and `wrong=0` are unchanged.
- **Cannot self-certify `VERIFIED`.** `DisclosureClaim.VERIFIED` degrades to `COMMIT`
  unless `EpistemicState.VERIFIED` (no producer; `RESERVED` in `policy.py`).
- **Default-dark.** **[adv]** `choose_served_disposition` has **no caller on the default
  live serving path** — its one caller (`core/epistemic_disclosure/ask_serving.py` via
  `chat/ask_runtime.py::maybe_apply_served_ask`) is itself unwired into `chat/runtime.py`.
  The `FrameVerdict` disclosure path lands in the same posture: classify + decide a
  disposition, but do **not** flip the live `shape_surface` STRICT identity until a
  ratified producer + lane exist. Byte-identical serving is preserved.

Standing/persistence (if a lane ever persists a refuted hypothesis): through
`VaultStore.store` only, **SPECULATIVE by default** (INV-21/22/23) — a perceptual
falsification refutes a SPECULATIVE `HypothesisClaim` (ADR-0211), it never mints COHERENT.
The only path to `verified` standing remains the certificate-gated
`apply_certified_promotion` (INV-29). `FrameVerdict` writes no status itself.

---

## 8. INV-31 — the firewall (closed-world `False` cannot reach the open-world runtime)  **[adv — fully revised]**

The review showed a single-level, 3-file import scan is **insufficient**: "the open-world
path" is not a scannable unit (`chat/runtime.py` is one file holding the open-world,
realization, and governance-render code together); a single-level scan is defeated by one
transitive hop (the spine already imports into `generate.proof_chain`, the `FrameVerdict`
producer package); and the *actual* leak surface is the **shared reader + shared
disclosure gate**, a data-flow path no import scan touches. INV-31 is therefore a
**two-part** firewall, and it lands in **PR-1 together with the type** — never after.

**Guarantee.** A closed-world verdict (`FrameVerdict`, especially `entailed_false` /
`contradiction`) can never be *produced by*, *imported by*, or *rendered as an open-world
fact by* the open-world runtime spine.

### Part A — transitive import containment

- **A1.** `generate/determine/determine.py` neither imports nor constructs `FrameVerdict`;
  `determine()`'s return union stays `Determined | Undetermined`.
- **A2.** `FrameVerdict(…)` is constructed **only** inside an **exact** allowlist (no glob):
  `ALLOWED_FRAME_VERDICT_SITES = frozenset({"generate/frame_verdict/evaluate.py", …exact
  files…, "evals/proofwriter_cwa/adapter.py", …})`. The matcher must catch **every**
  constructor, not just the literal `FrameVerdict(…)` call: classmethod factories,
  `dataclasses.replace(v, verdict=…)`, and any helper returning `FrameVerdict` — mirroring
  INV-21's receiver-binding matcher, which exists precisely to defeat wrapper evasion. A
  drift-guard (à la `test_allowlist_is_actually_used`) flags a listed-but-unused site. The
  construction scan's file-walk **must include `evals/`** (unlike INV-30's
  `_enumerate_project_py_files`, which excludes it) or the eval-adapter entries are
  unenforced.
- **A3 (transitive).** `generate/frame_verdict` is unreachable from the **transitive
  first-party import closure** of every open-world spine entry module — computed with the
  existing `_transitive_first_party_imports` walker (INV-27's), **not** a single-level
  scan. The spine set is the *whole files* `chat/runtime.py`, `session/context.py`,
  `vault/store.py` (each barred entirely — there is no "open-world path" sub-unit). The
  package is placed so no spine closure touches it, and it is **forbidden to be re-exported
  through `generate/proof_chain`** (which the spine already imports). `frame_verdict` may
  import *from* `generate.proof_chain.entail` and the lifted `generate/epistemic_basis.py`;
  those one-way edges are sanctioned and the scan is **directional** (spine ↛ frame_verdict,
  not the reverse).

### Part B — typed data-flow firewall (the shared-reader / shared-gate leak)

Imports alone don't reach the leak surface the shared front-end creates, so:

- **B1.** `determine()`'s grounds input is type-tagged such that a `ClosedFrame`-derived
  grounds **cannot** be fed to the open-world `determine()` (a typed guard + a test that a
  closed-frame provenance into `determine()` raises).
- **B2.** `choose_served_disposition` / `govern_response` / `shape_surface` **refuse to
  render a `FrameVerdict` via an open-world disposition** unless an explicit closed-world
  disposition tag is present. The render integration lives **inside
  `core/epistemic_disclosure`**, never in `chat/runtime.py`; the spine ↛ frame_verdict
  containment (A3) plus this typed render gate means a closed-world `entailed_false` cannot
  reach the user surface as an open-world assertion.

### Non-vacuity — a meaningful-failure anchor for *each* scan

Mirroring INV-30's trio (30b non-vacuity, 30b′ no-false-positive, 30c sites-visible) and
INV-29's parallel trio, every scan gets an anchor so a blind/mis-rooted scan fails loudly:

| Test | Fails when |
|---|---|
| `test_inv31_determine_is_visible_and_clean` (anchors A1) | the scan does **not** see `determine.py`'s real 3 `Determined` sites, or sees a `FrameVerdict` ref there |
| `test_inv31_construction_allowlist` (anchors A2) | any `FrameVerdict`/factory/`replace` construction occurs outside the exact allowlist |
| `test_inv31_construction_detector_is_non_vacuous` | a fixture constructing `FrameVerdict` (and each alternate-constructor shape) in a forbidden location is **not** flagged |
| `test_inv31_spine_imports_resolve_and_exclude` (anchors A3) | a spine module's transitive import set is empty (mis-rooted/typo'd scan), **or** it does include `generate.frame_verdict` |
| `test_inv31_determine_rejects_closed_frame_grounds` (anchors B1) | a `ClosedFrame`-derived grounds fed to `determine()` does **not** raise |
| `test_inv31_open_disposition_rejects_frameverdict` (anchors B2) | the open-world disposition renders a `FrameVerdict` without the closed-world tag |

The non-vacuity claim is scoped per scan — "INV-31 is non-vacuous" holds only because
*each* of A1/A2/A3/B1/B2 has its own meaningful-failure anchor, not because one fixture
test covers the construction scan alone.

---

## 9. Measurement

- **`wrong_total == 0`, closed-world edition.** For a future ProofWriter-CWA lane,
  `wrong` is *"the closed-world gear asserted `entailed_false` where the independent CWA
  oracle does not entail ¬query (or `entailed_true` where it does not entail query)."*
  The analogue of the OWA breach; `wrong` must stay 0, non-vacuous because the oracle is
  independent (INV-25/27).
- **Independent gold, disjoint solver.** A CWA oracle is the closed-world analogue of
  `evals/proofwriter_owa/oracle.py::label`: same disjoint-oracle discipline (imports no
  `determine`/`comprehend`/`frame_verdict`), but it may soundly return `False` more often
  under the declared CWA. The oracle stays the scorer; it is never promoted into serving.
- **Capability-index registration.** Unlike the OWA *refusal floor* (deliberately **not** a
  capability domain — low coverage drags `coverage_geomean`), a two-sided CWA lane *commits*
  `entailed_true`/`entailed_false` and **is** a real capability domain. It registers through
  the existing hook: a `proofwriter_cwa_result() -> DomainResult` adapter appended to
  `evals/capability_index/adapters.py::ADAPTERS`; a lane that fails to run is recorded in
  `Collection.not_covered`, never faked.
- **Replay digest stable.** Every `FrameVerdict.trace_hash` is deterministic (`sha256_json`,
  order-invariant). The lane's report digest must be byte-stable — no clock, no LLM, no
  sampling.
- **The OWA floor (#779) stays green.** A CWA lane is a *separate* measure-only lane. B4
  adds no `False` path to `determine()`, so the OWA `wrong=0` / `coverage_gaps` gate is
  unaffected.

---

## 10. Implementation plan (gated; this PR is design-only)

| PR | Scope | Gate |
|---|---|---|
| **PR-0 (this)** | This ADR only. No code. | ratification of this document |
| **PR-1** | Lift `_basis` → `generate/epistemic_basis.py`; add `generate/frame_verdict/` (the `FrameVerdict`/`ClosedFrame`/`ClosedWorldProof` types incl. the `__post_init__` admissibility invariant + `evaluate_frame_verdict` for the **text** frame, delegating to `entail`) + serialization + **INV-31 Part A & B** with all six non-vacuity anchors. No serving wire. | PR-0 ratified |
| **PR-2** | `evals/proofwriter_cwa/` — independent CWA oracle + hand-authored CWA fixtures + scorer (`correct_false` / `wrong_false` columns) + `capability_index` adapter. Measure-only. | PR-1 merged |
| **PR-3** | `sensorium/environment/` → `FrameVerdict` adapter (the **conservative** §5.2 residual decomposition: only `changed`→`entailed_false`; missing/unexpected/whole-missing→undetermined/scope_boundary; frame-conformance query; full-run `trace_hash` proof). Perception-NAF stays deferred. | PR-1 merged |
| **PR-4** | `core/epistemic_disclosure` integration — map `FrameVerdict` → `ServedDisposition` per §7, incl. a grounded-**negative** renderer for `entailed_false`, **default-dark** (no live `shape_surface` flip). | PR-2/3 merged + a ratified producer |

Sequencing rule: **INV-31 ships with the type (PR-1), never after.** The firewall must
exist the moment a `FrameVerdict` can be constructed.

---

## 11. Non-negotiables honored

| Non-negotiable | How this design satisfies it |
|---|---|
| Do not modify `determine()` to emit `answer=False` | `determine.py` untouched; INV-31 A1 fails if it imports/constructs `FrameVerdict`; the new path is a distinct package/function |
| Do not relax INV-30 | INV-30 unchanged and green; `FrameVerdict` has no `answer` field and a distinct name (review ran the real predicate → `[]`), so the scan cannot match it |
| Do not treat absence as false | text `entailed_false` only from an ROBDD refutation; **perception `entailed_false` only from a `changed`-slot contradiction** — missing/unexpected/whole-missing → undetermined/scope_boundary; NAF deferred both frames |
| No closed-world verdict masquerades as open-world `Determined` | distinct type, distinct entry point, 5-way `verdict` enum (not a bool), **and the typed data-flow firewall** (INV-31 Part B) blocks the shared-reader / shared-gate leak |
| Closed-world `False` requires an explicit closed/bounded frame + proof basis | entry point takes a `ClosedFrame` (never `SessionContext`); `OPEN`/forged/implicit frames → `SCOPE_BOUNDARY`; every `entailed_false` carries a positive-refutation `ClosedWorldProof` (enforced by `__post_init__`) |
| `FrameVerdict` is a separate type/surface from `Determined` | yes — separate package, type, entry point, and (PR-4) grounded-negative renderer |
| `response_governance` stays the final servability gate | verdict commits nothing; surfaces only via `choose_served_disposition` → `govern_response` → `shape_surface`, STRICT, default-dark |

---

## 12. Proof obligations (per *Schema-Defined Proof Obligations*)

Each claim is real only if an executing test can meaningfully fail under the violation it
names. Obligations PR-1+ must discharge:

1. **INV-31 per-scan non-vacuity** — the six anchors in §8 (each of A1/A2/A3/B1/B2 has a
   meaningful-failure test; the construction detector is exercised against every alternate
   constructor shape).
2. **`entailed_false` is proof-backed (now non-vacuous)** — the §3 `__post_init__` raises
   on `verdict==ENTAILED_FALSE` with a non-`{REFUTED,FALSIFIED}` proof; a test constructs
   that mismatch and asserts the raise.
3. **`contradiction ≠ entailed_false`** — inconsistent premises → `contradiction`, never
   `entailed_false`; and (§7) the two carry distinct `LimitationKind` so they stay
   distinguishable at the disclosure layer, not only upstream.
4. **Absence never yields `entailed_false`** — text: an `UNKNOWN` query → `undetermined`;
   perception: a **missing-only** residual and a whole-frame-missing run → `undetermined` /
   `scope_boundary`, asserted explicitly (the blocker the review caught).
5. **Replay determinism** — identical `trace_hash` across two runs and under input
   reordering; perception proof binds the full `FalsificationRun.trace_hash`.
6. **CWA `wrong=0` is non-vacuous** — the lane's scorer, against the independent oracle,
   fails if any `entailed_false` is asserted where the oracle does not entail ¬query.

---

## 13. Consequences

**Positive.** A single sound, replayable, frame-general closed-world verdict; text-CWA
and perception converge on one envelope before either is built, so neither invents an
incompatible "False" shape; the open-world runtime is firewalled by both import
containment *and* a typed data-flow guard; no new solver, no relaxed invariant, no serving
regression.

**Costs / risks.**
- **NAF deferral (both frames)** means v1 text-CWA asserts `False` only where the frame
  *declares* the refuting facts, and v1 perception asserts `False` only on a `changed`-slot
  contradiction. ProofWriter-CWA fixtures must include their closure facts — which matches
  how ProofWriter-CWA is presented. Acceptable; NAF is the riskier hinge and is correctly
  deferred.
- **Perception is binary-native and conservative.** It inhabits a subset of the verdict
  alphabet in v1; under-determined queries → `scope_boundary`. This is the honest cost of
  not laundering set-inequality into entailment.
- **Grounded-negative renderer is new (PR-4).** `entailed_false` is a committed "No" with
  no existing renderer; the open question (§14) is `COMMIT`-with-negative-surface vs a new
  closed-set member.
- **`_basis` lift** (PR-1) is a small, mechanical refactor that removes the open/closed
  package coupling the review flagged; INV-31's directional scan depends on it.
- **INV-31 import scans** must use the project-wide source walk with the maintained
  `.claude`/worktree exclusions (CLAUDE.md *Architectural Scan Exclusions*), and the
  construction scan must *include* `evals/`.

**Alternatives considered & rejected.**
- *Widen `determine()`/`Determined` with `answer=False`* — rejected: mechanically breaks
  INV-30 and contaminates the open-world session-memory path.
- *Map bare `FalsificationRun.verdict` (SUPPORTED/FALSIFIED) onto `entailed_true`/`entailed_false`*
  — rejected (review blocker): `FALSIFIED` fires on absence (`missing`, whole-frame-missing)
  and over-observation (`unexpected`); `SUPPORTED` is mere set-match, not a proof of any
  query. Only `changed` is a positively-observed contradiction.
- *Route `entailed_false` through `LimitationKind=contradiction`* — rejected (review):
  collapses a proven "No" with an inconsistent frame and mis-types a grounded answer as a
  block.
- *A single-level 3-file import scan as the firewall* — rejected (review): defeated by one
  transitive hop and blind to the shared-reader/disclosure leak.
- *Negation-as-failure in v1 (either frame)* — deferred (§5.3), not adopted, for soundness.

---

## 14. Ratification checklist (to be completed by architect)

- [ ] The `FrameVerdict` axes (§3) are the right closed set — `frame_kind`,
      `world_assumption`, the 5-way `verdict` (`undetermined`, aligning with the merged
      brief and `EpistemicState.UNDETERMINED`), `basis/proof/evidence`, `trace_hash`.
- [ ] No `answer` field / distinct name is accepted as the INV-30-safe shape, and the
      `__post_init__` admissibility invariant is accepted.
- [ ] The §5.1 text table and the **revised §5.2 perception decomposition** (only
      `changed`→`entailed_false`; missing/unexpected/whole-missing → undetermined/scope_boundary;
      frame-conformance query) are correct.
- [ ] NAF deferral on **both** frames (§5.3) is accepted for v1.
- [ ] **INV-31's two-part shape** (§8 — transitive import containment + typed data-flow
      firewall) with all six non-vacuity anchors is accepted, shipping in PR-1.
- [ ] The `_basis` lift to `generate/epistemic_basis.py` (PR-1) is authorized.
- [ ] The §7 governance mapping — `entailed_false` as a committed "No" (not a `contradiction`
      block), STRICT, default-dark, no `VERIFIED` self-cert — is correct. **Open question:**
      grounded-negative answer as `COMMIT`-with-negative-surface (recommended) vs a new
      closed-set `LimitationKind`/`EpistemicState` member.
- [ ] The `entailed_true` produced-`EpistemicState` reconcile (do not stamp `EVIDENCED`)
      is accepted as a PR-4 obligation.
- [ ] The PR sequence (§10) and the "INV-31 ships with the type" rule are authorized.
- [ ] The new invariant number **INV-31** is free / correctly assigned (review confirmed
      no existing `INV-31` reference).
