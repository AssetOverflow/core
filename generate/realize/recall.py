"""REALIZE R1 — structural recall of realized knowledge.

The field versor is NOT an injective key: two facts about the same subject embed
to the byte-identical versor, so the metric reader (``vault.recall``) returns
both at ``inf`` and cannot tell them apart. ``recall_realized`` retrieves
realized facts by their EXACT structural metadata — subject (the first relation
argument), predicate, content_hash, span-free structure_key, or structure_kind —
an exact, deterministic equality scan (no cosine / HNSW / ANN). It reads through
the public ``VaultStore.iter_metadata`` accessor and never mutates the vault.
"""

from __future__ import annotations

from session.context import SessionContext

from .realize import RealizedRecord, _record_from_metadata


def recall_realized(
    ctx: SessionContext,
    *,
    subject: str | None = None,
    predicate: str | None = None,
    content_hash: str | None = None,
    structure_key: str | None = None,
    structure_kind: str | None = None,
    entity: str | None = None,
) -> tuple[RealizedRecord, ...]:
    """Return realized records matching ALL provided structural filters.

    Filters are conjunctive; ``None`` filters are ignored, so ``recall_realized(ctx)``
    returns every realized record (in live deque order).

    - ``subject``       — the relation's first argument (the subject) equals this.
    - ``predicate``     — the relation predicate equals this.
    - ``content_hash``  — exact span-inclusive identity (disambiguates a single fact).
    - ``structure_key`` — exact span-FREE identity (same proposition, any source).
    - ``structure_kind``— the substrate (``meaning_graph`` / ``binding_graph``).
    - ``entity``        — this name appears among the fact's entities (any role).

    The scan is exact and order-preserving; it makes no metric call and does not
    mutate the vault.
    """
    out: list[RealizedRecord] = []
    for idx, meta in ctx.vault.iter_metadata():
        if meta.get("kind") != "realized":
            continue
        args = meta.get("relation_arguments", [])
        if subject is not None and (not args or args[0] != subject):
            continue
        if predicate is not None and meta.get("relation_predicate") != predicate:
            continue
        if content_hash is not None and meta.get("content_hash") != content_hash:
            continue
        if structure_key is not None and meta.get("structure_key") != structure_key:
            continue
        if structure_kind is not None and meta.get("structure_kind") != structure_kind:
            continue
        if entity is not None and entity not in meta.get("entity_names", []):
            continue
        out.append(_record_from_metadata(meta, idx))
    return tuple(out)
