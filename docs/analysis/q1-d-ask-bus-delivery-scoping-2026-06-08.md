# Q1-D — ASK bus delivery (`QUESTION_NEEDED` tenant) — decision record

**Date:** 2026-06-08 · **Status:** ACCEPTED + IMPLEMENTED (PR #668, merge commit
`07149c20`) · **Branch:** `docs/q1-d-ask-bus-delivery-scoping`

> **Decision record, not an open brief.** All five decisions below (D1–D5) were
> ruled and are implemented in PR #668. This doc is retained as the durable record of
> *what was decided and why*; the implementation lives in
> `core/epistemic_questions/delivery.py`, `generate/contemplation/findings.py`
> (`Terminal.QUESTION_NEEDED`), `core/epistemic_disclosure/limitation.py` (the now-total
> `terminal_for_action`), and `tests/test_question_delivery.py`. Where this doc and the
> code disagree, the code is authoritative. Two *served-surface* decisions remain open
> and are deferred to dedicated scoping docs (see §7): `ask_serving_enabled` and the
> registry/carve-out flip.

**What this records.** The decisions for the **fourth and last Q1 rung** — *delivery*.
Q1-A (limitation pass), Q1-B (typed residue + `missing_*` reclassification,
`Q1B_ASK_CARVE_OUT`), and Q1-C (the grounded-only renderer, strictly single-slot) all
shipped **off-serving**; Q1-D (also off-serving) takes the rendered question and routes
it onto Doc 1's Epistemic Disclosure Bus as the **second tenant** (`QUESTION_NEEDED`),
behind the first (`VERIFIED`). Each decision is pinned against the shipped code it
landed on.

> Design of record: the session doc
> `docs/sessions/2026-06-08-epistemic-question-articulation-first-skill-of-contemplation.md`
> (§4 the `QUESTION_NEEDED` terminal, §5/§1.5.8 bus integration).
> Frontier companions: [[q1-epistemic-question-articulation-v1-scoping-2026-06-08]]
> §5/§7 (Q1-D = bus delivery), [[stage2-epistemic-disclosure-bus-verified-v1-scoping-2026-06-08]]
> (the bus VERIFIED is first tenant of).

**The one-line shape.**

```text
LimitationAssessment(ask_question, missing_slots)
  → choose_served_disposition(...) = ServedDisposition.ASK        [P0-3, shipped]
  → render_question(assessment) = EpistemicQuestion               [Q1-C, shipped]
  → Q1-D: package → Terminal.QUESTION_NEEDED + DeliveredQuestion  [THIS RUNG]
  → (off-serving sink: written like a proposal, never auto-served)
```

**The hard constraint from the steer.** Q1-D **does not render**. It consumes only
the `EpistemicQuestion` the Q1-C renderer produced. This preserves the rung
separation that makes each layer independently auditable:

```text
Q1-B: typed residue        (what is missing, as typed slots)
Q1-C: renderability         (can it be asked without fabricating? → EpistemicQuestion)
Q1-D: delivery              (route the rendered question onto the bus)
```

If Q1-D re-derived or re-rendered, the wrong=0 grounded-rendering guard (Q1-C
`_names_only_grounded`) would be bypassed by a second, ungoverned surface — the
exact parallel-path anti-pattern the consolidation discipline forbids.

---

## 1. State of the substrate Q1-D lands on (verified on branch)

| Piece | Status | Q1-D dependency |
|---|---|---|
| `ServedDisposition` + `choose_served_disposition` (`core/epistemic_disclosure/disposition.py`) | **shipped (P0-3)** | `ask_question → ASK` already mapped; **zero runtime consumers** |
| `EpistemicQuestion` + `render_question` (`core/epistemic_questions/render.py`) | **shipped (Q1-C)** | the *only* input Q1-D consumes; strictly single-slot |
| `Terminal` enum (`generate/contemplation/findings.py`) | shipped, **7 members** | `QUESTION_NEEDED` **absent** — Q1-D adds it (sibling to `PROPOSAL_EMITTED`) |
| `LimitationAssessment` / `MissingSlot` (`core/epistemic_disclosure/limitation.py`) | shipped (Q1-A/B) | source of the assessment; `Q1B_ASK_CARVE_OUT` still live |
| failure-family `REGISTRY` (`core/comprehension_attempt/failure_family.py`) | shipped | `missing_*` families still `proposal_allowed=True` (carve-out) |
| contemplation proposal sink (`teaching/proposals/`) | shipped | the **template** for the off-serving question sink |

Two facts set the altitude:

1. **Nothing consumes `ServedDisposition.ASK` or `EpistemicQuestion` today.** The bus
   decision table is a pure mapping with no caller. Q1-D is therefore the **first**
   consumer of the ASK disposition — which is exactly why it must be scoped, not
   improvised.
2. **The bus is itself still off-serving.** The VERIFIED tenant (P1) was built as a
   proof-object producer in `evals/`; the served-surface wiring was deferred to a
   named decision (`verified_serving_enabled`). Q1-D inherits the same two-layer
   split: an off-serving delivery layer buildable now, and a served-surface wiring
   layer that waits on a ruling.

---

## 2. What Q1-D shipped (off-serving) — ACCEPTED

**Decision: build the off-serving delivery layer; defer served-surface wiring to a
named gate.** Implemented in #668. This mirrors the VERIFIED lane exactly (P1-B
produced proof objects off-serving; serving wiring is a separate, gated decision).
One scope refinement landed with the code: the delivery layer ships **standalone** —
`deliver_ask`/`emit_question` are tested but **not yet called from `pass_manager`**
(mirrors P1-B shipping the producer without wiring `verify.py`); pass-manager wiring is
a deliberate follow-up, folded into the §7 ASK serving-integration scope.

### 2.1 `Terminal.QUESTION_NEEDED` — the off-serving sink

Add `QUESTION_NEEDED` as an eighth contemplation terminal, a **sibling of
`PROPOSAL_EMITTED`** (the session doc §4 already specifies this: "not a subtype of
`PROPOSAL_EMITTED`; sibling terminals"). The contemplation pass, when an
`ask_question` assessment renders successfully, terminates `QUESTION_NEEDED` carrying
the `DeliveredQuestion` artifact — **just as `PROPOSAL_EMITTED` carries the proposal,
and just as proposal-only never auto-installs**. The artifact is written to a sink
(`teaching/proposals/`-analogue, e.g. `teaching/questions/` or a
`questions/` JSONL), reviewable, never delivered to a user by this rung.

### 2.2 `DeliveredQuestion` — the delivery artifact (wraps, never re-renders)

A new frozen dataclass that **wraps** the Q1-C `EpistemicQuestion` and adds the
delivery-level fields the assessment already carries — it does **not** promote the
renderer to the session-doc's richer aspirational model:

```text
DeliveredQuestion (frozen):
  question:        EpistemicQuestion   # verbatim from render_question — never rebuilt
  owner_organ:     str                 # from LimitationAssessment.owner_organ
  blocking_reason: str                 # from LimitationAssessment.blocking_reason
  answer_binding:  AnswerBinding | None # RESERVED (Q2); None in Q1-D
  source_attempt_id: str | None        # provenance, if the attempt supplied one
```

`AnswerBinding` is **reserved, not implemented** — the seat exists so the Q2
round-trip is wireable without reshaping, but Q1-D binds no answers (session doc §4:
"answer-binding must re-enter the gate", a later batch).

### 2.3 Off-serving guarantee

The delivery module imports **no** `generate.derivation` / `core.reliability_gate`
(AST-checked, same test shape as Q1-C `test_renderer_is_off_serving`). It cannot move
the sealed GSM8K metric or any pinned SHA. **No served surface, no `chat/runtime.py`
wiring, no `CLAIMS.md` change.**

---

## 3. The decisions — ALL ACCEPTED + IMPLEMENTED (#668)

These were the load-bearing choices Q1-D forced. Each was ruled as its recommendation
and is implemented in #668; the rulings are recorded inline (**Ruling:**) under each.

### D1 — Off-serving delivery now, or wait for the bus to be served? — **ACCEPTED: now**

The Q1 scoping doc (§7.4) said *"Q1-D requires the bus to be live (Stage 2 S2-A..C)."*
But Stage 2 shipped its first tenant **off-serving** (P1 is a proof-object producer;
serving wiring deferred). So the literal precondition ("bus live") never materialised
as *served* — it materialised as *off-serving infrastructure*.

- **Recommend:** build Q1-D's off-serving delivery layer now (matches the VERIFIED
  precedent), and defer served delivery to a named gate **`ask_serving_enabled`** —
  the ASK analogue of `verified_serving_enabled`. Q1-D off-serving produces and tests
  `QUESTION_NEEDED` + `DeliveredQuestion`; **nothing reaches a user.**
- **Alternative:** hold Q1-D entirely until the bus has a served surface. Costs the
  off-serving proof object that the VERIFIED lane found valuable; gains nothing the
  gate doesn't already protect.

### D2 — The unrenderable fallback (the wrong=0-adjacent decision) — **ACCEPTED**

When Q1-C returns `unrenderable` (`renderability_gap`, `multi_slot_not_supported`,
`fabrication_guard`, `no_missing_slot`), Q1-D must **not** terminate `QUESTION_NEEDED`
with no question — that would be a contentless ASK, the delivery-side equivalent of a
fabricated answer.

- **Recommend:** an unrenderable ASK **falls back to the family's standing
  disposition** — for the `missing_*` carve-out families that is `PROPOSAL_EMITTED`
  (they are `proposal_allowed=True` today); for an ambiguous-structure family with no
  renderable slot it is `NO_PROGRESS`. The rule: *an `ask` classification that cannot
  be rendered never produces a dead end and never produces an empty question.* This is
  the delivery-layer guard, and it gets a test that **fails** if an unrenderable
  assessment ever reaches `QUESTION_NEEDED`.
- This is why the carve-out (D3) must not flip yet — see below.

### D3 — Does Q1-D resolve the `Q1B_ASK_CARVE_OUT`? — **ACCEPTED: no, carve-out stays**

Q1-B deliberately **kept** `REGISTRY` `proposal_allowed=True` for `missing_total_count`
/ `missing_weighted_total` and added the disclosure-layer `Q1B_ASK_CARVE_OUT`, with the
stated condition: *no silent re-key, no proposal-signal dead zone "until ASK delivery
lands."* Q1-D **is** ASK delivery landing — so does the registry flip now?

- **Recommend: no — the carve-out persists until `ask_serving_enabled`.** Off-serving
  `QUESTION_NEEDED` does **not** yet replace the proposal channel a real user would
  see. If the registry flipped `proposal_allowed → ask` while serving still proposes,
  the carve-out's own dead-zone hazard reappears (a family classified `ask` with no
  served ask path). The flip is therefore gated on **serving** delivery, not
  off-serving delivery. Q1-D records this explicitly so the carve-out's resolution
  condition is unambiguous: *the carve-out closes when `ask_serving_enabled` is the
  ruling, not when off-serving `QUESTION_NEEDED` ships.*
- The D2 fallback (unrenderable ASK → standing disposition) is what makes this safe:
  while the carve-out stands, the registry's `proposal_allowed=True` remains the
  truthful fallback target.

### D4 — Where does the off-serving sink write? — **ACCEPTED: `teaching/questions/`**

`PROPOSAL_EMITTED` writes to `teaching/proposals/`. The question sink is a sibling.

- **Recommend:** `teaching/questions/` (or a `questions.jsonl` beside `proposals.jsonl`)
  — same proposal-only, review-gated, HITL-visible discipline; never auto-served. The
  artifact is the `DeliveredQuestion` serialized deterministically (frozen → hashable →
  replayable). Confirm the path/name; it is a one-line decision, not architecture.

### D5 — Single-slot carries through (no fan-out in Q1-D) — **ACCEPTED**

Q1-C is **strictly single-slot** (the `multi_slot_not_supported` refusal shipped in
this same review). Q1-D therefore delivers **at most one** `DeliveredQuestion` per
assessment; a multi-slot assessment renders unrenderable and takes the D2 fallback.
One-question-per-slot fan-out is **not** Q1-D — it is a later rung that must first
solve the "which slot first / minimal-sufficient" ranking (session doc §1.4, `rank.py`,
Q2+). Stated here so delivery does not silently grow a fan-out.

---

## 4. What Q1-D is NOT (non-claims)

- **Not** a served surface. No question reaches a user; `chat/runtime.py` is untouched;
  the served-surface wiring is the deferred `ask_serving_enabled` gate (D1).
- **Not** a re-renderer. Q1-D consumes the Q1-C `EpistemicQuestion` verbatim; it never
  builds prose, so the grounded-rendering wrong=0 guard is never bypassed.
- **Not** the registry flip. `missing_*` stays `proposal_allowed=True`; the
  `Q1B_ASK_CARVE_OUT` persists until `ask_serving_enabled` (D3).
- **Not** Q2 answer-binding. `AnswerBinding` is a reserved seat, bound to nothing; the
  answer round-trip re-enters the limitation gate in a later batch (session doc §4).
- **Not** a fan-out. One slot, one question — multi-slot takes the unrenderable
  fallback (D5).
- **Not** a metric/SHA/`CLAIMS.md` move — off-serving, AST-verified.

---

## 5. Verification lanes (as shipped in #668)

- `tests/test_question_delivery.py` (14 tests) — `ask_question` + renderable assessment
  → `Terminal.QUESTION_NEEDED` + a `DeliveredQuestion` wrapping the *exact* Q1-C
  `EpistemicQuestion`; both **D2 fallback branches** (proposing → `PROPOSAL_EMITTED`,
  non-proposing → `NO_PROGRESS`); the structural guards (a `DeliveredQuestion` cannot
  wrap an unrenderable question / be served / carry an `AnswerBinding`); the idempotent
  content-addressed sink + no-artifact-on-fallback; the off-serving AST test.
- `tests/test_limitation_assessment.py` — the two consolidation tests updated for the
  now-total `terminal_for_action` (`ask_question → QUESTION_NEEDED`).
- Schema-obligation discipline (CLAUDE.md): the D2 guard is enforced **twice** — in
  `deliver_ask` and structurally in `DeliveredQuestion.__post_init__` — so an
  unrenderable assessment can never terminate `QUESTION_NEEDED`; the off-serving test
  fails if a forbidden import is added. Results: smoke 90/0, affected suites 128/0.

---

## 6. Build order (Q1-D, off-serving, one PR — as shipped in #668)

1. `Terminal.QUESTION_NEEDED` added (sibling of `PROPOSAL_EMITTED`).
2. `DeliveredQuestion` dataclass (+ reserved `AnswerBinding`); wraps `EpistemicQuestion`.
3. The delivery function `deliver_ask`: `ask_question` assessment → render (consume
   Q1-C) → on renderable, `QUESTION_NEEDED` + artifact; on unrenderable, the **D2
   fallback**. Plus the `emit_question` sink writer.
4. Off-serving AST test + the D2 guard tests + the sink-write tests.

The served-surface wiring (`ask_serving_enabled`), the `pass_manager` call site, and the
registry flip (D3) are a **separate, later, ruling-gated** step — deferred to the §7
ASK serving-integration scoping doc, NOT this PR. Q2 answer-binding is a separate batch.

---

## 7. Outcome — RESOLVED, and what remains open

**Resolved (#668):** Q1-D's **off-serving** delivery layer was built —
`Terminal.QUESTION_NEEDED` + `DeliveredQuestion`, consuming Q1-C, with the D2
unrenderable-fallback guard and the D3 carve-out left standing — matching the VERIFIED
precedent, keeping wrong=0 honest, moving no metric. The off-serving ASK lane (residue →
renderability → delivery) is now complete.

**Open — deferred to dedicated scoping docs (no served-surface code until both are
reviewed):**

1. **ASK serving-integration** (`ask_serving_enabled`): the `pass_manager` integration
   point (where `deliver_ask` is actually called), the served-surface behaviour for a
   `QUESTION_NEEDED` reaching a user, the `Q1B_ASK_CARVE_OUT` retirement gate + registry
   flip (`proposal_allowed → ask`), and the no-question/no-proposal **dead-zone proof**
   (a family must never lose both signals across the flip).
2. **VERIFIED serving-wiring** (`verified_serving_enabled`): the gold-free independent
   reader requirement, holdout gates, proof-producer eligibility, and the explicit ban
   on eval-gold-backed serving.

Both are the VERIFIED/ASK halves of the same "this is where off-serving stops" line.
