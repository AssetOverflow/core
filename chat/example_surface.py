"""chat/example_surface.py — Phase 3.4: EXAMPLE intent composer.

When a prompt classifies as EXAMPLE — "Give me an example of X",
"Show me an instance of X", "Example of X" — the composer surfaces
a reviewed chain where X appears as the **object**, inverting the
typical "X is the subject" chain access pattern.

For "Give me an example of truth":

    (light, cause, reveals, truth)   exists in the cognition corpus
    → "Example of truth: light reveals truth."

This is the *converse* of NARRATIVE.  Where NARRATIVE walks every
chain rooted on X as subject ("X reveals A; X grounds B"), EXAMPLE
walks chains where X is the object ("A reveals X; B grounds X").
Both consult the same aggregated teaching index — no new corpus
ratification required.

Design constraints (matching ADR-0052..0065 doctrine):

- **No content synthesis.**  Every visible non-template token is
  pack-sourced or a verbatim chain atom.
- **Deterministic ordering.**  Examples sort by (intent, subject,
  connective) so identical corpus state yields identical surfaces.
- **Dedup by subject.**  Multiple chains can have the same object X
  with the same subject Y (e.g. cause/verification both
  ``Y reveals X``).  Emit one example per distinct subject.
- **Bounded count.**  Default ``max_examples=3`` keeps the surface
  readable.

Returns ``None`` when no chain references X as object — caller
falls through to pack-grounded DEFINITION (if X is pack-resident)
or to OOV invitation (if X is unknown).
"""

from __future__ import annotations

from chat.pack_resolver import resolve_lemma
from chat.teaching_grounding import (
    _all_chains_index,
    _pack_for_corpus,
)
from generate.semantic_templates import humanize_predicate


def example_grounded_surface(
    object_lemma: str,
    *,
    max_examples: int = 3,
) -> str | None:
    """Return a deterministic EXAMPLE-tier surface, or ``None``.

    Aggregates every reviewed chain whose **object** equals
    *object_lemma* across all registered teaching corpora.  Dedups
    by subject (the same subject acting under both cause + verification
    on the same object produces one example, not two).  Sorts
    lexicographically for replay stability.

    Returns ``None`` when no chain references *object_lemma* as
    object — caller routes through pack-grounded DEFINITION (if
    the lemma is pack-resident) or to OOV invitation.
    """
    if not object_lemma or not isinstance(object_lemma, str):
        return None
    key = object_lemma.strip().lower()
    if not key:
        return None
    if max_examples < 1:
        return None

    index = _all_chains_index()
    matching = [chain for chain in index.values() if chain.object == key]
    if not matching:
        return None

    # Dedup by subject — same subject acting twice (cause +
    # verification) on this object is one example.  Stable sort
    # by (intent, subject, connective).
    seen_subjects: set[str] = set()
    deduped: list = []
    for chain in sorted(
        matching, key=lambda c: (c.intent, c.subject, c.connective),
    ):
        if chain.subject in seen_subjects:
            continue
        seen_subjects.add(chain.subject)
        deduped.append(chain)
        if len(deduped) >= max_examples:
            break

    first = deduped[0]
    # Object domains come from the first chain's bound pack; falls
    # back to the cross-pack resolver if the chain's corpus is bound
    # to a pack that does not carry the object (defensive — strict
    # pack-residency in ADR-0064 prevents this).
    object_pack = _pack_for_corpus(first.corpus_id)
    object_domains = object_pack.get(first.object, ())
    if not object_domains:
        resolved = resolve_lemma(first.object)
        if resolved is None:
            return None
        object_domains = resolved[1]
    head_object = "; ".join(
        object_domains[: max(1, first.domains_object_k)]
    )

    corpora = tuple(sorted({c.corpus_id for c in deduped}))
    corpora_tag = corpora[0] if len(corpora) == 1 else " + ".join(corpora)

    clauses: list[str] = []
    for chain in deduped:
        connective = humanize_predicate(chain.connective)
        clauses.append(f"{chain.subject} {connective} {chain.object}")

    examples_text = "; ".join(clauses)
    return (
        f"{first.object} — example-grounded ({corpora_tag}): "
        f"{head_object}. Example: {examples_text}. "
        f"No session evidence yet."
    )


__all__ = ["example_grounded_surface"]
