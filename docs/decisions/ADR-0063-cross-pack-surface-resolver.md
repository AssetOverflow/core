# ADR-0063 — Cross-pack surface resolver

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Supersedes:** none (extends ADR-0048 / ADR-0050 / ADR-0052 / ADR-0053 / ADR-0060 / ADR-0061 / ADR-0062)
**Builds on:** the kinship starter pack `en_core_relations_v1` (commit `f0c57eb`).

---

## Context

ADR-0048 introduced the first pack-grounded surface composer — a
deterministic cold-start surface for `DEFINITION` / `RECALL` intents
whose subject lemma is present in the ratified cognition pack. ADR-0050
extended that to `COMPARISON`. ADR-0053 + ADR-0060 added a `CORRECTION`
acknowledgement composer (cold-start branch). ADR-0061 added a
`PROCEDURE` composer. All four composers shared a hardcoded reference
to a single lexicon pack:

```python
# chat/pack_grounding.py — pre-ADR-0063
PACK_ID: str = "en_core_cognition_v1"
```

That asymmetry was the rate-limiter on domain expansion. Mounting the
`en_core_relations_v1` kinship starter pack (already ratified —
checksum `1a013b46…`) would silently widen the runtime's mounted
manifold (vault recall + intent classification) without a corresponding
surface composer for kinship lemmas. The cold-start
`What is a parent?` prompt would fall through to the universal
"insufficient grounding" disclosure even though `parent` is in a
ratified, immutable pack on disk.

The previous ADR's memory recorded this explicitly:

> Engagement status: OPT-IN ONLY. Pack is NOT in
> `RuntimeConfig.input_packs` defaults… until cross-pack
> teaching-grounded composition exists, mounting silently exposes
> lemmas to vault recall and intent classification without a
> corresponding ratified surface composer.

ADR-0063 is the **one-PR architectural unlock** that closes that gap:
the surface composers consult an abstract *resolver* across all
mounted lexicon packs instead of one hardcoded pack, and the relations
pack joins the default mount.

---

## Decision

### 1. New abstraction: `chat/pack_resolver.py`

A small (~140 lines) pure module that maps a lemma to a
`(resolving_pack_id, semantic_domains)` pair across an ordered tuple of
mounted lexicon packs:

```python
DEFAULT_RESOLVABLE_PACK_IDS: tuple[str, ...] = (
    "en_core_cognition_v1",
    "en_core_relations_v1",
)

def resolve_lemma(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> tuple[str, tuple[str, ...]] | None: ...

def is_resolvable(lemma, pack_ids=...) -> bool: ...
def mounted_lemmas(pack_ids=...) -> frozenset[str]: ...
```

Properties:

- **First-match-wins.** Order matters: cognition is listed first so
  that any future cross-pack collision resolves cognition-side,
  preserving cognition-lane byte-identity.
- **lru_cache per-pack.** Each pack's `lexicon.jsonl` is loaded at most
  once per process (ratified packs are immutable).
- **No mutation.** Returns tuples, frozensets, plain strings.
- **Pure.** No I/O outside the cached read; no network; no LLM; no
  approximation.

### 2. Surface composers consult the resolver

`chat/pack_grounding.py`:

- `pack_grounded_surface(lemma)` — surface tag follows the resolving
  pack id. Cognition lemmas keep emitting
  `pack-grounded (en_core_cognition_v1)` byte-identically; kinship
  lemmas emit `pack-grounded (en_core_relations_v1)`.
- `pack_grounded_comparison_surface(a, b)` — each side resolved
  independently. When both resolve to the same pack, the tag stays
  single (`pack-grounded (en_core_cognition_v1)`). When the two
  resolve to different packs, the tag becomes composite
  (`pack-grounded (en_core_cognition_v1 × en_core_relations_v1)`).
- `pack_grounded_correction_surface(text)` — anchor pack stays
  cognition (`correction` is a cognition lemma); topic domains come
  from whichever pack resolves the topic lemma. Topic extraction
  scans `mounted_lemmas()` instead of the cognition-only index.
- `pack_grounded_procedure_surface(subject_text)` — topic extraction
  scans `mounted_lemmas()`; resolving pack id drives the surface tag.

`chat/teaching_grounding.py` is **unchanged** in this ADR. The
reviewed teaching corpus (`cognition_chains_v1.jsonl`) still
references cognition-pack lemmas only. Cross-pack teaching chains
(e.g. a `relations_chains_v1.jsonl`) are the natural next ADR.

### 3. Backward compatibility

- `chat/pack_grounding.py:PACK_ID = "en_core_cognition_v1"` and
  `_pack_index()` (cognition-only) are retained for back-compat with
  consumers in `teaching/contemplation.py`, `teaching/discovery.py`,
  `chat/teaching_grounding.py`, and various tests whose semantics are
  scoped to the cognition pack. They are NOT removed — only the
  composers' internal lookups switch to the resolver.
- `is_pack_lemma(lemma)` keeps its cognition-only semantics; cross-pack
  residency is `chat.pack_resolver.is_resolvable`.

### 4. Default mount adds the relations pack

`core/config.py`:

```python
input_packs: tuple[str, ...] = (
    "en_minimal_v1",
    "en_core_cognition_v1",
    "en_core_relations_v1",   # added in ADR-0063
    "he_logos_micro_v1",
    "grc_logos_micro_v1",
)
```

Mounting is now safe because the composers ground kinship lemmas
deterministically.

### 5. The relations-pack default-input test inverts

`tests/test_en_core_relations_v1_pack.py`:
- Before: `test_pack_is_not_in_default_input_packs`
- After: `test_pack_is_in_default_input_packs`

The earlier test was an explicit *guard against premature mounting*.
It guarded the asymmetry that ADR-0063 closes; its inverse is now the
correct invariant.

---

## Consequences

### Capability unlocked

| Surface composer | Cognition lemmas | Kinship lemmas |
|---|---|---|
| `pack_grounded_surface` (DEFINITION / RECALL) | byte-identical | **now grounds** |
| `pack_grounded_comparison_surface` (COMPARISON) | byte-identical when both cognition | **now grounds** kinship × kinship; composite tag for cross-pack |
| `pack_grounded_correction_surface` (CORRECTION) | byte-identical when topic ∈ cognition | **now anchors topic** on kinship lemmas |
| `pack_grounded_procedure_surface` (PROCEDURE) | byte-identical when topic ∈ cognition | **now grounds** kinship topics |

### Cognition lane: byte-identical

The cognition lane's prompts use only cognition lemmas. The resolver
picks cognition first, the surface tag stays `en_core_cognition_v1`,
the surface bytes are identical:

```
core eval cognition                      → 100/100/91.7/100 (public)
core eval cognition --split holdout      → 100/100/83.3/100 (holdout)
```

Both byte-identical to the pre-ADR baseline.

### Live-path grounding on kinship lemmas

```text
$ core chat
> What is a parent?
parent — pack-grounded (en_core_relations_v1): kinship.ascendant.direct;
kinship.parent; biology.progenitor. No session evidence yet.
grounding_source = pack
```

### Future ADRs unlocked

1. **ADR-0064 — Cross-pack teaching chains.** Add
   `relations_chains_v1.jsonl` (reviewed kinship chains) and extend
   `chat/teaching_grounding.py` to consult both corpora. The natural
   next ADR.
2. **Pronoun + role-filler v2.** `mother`, `father`, `son`, etc. as
   specializations of the v1 kinship primitives — extends
   `en_core_relations_v1` itself.
3. **Cross-domain triples.** `family causes belonging`,
   `parent grounds identity` — opens after cognition + relations both
   have ratified internal DAGs of reviewed chains.

---

## Trust boundaries

- The resolver does NOT execute pack metadata, validators, or scripts.
  It reads `lexicon.jsonl` only.
- A pack that fails to load produces an empty index — callers see
  `None`. No exception leaks into the runtime.
- No mutation site introduced. The resolver is read-only over
  immutable, ratified pack data.
- Tag tokens emitted in surfaces are always one of:
  `en_core_cognition_v1`, `en_core_relations_v1`, or the composite
  `{a} × {b}` form derived from mounted-pack ids — never from user
  input.
- `pack_resolver.clear_resolver_cache()` is a test-only escape hatch;
  production paths never call it.

---

## Verification

```
tests/test_pack_resolver.py                    28 passed
tests/test_cross_pack_grounding.py             17 passed
tests/test_pack_grounding.py                   13 passed
tests/test_pack_grounded_comparison.py         passed
tests/test_pack_grounded_correction.py         passed
tests/test_correction_topic_lemma.py           passed
tests/test_procedure_surface.py                passed
tests/test_teaching_grounding.py               passed
tests/test_composed_surface.py                 11 passed
tests/test_en_core_relations_v1_pack.py        6 passed  (inverted)

Lanes:
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed
  core test --suite full         <pending — see PR>

Cognition eval (byte-identical to pre-ADR baseline):
  public  split → intent 100% / surface 100% / term 91.7% / closure 100%
  holdout split → intent 100% / surface 100% / term 83.3% / closure 100%
```

The non-negotiable field invariant `versor_condition(F) < 1e-6` is
unaffected — this ADR is a routing/dispatch change over immutable
pack data; no algebra, no field operators, no normalization sites
were touched.

---

## Files changed

```
chat/pack_resolver.py                                NEW (~140 lines)
chat/pack_grounding.py                               composers use resolver
core/config.py                                       relations pack joins defaults
tests/test_pack_resolver.py                          NEW (28 tests)
tests/test_cross_pack_grounding.py                   NEW (17 tests)
tests/test_pack_grounding.py                         2 stale tests rewritten
tests/test_en_core_relations_v1_pack.py              default-input test inverted
docs/decisions/ADR-0063-cross-pack-surface-resolver.md   NEW (this file)
docs/decisions/README.md                             ADR-0063 index entry
```

Lines of net change: small. The architectural unlock is in
`chat/pack_resolver.py`; the rest of the diff is wiring + tests.
