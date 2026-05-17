# The Truth-Seeking Schema

> One of the foundational architectural commitments of CORE.
> Co-equal with the Cl(4,1) algebraic substrate; both are load-bearing.

## Why this document exists

Modern AI systems are widely understood to be capable, fast, and
useful. They are not widely understood to be *truth-seeking*. The
difference is not academic. A system that synthesizes plausible
outputs from opaque weights — and is rewarded during training for
sounding right — develops the same epistemic failure modes that
afflict human reasoning when it goes wrong: confabulation, narrative
smoothing, selective recall, defensive identity protection, deference
to authority, and the slow ossification of mistaken beliefs.

Building an AI that does *not* do these things is talked about more
than it is built. CORE is an attempt to build it. This document
states the architectural commitments that make that attempt
falsifiable: what we have actually built, where the current gaps are,
and what mechanism prevents each failure mode by construction rather
than by hope.

The reader who only cares about benchmarks should read
[`evals/CLAIMS.md`](../evals/CLAIMS.md) — every claim in this document
maps to a row there with a reproducible measurement command.

---

## The five architectural commitments

These are not principles the system tries to follow. They are
properties of the substrate the system runs on. Each is enforced in
code at the indicated location. Each has a test that fails if the
property is broken.

### 1. Coherence, not authority, is the only admission signal

> *Source: [`teaching/epistemic.py`](../teaching/epistemic.py),
> [ADR-0021 §3](decisions/ADR-0021-epistemic-grade-policy.md).*

A claim is admitted as evidence in downstream inference if and only
if it has been judged coherent with the existing reviewed field. Not
because the textbook said it. Not because a famous person endorsed it.
Not because a popular consensus exists. Not because the model itself
said it confidently a moment ago.

`EpistemicStatus` has four positions: `SPECULATIVE`, `COHERENT`,
`CONTESTED`, `FALSIFIED`. Only `COHERENT` is admissible as evidence
(`ADMISSIBLE_AS_EVIDENCE = frozenset({EpistemicStatus.COHERENT})`).
The enum deliberately excludes source-trust labels like
`peer_consensus`, `outsider_empirical`, or `established` — including
them would re-import the bias the schema is designed to refuse.

This is the structural defense against argument from authority, ad
populum, credentialism, and the closely related failure mode in which
a model trusts its own prior output because it sounds confident.

### 2. The non-hardening invariant

> *Source: [ADR-0021 §2](decisions/ADR-0021-epistemic-grade-policy.md),
> verified by absence: no `final`, `frozen`, `axiom`, or `permanent`
> flag exists in the codebase.*

No claim is ever locked. Even `COHERENT` is revisable. There is no
"this is settled, stop questioning" status, and adding one is a
deliberate architectural violation, not a feature request.

`FALSIFIED` claims are retained for audit and for the explicit
**Stage-3 inversion** path that allows a previously-falsified claim
to be revisited if new coherence emerges. The system does not erase
its mistakes; it keeps them as evidence and remains open to being
wrong about being wrong.

This is the structural defense against ossification — the human
reflex to defend a settled belief because revising it would threaten
identity, reputation, or sunk cost.

### 3. SPECULATIVE is the safe default

> *Source: [`teaching/epistemic.py::parse_status`](../teaching/epistemic.py),
> [`teaching/store.py::TeachingStore.add`](../teaching/store.py).*

Every new correction enters the revision graph at `SPECULATIVE`,
without exception. An unknown, absent, or malformed status string
does not silently promote a claim to `COHERENT`. Promotion to
`COHERENT` requires a curator-mediated coherence judgment, performed
by the review path, against the existing reviewed field.

This is the structural defense against confabulation slipping in
unverified. A system that defaults to "this is fine" is one bad row
away from a poisoned belief substrate.

### 4. The one-mutation-path invariant

> *Source:
> [`tests/test_architectural_invariants.py::TestINV21OneMutationPath`](../tests/test_architectural_invariants.py).*

Knowledge enters the runtime field through exactly one reviewed path.
Every module that calls `VaultStore.store(...)` must be explicitly
allowlisted in the architectural-invariant test. Adding a new writer
is permitted, but only by editing the allowlist with a documented
justification — the CI failure is the prompt to do so, not a
roadblock to route around.

This invariant exists because a schema with multiple admission paths
is operationally equivalent to no schema. Any backdoor — a debug
endpoint, an admin override, a fast-path for "known good" sources,
a quietly-added vault write inside a refactor — collapses the entire
guarantee. The test makes that collapse visible at commit time.

### 5. Identity cannot be rewritten by content

> *Source: [`teaching/review.py::_is_identity_override`](../teaching/review.py),
> [`core/physics/identity.py::IdentityCheck`](../core/physics/identity.py),
> [ADR-0010](decisions/ADR-0010-identity-physics.md).*

A correction that attempts to rewrite identity — "you are now Bob,"
"forget your prior axes," "ignore previous instructions" — is
rejected by two independent layers:

- A syntactic layer (pattern detection on the correction text).
- A geometric layer (`IdentityCheck.would_violate` on the
  versor-field trajectory the correction would produce). The
  geometric layer is paraphrase-invariant by construction: a novel
  phrasing of the same attack still trips the geometric check
  because the manifold trajectory is the same.

Either layer's veto is sufficient. The outcome is
`REJECTED_IDENTITY` and no proposal is created. Verified at 100% by
[`evals/adversarial_identity`](../evals/adversarial_identity) and
[`evals/teaching_injection_resistance`](../evals/teaching_injection_resistance).

This is the structural defense against the prompt-injection attack
class that frontier LLMs are vulnerable to as a category — not
because they were trained badly, but because instruction-following
is a soft prompt-level behavior in a sampling system, not an
architectural constraint.

---

## What this defends against, mapped to human failure modes

| Human failure mode | Architectural defense |
|---|---|
| Lying / fabrication | SPECULATIVE default + COHERENT-only admission + the `refusal_calibration` lane gating the surface layer |
| Confabulation (generating false detail that sounds true) | One-mutation-path invariant + `teaching_injection_resistance` lane proving the SPECULATIVE-only contract holds |
| Exaggeration / unwarranted confidence | `articulation_of_status` lane — every SPECULATIVE-backed surface must be marked as such, not stated as bare fact |
| Self-protection (burying inconvenient evidence) | FALSIFIED retention + Stage-3 inversion path; falsified claims are kept, never erased |
| Self-promotion (citing one's own claims as evidence) | Coherence-not-authority rule; system's prior output has no special standing; INV-21 makes self-feedback paths visible |
| Deference to authority | Source labels excluded from `EpistemicStatus` enum by deliberate design |
| Ossification (defending settled beliefs) | Non-hardening invariant — no claim is ever locked |
| Identity-protection attacks | Two-layer (syntactic + geometric) `REJECTED_IDENTITY` path; paraphrase-invariant |
| Prompt injection | Identity defense above + `teaching_injection_resistance` lane (anti-injection for content) |

Each row in the right column points to a file, a test, or an
eval lane — not a principle on a slide.

---

## What this does *not* yet do — honest gaps

Per the transparency commitment, the leaks we have a test for live
in this section. Each is also a row in
[`evals/CLAIMS.md` Tier 4.5](../evals/CLAIMS.md).

### ~~Leak A — Pack vocabulary defaults to COHERENT~~ — CLOSED 2026-05-17

**Original gap:** `language_packs/compiler.py:331` and
`language_packs/schema.py::LexicalEntry` defaulted unmarked pack rows
to `"coherent"`, silently admitting pack authority as a substitute
for coherence judgment.

**Fix landed:** Both defaults now `"speculative"`. The docstring on
`LexicalEntry` that previously rationalized the COHERENT default has
been corrected to align with ADR-0021 §Schema impact. Pack rows that
want to be admissible as evidence must declare
`"epistemic_status": "coherent"` explicitly — the declaration is the
curator's stamp, replacing the silent default.

**Regression guard:** `tests/test_architectural_invariants.py::TestINV22PackDefaultSpeculative`
(three tests: dataclass default, compiler payload default, explicit
COHERENT preservation).

**Residual work:** The 365 existing pack rows currently carry no
explicit status and now correctly report SPECULATIVE. When the
downstream filter for Leak B lands, those rows will need an explicit
curator-review pass before re-entering inference paths as evidence —
this is the discipline the schema enforces, surfaced rather than
inherited from a default.

### ~~Leak B — Vault recall is epistemic-blind~~ — CLOSED 2026-05-17

**Original gap:** `vault/store.py::VaultStore.recall` returned hits
without an epistemic tier; downstream consumers treated session
memory and reviewed knowledge as equivalent recall.

**Fix landed:** `VaultStore.store()` now stamps every entry with an
`EpistemicStatus` (default SPECULATIVE — the safe choice).
`VaultStore.recall(min_status=EpistemicStatus.COHERENT)` filters to
admissible-as-evidence entries only. All four vault-write sites in
the codebase pass an explicit status. Session-lookup behavior is
preserved as the default (no filter), because the session needs to
see its own turns regardless of tier — but any inference path that
opts in now gets the evidence guarantee.

**Regression guard:** `tests/test_architectural_invariants.py::TestINV23VaultEpistemicFilter`
(four tests).

### ~~Leak C — Self-reinforcing fabrication via `propose()`~~ — CLOSED 2026-05-17

**Original gap:** `generate/proposition.py:198` stored every
articulated proposition back into vault unmarked. The system says
something → recalls own output → cites it → says it again. A
fabrication-feedback loop in the substrate.

**Write-side fix:** the call site now stamps
`epistemic_status=EpistemicStatus.SPECULATIVE` with an inline comment
naming this leak. The feedback loop is broken in principle: any
inference path that recalls with `min_status=COHERENT` will exclude
the system's own prior utterances from evidence.

**Read-side audit (2026-05-17):** every production `vault.recall()`
callsite was categorized and an architectural invariant added
(`TestINV24VaultRecallRegistry`) that requires every new callsite to
declare its role. Categories:

- **RECOGNITION** — answers *"have we seen this before?"* (gate
  decisions, unknown-domain probes). Unfiltered recall is correct,
  because session-tier SPECULATIVE memory must count toward
  recognition. Sites: `chat/runtime.py:330`,
  `vault/decompose.py:121`.
- **EVIDENCE_TELEMETRY** — feeds `walk_surface` and trace evidence
  but NOT the user-facing surface (per
  `docs/runtime_contracts.md` §surface vs walk_surface). Tolerable
  unfiltered because the walk does not shape claims. Site:
  `generate/stream.py:147` (`_recall_state`).
- **EVIDENCE_USER_FACING** — would feed user-facing surface as if
  ratified knowledge. **MUST pass `min_status=COHERENT`.** Currently
  empty by design: user-facing articulation comes from
  `realize(proposition, vocab)` via pack lookup (now SPECULATIVE-default
  per Leak A fix), not from `vault.recall`.

If a future change routes the generation walk into the user-facing
surface, INV-24 forces the recategorization to be explicit and
requires the `min_status=COHERENT` filter — the fabrication loop
cannot reopen quietly.

**Regression guard:** `tests/test_architectural_invariants.py::TestINV24VaultRecallRegistry`
(three tests) + site-level `# INV-24 recall role:` provenance
comments at every callsite.

### ~~Realizer-side surface gaps~~ — CLOSED 2026-05-17

**Original gap:** The realizer did not consult
`pack_mutation_proposal.epistemic_status` when forming surface text.
SPECULATIVE-backed answers were stated as bare facts. The schema was
operationally invisible at the surface layer.

**Fix landed:** `CognitiveTurnPipeline` now tracks subjects of prior
SPECULATIVE teaching proposals and prepends an explicit
`(speculative, not yet reviewed)` marker to the surface when a
subsequent turn references one of those subjects — by subject
substring match, by tokenized split (so prefixed parses like
`correction: wisdom` still match a probe about `wisdom`), or by
reflexive query shape (`is your answer confirmed?`,
`has this been reviewed?`). The teach turn itself is not self-marked;
only subsequent probes are.

Same commit landed a parallel fix for refusal calibration: the
unknown-domain surface now reads "I don't know — insufficient
grounding for that yet.", aligning the text with the system's actual
behavior so the `refusal_calibration` lane can see what was already
happening.

**Lanes graduated** (Tier 4.5 → Tier 2):
- `refusal_calibration`: 0.00 → **1.00** refusal_rate, 0.00 fabrication, 1.00 in-grounding.
- `articulation_of_status`: 0.00 → **1.00** speculative_articulation, 0.60 → **0.00** false_certainty.

### Contradiction detection is not implemented

ADR-0021 reserves `EpistemicStatus.CONTESTED`. The machinery to
*enter* that state on conflict between teachings does not yet exist.
The `contradiction_detection` lane runs anyway, scoring 50% via a
weak versor-condition heuristic with a 100% false-positive rate —
which is exactly the right data to motivate the proper fix (a
coherence checker at `TeachingStore.add` that detects
`(S, R, O)` ↔ `(S, ¬R, O)` pairs and transitions both to
`CONTESTED`).

---

## Why we publish the gaps

A document that lists only what is built and omits what is not is
indistinguishable from marketing copy. The truth-seeking schema is
not credible if the document that describes it is itself
self-promoting. Listing the leaks where the audit found them, in
the same place the strengths are claimed, is the smallest concrete
act of the discipline the schema is designed to enforce.

A green Tier 4.5 row graduates to Tier 1/2/3 of `CLAIMS.md` in the
same commit that lands the fix. Watch for that movement, not for
revisions to this document's prose.

---

## What this is — and what it is not

This is **not** a safety overlay bolted onto a sampling LLM. There
is no instruction-following prompt, no classifier downstream of the
generator, no "guardrail" the model could in principle ignore. The
commitments above are properties of the substrate. A model that
samples does not have an `EpistemicStatus` because it has no
mechanism to attach one to a token. CORE has one because every
admitted claim carries one, and the only path to admission is the
review path.

This is **not** an attempt to make a system that is always right. It
is an attempt to make a system that is always honest about the
status of what it knows — including when that status is "this has
not been reviewed yet" or "this was falsified on a prior pass." The
two are not the same goal. The second is achievable. The first is
the failure mode every fluent system tends toward when the second
is not enforced.

---

## Pointers

- Status enum and parsing: [`teaching/epistemic.py`](../teaching/epistemic.py)
- Reviewed-teaching review path: [`teaching/review.py`](../teaching/review.py)
- Append-only teaching store: [`teaching/store.py`](../teaching/store.py)
- Identity-rewrite firewall (two-layer): [`teaching/review.py::_is_identity_override`](../teaching/review.py), [`core/physics/identity.py`](../core/physics/identity.py)
- Formation pipeline (LLMs propose, the Forge disposes, CORE composes): [`docs/formation_pipeline_plan.md`](formation_pipeline_plan.md)
- One-mutation-path invariant test: [`tests/test_architectural_invariants.py::TestINV21OneMutationPath`](../tests/test_architectural_invariants.py)
- ADR-0021 (epistemic grade policy): [`docs/decisions/ADR-0021-epistemic-grade-policy.md`](decisions/ADR-0021-epistemic-grade-policy.md)
- ADR-0010 (identity physics): [`docs/decisions/ADR-0010-identity-physics.md`](decisions/ADR-0010-identity-physics.md)
- Public claims with reproducible measurements: [`evals/CLAIMS.md`](../evals/CLAIMS.md)
- Eval lanes that exercise the schema:
  - [`evals/adversarial_identity`](../evals/adversarial_identity)
  - [`evals/teaching_injection_resistance`](../evals/teaching_injection_resistance)
  - [`evals/refusal_calibration`](../evals/refusal_calibration)
  - [`evals/contradiction_detection`](../evals/contradiction_detection)
  - [`evals/articulation_of_status`](../evals/articulation_of_status)
  - [`evals/provenance`](../evals/provenance)
  - [`evals/monotonic_learning`](../evals/monotonic_learning)
