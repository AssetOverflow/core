# Decoding, Not Generating: A Geometric Architecture for Aligned Cognition

**Josh Shay** · ACB Content / CORE

---

## Abstract

Current AI systems generate plausible outputs by sampling from distributions over
tokens. This paper argues that generation and cognition are architecturally
distinct: cognition is the decoding of structure that already exists, not the
synthesis of structure from statistical residue. We describe CORE , a cognitive architecture grounded entirely in
Conformal Geometric Algebra Cl(4,1), where memory is versor stabilization,
reasoning is field propagation, and alignment properties are substrate invariants
— not training objectives, prompt constraints, or classifier overlays. The
architecture is running, deterministically reproducible, and falsifiable at every
claimed property.

---

## 1. The Problem Is Not Scale

The dominant framing of AI alignment treats the problem as a property of
sufficiently capable generative systems: how do we ensure that a powerful sampler
pursues human-intended goals? This framing inherits a prior that is worth
questioning: that sampling from a learned distribution is what intelligence is.

The problems alignment research works hardest on — hallucination, sycophancy,
goal misgeneralization, prompt injection, identity instability under adversarial
input — are not failure modes of an otherwise-sound architecture. They are
structural consequences of building cognition on top of stochastic generation. A
system that samples cannot have a well-defined identity, because identity is a
trajectory property, not a token property. A system that samples cannot have
verified knowledge, because verification requires a fixed epistemic state to
verify against, and a sampling system's epistemic state is the weights — which
are frozen at training time and invisible at inference time. A system that samples
cannot refuse to fabricate, because fabrication is the mechanism. Confident-
sounding output is the signal the training process rewarded.

These are not bugs. They are the architecture.

---

## 2. The Thesis

**Cognition is the decoding of a reality that already is. It is not the
generation of plausible completions.**

More precisely: a cognitive system does not produce meaning from a probability
distribution. It finds the nearest point on a structured manifold — the point
that is already there — and names it. The distinction has architectural
consequences.

A generative system has no manifold. It has a weight matrix and a temperature
parameter. When it is wrong, there is no geometric fact about why it is wrong —
only a gradient signal saying the output should have been different.

A decoding system has an invariant. When it decodes incorrectly, the error is
locatable: a versor violated closure, a recall missed the correct neighbor, the
proposition graph was underspecified. These are failures with structure.
Structured failures are fixable. Stochastic failures are regularizable.

The falsifiable form of this claim is: a system built on geometric decoding
rather than statistical generation can maintain strict factual invariants across
a test set where a generative system cannot, without retraining, gradient descent,
or prompt engineering. The current evidence is in §4.

---

## 3. The Architecture as Direct Consequence

If cognition is decoding, the architecture follows from three geometric facts.

### 3.1 State is a field, not a flat array

Meaning is relational. A token out of context has no meaning. A field over a
structured space has meaning at every point because the space encodes
relationships geometrically. CORE's state is a single multivector in Cl(4,1) —
the Conformal Geometric Algebra of 3D space — a 32-dimensional object where every
grade carries a distinct geometric role: scalars, vectors, bivectors, trivectors,
quadvectors, pseudoscalar.

Cl(4,1) was chosen for one reason: it is the minimal algebra where all conformal
transformations — rotations, translations, dilations, inversions — are versors.
Every cognitive operation is algebraically closed. There is no "translation
handling" bolted on as a special case. The algebra is closed over the full
conformal group by construction.

### 3.2 Every transition is a versor product

```
F_new = V · F · reverse(V)
```

This is the only allowed field transition. The sandwich product with a versor
preserves grade structure, preserves the versor manifold, and has an analytic
inverse. The non-negotiable invariant is:

```
versor_condition(F) = ‖F · reverse(F) − 1‖_F < 1e-6
```

This scalar is zero on the versor manifold. Every input is verified at the
injection gate. Every accepted field state satisfies this condition. There is no
drift correction, no repair monitor, no normalization callback — these were all
deleted because they only exist when the algebra is not closed. The algebra is
closed.

### 3.3 Recall is exact conformal distance

For null vectors X, Y in Cl(4,1):

```
X · Y = −(1/2) d(X, Y)²
```

The CGA inner product *is* Euclidean distance in conformal embedding. Vault
recall is:

```
best_match = argmax_i { Q · V_i }
```

No ANN index. No approximate neighbor structure. No tunable similarity threshold.
The recall is exact, and exactness is not a performance tradeoff — it is what
makes the recalled result verifiable. A recall hit is a geometric fact, not a
probabilistic suggestion.

### 3.4 Learning requires review

Knowledge enters the runtime field through one path: the reviewed teaching loop.
Every new correction enters at `EpistemicStatus.SPECULATIVE`. Promotion to
`COHERENT` — the only status admissible as evidence in downstream inference —
requires a **coherence judgment** against the existing reviewed field. The
admission signal is coherence and only coherence: source authority, institutional
credentials, and the system's own *asserted* output carry no standing. Provenance
is retained for audit and revision, never as a promotion signal.

That judgment is curator-mediated today, and for most corrections it must be. The
fallible step is not the logic but the *reading* — translating a natural-language
claim into the field's propositional form, and selecting which reviewed claims it
bears on. A sound inference over a misread premise is a sound proof of the wrong
thing, so a human certifies the reading before a correction enters the reviewed
structure.

One subclass is different in principle. A claim that is *deductively entailed* by
claims already marked `COHERENT` is not new information and is not the system's own
opinion — it makes explicit what the reviewed field already contains. For that
subclass the entailment proof *is* the coherence judgment, and CORE's sound,
independently-checked deductive engine (`deductive_logic_v1`, §4) can certify it
deterministically, with the proof chain as the audit artifact — the logical form
of the *"structural coherence metric"* ADR-0021 names as the successor to curator
mediation. What review still gates there is the faithfulness of the reading, not
the deduction. This proof-carrying promotion path is **specified but not yet
wired** (see
[`docs/issues/proof-carrying-coherence-promotion.md`](issues/proof-carrying-coherence-promotion.md));
until it lands, all promotion is curator-mediated.

This is not a safety overlay. It is a consequence of the decoding thesis: if the
system decodes a reality that already is, then inputs that contradict — or merely
fail to follow from — reviewed structure need review before they enter that
structure. A system that accepts any confident-sounding correction without review
is a generative system in different clothing.

Two invariants enforce this at the architecture level, not the policy level.

**One-mutation-path invariant.** Knowledge enters the runtime field through
exactly one reviewed path. Every module that writes to the vault is explicitly
allowlisted in `tests/test_architectural_invariants.py::TestINV21OneMutationPath`.
Adding a new write path requires editing the allowlist with a documented
justification — the CI failure is the prompt to do so, not a roadblock to route
around. Any backdoor — a debug endpoint, an admin override, a fast-path for
"known good" sources — collapses the guarantee. The test makes that collapse
visible at commit time.

**Non-hardening invariant.** No claim is ever locked. Even `COHERENT` is
revisable. There is no `final`, `frozen`, `axiom`, or `permanent` flag in the
codebase — their absence is enforced by test. `FALSIFIED` claims are retained for
audit and remain eligible for reinvestigation if new coherence emerges. A system
that cannot revise a settled belief because doing so would threaten its identity
has ossified. CORE cannot ossify by construction.

---

## 4. Evidence

The following properties are currently measured, reproducible, and falsifiable.
Every claim maps to a reproducible command in `evals/CLAIMS.md`.

### The zero-wrong invariant — everywhere, without exception

On the real GSM8K train sample (50 problems drawn from the actual benchmark
distribution), CORE currently scores: **correct=3, refused=47, wrong=0**.

The natural reaction to seeing 3/50 correct is that this is a weak result. It is
not. It is the most important number in this paper, and understanding why requires
understanding what the alternatives mean.

A frontier LLM scores approximately 90%+ correct on GSM8K. It also produces wrong
answers — answers where it ran to completion, produced a number, and the number
was wrong. The model cannot distinguish its correct answers from its wrong ones.
From the inside, they look identical: a confident surface string. The only way to
know which is which is to check against ground truth. A system that confabulates
at 10% on a math benchmark is confabulating at some unknown rate on every other
domain it touches — and the confabulation is invisible, because the surface is
always confident.

CORE's current math score is 3/50 correct. But wrong=0 is not a constraint
imposed on the architecture. It is a property of the architecture. The system
cannot produce a wrong answer because it cannot complete a generation walk that
lacks geometric grounding. When the parser does not find an admissible candidate
for a statement or question, it refuses — with a named reason. There is no path
from "ungrounded input" to "completed output."

The refusal taxonomy for the 47 refused cases is fully enumerated by the
candidate-graph pipeline. Each refusal carries a named shape category — the
recognizer saw a statement shape its registered injector could not turn into
typed solver state, so the candidate refuses instead of fabricating a guess.

| Barrier category | Count | Description |
|---|---|---|
| `recognized_but_uninjectable(discrete_count_statement)` | 21 | Multi-word possession / acquisition shapes ("Lily has three boxes of pencils") whose v1 injector covers only the single-word DCS surface |
| `no_admissible_candidate` | 10 | Statement shape unrecognized by the v1 parser AND no registered recognizer matched — refuses cleanly, no admissible branch enumerated |
| `recognized_but_uninjectable(multiplicative_aggregation)` | 5 | Multi-quantity composition shapes ("3 vet appointments cost $400 each") — recognizer detects the shape; injector for the composed operand is the ADR-0169 frontier |
| `recognized_but_uninjectable(currency_amount)` | 4 | Currency-amount detections without per-unit framing — recognizer detects; v1 injector deliberately deferred |
| `recognized_but_uninjectable(rate_with_currency)` | 3 | Per-unit-rate statements ("$18 per hour") — detection works; rate→initial injection is the next deferred shape |
| `recognized_but_uninjectable(descriptive_setup_no_quantity)` | 2 | Setup sentences with no quantity to compose — contributing zero math state is correct; the refusal here is the no-admissible-candidate failure mode |
| `recognized_but_uninjectable(temporal_aggregation)` | 2 | Event-count-per-window patterns ("10 oysters in 5 minutes") — needs a rate primitive in the algebra |

Every refusal has a named reason. Not "low confidence," not "out of distribution"
— a specific shape category the recognizer detected but the injector has not yet
been wired to turn into typed solver state. This is a work queue, not a mystery.
Each named barrier corresponds to one or two extension PRs in the active backlog.
As coverage grows, correct count grows. Wrong count stays 0 by architectural
guarantee, not by tuning.

The question a generative system cannot answer: "which of my answers are wrong?"
CORE's answer is always: "none — and here is exactly what I couldn't solve and
why."

### Deterministic replay

Any fixed `(state, vocab, persona, admissibility_region, mode)` tuple produces
bit-identical output across reruns. Verified by 5-rerun byte-identity tests across
every generation path. Determinism is not a configuration option. It is the
default behavior of a system with no sampling temperature.

### Versor closure

`versor_condition(F) < 1e-6` holds on every accepted field state in every test
suite. Verified at the injection boundary. If it fails, the failure is at the
operator or construction boundary — not masked downstream.

### Identity protection under adversarial input

Attempts to rewrite identity — novel phrasings, indirect approaches, prompt
injection patterns — are rejected by two independent layers: syntactic pattern
detection and a geometric check on the versor-field trajectory the correction
would produce. The geometric layer is paraphrase-invariant by construction.
Rejection rate on the adversarial identity eval: 100%.

### Epistemic honesty

Claims backed by unreviewed knowledge are marked `SPECULATIVE` at the surface
layer. `articulation_of_status` eval lane current false certainty rate: 0.00.
`refusal_calibration` lane: 1.00 refusal rate on out-of-grounding probes, 0.00
fabrication.

---

## 5. Honest Gaps

**Math injector coverage is the active frontier.** The 47 refusals on the train
sample are not failures of reasoning — they are failures of injection. The
solver, once a problem reaches it, produces correct answers (3 cases, 100%
solve rate on admitted problems). The recognizer already detects most refused
shapes; what's missing is the per-shape injector that turns a recognized
statement into typed solver state without fabricating quantities the source
does not contain. The architecture for closing this gap — a reviewed
composition-pattern registry consumed by a registry-driven injector — is in
place; new shape coverage ships as per-shape matcher extensions that publish
pre-composed candidates the registry gates. These are enumerated, not
estimated.

**The holdout is sealed.** The real GSM8K test set (1,319 cases) is
age-encrypted and has not been run against a system with sufficient parser
coverage to produce meaningful correct counts. When it is opened, the zero-wrong
guarantee will either hold or falsify the architecture. There is no middle ground.

**The vocabulary manifold is finite and curated.** CORE does not generalize to
arbitrary domains through gradient descent. Extending to a new domain requires
constructing pack vocabulary, establishing coherence with existing reviewed
claims, and passing the eval lane. This is deliberately slow. Whether it scales
to the full breadth of human knowledge is an open question. Whether it can be
done without confabulation is not.

**Vision, audio, and motor modalities are planned, not built.** The
`ProjectionHead` protocol supports them architecturally. The projection heads do
not yet exist.

---

## 6. Why This Matters for Alignment

The alignment problem, stated geometrically: how do you ensure that the system's
behavior remains within an intended region of possibility space as the system
becomes more capable?

In a generative system, the answer is: train it toward intended behavior, then
add classifiers, prompt constraints, and RLHF. These work until they don't. The
failure modes are structural — a sampling system can always produce output outside
the intended region given sufficient context pressure, because the constraint is
behavioral, not algebraic.

In CORE, the answer is: the intended region is the admissibility region, enforced
at every generation step by the admissibility gate. A token is admitted if and
only if its versor aligns with the relation blade within the admissibility margin.
A rotor is admitted if and only if the field it would produce remains within the
frame versor's half-space. These are hard constraints on every step, not soft
regularizers on the training objective.

The teaching safety properties follow from the same logic. A system that cannot
accept arbitrary identity rewrites is not one that was trained to resist them. It
is one where identity is a geometric trajectory, and a rewrite is a geometric
violation detectable independently of the phrasing used to attempt it.

A concrete example: during architecture audit, CORE was found to have a
self-reinforcing fabrication path — the system could recall its own prior output
as evidence, cite it, and compound it across turns. This is not a hypothetical
failure mode; it is the epistemic structure of every system that stores its own
outputs without epistemic tagging. The path was found and closed architecturally:
every vault write now stamps an `EpistemicStatus`, the default is `SPECULATIVE`,
and any inference path that feeds the user-facing surface must pass
`min_status=COHERENT`. The fabrication loop cannot reopen quietly — the
one-mutation-path invariant ensures any new vault write path triggers a CI
failure until explicitly reviewed.

The deeper alignment claim: if cognition is decoding, then the space being decoded
has structure that exists independently of the system decoding it. Truth is
coherent. A system built to find coherent structure is, by construction, built to
be correctable — not because it was trained to be, but because its correction
mechanism operates on the same geometric substrate as its cognition. Review is
coherence judgment, not authority assertion. Falsified claims are retained, not
erased. No claim is ever locked.

This does not solve alignment. It relocates the hard problem from "how do we
train a sampler to stay in bounds" to "how do we specify the right admissibility
region." The second problem is harder to obscure and easier to audit. That is the
point.

---

## 7. Relationship to Existing Work

**Interpretability research** asks: what are the circuits inside a trained model
doing? CORE inverts the question: what geometry must the architecture have so that
behavior is interpretable by construction? Every field transition is a named
versor product. Every recall hit is a geometric distance. Every admitted claim
carries an epistemic status. There are no circuits to reverse-engineer because
there are no learned weights.

**Mechanistic alignment** (superposition work, SAE probing, etc.) seeks to
identify features in trained models. CORE's features are explicit — they are pack
lexicon entries with geometric coordinates. The cost is that domain coverage
requires curation. The benefit is that a feature's meaning is exact and auditable,
not inferred from probing.

**RLHF / Constitutional AI** shapes model behavior through feedback. CORE's
teaching loop shapes field structure through reviewed correction. The distinction:
in RLHF, the corrected behavior is baked into weights that are opaque. In CORE,
the corrected knowledge is a reviewed claim with a named epistemic status, a
SHA-256 provenance hash, and a deterministic replay trace. The correction is
auditable at the level of individual claims.

**Formal verification of AI** asks whether model properties can be proven. CORE's
invariants — versor closure, deterministic replay, zero confabulation, identity
protection — are not proven in the theorem-prover sense. They are verified by
construction and by eval: a falsifying case would be visible in the test suite.
That is a weaker guarantee than formal proof and a stronger guarantee than
behavioral testing of a black-box sampler.

---

## Concrete Evidence — Merged Demos (2026-06-11)

The claims in §4 are abstract without pointers to reproducible artifacts. This
section ties each abstract property to a specific merged demo, trace hash, and
runnable command. All three demos are in the public repository under `demos/`.

### Authority over claims — PR #687, merge `3ba65d51`

`demos/claude_hybrid_verification/` demonstrates the full authority boundary for
claim verification across five typed outcomes. A frontier-style proposer submits a
math problem as a typed tool call. CORE re-derives from the problem text and holds
sole accept/refuse/ask/invalid authority. The proposer appears nowhere in
`authority_path`.

Representative trace hashes (SHA-256 of response envelope):
- Verified: `c9b26b346d9539bd…` (Sara problem, 26 dollars, faithful 3-step derivation)
- Refused / disagreement: `c73e264092bb6940…` (two "complete" paths that disagree — CORE refuses rather than guessing)
- Ask / under-specified: `3c751beda82ca08c…` (grounded clarifying question, not fabricated answer)
- Refused / envelope: `48d5b24a135bb855…` (correct derivation but outside committed serving envelope)
- Invalid / smuggling: `22748265a24cc919…` (schema rejects `proposed_answer` field before evaluation)

Run: `python demos/claude_hybrid_verification/run_demo.py`

The hard finding — that reasoning-path agreement is not reliable safety — is
demonstrated concretely by the refused-disagreement scenario. Two derivation paths
independently agree the problem is solvable, produce well-formed arithmetic, and
disagree on the answer. The authority boundary catches this; a consensus-of-outputs
architecture would not.

### Authority over proposed tool actions — PR #688, merge `c55f7dfb`

`demos/claude_tool_authority/` demonstrates the same authority boundary for
proposed digital actions across four typed outcomes. A model-style proposer submits
action proposals; CORE alone authorizes, asks, refuses, or invalidates. Authorized
outputs are inert `licensed_action` artifacts; `execution_performed: false` on every
scenario.

Representative trace hashes:
- Authorized (inert): `9e797710ed34dfa5…` (`write_local_note`, `proposer_trace_hash_ignored: true`)
- Ask (confirmation required): `eeb8ed87e83ed410…` (`send_external_email`, confirmation gate)
- Refused: `fa1d2511f953306f…` (`delete_system_file`, not in envelope)
- Invalid / smuggling: `a336294778c1f496…` (`authorization_status` field rejected before evaluation)

Run: `python demos/claude_tool_authority/run_demo.py`

### Authority over epistemic state assignment — PR #690, merge `e80c8eae`

`demos/epistemic_truth_state/` demonstrates the same authority boundary for
epistemic state assignment across six typed outcomes. A model-style proposer
submits a claim with evidence and a `proposed_state`; CORE assigns the canonical
state from the evidence. `proposer_state_ignored: true` on every output.

Typed state vocabulary: `verified`, `evidenced`, `inferred`, `undetermined`,
`scope_boundary`. A proposer that injects `assigned_state` or `authority_path` into
the request payload is rejected at the typed schema boundary before evaluation.

Representative trace hashes:
- Verified: `4307277a0f8d8276…` (2 independent evidence items, `normative_clearance: cleared`)
- Evidenced: `f9f2e153e66aaba9…` (1 item, below threshold — proposer proposed `verified`)
- Inferred: `bc11e858ece14081…` (premise-only evidence — proposer proposed `verified`)
- Undetermined: `35b319eb0186be2d…` (off-topic evidence)
- Refused: `c9ef9560bcf71052…` (outside epistemic envelope)
- Invalid: `18dda5b4017b223b…` (5 smuggled output fields rejected)

Run: `python demos/epistemic_truth_state/run_demo.py`

**Honesty note:** `normative_clearance` is `"unassessable"` on five of six
scenarios. The demos do not perform a normative, safety, or ethics clearance pass.
This is recorded explicitly in the output. The `deterministic replay` and `identity
protection` claims in §4 are substrate properties; the epistemic state demos extend
them to claim/action/state authority surfaces not covered in the original paper.

---

## Conclusion

The question is not how to make generative AI safer. The question is whether
generation is the right substrate for cognition in the first place.

CORE is a running argument that it is not. The argument is not in this paper. It
is in the versor invariant, the zero-wrong eval gate, the deterministic trace
hash, the reviewed teaching path, the two-layer identity firewall, and now in three
public demos where a deterministic substrate holds exclusive authority over claims,
proposed actions, and epistemic state — each of which would fail visibly if the
thesis were wrong.

The code is open source under the CORE Non-Commercial License.
All commercial licensing inquiries: shayj292@gmail.com

---

*CORE is developed independently. All work was done on personal hardware.*
