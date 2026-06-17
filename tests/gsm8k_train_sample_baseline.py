"""Train-sample serving capability baseline (Inc1 rebaseline snapshot).

The 6/44/0 counts are a historical measurement receipt — not a design target
or ceiling on capability lift. Live serving tests use the monotonic contract:

    wrong == 0  (hard safety invariant)
    correct >= BASELINE_CORRECT
    refused <= BASELINE_REFUSED

Exact-count equality is reserved for explicitly named historical fixture tests
over the committed ``report.json`` artifact until a separate rebaseline ratifies
a new pin.
"""

from __future__ import annotations

BASELINE_CORRECT = 6
BASELINE_WRONG = 0
BASELINE_REFUSED = 44
TRAIN_SAMPLE_COUNT = 50


def assert_monotonic_serving_counts(counts: dict[str, int]) -> None:
    """Serving lane live contract: wrong=0 hard; counts monotonic vs floor."""
    assert counts["wrong"] == BASELINE_WRONG
    assert counts["correct"] >= BASELINE_CORRECT
    assert counts["refused"] <= BASELINE_REFUSED
    total = counts["correct"] + counts["wrong"] + counts["refused"]
    assert total == TRAIN_SAMPLE_COUNT, (
        f"expected {TRAIN_SAMPLE_COUNT} scored cases, got {total}"
    )
