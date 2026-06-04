"""Clean ratio-chain reader — the first sound real-GSM8K capability.

Built and measured on held-out data (`holdout_dev`), wired to serving. The obligations:
* **generalises** (not memorised to cv-0005): solves novel renumbered/re-entitied chains;
* **sound refusal**: declines comparative-additive ("12 inches longer than") and any
  under-determined / colliding chain — wrong=0 is the floor;
* **the lift**: cv-0005 now resolves on the serving path.
"""
from __future__ import annotations

from generate.derivation.ratio_chain import build_ratio_chain, resolve_ratio_chain
from generate.math_candidate_graph import parse_and_solve

CV0005 = (
    "Tom's cat is 8 years old. His rabbit is half the age of his cat. "
    "His dog is three times as old as his rabbit. How old is the dog?"
)


def _ans(text):
    r = resolve_ratio_chain(text)
    return None if r is None else r.answer


def test_cv0005_chain_solves() -> None:
    assert _ans(CV0005) == 12.0


def test_serving_lifts_cv0005() -> None:
    """The reader is wired to serving — the held-out lift is real end-to-end."""
    assert parse_and_solve(CV0005).answer == 12.0


def test_generalises_to_novel_chains() -> None:
    """Not memorised: novel entities + numbers, still correct."""
    assert _ans(
        "Sam's box is 10 pounds. His crate is twice the weight of his box. "
        "His pallet is three times as heavy as his crate. How heavy is the pallet?"
    ) == 60.0
    assert _ans(
        "Mary is 6. Her sister is twice as old as Mary. "
        "Her mother is five times as old as her sister. How old is the mother?"
    ) == 60.0


def test_refuses_comparative_additive() -> None:
    """WRONG=0 FLOOR: '12 inches longer than' is additive, not a ratio — must refuse,
    never read the 12 as a grounding (the bug that produced the lone held-out wrong)."""
    assert build_ratio_chain(
        "Jake's snake is 12 inches longer than Jenny's snake. How long is Jake's snake?"
    ) is None


def test_refuses_underdetermined_chain() -> None:
    """No grounded base -> refuse."""
    assert build_ratio_chain(
        "The dog is twice the age of the cat. How old is the dog?"
    ) is None
