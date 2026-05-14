"""generate/surface.py — SentenceAssembler (ADR-0012)

Bridges ArticulationPlan + GenerationResult.tokens into a fully coherent
surface sentence. This is the final realisation stage: every prior layer
(field walk, proposition formation, articulation) feeds here.

Contract:
  Input:  ArticulationPlan           — subject / predicate / object slots
          Sequence[str]              — ordered token walk from generate()
          DialogueRole               — assert | elaborate | question | refute
          output_language: str       — BCP-47 language tag (default "en")
  Output: str                        — a single grammatical sentence

Determinism guarantee:
  Identical (plan, tokens, role, language) → identical output string.
  No randomness, no model calls, no state mutation.

Sentence templates by DialogueRole (English):
  assert    →  "{Subject} {predicate} {object}."
  elaborate →  "{Subject} {predicate} {object} — {elaboration}."
  question  →  "Does {subject} {predicate} {object}?"
  refute    →  "{Subject} does not {predicate} {object}."

Elaboration material is drawn from the walk tokens that survive
_STOP_SURFACES filtering, deduplicated, capped at _MAX_ELAB_TOKENS, and
joined with commas. This keeps elaboration grounded in the actual
manifold walk rather than invented content.

Language routing:
  Hebrew (he)  — VSO order following articulation.py convention
  Greek  (grc) — SOV order following articulation.py convention
  All others   — SVO (English default)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from generate.articulation import ArticulationPlan
from generate.dialogue import DialogueRole

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tokens that carry no propositional content; excluded from elaboration.
_STOP_SURFACES: frozenset[str] = frozenset({
    "it", "to", "a", "an", "the", "and", "or", "but", "in", "on",
    "at", "of", "for", "with", "by", "from", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "word", "what", "who", "how",
    "why", "when", "which", "that", "this", "these", "those",
})

_MAX_ELAB_TOKENS: int = 4   # max walk tokens woven into elaboration


# ---------------------------------------------------------------------------
# SentencePlan — immutable record of the assembled sentence components
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SentencePlan:
    """Fully resolved sentence before punctuation is appended."""
    subject: str
    predicate_phrase: str
    object_phrase: str | None
    elaboration: str | None          # None unless role == "elaborate"
    dialogue_role: str
    output_language: str
    surface: str                     # the final rendered sentence


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cap(word: str) -> str:
    """Capitalise the first codepoint; leave the rest as-is."""
    if not word:
        return word
    return word[0].upper() + word[1:]


def _elaboration_tokens(
    tokens: Sequence[str],
    already_used: frozenset[str],
) -> list[str]:
    """Pick walk tokens that add propositional content beyond the slots."""
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


def _assemble_en(
    subject: str,
    predicate: str,
    object_: str | None,
    elab_tokens: list[str],
    role: str,
) -> str:
    """English SVO sentence assembly."""
    subj = _cap(subject)
    obj = object_ or ""

    if role == "assert":
        parts = [subj, predicate]
        if obj:
            parts.append(obj)
        return " ".join(parts) + "."

    if role == "elaborate":
        parts = [subj, predicate]
        if obj:
            parts.append(obj)
        base = " ".join(parts)
        if elab_tokens:
            elab = ", ".join(elab_tokens)
            return f"{base} — {elab}."
        return base + "."

    if role == "question":
        # "Does subject predicate object?"
        parts = ["Does", subject, predicate]
        if obj:
            parts.append(obj)
        return " ".join(parts) + "?"

    if role == "refute":
        # "Subject does not predicate object."
        parts = [subj, "does not", predicate]
        if obj:
            parts.append(obj)
        return " ".join(parts) + "."

    # fallback — treat as assert
    parts = [subj, predicate]
    if obj:
        parts.append(obj)
    return " ".join(parts) + "."


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
        neg = "\u03bf\u1f50"   # ou
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
    """Stateless assembler: maps (plan, tokens, role) to a surface sentence.

    No field state is held. All inputs are consumed read-only.
    The same instance may be shared across sessions.
    """

    def assemble(
        self,
        plan: ArticulationPlan,
        tokens: Sequence[str],
        role: DialogueRole = "assert",
    ) -> SentencePlan:
        """Produce a SentencePlan (with .surface) from an ArticulationPlan.

        Steps:
          1. Extract slot strings from the plan.
          2. Filter elaboration tokens from the walk.
          3. Route to language-specific assembler.
          4. Return an immutable SentencePlan.
        """
        subject = plan.subject or ""
        predicate = plan.predicate or ""
        object_ = plan.object or None
        lang = plan.output_language or "en"
        role_str = str(role)

        # Collect slots already present so elaboration doesn't repeat them.
        used_slots: frozenset[str] = frozenset(
            w.lower()
            for w in [subject, predicate, object_]
            if w
        )
        elab_tokens = _elaboration_tokens(tokens, used_slots)

        # Language dispatch
        if lang == "he":
            surface = _assemble_he(subject, predicate, object_, elab_tokens, role_str)
        elif lang == "grc":
            surface = _assemble_grc(subject, predicate, object_, elab_tokens, role_str)
        else:
            surface = _assemble_en(subject, predicate, object_, elab_tokens, role_str)

        return SentencePlan(
            subject=subject,
            predicate_phrase=predicate,
            object_phrase=object_,
            elaboration=", ".join(elab_tokens) if elab_tokens else None,
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
) -> str:
    """Convenience wrapper returning only the surface string."""
    return default_assembler.assemble(plan, tokens, role).surface
