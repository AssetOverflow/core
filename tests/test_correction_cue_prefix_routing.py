"""Regression test for "Actually X R Y" → CORRECTION routing.

The declarative-relation match (``_DECLARATIVE_RELATION_RE``) runs ahead
of the ``_RULES`` loop and previously swallowed sentences beginning with
"Actually" into the subject phrase, routing them to VERIFICATION. That
prevented the inference-closure lane from emitting
``PackMutationProposal`` records for any non-`is` premise (the lane
documented this regression on 2026-05-22 in ``gaps.md``).

The fix is the ``_CORRECTION_CUE_PREFIX_RE`` guard in
``generate/intent.py``: if the text starts with a correction cue token,
the declarative-match branch is skipped and the sentence falls through
to the ``_RULES`` loop where the CORRECTION rule fires.
"""

from __future__ import annotations

import pytest

from generate.intent import IntentTag, classify_intent


@pytest.mark.parametrize(
    "text,expected_subject",
    [
        ("Actually wisdom is light.", "wisdom is light"),
        ("Actually wisdom precedes recall.", "wisdom precedes recall"),
        ("Actually truth grounds knowledge.", "truth grounds knowledge"),
        ("Actually fire causes smoke.", "fire causes smoke"),
        ("Actually X reveals Y.", "X reveals Y"),
        ("Incorrect, wisdom precedes recall.", ", wisdom precedes recall"),
        ("Correction: wisdom precedes recall.", ": wisdom precedes recall"),
    ],
)
def test_correction_cue_prefix_routes_to_correction(
    text: str, expected_subject: str
) -> None:
    intent = classify_intent(text)
    assert intent.tag is IntentTag.CORRECTION, (
        f"expected CORRECTION for {text!r}, got {intent.tag.value}"
    )
    assert intent.relation is None
    assert intent.subject == expected_subject


@pytest.mark.parametrize(
    "text",
    [
        "Wisdom precedes recall.",
        "Truth grounds knowledge.",
        "Fire causes smoke.",
    ],
)
def test_bare_declarative_still_verification(text: str) -> None:
    """The guard must only fire on a correction-cue prefix.

    Plain declarative-relation assertions must continue to route to
    VERIFICATION so the relation/object slots are populated.
    """
    intent = classify_intent(text)
    assert intent.tag is IntentTag.VERIFICATION
    assert intent.relation is not None
