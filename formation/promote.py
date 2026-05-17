"""Stage 8 — Promote.  The only SPECULATIVE → COHERENT bridge.

Promotion is the **single** authorized mutation path from a Mastered course
into the language pack / teaching store.  Every other artifact in the
pipeline is proposal-only.  Per ADR-0021 §Schema impact, the bridge here
routes through ``teaching/review.py`` so the existing review gate is the
sole pack-mutation entry point in the entire system.

Promotion requirements (all must hold):

    P1. The ``MasteryReport`` must be ``ratified == True``.
    P2. Its ``report_sha256`` must verify (self-seal intact).
    P3. Every ``requires_courses`` entry in the ``SubjectSpec`` must be
        present in the ``MasteredCoursesIndex``.
    P4. Promotion is idempotent — calling ``promote`` twice with the same
        ``report_sha256`` is a no-op.

Promotion stamps every triple with ``report_sha256`` so the teaching store
carries the chain-of-custody back to the receipt that authorized the
mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.course import (
    MasteryReport,
    SubjectSpec,
    ValidatedTripleSet,
)
from formation.index import MasteredCourseEntry, MasteredCoursesIndex
from formation.mastery import verify_report
from generate.intent import DialogueIntent, IntentTag
from teaching.correction import CorrectionCandidate
from teaching.epistemic import EpistemicStatus
from teaching.review import (
    ReviewOutcome,
    ReviewedTeachingExample,
    review_correction,
)
from formation.hashing import sha256_of


class PromoteRefused(Exception):
    """Raised when a promotion is refused.  Carries the failure reason."""


@dataclass(frozen=True, slots=True)
class PromotedTriple:
    """A reviewed teaching example carrying the authorizing Mastery Report SHA."""

    report_sha256: str
    example: ReviewedTeachingExample
    triple: tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class PromotionResult:
    report_sha256: str
    course_id: str
    promoted: tuple[PromotedTriple, ...]
    rejected: tuple[PromotedTriple, ...]
    idempotent_skipped: bool = False


def _candidate_for(
    triple: tuple[str, str, str], report_sha: str
) -> CorrectionCandidate:
    head, relation, tail = triple
    correction_text = f"{head} {relation.replace('_', ' ')} {tail}."
    intent = DialogueIntent(tag=IntentTag.CORRECTION, subject=head)
    candidate_id = sha256_of(
        {"head": head, "relation": relation, "tail": tail, "report": report_sha}
    )[:16]
    return CorrectionCandidate(
        correction_text=correction_text,
        intent=intent,
        prior_surface="",
        prior_turn=-1,
        candidate_id=candidate_id,
    )


def promote(
    *,
    report: MasteryReport,
    spec: SubjectSpec,
    validated_set: ValidatedTripleSet,
    index: MasteredCoursesIndex,
) -> PromotionResult:
    """Run the Promote gate and route validated triples through the review path."""
    # P1: ratified.
    if not report.ratified:
        raise PromoteRefused(
            f"report not ratified: failure_reasons={list(report.failure_reasons)}"
        )

    # P2: seal intact.
    if not verify_report(report):
        raise PromoteRefused("report self-seal does not verify")

    # P3: prerequisites.
    missing = [
        c for c in spec.requires_courses if not index.contains_course(c)
    ]
    if missing:
        raise PromoteRefused(f"missing prerequisites: {missing}")

    # P4: idempotency — already promoted under this exact report SHA?
    if index.contains_report(report.report_sha256):
        return PromotionResult(
            report_sha256=report.report_sha256,
            course_id=report.course_id,
            promoted=(),
            rejected=(),
            idempotent_skipped=True,
        )

    promoted: list[PromotedTriple] = []
    rejected: list[PromotedTriple] = []

    for rel in validated_set.relations:
        triple = (rel.head, rel.relation, rel.tail)
        candidate = _candidate_for(triple, report.report_sha256)
        example = review_correction(
            candidate, epistemic_status=EpistemicStatus.SPECULATIVE
        )
        record = PromotedTriple(
            report_sha256=report.report_sha256, example=example, triple=triple
        )
        if example.outcome is ReviewOutcome.ACCEPTED:
            promoted.append(record)
        else:
            rejected.append(record)

    # Register in the index even if some triples were rejected by the review
    # path — the report itself is ratified, and individual triple rejections
    # are audit data, not a failure of the course.
    index.add(MasteredCourseEntry(
        course_id=report.course_id,
        report_sha256=report.report_sha256,
        issued_at=report.issued_at,
        course_sha256=report.course_sha256,
        validated_set_sha=report.validated_set_sha,
    ))

    return PromotionResult(
        report_sha256=report.report_sha256,
        course_id=report.course_id,
        promoted=tuple(promoted),
        rejected=tuple(rejected),
        idempotent_skipped=False,
    )
