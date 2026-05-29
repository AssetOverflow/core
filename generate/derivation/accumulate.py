"""ADR-0178 GB-3b.1 — single-referent accumulation chaining.

The first cross-clause *comprehension* reading: one actor's quantity changes over
successive clauses (``Sam has 14 apples. He buys 9 more.`` -> ``14 + 9``). It is
the safe specialisation of the cross-clause sum that GB-3a's referent guard
correctly refuses wholesale (the ``Alice has 6 … Tom has 2 …`` hazard): we chain
across clauses **only** when (a) the later clause stays on the **same referent**
and (b) it carries a **licensed change cue** whose polarity is unambiguous.
Otherwise we refuse — the guard is generalised, never weakened.

Reading:

1. **Anchor** — clause 1 must establish exactly one quantity ``(actor, N, unit)``.
2. **Change steps** — each later quantity-bearing clause applies ``+ M`` (gain) or
   ``- M`` (loss) to the running total, where ``M`` is the clause's single grounded
   quantity, taken **in the anchor's unit** (``9 more`` = 9 more *apples*; the unit
   is inherited from the running total, which is what accumulation means).
3. **Gate** — the constructed chain runs through the unchanged self-verification
   gate (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness). The gate keeps
   wrong=0; this only proposes a structurally-licensed candidate.

Polarity (ordered, so the ambiguous ``gives`` is resolved, never guessed):

* ``more`` present                          -> **gain** (covers ``buys/gets/…
  N more`` and ``gives her N more`` — the subject is the recipient);
* else an unambiguous **loss** verb         -> **loss**;
* else ``gives``/``gave`` with ``to``/``away`` -> **loss** (gives N *to* someone);
* else an unambiguous **gain** verb         -> **gain**;
* else                                       -> **refuse** (no guessing).

Referent guard (wrong=0-critical; the ADR-0174 multi-actor hazard's defensive fix,
built minimally in the clean lane rather than resurrecting the retired resolver):
a later clause stays on the anchor's referent iff its **subject token** is a
pronoun (``He/She/They/…``) or the same name as the anchor's subject. A **new named
subject** (a different capitalised non-pronoun first token, e.g. ``Tom``) -> refuse.
Pronoun gender/number is **not** matched (that was the old resolver's trap); a new
*name* is the only signal, and it triggers refusal, not resolution.

Sealed (no ``chat/`` import); deterministic; refuse-preferring.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

# Closed change-cue lexeme sets (ADR-0165: lexemes, not grammar templates; refined
# by the CP ledger, not asserted complete). Sorted use keeps cue selection stable.
_GAIN_VERBS: Final[frozenset[str]] = frozenset(
    {
        "buys", "bought", "gets", "got", "finds", "found", "picks", "picked",
        "earns", "earned", "receives", "received", "collects", "collected",
        "wins", "won", "makes", "made", "gains", "gained", "adds", "added",
    }
)
_LOSS_VERBS: Final[frozenset[str]] = frozenset(
    {
        "loses", "lost", "spends", "spent", "uses", "used", "eats", "ate",
        "sells", "sold", "donates", "donated", "drops", "dropped", "removes",
        "removed", "breaks", "broke",
    }
)
_PRONOUNS: Final[frozenset[str]] = frozenset(
    {"he", "she", "they", "it", "him", "her", "them", "his", "hers", "its", "their", "we", "i", "you"}
)

_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+")


def _subject_token(clause: str) -> str | None:
    """The clause's leading word token (its surface subject), or None if wordless."""
    match = _WORD_RE.search(clause)
    return match.group(0) if match is not None else None


def _same_referent(clause: str, anchor_subject: str | None) -> bool:
    """True iff ``clause`` does not introduce a new *named* subject.

    Conservative: a leading pronoun continues the referent; a leading token equal
    to the anchor's subject continues it; any other capitalised (named) leading
    token is a *new actor* and breaks the referent (-> caller refuses).
    """
    subject = _subject_token(clause)
    if subject is None:
        return True  # wordless fragment carries no new actor
    if subject.lower() in _PRONOUNS:
        return True
    if anchor_subject is not None and subject == anchor_subject:
        return True
    # A new capitalised, non-pronoun leading token is a new named actor.
    return not subject[:1].isupper()


def _polarity(clause: str) -> int | None:
    """+1 (gain), -1 (loss), or None (ambiguous / no licensed change cue -> refuse)."""
    tokens = set(_tokens(clause))
    if "more" in tokens:
        return +1
    loss = bool(_LOSS_VERBS & tokens)
    gain = bool(_GAIN_VERBS & tokens)
    gives = "gives" in tokens or "gave" in tokens
    directional = "to" in tokens or "away" in tokens
    if loss and not gain:
        return -1
    if gives and directional and not gain and not loss:
        return -1
    if gain and not loss:
        return +1
    return None


def _cue(clause: str, polarity: int) -> str:
    """A grounded cue lexeme present in the clause (for the gate's cue check)."""
    tokens = set(_tokens(clause))
    if "more" in tokens and polarity > 0:
        return "more"
    verbs = _GAIN_VERBS if polarity > 0 else _LOSS_VERBS
    present = sorted(verbs & tokens)
    if present:
        return present[0]
    return "gives"  # the only remaining licensed loss path (gives … to/away)


def _build_accumulation(
    problem_text: str, *, drop_isolated_foreign: bool
) -> GroundedDerivation | None:
    """Construct the single-referent accumulation chain (ungated).

    ``drop_isolated_foreign`` (ADR-0182): when a change clause carries more than
    one quantity, drop those with a **non-empty unit foreign to the anchor's unit**
    (a candidate distractor — ``studies for 3 hours`` among ``pencils``) and proceed
    if exactly one same-unit/unitless change remains. With the flag off this is the
    strict GB-3b.1 reading (a multi-quantity change clause refuses), so
    :func:`compose_accumulation` is byte-identical to its pre-ADR-0182 behavior.
    The distractor-skip reading is **never committed alone** — it only ever enters
    the pool to force a disagreement refusal (see :mod:`generate.derivation.pool`).
    """
    clauses = segment_clauses(problem_text)
    quantity_clauses = [c for c in clauses if extract_quantities(c)]
    if len(quantity_clauses) < 2:
        return None

    anchor_clause, *change_clauses = quantity_clauses
    anchor_quantities = extract_quantities(anchor_clause)
    if len(anchor_quantities) != 1:
        return None  # the anchor must establish exactly one quantity (GB-3b.1 scope)
    start = anchor_quantities[0]
    anchor_subject = _subject_token(anchor_clause)

    steps: list[Step] = []
    for clause in change_clauses:
        if not _same_referent(clause, anchor_subject):
            return None  # new named actor -> referent hazard -> refuse
        change_quantities = list(extract_quantities(clause))
        if drop_isolated_foreign and len(change_quantities) > 1:
            change_quantities = [
                q for q in change_quantities if not (q.unit and q.unit != start.unit)
            ]
        if len(change_quantities) != 1:
            return None  # one change per clause (multi-change is GB-3b.2)
        polarity = _polarity(clause)
        if polarity is None:
            return None  # no unambiguous licensed change cue -> refuse
        change = change_quantities[0]
        # The change is in the running total's dimension ("9 more" = 9 more apples).
        operand = Quantity(value=change.value, unit=start.unit, source_token=change.source_token)
        op = "add" if polarity > 0 else "subtract"
        steps.append(Step(op=op, operand=operand, cue=_cue(clause, polarity)))

    if not steps:
        return None
    return GroundedDerivation(start=start, steps=tuple(steps))


# ADR-0182 anchor-skip: sub-clause split on conjunctions. A single sentence can pack
# a state and its change ("Tom has 8 tickets and buys 4 more tickets") — the
# sentence-level segmenter (used everywhere; not changed) keeps them together. This
# finer split is *local* to the ungated candidate generator, so it cannot move
# GB-1/GB-2/serving/practice (which never call it). Lexeme-level (ADR-0165): it names
# coordinating conjunctions, it does not parse grammar.
_CONJUNCTION_SPLIT: Final[re.Pattern[str]] = re.compile(r",?\s+(?:and then|and|then)\s+")


def _sub_clauses(problem_text: str) -> list[str]:
    """Sentence clauses, each further split on coordinating conjunctions."""
    parts: list[str] = []
    for clause in segment_clauses(problem_text):
        parts.extend(p.strip() for p in _CONJUNCTION_SPLIT.split(clause) if p.strip())
    return parts


def _build_accumulation_anchor_skip(problem_text: str) -> GroundedDerivation | None:
    """ADR-0182 — accumulation over sub-clauses, skipping a leading all-foreign block.

    Reads ``A train travels 60 mph for 2 hours. Tom has 8 tickets and buys 4 more
    tickets.`` by skipping the (anchor-position) train block — its quantities cannot
    seed an anchor (≠1 quantity) — and anchoring on the first single-quantity
    sub-clause (``Tom has 8 tickets``), then chaining its conjunction-mate change
    (``buys 4 more`` → +4). The skipped block's quantities go unused; the pool's
    isolated-foreign exemption then classifies the reading ``exempt`` (commit-
    ineligible), so it can only force a disagreement refusal, never commit. Ungated.
    """
    sub_clauses = [(s, extract_quantities(s)) for s in _sub_clauses(problem_text)]
    quantity_subs = [(s, qs) for s, qs in sub_clauses if qs]
    if len(quantity_subs) < 2:
        return None

    # Anchor = first single-quantity sub-clause; leading non-anchorable (≠1
    # quantity) sub-clauses are skipped (candidate distractor blocks).
    anchor_idx = next((i for i, (_, qs) in enumerate(quantity_subs) if len(qs) == 1), None)
    if anchor_idx is None:
        return None
    anchor_sub, anchor_qs = quantity_subs[anchor_idx]
    start = anchor_qs[0]
    anchor_subject = _subject_token(anchor_sub)

    steps: list[Step] = []
    for sub, qs in quantity_subs[anchor_idx + 1:]:
        if not _same_referent(sub, anchor_subject):
            return None  # new named actor -> referent hazard -> refuse
        if len(qs) != 1:
            return None  # one change per sub-clause (multi-change is GB-3b.2)
        polarity = _polarity(sub)
        if polarity is None:
            return None  # no unambiguous licensed change cue -> refuse
        change = qs[0]
        operand = Quantity(value=change.value, unit=start.unit, source_token=change.source_token)
        op = "add" if polarity > 0 else "subtract"
        steps.append(Step(op=op, operand=operand, cue=_cue(sub, polarity)))

    if not steps:
        return None
    return GroundedDerivation(start=start, steps=tuple(steps))


def compose_accumulation(problem_text: str) -> Resolution | None:
    """GB-3b.1 composer — single-referent gain/loss accumulation. Refuse-preferring.

    The strict (commit) reading: it gates the no-distractor-skip derivation through
    the unchanged self-verification gate. Behavior is byte-identical to pre-ADR-0182.
    """
    derivation = _build_accumulation(problem_text, drop_isolated_foreign=False)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def accumulation_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]:
    """ADR-0182 — the ungated accumulation readings for cross-composer pooling.

    Three readings: the strict GB-3b.1 reading, the distractor-skip reading (drops an
    isolated-foreign quantity in a multi-quantity change clause — 0014), and the
    anchor-skip reading (skips a leading all-foreign block + reads a conjunction-mate
    intra-sentence change — 0016). Ungated: the pool classifies each (``complete``
    commits, ``exempt`` refuses-only) and the disagreement rule does the wrong=0 work.
    Deterministic; de-dup is the pool's job.
    """
    candidates: list[GroundedDerivation] = []
    for drop in (False, True):
        derivation = _build_accumulation(problem_text, drop_isolated_foreign=drop)
        if derivation is not None:
            candidates.append(derivation)
    anchor_skip = _build_accumulation_anchor_skip(problem_text)
    if anchor_skip is not None:
        candidates.append(anchor_skip)
    return tuple(candidates)
