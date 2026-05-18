# ADR-0048 — Pack-Grounded Surface for Cold-Start DEFINITION / RECALL

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0047](./ADR-0047-wire-forward-graph-constraint.md) isolated the
load-bearing finding from the cognition lane: with the forward graph
constraint engaged (6/13 cases), `surface_groundedness` and
`term_capture_rate` did **not** move.  The candidate-set restriction
upstream of `generate()` was working — the gap lived **downstream of
propagation**.

Investigation traced every cognition case to a single failure mode.
`ChatRuntime.chat()` consults `UnknownDomainGate` on each turn; the
gate measures whether anything in the **session vault** is similar to
the input.  A freshly instantiated runtime starts with `len(vault) == 0`,
so the gate fires immediately with `source="empty_vault"` and routes
through `_stub_response`, emitting the universal disclosure:

    "I don't know — insufficient grounding for that yet."

This is doctrine-correct refusal — no fabrication.  But it elides the
fact that CORE *does* have grounded evidence for `light`, `knowledge`,
`meaning`, `memory`, `truth`, `procedure`, `relation`, and many other
cognition-core lemmas: they are compiled into the **ratified
`en_core_cognition_v1` pack**, each carrying curated `semantic_domains`
(`["cognition.illumination", "logos.core", "perception.clarity",
"meaning.revelation"]` for `light`).

CLAUDE.md is explicit:

> *Semantic Pack Discipline — Prefer compact, curated packs … `en_core_cognition_v1`
> supplies thought vocabulary, operations, and relation predicates.*

Pack evidence is **reviewed/curated memory**, the strongest form of
grounding short of session vault evidence.  The gate consulted only
session memory and treated cold-start as universally ungrounded.

---

## Decision

Add a narrow second-source-of-grounding alongside the session vault:

1. **`chat/pack_grounding.py`** (new) — loads `en_core_cognition_v1`'s
   lexicon once (cached; ratified packs are immutable) and exposes
   `pack_grounded_surface(lemma) -> str | None`.  The surface format is
   fixed and entirely composed of pack-sourced atoms:

   ```text
   {lemma} — pack-grounded ({pack_id}): {d1}; {d2}; {d3}. No session evidence yet.
   ```

   Every visible token is either the lemma itself or a verbatim
   `semantic_domains` string from the pack.  No rewording, no LLM,
   no synthesis.  The trailing disclosure (`No session evidence yet.`)
   is a constant trust-boundary label distinguishing pack-grounded
   surfaces from vault-grounded surfaces.

2. **`chat/runtime.py`** — extends `_stub_response` with an optional
   `pack_grounded_surface: str | None = None` parameter.  When the
   `UnknownDomainGate` fires, the runtime calls a narrow helper
   `_maybe_pack_grounded_surface(text, gate_source)` that returns a
   non-`None` surface **only** when:

   - `gate_source == "empty_vault"` (not any other gate-firing source),
   - `config.output_language == "en"` (pack is English-specific),
   - `intent.tag in {DEFINITION, RECALL}` (narrow intent scope),
   - `intent.subject` is a known pack lemma.

   When all four hold, the stub-path response carries the
   pack-grounded surface instead of `_UNKNOWN_DOMAIN_SURFACE`.  Safety
   and ethics refusal still take priority above this branch (refusal is
   a remediation tier, not a grounding source).

3. **`ChatResponse.grounding_source`** and **`TurnEvent.grounding_source`** —
   one new field on each, valued in `{"vault", "pack", "none"}`.  The
   tag is preserved verbatim through the telemetry stream so downstream
   audit consumers can distinguish session-evidence answers, pack-
   evidence answers, and disclosures.

4. **`core/cognition/pipeline.py`** — `gate_fired` detection is moved
   from string equality on `_UNKNOWN_DOMAIN_SURFACE` to provenance:

   ```python
   gate_fired = response.vault_hits == 0 and response.grounding_source != "vault"
   ```

   The realizer's template fallback (`"Truth is defined as ..."`) is
   suppressed identically on both stub-path surfaces (universal
   disclosure and pack-grounded), preserving the
   "calibration gaps Finding 2" contract while accepting the broader
   stub-path surface set.

---

## Why this is doctrine-aligned, not a fabrication

CLAUDE.md prohibits *opaque LLM fallbacks, stochastic sampling, hidden
normalisation, hot-path repair, and approximate recall*.  Pack-grounded
surfaces are:

- **Not opaque.**  Every visible atom is the lemma or a verbatim pack
  `semantic_domains` string; the source pack is named in the surface.
- **Not stochastic.**  Deterministic JSONL read; identical input
  produces byte-identical output (`test_surface_is_deterministic`).
- **Not hidden normalisation.**  The pack lookup is a separate source
  of grounding, not a normalisation step inside an existing operator.
- **Not hot-path repair.**  `UnknownDomainGate` remains correct — the
  gate still fires; the change is what the runtime emits *after* the
  gate fires, in a narrow, intent-typed, audit-tagged branch.
- **Not approximate recall.**  Exact dictionary lookup on the pack
  lexicon by lemma.  No metric, no neighbourhood, no threshold.

The fundamental architectural move is recognising that **the system has
two grounding sources, not one**: session vault and reviewed pack.  The
old code consulted only session vault; this ADR extends the recall step
to also consult the reviewed pack, with provenance preserved end-to-end.

This matches the same trust-boundary discipline ADR-0029 (safety packs)
and ADR-0033 (ethics packs) established for the verdict surfaces:
multiple ratified packs compose into the runtime's evidence basis, each
with its own provenance tag.  Identity / safety / ethics packs already
contribute to the manifold and the verdict bundle; this ADR adds the
cognition pack as a corresponding contributor to the *surface*.

---

## Characterisation — `core eval cognition`

A/B run on the 13-case public cognition split, identical
`RuntimeConfig` except for the merge of this ADR:

| Metric                    | Pre-ADR-0048 | Post-ADR-0048 | Δ          |
|---------------------------|--------------|---------------|------------|
| `intent_accuracy`         | 100.0 %      | 100.0 %       | 0          |
| `surface_groundedness`    | 15.4 %       | **46.2 %**    | **+30.8**  |
| `term_capture_rate`       | 0.0 %        | **33.3 %**    | **+33.3**  |
| `versor_closure_rate`     | 100.0 %      | 100.0 %       | 0          |
| `versor_condition < 1e-6` | preserved    | preserved     | invariant  |

The lift is **not** uniform across cases.  ADR-0048 only engages on
single-lemma DEFINITION / RECALL where the subject is in the pack.  The
remaining cases (CAUSE / COMPARISON / VERIFICATION / multi-word OOV
subjects) still return the universal disclosure, which is the correct
behaviour — the cognition pack doesn't carry causal explanations or
verification logic, and fabricating those would violate the no-LLM-
fallback doctrine.

Surface examples (post-ADR-0048):

| Prompt | Surface |
|--------|---------|
| `What is light?` | `"light — pack-grounded (en_core_cognition_v1): cognition.illumination; logos.core; perception.clarity. No session evidence yet."` |
| `What is knowledge?` | `"knowledge — pack-grounded (en_core_cognition_v1): cognition.knowledge; epistemic.ground; memory.semantic. No session evidence yet."` |
| `Remember light` | `"light — pack-grounded (en_core_cognition_v1): cognition.illumination; logos.core; perception.clarity. No session evidence yet."` |
| `Why does light exist?` | `"I don't know — insufficient grounding for that yet."` (CAUSE intent — no pack path) |
| `What is a procedure?` | `"I don't know — insufficient grounding for that yet."` (multi-word subject "a procedure" not in pack index) |

---

## Consequences

### What changes

- `ChatRuntime` cold-start DEFINITION / RECALL on a pack-known English
  lemma emits a pack-grounded surface instead of the universal
  disclosure.
- `ChatResponse` and `TurnEvent` carry a new `grounding_source` field;
  downstream audit consumers can filter on `"vault" | "pack" | "none"`.
- `CognitiveTurnPipeline.run` no longer string-matches on the universal
  disclosure to detect a gate-fired turn — it uses
  `response.grounding_source != "vault"`.  Same intent, broader surface
  set.
- One test (`test_pipeline_honours_safety_stub_when_gate_fires`)
  updated to assert the broader stub-path contract: surface is either
  the universal disclosure or a pack-grounded surface, and never the
  realizer's `"X is defined as ..."` template.

### What does not change

- `UnknownDomainGate` semantics are unchanged.  It still fires on
  every empty-vault cold-start turn.  Provenance signal preserved
  (`gate_decision.source == "empty_vault"`).
- Safety / ethics refusal still takes priority above pack grounding
  — refusal is a remediation tier, not a grounding source.
- `_UNKNOWN_DOMAIN_SURFACE` constant retained; non-English, non-pack-
  lemma, non-DEFINITION/RECALL paths still return it unchanged.
- `versor_condition(F) < 1e-6` invariant unaffected (no algebra
  changes).
- Main walk path's `ChatResponse` carries `grounding_source="vault"`.

### Scope limits

- English path only (`en_core_cognition_v1`).  Multilingual cognition
  packs would follow the same pattern under a separate ADR.
- DEFINITION + RECALL only.  CAUSE / COMPARISON / VERIFICATION /
  PROCEDURE intents are out of scope — they need either teaching-store
  chains (ADR-0018) or operator-driven inference, not pack lookup.
- Single-lemma subjects only.  Multi-word subjects produced by the
  intent classifier (`"does light exist"`, `"a procedure"`) bypass the
  pack lookup; tightening the intent classifier's subject extraction
  is a separate concern and a candidate follow-up ADR.
- Top-3 `semantic_domains` rendered.  The pack's deterministic order
  in the JSONL determines which three; pack authors can re-order if
  needed (a one-line edit to the lexicon).

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — `intent_bridge` /
  `classify_intent` whose `DialogueIntent.tag` and `subject` this
  ADR consults.
- [ADR-0029](./ADR-0029-safety-packs.md) and
  [ADR-0033](./ADR-0033-ethics-packs.md) — sibling pack-grounded
  contributors to the runtime: this ADR extends that pattern from
  *verdict* surfaces to the *answer* surface.
- [ADR-0035](./ADR-0035-turn-loop-verdict-surfacing.md) — stub-path
  TurnEvent emission that pack-grounded surfaces preserve.
- [ADR-0046](./ADR-0046-forward-graph-constraint.md) /
  [ADR-0047](./ADR-0047-wire-forward-graph-constraint.md) — the
  Pillar 1→2→3 wiring whose A/B characterisation isolated the
  surface-grounding gap addressed here.

---

## Verification

```
tests/test_pack_grounding.py                    — 18 tests, all green
tests/test_semantic_realizer_integration.py     — gate-fired test updated, all green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed

core eval cognition (pre → post):
  intent_accuracy        100.0% → 100.0%   (=)
  surface_groundedness    15.4% →  46.2%   (+30.8 pp)
  term_capture_rate        0.0% →  33.3%   (+33.3 pp)
  versor_closure_rate    100.0% → 100.0%   (=)
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`) is
preserved: this ADR adds a surface-construction branch on the
existing stub path — no algebra changes, no rotor construction,
no field update.
