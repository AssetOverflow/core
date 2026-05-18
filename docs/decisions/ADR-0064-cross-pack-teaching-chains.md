# ADR-0064 — Cross-pack teaching chains

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Supersedes:** none (extends ADR-0052 / ADR-0062 / ADR-0063)
**Phase:** Plan Phase 1 (corpus flywheel)

---

## Context

ADR-0052 introduced reviewed teaching chains as a third grounding
source alongside vault and pack-grounded surfaces. The corpus
(`teaching/cognition_chains/cognition_chains_v1.jsonl`) is reviewed,
immutable, append-only memory. ADR-0063 brought
`en_core_relations_v1` (kinship pack) onto the live runtime, but the
teaching-grounded surface composer was still hardcoded to the
cognition corpus:

```python
# chat/teaching_grounding.py — pre-ADR-0064
TEACHING_CORPUS_ID: str = "cognition_chains_v1"
_CORPUS_PATH = .../cognition_chains/cognition_chains_v1.jsonl
```

Every cold-start CAUSE/VERIFICATION prompt on a kinship lemma fell
through to the universal disclosure even though the relations pack
was mounted, because no kinship chain corpus existed and no path
existed to register one.

ADR-0064 closes that gap architecturally. ADR-0063 was the resolver
unlock at the *pack* layer; ADR-0064 is the same unlock at the
*teaching corpus* layer.

---

## Decision

### 1. Teaching corpus registry

A new dataclass + constant in `chat/teaching_grounding.py`:

```python
@dataclass(frozen=True, slots=True)
class TeachingCorpusSpec:
    corpus_id: str
    path: Path
    pack_id: str

TEACHING_CORPORA: tuple[TeachingCorpusSpec, ...] = (
    TeachingCorpusSpec("cognition_chains_v1", .../cognition_chains_v1.jsonl, "en_core_cognition_v1"),
    TeachingCorpusSpec("relations_chains_v1", .../relations_chains_v1.jsonl, "en_core_relations_v1"),
)
```

Each corpus is **1:1-bound to exactly one lexicon pack**. The 1:1
binding is the structural invariant that prevents cross-domain
leakage during cold-start surface composition: a relations chain
cannot accidentally surface a cognition-pack atom (or vice versa)
because pack-residency at load time is scoped to the corpus's
declared pack. Cross-domain chain shapes are out of scope for v1
per `docs/teaching_order.md` §5.

### 2. Aggregated chain index

`_all_chains_index()` — `lru_cache`d aggregator that loads every
registered corpus via `_load_corpus(spec)` and unions them into a
single `{(subject, intent): TeachingChain}` view. Registration order
is the resolution order; cognition is registered first so cognition-
lane byte-identity is preserved on any future cross-corpus
collision.

`TeachingChain` gains a `corpus_id` field so the surface tag and
audit trail are unambiguous when multiple corpora are active.

### 3. Surface composers consult the aggregated view

`teaching_grounded_surface` and `teaching_grounded_surface_composed`
now call `_all_chains_index()`. The surface tag follows the chain's
resolving `corpus_id`:

```
parent  → teaching-grounded (relations_chains_v1)
light   → teaching-grounded (cognition_chains_v1)
```

Cognition-lane surfaces remain byte-identical; relations-pack lemmas
now ground on the live path.

### 4. Discovery gate updated for cross-corpus residency

`teaching/discovery.py` previously gated on
`(lemma in cognition_pack) AND ((lemma, intent) not in cognition_corpus)`.
Updated to:

```python
from chat.pack_resolver import is_resolvable
from chat.teaching_grounding import _all_chains_index

if not is_resolvable(lemma):           # any mounted pack
    return ()
if (lemma, intent_name) in _all_chains_index():   # any registered corpus
    return ()
```

A kinship CAUSE prompt that lacks a relations chain is now
correctly flagged as a discovery candidate, instead of being
suppressed because the cognition pack doesn't carry the lemma.

### 5. Replay-equivalence gate registers the swap

`teaching/replay.py`'s `_swap_corpus_path` was extended to also
rewrite the registry entry's `path` for the swapped corpus AND
invalidate `_all_chains_index` cache, so surface composers re-read
the swapped corpus during the gate's transient phase. The active
corpus on disk remains byte-identical to its pre-swap state — the
replay invariant is preserved.

### 6. Back-compat

`_corpus_index()`, `_CORPUS_PATH`, `TEACHING_CORPUS_ID` retain
cognition-corpus-specific semantics for consumers whose scope is
explicitly the cognition corpus (audit, replay's cognition-public
runner, replay state-tracking). They are not removed. The aggregated
`_all_chains_index` is the new abstraction for surface composers
and the discovery gate.

A new helper `clear_teaching_caches()` drops every teaching-related
`lru_cache` atomically — replaces ad-hoc `_corpus_index.cache_clear()`
calls in replay code paths.

---

## Consequences

### Capability unlocked

| Path | Cognition lemmas | Kinship lemmas |
|---|---|---|
| `teaching_grounded_surface(CAUSE/VERIFICATION)` | byte-identical | **now grounds** for cells in `relations_chains_v1` |
| `teaching_grounded_surface_composed` | byte-identical | composes within relations corpus when chain-of-chains exists |
| Discovery gate | byte-identical | now emits candidates for kinship cells absent from the relations corpus |

### Cognition lane: byte-identical

Cognition lemmas resolve to the cognition corpus first; the
orthogonal-pack invariant prevents any (subject, intent) collision
between corpora. Public/holdout eval baselines unchanged:

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

### Live verification

```
$ core chat
> Why does parent exist?
parent — teaching-grounded (relations_chains_v1): kinship.ascendant.direct;
kinship.parent. parent precedes child (kinship.descendant.direct).
No session evidence yet.
grounding_source = teaching
```

### Future ADRs unlocked

1. **Cross-domain triples.** Once relations corpus saturates
   internally, a follow-up ADR can extend the chain shape to allow
   subject and object in different packs (e.g. `family grounds
   identity` — family ∈ relations, identity ∈ cognition).
2. **Relations eval lane.** Mirror the cognition lane harness with
   relations-domain holdout cases. The seed corpus is the ground
   truth.
3. **Audit + supersede for the relations corpus.** `teaching audit`
   and `teaching supersede` are cognition-corpus-only today; the
   registry layer makes generalizing them mechanical.

---

## Trust boundaries

- Each corpus is 1:1-bound to one lexicon pack. The binding is
  declared statically in `TEACHING_CORPORA` — runtime cannot
  introduce a new corpus or rebind a pack.
- Chain loading is read-only over immutable, reviewed, append-only
  files. Same trust boundary as ADR-0052.
- Surface tag tokens emitted are corpus_id strings declared in
  `TEACHING_CORPORA` — never derived from user input.
- The replay-gate swap rewrites the registry tuple in-place for the
  duration of the gate's transient phase and restores it on exit.
  Side-effect-free from outside the contextmanager.

---

## Files changed

```
chat/teaching_grounding.py                                      registry layer
teaching/discovery.py                                           cross-corpus gate
teaching/replay.py                                              swap-the-registry
teaching/relations_chains/relations_chains_v1.jsonl             NEW (seed corpus, 7 chains)
tests/test_relations_chains_v1.py                               NEW (17 tests)
docs/decisions/ADR-0064-cross-pack-teaching-chains.md           NEW (this file)
docs/decisions/README.md                                        index entry
docs/curriculum/relations_chains_v1.md                          NEW (curriculum unit doc)
```

---

## Verification

```
tests/test_relations_chains_v1.py                  17 passed
tests/test_teaching_audit.py                       23 passed
tests/test_composed_surface.py                     11 passed
tests/test_teaching_grounding.py                   passed
tests/test_discovery_candidates.py                 24 passed

Lanes:
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed
```

The non-negotiable field invariant `versor_condition(F) < 1e-6` is
unaffected — this ADR is a routing/dispatch change over immutable
corpus data; no algebra, no field operators, no normalization sites
were touched.
