# ASK serving-integration — `ask_serving_enabled` — scoping brief

**Date:** 2026-06-08 · **Status:** scoping (NO CODE) · **HOLD for review** ·
**Branch:** `docs/serving-integration-scoping`

**What this brief is.** The scope for the *one* served-surface decision the ASK lane
deferred. The off-serving ASK lane is complete and on main:

```text
Q1-B  typed residue + ask classification         (LimitationAssessment.missing_slots)
Q1-C  grounded-only rendering                     (render_question → EpistemicQuestion)
Q1-D  off-serving delivery artifact               (deliver_ask → QUESTION_NEEDED + sink)
```

`deliver_ask` / `emit_question` exist and are tested, but **nothing calls them from a
live path** — they are produced-but-not-emitted, exactly as P1-B's verified producer
is built-but-not-served. This brief scopes the step that closes that gap: letting a
`QUESTION_NEEDED` actually reach a user, behind a named gate. **No code here** — this
is the decision surface for review.

> Companions: [[q1-d-ask-bus-delivery-scoping-2026-06-08]] (the off-serving rung, §7
> defers exactly this), [[verified-serving-wiring-scoping-2026-06-08]] (the VERIFIED
> half of the same "where off-serving stops" line). Design of record: the session doc
> §5 / §1.5.8 (the disclosure bus).

---

## 1. The five things this decision must pin

The steer named five; each is grounded against shipped code below.

```text
1. ask_serving_enabled              — the kill switch
2. the pass_manager integration point  — where deliver_ask is actually called
3. the Q1B_ASK_CARVE_OUT retirement gate + registry flip
4. served-surface behaviour for a QUESTION_NEEDED reaching a user
5. the no-question/no-proposal dead-zone proof
```

---

## 2. The integration point (grounded)

`generate/contemplation/pass_manager.py::contemplate(text, *, proposal_root=...)` is
the live contemplation entry. When every attempt is refused it calls
`_classify_all_refused(text, attempts, findings, proposal_root)`, which is where
`emit_proposal` fires for a `proposal_allowed` family and terminates
`PROPOSAL_EMITTED`. **That is the exact analogous site for ASK:** when a refused
attempt's family maps to `ask_question` (via `assess_from_attempt`), call `deliver_ask`
and — on a renderable result — `emit_question` to the sink and terminate
`QUESTION_NEEDED`; on the D2 fallback, fall through to today's proposal/refuse path.

`contemplate()` is called from `chat/runtime.py` at three sites (827, 901, 1364) — so
the contemplation `Terminal` is already on the served path. The served question text
travels the same way `PROPOSAL_EMITTED` already does.

**Two-layer split (the recommendation), mirroring VERIFIED:**

- **Layer A — pass-manager emission (off-serving still).** `contemplate` emits
  `QUESTION_NEEDED` + writes the `teaching/questions/` artifact, exactly as it emits
  `PROPOSAL_EMITTED` today. This changes the *contemplation* terminal but **reaches no
  user** — the teaching loop is off-serving. This layer is buildable behind no gate
  (it only adds a terminal the pass can reach), but see §3: it interacts with the
  carve-out and so should still wait for the gate, to avoid double-emission churn.
- **Layer B — served delivery (the gated surface).** `chat/runtime.py`, gated by
  `ask_serving_enabled`, renders the `DeliveredQuestion.question.text` to the user as
  the served response when the terminal is `QUESTION_NEEDED`. This is the only layer
  that actually asks the user anything.

Decision to confirm: **do Layer A and Layer B land together behind one gate, or does
Layer A land first (pass emits, nothing served) and Layer B follow?** Recommend
**together, behind `ask_serving_enabled`** — Layer A alone creates the double-emission
state in §3 with no compensating benefit.

---

## 3. The kill switch + the carve-out retirement gate (the coupled core)

### 3.1 `ask_serving_enabled`

Add `ask_serving_enabled: bool = False` to `core/config.py`, the sibling of the
existing `estimation_enabled = False` kill-switch pattern. Default **off**: the
served question path is dark until deliberately enabled, holdout-gated (§5).

### 3.2 Why the carve-out flip is *coupled* to the gate (not to Q1-D)

Q1-B introduced `Q1B_ASK_CARVE_OUT` for `missing_total_count` / `missing_weighted_total`:
the disclosure layer classifies them `ask_question`, but the shipped `REGISTRY` keeps
`proposal_allowed = True` so the proposal pile keeps working. The carve-out's
*retirement condition* is written into `limitation.py`: *"Once ASK is serving, flip
`proposal_allowed = False` on these two families, drop the carve-out set, amend the
test."* The operative word is **serving** — not "delivery exists" (Q1-D already shipped
that off-serving). So:

```text
carve-out retires  ⟺  ask_serving_enabled is the ruling
                       AND a QUESTION_NEEDED is actually served for these families
                       AND the §4 dead-zone proof holds
```

Until then, `proposal_allowed` stays `True`. During the gate's "off" state both signals
coexist (the off-serving question artifact + the proposal) — intentional, no loss.

### 3.3 The flip, as a single reviewed act

When `ask_serving_enabled` is turned on for these families, in **one** change:
1. `proposal_allowed = False` for `missing_total_count` / `missing_weighted_total`.
2. Drop them from `Q1B_ASK_CARVE_OUT` (empty the set, or remove the constant).
3. Amend the `proposal_allowed` invariant test + the carve-out test.
4. The §4 dead-zone proof test must already be green.

This is the "conscious act, not a silent re-key" the carve-out was built to force.

---

## 4. The no-question/no-proposal dead-zone proof (the wrong=0-adjacent guard)

**The hazard.** The flip removes the proposal signal for these families. If, for some
input class, the family classifies `ask_question` BUT the question is unrenderable
(D2), AND the proposal is now off, the family would terminate `NO_PROGRESS` with **no
served question and no proposal** — a dead zone where a user-resolvable gap produces
*nothing*. That is the ASK-side wrong=0 hazard: not a false answer, but a silent loss
of a capability that previously at least proposed.

**The proof obligation (before any flip).** For every family being flipped, prove that
**no input class lands in the dead zone** — i.e. for every reachable assessment of that
family, the question renders (so `QUESTION_NEEDED` is served), OR the proposal is still
on. Concretely:

- The `missing_*` families have pinned single slots in `_FAMILY_TO_MISSING_SLOTS` with
  mapped types (`count_int` / `measured_unit_int`) → they **always render** today, so
  the dead zone is currently empty. The proof must show this is *structural*, not
  incidental: a test that asserts `deliver_ask` returns `QUESTION_NEEDED` (never a
  fallback) for every reachable assessment of the flipped families.
- If any future residue change could make one of these unrenderable (multi-slot,
  unmapped type), the flip must be blocked for that family until either the renderer
  covers it or the proposal stays on.

**The rule:** `proposal_allowed` may flip `True → False` for a family **only** if a
test proves every reachable ask of that family renders. The dead-zone proof is a
precondition of the flip, enforced like the D2 guard (it must *fail* if a fallback path
is reachable for a flipped family).

---

## 5. Served-surface behaviour + holdout gating

### 5.1 What a served `QUESTION_NEEDED` looks like

When `ask_serving_enabled` and the terminal is `QUESTION_NEEDED`, the served surface
returns the `DeliveredQuestion.question.text` (the grounded-only rendered question) as
the response — distinct from a committed answer, an `[approximate]` disclosure, or a
refusal. It is an **intake request**: the disposition is `ServedDisposition.ASK`
(already mapped in `disposition.py`). The question names nothing ungrounded (Q1-C
guarantee), so it cannot leak a fabricated entity even on the served path.

Open sub-decision: **the served prefix/marker.** VERIFIED gets a distinct `[verified]`
prefix; APPROXIMATE gets `[approximate]`. ASK should get its own surface marker (a
question is neither). Recommend a distinct, tested marker; pin the exact string at
build, not here.

### 5.2 Holdout gate (no quiet widening)

Like VERIFIED, ASK serving must be proven on a holdout before it widens live: a
validate-first probe over a held-out set confirming (a) served questions are
grounded-only (no fabrication escapes on the served path), (b) no family in the flip
set hits the dead zone, (c) the GSM8K serving seal is byte-identical (ASK is
off-the-metric — it asks, it does not answer — but the probe proves it). Only then does
`ask_serving_enabled` go on, one surface at a time.

---

## 6. What this is NOT

- **Not** a dialogue manager / multi-turn state machine — one grounded question, then
  the existing flow; the answer round-trip is Q2 (`AnswerBinding`, a separate batch).
- **Not** a re-render — the served path emits the Q1-D `DeliveredQuestion.question.text`
  verbatim; no second prose surface.
- **Not** a GSM8K-metric move — ASK asks, it never answers; the pinned SHAs and
  `CLAIMS.md` are untouched. The holdout probe proves it.
- **Not** the carve-out flip *yet* — the flip is the terminal act of *this* decision,
  gated on `ask_serving_enabled` + the §4 dead-zone proof, not on Q1-D.

---

## 7. The questions for the ruling

1. **Gate:** add `ask_serving_enabled = False` (sibling of `estimation_enabled`)? (rec: yes)
2. **Layering:** land pass-emission (Layer A) and served delivery (Layer B) together
   behind the one gate? (rec: yes — Layer A alone only adds double-emission churn)
3. **Carve-out flip:** retire `Q1B_ASK_CARVE_OUT` + flip `proposal_allowed` as a single
   reviewed act, gated on the gate AND the §4 dead-zone proof? (rec: yes)
4. **Dead-zone proof:** require a passing "every reachable ask of a flipped family
   renders" test as a precondition of any flip? (rec: yes — this is the ASK wrong=0 guard)
5. **Served marker:** a distinct ASK surface marker (not `[verified]` / `[approximate]`)? (rec: yes)
6. **Holdout:** validate-first probe (grounded-only on served path + no dead zone +
   GSM8K seal byte-identical) before the gate goes on? (rec: yes)

No served-surface code until this brief is reviewed.
