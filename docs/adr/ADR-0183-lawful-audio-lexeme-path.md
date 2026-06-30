# ADR-0183: Lawful Audio→Lexeme Path (stub)

**Status:** Proposed (stub — placeholder to record the fork; not yet a full design)
**Date:** 2026-05-29
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `sensorium/audio/`, `language_packs/`, (future) `generate/`
**Depends on:** ADR-0013 (Sensorium Protocol), ADR-0181 (Audio Compiler), ADR-0180 (Delta-CRDT substrate)
**Related:** [`docs/audio_pipeline_overview.md`](../audio_pipeline_overview.md) §9 (teacher boundary), [`docs/plans/audio-compiler-eval-plan.md`](../plans/audio-compiler-eval-plan.md) §4 (teacher policy)

---

## 1. Why this ADR exists (context)

The audio compiler (ADR-0181) decodes the **paralinguistic** layer of speech
lawfully and deterministically: energy, voicing, pitch contour (prosody),
pauses, turn boundaries, emphasis, non-speech events. It is **deaf to lexical
content** — it hears *how* something is said, never *what words* were said.

ADR-0181 admits learned ASR (Whisper/NeMo) as **teacher/shadow lanes only** —
typed transcript *labels*, never substrate, never folded into the versor. The
serving path is and must remain Whisper-free
([overview §9](../audio_pipeline_overview.md)): **the teacher teaches; the lawful
path serves.**

That doctrine only holds in production **if a lawful runtime path exists to carry
the words** the teacher bootstrapped. This ADR is the placeholder for designing
that path. It is a **stub**: it records the fork and the constraints so whoever
reaches the words problem does not silently reach for Whisper in the serving
path. It is **not** a committed design yet.

> **This is the PR to scrutinise hard** (per the overview's warning): the moment
> a real consumer turns audio into words at serving time, the 0-parameter,
> decode-not-borrow doctrine is on the line.

## 2. Problem statement

Define a **deterministic, 0-parameter, replayable** path from a canonical audio
signal to **lexical content** (words / lexemes) that:

- never calls a learned model in the serving path;
- preserves the ADR-0181 invariants (versor condition < 1e-6; merge-key
  determinism; no PCM in traces; no normalization outside allowed sites);
- recovers what it can from physical facts in the wave (decode, not borrow), and
  refuses honestly where it cannot (no fabricated words — the `wrong = 0`
  discipline generalises here);
- can be *taught* (vocabulary grown through the reviewed corridor) without the
  teacher becoming a runtime dependency.

## 3. Candidate directions (to be evaluated, not yet decided)

Two non-exclusive paths, named in the overview:

- **(A) Words-as-text.** Audio stays a paralinguistic-plus-coarse-phonetic sense;
  the *what* arrives through the existing **text modality**. No serving-time ASR
  at all. Cleanest and lowest-risk; may be sufficient for many use cases.
- **(B) Deterministic audio→lexeme decode.** Extend the acoustic front-end toward
  **lawful phonetics** — formant tracking, spectral-band energies — to recover
  vowel quality and broad consonant classes, then match against **taught
  vocabulary** (acoustic-pattern ↔ lexeme associations grown via the reviewed
  teaching corridor). 0-parameter, fully replayable; real-speech ceiling is lower
  than learned ASR, and that cost must be stated honestly.

A teacher (Whisper, reviewed) may **bootstrap** the taught vocabulary for (B),
then be removed — it is scaffolding, not a component
([overview §9](../audio_pipeline_overview.md)).

## 4. Constraints any accepted design must honour

- **0 learned parameters in the serving path** (track in
  [`docs/model_dependency_size_tally.md`](../model_dependency_size_tally.md)).
- **Decode, not borrow** — features must be physically present in the wave; no
  opaque latents (ADR-0181 §5 rejects embeddings as substrate).
- **Refuse over fabricate** — where phonetic evidence is insufficient, emit no
  lexeme rather than a guess; reuse the `wrong = 0` / honest-refusal discipline.
- **Lexeme growth is reviewed** — new acoustic↔lexeme associations enter only
  through the contemplation → proposal → HITL corridor (cf. ADR-0164/0165's
  treatment of lexicon/primitive growth), never as raw model output.
- **Determinism / replay** — same canonical bytes ⇒ same lexemes ⇒ same trace
  hash; quantize before semantics (ADR-0181 spec §7).

## 5. Open questions (for the full ADR)

- Is (A) alone sufficient, deferring (B) indefinitely? What use cases actually
  require serving-time audio→words?
- What is the minimal lawful phonetic feature set (formants? MFCC-like bands? —
  noting MFCC must stay deterministic and inspectable, not a learned frontend)?
- How are acoustic↔lexeme associations represented in a pack, and how are they
  taught/reviewed/versioned/checksummed?
- What is the honest accuracy ceiling of (B), and how is it measured (a sealed
  audio eval lane analogous to the GSM8K sealed test)?
- Speaker/accent/noise robustness without learned models — scope or explicitly
  out-of-scope for v1?
- Does (B) compose with the binding-graph / comprehension reader the same way the
  text path does, so downstream is unchanged?

## 6. Decision

**Deferred.** This stub records the fork and the constraints. No path is selected
yet. The serving path remains Whisper-free and audio remains paralinguistic until
a full ADR selects and specifies (A) and/or (B).

## 7. Consequences

- Until this is taken up, audio comprehension is **prosody/turn/affect only** at
  serving time; lexical content for audio is unavailable in production (text
  modality carries words).
- Recording the fork now prevents the silent failure mode: someone wiring a
  teacher into the serving path because "audio needs words" without confronting
  the doctrinal cost. That decision must go through *this* ADR's successor.

## 8. References

- ADR-0181 — Audio compiler; teacher/shadow policy; embeddings rejected as substrate.
- ADR-0180 — Delta-CRDT substrate; trace/merge determinism the lexeme path must preserve.
- ADR-0164 / ADR-0165 — reviewed growth of lexicon entries and lexeme primitives (the corridor a taught audio vocabulary would reuse).
- [`docs/audio_pipeline_overview.md`](../audio_pipeline_overview.md) §9 — teacher = scaffolding; serving path stays Whisper-free; paths (A)/(B).
- [`docs/model_dependency_size_tally.md`](../model_dependency_size_tally.md) — the 0-parameter tally this path must not move.
