"""E — the serving-side SERVE license for the converse-guess.

Reads the **ratified, committed** estimation ledger (``data/estimation_ledger.json``)
and exposes, per predicate, whether the converse-guess has earned ``Action.SERVE``
under the safe default ceilings (θ_SERVE=0.99). The engine READS this artifact; it
never writes it. The artifact is the sealed-practice output of
``evals.determination_estimation.build_ledger`` — its ``content_sha256`` is verified on
load, so a hand-edited (un-ratified) ledger is rejected rather than silently trusted.

Determinism: the ledger is immutable ratified data, parsed once and cached; the gate
(``license_for``) is pure. No engine self-authorization — ceilings stay at the safe
defaults (raising one's own bar is structurally impossible, ADR-0175 invariant #4).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.reliability_gate import Action, Ceilings, ClassTally, LicenseDecision, license_for
from formation.hashing import sha256_of
from generate.determine.estimate import converse_class_name

_LEDGER_PATH = Path(__file__).resolve().parent / "data" / "estimation_ledger.json"


class RatifiedLedgerError(ValueError):
    """The committed estimation ledger is missing, malformed, or tampered with."""


@lru_cache(maxsize=1)
def load_ratified_ledger() -> dict[str, ClassTally]:
    """Load + verify the ratified estimation ledger → per-class ``ClassTally``.

    Raises :class:`RatifiedLedgerError` if the file is absent/malformed or its
    recomputed ``content_sha256`` does not match the committed one (tamper-evidence:
    only the sealed-practice output is trusted, never a hand-edited ledger).
    """
    try:
        artifact = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise RatifiedLedgerError(f"cannot read ratified ledger: {exc}") from exc

    classes = artifact.get("classes")
    if not isinstance(classes, dict):
        raise RatifiedLedgerError("ratified ledger has no 'classes' table")
    if sha256_of(classes) != artifact.get("content_sha256"):
        raise RatifiedLedgerError(
            "ratified ledger content_sha256 mismatch — not the sealed-practice output"
        )

    ledger: dict[str, ClassTally] = {}
    for cls, counts in classes.items():
        ledger[cls] = ClassTally(
            class_name=cls,
            correct=int(counts.get("correct", 0)),
            wrong=int(counts.get("wrong", 0)),
            refused=int(counts.get("refused", 0)),
            t2_verified=int(counts.get("t2_verified", 0)),
            t2_agrees_gold=int(counts.get("t2_agrees_gold", 0)),
        )
    return ledger


def serve_license(
    predicate: str,
    *,
    ledger: dict[str, ClassTally] | None = None,
    ceilings: Ceilings | None = None,
) -> LicenseDecision | None:
    """The ``Action.SERVE`` license for ``predicate``'s converse-guess, or ``None``.

    ``None`` means the predicate-class is absent from the ratified ledger (no committed
    evidence → never licensed; the caller refuses, the safe default). Otherwise the
    deterministic ``license_for`` verdict under the safe default ceilings.
    """
    ledger = ledger if ledger is not None else load_ratified_ledger()
    tally = ledger.get(converse_class_name(predicate))
    if tally is None:
        return None
    ceilings = ceilings if ceilings is not None else Ceilings.default()
    return license_for(tally, Action.SERVE, ceilings)


__all__ = ["RatifiedLedgerError", "load_ratified_ledger", "serve_license"]
