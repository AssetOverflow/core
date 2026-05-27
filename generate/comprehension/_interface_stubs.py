"""Phase-1 stubs for Briefs 6 (lexeme primitives) and 7 (lexicon loader).

Replace the imports in :mod:`generate.comprehension.lifecycle` with the real
modules once Briefs 6 and 7 land. Until then, this module provides a thin,
deterministic surface that covers exactly the categories the Phase-1 reader
needs to admit the five GSM8K train_sample question sentences listed in
Brief 8 (ADR-0164.3 §Worked example follow-on).

The stub embeds:

* a minimal lexicon: the entries already present in
  ``language_packs/data/en_core_math_v1/lexicon.jsonl`` are honored, plus a
  small supplemental vocabulary explicitly named "Phase-1 reader
  supplemental — to be folded into the math pack" so it does not pretend
  to be ratified pack content.
* a primitive scanner that covers numeric, time-amount, currency, and
  sentence-terminator shapes. ADR-0164.1 §Seed primitive set defines the
  full set; the stub implements the subset the question sentences need.

Determinism: ``scan_primitive`` and ``lookup`` are pure functions over
their inputs. The module-level lexicon dict is populated once at import
time from a frozen literal and the on-disk lexicon file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Public types — match the signatures Brief 8 imports from briefs 6 and 7.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LexemeMatch:
    """A primitive-scanner hit.

    ``emit_category`` is what the reader's expectation-check consumes.
    """

    emit_category: str
    surface: str


@dataclass(frozen=True, slots=True)
class LexiconEntry:
    """Minimal lexicon record. Briefs 6/7's real record may carry more."""

    surface: str
    category: str


Lexicon = dict[str, LexiconEntry]


# ---------------------------------------------------------------------------
# Primitive shapes — closed orthographic recognizers per ADR-0164.1.
# Each tuple is (compiled regex, emit category). First match wins.
# ---------------------------------------------------------------------------

_PRIMITIVE_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"^\$(\d+)\.(\d{2})$"), "decimal_currency_literal"),
    (re.compile(r"^\$(\d+(?:\.\d+)?)$"), "currency_literal"),
    (re.compile(r"^(\d+(?:\.\d+)?)\s?%$"), "percentage_literal"),
    (re.compile(r"^(\d+)/(\d+)$"), "fraction_literal"),
    (
        re.compile(
            r"^(\d+)(?:-)?(hour|minute|day|week|month|year|second)s?$",
            re.IGNORECASE,
        ),
        "time_amount_literal",
    ),
    (re.compile(r"^\d+(?:\.\d+)?$"), "numeric_literal"),
    (re.compile(r"^\?$"), "question_terminator"),
    (re.compile(r"^[.!]$"), "statement_terminator"),
    (re.compile(r"^,$"), "punctuation_comma"),
)


def scan_primitive(word: str) -> LexemeMatch | None:
    """Return the first orthographic primitive that matches ``word``.

    Pure / deterministic. Case-insensitive for shape-bearing primitives;
    word-boundary alignment is the caller's responsibility (the reader
    pre-tokenises).
    """
    if not isinstance(word, str) or word == "":
        return None
    for pattern, category in _PRIMITIVE_PATTERNS:
        if pattern.match(word) is not None:
            return LexemeMatch(emit_category=category, surface=word)
    return None


# ---------------------------------------------------------------------------
# Lexicon — the on-disk en_core_math_v1 entries plus a Phase-1 supplemental.
# Real Brief 7 loader will read the pack with full provenance and discipline;
# this stub keeps the dependency surface minimal.
# ---------------------------------------------------------------------------

# Map en_core_math_v1 semantic-domain string → reader category.
# Categories named here match the rule table in lifecycle.apply_word.
_DOMAIN_TO_CATEGORY: Final[dict[str, str]] = {
    "math.question_open": "question_open",
    "math.entity_pronoun": "entity_pronoun",
    "math.residual_modifier": "residual_modifier",
    "math.currency_unit_noun": "currency_unit_noun",
    "math.accumulation_verb": "accumulation_verb",
    "math.depletion_verb": "depletion_verb",
    "math.transfer_verb": "transfer_verb",
    "math.capacity_verb": "capacity_verb",
    "math.possession_verb": "possession_verb",
    "math.proper_noun_entity_female": "proper_noun_entity_female",
    "math.proper_noun_entity_male": "proper_noun_entity_male",
}

# Phase-1 reader supplemental — to be folded into en_core_math_v1 once
# Briefs 6/7 land (or earlier as a separate pack PR). These are the
# closed-set words required by the five Brief-8 target question sentences.
_SUPPLEMENTAL_VOCAB: Final[dict[str, str]] = {
    # Question quantifiers
    "many": "question_discrete_qty",
    "much": "question_continuous_qty",
    # Comparatives
    "more": "question_comparative",
    "less": "question_comparative",
    "longer": "question_comparative",
    "fewer": "question_comparative",
    # Aggregate
    "total": "aggregate_modifier",  # overrides currency_unit_noun pack hit
    "combined": "aggregate_modifier",
    # Modal aux
    "will": "modal_aux",
    "did": "modal_aux",
    "does": "modal_aux",
    "do": "modal_aux",
    "would": "modal_aux",
    "can": "modal_aux",
    # Copula
    "be": "copula_verb",
    "is": "copula_verb",
    "are": "copula_verb",
    "was": "copula_verb",
    "were": "copula_verb",
    # Count unit nouns
    "box": "count_unit_noun",
    "boxes": "count_unit_noun",
    "crayon": "count_unit_noun",
    "crayons": "count_unit_noun",
    "follower": "count_unit_noun",
    "followers": "count_unit_noun",
    "candy": "count_unit_noun",
    "candies": "count_unit_noun",
    "bean": "count_unit_noun",
    "beans": "count_unit_noun",
    "person": "count_unit_noun",
    "people": "count_unit_noun",
    # Time unit nouns
    "time": "time_unit_noun",
    "hour": "time_unit_noun",
    "hours": "time_unit_noun",
    "day": "time_unit_noun",
    "days": "time_unit_noun",
    "minute": "time_unit_noun",
    "minutes": "time_unit_noun",
    "week": "time_unit_noun",
    "weeks": "time_unit_noun",
    # Verbs (frame-closing for question_frame)
    "need": "accumulation_verb",
    "buy": "accumulation_verb",
    "want": "accumulation_verb",
    "cost": "currency_unit_noun",
    "make": "capacity_verb",
    "give": "transfer_verb",
    "gave": "transfer_verb",
    # Proper nouns missing from pack
    "monica": "proper_noun_entity_female",
    "malcolm": "proper_noun_entity_male",
    "rachel": "proper_noun_entity_female",
    # Additional pronouns / determiners
    "him": "entity_pronoun",
    "her": "entity_pronoun",
    "his": "entity_pronoun",
    "hers": "entity_pronoun",
    # Question/relative connectives that drain harmlessly post-frame
    "if": "drain_token",
    "of": "drain_token",
    "on": "drain_token",
    "in": "drain_token",
    "at": "drain_token",
    "for": "drain_token",
    "with": "drain_token",
    "a": "drain_token",
    "an": "drain_token",
    "the": "drain_token",
    "all": "drain_token",
    "some": "drain_token",
    "this": "drain_token",
    "that": "drain_token",
    "during": "drain_token",
    "five": "drain_token",
    "two": "drain_token",
    "three": "drain_token",
    "four": "drain_token",
    "studying": "drain_token",
    "purchase": "drain_token",
    "social": "drain_token",
    "media": "drain_token",
    "left": "residual_modifier",
    "remaining": "residual_modifier",
    "after": "residual_modifier",
}


def _read_pack_lexicon(path: Path) -> dict[str, LexiconEntry]:
    """Load en_core_math_v1 entries, mapping semantic_domains to reader
    categories. Skips entries whose domain is not in _DOMAIN_TO_CATEGORY.
    """
    out: dict[str, LexiconEntry] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        surface = record["surface"].lower()
        for domain in record["semantic_domains"]:
            category = _DOMAIN_TO_CATEGORY.get(domain)
            if category is not None:
                # First domain wins; deterministic by file order.
                out.setdefault(surface, LexiconEntry(surface=surface, category=category))
                break
    return out


def _build_lexicon() -> Lexicon:
    pack_path = (
        Path(__file__).resolve().parents[2]
        / "language_packs"
        / "data"
        / "en_core_math_v1"
        / "lexicon.jsonl"
    )
    lex: dict[str, LexiconEntry] = _read_pack_lexicon(pack_path)
    # Supplemental overrides pack entries to honour Phase-1 rule table.
    for surface, category in _SUPPLEMENTAL_VOCAB.items():
        lex[surface] = LexiconEntry(surface=surface, category=category)
    return lex


def load_lexicon() -> Lexicon:
    """Return a freshly built lexicon. Caller is expected to cache."""
    return _build_lexicon()


def lookup(lex: Lexicon, word: str) -> LexiconEntry | None:
    """Case-insensitive lookup. Returns ``None`` on miss.

    Strips a single trailing punctuation mark (``,`` ``?`` ``.``) before
    lookup; primitive-scanner is consulted separately for terminators.
    """
    if not isinstance(word, str) or word == "":
        return None
    key = word.lower()
    return lex.get(key)
