"""Ratification threshold default — Finding 3 (audit 2026-05-20).

Pre-fix the default threshold was ``0.0`` and the field gate was
semantically transparent (any non-negative projection passed).  This
test pins the calibrated default so a future change cannot silently
revert to a transparent gate without updating the test and the
calibration evidence comment in
``generate/intent_ratifier.py:_DEFAULT_RATIFICATION_THRESHOLD``.

The calibration data the default rests on was measured by
``scripts/calibrate_ratification_threshold.py``:

  * 34 RATIFIED cases across public+dev+holdout splits
  * minimum ``cga_inner(prompt, anchor)`` observed: ~1.10
  * 0.5 sits well below the floor (no regression on any passing case)
    and clearly non-trivially positive (random Cl(4,1) inner products
    fluctuate around zero).
"""

from __future__ import annotations

import inspect

from generate.intent_ratifier import _DEFAULT_RATIFICATION_THRESHOLD, ratify_intent


def test_default_threshold_is_calibrated() -> None:
    assert _DEFAULT_RATIFICATION_THRESHOLD == 0.5


def test_ratify_intent_signature_uses_calibrated_default() -> None:
    sig = inspect.signature(ratify_intent)
    threshold_param = sig.parameters["threshold"]
    assert threshold_param.default == _DEFAULT_RATIFICATION_THRESHOLD
    assert threshold_param.default != 0.0  # pre-fix value must not resurface
