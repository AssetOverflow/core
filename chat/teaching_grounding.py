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
from generate.intent import IntentTag
from generate.semantic_templates import humanize_predicate

TEACHING_CORPUS_ID: str = "cognition_chains_v1"

_VALID_INTENTS: frozenset[str] = frozenset({"cause", "verification"})

_INTENT_TAG_BY_NAME: dict[str, IntentTag] = {
    "cause": IntentTag.CAUSE,
    "verification": IntentTag.VERIFICATION,
}

_CORPUS_PATH = (
    Path(__file__).resolve().parent.parent
    / "teaching"
    / "cognition_chains"
    / f"{TEACHING_CORPUS_ID}.jsonl"
)


@dataclass(frozen=True, slots=True)
class TeachingChain:
    """One reviewed cognition chain.

    Fields are copied verbatim from the JSONL line; the runtime never
    mutates them.  ``provenance`` is preserved for audit but not emitted
    in the user-facing surface.
    """

    chain_id: str
    subject: str
    intent: str
    connective: str
    object: str
    domains_subject_k: int
    domains_object_k: int
    provenance: str


@lru_cache(maxsize=1)
def _corpus_index() -> dict[tuple[str, str], TeachingChain]:
    """Load the cognition-chains corpus once.

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
            )
        except (TypeError, ValueError):
            continue
        out[(subject, intent)] = chain
    return out


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
    chain = _corpus_index().get((key, intent_name))
    if chain is None:
        return None
    pack = _pack_index()
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
        f"{chain.subject} — teaching-grounded ({TEACHING_CORPUS_ID}): "
        f"{head_subject}. {chain.subject} {connective} {chain.object} "
        f"({head_object}). No session evidence yet."
    )


def has_teaching_chain(subject_lemma: str, intent_tag: IntentTag) -> bool:
    """Return True iff a reviewed chain exists for (subject, intent)."""
    if not subject_lemma or not isinstance(subject_lemma, str):
        return False
    intent_name = _intent_name(intent_tag)
    if intent_name is None:
        return False
    return (subject_lemma.strip().lower(), intent_name) in _corpus_index()
