"""chat/cross_pack_grounding.py — ADR-0067 cross-pack teaching surface.

Phases 1–3 closed the chain-gap and OOV flywheels and opened the
turn-level composition surfaces (NARRATIVE / EXAMPLE / anaphora).
But every reviewed chain still had to live entirely within one
ratified pack: ADR-0064 binds each :data:`TEACHING_CORPORA` entry
1:1 to a single ``pack_id``, and chains whose subject and object
resolve to different packs are dropped at load time.

That constraint is structural — it kept cross-domain leakage out of
v1 while the per-pack chain DAGs ratified.  With three packs
(cognition + relations v1/v2) live and 36 reviewed in-pack chains,
the prerequisite is satisfied; this module lifts the constraint with
a deliberately narrow cross-pack chain shape.

Each chain in the cross-pack corpus carries TWO ``pack_id`` fields —
``subject_pack_id`` and ``object_pack_id`` — and the loader verifies
that the subject resolves in the named subject pack and the object
resolves in the named object pack.  No cross-pack collision matters:
each chain names its own residency.  The surface tag exposes both
pack ids so the trust boundary is explicit:

    "{X} — cross-pack-grounded (cross_pack_chains_v1:
     {subject_pack_id} × {object_pack_id}): {dX}. {X} {conn} {Y}
     ({dY}). No session evidence yet."

Design constraints (mirrors ADR-0052 / ADR-0064):

- Reconstruction-over-storage: corpus + both packs loaded lazily once.
- Strict per-chain pack-residency: a chain whose subject is not in
  its declared subject pack (or whose object is not in its declared
  object pack) is dropped silently — pack-corpus skew cannot leak a
  non-pack atom into the surface.
- Connective MUST be in :func:`generate.semantic_templates.humanize_predicate` —
  no free-form predicates, ever.
- No prose generation.  Every visible non-template token is a lemma,
  a pack ``semantic_domains`` string, or a whitelisted connective.

The corpus path is the sole write surface (proposal-only per
ADR-0027 / ADR-0057).  This module is read-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from chat.pack_resolver import _pack_lexicon_for
from generate.intent import IntentTag
from generate.semantic_templates import humanize_predicate
from packs.register.loader import RegisterPack, UNREGISTERED

CROSS_PACK_CORPUS_ID: str = "cross_pack_chains_v1"

_VALID_INTENTS: frozenset[str] = frozenset({"cause", "verification"})

_INTENT_NAME_BY_TAG: dict[IntentTag, str] = {
    IntentTag.CAUSE: "cause",
    IntentTag.VERIFICATION: "verification",
}

_TEACHING_ROOT = Path(__file__).resolve().parent.parent / "teaching"

_CORPUS_PATH = (
    _TEACHING_ROOT / "cross_pack_chains" / f"{CROSS_PACK_CORPUS_ID}.jsonl"
)


@dataclass(frozen=True, slots=True)
class CrossPackChain:
    """One reviewed cross-pack chain.

    Both ``subject_pack_id`` and ``object_pack_id`` are explicit per
    entry — the runtime never infers residency.  ``provenance`` is
    preserved for audit and never emitted in the surface.
    """

    chain_id: str
    subject: str
    intent: str
    connective: str
    object: str
    subject_pack_id: str
    object_pack_id: str
    domains_subject_k: int
    domains_object_k: int
    provenance: str
    corpus_id: str = CROSS_PACK_CORPUS_ID


@lru_cache(maxsize=1)
def _all_cross_pack_chains() -> tuple[CrossPackChain, ...]:
    """Load every reviewed cross-pack chain once.

    Returns a flat tuple of validated chains (insertion order).
    Entries with invalid schema, unsupported intents, missing pack
    ids, or whose subject/object are absent from their declared
    packs are dropped silently.

    NARRATIVE and EXAMPLE composers iterate this list directly so
    multiple chains rooted on the same ``(subject, intent)`` are
    surfaced as distinct clauses.  Single-chain lookup goes through
    :func:`_cross_pack_index` which keeps first-occurrence-wins.

    ADR-0055 Phase A supersession: an entry whose ``chain_id``
    appears as another entry's ``superseded_by`` is dropped from the
    active view.  Append-only history on disk is preserved.
    """
    if not _CORPUS_PATH.exists():
        return ()

    superseded_ids: set[str] = set()
    parsed_lines: list[dict] = []
    for line in _CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        parsed_lines.append(entry)
        sup = entry.get("superseded_by")
        if isinstance(sup, str) and sup.strip():
            superseded_ids.add(sup.strip())

    out: list[CrossPackChain] = []
    for entry in parsed_lines:
        subject = (entry.get("subject") or "").strip().lower()
        intent = (entry.get("intent") or "").strip().lower()
        obj = (entry.get("object") or "").strip().lower()
        connective = (entry.get("connective") or "").strip()
        subject_pack_id = (entry.get("subject_pack_id") or "").strip()
        object_pack_id = (entry.get("object_pack_id") or "").strip()
        if not all((subject, intent, obj, connective,
                    subject_pack_id, object_pack_id)):
            continue
        if intent not in _VALID_INTENTS:
            continue
        # Phase 4 anti-leakage invariant: a "cross-pack" chain must
        # actually cross packs.  Same-pack entries are corpus-mis-
        # filings and should live in the in-pack corpus instead.
        if subject_pack_id == object_pack_id:
            continue
        subject_pack = _pack_lexicon_for(subject_pack_id)
        object_pack = _pack_lexicon_for(object_pack_id)
        if subject not in subject_pack or obj not in object_pack:
            continue
        chain_id = str(entry.get("chain_id") or f"{subject}_{intent}_{obj}")
        if chain_id in superseded_ids:
            continue
        try:
            chain = CrossPackChain(
                chain_id=chain_id,
                subject=subject,
                intent=intent,
                connective=connective,
                object=obj,
                subject_pack_id=subject_pack_id,
                object_pack_id=object_pack_id,
                domains_subject_k=int(entry.get("domains_subject_k", 2)),
                domains_object_k=int(entry.get("domains_object_k", 1)),
                provenance=str(entry.get("provenance", "")),
            )
        except (TypeError, ValueError):
            continue
        out.append(chain)
    return tuple(out)


@lru_cache(maxsize=1)
def _cross_pack_index() -> dict[tuple[str, str], CrossPackChain]:
    """``(subject, intent) → first cross-pack chain``.

    First-occurrence-wins on collision — same rule as
    :func:`chat.teaching_grounding._all_chains_index`.  Single-chain
    surface composition (``cross_pack_grounded_surface``) goes through
    this lookup; multi-chain composition (NARRATIVE / EXAMPLE) walks
    :func:`_all_cross_pack_chains` directly.
    """
    out: dict[tuple[str, str], CrossPackChain] = {}
    for chain in _all_cross_pack_chains():
        key = (chain.subject, chain.intent)
        if key not in out:
            out[key] = chain
    return out


def clear_cross_pack_cache() -> None:
    """Test-only escape hatch: drop the lru_cache on the corpus index."""
    _all_cross_pack_chains.cache_clear()
    _cross_pack_index.cache_clear()


def cross_pack_grounded_surface(
    subject_lemma: str,
    intent_tag: IntentTag,
    *,
    register: RegisterPack = UNREGISTERED,
) -> str | None:
    """Return a deterministic cross-pack teaching surface, or ``None``.

    The surface format is fixed:

        "{X} — cross-pack-grounded ({corpus_id}: {pack_X} × {pack_Y}):
         {dX1}; {dX2}. {X} {conn} {Y} ({dY1}). No session evidence
         yet."

    Returns ``None`` when:
      - the lemma is empty or not a string,
      - the intent tag is not ``CAUSE`` or ``VERIFICATION``,
      - the (subject, intent) pair has no cross-pack chain,
      - the chain's declared packs no longer resolve the lemmas
        (corpus drift — fail closed).
    """
    if not subject_lemma or not isinstance(subject_lemma, str):
        return None
    key = subject_lemma.strip().lower()
    if not key:
        return None
    intent_name = _INTENT_NAME_BY_TAG.get(intent_tag)
    if intent_name is None:
        return None
    chain = _cross_pack_index().get((key, intent_name))
    if chain is None:
        return None
    subject_pack = _pack_lexicon_for(chain.subject_pack_id)
    object_pack = _pack_lexicon_for(chain.object_pack_id)
    subject_domains = subject_pack.get(chain.subject, ())
    object_domains = object_pack.get(chain.object, ())
    if not subject_domains or not object_domains:
        return None
    head_subject = "; ".join(
        subject_domains[: max(1, chain.domains_subject_k)]
    )
    head_object = "; ".join(
        object_domains[: max(1, chain.domains_object_k)]
    )
    connective = humanize_predicate(chain.connective)
    return (
        f"{chain.subject} — cross-pack-grounded "
        f"({chain.corpus_id}: {chain.subject_pack_id} × "
        f"{chain.object_pack_id}): {head_subject}. "
        f"{chain.subject} {connective} {chain.object} "
        f"({head_object}). No session evidence yet."
    )


def cross_pack_chains_for_subject(
    subject_lemma: str,
) -> tuple[CrossPackChain, ...]:
    """Return every cross-pack chain rooted on *subject_lemma*.

    Used by NARRATIVE composition (Phase 4.2) to weave cross-pack
    clauses into the multi-clause narrative surface.  Deterministic
    ordering: by ``(intent, connective, object)``.
    """
    if not subject_lemma or not isinstance(subject_lemma, str):
        return ()
    key = subject_lemma.strip().lower()
    if not key:
        return ()
    matches = [c for c in _all_cross_pack_chains() if c.subject == key]
    matches.sort(key=lambda c: (c.intent, c.connective, c.object))
    return tuple(matches)


def cross_pack_chains_for_object(
    object_lemma: str,
) -> tuple[CrossPackChain, ...]:
    """Return every cross-pack chain whose OBJECT is *object_lemma*.

    Used by EXAMPLE composition (Phase 4.2) to weave reverse-chain
    cross-pack clauses into the example surface.
    """
    if not object_lemma or not isinstance(object_lemma, str):
        return ()
    key = object_lemma.strip().lower()
    if not key:
        return ()
    matches = [c for c in _all_cross_pack_chains() if c.object == key]
    matches.sort(key=lambda c: (c.intent, c.subject, c.connective))
    return tuple(matches)
