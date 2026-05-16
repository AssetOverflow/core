"""generate/surface.py — SentenceAssembler (ADR-0012, rev 2)

Bridges ArticulationPlan + GenerationResult.tokens into a fully coherent
surface sentence. This is the final realisation stage: every prior layer
(field walk, proposition formation, articulation) feeds here.

Contract:
  Input:  ArticulationPlan           — subject / predicate / object slots
          Sequence[str]              — ordered token walk from generate()
          DialogueRole               — assert | elaborate | question | refute
          output_language: str       — BCP-47 language tag (default "en")
          context (optional)         — SurfaceContext for cross-turn features
  Output: SentencePlan               — immutable record with .surface string

Determinism guarantee:
  Identical (plan, tokens, role, language, context) → identical output string.
  No randomness, no model calls, no state mutation.

Sentence templates by DialogueRole (English, base):
  assert    →  "{Subject} {predicate} {object}."
  elaborate →  "{Subject} {predicate} {object} — {elaboration}."
  question  →  "Does {subject} {predicate} {object}?"
  refute    →  "{Subject} does not {predicate} {object}."

Composition extensions (rev 2)
-------------------------------
When a SurfaceContext is supplied, the assembler applies additional
realisation rules on top of the base template:

  Coordination
    If elab_tokens contains >=2 content units and context.elab_conjunction
    is set, they are joined with the conjunction ("and", "but", etc.)
    rather than bare commas.  The sign of context.valence_delta determines
    the default conjunction when none is specified: positive → "and",
    negative → "but".

  Subordination
    If role is "question" and context.active_referent_surface is non-empty,
    the question is prefixed: "Given that {referent}, {question}"

  Hedging
    If context.identity_alignment < HEDGE_THRESHOLD, the output is wrapped:
    "It seems that {sentence}" (below 0.4) or "Perhaps {sentence}" (0.4-0.5).

  Contrast
    If context.valence_delta < -CONTRAST_THRESHOLD, the output is prefixed
    with "However, ".

  Pronoun coreference emission
    If the realised subject matches context.active_referent_surface
    (case-insensitive), it is replaced with the appropriate pronoun:
    "it" for neut_sg, "they" for plural, "he" / "she" for animate.

Language routing:
  Hebrew (he)  — VSO order following articulation.py convention
  Greek  (grc) — SOV order following articulation.py convention
  All others   — SVO (English default)
  Composition extensions are English-only in this revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from generate.articulation import ArticulationPlan
from generate.dialogue import DialogueRole

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STOP_SURFACES: frozenset[str] = frozenset({
    "it", "to", "a", "an", "the", "and", "or", "but", "in", "on",
    "at", "of", "for", "with", "by", "from", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "word", "what", "who", "how",
    "why", "when", "which", "that", "this", "these", "those",
})

_MAX_ELAB_TOKENS: int = 4

#: identity_alignment below this → hedge with "It seems that ..."
HEDGE_STRONG_THRESHOLD: float = 0.4
#: identity_alignment below this → hedge with "Perhaps ..."
HEDGE_SOFT_THRESHOLD: float = 0.5

#: |valence_delta| above this triggers a contrast prefix
CONTRAST_THRESHOLD: float = 0.3

#: Pronoun substitution map: slot → surface pronoun emitted in output
_SLOT_PRONOUN: dict[str, str] = {
    "neut_sg": "it",
    "plural":  "they",
    "masc_sg": "he",
    "fem_sg":  "she",
}


# ---------------------------------------------------------------------------
# SurfaceContext — optional cross-turn signal for composition extensions
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SurfaceContext:
    """
    Cross-turn signals for composition extensions.

    All fields have safe defaults so passing SurfaceContext() always works.

    Parameters
    ----------
    active_referent_surface
        Surface form of the most recently registered referent (neut_sg slot).
        Used for subordination prefix and pronoun coreference emission.
    active_referent_slot
        Which pronoun slot the active referent fills.
    identity_alignment
        identity_score.alignment from the current turn.  Triggers hedging.
    valence_delta
        current_valence - last_turn_valence.  Negative → contrast prefix.
    elab_conjunction
        Override for the coordination conjunction.
        If empty, derived from valence_delta sign.
    """
    active_referent_surface: str = ""
    active_referent_slot: str = "neut_sg"
    identity_alignment: float = 1.0
    valence_delta: float = 0.0
    elab_conjunction: str = ""


# ---------------------------------------------------------------------------
# SentencePlan — immutable record of the assembled sentence components
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SentencePlan:
    """Fully resolved sentence before punctuation is appended."""
    subject: str
    predicate_phrase: str
    object_phrase: str | None
    elaboration: str | None
    dialogue_role: str
    output_language: str
    surface: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cap(word: str) -> str:
    if not word:
        return word
    return word[0].upper() + word[1:]


def _elaboration_tokens(
    tokens: Sequence[str],
    already_used: frozenset[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if (
            low in _STOP_SURFACES
            or low in already_used
            or low in seen
            or not tok.isalpha()
        ):
            continue
        seen.add(low)
        result.append(tok)
        if len(result) >= _MAX_ELAB_TOKENS:
            break
    return result


def _join_elab(
    elab_tokens: list[str],
    conjunction: str,
) -> str:
    """Join elaboration tokens with a conjunction between the last two."""
    if not elab_tokens:
        return ""
    if len(elab_tokens) == 1:
        return elab_tokens[0]
    head = ", ".join(elab_tokens[:-1])
    return f"{head} {conjunction} {elab_tokens[-1]}"


def _pick_conjunction(valence_delta: float, override: str) -> str:
    if override:
        return override
    return "but" if valence_delta < 0 else "and"


def _coref_subject(subject: str, ctx: SurfaceContext | None) -> str:
    """Replace subject with pronoun if it matches the active referent."""
    if ctx is None or not ctx.active_referent_surface:
        return subject
    if subject.casefold() == ctx.active_referent_surface.casefold():
        pronoun = _SLOT_PRONOUN.get(ctx.active_referent_slot, "it")
        # Preserve capitalisation: if subject was capitalised, so is pronoun
        return pronoun[0].upper() + pronoun[1:] if subject and subject[0].isupper() else pronoun
    return subject


def _apply_hedge(surface: str, alignment: float) -> str:
    """Wrap surface in hedging language if alignment is low."""
    if alignment < HEDGE_STRONG_THRESHOLD:
        return f"It seems that {surface[0].lower() + surface[1:] if surface else surface}"
    if alignment < HEDGE_SOFT_THRESHOLD:
        return f"Perhaps {surface[0].lower() + surface[1:] if surface else surface}"
    return surface


def _apply_contrast(surface: str, valence_delta: float) -> str:
    """Prepend contrast marker when valence flips negatively."""
    if valence_delta < -CONTRAST_THRESHOLD:
        return f"However, {surface[0].lower() + surface[1:] if surface else surface}"
    return surface


def _apply_subordination(
    surface: str,
    role: str,
    ctx: SurfaceContext | None,
    lang: str,
) -> str:
    """Prepend subordinate clause for questions with an active referent."""
    if lang != "en":
        return surface
    if role != "question":
        return surface
    if ctx is None or not ctx.active_referent_surface:
        return surface
    referent = ctx.active_referent_surface
    # Lowercase the question start after the subordinate clause
    rest = surface[0].lower() + surface[1:] if surface else surface
    return f"Given that {referent}, {rest}"


# ---------------------------------------------------------------------------
# Language assemblers
# ---------------------------------------------------------------------------

def _assemble_en(
    subject: str,
    predicate: str,
    object_: str | None,
    elab_tokens: list[str],
    role: str,
    ctx: SurfaceContext | None,
) -> str:
    """English SVO sentence assembly with composition extensions."""
    # Pronoun coreference emission
    subj_out = _coref_subject(subject, ctx)
    subj = _cap(subj_out)
    obj = object_ or ""

    conjunction = _pick_conjunction(
        ctx.valence_delta if ctx else 0.0,
        ctx.elab_conjunction if ctx else "",
    )
    elab_str = _join_elab(elab_tokens, conjunction) if elab_tokens else ""

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
        surface = (f"{base} — {elab_str}." if elab_str else base + ".")

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

    # Composition extensions (English only)
    surface = _apply_subordination(surface, role, ctx, lang="en")
    if ctx is not None:
        surface = _apply_contrast(surface, ctx.valence_delta)
        surface = _apply_hedge(surface, ctx.identity_alignment)

    return surface


def _assemble_he(
    subject: str,
    predicate: str,
    object_: str | None,
    elab_tokens: list[str],
    role: str,
) -> str:
    """Hebrew VSO — verb precedes subject, object follows."""
    obj = object_ or ""
    if role == "question":
        parts = ["\u05d4\u05d0\u05dd", predicate, subject]
        if obj:
            parts.append(obj)
        return " ".join(parts) + "?"
    if role == "refute":
        parts = ["\u05dc\u05d0", predicate, subject]
        if obj:
            parts.append(obj)
        return " ".join(parts) + "."
    parts = [predicate, subject]
    if obj:
        parts.append(obj)
    base = " ".join(parts)
    if role == "elaborate" and elab_tokens:
        elab = ", ".join(elab_tokens)
        return f"{base} \u2014 {elab}."
    return base + "."


def _assemble_grc(
    subject: str,
    predicate: str,
    object_: str | None,
    elab_tokens: list[str],
    role: str,
) -> str:
    """Ancient Greek SOV — subject, object, verb."""
    subj = _cap(subject)
    obj = object_ or ""
    if role == "question":
        parts = [subj]
        if obj:
            parts.append(obj)
        parts.append(predicate)
        return " ".join(parts) + ";"
    if role == "refute":
        neg = "\u03bf\u1f50"
        parts = [subj, neg]
        if obj:
            parts.append(obj)
        parts.append(predicate)
        return " ".join(parts) + "."
    parts = [subj]
    if obj:
        parts.append(obj)
    parts.append(predicate)
    base = " ".join(parts)
    if role == "elaborate" and elab_tokens:
        elab = ", ".join(elab_tokens)
        return f"{base} \u2014 {elab}."
    return base + "."


# ---------------------------------------------------------------------------
# SentenceAssembler — public API
# ---------------------------------------------------------------------------

class SentenceAssembler:
    """Stateless assembler: maps (plan, tokens, role, context) to a surface sentence.

    No field state is held. All inputs are consumed read-only.
    The same instance may be shared across sessions.
    """

    def assemble(
        self,
        plan: ArticulationPlan,
        tokens: Sequence[str],
        role: DialogueRole = "assert",
        context: SurfaceContext | None = None,
    ) -> SentencePlan:
        """Produce a SentencePlan (with .surface) from an ArticulationPlan.

        Steps:
          1. Extract slot strings from the plan.
          2. Filter elaboration tokens from the walk.
          3. Route to language-specific assembler.
          4. Apply composition extensions (English only).
          5. Return an immutable SentencePlan.
        """
        subject = plan.subject or ""
        predicate = plan.predicate or ""
        object_ = plan.object or None
        lang = plan.output_language or "en"
        role_str = str(role)

        used_slots: frozenset[str] = frozenset(
            w.lower()
            for w in [subject, predicate, object_]
            if w
        )
        elab_tokens = _elaboration_tokens(tokens, used_slots)

        if not subject and not predicate:
            fallback = plan.surface or " ".join(t for t in tokens if t)
            return SentencePlan(
                subject="",
                predicate_phrase="",
                object_phrase=object_,
                elaboration=None,
                dialogue_role=role_str,
                output_language=lang,
                surface=fallback,
            )

        if lang == "he":
            surface = _assemble_he(subject, predicate, object_, elab_tokens, role_str)
        elif lang == "grc":
            surface = _assemble_grc(subject, predicate, object_, elab_tokens, role_str)
        else:
            surface = _assemble_en(subject, predicate, object_, elab_tokens, role_str, context)

        return SentencePlan(
            subject=subject,
            predicate_phrase=predicate,
            object_phrase=object_,
            elaboration=_join_elab(elab_tokens, _pick_conjunction(
                context.valence_delta if context else 0.0,
                context.elab_conjunction if context else "",
            )) if elab_tokens else None,
            dialogue_role=role_str,
            output_language=lang,
            surface=surface,
        )


# Module-level default instance (stateless — safe to share)
default_assembler = SentenceAssembler()


def assemble(
    plan: ArticulationPlan,
    tokens: Sequence[str],
    role: DialogueRole = "assert",
    context: SurfaceContext | None = None,
) -> str:
    """Convenience wrapper returning only the surface string."""
    return default_assembler.assemble(plan, tokens, role, context).surface
