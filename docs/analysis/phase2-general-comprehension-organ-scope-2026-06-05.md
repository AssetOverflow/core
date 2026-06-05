# Phase 2 — The General Comprehension Organ (scope, not build)

**Status:** SCOPE — no code. This is the scope-before-build for the make-or-break
phase of the AGI-candidacy roadmap
([AGI-candidacy-autonomous-improvement-roadmap-2026-06-05.md](./AGI-candidacy-autonomous-improvement-roadmap-2026-06-05.md)).
Phase 1 (MEASURE — the cross-domain capability index) is landed (#575); this
document scopes Phase 2 (COMPREHEND) so the first increment can be built TDD
without falling into the per-domain-matcher overfit trap that would fake the
capability number.

**Reviewer note:** I am the eyes on the implementation; the architectural
decision in §4 is presented with a recommendation for design review. Nothing
here is committed beyond this document.

---

## 1. Why this phase is the gate

The roadmap's loop is `COMPREHEND → REALIZE → REASON/GROUND/RECALL → RESPOND
(assert/estimate/refuse) → PROPOSE → HITL → ACCUMULATE → measurably more
capable → repeat`. Every later phase consumes the output of COMPREHEND. If
comprehension is narrow, the whole organism is narrow no matter how good the
reasoners are. This is exactly what the GSM8K serving numbers were telling us:
~92% **refused** is not a reasoning failure, it is a **comprehension** failure —
the engine could not turn the prose into a structure the reasoner could touch.

**The one-line gap:** CORE can *reason* over structured input in several
domains, and it can *articulate* a response from field resonance, but it has
**no organ that turns arbitrary natural language into reasoning-ready
structure.** The reasoning side and the articulation side never connect.

---

## 2. The honest substrate map

### 2a. The articulation side (chat) — shallow comprehension, aimed at responding

| Module | What it actually does |
| --- | --- |
| `generate/proposition.py` :: `PropositionGraph` | "prompt and field form a relation blade; a frame is selected by exact CGA inner product against that relation; vocabulary points instantiate the frame slots." Frame-fill from field resonance. |
| `generate/graph_planner.py` | `PropositionGraph → ArticulationTarget` (topological walk → ordered articulation steps). This is the **output** path. |
| `generate/intent.py`, `generate/realizer.py` | intent classification + deterministic surface realization. |

This path is **general over input** but **shallow**: it selects a response
frame by field resonance and fills slots from vocabulary. It is built to
*respond*, not to *understand-for-reasoning*. Its `PropositionGraph` is **not**
a refusal-first, reasoning-ready meaning structure — and it shares a name with
the logic-side proposition representation (§2b), which we must not conflate.

### 2b. The reasoning side — strong reasoners, but they consume *structured* input

| Lane / module | Input it consumes | Meaning structure |
| --- | --- | --- |
| `evals/deductive_logic` (ROBDD) | **already-formal** facts + rules + query (JSON) | proof_chain proposition repr (ADR-0201/0202), canonicalizer, proof-graph-builder (ADR-0204), modus-ponens (ADR-0205) |
| `evals/relational_metric` (`generate/relational_field_reader`) | **narrow templated text** | tiny quantitative grammar: `fact / more_than / fewer_than / sum_of` |
| `evals/dimensional` | structured cases | unit/dimension analysis |
| GSM8K (`generate/derivation`, `generate/binding_graph`) | math word problems → `MathProblemGraph` | **binding-graph** (ADR-0132): the canonized NL↔reasoning interlingua |

### 2c. The binding-graph interlingua — neutral, but arithmetic-shaped

`generate/binding_graph/model.py` (ADR-0132) is described as "the typed compiler
boundary between natural language and symbolic reasoning," and INV-26 keeps it
**neutral** (it imports no engine/benchmark/domain code). That discipline is
exactly right. But:

- Its closed vocabularies are **arithmetic**: `SEMANTIC_ROLES = {entity,
  quantity, rate, duration, count, total, difference, ratio, unknown}`;
  `QUESTION_FORMS = {count, rate, total, difference, ratio, identity}`.
- Its only relational node is `BoundEquation` (`lhs := rhs`, quantitative) and a
  single-symbol `BoundConstraint` (`predicate` string). **There is no general
  n-ary relation / predicate node, no class-membership, no quantifier.**
- Its **only producer** is `generate/binding_graph/adapter.py`, which translates
  an *already-structured* `MathProblemGraph` — **not raw NL** — into the graph.

So the "interlingua" exists and is well-disciplined, but today it is the
**arithmetic word-problem** interlingua, fed by the math reader, never by a
general parser.

### 2d. The precise gap (the "missing middle")

```
            arbitrary NL prose
                   │
                   ▼
        ┌──────────────────────┐
        │  ???  GENERAL         │   ← Phase 2: this organ does not exist
        │  COMPREHENSION ORGAN  │
        └──────────────────────┘
                   │  (general meaning structure)
        ┌──────────┴───────────┐
        ▼          ▼           ▼
   binding-graph  proof_chain  relational/dimensional
   (quantities)   propositions  grammars
        │          │           │
        ▼          ▼           ▼
        the reasoners (already built, already independent-gold)
```

The reasoners are built. The yardstick is built. The articulation path is built.
**The general parser from prose into the reasoners' world is the unbuilt
make-or-break.**

---

## 3. Definitions made precise (carrying the corrected epistemic frame)

These align with the roadmap's epistemic foundation (honesty designed,
estimation learned) and the user's corrections.

- **Comprehend** = turn arbitrary input into a **structured meaning** keyed on
  general structure (syntax + grounding), not on domain word-lists. Output is a
  general meaning structure (§4), or a **refusal** — never a fabricated parse.
- **Realize** = integrate that meaning into the held self with an
  **EpistemicStatus** (told / coherent-with-evidence / verified). "Being told"
  is first-class: most knowledge arrives as told facts the engine realizes and
  earns the why/how over time. Realization is what makes intake recallable.
- **Intake** is first-class (NOT "no ingestion"): take in inputs, comprehend,
  realize as structured grounded memory it can recall. The ban is on **bulk
  indiscriminate absorption** into a database, not on ingesting knowledge.
- **Parse-or-refuse floor** = a statement comprehends iff its **structure** maps
  to the meaning structure via general rules **and** its **content** grounds
  (known lemmas, or honest typed unknowns). Anything else → refuse. This is how
  `wrong=0` holds *at the comprehension layer*: the engine never invents a
  reading it cannot ground. (Note: `wrong=0` here is the comprehension gear of
  the roadmap's "honesty designed in," not a universal law.)

**Non-goal restated:** comprehension does **not** include a guess organ. If the
structure or grounding is absent, it refuses. Estimation, where it ever applies,
is a *learned, ratified* competence built later (Phase 6), never designed into
the parser.

---

## 4. The architectural decision: what does comprehension emit?

This is the load-bearing decision and the reason to scope before building.
Meaning-structure today is spread across three substrates, none general:

1. **binding-graph** (quantities/equations) — math-shaped, INV-26 neutral.
2. **proof_chain propositions** (ADR-0201/0202) — logic-shaped.
3. **PropositionGraph** (`generate/proposition.py`) — field-resonance
   articulation, wrong tool, name-collision hazard.

To comprehend general declarative/interrogative prose across domains we need to
represent at least: **entities** (have), **n-ary named relations / predicates**
(*missing*), **class-membership / subsumption** (*missing*), **attribution /
properties** (*missing*), **quantified statements** (*missing*), **quantities &
equations** (have, in binding-graph), **logical connectives** (have, in
proof_chain).

### The options

- **Option A — extend the binding-graph's closed vocab** with general roles +
  an n-ary relation node + class/quantifier nodes.
  *Pro:* one canonized neutral meeting point; reuse refusal/provenance/canonical
  discipline. *Con:* bloats a structure designed for quantities into a
  god-structure; the closed-vocab ADRs explicitly say "extend deliberately in a
  future ADR"; couples logic/relations into the math interlingua.

- **Option B (recommended) — a general meaning structure that the existing
  structures *project into*.** Comprehension emits a **general claim/meaning
  graph** (working name `MeaningGraph`) sharing the binding-graph's discipline
  (frozen/slots, `SourceSpanLink` provenance, refusal-first, `to_canonical_string`,
  INV-neutral). A thin **projector** maps it to whichever reasoner's input shape
  (binding-graph for arithmetic, proof_chain propositions for logic, the
  relational grammar for relational_metric). The binding-graph and proof_chain
  propositions become **downstream projections**, not rivals.
  *Pro:* doesn't bloat math; keeps INV-26 (a neutral meeting point); reuses every
  existing reasoner unchanged; the general organ has one general target. *Con:* a
  new substrate to design — mitigated by building it **minimally, one class at a
  time**, per the defer-substrate-vocab discipline.

- **Option C — reuse `PropositionGraph`.** Rejected: it is field-resonance
  frame-fill for articulation, not refusal-first reasoning-ready structure.

### Recommendation

**Option B, built minimally and use-case-driven.** Do **not** pre-lock a full
general vocabulary (that violates the defer-substrate-vocab discipline). Instead:

> Introduce `MeaningGraph` carrying exactly the node kinds the **first increment**
> needs (entities + one general relation kind), with the binding-graph's
> refusal/provenance/canonical discipline and an INV firewall keeping it neutral.
> Every later class (subsumption, quantifier, attribution) is a deliberate,
> use-case-driven vocabulary extension with its own cross-domain proof.

The **field as a standing hand** (CL(4,1) inner product / incidence) is a
*candidate* for relation-consistency checks (transitivity, contradiction) — note
it, do **not** depend on it. The field-reasoner wedge found metric
reading-independence unproven and field-as-reasoner deferred; comprehension must
stand without it, and may later borrow it where it is geometrically honest.

---

## 5. The general reader architecture (how the organ works)

```
NL statement
   │
   ▼  (1) STRUCTURAL PARSE — keyed on SYNTAX, not domain words
        en_core_syntax_v1 (definitional layer, reviewed) supplies the
        general structural skeleton: subject–predicate–object, modifiers,
        quantifiers, connectives. Domain-agnostic.
   │
   ▼  (2) GROUNDING-FILL — content fills the skeleton
        entities/relations resolved against packs + vault (known lemmas) or
        marked as honest typed unknowns. Content is NEVER hard-coded per domain.
   │
   ▼  (3) PARSE-OR-REFUSE GATE
        emit MeaningGraph iff structure maps via general rules AND content
        grounds; otherwise REFUSE (typed, audited). No fabricated reading.
   │
   ▼  MeaningGraph  ──projector──▶  reasoner input (binding-graph / proposition / grammar)
```

The decisive design commitment: **step (1) keys on structure (syntax), step (2)
on grounding (packs/vault).** A class of statement comprehends because of its
*grammar*, which is domain-agnostic; the *content* that fills it varies by
domain. This is what makes the organ general rather than a pile of recognizers —
and it is exactly the property the overfit trap violates.

---

## 6. Cross-domain proof obligation & overfit-trap guardrails

The overfit trap: build a per-domain matcher that lifts one lane's coverage and
**fakes** the capability number. The Phase-1 yardstick was built precisely to
make this visible (geomean → 0 if any domain stays at zero), but the discipline
must be enforced at the comprehension layer too:

1. **Every comprehension *class* is proven on ≥3 distinct domains** with the
   *same grammar, different content* (e.g. binary relation "X R Y" over kinship,
   biology, geometry). Works in only one domain ⇒ it is a matcher ⇒ rejected.
2. **The Phase-1 capability index is the acceptance gate.** A comprehension
   increment is accepted only if `breadth` rises (or coverage rises across
   *multiple* domains' geomean), with `wrong_total == 0`. A one-domain bump that
   leaves the geomean flat is, by construction, not progress.
3. **Schema-defined proof obligation (CLAUDE.md rule).** The parse-or-refuse
   gate is load-bearing only if a test **meaningfully fails** when a fabricated
   reading is admitted. Each class ships with a refusal test that fails if the
   gate is loosened to admit an ungrounded parse.
4. **INV firewall for `MeaningGraph` neutrality** (sibling of INV-26): the
   structure imports no engine/benchmark/domain code, so two independent
   decodings can meet there honestly.
5. **No silent caps.** If an increment bounds coverage (clause types handled,
   grounding sources), it is logged — silent truncation reads as "general" when
   it is not.

---

## 7. Increment decomposition (build order)

Each increment is a small, load-bearing PR with the yardstick as its gate.

### 2a — `MeaningGraph` substrate + the first general class (binary relations), end-to-end
- `MeaningGraph` data model (frozen/slots, `SourceSpanLink` provenance,
  refusal-first, `to_canonical_string`, INV firewall) carrying **entities + one
  general n-ary relation node**.
- The structural reader (step 1–3) for **binary-relation declaratives** ("X R Y"),
  keyed on syntax via `en_core_syntax_v1`, grounded against packs/vault,
  parse-or-refuse.
- A projector `MeaningGraph → relational grammar` so the existing
  `relational_metric` reasoner consumes it unchanged (proves the projection
  pattern on a real reasoner).
- **Acceptance:** binary-relation comprehension proven on **≥3 distinct domains**
  on the capability index; `wrong_total == 0`; refusal tests bite; index digest
  recorded as the new baseline.

### 2b — widen relation classes (use-case-driven)
- Add class-membership / subsumption ("a raven is a bird", "all ravens are
  birds") with a projector into the proof_chain proposition repr so the
  **deductive_logic** reasoner consumes comprehended prose (closing the
  formal-input gap for the largest lane).
- Each class: ≥3-domain proof, wrong=0, refusal test, geomean must move.

### 2c — attribution / quantity bridges + loop-until-coverage
- Attribution ("the ball is red"), and the quantity bridge `MeaningGraph →
  binding-graph` so comprehended math prose reaches the GSM8K reasoner without
  the `MathProblemGraph` shortcut.
- Loop one class at a time until coverage stops rising (loop-until-dry), each
  cross-domain-proven.

---

## 8. Risks, invariants, non-goals

**Invariants preserved:** `versor_condition < 1e-6` (untouched — comprehension is
symbolic/structural, no field repair); exact CGA recall (no approximate match
introduced); `wrong=0` as the comprehension gear (parse-or-refuse); INV-26-style
neutrality extended to `MeaningGraph`; reviewed learning stays HITL (comprehension
feeds REALIZE/PROPOSE, never self-ratifies).

**Risks:**
- *Vocabulary creep* → mitigated by use-case-driven extension, one class at a
  time, each with its own ADR and proof (defer-substrate-vocab discipline).
- *`MeaningGraph` becoming a third orphan structure* → mitigated by the projector
  pattern: it must feed an existing reasoner from increment 2a, or it is not
  built.
- *Syntax-pack depth unknown* → `en_core_syntax_v1` is a lexicon/gloss pack, not
  a parser. 2a must establish how much general structural parsing it actually
  supports; if insufficient, the first sub-task is a minimal, collision-audited
  structural-parse capability (NOT a bulk grammar import — recall the #503 syntax
  revert).
- *Name collision* `PropositionGraph` (articulation) vs proof_chain propositions
  vs `MeaningGraph` → documented here; keep them distinct.

**Non-goals (this phase):** a guess/estimate organ (Phase 6, learned+ratified);
field-as-reasoner (deferred research); bulk corpus ingestion; touching the
serving GSM8K metric (this is additive — comprehension feeds reasoners, it does
not change their gold).

---

## 9. Open questions for design review

1. **Option B vs A** — do we accept a sibling `MeaningGraph` that existing
   structures project into, or extend the binding-graph in place? (Recommend B.)
2. **First class** — binary relations as 2a's first class, projecting into
   `relational_metric`? (Recommend yes: smallest general structure beyond
   entities, with an existing reasoner + reader to lift from.)
3. **Syntax-parse depth** — is `en_core_syntax_v1` enough for general structural
   parsing of declaratives, or does 2a need a minimal structural-parse capability
   first? (Needs a spike inside 2a before the reader is built.)
4. **Field standing-hand** — reserve CL(4,1) incidence as the relation-consistency
   checker for a later increment, or leave it out entirely until the wedge
   resolves? (Recommend: note, don't depend.)
