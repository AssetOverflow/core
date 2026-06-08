# Session 2026-06-08 — Epistemic question articulation: the first skill of contemplation

**Status:** discussion / design note — **session document, not an ADR yet.** No
code shipped. This records a design reached in conversation immediately after the
servability-blade discussion
([`2026-06-08-practice-attempts-and-servability-blade`](./2026-06-08-practice-attempts-and-servability-blade.md)),
and deliberately preserves the train of thought so the idea cannot be silently
collapsed into a generic "ask clarifying questions" feature. **Headline:** The
first real skill of contemplation is not thinking harder, not adding more steps,
not producing reflection text. It is: **recognise that the current state is
underdetermined, articulate the missing information, and ask the question whose
answer would collapse the uncertainty.** For CORE this becomes a typed,
deterministic, failure-family-driven organ — `core/epistemic_questions/` — that
produces a typed `EpistemicQuestion` artifact, routes it to the surface as
`QUESTION_NEEDED`, and reserves an `AnswerBinding` slot so the answer drives the
solve, not a guess.

`No serving path, algebra, versor, recall, or gate touched. This is the research`
`trail — design and reasoning preserved for the open-source record.`

> **Why this doc exists.** CORE is open-source research in an uncharted corner
> of AI. The *reasoning behind* a design is as load-bearing as the design itself.
> This captures not just *what* to build but *why the idea matters*, *how the
> conversation arrived at it*, and *what the sharp edges are* — so future agents,
> the operator, and outside researchers can follow the actual train of thought
> rather than just read a finished spec.

---

## TL;DR — the core insight in four lines

```text
A question is not language.  A question is a typed request for missing state.
The first skill of contemplation is: ask the smallest question that unblocks the proof.
But the FIRST move is upstream of the question: a limitation pass classifies the gap —
  only missing/ambiguous information becomes a question (the intake gate; see §1.5).
question  ≠  proposal  (missing information in the world vs missing capability in CORE)
Question generation must be deterministic, slot-directed, template-driven — never vibes.
```

---

## 1. How we got here — the chain of reasoning

### 1.1 The provocation

This session grew directly from the servability-blade discussion. Once we
established that `wrong=0` means *no false presentation of epistemic status* —
not silence unless omniscient — the next question was immediate: if the engine
**cannot** produce a verified answer and **should not** guess, what *should* it
do with that underdetermined state?

The first answer is the blade's `REFUSE_UNSUPPORTED`. But that throws the problem
away. The better answer, for problems that are merely *underdetermined*, is to
ask the one question that would make the problem solvable.

### 1.2 The reframing of contemplation

Generic AI systems treat "asking a question" as a conversational habit — a
politeness or a hedge. The reframing arrived in this conversation:

> A question is not merely language. A question is a typed request for missing state.

That single sentence reorients the whole design. If a question is a *typed
request*, then:

- it has a *kind* (what category of missing information),
- it has a *target slot* (exactly where the answer will bind),
- it has an *expected answer type* (what form the answer must take),
- it has a *blocking reason* (why the current attempt cannot proceed),
- it has a *resolution target* (which constraints it unblocks).

And therefore it must be *generated from typed failure evidence*, not from free
text improvisation.

### 1.3 The minimal sufficient question

The discipline that followed from that reframing:

> Ask the smallest question that would unblock the current proof.

This is the criterion that distinguishes *epistemic query generation* from
chatbot clarification-seeking. A valid question must satisfy all of:

1. It targets exactly one missing slot.
2. The expected answer type is known.
3. If answered, the system knows exactly where to bind the value.
4. It does not ask for information the system could derive.
5. It does not ask for unsupported capabilities.
6. It does not ask multiple things at once.

Violation of any criterion is a quality failure in the question organ, not a
"good enough" clarification.

### 1.4 The sharp distinction: question vs proposal

This is the most critical architectural boundary. Two different contemplation
terminals are possible:

| Terminal | Meaning | Example |
|---|---|---|
| `QUESTION_NEEDED` | The problem has enough structure to be solvable, but a specific value / referent / choice is missing from the *input* | Anna + Ben painting, only Anna's rate given → "What is Ben's rate in rooms per hour?" |
| `PROPOSAL_EMITTED` | The problem is fully specified, but CORE lacks the *capability* to solve it | Anna finishes in 3 h, Ben in 6 h → reciprocal work-rate, CORE has no solver for that yet |

These must never be conflated:

- **Asking a question** says: *the problem is knowable; I need one more datum from
  the world.*
- **Emitting a proposal** says: *the problem is knowable; I need one more organ
  from engineering.*

Confusing them would let the engine ask users for things the users already told
it, or propose capability additions for problems it could solve if it just asked.
The blocking reason from the failure family is the gate: if the failure family
signals *missing input*, route to `QUESTION_NEEDED`; if it signals *missing
solver*, route to `PROPOSAL_EMITTED`.

---

## 1.5 — The pre-question limitation pass (session refinement)

A refinement raised later in the same session. The trigger question:

> Do we have anything, in the process of contemplation and asking the question,
> about identifying the **limitations** of what the contemplation is *about*?

Yes — and it must be explicit, and it must come **first**. Before contemplation
asks anything, it must identify *the limits of the contemplated situation*. A
question is only one of several dispositions, and asking is wrong unless the
limitation is specifically the kind a question resolves. Otherwise CORE can ask
something grammatical but epistemically wrong — too broad, out of scope, aimed at
the wrong gap, or naming what it never grounded.

So the first contemplative move is **not** *"what question do I ask?"* It is:

```text
What is preventing resolution — and what KIND of limitation is it?
```

### 1.5.1 Why this is load-bearing — it is CORE's intake gate

This is bigger than asking tidy questions. **Limitation assessment is the gate on
CORE's ability to receive necessary information at all.** Get the classification
wrong and the intake path blocks in one of two dangerous ways:

| Failure | What goes wrong | Cost |
|---|---|---|
| **Refuse when it should ask** (`missing_information → terminal refusal`) | CORE never receives the one fact that would make the problem solvable | a *structural* inability to take in the unlocking datum — not a clumsy answer, a lost capability |
| **Ask when it should propose** (`capability_gap → question`) | CORE asks for something the user already supplied / cannot supply | the intake channel is wasted and the user is misled about what's missing |

Example of the first (must ask, not refuse):

```text
Anna and Ben work together. Anna paints 3 rooms/hour. How many rooms in 4 hours?
  bad:     "I cannot solve this."         (refuses → never receives Ben's rate)
  correct: "What is the second person's painting rate in rooms per hour?"
```

Example of the second (must propose, not ask):

```text
Anna can finish in 3 hours. Ben can finish in 6 hours. How long together?
  bad:     "What is Anna's rate?"          (the info is present; asking is wrong in KIND)
  correct: deferred-capability proposal (reciprocal work-rate); no question
```

**The key phrase to pin in the Q1 scope:**

> Question-asking is the intake mechanism for resolvable missing state.
> Limitation assessment is the gate that determines whether intake is appropriate.

That is what keeps a CORE question from collapsing into generic clarification, and
makes intake part of the deterministic reasoning loop rather than a chat reflex.

### 1.5.2 The flow

The question organ is **downstream** of limitation assessment — not
`failure → question`, but `failure → limitation assessment → question only when appropriate`:

```text
problem / situation
  → contemplate (organ attempts + domain-precedence adjudication)
  → identify the terminal limitation          ← the new pass
  → classify the limitation kind
  → choose a resolution action (answer / ask / propose / refuse / report / step aside)
  → if ask:  derive missing slot → check renderability → render minimal sufficient question
     else:   refuse / propose / report / narrow scope / step aside
```

### 1.5.3 The limitation inventory

Only one of these kinds becomes a question. The rest are *not* questions by default.

| Limitation kind | Meaning | Disposition | Example |
|---|---|---|---|
| `missing_information` | a needed datum is absent from the input | **ask** | only one of two rates given → "What is the second rate?" |
| `ambiguous_structure` | the data is present but the relationship is unclear | **ask** | two rates, no cue → "together, opposing, or separate?" |
| `scope_boundary` | the ask exceeds current capability/evidence | **explain (scope)** | "solve *all* combined-rate problems?" → state the v1 envelope |
| `capability_gap` | the info is present; CORE lacks the transform | **propose** | reciprocal work-rate → proposal, not question |
| `hard_boundary` | mathematically/logically impossible or undefined | **refuse** | net rate 0 → refuse, no question |
| `contradiction` | evidence conflicts with a claimed answer | **report** | derived 20 vs key 18 → report (ask only via a later source-authority lane) |
| `renderability_gap` | asking is right, but terms aren't grounded enough to ask safely | **ask generic / refuse-to-name** | unnamed 2nd painter → "the second person's rate", never "Ben's" |
| `input_shape` | not this organ's domain | **step aside** | single-rate text reaching CMB → cede to R3 |

### 1.5.4 The model

```python
LimitationKind = Literal[
    "missing_information", "ambiguous_structure", "scope_boundary",
    "capability_gap", "hard_boundary", "contradiction",
    "renderability_gap", "input_shape",
]

ResolutionAction = Literal[
    "answer", "ask_question", "emit_proposal",
    "refuse_known_boundary", "report_contradiction", "step_aside",
]

@dataclass(frozen=True)
class LimitationAssessment:
    limitation_kind: LimitationKind
    epistemic_state: EpistemicState           # reuse core/epistemic_state.py — not a new enum
    resolution_action: ResolutionAction
    owner_organ: str | None
    blocking_reason: str                       # the failure-family key (the partition key)
    grounded_terms: tuple[str, ...]            # what the trace actually grounded (renderability source)
    missing_slots: tuple[MissingSlot, ...]
    unsupported_capabilities: tuple[str, ...]
    contradictions: tuple[str, ...]
    scope_boundary: str | None
```

The `epistemic_state` / `resolution_action` split keeps state ("I do not have
enough information" = `UNDETERMINED`) distinct from action ("ask the minimal
sufficient question" = `ask_question`).

### 1.5.5 The intake rule — ask only when ALL of these hold

```text
1. The limitation is missing or ambiguous external/problem information.
2. The missing slot is typed.
3. The expected answer form is known.
4. The question can be rendered from grounded terms only.
5. The answer, if provided, would re-enter the gate and could unblock solving.
```

If any fail: refuse, report, propose, narrow scope, or step aside — do **not** ask.

### 1.5.6 This is bigger than math (lived / agentic intake)

The same gate governs intake for any goal-directed situation:

```text
No goal        → ask for the goal.
No constraint  → ask for the constraint.
No observation → ask what happened.
No source      → ask which source to trust.
No metric      → ask what success means.
Capability gap → do NOT ask; propose / build capability.
Hard boundary  → do NOT ask; refuse / report the boundary.
```

Without limitation assessment, CORE cannot properly *receive* information, because
it does not know what kind of information is admissible or useful. This is why the
organ lives in `core/` — intake discipline is general-intelligence infrastructure,
not a math feature.

### 1.5.7 Implementation discipline (notes added in review)

Three sharp edges to honour when this is built, so the refinement does not create
new hazards:

- **`LimitationAssessment` is a *consolidating view*, not a fourth taxonomy.** We
  already encode disposition in three overlapping places: the **failure-family
  registry** (`must_remain_refused` / `proposal_allowed` / `input_shape` /
  `owner`), the **contemplation terminals** (`SOLVED_VERIFIED` /
  `REFUSED_KNOWN_BOUNDARY` / `PROPOSAL_EMITTED` / `CONTRADICTION_DETECTED` / …),
  and now `LimitationKind` / `ResolutionAction`. `ResolutionAction` ≈ the terminal
  set we already ship; `LimitationKind` ≈ the *why* the failure family half-encodes.
  The pass must **derive** disposition from those and *unify* them — adding only the
  genuinely new `ask_question` and the `renderability_gap` guard — never stack a
  parallel fourth source of truth (CLAUDE.md: no parallel correction/decision paths).
  Concrete mapping to the shipped registry:

  ```text
  hard_boundary    ← must_remain_refused math/logic families (cmb_non_positive_net, cmb_non_integer, …)
  ambiguous_struct ← must_remain_refused ambiguity families  (cmb_combine_ambiguous)
  missing_info     ← must_remain_refused underdetermined      (cmb_underdetermined, rate_underdetermined)
                     AND (see next note) the proposal_allowed missing_* families
  capability_gap   ← proposal_allowed capability families     (cmb_unsupported_*, unsupported_rate_duration)
  contradiction    ← answer_key_contradiction
  input_shape      ← input_shape (step_aside)
  ```

- **Introducing `ask` re-audits the *shipped* failure families, and it cuts both
  ways.** It splits `must_remain_refused` (the math/contradiction families stay
  hard-refuse; the ambiguous/underdetermined-*input* families become **ask** — and
  per the intake argument above, a refuse-when-should-ask there is a real loss, not
  a label quibble). It also pulls from `proposal_allowed`: `missing_total_count` /
  `missing_weighted_total` are *missing-information* (the user could state the
  total), not *capability gaps* — once `ask` exists they look mis-classified and
  should ask, not propose. This is a real change to shipped behaviour, so it is
  **scope-it-don't-silently-re-key** territory, decided in the Q1 derivation slice
  with tests, not edited into the registry in passing.

- **`renderability_gap` is a first-class limitation, and the guard is the
  question-equivalent of "no fabricated source":** *a question may not name an
  entity, slot, unit, or relation that was not grounded in the attempted
  comprehension trace.* When `grounded_terms` lacks the field a template needs,
  degrade to a generic question or emit `question_unrenderable` — never a named
  guess. This is exactly the surface where the CMB reader's adversarial passes kept
  catching real wrong=0 bugs; the same discipline applies to asking.

### 1.5.8 Where this meets Stage 2 (the disclosure bus)

This is the off-serving mirror of the Stage 2 served-surface bus. The bus maps:

```text
EpistemicState + LimitationAssessment → ServedDisposition

  VERIFIED                          → disclose answer (widened reach)   ← Stage 2 v1 (only one implemented)
  UNDETERMINED + missing_information → ASK_QUESTION                      ← reserved (Q1 tenant)
  UNDETERMINED + capability_gap      → PROPOSAL                         ← reserved
  UNDETERMINED + scope_boundary      → SCOPE_BOUNDARY disclosure        ← reserved (RESERVED EpistemicState)
  CONTRADICTED                       → REPORT_CONTRADICTION             ← reserved
```

So Stage 2 should be scoped *generally* enough to reserve these dispositions (so a
question is governed for the surface exactly as an answer is), while implementing
only `VERIFIED` first. `QUESTION_NEEDED` then becomes the second tenant on the same
bus: `LimitationAssessment(missing_information) → QUESTION_NEEDED → render → bus`.

---

## 2. The organ — `core/epistemic_questions/`

Located in `core/` (not `generate/`) because question articulation will
eventually apply across math, language, modality, planning, memory, UI, and the
lived-loop — not only comprehension.

```text
core/epistemic_questions/
  model.py        — typed data model (EpistemicQuestion, MissingSlot, AnswerBinding)
  derive.py       — failure-family → missing-slot → EpistemicQuestion
  render.py       — deterministic template rendering of the natural-language prompt
  rank.py         — (Q2+) rank multiple candidates, pick minimal sufficient question
  answer_bind.py  — (Q2) typed slot binding after user answer
```

### 2.1 Data model

```python
QuestionKind = Literal[
    "missing_value",
    "missing_unit",
    "ambiguous_referent",
    "ambiguous_operation",
    "missing_time_interval",
    "missing_category",
    "missing_rate",
    "missing_query_target",
    "contradiction_resolution",
    "scope_boundary",
]

@dataclass(frozen=True)
class MissingSlot:
    name: str                    # the slot identifier (e.g. "rate_b")
    role: str                    # its semantic role (e.g. "second_combined_rate")
    entity: str | None           # the referent entity (e.g. "Ben")
    unit: str | None             # expected unit (e.g. "rooms/hour")
    constraints: tuple[str, ...] # what this slot must satisfy

@dataclass(frozen=True)
class EpistemicQuestion:
    id: str
    source_attempt_id: str
    question_kind: QuestionKind
    missing_slot: MissingSlot
    prompt: str                  # deterministic rendered text; never improvised
    expected_answer_type: AnswerType
    expected_unit: str | None
    owner_organ: str             # which reader/solver will consume the answer
    blocking_reason: str         # the failure-family key
    resolves: tuple[str, ...]    # slot names this answer will unlock
    priority: int                # lower = ask first

@dataclass(frozen=True)
class AnswerBinding:             # reserved in Q1; implemented in Q2
    question_id: str
    target_organ: str
    target_slot: str
    parser: str                  # which typed parser handles the raw answer
    unit: str | None
```

All dataclasses are **frozen** (deterministic, hashable, replayable) — consistent
with the determinism doctrine throughout CORE.

### 2.2 Example artifact

```json
{
  "question_kind": "missing_rate",
  "missing_slot": {
    "name": "rate_b",
    "role": "second_combined_rate",
    "entity": "Ben",
    "unit": "rooms/hour",
    "constraints": ["positive_integer"]
  },
  "prompt": "What is Ben's painting rate in rooms per hour?",
  "expected_answer_type": "positive_integer_rate",
  "owner_organ": "combined_rate_comprehension",
  "blocking_reason": "cmb_missing_second_rate",
  "resolves": ["rate_b"],
  "priority": 100
}
```

The `prompt` is not generated by an LLM. It is rendered by `render.py` from a
deterministic template keyed on `blocking_reason`, with required fields drawn
from the `MissingSlot`. If required fields are absent, `render.py` emits
`question_unrenderable` — **it does not hallucinate**.

---

## 3. Derivation — failure family to question

Questions are not generated by the reader directly. The flow is:

```text
reader / router / contemplation
→ ComprehensionAttempt
→ FailureFamily
→ MissingSlot
→ EpistemicQuestion
```

This means `derive.py` consumes *already-typed failure state*. It does not
re-read the problem text. That keeps question generation deterministic and
failure-family-scoped — it cannot ask about things it has not already identified
as missing through the typed comprehension path.

### 3.1 The ask/don't-ask decision is per family

Not every failure family should produce a question. The decision table for the
initial set (Q1):

| Failure family | Ask? | Why |
|---|---|---|
| `cmb_missing_second_rate` | ✅ | Input incomplete; one rate datum is missing |
| `cmb_combine_mode_ambiguous` | ✅ | Input ambiguous; operation choice is underspecified |
| `r1_ambiguous_referent` | ✅ | Referent resolution blocked by pronoun without antecedent |
| `r2_missing_weighted_total` | ✅ | A required aggregate is not given |
| `r2_missing_total_count` | ✅ | A required count is not given |
| `r3_missing_rate` | ✅ | Rate datum absent from problem text |
| `non_integer_solution` | ❌ | Mathematical exactness boundary; asking changes nothing |
| `non_positive_net_rate` | ❌ | Mathematical boundary; not a missing-input problem |
| `rate_unit_mismatch` | ❌ (for now) | Ask deferred until dimension registry exists |
| `answer_key_contradiction` | ❌ | Report contradiction; do not ask unless source-authority lane exists |
| `cmb_reciprocal_work_rate_deferred` | ❌ → `PROPOSAL_EMITTED` | Capability gap, not input gap |

The ask/don't-ask decision is **a property of the failure family**, not a
runtime heuristic. It is a closed, tested mapping.

### 3.2 Template table (Q1 scope)

```text
cmb_missing_second_rate:
  required: [missing_agent, rate_unit]
  template: "What is {missing_agent}'s rate in {numerator} per {denominator}?"

cmb_combine_mode_ambiguous:
  required: [rate_a_entity, rate_b_entity]
  template: "Are {rate_a_entity} and {rate_b_entity} working together,
             opposing each other, or separately?"

r1_ambiguous_referent:
  required: [pronoun, candidates]
  template: "Who or what does '{pronoun}' refer to: {candidates}?"

r2_missing_weighted_total:
  required: [unit]
  template: "What is the total number of {unit}?"

r2_missing_total_count:
  required: [entity_class]
  template: "How many {entity_class} are there in total?"

r3_missing_rate:
  required: [entity, rate_unit]
  template: "What is {entity}'s rate in {rate_unit}?"
```

Templates are data, not code. They are validated at load time. A template with a
missing required field at render time produces `question_unrenderable` — a typed
failure, not a crash or improvisation.

---

## 4. The new contemplation terminal: `QUESTION_NEEDED`

The contemplation pass manager gains a new terminal state:

```python
terminal: Literal[
    ...,
    "PROPOSAL_EMITTED",   # existing: missing capability
    "QUESTION_NEEDED",    # new: missing input datum
    "CONTRADICTION_DETECTED",  # (planned: contradiction report)
]
```

The epistemic state / resolution action split is:

```text
epistemic_state: UNDETERMINED
resolution_action: ASK_QUESTION
terminal: QUESTION_NEEDED
artifact: EpistemicQuestion(...)
```

`QUESTION_NEEDED` is not a subtype of `PROPOSAL_EMITTED`. They are sibling
terminals. The distinction is real and must be preserved in every downstream
consumer (the servability blade, the surface realizer, the teaching corridor).

The `ContemplationResult` (or the relevant terminal object) carries the question
artifact when the terminal is `QUESTION_NEEDED`, just as it carries the proposal
artifact when the terminal is `PROPOSAL_EMITTED`.

---

## 5. How question-asking becomes active problem solving

The full loop, once Q2 (answer binding) exists:

```text
1. Attempt solution
2. Detect blocked state → FailureFamily
3. Identify missing slot → MissingSlot
4. Generate minimal sufficient question → EpistemicQuestion
5. Surface question to user (via ServabilityBlade mode = "clarify")
6. User answers
7. AnswerBinding: parse typed answer → bind to target slot
8. Re-run owner organ with augmented problem
9. Resume solving
```

Steps 1–5 are Q1. Steps 6–9 are Q2. **Q1 must design the artifacts for Q2** —
specifically: `expected_answer_type`, `owner_organ`, and `target_slot` must be
present in the Q1 `EpistemicQuestion` even before binding is implemented, so Q2
does not require an artifact-schema migration.

The same loop generalises past math:

| Domain | Example failure | Minimal question |
|---|---|---|
| Math (combined rate) | `cmb_missing_second_rate` | "What is Ben's rate in rooms per hour?" |
| Business problem-solving | `missing_objective_metric` | "What outcome are you trying to improve first: revenue, profit, retention, or workload?" |
| Debugging | `missing_observed_failure` | "What error message or failing behavior do you see?" |
| Planning | `missing_target_goal` | "What is the target event or outcome?" |
| Language referent | `r1_ambiguous_referent` | "Who does 'they' refer to?" |

The organ is the same in all cases. Only the failure families and templates
differ. This is why `core/epistemic_questions/` is not inside `generate/` — it
is general-intelligence infrastructure.

---

## 6. Why question generation must be deterministic

The whole CORE architecture rests on determinism and replayability
(CLAUDE.md: "prefer inspectable state, provenance, and deterministic replay over
impressive-looking but ungrounded outputs"). The same obligation extends to
question generation:

- **No freeform improvisation.** The renderer never calls an LLM to generate the
  question text. It fills a template from typed slot data.
- **No hallucination.** If a required template field is absent, `render.py`
  returns `question_unrenderable` — a typed, auditable failure — rather than
  substituting a guess.
- **No multi-question improvisation.** Q1 emits at most one question per
  contemplation pass. Ranking (`rank.py`) is Q2+. Dialogue management is later
  still.
- **Replayable.** Same `ComprehensionAttempt` + same failure family → same
  `EpistemicQuestion`, always.

This is how *asking a question* remains a cognitive operation rather than a
conversational habit.

---

## 7. Proposed Q1 PR ladder

### Q1-a — Question artifact model
`core/epistemic_questions/model.py` + `tests/test_epistemic_question_model.py`

No contemplation integration. Tests cover: deterministic serialization, stable
id/hash, no empty prompt, `expected_answer_type` required, `owner_organ`
required.

### Q1-b — Failure-family → missing-slot derivation
`core/epistemic_questions/derive.py` + `tests/test_epistemic_question_derivation.py`

Maps the initial 6–8 failure families (ask/don't-ask table in §3.1). Tests
include one case per mapped family proving the right terminal is selected, and
one case per non-asking family proving no question is emitted.

### Q1-c — Deterministic template renderer
`core/epistemic_questions/render.py` + `tests/test_epistemic_question_rendering.py`

Tests: correct prompt for each template, `question_unrenderable` when required
fields absent, no improvisation possible (no LLM call path).

### Q1-d — Contemplation terminal
`generate/comprehension_contemplation/pass_manager.py` (or equivalent)

Add `QUESTION_NEEDED` as a terminal. Wire two or three routed examples
(`cmb_missing_second_rate`, `cmb_combine_mode_ambiguous`,
`r1_ambiguous_referent`). Tests: terminal state correct, artifact present, no
impact on existing `PROPOSAL_EMITTED` and `REFUSED` paths.

### Q1-e — Analysis doc
`docs/analysis/epistemic-question-articulation-v1-2026-06-08.md`

Non-claims explicitly stated:
- No freeform clarification.
- No multi-question dialogue manager.
- No answer binding (Q2).
- No serving change.
- No self-modification.

---

## 8. Q1 acceptance criteria

After Q1, CORE must be able to demonstrate:

```text
cmb_missing_second_rate
  → QUESTION_NEEDED
  → "What is Ben's painting rate in rooms per hour?"
  → no proposal emitted, no answer guessed

cmb_combine_mode_ambiguous
  → QUESTION_NEEDED
  → "Are the two rates working together, opposing each other, or separately?"

r1_ambiguous_referent
  → QUESTION_NEEDED
  → "Who does 'they' refer to?"

r2_missing_weighted_total
  → QUESTION_NEEDED
  → "What is the total number of [unit]?"

cmb_reciprocal_work_rate_deferred
  → PROPOSAL_EMITTED
  → no question

answer_key_contradiction
  → CONTRADICTION_DETECTED (or existing refusal)
  → no question
```

And across all cases:

```text
R1 / R2 / R3 / CMB serving: unchanged
wrong=0: intact
proposal-only teaching: unchanged
GSM8K lane SHAs: pinned and unchanged
```

---

## 9. How this connects to the servability blade

The `EpistemicQuestion` artifact is the bridge between the attempt layer (PRA)
and the `ServabilityBlade` from the previous discussion:

```text
ProblemAttemptSession
  → terminal = QUESTION_NEEDED
  → EpistemicQuestion artifact
        │
        ▼
   ServabilityBlade
  → mode = "clarify"
  → required_disclosures = [the question prompt]
  → servable_claims = []        (no answer claimed; none exists yet)
        │
        ▼
   surface: "What is Ben's painting rate in rooms per hour?"
```

The blade's `"clarify"` mode was designed exactly for this case. The question
organ is what *produces* the artifact the blade routes. Together they close the
loop: **underdetermined → type the gap → ask the minimal question → blade routes
it honestly → solve on reply.**

---

## 10. What comes after Q1

**Q2 — Answer binding.** The user replies; a typed parser extracts the value;
`AnswerBinding` maps it to the `target_slot` in the `owner_organ`; the organ
reruns with the augmented problem. For the Ben painting example:

```text
Question:  "What is Ben's painting rate in rooms per hour?"
Answer:    "2"
Binding:   rate_b = 2 rooms/hour  (typed PositiveIntegerRate)
Rerun:     effective_rate = 3 + 2 = 5 rooms/hour
           quantity = 5 × 4 hours = 20 rooms
```

That is when question-asking becomes active problem solving, not just surface
decoration.

**Q3+ — Multi-question ranking.** When multiple missing slots exist,
`rank.py` selects the minimal sufficient question (prefer one-slot numeric over
broad; prefer questions that unblock an existing solver; prefer questions with
known unit/type; do not ask when contradiction should be reported instead).

**Longer term.** The same organ applies across domains beyond math — business
problem-solving, debugging, planning, language referent resolution — because
`question_kind` and `MissingSlot` are not math-specific. The failure-family
table grows; the template table grows; the core machinery is the same.

---

## Bottom line

The first real skill of contemplation is:

```text
I cannot solve this because slot X is missing.
The minimal question that unblocks me is Y.
I expect an answer of type Z.
If answered, I know exactly where to bind it.
```

That is a **typed, deterministic, failure-family-driven operation** — not
thinking, not explaining, not guessing. Not a chatbot habit. A cognitive act with
provenance, a binding target, and a defined resolution path.

The proposal is `core/epistemic_questions/` (Q1: model + derive + render +
terminal integration), followed by `answer_bind.py` (Q2). The full loop — attempt
→ detect blocked state → articulate the gap → ask the right question → bind the
answer → solve — is the simplest real reasoning loop CORE can run.
