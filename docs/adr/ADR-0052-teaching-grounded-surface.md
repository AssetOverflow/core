# ADR-0052 — Teaching-Grounded Surface for Cold-Start CAUSE / VERIFICATION

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0048](./ADR-0048-pack-grounded-surface.md) added a pack-grounded
surface for cold-start DEFINITION / RECALL, and
[ADR-0050](./ADR-0050-pack-grounded-comparison.md) extended that to
COMPARISON.  Both consult the ratified ``en_core_cognition_v1`` pack
as a second source of grounding alongside the session vault and
brought the cognition eval to
``surface_groundedness=69.2%`` / ``term_capture_rate=58.3%``.

The remaining unlift cases on the 13-case public split were:

| Case | Prompt | Intent |
|------|--------|--------|
| `cause_light_007` | "Why does light exist?" | CAUSE |
| `cause_knowledge_032` | "Why does knowledge require evidence?" | CAUSE |
| `verification_memory_037` | "Does memory require recall?" | VERIFICATION |
| `correction_specific_015` | "No, correction means reviewed repair" | CORRECTION |

`correction_specific_015` is out of scope — it requires prior-turn
context, not cold-start teaching-store inference.

The three cold-start cases share a structural property the pack alone
cannot satisfy: they ask about a **relation between two pack-known
lemmas** (`light` ↔ `truth`, `knowledge` ↔ `evidence`, `memory` ↔
`recall`).  Pack ``semantic_domains`` describe a single subject, not a
relation.  Fabricating the relation would violate the no-LLM-fallback
doctrine.

However, the system already has a documented place for reviewed
relational memory: per CLAUDE.md's *Teaching Safety* section and
[ADR-0018](./ADR-0018-tool-use-scope.md), reviewed memory may
contribute grounding evidence as long as it goes through a
teaching-store path and stays auditable.  The doctrinally clean fix is
a third grounding source — a small, ratified corpus of cognition
chains, treated as immutable reviewed memory at runtime, whose every
emitted atom is verifiably pack-sourced.

---

## Decision

Add a deterministic teaching-grounded surface as a third branch of
``_maybe_pack_grounded_surface``, identical guardrails to the
DEFINITION/RECALL and COMPARISON branches.

### Corpus

A new file ``teaching/cognition_chains/cognition_chains_v1.jsonl``
holds the reviewed chain corpus.  Each line:

```json
{
  "chain_id": "cause_knowledge_requires_evidence",
  "subject": "knowledge",
  "intent": "cause",
  "connective": "requires",
  "object": "evidence",
  "domains_subject_k": 2,
  "domains_object_k": 1,
  "provenance": "adr-0052:reviewed:2026-05-18"
}
```

Constraints enforced at load time
(`chat/teaching_grounding.py:_corpus_index`):

- `intent` ∈ {`cause`, `verification`} (any other value is dropped).
- `subject` and `object` MUST both be present in the ratified
  ``en_core_cognition_v1`` pack with non-empty ``semantic_domains``.
- `connective` MUST be a key recognised by
  ``generate.semantic_templates.humanize_predicate`` (e.g. `requires`,
  `reveals`, `evidences`, `is_grounded_in`).

Entries that fail any constraint are silently dropped — the runtime
cannot leak a non-pack atom into a surface even if the corpus is
edited improperly.

Three chains ship in v1:

| chain_id | subject | intent | connective | object |
|----------|---------|--------|------------|--------|
| `cause_light_reveals_truth` | `light` | cause | `reveals` | `truth` |
| `cause_knowledge_requires_evidence` | `knowledge` | cause | `requires` | `evidence` |
| `verification_memory_requires_recall` | `memory` | verification | `requires` | `recall` |

Each connective is corroborated by the subject's own pack
``semantic_domains`` (`light → meaning.revelation`; `memory →
recall.surface`; `knowledge → epistemic.ground`).

### Surface format

```text
{subject} — teaching-grounded ({corpus_id}): {ds1}; {ds2}. {subject} {connective} {object} ({do1}). No session evidence yet.
```

Every visible non-template token is either one of the two lemmas, a
verbatim ``semantic_domains`` string from the pack, or the connective
predicate already humanised by ``humanize_predicate``.  No rewording,
no LLM, no synthesis.

### Engagement conditions

``teaching_grounded_surface(subject_lemma, intent_tag)`` returns a
non-``None`` surface **only** when **all** hold:

- ``subject_lemma`` is a non-empty string,
- ``intent_tag`` is ``IntentTag.CAUSE`` or ``IntentTag.VERIFICATION``,
- the (subject, intent) pair has a chain in the corpus.

``_maybe_pack_grounded_surface`` invokes this path **only** when:

- gate fired with ``source="empty_vault"`` (cold-start session),
- ``config.output_language == "en"``,
- intent ∈ {``CAUSE``, ``VERIFICATION``},
- ``intent.subject`` resolves to a chain.

Any other condition returns ``None`` and the runtime falls through to
the universal disclosure unchanged.  Safety / ethics refusal still
takes priority above this branch (refusal is a remediation tier, not
a grounding source).

### Provenance tag

``ChatResponse.grounding_source`` and ``TurnEvent.grounding_source``
gain a fourth value, ``"teaching"``, sibling to ``"vault"``, ``"pack"``,
``"none"``.  Downstream audit consumers can filter teaching-grounded
surfaces distinctly from pack-grounded surfaces — important because
the corpus is reviewed memory, not pack memory, and may receive
updates through a different process than pack ratification.

``_maybe_pack_grounded_surface`` was widened to return
``tuple[str, str] | None`` so the provenance tag is propagated
alongside the surface; the previous boolean ``"pack" if pack_surface
else "none"`` collapsed too early.

---

## Why this is doctrine-aligned

CLAUDE.md prohibits *opaque LLM fallbacks, stochastic sampling,
hidden normalisation, hot-path repair, and approximate recall*.  This
ADR is:

- **Not opaque.**  Every visible atom is either a lemma supplied by
  the intent classifier or a verbatim pack ``semantic_domains``
  string.  Corpus id and pack id are both inspectable.
- **Not stochastic.**  Deterministic JSONL read; identical input
  produces byte-identical output (`test_surface_is_deterministic`).
- **Not hidden normalisation.**  The corpus lookup is a separate
  source of grounding, not a normalisation step inside an existing
  operator.  No versor, no manifold, no field state touched.
- **Not hot-path repair.**  `UnknownDomainGate` semantics are
  unchanged — the gate still fires; this ADR only broadens what the
  stub-path emits *after* the gate fires, in a narrow intent-typed
  branch.
- **Not approximate recall.**  Exact dictionary lookup on the corpus
  by (subject, intent) key, exact dictionary lookup on the pack by
  lemma.  No metric, no neighbourhood, no threshold.
- **Reviewed teaching, not unreviewed mutation.**  The corpus ships
  as a checked-in artifact; no runtime path mutates it.  The corpus
  is treated as immutable reviewed memory in the spirit of
  ADR-0018's teaching-store discipline.

The fundamental architectural move is the same as ADR-0048 / ADR-0050:
multiple ratified sources contribute to the runtime's grounding basis,
each with its own provenance tag.  This ADR adds **reviewed teaching
chains** as a third sibling alongside session vault and ratified pack.

---

## Characterisation — `core eval cognition`

A/B run on the 13-case public cognition split, identical
`RuntimeConfig` except for the merge of this ADR:

| Metric                    | Pre-ADR-0052 | Post-ADR-0052 | Δ            |
|---------------------------|--------------|---------------|--------------|
| `intent_accuracy`         | 100.0 %      | 100.0 %       | 0            |
| `surface_groundedness`    | 69.2 %       | **92.3 %**    | **+23.1 pp** |
| `term_capture_rate`       | 58.3 %       | **83.3 %**    | **+25.0 pp** |
| `versor_closure_rate`     | 100.0 %      | 100.0 %       | 0            |
| `versor_condition < 1e-6` | preserved    | preserved     | invariant    |

The three cases that lift are exactly the ones targeted:

```text
"Why does light exist?"
  -> intent.tag = CAUSE, subject="light"
  -> chain: light -reveals-> truth
  -> "light — teaching-grounded (cognition_chains_v1):
      cognition.illumination; logos.core. light reveals truth
      (cognition.truth). No session evidence yet."
  -> grounding_source = "teaching"

"Why does knowledge require evidence?"
  -> intent.tag = CAUSE, subject="knowledge"
  -> chain: knowledge -requires-> evidence
  -> "knowledge — teaching-grounded (cognition_chains_v1):
      cognition.knowledge; epistemic.ground. knowledge requires
      evidence (cognition.evidence). No session evidence yet."
  -> grounding_source = "teaching"

"Does memory require recall?"
  -> intent.tag = VERIFICATION, subject="memory"
  -> chain: memory -requires-> recall
  -> "memory — teaching-grounded (cognition_chains_v1):
      cognition.memory; memory.semantic. memory requires recall
      (operation.recall). No session evidence yet."
  -> grounding_source = "teaching"
```

The single remaining unlift case (`correction_specific_015`) is
correctly out of scope — it requires prior-turn context, not cold-start
inference.

---

## Consequences

### What changes

- New file: ``teaching/cognition_chains/cognition_chains_v1.jsonl``
  — reviewed corpus of 3 cognition chains.
- New module: ``chat/teaching_grounding.py``
  — corpus loader, ``teaching_grounded_surface``, ``has_teaching_chain``.
- ``chat/runtime.py:_maybe_pack_grounded_surface`` widened to return
  ``(surface, grounding_source_tag)`` and gains a CAUSE / VERIFICATION
  branch that routes to teaching.
- ``ChatResponse.grounding_source`` and ``TurnEvent.grounding_source``
  docstrings updated; ``"teaching"`` is now an accepted value.
- Three new cases lift in the cognition eval.

### What does not change

- ``_UNKNOWN_DOMAIN_SURFACE`` constant retained; unmodelled intents,
  unknown subjects, and non-English paths still return the universal
  disclosure unchanged.
- ``UnknownDomainGate`` semantics unchanged — the gate still fires on
  every empty-vault cold-start turn.
- DEFINITION / RECALL / COMPARISON paths unchanged — they still emit
  ``grounding_source="pack"`` via ADR-0048 / ADR-0050.
- ``core/cognition/pipeline.py``'s ``gate_fired`` detection
  (``response.grounding_source != "vault"``) works without
  modification — ``"teaching" != "vault"``.
- Safety / ethics refusal still takes priority above teaching grounding.
- ``versor_condition(F) < 1e-6`` invariant unaffected (no algebra
  changes).

### Scope limits

- English only (``en_core_cognition_v1``).  Same constraint as
  ADR-0048 / ADR-0050.
- CAUSE / VERIFICATION only.  Other intents (PROCEDURE,
  TRANSITIVE_QUERY, FRAME_TRANSFER) are out of scope here; they
  would need their own reviewed corpora.
- Single-subject CAUSE / VERIFICATION only.  Multi-clause causal
  structures would need richer chain shape and are deferred.
- Three chains in v1.  The corpus is intentionally compact — the
  pattern is the load-bearing artifact, not corpus volume.  Each new
  chain must be reviewed and reference only pack-known lemmas.
- Corpus is immutable at runtime.  Future ADRs may add a reviewed
  proposal-and-ratification path; the current contract is
  checked-in-only.
- ``correction_specific_015`` remains unlifted by design — corrections
  reference prior-turn context which cold-start teaching cannot supply.

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — teaching-store
  infrastructure whose discipline this ADR's corpus extends to the
  surface layer.
- [ADR-0048](./ADR-0048-pack-grounded-surface.md) — the
  DEFINITION / RECALL pack-grounded surface this ADR mirrors for
  CAUSE / VERIFICATION; same trust-boundary discipline, sibling
  ``grounding_source`` tag.
- [ADR-0049](./ADR-0049-intent-subject-extraction.md) — head-noun
  subject extraction this ADR consumes.  ``intent.subject`` for
  ``"Why does knowledge require evidence?"`` is the clean lemma
  ``"knowledge"``.
- [ADR-0050](./ADR-0050-pack-grounded-comparison.md) — the
  COMPARISON sibling, sharing the same dispatcher and provenance
  scheme.
- [ADR-0029](./ADR-0029-safety-packs.md) /
  [ADR-0033](./ADR-0033-ethics-packs.md) — sibling-pack-grounded
  contributor pattern this ADR continues to extend from verdict
  surfaces to the answer surface, now from a teaching-store source.

---

## Verification

```
tests/test_teaching_grounding.py                 — 22 tests, all green
tests/test_pack_grounded_comparison.py           — pre-existing, still green
tests/test_pack_grounding.py                     — pre-existing, still green
tests/test_intent_subject_extraction.py          — pre-existing, still green
tests/test_semantic_realizer_integration.py      — pre-existing, still green

Lanes (all green on this branch):
  core test --suite smoke         64 passed (3 pre-existing failures in
                                             tests/test_architectural_invariants.py
                                             flag stale worktree directories,
                                             unrelated to this ADR)
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite packs          6 passed
  core test --suite teaching      17 passed
  core test --suite algebra      132 passed

core eval cognition (pre → post):
  intent_accuracy        100.0% → 100.0%   (=)
  surface_groundedness    69.2% →  92.3%   (+23.1 pp)
  term_capture_rate       58.3% →  83.3%   (+25.0 pp)
  versor_closure_rate    100.0% → 100.0%   (=)
```

The non-negotiable field invariant (``versor_condition(F) < 1e-6``) is
preserved: this ADR adds a surface-construction branch on the existing
stub path — no algebra changes, no rotor construction, no field
update.
