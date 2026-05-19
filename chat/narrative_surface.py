"""chat/narrative_surface.py — Phase 3.3: NARRATIVE intent composer.

When a prompt classifies as NARRATIVE — "Tell me about X", "Describe
X", "What can you say about X" — the composer walks every reviewed
chain rooted on X across every registered teaching corpus and emits
a multi-clause surface that surfaces *everything* the system has
reviewed about X.

Sibling to:

  - :func:`chat.teaching_grounding.teaching_grounded_surface` —
    surfaces ONE chain rooted on X for a specific intent.
  - :func:`chat.teaching_grounding.teaching_grounded_surface_composed`
    — extends one chain with a follow-up (depth-1 chain-of-chains).
  - :func:`chat.pack_grounding.pack_grounded_surface` — surfaces X's
    pack semantic_domains.

Whereas those composers pick one chain or one extension, NARRATIVE
aggregates *every distinct (predicate, object) clause* rooted on X
across both cause and verification intents.  Surface format:

    "{X} — narrative-grounded ({corpus_ids}): {dX1}; {dX2}.
     {X} {conn1} {O1} ({dO1}); {X} {conn2} {O2} ({dO2}); ...
     No session evidence yet."

Design constraints (matching ADR-0052..0065 doctrine):

- **No content synthesis.**  Every visible non-template token is
  either the lemma X, a verbatim pack ``semantic_domains`` atom, a
  reviewed chain object lemma, or a fixed connective from
  ``humanize_predicate``.
- **Deterministic ordering.**  Clauses sort by (intent_name,
  connective, object) so identical corpus state always produces
  the identical surface.
- **Dedup by (connective, object).**  When cause and verification
  carry the same predicate + object, only one clause is emitted —
  the dual-tag is implicit in the chain provenance and adding both
  reads as noise to the user.
- **Pack-internal.**  Chains are loaded from the cross-corpus
  aggregator (:func:`_all_chains_index`); each chain's object
  domains are read from its bound pack via
  :func:`_pack_for_corpus`.
- **Bounded clause count.**  Default ``max_clauses=4`` to keep the
  surface readable.  Operators can raise the cap for analytic
  workloads.

Returns ``None`` when no chain references X as subject — caller
falls through to the pack-grounded surface (DEFINITION-like
narrative) or to the OOV invitation if X is also not pack-resident.
"""

from __future__ import annotations

from chat.cross_pack_grounding import cross_pack_chains_for_subject
from chat.pack_resolver import _pack_lexicon_for, resolve_lemma
from chat.teaching_grounding import (
    _all_chains_index,
    _pack_for_corpus,
)
from generate.semantic_templates import humanize_predicate


def _object_domains_for_chain(chain) -> tuple[str, ...]:
    """Return the object lemma's semantic domains for *chain*.

    Handles both in-pack ``TeachingChain`` (residency via its bound
    corpus pack) and cross-pack ``CrossPackChain`` (residency in
    its declared ``object_pack_id``).
    """
    object_pack_id = getattr(chain, "object_pack_id", None)
    if object_pack_id:
        return _pack_lexicon_for(object_pack_id).get(chain.object, ())
    return _pack_for_corpus(chain.corpus_id).get(chain.object, ())


def _subject_domains_for_chain(chain) -> tuple[str, ...]:
    """Same as :func:`_object_domains_for_chain` but for the subject."""
    subject_pack_id = getattr(chain, "subject_pack_id", None)
    if subject_pack_id:
        return _pack_lexicon_for(subject_pack_id).get(chain.subject, ())
    return _pack_for_corpus(chain.corpus_id).get(chain.subject, ())


def narrative_grounded_surface(
    subject_lemma: str,
    *,
    max_clauses: int = 4,
) -> str | None:
    """Return a deterministic NARRATIVE-tier surface, or ``None``.

    Aggregates every reviewed chain whose subject equals *subject_lemma*
    across all registered teaching corpora.  Dedups by (connective,
    object).  Sorts clauses lexicographically for replay stability.

    ``max_clauses`` caps the emitted clause count.  Default 4 reads
    smoothly; operators can raise for analytic workloads.

    Returns ``None`` when no chain references *subject_lemma* — the
    caller routes through pack-grounded DEFINITION (or OOV if the
    lemma is unknown).
    """
    if not subject_lemma or not isinstance(subject_lemma, str):
        return None
    key = subject_lemma.strip().lower()
    if not key:
        return None
    if max_clauses < 1:
        return None

    index = _all_chains_index()
    matching: list = [
        chain for (s, _), chain in index.items() if s == key
    ]
    # ADR-0067 — merge cross-pack chains rooted on the same subject.
    # In-pack chains take precedence on (intent, connective, object)
    # collision (first-occurrence-wins in dedup loop below).
    matching.extend(cross_pack_chains_for_subject(key))
    if not matching:
        return None

    # Dedup by (connective, object) — verification and cause carrying
    # the same predicate produce one clause, not two.  Stable sort
    # by (intent, connective, object) so replay produces byte-identical
    # output.
    seen: set[tuple[str, str]] = set()
    deduped: list = []
    for chain in sorted(
        matching, key=lambda c: (c.intent, c.connective, c.object),
    ):
        sig = (chain.connective, chain.object)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(chain)
        if len(deduped) >= max_clauses:
            break

    # Subject domains: take from the first chain's bound pack so the
    # narrative header is sourced from the lemma's own pack — even
    # when the matching chains span multiple corpora.
    first = deduped[0]
    subject_domains = _subject_domains_for_chain(first)
    if not subject_domains:
        # Fall back to cross-pack resolver — subject may live in a
        # different pack than its chains' corpus binding (defensive).
        resolved = resolve_lemma(first.subject)
        if resolved is None:
            return None
        subject_domains = resolved[1]
    head_subject = "; ".join(
        subject_domains[: max(1, first.domains_subject_k)]
    )

    # Collect involved corpora for the tag.
    corpora = tuple(sorted({c.corpus_id for c in deduped}))
    corpora_tag = corpora[0] if len(corpora) == 1 else " + ".join(corpora)

    # Emit one clause per deduped chain.
    clauses: list[str] = []
    for chain in deduped:
        obj_domains = _object_domains_for_chain(chain)
        if not obj_domains:
            continue
        obj_head = "; ".join(
            obj_domains[: max(1, chain.domains_object_k)]
        )
        connective = humanize_predicate(chain.connective)
        clauses.append(
            f"{chain.subject} {connective} {chain.object} ({obj_head})"
        )

    if not clauses:
        return None

    return (
        f"{first.subject} — narrative-grounded ({corpora_tag}): "
        f"{head_subject}. {'; '.join(clauses)}. "
        f"No session evidence yet."
    )


__all__ = ["narrative_grounded_surface"]
