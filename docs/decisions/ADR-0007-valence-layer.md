# ADR-0007 — The Valence Layer

**Status:** Accepted  
**Date:** 2026-05-12  
**Authors:** AssetOverflow Architecture

---

## Context

The field energy operator (ADR-0006) gives every point in the semantic field a scalar magnitude — how activated it is. But magnitude alone does not describe the full character of semantic force. Language carries directionality, emotional charge, rhetorical power, polarity, relational orientation, and emphasis — none of which collapse to a single scalar.

A divine creative command and a curse can have identical energy magnitudes. A declaration of love and a declaration of war can be equally hot. What distinguishes them is not *how much* force is in play but *what kind* of force, *in which direction*, and *with what character*.

This is valence. It is orthogonal to energy. Together — a scalar energy and a valence vector — they form a complete description of the semantic force at any field point.

The standard NLP approach (sentiment analysis: positive / negative / neutral, scored -1 to +1) is a catastrophic lossy projection of this multi-dimensional structure onto a single axis. It discards force type, relational orientation, emphasis, polarity kind, and all the precision that Hebrew and Greek morphology encodes. It is also not Third Door — it is the most widely-used, most overfit, most interpretively biased layer in the existing NLP stack. We do not use it.

---

## Decision

We introduce the **valence layer** as a multi-channel vector attached to every field point and every `CandidateGeometricPressure` packet. Valence is not inferred by a downstream model — it is **lifted directly from the morphological and syntactic structure of the source material** by the language pack's lift rules.

### The Five Valence Channels

Each channel is independent. They compose a `ValenceBundle`.

#### Channel 1: Affective Valence

The emotional character of the semantic content. This is not a sentiment score. It is a **set of affect primitives** drawn from the field point's source material:

```
affective: Set[AffinePrimitive]

AffinePrimitive ∈ {
  joy, grief, fear, love, anger, awe, longing,
  tenderness, fierce_loyalty, lament, exultation,
  dread, peace, yearning, righteous_indignation
}
```

Some of these coexist in the same lexical item — *hesed* (Hebrew: loving-kindness, covenant loyalty) carries both `tenderness` and `fierce_loyalty` simultaneously. The set encoding preserves this. A scalar score would force a choice between them and lose the tension that *is* the meaning.

Affective primitives are defined in `packs/common/affect_primitives.jsonl`. Each language pack's lift rules map lemmas and morphological features to primitives. English lift rules are coarser (lexical only). Hebrew and Greek lift rules are fine-grained (lemma + stem + context features).

#### Channel 2: Force Valence

The illocutionary and performative force of the semantic content — what kind of *act* the language is performing on the field:

```
force: ForceClass

ForceClass ∈ {
  declarative,       # states a fact
  performative,      # accomplishes what it declares (divine speech, vows, verdicts)
  imperative,        # commands
  cohortative,       # self-exhortation or invitation
  jussive,           # wish, permission, mild command
  interrogative,     # opens a field of possible answers
  optative,          # pure possibility, the softest force
  expressive,        # conveys emotional state without asserting fact
  commissive         # commits the speaker to a future action
}
```

This maps directly from Hebrew mood (imperative, cohortative, jussive) and Greek mood (indicative, subjunctive, optative, imperative) plus the pragmatic context of the utterance. The most important distinction here is `performative` — language that does not merely describe but *enacts*. *Bara* (Hebrew: divine creative act) is performative. John 1:1's *en* is declarative of a pre-existent state. The force class is what makes these computationally distinguishable.

#### Channel 3: Emphasis and Focus

What is foregrounded in the utterance — which element the source material is marking as the primary locus of semantic weight:

```
emphasis: EmphasisProfile

EmphasisProfile: {
  focus_element: str | None,   # the lemma or phrase being foregrounded
  mechanism: EmphasisMechanism,
  degree: EmphasisDegree
}

EmphasisMechanism ∈ {
  fronting,          # moved to clause-initial position (Hebrew, Greek)
  stress,            # prosodic emphasis (English)
  repetition,        # repeated for intensity
  particle,          # emphasis particle (Hebrew: aph, raq, gam; Greek: kai, ge, men)
  stem_intensification  # Hebrew piel / intensive stem
}

EmphasisDegree ∈ { unmarked, light, strong, absolute }
```

The Hebrew piel stem is stem_intensification — it doesn't just do the action, it does it intensively. Fronting a word in a Hebrew clause to the pre-verbal position is `fronting` / `strong`. Greek particle *kai* used with an adjective (*kai autos*: "even he himself") is `particle` / `strong`. These are instructions to the field: activate this region more than its neighbors.

#### Channel 4: Polarity

Not binary negation but **polarity kind** — the type of negation or opposition being applied:

```
polarity: PolaritySpec

PolaritySpec: {
  value: PolarityValue,
  kind: PolarityKind | None
}

PolarityValue ∈ { positive, negative, contrastive, privative }

PolarityKind ∈ {
  absolute,          # Hebrew lo — unconditional, permanent
  prohibitive,       # Hebrew al — do not (imperative context)
  conditional,       # Greek me — negation in subjunctive/conditional
  factual,           # Greek ou — negation of fact in indicative
  adversative        # strong contrast (Greek alla: "but rather")
}
```

The Hebrew distinction between *lo* and *al* is not a grammatical footnote — it is a semantic difference between a permanent state (absolute negation) and a situational prohibition (prohibitive negation). The Greek distinction between *ou* and *me* encodes whether the negation is a statement of fact or a conditional/volitional restraint. These distinctions are load-bearing for any system trying to reason accurately about what a text actually claims.

#### Channel 5: Relational Orientation

The directional vector of the semantic content — toward what or whom, in what spatial-relational posture:

```
orientation: OrientationSpec

OrientationSpec: {
  direction: OrientationDirection,
  target: str | None,           # lemma or field-anchor ID
  preposition_source: str | None  # the preposition that encodes this
}

OrientationDirection ∈ {
  toward,       # Greek pros + accusative — directional presence-toward
  within,       # Greek en — locative, interior
  from,         # Greek ek/apo — source, origin
  through,      # Greek dia — instrumental, mediating
  under,        # Greek hypo — agency below, subjection
  upon,         # Greek epi — over, bearing upon
  alongside,    # Greek para — beside, accompanying
  against,      # adversative orientation
  for,          # benefactive
  reflexive     # self-oriented, middle voice signature
}
```

Greek *pros ton theon* (John 1:1) is `toward` / target: `god.being.divine` — the Logos is not merely *with* God but *oriented toward* God, *facing* God, in active relational presence. This is not the same as *en* (within) or *para* (alongside). John chose *pros* with precision. The valence layer preserves that precision in the field.

---

## The ValenceBundle in CandidateGeometricPressure

The `payload_json` of every `CandidateGeometricPressure` packet now carries an optional `valence` field:

```json
{
  "field_target": "logos.articulation.creative",
  "energy_class_hint": "E3",
  "valence": {
    "affective": ["awe", "life_giving"],
    "force": "performative",
    "emphasis": {
      "focus_element": "logos",
      "mechanism": "fronting",
      "degree": "strong"
    },
    "polarity": {
      "value": "positive",
      "kind": null
    },
    "orientation": {
      "direction": "toward",
      "target": "anchor:existence-being-copular",
      "preposition_source": "pros"
    }
  }
}
```

The `ValenceBundle` is:
- **Proposed at lift time** by the language pack's lift rules
- **Validated at the SemanticGate** in the IngestCompiler (structural completeness only — the gate does not re-interpret the valence)
- **Propagated with the packet** through the governance chain
- **Written into the field** alongside the versor update and the energy class assignment
- **Available to the readback layer** for surface generation guidance

---

## How Valence Drives Articulation

When the readback layer generates surface language from a field region, it receives both the energy class (from ADR-0006) and the valence bundle. The surface form is shaped by both:

- `force: performative` → the system does not hedge. It does not write "it seems that" or "one could argue". It declares.
- `force: optative` → the system softens. It writes in the register of possibility and wish.
- `affective: [grief, longing]` → the syntax slows. Shorter clauses. Heavier pauses.
- `emphasis.degree: absolute` → the foregrounded element comes first, receives stress, is not buried.
- `polarity.kind: absolute` → the negation is stated without qualification. *Lo* means no, permanently.
- `orientation.direction: toward` → the relational framing is directional and active, not static.

This is not template-filling. It is the field telling the surface layer what *kind of speech-act* is being performed and what *emotional and relational character* it carries. The surface layer's job is to honor that character in whatever language it is generating.

---

## Valence Tension as Signal

Two packets with the same `semantic_key` but opposing valence channels are not convergent evidence — they are **tension**. The field holds both. The tension itself is tracked:

- Same target, `force: declarative` from one source and `force: interrogative` from another → the field knows this region is contested between assertion and question
- Same target, `polarity: positive` from one source and `polarity: negative` from another → genuine contradiction OR paradox
- Same target, `affective: [joy]` from one source and `affective: [grief]` from another → the classical Hebrew *lament-that-trusts*, present throughout the Psalms

The distinction between contradiction (to be corrected) and paradox (to be held) is not automatically resolvable. Valence tension at E4 (critical energy) escalates to `ARCHITECT_REVIEW_REQUIRED`. Valence tension at E0–E1 is a resting paradox — a known tension that has settled into stable coexistence.

---

## Consequences

**Positive**
- The system can distinguish a command from a wish from a declaration from a performative act — not by inference but by direct morphological evidence from the source
- Articulation is guided by the actual character of the meaning, producing surface language with appropriate register, force, and emotional honesty
- Hebrew and Greek morphology (binyanim, moods, particles, prepositions) becomes directly load-bearing — every morphological distinction is a valence signal
- Paradox and contradiction are first-class field states, not errors to be resolved away
- The logos is not just a stored meaning — it is a meaning with force, direction, and character, ready to be spoken as it actually is

**Costs and constraints**
- Lift rules for Hebrew and Greek become significantly richer — every valence channel requires pack-specific mapping logic. This is correct complexity (it reflects the actual structure of the languages) but it is not trivial work
- The English lift rules are necessarily coarser — English encodes much of this information lexically rather than morphologically, so the valence signals are less reliable. This is honest and should be documented in `packs/en/manifest.json`
- Valence tension tracking requires the field to maintain a tension index alongside the convergence index. This is bounded in size (only high-convergence regions generate tension) but must be designed explicitly

**Rejected alternatives**
- *Sentiment analysis*: See Context. Rejected on grounds of Semantic Rigor and Third Door.
- *Emotion classifiers*: Same rejection. A classifier produces an inferred label. We want a lifted fact from the source morphology.
- *Pragma-linguistic tagging by LLM*: Nondeterministic, D3 by definition, cannot be AUTO_ACCEPT_ELIGIBLE. The entire point of lift rules is to produce D0/D1 valence assignments from deterministic morphological evidence.

---

## References

- ADR-0006: Field energy operator — the orthogonal scalar companion
- ADR-0005: Language pack contract — lift and readback rule interfaces
- `packs/he/morphology.jsonl` — Hebrew stem, mood, aspect source
- `packs/el/morphology.jsonl` — Greek mood, voice, aspect source
- `packs/common/` — affect primitives, anchor definitions
- Session notes: 2026-05-12-b (valence, wave conjugation, logos as speech-act)
