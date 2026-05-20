"""chat/pack_grounding.py — pack-grounded surface for cold-start DEFINITION
and RECALL intents (ADR-0048).

When the ``UnknownDomainGate`` fires with ``source="empty_vault"`` — i.e.
the runtime has no session evidence yet — the runtime would otherwise
emit the universal ``_UNKNOWN_DOMAIN_SURFACE`` disclosure on every turn,
including for terms that are explicitly compiled into the ratified
cognition pack.

This module supplies a narrow, auditable alternative: when the input's
intent is ``DEFINITION`` or ``RECALL`` AND the intent's subject lemma is
present in ``en_core_cognition_v1``, return a deterministic surface
composed from the pack lexicon's ``semantic_domains`` for that lemma,
explicitly tagged as pack-sourced.

Design constraints (matching the seven axioms):

- Geometry-first: the pack lookup is by lemma surface, but the
  ``semantic_domains`` were curated against the same versors the
  vocabulary carries; the surface refers only to the lemma and its
  curated descriptors — no synthesis, no LLM fallback.
- Reconstruction-over-storage: the surface is reconstructed from the
  pack at call time; the lexicon is loaded once and cached because
  ratified packs are immutable.
- Dual-correction: any lemma not in the pack returns ``None``;
  callers fall through to ``_UNKNOWN_DOMAIN_SURFACE`` unchanged.
- Compilation-last: no tensors, no kernels — JSONL read and string
  formatting only.
- Trust boundary: every surface produced here is explicitly tagged
  ``pack:en_core_cognition_v1`` so the audit contract distinguishes
  pack-grounded surfaces from vault-grounded surfaces and from the
  universal disclosure.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from chat.pack_resolver import (
    DEFAULT_RESOLVABLE_PACK_IDS,
    mounted_lemmas,
    resolve_lemma,
)
from packs.anchor_lens.loader import AnchorLens, UNANCHORED
from packs.register.loader import RegisterPack, UNREGISTERED

PACK_ID: str = "en_core_cognition_v1"

# ADR-0073c — substrate → mounted pack ids for anchor-lens engagement.
# Cognition-tier packs are the primary L1.3 substrate.  Micro packs are
# included as a defensive fallback for the few distinct lemmas they
# carry; the engagement path early-exits once an atom-match is found.
_ANCHOR_LENS_SUBSTRATE_PACK_IDS: dict[str, tuple[str, ...]] = {
    "grc": ("grc_logos_cognition_v1", "grc_logos_micro_v1"),
    "he": ("he_core_cognition_v1", "he_logos_micro_v1"),
    "en": (PACK_ID,),
}

_PACK_LEXICON_PATH = (
    Path(__file__).resolve().parent.parent
    / "language_packs"
    / "data"
    / PACK_ID
    / "lexicon.jsonl"
)

# ADR-0073c — synthetic English anchor lemmas for cross-lang collapse.
# Holds entry_ids like ``en-collapse-love`` so anchor-lens engagement
# (he_chesed_v1 / he_shalom_v1 / he_tzedek_v1) can resolve English
# prompts like "What is love?" to a target entry_id and walk the
# alignment graph from there.  This pack is engagement-only: it is
# intentionally NOT included in ``DEFAULT_RESOLVABLE_PACK_IDS`` so the
# composer does not fabricate a pack-grounded definition for these
# lemmas — only lens-engagement reads from here.
_COLLAPSE_ANCHORS_LEXICON_PATH = (
    Path(__file__).resolve().parent.parent
    / "language_packs"
    / "data"
    / "en_collapse_anchors_v1"
    / "lexicon.jsonl"
)


@lru_cache(maxsize=1)
def _pack_index() -> dict[str, tuple[str, ...]]:
    """Load the cognition pack lexicon once and return ``{lemma: semantic_domains}``.

    Ratified packs are immutable; safe to cache for the process lifetime.
    Returns an empty dict if the pack is unavailable — callers must treat
    a missing pack as "no pack-grounded surface available."
    """
    if not _PACK_LEXICON_PATH.exists():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for line in _PACK_LEXICON_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        lemma = entry.get("lemma") or entry.get("surface")
        if not lemma:
            continue
        domains = tuple(entry.get("semantic_domains", ()))
        if domains:
            out[lemma.lower()] = domains
    return out


def _frame_gloss(lemma: str, pos: str, gloss: str) -> str:
    """Render a fluent sentence from a (lemma, pos, gloss) triple.

    POS-aware sentence frames:

      NOUN          -> "{Lemma} is {gloss}."
      VERB          -> "To {lemma} means {gloss}."
      ADJ           -> "Something is {lemma} when it {gloss}."
      ADV           -> "{Lemma} indicates {gloss}."
      ADP           -> "{Lemma} is a relation of {gloss}."
      SCONJ         -> "{Lemma} introduces {gloss}."
      PRON          -> "{Lemma} asks for {gloss}."
      AUX           -> "{Lemma} expresses {gloss}."
      INTJ          -> "{Lemma} is uttered to {gloss}."
      DET           -> "{Lemma} specifies {gloss}."
      NUM           -> "{Lemma} is the cardinal value {gloss}."
      *  (unknown)  -> "{Lemma}: {gloss}."  (back-compat fallback)

    The glosses are authored to match these frames exactly (see
    the subagent briefs and ``language_packs/data/<pack>/glosses.jsonl``).
    Capitalization is applied only to the framed surface, never to
    the lemma in the lexicon (which stays lowercase by convention).
    """
    key = lemma.strip()
    cap = key[:1].upper() + key[1:] if key else key
    pos_u = (pos or "").upper()
    if pos_u == "NOUN":
        return f"{cap} is {gloss}."
    if pos_u == "VERB":
        return f"To {key} means {gloss}."
    if pos_u == "ADJ":
        return f"Something is {key} when it {gloss}."
    if pos_u == "ADV":
        return f"{cap} indicates {gloss}."
    if pos_u == "ADP":
        return f"{cap} is a relation of {gloss}."
    if pos_u == "SCONJ":
        return f"{cap} introduces {gloss}."
    if pos_u == "PRON":
        return f"{cap} asks for {gloss}."
    if pos_u == "AUX":
        return f"{cap} expresses {gloss}."
    if pos_u == "INTJ":
        return f"{cap} is uttered to {gloss}."
    if pos_u == "DET":
        return f"{cap} specifies {gloss}."
    if pos_u == "NUM":
        return f"{cap} is the cardinal value {gloss}."
    return f"{cap}: {gloss}."


_DEFAULT_DISCLOSURE_DOMAIN_COUNT: int = 3


def _resolve_disclosure_domain_count(
    register: RegisterPack,
    *,
    intent_name: str | None = None,
) -> int:
    """Return clamped disclosure_domain_count for *register*.

    Resolution order (ADR-0071 per_intent extension):

    1. ``realizer_overrides.per_intent[intent_name].disclosure_domain_count``
    2. ``realizer_overrides.disclosure_domain_count`` (flat key)
    3. Default ``_DEFAULT_DISCLOSURE_DOMAIN_COUNT`` (= 3)

    The ratification gate (``scripts/ratify_register_packs.py``) is the
    authoritative trust boundary: only known keys with in-bounds values
    can ratify.  This clamp is fail-soft defense-in-depth for off-path
    callers (test fixtures, ad-hoc CLI) — a malformed override should
    not crash the realizer hot path.  See ADR-0070.
    """
    from collections.abc import Mapping as _Mapping
    overrides = register.realizer_overrides
    n: object = _DEFAULT_DISCLOSURE_DOMAIN_COUNT
    if intent_name is not None:
        per_intent: object = (
            overrides.get("per_intent") if hasattr(overrides, "get") else None
        )
        if isinstance(per_intent, _Mapping):
            sub: object = per_intent.get(intent_name)
            if isinstance(sub, _Mapping) and "disclosure_domain_count" in sub:
                candidate = sub["disclosure_domain_count"]
                if (
                    isinstance(candidate, int)
                    and not isinstance(candidate, bool)
                    and 1 <= candidate <= 3
                ):
                    return candidate
    flat = overrides.get("disclosure_domain_count") if hasattr(overrides, "get") else None
    if flat is not None:
        n = flat
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 3:
        return _DEFAULT_DISCLOSURE_DOMAIN_COUNT
    return n


@lru_cache(maxsize=8)
def _substrate_lexicon_by_entry_id(pack_id: str) -> dict[str, tuple[str, ...]]:
    """Map ``entry_id -> semantic_domains`` for a substrate pack.

    Cached for the process lifetime — ratified packs are immutable.
    Returns an empty dict when the pack is unavailable.
    """
    lexicon_path = (
        Path(__file__).resolve().parent.parent
        / "language_packs"
        / "data"
        / pack_id
        / "lexicon.jsonl"
    )
    if not lexicon_path.is_file():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for line in lexicon_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        entry_id = entry.get("entry_id")
        if not entry_id:
            continue
        out[str(entry_id)] = tuple(entry.get("semantic_domains", ()))
    return out


@lru_cache(maxsize=1)
def _en_lemma_to_entry_id() -> dict[str, str]:
    """Map ``en lemma -> entry_id`` for anchor-lens engagement.

    Merges the cognition pack (``en_core_cognition_v1``) with the
    collapse-anchor pack (``en_collapse_anchors_v1``).  Cognition entries
    win on lemma collision since they carry real semantic_domains.
    Cached for the process lifetime — ratified packs are immutable.
    """
    out: dict[str, str] = {}
    for path in (_COLLAPSE_ANCHORS_LEXICON_PATH, _PACK_LEXICON_PATH):
        # cognition path is iterated second so it wins on lemma collision
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            lemma = entry.get("lemma") or entry.get("surface")
            entry_id = entry.get("entry_id")
            if not lemma or not entry_id:
                continue
            out[str(lemma).lower()] = str(entry_id)
    return out


def _resolve_anchor_lens_mode(
    en_lemma: str, anchor_lens: AnchorLens,
) -> str | None:
    """Return the lens's ``cognitive_mode_label`` if it engages on ``en_lemma``.

    Engagement rule (single):
      1. Resolve ``en_lemma`` to its entry_id in the cognition pack.
      2. Walk the alignment graph(s) of every substrate pack matching
         ``anchor_lens.primary_substrate`` and find substrate lemmas
         whose edges target this en entry_id.
      3. For each such substrate lemma, check whether its
         ``semantic_domains`` contains any atom from
         ``anchor_lens.semantic_domain_preferences``.  First match wins.

    Returns ``None`` when:
      * ``anchor_lens.is_null_lens()`` (the unanchored sentinel and
        ``default_unanchored_v1`` both early-exit here)
      * ``primary_substrate`` is ``"none"`` or has no mounted packs
      * the en lemma is not in the cognition pack
      * no substrate lemma aligned to this en lemma carries a
        preferred atom

    The function never reads non-ASCII surface text — it pivots on
    entry_ids and atom strings only.  Glyph-leak is structurally
    impossible from this engagement path.

    Lazy import of :func:`alignment.graph.load_alignment` keeps the
    alignment subsystem out of cold-import paths.
    """
    if anchor_lens.is_null_lens() or not anchor_lens.semantic_domain_preferences:
        return None
    substrate = anchor_lens.primary_substrate
    if substrate == "none":
        return None
    substrate_packs = _ANCHOR_LENS_SUBSTRATE_PACK_IDS.get(substrate, ())
    if not substrate_packs:
        return None
    en_entry_id = _en_lemma_to_entry_id().get(en_lemma.strip().lower())
    if not en_entry_id:
        return None
    from alignment.graph import load_alignment

    preferred = set(anchor_lens.semantic_domain_preferences)
    for pack_id in substrate_packs:
        graph = load_alignment(pack_id)
        if len(graph) == 0:
            continue
        substrate_index = _substrate_lexicon_by_entry_id(pack_id)
        for edge in graph.edges:
            if edge.target_id != en_entry_id:
                continue
            source_atoms = substrate_index.get(edge.source_id, ())
            if not source_atoms:
                continue
            if any(atom in preferred for atom in source_atoms):
                return anchor_lens.cognitive_mode_label
    return None


def _maybe_append_anchor_lens_annotation(
    surface: str, en_lemma: str, anchor_lens: AnchorLens,
) -> str:
    """Append ``[lens({lens_id}):{mode_label}]`` when lens engages.

    Annotation goes between the existing trailing period and the end of
    string, e.g.:

        "...pack-grounded (en_core_cognition_v1)."
        →
        "...pack-grounded (en_core_cognition_v1) [lens(grc_logos_v1):systematic]."

    Surface without a trailing period gets the annotation suffixed
    directly.  No-op when the lens does not engage.

    Audit invariant: the annotation is pure ASCII (lens_id and mode
    label both bounded to 64 ASCII chars by the loader).
    """
    mode = _resolve_anchor_lens_mode(en_lemma, anchor_lens)
    if mode is None:
        return surface
    annotation = f"[lens({anchor_lens.lens_id}):{mode}]"
    if surface.endswith("."):
        return f"{surface[:-1]} {annotation}."
    return f"{surface} {annotation}"


def build_pack_surface_candidate(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
    *,
    register: RegisterPack = UNREGISTERED,
    anchor_lens: AnchorLens = UNANCHORED,
):
    """Return a :class:`PackSurfaceCandidate` for *lemma*, or ``None``.

    This is the selector-ready intermediate that
    :func:`pack_grounded_surface` renders to a string.  Two grounding
    paths feed it:

      1. Reviewed gloss (preferred) — when the pack ships a gloss for
         the lemma AND the lemma is ratified in the same pack's
         lexicon (verified by :func:`resolve_gloss`), the candidate
         carries the gloss and ``is_fluent_sentence=True``.

      2. Dotted-domain disclosure (fallback) — when no gloss exists
         for the lemma, the candidate falls back to the original
         "{lemma} — pack-grounded (...): d1; d2; d3. No session
         evidence yet." structured form.  ``is_fluent_sentence=False``.

    When the future :class:`SurfaceSelector` lands, it will consume
    this candidate directly without re-rendering; the surface field
    is already the final user-facing string.
    """
    from chat.pack_resolver import resolve_gloss
    from chat.pack_surface_candidate import PackSurfaceCandidate
    resolved = resolve_lemma(lemma, pack_ids)
    if resolved is None:
        return None
    resolved_pack_id, domains = resolved
    key = lemma.strip().lower()

    # Try the gloss path first.  resolve_gloss enforces lexicon
    # residency, so a gloss that snuck into glosses.jsonl without a
    # matching lexicon entry is rejected.
    gloss_entry = resolve_gloss(lemma, pack_ids)
    if gloss_entry is not None and gloss_entry[0] == resolved_pack_id:
        _, gloss_pos, gloss_text = gloss_entry
        # Fall back to the pack-resident POS when the gloss carries
        # no POS (older gloss files).  POS drives the sentence frame.
        if not gloss_pos:
            # Pull POS from the lexicon entry if we can.
            from chat.pack_resolver import _pack_lexicon_for  # noqa
            # _pack_lexicon_for only stores domains today; POS is not
            # in its cached dict.  Default to NOUN frame as the safest
            # fallback — most lemmas with glosses are nouns.
            gloss_pos = "NOUN"
        # Use lowercase "pack-grounded" mid-sentence so existing
        # substring assertions in tests/test_pack_grounding.py (and
        # downstream) continue to match.  The marker is a provenance
        # tag, not a sentence-starting word.
        surface = (
            f"{_frame_gloss(key, gloss_pos, gloss_text)} "
            f"pack-grounded ({resolved_pack_id})."
        )
        # ADR-0073c — anchor-lens annotation when lens engages on
        # this en lemma via the substrate alignment graph.  No-op
        # under UNANCHORED / default_unanchored_v1 (null-lift).
        surface = _maybe_append_anchor_lens_annotation(
            surface, key, anchor_lens,
        )
        return PackSurfaceCandidate(
            surface=surface,
            grounding_source="pack",
            pack_id=resolved_pack_id,
            gloss=gloss_text,
            semantic_domains=tuple(domains),
            lemma=key,
            pos=gloss_pos,
            is_user_facing_safe=True,
            is_fluent_sentence=True,
        )

    # Dotted-domain disclosure fallback.  Slice width is the register's
    # disclosure_domain_count (ADR-0070); default (3) preserves the
    # pre-R3 surface byte-for-byte under the unregistered sentinel and
    # under null registers (default_neutral_v1).
    n = _resolve_disclosure_domain_count(register)
    head = "; ".join(domains[:n])
    surface = (
        f"{key} — pack-grounded ({resolved_pack_id}): {head}. "
        f"No session evidence yet."
    )
    # ADR-0073c — anchor-lens annotation appended after the trailing
    # period of the disclosure surface.  No-op under UNANCHORED /
    # default_unanchored_v1 (null-lift).
    surface = _maybe_append_anchor_lens_annotation(
        surface, key, anchor_lens,
    )
    return PackSurfaceCandidate(
        surface=surface,
        grounding_source="pack",
        pack_id=resolved_pack_id,
        gloss=None,
        semantic_domains=tuple(domains),
        lemma=key,
        pos="",  # POS unknown via this code path
        is_user_facing_safe=True,
        is_fluent_sentence=False,
    )


def pack_grounded_surface(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
    *,
    register: RegisterPack = UNREGISTERED,
    anchor_lens: AnchorLens = UNANCHORED,
) -> str | None:
    """Return a deterministic pack-grounded surface for *lemma*, or ``None``.

    Two surface forms, selected by gloss presence:

      With gloss (preferred, lexicon-resident):
        "{Lemma} is {gloss}. Pack-grounded ({pack_id})."
        (frame varies by POS — see :func:`_frame_gloss`)

      Without gloss (dotted-domain disclosure — original ADR-0048 form):
        "{lemma} — pack-grounded ({pack_id}): {d1}; {d2}; {d3}. No session evidence yet."

    Both forms carry the ``"pack-grounded ({pack_id})"`` provenance
    marker so substring-permissive tests continue to pass through
    the transition.

    The intermediate :class:`PackSurfaceCandidate` is the
    selector-ready shape; this function renders the candidate to a
    string for current callers.  When :class:`SurfaceSelector` lands
    the candidate is what the selector consumes directly.

    Returns ``None`` when the lemma is empty or doesn't resolve.
    """
    candidate = build_pack_surface_candidate(
        lemma, pack_ids, register=register, anchor_lens=anchor_lens,
    )
    return candidate.surface if candidate is not None else None


_RELATION_CONFIRMATION_DISPLAY: dict[str, str] = {
    "reveals": "reveals",
    "grounds": "grounds",
    "supports": "supports",
    "requires": "requires",
    "causes": "causes",
    "precedes": "precedes",
    "follows": "follows",
}


def pack_grounded_relation_confirmation_surface(
    subject_lemma: str,
    relation: str | None,
    object_lemma: str | None,
    *,
    negated: bool = False,
) -> str | None:
    """Return a deterministic surface for a confirmed relation claim.

    C2 handles prompts like ``"Light reveals truth, right?"`` by
    stripping the terminal confirmation tag before intent classification.
    This composer preserves the resulting proposition without requiring
    a reviewed teaching chain for every relation variant.  It only
    emits when both endpoint lemmas resolve in mounted packs and the
    relation is in the closed display table above.
    """
    if not subject_lemma or not object_lemma or not relation:
        return None
    rel = _RELATION_CONFIRMATION_DISPLAY.get(relation.strip().lower())
    if rel is None:
        return None
    subject_key = subject_lemma.strip().lower()
    object_key = object_lemma.strip().lower()
    subject_resolved = resolve_lemma(subject_key)
    object_resolved = resolve_lemma(object_key)
    if subject_resolved is None or object_resolved is None:
        return None
    subject_pack_id, subject_domains = subject_resolved
    object_pack_id, object_domains = object_resolved
    if negated:
        predicate = f"does not {rel[:-1] if rel.endswith('s') else rel}"
    else:
        predicate = rel
    return (
        f"{subject_key} {predicate} {object_key}. "
        f"pack-grounded ({subject_pack_id}; {object_pack_id}): "
        f"{subject_domains[0]}; {object_domains[0]}."
    )


def is_pack_lemma(lemma: str) -> bool:
    """Return True iff *lemma* has an entry with ``semantic_domains`` in the
    ratified cognition pack (``en_core_cognition_v1``).

    Cognition-pack-specific helper retained for back-compat with the
    cognition-corpus modules (discovery, contemplation, teaching
    chains) whose semantics are scoped to the cognition pack.  For
    cross-pack residency checks, use
    :func:`chat.pack_resolver.is_resolvable`.
    """
    if not lemma or not isinstance(lemma, str):
        return False
    return lemma.strip().lower() in _pack_index()


_CORRECTION_TOPIC_STOPWORDS: frozenset[str] = frozenset({
    # The meta-cognition lemma itself — we never echo it as the topic
    # because it's already the subject of the acknowledgement template.
    "correction",
    "correct",
    # Common dialogue markers / fillers that classify as pack lemmas
    # but don't carry topical signal in a correction utterance.
    "be",
    "have",
    # Polarity markers (en_core_polarity_v1) — pack-resident dialogue
    # tokens that carry NO topical signal in a correction utterance.
    # "No, my parent disagrees" — ``no`` is the correction marker
    # itself, not the topic.  Without these stopwords the topic
    # extractor would short-circuit on ``no`` and miss ``parent``.
    "no",
    "yes",
    "maybe",
    "perhaps",
    "hardly",
    "indeed",
    "surely",
    "definitely",
})


def _extract_correction_topic_lemma(text: str) -> str | None:
    """Return the first mounted-pack-resident, topical lemma in *text*, or None.

    Deterministic: tokens are processed in left-to-right utterance
    order; the first token that is resident in any mounted pack AND not
    in the correction-stopword set wins.  Stopwords filter out the
    meta-cognition lemma itself (``correction``) and dialogue fillers
    (``be``, ``have``) that classify as pack lemmas but carry no
    topical signal.

    ADR-0063 — residency is checked across all mounted lexicon packs
    (see :data:`chat.pack_resolver.DEFAULT_RESOLVABLE_PACK_IDS`), so a
    kinship correction (``"No, my parent disagrees"``) anchors the
    acknowledgement on the kinship topic.

    Used by :func:`pack_grounded_correction_surface` to weave the
    corrected claim's subject into the acknowledgement template.
    """
    if not text or not isinstance(text, str):
        return None
    lemmas = mounted_lemmas()
    raw = text.lower()
    for ch in ",.;:!?\"'()[]{}":
        raw = raw.replace(ch, " ")
    for token in raw.split():
        if not token:
            continue
        if token in _CORRECTION_TOPIC_STOPWORDS:
            continue
        if token in lemmas:
            return token
    return None


def pack_grounded_correction_surface(
    text: str | None = None,
    *,
    register: RegisterPack = UNREGISTERED,
) -> str | None:
    """ADR-0053 + ADR-0060 — cold-start CORRECTION acknowledgement.

    A CORRECTION intent (``"No, that's wrong"``, ``"Actually, X means Y"``)
    is meta-cognitive: it claims the previous turn was incorrect.  On a
    cold-start session there is no prior turn to apply the correction
    to, so the doctrine-aligned response is **not** to define what
    correction is (that would be the DEFINITION path) but to
    acknowledge receipt and state explicitly that no prior turn exists
    in this session.

    Surface format (fixed templates, all atoms pack-sourced):

      - **Without topic** (text=None or no pack-resident lemma found):

          "correction received — pack-grounded ({pack_id}): {d1}; {d2}; {d3}.
           No prior turn in this session to correct yet."

      - **With topic** (text supplied AND pack lemma found):

          "correction received — pack-grounded ({pack_id}): {d1}; {d2}; {d3}.
           Noted topic: {lemma} ({td1}; {td2}).
           No prior turn in this session to correct yet."

    Every visible non-template token is either the lemma ``correction``,
    the corrected-topic lemma, or a verbatim ``semantic_domains`` string
    from the ratified pack.  No inference; no rewording.

    The trailing disclosure (``No prior turn in this session to correct
    yet.``) is the constant trust-boundary label distinguishing this
    cold-start acknowledgement from the post-correction teaching
    repair path (``teaching/correction.py``) which engages once a
    prior turn exists.

    Returns ``None`` if the pack is unavailable or has no entry for
    ``correction`` — callers fall through to the universal disclosure
    unchanged.
    """
    index = _pack_index()
    domains = index.get("correction")
    if not domains:
        return None
    head = "; ".join(domains[:3])
    topic_lemma = _extract_correction_topic_lemma(text) if text else None
    if topic_lemma is not None:
        # ADR-0063 — topic_lemma may resolve in a non-cognition pack
        # (e.g. ``parent`` in en_core_relations_v1).  Anchor pack stays
        # cognition (``correction`` is a cognition lemma), topic domains
        # come from whichever pack resolves the topic.
        topic_resolved = resolve_lemma(topic_lemma)
        topic_domains = topic_resolved[1] if topic_resolved is not None else ()
        topic_head = "; ".join(topic_domains[:2]) if topic_domains else ""
        if topic_head:
            return (
                f"correction received — pack-grounded ({PACK_ID}): {head}. "
                f"Noted topic: {topic_lemma} ({topic_head}). "
                f"No prior turn in this session to correct yet."
            )
        return (
            f"correction received — pack-grounded ({PACK_ID}): {head}. "
            f"Noted topic: {topic_lemma}. "
            f"No prior turn in this session to correct yet."
        )
    return (
        f"correction received — pack-grounded ({PACK_ID}): {head}. "
        f"No prior turn in this session to correct yet."
    )


_PROCEDURE_TOPIC_STOPWORDS: frozenset[str] = frozenset({
    # Pack-resident lemmas that classify but carry no topical signal
    # in a procedure utterance — dialogue fillers / copulae.
    "be",
    "have",
})


def _extract_procedure_topic_lemma(subject_text: str) -> str | None:
    """Return the **last** pack-resident topical lemma in *subject_text*.

    Procedure subjects emerge from the intent classifier as verb
    phrases (e.g. ``"define a concept"``, ``"correct an error"``,
    ``"verify a claim"``).  The procedure verb tends to be the
    first pack-resident lemma; the *topic* of the procedure tends
    to be the last.  Selecting the last pack-resident lemma
    captures the user's actual subject of interest without requiring
    POS tagging or syntactic analysis.

    Deterministic: tokens are processed left-to-right; the *last*
    token that is pack-resident AND not in the stopword set wins.

    Stopwords filter only dialogue fillers (``be`` / ``have``);
    pack-resident verbs (``define``, ``verify``, ``correct``, etc.)
    are NOT stopworded — when a procedure utterance contains only
    one pack-resident lemma and that lemma is the verb, the verb
    is the topical anchor by elimination.
    """
    if not subject_text or not isinstance(subject_text, str):
        return None
    lemmas = mounted_lemmas()
    raw = subject_text.lower()
    for ch in ",.;:!?\"'()[]{}":
        raw = raw.replace(ch, " ")
    last_match: str | None = None
    for token in raw.split():
        if not token:
            continue
        if token in _PROCEDURE_TOPIC_STOPWORDS:
            continue
        if token in lemmas:
            last_match = token
    return last_match


def pack_grounded_procedure_surface(
    subject_text: str,
    *,
    register: RegisterPack = UNREGISTERED,
) -> str | None:
    """ADR-0061 — cold-start PROCEDURE pack-grounded surface.

    A PROCEDURE intent (``"How do I X?"``, ``"How can I Y?"``) requests
    step-by-step guidance.  Procedural chains are not part of the
    reviewed teaching corpus today (teaching chains cover CAUSE and
    VERIFICATION intents only — see
    ``chat.teaching_grounding._VALID_INTENTS``).  Rather than fall
    through to the universal disclosure on every procedure question,
    this composer emits a pack-grounded acknowledgement that surfaces
    the topical lemma of the procedure and notes explicitly that
    step-by-step guidance is not yet ratified — preserving honesty
    while grounding the user's topic in pack semantics.

    Surface format (fixed template, all atoms pack-sourced):

        "procedure-grounded ({pack_id}): {lemma} ({d1}; {d2}).
         Step-by-step guidance for {lemma} is not yet ratified
         in this session."

    The trailing clause is the constant trust-boundary label,
    analogous to ``"No prior turn in this session to correct yet."``
    in the CORRECTION acknowledgement (ADR-0053 / ADR-0060).

    Returns ``None`` if no pack-resident lemma is found in
    *subject_text* — callers fall through to the universal disclosure
    unchanged (preserves the ADR-0053 honesty contract for the
    fully-unknown case).
    """
    lemma = _extract_procedure_topic_lemma(subject_text)
    if lemma is None:
        return None
    # ADR-0063 — resolve topic across all mounted lexicon packs.  The
    # surface tag follows the resolving pack id so a kinship procedure
    # (``"How do I trace my ancestor?"``) emits
    # ``procedure-grounded (en_core_relations_v1)``.
    resolved = resolve_lemma(lemma)
    if resolved is None:
        return None
    resolved_pack_id, domains = resolved
    head = "; ".join(domains[:2])
    return (
        f"procedure-grounded ({resolved_pack_id}): {lemma} ({head}). "
        f"Step-by-step guidance for {lemma} is not yet ratified in this session."
    )


def pack_grounded_comparison_surface(
    lemma_a: str,
    lemma_b: str,
    *,
    register: RegisterPack = UNREGISTERED,
) -> str | None:
    """ADR-0050 — deterministic pack-grounded surface for COMPARISON intent.

    Returns a surface that composes each lemma's pack semantic_domains
    side-by-side, with no rewording or inference:

        "{a} (d_a1; d_a2) contrasts with {b} (d_b1; d_b2) — pack-grounded
         ({pack_id}). No session evidence yet."

    Up to two semantic_domains per side are emitted to keep the surface
    compact.  All visible tokens are either the lemmas themselves or
    verbatim pack strings; the verb "contrasts with" is the fixed
    COMPARISON template constant (mirroring the relation predicate
    `contrasts_with` already humanised by ``humanize_predicate``).

    Returns ``None`` when:
      - either lemma is empty or not a string,
      - either lemma is not present in the pack,
      - the two lemmas are identical (a comparison between a term
        and itself carries no contrastive evidence — defer to the
        single-lemma ``pack_grounded_surface`` path or to the
        universal disclosure).
    """
    if not lemma_a or not isinstance(lemma_a, str):
        return None
    if not lemma_b or not isinstance(lemma_b, str):
        return None
    key_a = lemma_a.strip().lower()
    key_b = lemma_b.strip().lower()
    if not key_a or not key_b:
        return None
    if key_a == key_b:
        return None
    resolved_a = resolve_lemma(key_a)
    resolved_b = resolve_lemma(key_b)
    if resolved_a is None or resolved_b is None:
        return None
    pack_a, domains_a = resolved_a
    pack_b, domains_b = resolved_b
    head_a = "; ".join(domains_a[:2])
    head_b = "; ".join(domains_b[:2])
    # ADR-0063 — tag follows the resolving pack ids.  Cognition-only
    # comparisons stay byte-identical (both sides resolve to cognition);
    # cross-pack comparisons render the composite tag explicitly.
    if pack_a == pack_b:
        tag = f"pack-grounded ({pack_a})"
    else:
        tag = f"pack-grounded ({pack_a} × {pack_b})"
    return (
        f"{key_a} ({head_a}) contrasts with {key_b} ({head_b}) "
        f"— {tag}. No session evidence yet."
    )
