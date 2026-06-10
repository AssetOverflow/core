"""ADR-0184 §7 S4 — the semantic candidate-source boundary tests.

The boundary (:mod:`generate.derivation.state.source`) is the single surface through
which semantic-ledger worlds become derivation candidates, and ``pool.py`` now sources
the accumulation readings through it.  These tests pin the boundary laws
(CLAUDE.md "Schema-Defined Proof Obligations" — each must fail loudly if exactly its
guard is removed):

* **byte-equivalence** — the boundary enumeration is identical to the legacy
  ``accumulation_candidates`` enumeration (order, duplicates, refusals included);
* **authority unchanged** — a boundary candidate commits only through verify/pool:
  acceptance requires classification, rejection fails closed (no world -> no
  candidate -> refusal or fall-through, never a synthesized answer);
* **no direct commit path** — nothing under ``generate/derivation/state/`` imports
  the verifier or the pool (structural scan, with a predicate self-test so the scan
  cannot be vacuous);
* **legacy surfaces preserved** — ``compose_accumulation`` / ``accumulation_candidates``
  behave exactly as before the swap.
"""

from __future__ import annotations

import ast
from pathlib import Path

from generate.derivation import pool
from generate.derivation.accumulate import accumulation_candidates, compose_accumulation
from generate.derivation.model import GroundedDerivation
from generate.derivation.pool import resolve_pooled
from generate.derivation.state.source import (
    accumulation_ledger_worlds,
    semantic_state_candidates,
)
from generate.derivation.verify import Resolution, classify_derivation

_CLEAN_GAIN = "Sam has 14 apples. He buys 9 more apples. How many apples does Sam have?"
_CLEAN_LOSS = "Anna has 25 stickers. She gives 10 away. How many stickers does Anna have?"
_NEW_ACTOR = "Sam has 14 apples. Tom buys 9 more apples. How many apples does Sam have?"
_DISTRACTOR_0014 = (
    "Kate has 20 pencils. She studies for 3 hours and then buys 5 more pencils. "
    "How many pencils does Kate have?"
)
_ANCHOR_SKIP_0016 = (
    "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
    "he buys 4 more tickets. How many tickets does Tom have?"
)
_NO_QUANTITIES = "Sam walked to the library and read a book."

_BATTERY = (
    _CLEAN_GAIN,
    _CLEAN_LOSS,
    _NEW_ACTOR,
    _DISTRACTOR_0014,
    _ANCHOR_SKIP_0016,
    _NO_QUANTITIES,
)


class TestBoundaryEquivalence:
    """The boundary is a re-plumbing, not a new reading."""

    def test_legacy_wrapper_delegates_byte_identically(self) -> None:
        for text in _BATTERY:
            assert accumulation_candidates(text) == semantic_state_candidates(text)

    def test_enumeration_order_is_strict_then_skip_readings(self) -> None:
        # The distractor problem yields the strict refusal (absent) then the
        # distractor-skip reading; the anchor-skip problem yields the anchor-skip
        # reading. Order changes would change which derivation object a commit
        # reports — pinned here.
        skip = semantic_state_candidates(_DISTRACTOR_0014)
        assert [d.answer for d in skip] == [25.0]
        anchor = semantic_state_candidates(_ANCHOR_SKIP_0016)
        assert anchor and anchor[-1].answer == 12.0

    def test_clean_problem_emits_duplicate_readings(self) -> None:
        # On a clean problem the strict, distractor-skip, AND anchor-skip worlds all
        # coincide; the legacy enumeration emitted all three (pool dedups).
        # Collapsing them here would silently change pool input multiplicity.
        candidates = semantic_state_candidates(_CLEAN_GAIN)
        assert len(candidates) == 3
        assert len(set(candidates)) == 1

    def test_every_world_starts_with_set(self) -> None:
        # The builder can only emit replayable accumulation shapes — a non-SET-start
        # world would be silently dropped by replay; prove the enumeration never
        # produces one (fail-closed is for hand-built ledgers, not a leak here).
        for text in _BATTERY:
            for world in accumulation_ledger_worlds(text):
                assert world.transitions[0].op == "set"

    def test_compose_accumulation_unchanged(self) -> None:
        result = compose_accumulation(_CLEAN_GAIN)
        assert result is not None and result.answer == 23.0
        assert compose_accumulation(_NEW_ACTOR) is None


class TestAuthorityUnchanged:
    """Semantic candidates pass through verify/pool or do not pass at all."""

    def test_boundary_emits_only_inert_value_objects(self) -> None:
        for text in _BATTERY:
            for candidate in semantic_state_candidates(text):
                assert isinstance(candidate, GroundedDerivation)
                assert not isinstance(candidate, Resolution)

    def test_pool_sources_the_boundary_function(self) -> None:
        assert pool.semantic_state_candidates is semantic_state_candidates

    def test_acceptance_still_requires_pool_commit_rules(self) -> None:
        resolution = resolve_pooled(_CLEAN_GAIN)
        assert resolution is not None and resolution.answer == 23.0
        # the committed derivation is one the boundary emitted and verify classified
        assert classify_derivation(resolution.derivation, _CLEAN_GAIN) == "complete"

    def test_unverifiable_semantic_candidate_never_commits(self) -> None:
        # A boundary candidate evaluated against text it is not grounded in fails
        # the verifier — the boundary cannot vouch for its own output.
        candidate = semantic_state_candidates(_CLEAN_GAIN)[0]
        foreign_text = "Lily has 3 books. She buys 2 more books."
        assert classify_derivation(candidate, foreign_text) is None

    def test_rejection_fails_closed(self) -> None:
        # No expressible world -> empty tuple -> downstream refusal/fall-through;
        # never a placeholder candidate.
        assert semantic_state_candidates(_NEW_ACTOR) == ()
        assert semantic_state_candidates(_NO_QUANTITIES) == ()

    def test_distractor_disagreement_still_refuses(self) -> None:
        assert resolve_pooled(_DISTRACTOR_0014) is None

    def test_anchor_skip_reading_is_still_exempt_only(self) -> None:
        # ADR-0182's refusals depend on the exempt rival reading surviving the swap.
        anchor = semantic_state_candidates(_ANCHOR_SKIP_0016)[-1]
        assert classify_derivation(anchor, _ANCHOR_SKIP_0016) == "exempt"


_STATE_DIR = Path(__file__).resolve().parent.parent / "generate" / "derivation" / "state"
_FORBIDDEN_MODULES = ("generate.derivation.verify", "generate.derivation.pool")
_FORBIDDEN_NAMES = frozenset(
    {
        "Resolution",
        "classify_derivation",
        "resolve_pooled",
        "select_self_verified",
        "self_verifies",
    }
)


def _authority_imports(source: str) -> list[str]:
    """Names a module imports from the verifier/pool authority surfaces."""
    violations: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                alias.name for alias in node.names if alias.name in _FORBIDDEN_MODULES
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in _FORBIDDEN_MODULES:
                violations.append(module)
            else:
                violations.extend(
                    alias.name for alias in node.names if alias.name in _FORBIDDEN_NAMES
                )
    return violations


class TestNoDirectCommitPath:
    """Structural: the semantic-state package cannot reach commit authority."""

    def test_state_package_never_imports_verifier_or_pool(self) -> None:
        scanned = 0
        for path in sorted(_STATE_DIR.glob("*.py")):
            violations = _authority_imports(path.read_text())
            assert not violations, f"{path.name} imports commit authority: {violations}"
            scanned += 1
        assert scanned >= 6, "state/ package moved? scan would be vacuous"

    def test_scan_predicate_flags_module_import(self) -> None:
        # Predicate self-test (non-vacuity): both import forms must be caught.
        assert _authority_imports("from generate.derivation.verify import Resolution")
        assert _authority_imports("import generate.derivation.pool")

    def test_scan_predicate_flags_indirect_name_import(self) -> None:
        # Re-exported authority names are caught even via a laundering module.
        assert _authority_imports("from generate.derivation import resolve_pooled")
        assert _authority_imports("from generate.derivation import Resolution")
