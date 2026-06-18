"""Review hardening for Sprint 11 A2q calendar-piecewise boundaries."""

from __future__ import annotations

from generate.derivation.piecewise_daily_hours_total import compose_piecewise_daily_hours_total


MISSING_DAILY_ANCHOR = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews "
    "to her channel. She uploaded videos halfway through June, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

UNRELATED_DOUBLED_REMAINING_DAYS = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June, at that pace. "
    "Her fundraiser doubled the number of raffle tickets on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

VALID_EACH_DAY_SIBLING = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

VALID_PER_DAY_SIBLING = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews per day "
    "to her channel. She uploaded videos halfway through June, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)


def test_missing_daily_anchor_refuses() -> None:
    assert compose_piecewise_daily_hours_total(MISSING_DAILY_ANCHOR) is None


def test_unrelated_doubled_remaining_days_refuses() -> None:
    assert compose_piecewise_daily_hours_total(UNRELATED_DOUBLED_REMAINING_DAYS) is None


def test_each_day_sibling_still_admits() -> None:
    resolution = compose_piecewise_daily_hours_total(VALID_EACH_DAY_SIBLING)
    assert resolution is not None
    assert resolution.answer == 450.0


def test_per_day_sibling_still_admits() -> None:
    resolution = compose_piecewise_daily_hours_total(VALID_PER_DAY_SIBLING)
    assert resolution is not None
    assert resolution.answer == 450.0
