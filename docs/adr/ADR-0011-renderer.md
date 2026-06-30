# ADR-0011 — Renderer Layer Contract

**Status:** Accepted  
**Date:** 2026-05-13

---

## Context

The architecture pipeline terminates at `generate/stream.py`, which produces a sequence of
versor-nearest tokens. Those tokens are internal field entities — they have CGA coordinates,
provenance, and algebraic identity. Before reaching any surface (terminal, API response, UI,
audio), they must be realized into a modality-specific form.

In `core-ai`, this became `core_logos` — a full subsystem with deterministic readback, surface
realization, public trace metadata, and its own authority boundary. That was over-engineering:
it solved operational concerns (auditability, proof artifacts, API stability) before the
underlying generation was correct.

In `core`, the renderer is deliberately thin. It is not a subsystem. It is a single contract.

---

## Decision

The renderer layer is defined by one interface:

```python
class Renderer(Protocol):
    """Convert a generated token sequence into surface output.

    Contract:
        - Input:  Iterable[VocabEntry]  — the ordered token stream from generate/stream.py
        - Output: str | bytes           — modality-specific surface realization
        - Stateless: the renderer holds no field state and modifies nothing
        - Deterministic: identical token sequences produce identical surface output
    """
    def render(self, tokens: Iterable["VocabEntry"]) -> str | bytes: ...
```

The default implementation (`generate/render.py`) is a plain text renderer:
tokens → their `.surface` strings joined by the language-appropriate separator.

Modality-specific renderers (markdown, Hebrew RTL, Koine Greek polytonic, audio phoneme stream)
are implementations of this same protocol, registered externally. The engine never selects a
renderer — the caller provides one.

---

## Rationale

**Why thin?**  
The field knows what it means. The renderer only knows how to write it down. These are
fundamentally different concerns. Mixing them (as `core_logos` did) creates a subsystem that
must understand both the algebra and the output format — a dual responsibility that violates
Semantic Rigor.

**Why caller-provided?**  
The engine has no concept of "deployment context." Whether it renders to a terminal, an API,
a mobile UI, or an audio stream is not the engine's concern. Injecting a renderer at the call
site keeps the engine's contract pure and keeps the engine testable in isolation.

**Why stateless?**  
Propagation-over-mutation. The renderer receives a completed token stream. It does not
accumulate, buffer, or modify field state. If continuity across renders is needed, that is a
session-level concern, not a renderer concern.

**Why deterministic?**  
Third Door: the renderer is a pure function of the token stream. Non-determinism (formatting
decisions, adaptive punctuation, "natural" variation in surface form) is a property of language
models that apply stochastic transforms at output time. CORE does not do that. The field
determines meaning; the renderer transcribes it exactly.

---

## Hebrew and Koine Greek Rendering

These are not localizations — they are depth languages with structurally different rendering
requirements:

- **Hebrew:** RTL script, prefix/suffix morphology carried as field metadata, nikud
  (vowel points) rendered only when the VocabEntry carries them explicitly
- **Koine Greek:** polytonic diacritics, breathing marks, iota subscript — all carried in the
  VocabEntry's `.surface` field; the renderer writes them as-is

Neither requires a special renderer *subsystem*. Both require only that the VocabEntry's
`.surface` field is correctly populated upstream (in `vocab/`), and that the text renderer
respects Unicode directionality. That is all.

---

## Consequences

- `generate/render.py` is added as the default `TextRenderer` implementation
- `generate/stream.py` does not call any renderer — it yields tokens
- No `core_logos` equivalent will be introduced
- Future modality renderers (audio, structured data) implement `Renderer` and are provided
  by the caller
- The renderer is the last thing that happens before output leaves the system
- Nothing after the renderer touches the field
