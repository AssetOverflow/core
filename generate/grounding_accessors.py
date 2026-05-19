"""Structured grounding accessors for the discourse planner.

Step 3 of the discourse-planner sequencing.  These accessors convert
the existing grounding substrate (ratified packs, reviewed teaching
corpora, reviewed cross-pack corpora) into typed
:class:`generate.discourse_planner.GroundedFact` tuples that the
planner can compose into a :class:`DiscoursePlan`.

Doctrine invariants this module respects:

* **Reuse, do not reimplement.**  Pack lemmas come from
  ``chat.pack_resolver.resolve_lemma`` and ``resolve_gloss``; teaching
  chains come from ``chat.teaching_grounding._all_chains_index``;
  cross-pack chains come from
  ``chat.cross_pack_grounding.cross_pack_chains_for_subject``.  No new
  loader, no new I/O path.
* **Existing string composers untouched.**  This module does not
  import from any ``pack_grounded_*`` / ``teaching_grounded_*`` /
  ``cross_pack_grounded_*`` *surface* function — it consults only the
  underlying data accessors that those composers already use.
  ``chat/runtime.py`` is not imported.
* **Canonical ordering.**  Returned facts are sorted by their
  ``GroundedFact.sort_key`` so two equal calls produce byte-identical
  tuples.  This is the precondition that the source-order
  characterization test (``test_grounding_source_characterization``)
  pins for downstream determinism.
* **No content synthesis.**  Every fact's ``obj`` is either a verbatim
  pack ``semantic_domains`` string, a verbatim pack ``gloss`` string,
  or a verbatim teaching/cross-pack chain object lemma.  Never a
  template, never an LLM string, never an approximation.
"""

from __future__ import annotations

from chat.cross_pack_grounding import (
    CROSS_PACK_CORPUS_ID,
    cross_pack_chains_for_object,
    cross_pack_chains_for_subject,
)
from chat.pack_resolver import (
    DEFAULT_RESOLVABLE_PACK_IDS,
    resolve_gloss,
    resolve_lemma,
)
from chat.teaching_grounding import _all_chains_index
from generate.discourse_planner import (
    FactSource,
    GroundedFact,
    GroundingBundle,
)

# Canonical predicate vocabulary the accessors emit for pack facts.
# These mirror predicate forms already used in the existing
# pack-grounded composers and the semantic-templates module, so the
# planner's downstream graph mapping uses tokens the realizer knows.
_PACK_BELONGS_TO = "belongs_to"
_PACK_IS_DEFINED_AS = "is_defined_as"


def pack_grounded_facts(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> tuple[GroundedFact, ...]:
    """Return canonical, sorted ``GroundedFact`` tuple for *lemma*.

    Emits one ``is_defined_as`` fact per pack gloss (when the pack
    ships a gloss for the lemma) and one ``belongs_to`` fact per
    ``semantic_domains`` entry.  First-match-wins across *pack_ids*
    matches ``resolve_lemma`` precedence (in-pack cognition first by
    default), so the lemma is grounded in exactly one pack.
    """

    if not lemma or not isinstance(lemma, str):
        return ()
    key = lemma.strip().lower()
    if not key:
        return ()
    resolved = resolve_lemma(key, pack_ids=pack_ids)
    if resolved is None:
        return ()
    pack_id, domains = resolved
    facts: list[GroundedFact] = []
    gloss = resolve_gloss(key, pack_ids=(pack_id,))
    if gloss is not None:
        _, _, gloss_text = gloss
        facts.append(
            GroundedFact(
                subject=key,
                predicate=_PACK_IS_DEFINED_AS,
                obj=gloss_text,
                source=FactSource.PACK,
                source_id=f"{pack_id}:{key}#gloss",
            )
        )
    for idx, domain in enumerate(domains):
        facts.append(
            GroundedFact(
                subject=key,
                predicate=_PACK_BELONGS_TO,
                obj=str(domain),
                source=FactSource.PACK,
                source_id=f"{pack_id}:{key}#domain:{idx}",
            )
        )
    return tuple(sorted(facts, key=GroundedFact.sort_key))


def teaching_grounded_chains(
    lemma: str,
) -> tuple[GroundedFact, ...]:
    """Return canonical teaching chains rooted on *lemma* as facts.

    Pulls from the aggregated teaching index (every registered teaching
    corpus, ADR-0064 cross-pack teaching).  Both ``cause`` and
    ``verification`` intents are surfaced so the discourse planner can
    select either depending on response mode.
    """

    if not lemma or not isinstance(lemma, str):
        return ()
    key = lemma.strip().lower()
    if not key:
        return ()
    aggregated = _all_chains_index()
    facts: list[GroundedFact] = []
    for (subject, _intent), chain in aggregated.items():
        if subject != key:
            continue
        facts.append(
            GroundedFact(
                subject=chain.subject,
                predicate=chain.connective,
                obj=chain.object,
                source=FactSource.TEACHING,
                source_id=f"{chain.corpus_id}#{chain.chain_id}",
            )
        )
    return tuple(sorted(facts, key=GroundedFact.sort_key))


def cross_pack_grounded_chains(
    lemma: str,
    *,
    include_object_view: bool = True,
) -> tuple[GroundedFact, ...]:
    """Return canonical cross-pack chains touching *lemma* as facts.

    Surfaces chains where *lemma* is the subject (forward view) and,
    when ``include_object_view`` is True (default), chains where *lemma*
    is the object (reverse view used by EXAMPLE intent).
    """

    if not lemma or not isinstance(lemma, str):
        return ()
    key = lemma.strip().lower()
    if not key:
        return ()
    raw: list[GroundedFact] = []
    for chain in cross_pack_chains_for_subject(key):
        raw.append(
            GroundedFact(
                subject=chain.subject,
                predicate=chain.connective,
                obj=chain.object,
                source=FactSource.TEACHING,
                source_id=f"{CROSS_PACK_CORPUS_ID}#{chain.chain_id}",
            )
        )
    if include_object_view:
        for chain in cross_pack_chains_for_object(key):
            raw.append(
                GroundedFact(
                    subject=chain.subject,
                    predicate=chain.connective,
                    obj=chain.object,
                    source=FactSource.TEACHING,
                    source_id=f"{CROSS_PACK_CORPUS_ID}#{chain.chain_id}",
                )
            )
    # Dedupe by sort_key — forward+reverse views can repeat the same
    # chain when lemma == subject == object (rare but possible).
    seen: set[tuple[int, str, str, str, str]] = set()
    deduped: list[GroundedFact] = []
    for fact in raw:
        sk = fact.sort_key()
        if sk in seen:
            continue
        seen.add(sk)
        deduped.append(fact)
    return tuple(sorted(deduped, key=GroundedFact.sort_key))


def grounding_bundle_for(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> GroundingBundle:
    """Compose every grounding source into one bundle for the planner.

    Convenience constructor that the runtime adapter calls when
    building a :class:`DiscoursePlan` input.  Pack facts come first
    (canonical priority), then aggregated teaching chains, then
    cross-pack chains.  The bundle's own ``sorted_facts`` re-sorts on
    read, so callers always see a canonical view.
    """

    bundle = GroundingBundle(
        facts=(
            *pack_grounded_facts(lemma, pack_ids=pack_ids),
            *teaching_grounded_chains(lemma),
            *cross_pack_grounded_chains(lemma),
        )
    )
    return bundle


__all__ = [
    "cross_pack_grounded_chains",
    "grounding_bundle_for",
    "pack_grounded_facts",
    "teaching_grounded_chains",
]
