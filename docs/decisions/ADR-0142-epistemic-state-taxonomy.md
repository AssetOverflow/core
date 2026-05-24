# ADR-0142: Epistemic State Taxonomy — First-Class Vocabulary

**Status:** Accepted (integration deferred pending ADR-0144)
**Date:** 2026-05-24
**Supersedes:** none
**Related:** [epistemic-state-taxonomy-scope](./epistemic-state-taxonomy-scope.md), ADR-0021 (teaching safety), ADR-0024 (refusal materialisation), ADR-0144 (PropositionGraph integration — gate for full cross-subsystem wiring)

---

## Context

CORE's thesis commits the engine to *decoding* a reality that already is, not
generating plausible continuations. Decoding requires the engine to hold
propositions in varying degrees of grounding — not "true" vs "false" but a
richer vocabulary describing *how* a proposition is currently known and *what
evidence* supports that knowing.

Without an explicit vocabulary, the engine implicitly caps its epistemic scope
at binary admit/refuse. Six subsystem audits (math, vault, language packs,
runtime packs, teaching pipeline, cognition pipeline, and chat runtime — 136
total decision points) confirm that the engine already makes implicit epistemic
distinctions across all of these subsystems: it distinguishes exact recall
from decomposed recall, curated pack data from dynamically composed units,
reviewed teaching chains from speculative candidates, and refusals caused by
evidence absence from refusals caused by safety/ethics violations. The audits
show these distinctions are consistent enough to unify under a single taxonomy.

## Decision

Ratify the following 14-state epistemic vocabulary as the engine's first-class
epistemic axis. Every proposition the engine reasons about carries exactly one
of these states, plus structured provenance (see Provenance Requirements below).

| State | Meaning | Primary source |
|---|---|---|
| **PERCEIVED** | Token/span observed in input; not yet committed to meaning | Raw ingestion |
| **EVIDENCED** | Feature lifts from specific input spans bind a proposition | Recognition layer |
| **EVIDENCED-INCOMPLETE** | Feature lift succeeded for a sub-span but the proposition is structurally partial — lift did not fail, but no consuming proposition exists yet | Recognition layer — partial structural match |
| **VERIFIED** | Cross-checked against ratified knowledge (pack / vault / teaching); consistent | Substrate cross-reference |
| **DECODED** | VERIFIED plus replay-equality from input (trace-hash invariant) | Replay machinery |
| **DECODED-UNARTICULATED** | Proposition is DECODED internally but surface realization path broke; the answer is correct but cannot be communicated. Must not be classified as `wrong` | Verifier pass + Realizer failure |
| **INFERRED** | Derived from DECODED components by a ratified deterministic rule; composite not itself curated | Rule application over DECODED primitives |
| **UNVERIFIED-POSSIBLE** | Consistent with verified knowledge but not directly verified; usable provisionally | Default for non-contradicting novel propositions |
| **UNVERIFIED-NOVEL** | Not contradicted; introduces structure the engine has not decoded yet; candidate for teaching expansion | OOV refusal pointing at expansion need |
| **CONTRADICTED** | Conflicts with verified knowledge; refuse unless this is a ratified correction | Verification failure |
| **AMBIGUOUS** | Input could support multiple incompatible propositions; engine cannot choose without more context | Multi-evidence-binding conflict at recognition |
| **UNDETERMINED** | Feature lifts could not complete; specific dimensions missing | Recognition-layer refusal |
| **SCOPE_BOUNDARY** | Proposition type recognized but outside current capability envelope. Distinct from UNDETERMINED (lift succeeded) and CONTRADICTED (no conflict — engine cannot decode yet) | Capability-envelope check |
| **COMPUTATIONALLY_BOUNDED** | Engine cannot determine epistemic status within resource envelope; not AMBIGUOUS, not UNDETERMINED | Search/enumeration resource-limit hit |

Plus one meta-state:

| **EPISTEMIC_STATE_NEEDED** | None of the existing states fit; engine refuses and surfaces the gap for teaching expansion | Recursive refusal |

The meta-state is what makes the vocabulary non-capping. When no existing state
fits, the engine refuses with a structured description of the gap; the teaching
loop either ratifies a new state or determines an existing one covers the case.

## Companion axis: Normative clearance (orthogonal)

Safety and ethics verdicts are **not epistemic states**. They answer a
different question: *has this turn's behavior complied with the active
constraints?* The two axes are orthogonal — a VERIFIED proposition can violate
a safety boundary; an UNDETERMINED proposition can pass every ethics predicate.

Every proposition reaching `ChatResponse` or `TurnEvent` carries both axes:

| Clearance state | Meaning |
|---|---|
| **CLEARED** | All active normative constraints (safety + ethics) passed |
| **VIOLATED** | At least one constraint breached; audit record written |
| **UNASSESSABLE** | Constraint exists but cannot be evaluated at runtime |
| **SUPPRESSED** | A refusal commitment fired; proposition replaced with typed refusal before reaching the surface |

`normative_detail` carries the violated boundary/commitment IDs when clearance
is VIOLATED or SUPPRESSED; empty string otherwise.

## Provenance requirements

Every assignment of a state to a proposition must carry structured provenance:

- **Source:** which subsystem assigned this state
- **Evidence span(s):** which input or knowledge spans supported the assignment
- **Transition history:** if the proposition was previously in another state, what evidence caused the transition

Provenance is what distinguishes thesis-aligned epistemic tracking from
confidence scores. A confidence score is a number; provenance is a trace the
engine can replay, audit, and correct.

*Full provenance enforcement is deferred to ADR-0144 integration. Phase 3
(this ADR) establishes the vocabulary and wires state labels onto runtime
artifacts. Phase 4 (post ADR-0144) adds structured provenance records.*

## What Phase 3 delivers (already landed)

The following is implemented and merged:

- `core/epistemic_state.py` — `EpistemicState` and `NormativeClearance` enums,
  `clearance_from_verdicts()`, `epistemic_state_for_grounding_source()`,
  `normative_detail_from_verdicts()`, `coerce_*` helpers.
- `core/physics/identity.py` — `TurnEvent` carries `epistemic_state`,
  `normative_clearance`, `normative_detail`.
- `chat/runtime.py` — `ChatResponse` carries all three fields; both stub and
  main paths populate them from verdicts and grounding source.
- `chat/telemetry.py` — serializes state axes into JSONL turn events.
- `language_packs/loader.py` — `UnitEntry` carries `epistemic_state`; curated
  entries tagged DECODED, composition-rule entries tagged INFERRED.
- `vocab/manifold.py` — `add()` accepts `epistemic_state`; `add_transient()`
  tags words UNVERIFIED_NOVEL; `epistemic_state_for_word()` exposed.
- `language_packs/compiler.py` — passes `epistemic_state` through compile,
  clone, and cached-load paths.
- `vault/store.py` — `epistemic_state_for_vault_status()` mapping;
  `epistemic_state` stamped into metadata on `store()`; recall results expose
  the field.
- Phase 2 bug fixes (PR #219): FALSIFIED/SPECULATIVE explicitly distinguished
  in `_status_admits`; `mean_pair_score([])` returns NaN; `RealizerError` on
  verified trace routes to `decoded_unarticulated` outcome; domain contract
  `present=False` is `valid=True`; `domain_id:unknown` routes to
  `scope_boundary`.

## What remains gated on ADR-0144

- **Cross-subsystem transition machinery.** How a proposition carries its state
  and provenance as it moves between subsystems (recognition → verifier → vault)
  requires the `PropositionGraph` as the carrier. ADR-0144 defines that graph.
- **Structured provenance records.** Per-assignment provenance objects (source,
  span, transition history) add overhead that needs the PropositionGraph as a
  home before they can be allocated.
- **`CognitiveTurnResult.refusal_reason` materialisation.** The field is
  populated by ChatRuntime (PR #222) but the cognition pipeline does not yet
  read it back for trace folding. Full wiring is post-ADR-0144.
- **State storage layer.** Where states are persisted per-session vs.
  per-proposition vs. in the vault is an open question (see scope doc Q2).

## Implementation debts to resolve before full cross-subsystem integration

From the six-subsystem audit:

1. **Cognition pipeline cold-start PASSTHROUGH** (`pipeline.py:_ratify_intent`)
   collapses three distinct conditions (no field_state, no vocab, no
   prompt_versor) into one indistinguishable `PASSTHROUGH` outcome. Extend
   `RatificationOutcome` to distinguish them.

2. **Chat runtime grounding-source dispatcher** (`runtime.py:831–1012`) does
   not record which sources were attempted or why each fell through. Six
   provenance gaps cluster around this site. Add an explicit dispatch trace
   structure once the PropositionGraph carrier exists.

3. **Teaching pipeline watched-metrics tuple** (`replay.py`) should be a named,
   versioned `MetricSet` dataclass to survive future metric additions without
   breaking trace byte-identity.

## Consequences

- The vocabulary is non-negotiable going forward. New subsystem work must assign
  one of these states (or emit EPISTEMIC_STATE_NEEDED) to every proposition it
  handles.
- The normative clearance axis is orthogonal. Safety/ethics machinery must not
  modify epistemic state and must not be expressed as an epistemic state.
- DECODED is the strongest positive state the engine can assign. VERIFIED is one
  step below it (cross-checked but not yet replay-equal). Nothing stronger than
  DECODED is defined; the engine does not claim certainty beyond replay equality.
- EPISTEMIC_STATE_NEEDED is the escape hatch that keeps the taxonomy from
  capping the engine's scope. Every EPISTEMIC_STATE_NEEDED emission is a
  teaching opportunity.
