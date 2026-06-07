"""Parse a multiple-choice option map into normalized integer values (R2 C4).

Options arrive as ``{label: value}``. A value may be a bare integer (the R2 gold form) or a
string carrying exactly one integer (``"11"``, ``"11 chickens"``, ``"$11"``). A string with
zero or several integers denotes no single value and REFUSES — the verifier must never guess
which number an ambiguous option meant. Off-serving; deterministic.
"""

from __future__ import annotations

import re
from typing import Any

from generate.meaning_graph.reader import Refusal

_INT_RE = re.compile(r"-?\d+")


def parse_option_value(value: Any) -> int | None:
    """The integer an option denotes, or ``None`` if it denotes no single integer.

    An ``int`` is taken verbatim; a ``str`` is accepted iff it carries exactly one integer
    (so ``"between 5 and 10"`` -> ``None``). ``bool`` is rejected (``True`` is not a count).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        found = _INT_RE.findall(value)
        if len(found) == 1:
            return int(found[0])
    return None


def parse_options(raw: Any) -> dict[str, int] | Refusal:
    """Normalize ``{label: value}`` into ``{label: int}``; refuse an empty or unparseable map."""
    if not isinstance(raw, dict) or not raw:
        return Refusal("no_options")
    out: dict[str, int] = {}
    for label, value in raw.items():
        parsed = parse_option_value(value)
        if parsed is None:
            return Refusal("unparseable_option", f"{label}: {value!r}")
        out[str(label)] = parsed
    return out


__all__ = ["parse_option_value", "parse_options"]
