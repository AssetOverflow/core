"""generate/surface.py — deterministic sentence assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from generate.articulation import ArticulationPlan
from generate.dialogue import DialogueRole

_STOP_SURFACES: frozenset[str] = frozenset({
    "it", "to", "a", "an", "the", "and", "or", "but", "in", "on",
    "at", "of", "for", "with", "by", "from", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "word", "what", "who", "how",
    "why", "when", "which", "that", "this", "these", "those",
})
_MAX_ELAB_TOKENS: int = 4
# Legacy default thresholds — used when SurfaceContext is constructed
# without pack-supplied identity surface preferences.  Identical to the
# pre-ADR-0028 hardcoded values; do not change without bumping every
# downstream test that asserts on these constants.
HEDGE_STRONG_THRESHOLD: float = 0.4
HEDGE_SOFT_THRESHOLD: float = 0.5
_DEFAULT_HEDGE_STRONG_PHRASE: str = "It seems that"
_DEFAULT_HEDGE_SOFT_PHRASE: str = "Perhaps"
_DEFAULT_QUALIFIER_PHRASE: str = "In some cases,"
_DEFAULT_QUALIFIED_BAND_HIGH: float = 0.75
# ADR-0030 — depth-language hedge phrases.  Same thresholds and
# claim_strength policy from the identity pack apply to Hebrew and
# Koine Greek, but the hedge surface strings are language-specific
# (per-pack overrides are deferred to a future schema bump).  Tuple
# layout: (strong, soft, qualifier).
_DEPTH_HEDGE_PHRASES: dict[str, tuple[str, str, str]] = {
    "he": (
        "נראה ש",         # "nir'eh she" — it seems that
        "אולי",                  # "ulai" — perhaps
        "במקרים מסוימים,",  # "be'mikrim mesuyamim," — in some cases,
    ),
    "grc": (
        "δοκεῖ ὅτι",  # "dokei hoti" — it seems that
        "ἴσως",                              # "isos" — perhaps
        "ἐνίοτε,",                # "eniote," — at times,
    ),
}
CONTRAST_THRESHOLD: float = 0.3
_SLOT_PRONOUN: dict[str, str] = {
    "neut_sg": "it",
    "plural": "they",
    "masc_sg": "he",
    "fem_sg": "she",
}


@dataclass(frozen=True, slots=True)
class SurfaceContext:
    active_referent_surface: str = ""
    active_referent_slot: str = "neut_sg"
    identity_alignment: float = 1.0
    valence_delta: float = 0.0
    elab_conjunction: str = ""
    # ADR-0028 — pack-supplied identity surface preferences.  Defaults
    # preserve the pre-ADR ``_apply_hedge`` behavior byte-for-byte when
    # the chat runtime is constructed without an identity-pack manifold
    # (no test should ever exercise that path post-ADR-0027, but the
    # defaults keep ``SurfaceContext()`` legal and harmless).
    hedge_threshold_strong: float = HEDGE_STRONG_THRESHOLD
    hedge_threshold_soft: float = HEDGE_SOFT_THRESHOLD
    preferred_hedge_strong: str = _DEFAULT_HEDGE_STRONG_PHRASE
    preferred_hedge_soft: str = _DEFAULT_HEDGE_SOFT_PHRASE
    claim_strength: str = "balanced"
    qualified_band_high: float = _DEFAULT_QUALIFIED_BAND_HIGH
    preferred_qualifier: str = _DEFAULT_QUALIFIER_PHRASE


@dataclass(frozen=True, slots=True)
class SentencePlan:
    subject: str
    predicate_phrase: str
    object_phrase: str | None
    elaboration: str | None
    dialogue_role: str
    output_language: str
    surface: str


def _cap(word: str) -> str:
    return word[0].upper() + word[1:] if word else word


def _elaboration_tokens(tokens: Sequence[str], already_used: frozenset[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in _STOP_SURFACES or low in already_used or low in seen or not tok.isalpha():
            continue
        seen.add(low)
        result.append(tok)
        if len(result) >= _MAX_ELAB_TOKENS:
            break
    return result


def _join_elab(elab_tokens: list[str], conjunction: str) -> str:
    if not elab_tokens:
        return ""
    if len(elab_tokens) == 1:
        return elab_tokens[0]
    return f"{', '.join(elab_tokens[:-1])} {conjunction} {elab_tokens[-1]}"


def _pick_conjunction(valence_delta: float, override: str) -> str:
    return override or ("but" if valence_delta < 0 else "and")


def _elaboration_string(elab_tokens: list[str], ctx: SurfaceContext | None) -> str:
    return _join_elab(
        elab_tokens,
        _pick_conjunction(
            ctx.valence_delta if ctx else 0.0,
            ctx.elab_conjunction if ctx else "",
        ),
    )


def _coref_subject(subject: str, ctx: SurfaceContext | None) -> str:
    if ctx is None or not ctx.active_referent_surface:
        return subject
    if subject.casefold() == ctx.active_referent_surface.casefold():
        return _SLOT_PRONOUN.get(ctx.active_referent_slot, "it")
    return subject


def _lower_first(surface: str) -> str:
    return surface[0].lower() + surface[1:] if surface else surface


def _apply_hedge(surface: str, ctx: SurfaceContext, lang: str = "en") -> str:
    """Apply identity-pack-supplied hedge and claim-strength shaping.

    Bands, in descending hedge strength:

    1. ``alignment < hedge_threshold_strong``  → strong hedge phrase.
    2. ``alignment < hedge_threshold_soft``    → soft hedge phrase.
    3. Otherwise, in the *marginal* band
       ``[hedge_threshold_soft, qualified_band_high)``:
       - ``claim_strength == "qualified"``    → prepend ``preferred_qualifier``.
       - ``claim_strength == "affirmative"``  → leave assertion bare.
       - ``claim_strength == "balanced"``     → leave assertion bare.
    4. Above ``qualified_band_high``          → leave assertion bare.

    Thresholds and ``claim_strength`` come from the identity pack
    (carried on ``ctx``) regardless of ``lang``.  Hedge phrases come
    from ``ctx`` for English and from ``_DEPTH_HEDGE_PHRASES`` for
    Hebrew (``"he"``) and Koine Greek (``"grc"``) — ADR-0030.
    """
    alignment = ctx.identity_alignment
    if lang in _DEPTH_HEDGE_PHRASES:
        strong_phrase, soft_phrase, qualifier_phrase = _DEPTH_HEDGE_PHRASES[lang]
    else:
        strong_phrase = ctx.preferred_hedge_strong
        soft_phrase = ctx.preferred_hedge_soft
        qualifier_phrase = ctx.preferred_qualifier
    if alignment < ctx.hedge_threshold_strong:
        return f"{strong_phrase} {_lower_first(surface)}"
    if alignment < ctx.hedge_threshold_soft:
        return f"{soft_phrase} {_lower_first(surface)}"
    if (
        ctx.claim_strength == "qualified"
        and alignment < ctx.qualified_band_high
    ):
        return f"{qualifier_phrase} {_lower_first(surface)}"
    return surface


def _apply_contrast(surface: str, valence_delta: float) -> str:
    if valence_delta < -CONTRAST_THRESHOLD:
        return f"However, {_lower_first(surface)}"
    return surface


def _apply_subordination(surface: str, role: str, ctx: SurfaceContext | None, lang: str) -> str:
    if lang != "en" or role != "question" or ctx is None or not ctx.active_referent_surface:
        return surface
    return f"Given that {ctx.active_referent_surface}, {_lower_first(surface)}"


def _assemble_en(
    subject: str,
    predicate: str,
    object_: str | None,
    elaboration: str,
    role: str,
    ctx: SurfaceContext | None,
) -> str:
    subj_out = _coref_subject(subject, ctx)
    subj = _cap(subj_out)
    obj = object_ or ""
    if role == "assert":
        parts = [subj, predicate]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "."
    elif role == "elaborate":
        parts = [subj, predicate]
        if obj:
            parts.append(obj)
        base = " ".join(parts)
        surface = f"{base} — {elaboration}." if elaboration else base + "."
    elif role == "question":
        parts = ["Does", subj_out, predicate]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "?"
    elif role == "refute":
        parts = [subj, "does not", predicate]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "."
    else:
        parts = [subj, predicate]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "."
    surface = _apply_subordination(surface, role, ctx, lang="en")
    if ctx is not None:
        surface = _apply_contrast(surface, ctx.valence_delta)
        surface = _apply_hedge(surface, ctx)
    return surface


def _assemble_he(
    subject: str,
    predicate: str,
    object_: str | None,
    elaboration: str,
    role: str,
    ctx: SurfaceContext | None,
) -> str:
    obj = object_ or ""
    if role == "question":
        parts = ["\u05d4\u05d0\u05dd", predicate, subject]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "?"
    elif role == "refute":
        parts = ["\u05dc\u05d0", predicate, subject]
        if obj:
            parts.append(obj)
        surface = " ".join(parts) + "."
    else:
        parts = [predicate, subject]
        if obj:
            parts.append(obj)
        base = " ".join(parts)
        surface = (
            f"{base} \u2014 {elaboration}."
            if role == "elaborate" and elaboration
            else base + "."
        )
    if ctx is not None:
        surface = _apply_hedge(surface, ctx, lang="he")
    return surface


def _assemble_grc(
    subject: str,
    predicate: str,
    object_: str | None,
    elaboration: str,
    role: str,
    ctx: SurfaceContext | None,
) -> str:
    subj = _cap(subject)
    obj = object_ or ""
    if role == "question":
        parts = [subj]
        if obj:
            parts.append(obj)
        parts.append(predicate)
        surface = " ".join(parts) + ";"
    elif role == "refute":
        parts = [subj, "\u03bf\u1f50"]
        if obj:
            parts.append(obj)
        parts.append(predicate)
        surface = " ".join(parts) + "."
    else:
        parts = [subj]
        if obj:
            parts.append(obj)
        parts.append(predicate)
        base = " ".join(parts)
        surface = (
            f"{base} \u2014 {elaboration}."
            if role == "elaborate" and elaboration
            else base + "."
        )
    if ctx is not None:
        surface = _apply_hedge(surface, ctx, lang="grc")
    return surface


class SentenceAssembler:
    def assemble(
        self,
        plan: ArticulationPlan,
        tokens: Sequence[str],
        role: DialogueRole = "assert",
        context: SurfaceContext | None = None,
    ) -> SentencePlan:
        subject = plan.subject or ""
        predicate = plan.predicate or ""
        object_ = plan.object or None
        lang = plan.output_language or "en"
        role_str = str(role)
        used_slots = frozenset(w.lower() for w in [subject, predicate, object_] if w)
        elab_tokens = _elaboration_tokens(tokens, used_slots)
        elaboration = _elaboration_string(elab_tokens, context) if elab_tokens else ""
        if not subject and not predicate:
            fallback = plan.surface or " ".join(t for t in tokens if t)
            return SentencePlan("", "", object_, None, role_str, lang, fallback)
        if lang == "he":
            surface = _assemble_he(
                subject, predicate, object_, elaboration, role_str, context,
            )
        elif lang == "grc":
            surface = _assemble_grc(
                subject, predicate, object_, elaboration, role_str, context,
            )
        else:
            surface = _assemble_en(subject, predicate, object_, elaboration, role_str, context)
        return SentencePlan(
            subject=subject,
            predicate_phrase=predicate,
            object_phrase=object_,
            elaboration=elaboration or None,
            dialogue_role=role_str,
            output_language=lang,
            surface=surface,
        )


default_assembler = SentenceAssembler()


def assemble(
    plan: ArticulationPlan,
    tokens: Sequence[str],
    role: DialogueRole = "assert",
    context: SurfaceContext | None = None,
) -> str:
    return default_assembler.assemble(plan, tokens, role, context).surface
