"""chat/teaching_grounding.py — teaching-grounded surface for cold-start
CAUSE and VERIFICATION intents (ADR-0052).

ADR-0048 added pack-grounded surfaces for cold-start DEFINITION / RECALL,
and ADR-0050 extended that to COMPARISON.  Both consult the ratified
``en_core_cognition_v1`` pack as a second source of grounding alongside
the session vault.

CAUSE and VERIFICATION cannot be answered from pack ``semantic_domains``
alone — those describe a single subject, not a relation between two
subjects.  But the system already has reviewed, auditable memory for a
small, well-known set of cognition-core chains (e.g. ``knowledge requires
evidence``, ``memory requires recall``, ``light reveals truth``).  Per
the Teaching Safety discipline in CLAUDE.md, reviewed memory may
contribute grounding evidence; this module supplies that contribution as
a third grounding source.

The corpus lives at ``teaching/cognition_chains/cognition_chains_v1.jsonl``
and is treated as reviewed, immutable memory at runtime: each entry
names a subject lemma, an intent (``cause`` or ``verification``), a
fixed connective predicate already present in
``generate/semantic_templates.py:_PREDICATE_HUMANIZE``, and an object
lemma.  Both lemmas must be present in the ratified cognition pack —
every visible non-template token in the emitted surface is therefore
either one of the two lemmas, a verbatim pack ``semantic_domains``
string, or a fixed-template connective.  No LLM, no synthesis, no
inference.

Design constraints (matching ADR-0048 / ADR-0050 axioms):

- Reconstruction-over-storage: the surface is reconstructed from the
  corpus + pack at call time; both are loaded once and cached because
  the corpus is reviewed memory (immutable) and ratified packs are
  immutable.
- Dual-correction: any subject not in the corpus, any intent outside
  ``{CAUSE, VERIFICATION}``, or any chain referencing lemmas missing
  from the pack returns ``None`` and callers fall through to
  ``_UNKNOWN_DOMAIN_SURFACE`` unchanged.
- Trust boundary: every surface produced here is explicitly tagged
  ``teaching:cognition_chains_v1`` so the audit contract distinguishes
  teaching-grounded surfaces from pack-grounded surfaces from
  vault-grounded surfaces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from chat.pack_grounding import PACK_ID as COGNITION_PACK_ID, _pack_index
from chat.pack_resolver import _pack_lexicon_for
from generate.intent import IntentTag
from generate.semantic_templates import humanize_predicate

TEACHING_CORPUS_ID: str = "cognition_chains_v1"

_VALID_INTENTS: frozenset[str] = frozenset({"cause", "verification"})

_INTENT_TAG_BY_NAME: dict[str, IntentTag] = {
    "cause": IntentTag.CAUSE,
    "verification": IntentTag.VERIFICATION,
}

_TEACHING_ROOT = Path(__file__).resolve().parent.parent / "teaching"

_CORPUS_PATH = (
    _TEACHING_ROOT
    / "cognition_chains"
    / f"{TEACHING_CORPUS_ID}.jsonl"
)


@dataclass(frozen=True, slots=True)
class TeachingCorpusSpec:
    """ADR-0064 — descriptor for one reviewed teaching corpus.

    A corpus is a JSONL file of reviewed chains plus the single lexicon
    pack whose vocabulary every chain in that corpus must reside in.  The
    1-to-1 corpus↔pack binding is the structural invariant that prevents
    cross-domain leakage during cold-start surface composition: a
    relations-domain chain cannot accidentally surface a cognition-pack
    atom (or vice versa) because the pack-consistency check at load time
    is scoped to the corpus's declared pack.

    Each registered corpus is treated as immutable, reviewed memory.
    Cross-domain triples (cognition × relations) are deliberately out of
    scope for v1 — they require a follow-up ADR that introduces a
    cross-pack chain shape, per ``docs/teaching_order.md`` §5.
    """

    corpus_id: str
    path: Path
    pack_id: str


# ADR-0064 — registered teaching corpora.  Order matters: chains in
# earlier corpora win on (subject, intent) collision.  Cognition is
# listed first so the cognition-lane byte-identity invariant is
# preserved when a relations chain ever shares a key (today the
# orthogonal-pack invariant prevents any such collision, but the
# resolution rule is documented).
TEACHING_CORPORA: tuple[TeachingCorpusSpec, ...] = (
    TeachingCorpusSpec(
        corpus_id="cognition_chains_v1",
        path=_TEACHING_ROOT / "cognition_chains" / "cognition_chains_v1.jsonl",
        pack_id="en_core_cognition_v1",
    ),
    TeachingCorpusSpec(
        corpus_id="relations_chains_v1",
        path=_TEACHING_ROOT / "relations_chains" / "relations_chains_v1.jsonl",
        pack_id="en_core_relations_v1",
    ),
)


@dataclass(frozen=True, slots=True)
class TeachingChain:
    """One reviewed teaching chain.

    Fields are copied verbatim from the JSONL line; the runtime never
    mutates them.  ``provenance`` is preserved for audit but not emitted
    in the user-facing surface.

    ADR-0064 — ``corpus_id`` records which registered teaching corpus
    the chain belongs to so the surface tag and audit trail are
    unambiguous when multiple corpora are active.
    """

    chain_id: str
    subject: str
    intent: str
    connective: str
    object: str
    domains_subject_k: int
    domains_object_k: int
    provenance: str
    corpus_id: str = "cognition_chains_v1"


def _load_corpus(spec: TeachingCorpusSpec) -> dict[tuple[str, str], TeachingChain]:
    """ADR-0064 — load one registered teaching corpus.

    Returns ``{(subject_lower, intent_lower): TeachingChain}`` keyed
    within this corpus only.  Pack-consistency is scoped to
    ``spec.pack_id``: every chain's subject AND object must reside in
    that specific pack's lexicon.  Cross-pack chain shapes (e.g. a
    relations subject with a cognition object) are out of scope for
    v1 per ``docs/teaching_order.md`` §5 and produce a drop with no
    surface impact.

    ADR-0055 Phase A: an entry whose ``chain_id`` appears as another
    entry's ``superseded_by`` is dropped from the active view.
    Append-only history on disk is preserved; the loader derives the
    active set.
    """
    if not spec.path.exists():
        return {}
    pack = _pack_lexicon_for(spec.pack_id)
    if not pack:
        return {}
    superseded_ids: set[str] = set()
    parsed_lines: list[dict] = []
    for line in spec.path.read_text(encoding="utf-8").splitlines():
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

    out: dict[tuple[str, str], TeachingChain] = {}
    for entry in parsed_lines:
        subject = (entry.get("subject") or "").strip().lower()
        intent = (entry.get("intent") or "").strip().lower()
        obj = (entry.get("object") or "").strip().lower()
        connective = (entry.get("connective") or "").strip()
        if not subject or not intent or not obj or not connective:
            continue
        if intent not in _VALID_INTENTS:
            continue
        if subject not in pack or obj not in pack:
            continue
        chain_id = str(entry.get("chain_id") or f"{subject}_{intent}")
        if chain_id in superseded_ids:
            continue
        try:
            chain = TeachingChain(
                chain_id=chain_id,
                subject=subject,
                intent=intent,
                connective=connective,
                object=obj,
                domains_subject_k=int(entry.get("domains_subject_k", 2)),
                domains_object_k=int(entry.get("domains_object_k", 1)),
                provenance=str(entry.get("provenance", "")),
                corpus_id=spec.corpus_id,
            )
        except (TypeError, ValueError):
            continue
        out[(subject, intent)] = chain
    return out


@lru_cache(maxsize=1)
def _corpus_index() -> dict[tuple[str, str], TeachingChain]:
    """Load the cognition-chains corpus once (back-compat surface).

    Retained for discovery / replay / audit consumers whose semantics
    are scoped to the cognition corpus specifically.  Cross-corpus
    composition uses :func:`_all_chains_index` instead.

    Returns ``{(subject_lower, intent_lower): TeachingChain}``.  Entries
    with invalid schema, unsupported intents, or with subject/object
    missing from the ratified cognition pack are dropped — the corpus
    is reviewed memory but the runtime still verifies pack consistency
    on load so a pack-corpus skew cannot leak a non-pack atom into a
    surface.

    ADR-0055 Phase A: an entry whose ``chain_id`` appears as another
    entry's ``superseded_by`` is also dropped from the active view.
    Append-only history on disk is preserved; the loader derives the
    active set.
    """
    if not _CORPUS_PATH.exists():
        return {}
    pack = _pack_index()
    # First sweep: collect supersession claims.  Only well-formed
    # entries (parseable JSON object) can retire other entries — a
    # malformed line cannot supersede a good one.
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

    out: dict[tuple[str, str], TeachingChain] = {}
    for entry in parsed_lines:
        subject = (entry.get("subject") or "").strip().lower()
        intent = (entry.get("intent") or "").strip().lower()
        obj = (entry.get("object") or "").strip().lower()
        connective = (entry.get("connective") or "").strip()
        if not subject or not intent or not obj or not connective:
            continue
        if intent not in _VALID_INTENTS:
            continue
        # Both lemmas MUST be in the ratified pack — guarantees every
        # surface atom is pack-sourced.
        if subject not in pack or obj not in pack:
            continue
        chain_id = str(entry.get("chain_id") or f"{subject}_{intent}")
        if chain_id in superseded_ids:
            continue
        try:
            chain = TeachingChain(
                chain_id=chain_id,
                subject=subject,
                intent=intent,
                connective=connective,
                object=obj,
                domains_subject_k=int(entry.get("domains_subject_k", 2)),
                domains_object_k=int(entry.get("domains_object_k", 1)),
                provenance=str(entry.get("provenance", "")),
                corpus_id=TEACHING_CORPUS_ID,
            )
        except (TypeError, ValueError):
            continue
        out[(subject, intent)] = chain
    return out


@lru_cache(maxsize=1)
def _all_chains_index() -> dict[tuple[str, str], TeachingChain]:
    """ADR-0064 — aggregated view across every registered teaching corpus.

    Returns ``{(subject_lower, intent_lower): TeachingChain}`` keyed
    across all corpora in :data:`TEACHING_CORPORA`.  Registration order
    is the resolution order: earlier corpora win on collision.  The
    cognition corpus is registered first so the cognition-lane
    byte-identity invariant is preserved.

    The :func:`_corpus_index` back-compat loader is **not** an input to
    this aggregator — both consult the same underlying file but
    :func:`_corpus_index` is reserved for cognition-corpus-only
    consumers (audit, replay, discovery's gate).  Cross-corpus surface
    composition consults :func:`_all_chains_index`.
    """
    aggregated: dict[tuple[str, str], TeachingChain] = {}
    for spec in TEACHING_CORPORA:
        corpus = _load_corpus(spec)
        for key, chain in corpus.items():
            if key not in aggregated:
                aggregated[key] = chain
    return aggregated


@lru_cache(maxsize=8)
def _pack_for_corpus(corpus_id: str) -> dict[str, tuple[str, ...]]:
    """Return the lexicon for the pack bound to *corpus_id*, cached.

    ADR-0064 — each registered teaching corpus is bound to exactly
    one lexicon pack via :data:`TEACHING_CORPORA`.  Returns an empty
    dict if *corpus_id* is unknown — callers see this as "chain
    cannot be surfaced" and fall through to the universal disclosure.
    """
    for spec in TEACHING_CORPORA:
        if spec.corpus_id == corpus_id:
            return _pack_lexicon_for(spec.pack_id)
    return {}


def _intent_name(intent_tag: IntentTag) -> str | None:
    """Return the lower-case intent key for the corpus, or ``None``."""
    if intent_tag is IntentTag.CAUSE:
        return "cause"
    if intent_tag is IntentTag.VERIFICATION:
        return "verification"
    return None


def teaching_grounded_surface(
    subject_lemma: str, intent_tag: IntentTag
) -> str | None:
    """Return a deterministic teaching-grounded surface, or ``None``.

    The surface format is fixed:

        "{subject} — teaching-grounded ({corpus_id}): {ds1}; {ds2}.
         {subject} {connective} {object} ({do1}). No session evidence yet."

    Every visible non-template token is either one of the two lemmas, a
    verbatim ``semantic_domains`` string from the ratified cognition
    pack, or the connective predicate already humanised by
    ``generate.semantic_templates.humanize_predicate``.  The trailing
    disclosure (``No session evidence yet.``) is the constant
    trust-boundary label that distinguishes teaching-grounded surfaces
    from vault-grounded surfaces.

    Returns ``None`` when:
      - the lemma is empty or not a string,
      - the intent tag is not ``CAUSE`` or ``VERIFICATION``,
      - the (subject, intent) pair is not in the teaching corpus.
    """
    if not subject_lemma or not isinstance(subject_lemma, str):
        return None
    key = subject_lemma.strip().lower()
    if not key:
        return None
    intent_name = _intent_name(intent_tag)
    if intent_name is None:
        return None
    chain = _all_chains_index().get((key, intent_name))
    if chain is None:
        return None
    # ADR-0064 — pack-residency is scoped to the chain's resolving
    # corpus.  Each registered corpus is bound to exactly one pack.
    pack = _pack_for_corpus(chain.corpus_id)
    subject_domains = pack.get(chain.subject, ())
    object_domains = pack.get(chain.object, ())
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
        f"{chain.subject} — teaching-grounded ({chain.corpus_id}): "
        f"{head_subject}. {chain.subject} {connective} {chain.object} "
        f"({head_object}). No session evidence yet."
    )


def teaching_grounded_surface_composed(
    subject_lemma: str, intent_tag: IntentTag,
) -> str | None:
    """ADR-0062 — chain-of-chains teaching-grounded surface.

    When a chain ``(A, intent_A, conn_A, B)`` exists AND a follow-up
    chain ``(B, ?, conn_B, C)`` exists for either intent, compose a
    two-clause surface:

        "{A} — teaching-grounded ({corpus_id}): {dA1}; {dA2}.
         {A} {conn_A} {B} ({dB1}), which {conn_B} {C} ({dC1}).
         No session evidence yet."

    Cycle-safe: if ``C == A`` or ``C == B``, the composer falls back
    to the single-chain surface (no follow-up clause).  Bounded depth:
    v1 follows exactly one hop; deeper chains require a future ADR.

    Follow-up intent preference: prefer ``cause`` when both exist
    (causal continuation reads more naturally than a verification
    detour).  This preference is deterministic and pack-agnostic.

    Returns ``None`` under the same conditions as
    ``teaching_grounded_surface``.  When the initial chain exists
    but no follow-up does, the composer degrades to the single-chain
    surface byte-identically — drop-in replacement.
    """
    if not subject_lemma or not isinstance(subject_lemma, str):
        return None
    key = subject_lemma.strip().lower()
    if not key:
        return None
    intent_name = _intent_name(intent_tag)
    if intent_name is None:
        return None
    corpus = _all_chains_index()
    chain = corpus.get((key, intent_name))
    if chain is None:
        return None
    # ADR-0064 — pack lookups follow each chain's resolving corpus.
    pack = _pack_for_corpus(chain.corpus_id)
    subject_domains = pack.get(chain.subject, ())
    object_domains = pack.get(chain.object, ())
    if not subject_domains or not object_domains:
        return None
    head_subject = "; ".join(
        subject_domains[: max(1, chain.domains_subject_k)]
    )
    head_object_short = "; ".join(
        object_domains[: max(1, chain.domains_object_k)]
    )
    connective = humanize_predicate(chain.connective)

    # Look for a follow-up chain whose subject equals the initial
    # chain's object.  Prefer cause; fall back to verification.
    follow_up = None
    for next_intent in ("cause", "verification"):
        candidate = corpus.get((chain.object, next_intent))
        if candidate is None:
            continue
        # Cycle guard: don't follow if the next object is the initial
        # subject (1-step cycle) or the same as the current object
        # (degenerate same-cell mismatch).
        if candidate.object in (chain.subject, chain.object):
            continue
        follow_up = candidate
        break

    if follow_up is None:
        # No follow-up available — degrade to single-chain surface
        # byte-identically with ``teaching_grounded_surface``.
        return (
            f"{chain.subject} — teaching-grounded ({chain.corpus_id}): "
            f"{head_subject}. {chain.subject} {connective} {chain.object} "
            f"({head_object_short}). No session evidence yet."
        )

    follow_pack = _pack_for_corpus(follow_up.corpus_id)
    follow_object_domains = follow_pack.get(follow_up.object, ())
    if not follow_object_domains:
        # Follow-up's object isn't pack-resident with semantic domains
        # — degrade to single-chain surface rather than emit a
        # partially-grounded composition.
        return (
            f"{chain.subject} — teaching-grounded ({chain.corpus_id}): "
            f"{head_subject}. {chain.subject} {connective} {chain.object} "
            f"({head_object_short}). No session evidence yet."
        )

    follow_head = "; ".join(
        follow_object_domains[: max(1, follow_up.domains_object_k)]
    )
    follow_connective = humanize_predicate(follow_up.connective)
    return (
        f"{chain.subject} — teaching-grounded ({chain.corpus_id}): "
        f"{head_subject}. {chain.subject} {connective} {chain.object} "
        f"({head_object_short}), which {follow_connective} {follow_up.object} "
        f"({follow_head}). No session evidence yet."
    )


def has_teaching_chain(subject_lemma: str, intent_tag: IntentTag) -> bool:
    """Return True iff a reviewed chain exists for (subject, intent)
    in any registered teaching corpus (ADR-0064 cross-corpus view)."""
    if not subject_lemma or not isinstance(subject_lemma, str):
        return False
    intent_name = _intent_name(intent_tag)
    if intent_name is None:
        return False
    return (subject_lemma.strip().lower(), intent_name) in _all_chains_index()


def clear_teaching_caches() -> None:
    """Drop every teaching-grounding lru_cache.

    ADR-0064 — the replay-equivalence gate swaps ``_CORPUS_PATH`` to
    a transient corpus and clears ``_corpus_index``; when multiple
    corpora are registered the aggregated index must also reset so
    the swap takes effect.  Test-only and replay-only escape hatch;
    production code never calls this on the hot path.
    """
    _corpus_index.cache_clear()
    _all_chains_index.cache_clear()
    _pack_for_corpus.cache_clear()
