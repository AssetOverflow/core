"""
Deterministic trace hashing for cognitive turns.

The hash captures every meaningful output of a pipeline run so that:
  - identical inputs on identical field state → identical hash
  - any output change → different hash

Only stable, semantically meaningful fields are included.  Floating-point
values are rounded to 9 decimal places before hashing so that numeric
noise from different hardware does not break determinism within a run.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.cognition.result import CognitiveTurnResult


def _round_float(v: float, ndigits: int = 9) -> float:
    return round(float(v), ndigits)


def compute_trace_hash(
    input_text: str,
    filtered_tokens: tuple[str, ...],
    surface: str,
    walk_surface: str,
    articulation_surface: str,
    dialogue_role: str,
    versor_condition: float,
    vault_hits: int,
    intent_tag: str = "unknown",
) -> str:
    """Return a deterministic SHA-256 hex digest over the turn's key outputs.

    Parameters match the subset of CognitiveTurnResult that is both
    semantically meaningful and stable across hardware.
    """
    payload = {
        "input_text": input_text,
        "filtered_tokens": list(filtered_tokens),
        "surface": surface,
        "walk_surface": walk_surface,
        "articulation_surface": articulation_surface,
        "dialogue_role": str(dialogue_role),
        "versor_condition": _round_float(versor_condition),
        "vault_hits": int(vault_hits),
        "intent_tag": intent_tag,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def trace_hash_from_result(result: "CognitiveTurnResult") -> str:
    """Convenience wrapper — compute the hash directly from a result object."""
    intent_tag = result.intent.tag.value if result.intent is not None else "unknown"
    return compute_trace_hash(
        input_text=result.input_text,
        filtered_tokens=result.filtered_tokens,
        surface=result.surface,
        walk_surface=result.walk_surface,
        articulation_surface=result.articulation_surface,
        dialogue_role=str(result.dialogue_role),
        versor_condition=result.versor_condition,
        vault_hits=result.vault_hits,
        intent_tag=intent_tag,
    )
