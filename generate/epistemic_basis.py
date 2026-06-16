"""Epistemic basis of a grounded conclusion — the shared standing rule.

Extracted BYTE-IDENTICALLY from ``generate/determine/determine.py::_basis`` (ADR-0222 §3
note / §8 A3). Lifting it here lets the open-world DETERMINE gear AND the closed-world
``generate/frame_verdict`` evaluator both compute a verdict's standing without either
package importing the other — so INV-31's *directional* import scan (spine ↛ frame_verdict;
frame_verdict → leaf helpers) does not have to special-case a ``frame_verdict → determine``
edge. A leaf module: at runtime it imports only ``teaching.epistemic``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from teaching.epistemic import ADMISSIBLE_AS_EVIDENCE, EpistemicStatus

if TYPE_CHECKING:
    from generate.realize import RealizedRecord


def epistemic_basis(grounds: tuple[RealizedRecord, ...]) -> str:
    """Carry the grounds' epistemic standing forward — never overclaim "verified".

    Returns ``"verified"`` iff ``grounds`` is non-empty AND every ground is
    admissible-as-evidence (COHERENT); otherwise ``"as_told"`` (the only case reachable
    today, since every realizable record is SPECULATIVE). An empty grounds set is
    ``"as_told"`` — a proofless conclusion can never claim verified.
    """
    statuses = {EpistemicStatus(g.epistemic_status) for g in grounds}
    return "verified" if statuses and statuses <= ADMISSIBLE_AS_EVIDENCE else "as_told"
