"""P0-2 — tests for the DisclosureClaim axis.

Each test guards a specific confusion: that ``verified`` is a reach level, that the
claim axis is entangled with the resolution-action axis, that a value with no
producer (``PROVEN``) crept in, or that the default is anything but ``NONE``. None
passes under the confusion it is written to catch.
"""

from __future__ import annotations

import ast
import pathlib
from enum import Enum
from typing import get_args

import core.epistemic_disclosure.disclosure_claim as claim_module
from core.epistemic_disclosure.disclosure_claim import (
    DEFAULT_DISCLOSURE_CLAIM,
    DisclosureClaim,
)
from core.epistemic_disclosure.limitation import ResolutionAction
from core.response_governance.policy import ReachLevel


def test_default_claim_is_none():
    assert DEFAULT_DISCLOSURE_CLAIM is DisclosureClaim.NONE


def test_verified_is_not_a_reach_level():
    """The locked Stage-2 decision: VERIFIED is an epistemic claim, never a reach."""
    assert not any(level.name == "VERIFIED" for level in ReachLevel)
    assert "verified" not in {level.value for level in ReachLevel}
    assert not isinstance(DisclosureClaim.VERIFIED, ReachLevel)
    assert DisclosureClaim is not ReachLevel


def test_disclosure_claim_independent_of_resolution_action():
    """Orthogonal axes: disjoint value spaces (knowing the action doesn't fix the claim)."""
    claim_values = {c.value for c in DisclosureClaim}
    action_values = set(get_args(ResolutionAction))
    assert claim_values.isdisjoint(action_values)


def test_no_proven_claim_without_a_producer():
    """Discipline: the spine enforces on itself what it enforces on answers."""
    assert not hasattr(DisclosureClaim, "PROVEN")


def test_members_are_exactly_the_approved_four():
    # Four claims, each with a real or imminent producer. ESTIMATED and PROVEN are
    # intentionally absent (no producer → no declared label).
    assert {c.name for c in DisclosureClaim} == {
        "NONE",
        "VERIFIED",
        "APPROXIMATE",
        "PROPOSAL_ONLY",
    }


def test_estimated_absent_no_claim_without_a_producer():
    # ESTIMATED is a future split of APPROXIMATE; not declared until a producer exists.
    assert not hasattr(DisclosureClaim, "ESTIMATED")


def test_values_serialize_stably_as_snake_case():
    for c in DisclosureClaim:
        assert c.value == c.value.lower()
        assert " " not in c.value
        assert "-" not in c.value


def test_is_str_enum_for_stable_serialization():
    assert issubclass(DisclosureClaim, str)
    assert issubclass(DisclosureClaim, Enum)
    # str-valued: a member compares/serializes as its value
    assert DisclosureClaim.VERIFIED == "verified"


def test_module_is_off_serving_and_dependency_free():
    """P0-2 is the bare axis: it imports nothing, so it trivially cannot touch serving."""
    module_path = claim_module.__file__
    assert module_path is not None
    src = pathlib.Path(module_path).read_text()
    tree = ast.parse(src)
    from_imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    plain_imports = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    all_modules = from_imports + plain_imports
    forbidden = [
        m for m in all_modules
        if "generate.derivation" in m or "reliability_gate" in m or m.endswith("verify")
    ]
    assert forbidden == []
    # the only import is the stdlib enum — no project coupling at all (P0-2 is the bare axis)
    assert all(m in {"", "__future__", "enum"} for m in all_modules), all_modules
