"""Phase 1.2 — gap auto-promotion tests.

The contract these tests pin:

  - ``promote_gaps`` is a pure derivation from :class:`Gap` records.
  - Default mode filters by ``boundary_clean_count``; tainted-only
    cells never auto-promote unless ``include_tainted=True``.
  - Threshold ``< 1`` raises — a zero threshold defeats the queue.
  - Ordering: highest effective count first, ties broken by
    (subject, intent) — matches :func:`aggregate_gaps`.
  - ``queue_id`` is stable + deterministic.
"""

from __future__ import annotations

import pytest

from teaching.gaps import Gap
from teaching.promotion import GapPromotion, promote_gaps


def _gap(
    subject: str,
    intent: str = "cause",
    count: int = 3,
    clean: int | None = None,
    months: tuple[str, ...] = ("2026-05",),
) -> Gap:
    return Gap(
        subject=subject,
        intent=intent,
        count=count,
        boundary_clean_count=count if clean is None else clean,
        sample_candidate_ids=("a", "b"),
        months_seen=months,
    )


# ---------------------------------------------------------------------------
# Default mode — boundary_clean_count gates the promotion
# ---------------------------------------------------------------------------


def test_clean_count_meets_threshold_promotes() -> None:
    gaps = (_gap("parent", count=5, clean=5),)
    promoted = promote_gaps(gaps, threshold=3)
    assert len(promoted) == 1
    assert promoted[0].subject == "parent"
    assert promoted[0].count == 5
    assert promoted[0].boundary_clean_count == 5
    assert promoted[0].threshold == 3


def test_clean_count_below_threshold_does_not_promote() -> None:
    gaps = (_gap("parent", count=5, clean=2),)
    promoted = promote_gaps(gaps, threshold=3)
    assert promoted == ()


def test_tainted_only_cell_does_not_promote_by_default() -> None:
    """A cell with count=5 but boundary_clean_count=0 means every
    emission was refusal/hedge-tainted.  Default mode must NOT
    promote — those signals may indicate the *prompt* hit a safety
    axis, not a curriculum gap."""
    gaps = (_gap("forbidden_thing", count=5, clean=0),)
    promoted = promote_gaps(gaps, threshold=3)
    assert promoted == ()


def test_include_tainted_counts_every_emission() -> None:
    gaps = (_gap("forbidden_thing", count=5, clean=0),)
    promoted = promote_gaps(gaps, threshold=3, include_tainted=True)
    assert len(promoted) == 1
    assert promoted[0].count == 5
    assert promoted[0].boundary_clean_count == 0


# ---------------------------------------------------------------------------
# Threshold validation
# ---------------------------------------------------------------------------


def test_threshold_must_be_positive() -> None:
    with pytest.raises(ValueError):
        promote_gaps((_gap("parent"),), threshold=0)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_order_is_count_desc_then_subject() -> None:
    gaps = (
        _gap("child", count=3, clean=3),
        _gap("parent", count=5, clean=5),
        _gap("ancestor", count=3, clean=3),
    )
    promoted = promote_gaps(gaps, threshold=3)
    assert [p.subject for p in promoted] == ["parent", "ancestor", "child"]


def test_order_is_stable_for_identical_counts() -> None:
    gaps = (
        _gap("child", count=3),
        _gap("ancestor", count=3),
        _gap("parent", count=3),
    )
    a = promote_gaps(gaps, threshold=3)
    b = promote_gaps(gaps, threshold=3)
    assert a == b
    assert [p.subject for p in a] == ["ancestor", "child", "parent"]


# ---------------------------------------------------------------------------
# queue_id stability
# ---------------------------------------------------------------------------


def test_queue_id_format_and_stability() -> None:
    gaps = (_gap("parent", intent="cause", count=3, clean=3),)
    promoted = promote_gaps(gaps, threshold=3)
    assert promoted[0].queue_id == "gap:cause:parent@3"

    # Same cell at a different threshold → different queue_id.
    promoted2 = promote_gaps(
        (_gap("parent", intent="cause", count=10, clean=10),), threshold=5
    )
    assert promoted2[0].queue_id == "gap:cause:parent@5"


def test_queue_id_distinguishes_intent() -> None:
    promoted = promote_gaps(
        (
            _gap("parent", intent="cause", count=3, clean=3),
            _gap("parent", intent="verification", count=3, clean=3),
        ),
        threshold=3,
    )
    queue_ids = {p.queue_id for p in promoted}
    assert queue_ids == {"gap:cause:parent@3", "gap:verification:parent@3"}


# ---------------------------------------------------------------------------
# Promotion is a pure derivation — no side effects
# ---------------------------------------------------------------------------


def test_promotion_does_not_mutate_input() -> None:
    gaps = (_gap("parent", count=3, clean=3),)
    snapshot = gaps[0]
    promote_gaps(gaps, threshold=3)
    promote_gaps(gaps, threshold=2, include_tainted=True)
    assert gaps[0] == snapshot


def test_promotion_is_frozen() -> None:
    promo = GapPromotion(
        subject="parent", intent="cause", count=3, boundary_clean_count=3,
        sample_candidate_ids=("a",), months_seen=("2026-05",), threshold=3,
    )
    with pytest.raises((AttributeError, TypeError)):
        promo.count = 99  # type: ignore[misc]
