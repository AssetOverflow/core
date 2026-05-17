"""teaching — correction capture, review, and proposal-only pack mutation.

The teaching loop allows CORE to learn from corrections in a controlled,
auditable way. Corrections flow through three stages:

  1. Capture  — extract a CorrectionCandidate from a correction intent
  2. Review   — validate the candidate (identity-safe, bounded, deterministic)
  3. Store    — persist reviewed examples; propose pack mutations without applying

Identity overrides are rejected at the review stage. Pack mutations are
emitted as proposals (PackMutationProposal) that require explicit external
approval before they touch the vocabulary manifold.
"""

from teaching.correction import CorrectionCandidate, extract_correction
from teaching.epistemic import ADMISSIBLE_AS_EVIDENCE, EpistemicStatus, parse_status
from teaching.review import ReviewedTeachingExample, ReviewOutcome, review_correction
from teaching.store import TeachingStore, PackMutationProposal

__all__ = [
    "ADMISSIBLE_AS_EVIDENCE",
    "CorrectionCandidate",
    "EpistemicStatus",
    "PackMutationProposal",
    "ReviewedTeachingExample",
    "ReviewOutcome",
    "TeachingStore",
    "extract_correction",
    "parse_status",
    "review_correction",
]
