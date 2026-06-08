"""Combined-rate prose reader (CMB-c): explicit two-rate prose -> CombinedRateProblem.

Reads ONLY explicit combined-rate problems — two rates over one shared unit, combined by an
explicit cooperative (``sum``) or opposing-flow (``difference``) cue — and refuses everything else
with the closed CMB reader taxonomy. It does NOT solve: a non-positive net rate or a non-integer
answer is the *solver's* boundary (CMB-b), reached only after this reader produces a setup.

The wrong=0 spine is the CMB-a **2×2 domain-entry grid** (rate-count × combination cue):

```text
            | combination cue        | no cue
 two rates  | parse (sum/difference) | combine_mode_ambiguous   (same unit only)
 one rate   | missing_second_rate    | not_combined_rate_shaped   <- step aside (R3 territory)
```

plus "combined-shaped but deferred / malformed" refusals that fire ONLY once a genuine two-rate
combination cue is present, so CMB never claims a substantive boundary on R1/R2/R3 text:
``three_or_more_rates``, ``rate_unit_mismatch`` (the two rates differ in unit),
``clock_interval_deferred``, ``reciprocal_work_rate_deferred``.

**Robustness (each guards a wrong=0 / hygiene failure mode an adversarial pass found):**
  - cues are **whole-word** regexes, never substrings (``exempt`` is not a drain; ``bothered`` is
    not ``both``);
  - ``difference`` requires an explicit **fill AND drain pair**, and assigns ``rate_a`` = fill
    (minuend) / ``rate_b`` = drain (subtrahend) **by role**, not by text order (a drain listed
    first must still subtract);
  - the duration and the time-query target are read from the **query clause** (after the last rate
    clause), so a preamble number ("50 liters already in the tank …") is never mistaken for them;
  - the rate regex rejects **decimals** (``3.5 pages per hour`` is not an integer rate -> step aside);
  - substantive refusals are **gated behind a combination cue** — foreign two-/three-rate prose with
    no cue steps aside as ``not_combined_rate_shaped`` (router-organ hygiene), never a substantive
    boundary; and **sequential segments** (each rate carrying its own adjacent duration) step aside.

Off-serving (imports no ``generate.derivation`` / ``core.reliability_gate``); deterministic.
"""

from __future__ import annotations

import re

from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.combined_rate_comprehension.units import RateUnit
from generate.meaning_graph.reader import Refusal

# An integer rate ``<N> <plural> per <singular>``; the lookbehind rejects a digit that is part of a
# decimal ("3.5 pages per hour" -> no match -> the reader steps aside rather than read "5").
_RATE_VALUE = re.compile(r"(?<![\d.])(\d+)\s+([a-z]+)\s+per\s+([a-z]+)\b")
_DURATION = re.compile(r"\b(?:for|in|after)\s+(\d+)\s+([a-z]+)\b")
_DIGIT_NOUN = re.compile(r"(?<![\d.])(\d+)\s+([a-z]+)\b")
_HOW_MANY = re.compile(r"\bhow many ([a-z]+)\b")
# An effective-rate question — constrained to a direct "what … net/combined … rate" so a mid-sentence
# "at their combined rate, how many …" does NOT steal the slot from a quantity question.
_EFF_RATE_QUERY = re.compile(r"\bwhat\b[^.?!]*\b(?:net|combined)\b[^.?!]*\brate\b")
_CLOCK = re.compile(r"\b\d+\s*(?:am|pm)\b|\bo'?clock\b")
# Two conjoined agents in the premise ("Anna and Ben …") — the strong signal for missing_second_rate.
_AGENT_CONJ = re.compile(r"\b[a-z]+\s+and\s+[a-z]+\b")
# A query that attributes the answer to a SINGLE agent ("how many words does Alice type") rather
# than the combination ("how many … do they …" / "… are produced"). "does it/this/that" is the
# combined process, not a single agent, so it is excluded.
_SINGLE_AGENT_QUERY = re.compile(r"\bdoes\s+(?!it\b|this\b|that\b|they\b)[a-z]")

#: Whole-word fill / drain verbs. Detected PER RATE CLAUSE (in the clause's own lead-in), never
#: globally — an incidental "the drain stays closed" or a "draining" that governs a different clause
#: must not flip the mode. ``difference`` is a *clean opposition*: one fill clause + one drain clause.
_FILL_RE = re.compile(r"\b(?:fills?|filling|filled|adds?|adding|added|pours?|pouring|injects?|pumps?\s+in)\b")
_DRAIN_RE = re.compile(r"\b(?:drains?|draining|drained|removes?|removing|removed|leaks?|leaking|leaked|empties|emptied|emptying|siphons?|siphoning)\b")
_COOP_RE = re.compile(r"\b(?:together|combined|both)\b")
_RECIPROCAL_RE = re.compile(r"\bcan\b")  # "X can do the job in N time" — the reciprocal work-rate form

#: How far before a rate's number to look for its governing fill/drain verb ("a pipe fills a tank at
#: 5", "while a drain removes 2"). Kept tight so a verb governing the OTHER clause is not captured.
_LEADIN = 25


def _singular(noun: str) -> str:
    if noun.endswith("es") and noun[:-2].endswith(("x", "s", "z", "ch", "sh")):
        return noun[:-2]
    if noun.endswith("s") and len(noun) > 1:
        return noun[:-1]
    return noun


def _clause_role(t: str, start: int) -> str:
    """``drain`` / ``fill`` / ``other`` for the rate clause at *start*, by the verb directly before
    its number (within ``_LEADIN`` chars). Drain wins ties — a drain verb is the load-bearing sign."""
    leadin = t[max(0, start - _LEADIN) : start]
    if _DRAIN_RE.search(leadin):
        return "drain"
    if _FILL_RE.search(leadin):
        return "fill"
    return "other"


def _is_sequential(t: str, rate_spans: list[tuple[int, int]]) -> bool:
    """True iff BOTH rate clauses carry their own following duration (sequential segments — "60 mph
    for 2 hours and then 40 mph for 3 hours" — which is R3.x, not a simultaneous combination). The
    window tolerates a short connector ("also for", "then for")."""
    return all(_DURATION.search(t[e : e + 28]) is not None for _s, e in rate_spans)


def _digit_noun_after(t: str, start: int, noun: str) -> int | None:
    """The first ``<N> <noun>`` value at/after *start* — anchored to AFTER the ``how many`` question,
    so neither a premise number nor a transitional distractor inside the query clause is mistaken for
    the queried quantity."""
    for m in _DIGIT_NOUN.finditer(t, start):
        if _singular(m.group(2)) == noun:
            return int(m.group(1))
    return None


def read_combined_rate_problem(text: str) -> CombinedRateProblem | Refusal:
    """Comprehend explicit combined-rate prose into a typed CombinedRateProblem, or refuse."""
    if not text or not text.strip():
        return Refusal("empty")
    t = text.lower()

    rate_clauses = _RATE_VALUE.findall(t)  # [(value, plural, denom_singular), ...]
    rate_spans = [m.span() for m in _RATE_VALUE.finditer(t)]
    n = len(rate_clauses)
    coop = _COOP_RE.search(t) is not None
    n_durations = len(_DURATION.findall(t))

    # --- the grid's rate-count axis ----------------------------------------------------------- #
    if n == 0:
        # No explicit "per" rate. A cooperative cue + ≥2 completion durations + a "can"-style
        # capability is the reciprocal work-rate form (1/(1/a+1/b)); else not CMB's domain.
        if coop and n_durations >= 2 and _RECIPROCAL_RE.search(t):
            return Refusal("reciprocal_work_rate_deferred", "durations-to-complete, not explicit rates")
        return Refusal("not_combined_rate_shaped", "no explicit rate clause")
    if n >= 3:
        # Substantive ONLY with a combination cue; otherwise foreign prose that merely has ≥3 rate
        # patterns -> step aside (hygiene).
        if coop or any(_clause_role(t, s) == "drain" for s, _e in rate_spans):
            return Refusal("three_or_more_rates", f"{n} explicit rates; CMB v1 combines exactly two")
        return Refusal("not_combined_rate_shaped", "three or more rates but no combination cue")
    if n == 1:
        # One rate is substantive (missing a second) ONLY with a cooperative cue AND two conjoined
        # agents in the premise; a lone rate (or an incidental "combined"/"both") is R3 territory.
        if coop and any(m.start() < rate_spans[0][0] for m in _AGENT_CONJ.finditer(t)):
            return Refusal("missing_second_rate", "a cooperation cue and two agents but only one explicit rate")
        return Refusal("not_combined_rate_shaped", "a single rate with no two-agent combination cue")

    # --- n == 2 -------------------------------------------------------------------------------- #
    u0 = (_singular(rate_clauses[0][1]), _singular(rate_clauses[0][2]))
    u1 = (_singular(rate_clauses[1][1]), _singular(rate_clauses[1][2]))
    if _is_sequential(t, rate_spans):
        return Refusal("not_combined_rate_shaped", "two rates with their own durations are sequential segments")

    # The combine mode comes from the two clauses' OWN roles: a clean fill/drain opposition is the
    # only difference; a cooperative cue is the only sum. Anything else has no usable cue.
    roles = [_clause_role(t, s) for s, _e in rate_spans]
    if sorted(roles) == ["drain", "fill"]:
        mode = "difference"
    elif coop:
        mode = "sum"
    else:
        mode = None
    if mode is None:
        # combine_mode_ambiguous is substantive (CMB's domain), so it fires ONLY when the question
        # actually asks to COMBINE the two same-unit rates — a total quantity/time, or the net/combined
        # rate. Two same-unit rates merely COMPARED ("which is faster?"), or with a different unit, or
        # with no combined query, are not a CMB problem -> step aside (router hygiene).
        if u0 == u1:
            hm = _HOW_MANY.search(t)
            asked0 = _singular(hm.group(1)) if hm else None
            combined_q = asked0 in u0 or _EFF_RATE_QUERY.search(t, rate_spans[-1][1]) is not None
            # A query attributing the answer to a SINGLE agent ("how many words does Alice type") is a
            # single-rate question with a distractor rate, NOT a combined query -> step aside, never
            # claim the substantive combine_mode_ambiguous on it (router hygiene).
            if combined_q and _SINGLE_AGENT_QUERY.search(t, rate_spans[-1][1]) is None:
                return Refusal("combine_mode_ambiguous", "two same-unit rates and a combined query but no mode cue")
        return Refusal("not_combined_rate_shaped", "two rates that are not a clean combined-rate problem")
    # A combination cue IS present — now substantive combined-rate refusals are legitimate.
    if u0 != u1:
        return Refusal("rate_unit_mismatch", f"two rates differ in unit: {u0} vs {u1}")
    if _CLOCK.search(t):
        return Refusal("clock_interval_deferred", "an elapsed clock interval is not an explicit duration")

    unit = RateUnit(*u0)
    if mode == "difference":
        # rate_a = fill (minuend), rate_b = drain (subtrahend), BY ROLE not by text order.
        drain_idx = roles.index("drain")
        rate_a, rate_b = (
            (int(rate_clauses[1][0]), int(rate_clauses[0][0]))
            if drain_idx == 0
            else (int(rate_clauses[0][0]), int(rate_clauses[1][0]))
        )
    else:
        rate_a, rate_b = int(rate_clauses[0][0]), int(rate_clauses[1][0])

    # --- query slot + assembly: read the queried slot from AFTER the "how many" question, so a
    # premise number or a transitional time marker is never mistaken for it. --------------------- #
    if _EFF_RATE_QUERY.search(t, rate_spans[-1][1]):
        return CombinedRateProblem(rate_a, rate_b, unit, mode, None, None, "effective_rate")

    how_many = _HOW_MANY.search(t)
    if how_many is None:
        return Refusal("not_combined_rate_shaped", "no recognizable query slot")  # defensive (no gold)
    asked = _singular(how_many.group(1))
    q_start = how_many.end()

    if asked == unit.numerator:  # quantity query — needs a duration in the rate's denominator unit
        dur = _DURATION.search(t, q_start)
        if dur is None:
            return Refusal("not_combined_rate_shaped", "quantity query without a duration")  # defensive
        time_value, time_unit = int(dur.group(1)), _singular(dur.group(2))
        if time_unit != unit.denominator:
            # CMB v1 crosses no units (R3.2 conversion is single-rate only) — refuse rather than
            # silently treat a non-denominator duration as the rate's unit.
            return Refusal("rate_unit_mismatch", f"duration {time_unit!r} != rate denominator {unit.denominator!r}")
        return CombinedRateProblem(rate_a, rate_b, unit, mode, time_value, None, "quantity", time_unit=time_unit)

    if asked == unit.denominator:  # time query — needs the target quantity (in the numerator unit)
        qty = _digit_noun_after(t, q_start, unit.numerator)
        if qty is None:
            return Refusal("not_combined_rate_shaped", "time query without a target quantity")  # defensive
        return CombinedRateProblem(rate_a, rate_b, unit, mode, None, qty, "time")

    return Refusal("not_combined_rate_shaped", f"unrecognized query target {asked!r}")  # defensive


__all__ = ["read_combined_rate_problem"]
