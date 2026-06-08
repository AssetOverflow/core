# Q1 — Epistemic Question Articulation (v1) — companion scoping brief

**Date:** 2026-06-08 · **Status:** scoping (NO CODE) · **HOLD for review** ·
**Branch:** `docs/stage2-bus-and-q1-scoping`

**What this brief is.** A *companion* to the design-of-record — the session doc
`docs/sessions/2026-06-08-epistemic-question-articulation-first-skill-of-contemplation.md`
(535 lines), which already specifies the typed-question model, the minimal-sufficient
question, the pre-question limitation pass / intake gate (§1.5), and the organ shape
(`core/epistemic_questions/`). **This brief does not duplicate that.** It adds the five
things the session doc points at but does not pin down against shipped code, so that
when Q1 is built it lands on the real substrate without surprises:

1. the four ASK-relevant dispositions mapped onto the **shipped** failure-family
   registry, including the **reclassification finding** that `ask` exposes (§1);
2. the **grounded-rendering wrong=0 invariant** — the question-side analogue of "no
   fabricated source" (§2);
3. the **structured-residue-on-refusal cost** — readers emit a reason *string*
   today, not the typed residue a *named* question needs (§3);
4. **Q2 answer-binding must re-enter the gate** — augment input and re-run, never
   mutate the model mid-flight (§4);
5. **bus integration** — `QUESTION_NEEDED` is a reserved tenant on Doc 1's
   Epistemic Disclosure Bus, not a parallel delivery path (§5).

> Primary frontier: [[stage2-epistemic-disclosure-bus-verified-v1-scoping-2026-06-08]]
> (Stage 2 / VERIFIED is the first implementation; Q1 is the **second** bus tenant,
> scoped now only so the bus reserves its seat). Q1 derivation can be built
> off-serving early; Q1 *delivery* waits on the bus.

**Why Q1 matters (one line, from the intake argument).** A question is CORE's
**intake mechanism for resolvable missing state**; the limitation pass is the gate
that decides whether intake is appropriate (session-doc §1.5). Mis-handle it and CORE
either *refuses when it should ask* (a structural inability to receive the unlocking
datum) or *asks when it should propose* (a wasted channel). Q1 is therefore
general-intelligence infrastructure, which is why the organ lives in `core/`.

---

## 1. The four dispositions, mapped to the SHIPPED registry — and what `ask` re-audits

The limitation pass (session-doc §1.5.3) yields eight `LimitationKind`s and six
`ResolutionAction`s. Only **two** kinds become a question. The discipline binding
this brief and Doc 1: `LimitationAssessment` is a **consolidating view** over the
shipped `core/comprehension_attempt/failure_family.py` registry + the contemplation
terminals — **not a fourth taxonomy** (session-doc §1.5.7; CLAUDE.md "no parallel
decision paths"). So the ASK scope must be expressed as a *derivation from* the
families that already ship, family by family.

The registry today (`REGISTRY`, verified on branch) partitions every organ refusal
reason into `must_remain_refused` vs `proposal_allowed` vs `input_shape`. Introducing
`ask` re-reads that partition, and it **cuts both ways**:

| Shipped family (examples) | Today | `LimitationKind` | With `ask`, disposition |
|---|---|---|---|
| `cmb_non_positive_net`, `cmb_non_integer`, `non_integer_solution`, `negative_solution` | refuse | `hard_boundary` | **refuse** (unchanged — math/logic impossibility) |
| `cmb_combine_ambiguous` | refuse | `ambiguous_structure` | **ask** ("together, opposing, or separate?") |
| `cmb_underdetermined` (`cmb_missing_second_rate`), `rate_underdetermined` (`missing_rate`/`missing_time`/`missing_quantity`), `ungrounded_base` | refuse | `missing_information` | **ask** (the missing datum) |
| `cmb_unsupported_*`, `unsupported_rate_duration`, `missing_category_pair` | propose | `capability_gap` | **propose** (unchanged — CORE lacks the transform) |
| `answer_key_contradiction` | report | `contradiction` | **report** (unchanged) |
| `input_shape` (`not_combined_rate_shaped`, …) | step aside | `input_shape` | **step aside** (unchanged) |
| **`missing_total_count`, `missing_weighted_total`** | **propose** | **`missing_information`** | **ask** ⚠ *reclassification* |

### 1.1 The reclassification finding (decide with tests, never silently re-key)

Two shipped families are currently `proposal_allowed = True` →
`proposal_target="r2_gold_fixture"`:

```text
missing_total_count     ("propose a total-count-constraint gold fixture")
missing_weighted_total  ("propose a weighted-total-constraint gold fixture")
```

But by the limitation taxonomy these are **`missing_information`, not
`capability_gap`**: the user *could state the total* and unblock solving — CORE does
not lack the transform, it lacks a datum. The shipped registry classifies them as
coverage gaps **because `ask` does not exist yet** — proposing a fixture was the only
non-refuse move available. Once `ask` exists they are mis-classified and should **ask,
not propose**.

This is a real change to shipped behaviour, so it is **scope-it-don't-silently-re-key**
territory: decided in the Q1 derivation slice (Q1-B) **with tests**, not edited into
`failure_family.py` in passing. The test must assert the *specific* path: a
`missing_total_count` attempt now yields `ResolutionAction.ask_question` with a typed
`MissingSlot`, and no longer emits a proposal. (Contrast the families that stay
`propose`: `cmb_unsupported_reciprocal` is a genuine capability gap — no datum the user
can supply makes CORE able to do reciprocal work-rate arithmetic.)

Shay's rule, already encoded in the registry comments: **proposals are for structural
capability gaps, not under-specified inputs.** `ask` is what finally lets the registry
honour that rule for `missing_*`.

---

## 2. The grounded-rendering wrong=0 invariant (the hard one)

The question organ has its **own** wrong=0 obligation, and it is the question-side
analogue of "no fabricated source / no ungrounded named operand":

> **A question may not name an entity, slot, unit, relation, or missing fact unless
> that element was grounded in the attempted comprehension trace.** When the grounded
> terms lack the field a question template needs, degrade to a **generic** question or
> emit `question_unrenderable` — never a named guess.

```text
Anna and <unnamed> work together. Anna paints 3 rooms/hour. How many rooms in 4 hours?
  grounded:  {Anna, rooms/hour, 4 hours, "second agent (unnamed)"}
  WRONG ask: "What is Ben's rate?"               ← "Ben" was never grounded — fabricated
  OK   ask:  "What is the second person's rate in rooms per hour?"   ← generic, all terms grounded
```

This is the precise surface where the R4 (CMB) reader's adversarial passes kept
catching real wrong=0 bugs (11 in the CMB-c reader alone) — fabricating structure the
text did not license. The **same** discipline applies to asking: a fabricated entity in
a question is as much a wrong=0 breach as a fabricated operand in an answer. So the
question renderer is a wrong=0-adjacent surface and gets the same adversarial,
read-only verification treatment when built.

`renderability_gap` is therefore a **first-class** `LimitationKind` (session-doc
§1.5.3), with its own disposition (**ask generic / refuse-to-name**) — not an
afterthought inside the `ask` path.

---

## 3. Structured residue on refusal — the substrate gap Q1 must close first

Today the comprehension organs surface, per attempt
(`core/comprehension_attempt/model.py::ComprehensionAttempt`):

```python
refusal_reason: str | None         # e.g. "cmb_missing_second_rate"  ← a string
setup_signature: str | None
answer: int | None
evidence: tuple[SourceSpanLink, ...]   # source spans — partial, not typed slots
```

That is **enough to classify** the limitation (the reason string keys the failure
family) but **not enough to render a *named* question.** To ask "What is the second
person's rate **in rooms per hour**?" the renderer needs typed partial-parse residue:
*which* slot is missing, *what unit/type* its answer must take, and *which grounded
terms* may appear in the prose. The string `"cmb_missing_second_rate"` and a tuple of
source spans do not carry that.

So Q1 v1 has a **prerequisite substrate slice**: organs must emit, on the refusals
that map to `ask`, a typed residue — sketched in the session doc as `MissingSlot`
(slot name, expected answer type/unit, binding target) and `grounded_terms` (the
renderability source). This is additive and off-serving:

- It rides on the existing `ComprehensionAttempt` (add typed-residue fields; do not
  fork a parallel record).
- It is emitted **only** for the `ask`-mapped families (§1) — `hard_boundary` /
  `capability_gap` / `input_shape` refusals need no residue (they don't ask).
- Without it, every question degrades to **generic** by the §2 invariant — which is
  *safe* (wrong=0-preserving) but low-value. The residue is what earns *named*,
  minimal-sufficient questions without fabricating.

This is the honest cost the session doc implies: **named questions are gated on a
typed-residue upgrade to the readers**, not free once the question organ exists.

---

## 4. Answer-binding (Q2) must re-enter the gate — not mutate the model

When a user answers a CORE question, the binding step (the session doc's Q2 /
`AnswerBinding`) is **not** "patch the missing slot into the existing model and
continue." It is:

```text
parse typed answer  →  augment the ORIGINAL problem input with the bound datum
                    →  RE-RUN the owner organ (read → solve → verify) from scratch
                    →  the re-run re-enters the limitation gate
```

Two reasons this is load-bearing, both wrong=0:

- **Immutability (CLAUDE.md coding-style).** A `ComprehensionAttempt` is frozen;
  binding produces a *new* augmented input and a *new* attempt, never an in-place
  mutation of the first.
- **The answer is itself input, and input is never trusted.** A bound answer can be
  ambiguous, out of range, or *introduce a new limitation* (e.g. it makes the system
  over-determined, or contradicts a stated quantity). Re-entering the gate means the
  augmented problem is re-classified — it may now `solve`, but it may also `ask again`,
  `refuse`, or `report a contradiction`. A mutate-and-continue path would skip that
  re-classification and could commit a wrong answer the fresh gate would have caught.

Q2 is **out of scope for Q1 v1** (non-claim, §6) — but the binding contract must be
*written down now* so the Q1 question carries the typed target a future re-run needs
(the `MissingSlot.binding_target`), rather than a free-text slot a mutate-path would
assume.

---

## 5. Bus integration — `QUESTION_NEEDED` is a reserved tenant, not a side channel

Q1 does not get its own delivery path to the user. A served question is governed for
the surface **exactly as a served answer is**, through Doc 1's Epistemic Disclosure
Bus (`EpistemicState + LimitationAssessment → ServedDisposition`):

```text
LimitationAssessment(missing_information | ambiguous_structure)
    → ResolutionAction.ask_question
    → ServedDisposition(DISPOSITION=ask, ...)
    → QUESTION_NEEDED   (a RESERVED tenant on the bus; see Doc 1 §0 matrix)
    → render (grounded-only, §2) → served surface
```

Consequences for sequencing:

- **Doc 1 must reserve the `ask` disposition / `QUESTION_NEEDED` seat now** (it does —
  Doc 1 §0, §7) so the bus is not designed too narrowly around VERIFIED.
- **Q1 *derivation* (limitation pass + missing-slot residue + renderer) can be built
  off-serving early** — it imports no serving path, so it cannot regress the GSM8K
  seal, and it can be validated against organ holdouts.
- **Q1 *delivery* (a question actually reaching a served surface) waits on the bus**
  being live (Stage 2 builds it). Until then, questions are produced and tested
  off-serving; nothing new reaches the user.

This keeps Q1 from becoming a parallel "clarification feature" bolted beside the
served path — the exact anti-pattern the consolidation discipline forbids.

---

## 6. What Q1 v1 is NOT (non-claims)

- **Not** a freeform clarification / chat-style "can you tell me more?" — every
  question is typed, minimal-sufficient, single-slot, and grounded-only (§2;
  session-doc §1.4 minimal-sufficient rules).
- **Not** a dialogue manager / multi-turn conversation state machine.
- **Not** Q2 answer-binding — that is a separate, later slice; Q1 only *produces* the
  question and records the typed target (§4).
- **Not** a silent re-key of `missing_total_count` / `missing_weighted_total` — the
  reclassification is decided in Q1-B with tests (§1.1).
- **Not** a change to any served surface — Q1 derivation is off-serving; delivery
  waits on Doc 1's bus (§5). No serving metric, pinned SHA, or `CLAIMS.md` moves.
- **Not** a fourth disposition taxonomy — `LimitationAssessment` consolidates the
  shipped failure-family registry + contemplation terminals (§1; session-doc §1.5.7).

---

## 7. Build order (Q1-A..D) — off-serving, each its own PR (scoping only here)

> Sequenced **after** Stage 2 establishes the bus, except Q1-A/B which are
> off-serving and can begin in parallel once this brief is approved.

1. **Q1-A — Limitation pass (`LimitationAssessment`) as a consolidating view.** The
   pre-question classifier (session-doc §1.5): derive `LimitationKind` /
   `ResolutionAction` from the shipped failure families + contemplation terminals;
   add **only** the new `ask_question` action and the `renderability_gap` guard. Tests
   assert the §1 mapping, including that math/contradiction families stay non-ask.
2. **Q1-B — Typed missing-slot residue (the §3 substrate slice) + the
   reclassification.** Add typed residue (`MissingSlot`, `grounded_terms`) to the
   `ask`-mapped organ refusals; decide `missing_total_count` / `missing_weighted_total`
   → `ask` with the specific tests from §1.1. Off-serving.
3. **Q1-C — The renderer with the grounded-rendering invariant (§2).** Render minimal,
   single-slot, grounded-only questions; degrade to generic / `question_unrenderable`
   when residue is insufficient. Adversarial read-only verification on this surface
   (it is wrong=0-adjacent). Off-serving.
4. **Q1-D — Bus delivery (`QUESTION_NEEDED` tenant).** Wire the rendered question to
   Doc 1's bus as the second disposition. **Requires the bus to be live** (Stage 2
   S2-A..C). Until then Q1-A..C ship and are validated off-serving with nothing
   reaching a served surface.

Q2 answer-binding (§4) is a **separate later batch**, explicitly out of Q1 v1.

---

## 8. Verification lanes (when built)

- `core test --suite full -q` — the §1 family-mapping tests (Q1-A), the
  reclassification tests (Q1-B), the grounded-rendering / `question_unrenderable`
  tests (Q1-C).
- The router-organ-hygiene invariant (`tests/test_router_organ_hygiene.py`) — the
  limitation pass must not let any organ claim a foreign-text limitation (it must map
  to `input_shape` / `step_aside`).
- Adversarial read-only verification on the Q1-C renderer (the wrong=0-adjacent
  surface), the same discipline that paid off across the CMB ladder.
- `scripts/verify_lane_shas.py` + `scripts/generate_claims.py --check` — must stay
  **green and unchanged** (Q1 is off-serving; the GSM8K seal does not move).

> **Stop boundary.** This brief is scoping. No code lands until review approves it and
> the Q1-A..D order. The design of record remains the session doc; this brief only
> pins Q1 to the shipped substrate. HOLD for review.
