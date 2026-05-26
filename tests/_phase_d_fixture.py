"""Phase D test fixture — synthetic ratified registry from live log.

Per ADR-0161 §5, the agent does NOT ratify the live proposal log.  The
agent's tests build a SYNTHETIC RATIFIED REGISTRY in memory from the
three live PENDING Phase C proposals, populating ``review_date`` with
a fixed synthetic date.  This exercises the per-category match
functions + the candidate-graph wiring against the EXACT
RecognizerSpec content the operator will later ratify, with zero
modification of the live proposal log.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.recognizer_registry import RatifiedRecognizer
from teaching.proposals import ProposalLog


PHASE_C_PROPOSAL_IDS: tuple[str, ...] = (
    "59223f13722f906a1cf9b65d9b01c990",  # descriptive_setup_no_quantity
    "46ce297f797ff16da12db5de422ca3c9",  # rate_with_currency
    "a3b892546977c5f0f64c578d6052adbd",  # temporal_aggregation
)

SYNTHETIC_REVIEW_DATE: str = "2026-05-27"


def build_synthetic_registry(
    log_path: Path | None = None,
) -> tuple[RatifiedRecognizer, ...]:
    """Build the in-memory ratified registry from live pending Phase C proposals.

    Reads ``teaching/proposals/proposals.jsonl`` (or *log_path*), pulls
    the three Phase C proposals by id, and converts their pending
    ``proposed_chain.recognizer_spec`` payloads into
    :class:`RatifiedRecognizer` records.

    Raises :class:`AssertionError` if any of the three Phase C
    proposal_ids cannot be located in the log.  This is intentional —
    Phase D's tests assume Phase C's exemplar-corpus proposals exist;
    if they don't, the operator should re-run
    ``core teaching propose-from-exemplars --all`` first.
    """
    log = ProposalLog(log_path)
    state = log.current_state()
    recognizers: list[RatifiedRecognizer] = []
    for pid in PHASE_C_PROPOSAL_IDS:
        record = state.get(pid)
        assert record is not None, (
            f"Phase D fixture: proposal {pid!r} not in {log.path}; "
            "run `core teaching propose-from-exemplars --all` first"
        )
        chain = record["proposal"]["proposed_chain"]
        spec: Mapping[str, object] = chain["recognizer_spec"]  # type: ignore[assignment]
        shape_category = ShapeCategory(spec["shape_category"])  # type: ignore[arg-type]
        recognizers.append(
            RatifiedRecognizer(
                proposal_id=pid,
                shape_category=shape_category,
                canonical_pattern=spec["canonical_pattern"],  # type: ignore[arg-type]
                spec_digest=str(chain["object"]),
                review_date=SYNTHETIC_REVIEW_DATE,
                ratified_at_revision=str(
                    record["proposal"]["source"]["emitted_at_revision"]
                ),
            )
        )
    recognizers.sort(key=lambda r: (r.review_date, r.proposal_id))
    return tuple(recognizers)


__all__ = [
    "PHASE_C_PROPOSAL_IDS",
    "SYNTHETIC_REVIEW_DATE",
    "build_synthetic_registry",
]
