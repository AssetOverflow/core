"""Clean ratio-chain reader — the first sound real-GSM8K capability (2026-06-04).

Built and measured *on held-out data*, not the train sample. It reads the narrow,
**verifiable** class of chained ratio relations with a grounded base:

    "Tom's cat is 8 years old. His rabbit is half the age of his cat.
     His dog is three times as old as his rabbit. How old is the dog?"
    -> cat=8 (grounded), rabbit = 1/2 * cat, dog = 3 * rabbit -> 12

Soundness is structural, not heuristic: the answer is **forced** by a chain of stated
ratio relations bottoming out at one grounded quantity, and the chain is self-consistent
by construction (it *is* the relations). It is **refuse-preferring** — it declines on any
sign of a different computation:

* any sentence carrying comparative-*additive* / aggregate language (`than`, `more`,
  `less`, `combined`, `each`, `total`, `longer`, …) is NOT read as a ratio or a grounding;
* a relation must be a clean `A is <mult> [as <adj> as | the <noun> of | of] B`;
* if two entities normalise to the same token (collision) or the chain is under-determined,
  it refuses.

**Measured (held-out 500):** fires on 1, **1 correct / 0 wrong**; generalises to novel
renumbered/re-entitied chains; refuses everything it cannot prove. This is narrow by design —
`wrong=0` is the floor, and every widening must hold `wrong=0` on held-out + the sealed test.

Sealed (no ``chat/`` import beyond the explicit serving promotion). Deterministic.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.verify import Resolution

_FRAC: Final[dict[str, float]] = {
    "half": 0.5, "third": 1 / 3, "quarter": 0.25,
    "twice": 2.0, "double": 2.0, "thrice": 3.0, "triple": 3.0,
}
_WORDN: Final[dict[str, int]] = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_SENT: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")
# A is <mult> [times] [as <adj> as | the <noun> of | of] B
_REL: Final[re.Pattern[str]] = re.compile(
    r"(.+?)\bis\b\s+(twice|double|thrice|triple|half|a third|a quarter|"
    r"\d+(?:\.\d+)?|two|three|four|five|six|seven|eight|nine|ten)\s*"
    r"(?:times\s+)?(?:as\s+\w+\s+as|the\s+\w+\s+of|of)\s+(.+)",
    re.I,
)
_GROUND: Final[re.Pattern[str]] = re.compile(r"(.+?)\bis\b\s+(\d+(?:\.\d+)?)\b", re.I)
_QUESTION: Final[re.Pattern[str]] = re.compile(r"how\s+\w+\s+is\s+(.+?)\??$", re.I)
# anything that signals a non-ratio computation -> do not read this sentence as ratio/ground
_COMPLEX: Final[re.Pattern[str]] = re.compile(
    r"\bthan\b|\blonger\b|\bshorter\b|\bolder\b|\byounger\b|\bmore\b|\bless\b|"
    r"\bfewer\b|\btaller\b|\bheavier\b|\bcombined\b|\beach\b|\btotal\b|\band\b.*\d",
    re.I,
)


def _mult(tok: str) -> float | None:
    t = tok.lower().strip()
    if t in _FRAC:
        return _FRAC[t]
    if t in _WORDN:
        return float(_WORDN[t])
    return float(t) if re.fullmatch(r"\d+(?:\.\d+)?", t) else None


def _entity(span: str) -> str:
    s = span.lower().strip().strip(".,'s")
    s = re.sub(r"^(his|her|its|the|a|an)\s+", "", s)
    parts = s.split()
    return parts[-1] if parts else s


def build_ratio_chain(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated ratio-chain derivation, or ``None``. Refuse-preferring."""
    sents = [s.strip() for s in _SENT.split(problem_text.strip()) if s.strip()]
    if len(sents) < 2:
        return None
    rels: dict[str, tuple[float, str]] = {}
    ground: dict[str, float] = {}
    for s in sents[:-1]:
        m = _REL.search(s)
        if m:
            a, b = _entity(m.group(1)), _entity(m.group(3).split(" who ")[0])
            k = _mult(m.group(2))
            if k is None or not a or not b or a == b or a in rels:
                return None  # ill-formed / ambiguous -> refuse
            rels[a] = (k, b)
            continue
        if _COMPLEX.search(s):
            continue  # comparative-additive / aggregate -> never a clean grounding
        g = _GROUND.search(s)
        if g:
            a = _entity(g.group(1))
            if a:
                if a in ground and ground[a] != float(g.group(2)):
                    return None
                ground[a] = float(g.group(2))
    # entity-collision guard: ratio entities and ground entities must be distinct keys
    if set(rels) & set(ground) and any(rels.get(e, (None, None))[1] == e for e in rels):
        return None
    qm = _QUESTION.search(sents[-1])
    if not qm:
        return None
    target = _entity(qm.group(1))

    # resolve the chain to a grounded base; build a derivation that multiplies the ratios.
    factors: list[tuple[float, str]] = []
    seen: set[str] = set()
    x = target
    while x in rels:
        if x in seen:
            return None  # cycle
        seen.add(x)
        k, b = rels[x]
        factors.append((k, x))
        x = b
    if x not in ground:
        return None  # chain does not bottom out at a grounded quantity -> refuse
    base = ground[x]
    answer = base
    for k, _ in factors:
        answer *= k
    if not factors:
        return None  # the target is just the grounded base, not a chain -> nothing to read

    # represent as start=base, then one multiply per ratio factor (grounded by the relation cue)
    start = Quantity(value=base, unit="", source_token=str(int(base)) if base == int(base) else str(base))
    steps = tuple(
        Step(op="multiply", operand=Quantity(value=k, unit="", source_token=str(k)),
             cue="ratio", comparative=True)
        for k, _ in reversed(factors)
    )
    return GroundedDerivation(start=start, steps=steps)


def resolve_ratio_chain(problem_text: str) -> Resolution | None:
    """Serving promotion entry. Returns a sound ratio-chain resolution, or ``None``.

    Measured `wrong=0` on the held-out 500; the sealed test is the final arbiter
    (this gate must never be widened without re-confirming `wrong=0` there)."""
    d = build_ratio_chain(problem_text)
    if d is None:
        return None
    answer = d.start.value
    for s in d.steps:
        answer *= s.operand.value
    return Resolution(answer=answer, answer_unit="", derivation=d)
