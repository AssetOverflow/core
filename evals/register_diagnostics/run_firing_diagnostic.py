"""Marker-firing diagnostic across the 100-pack register catalog.

For every (register_pack, cognition_case) cell, runs the prompt under
the pack and reports whether the opening / closing markers actually
fired (non-empty selection from the bucket).

Why this exists.  The 100-pack widened tour revealed that some packs
collapse to baseline on certain prompts — their non-empty marker
entries simply don't get selected by the SHA-256 seed for that
particular (seed_text, register_id, turn_idx) combination.  Without a
diagnostic, we can only spot collapses by eyeballing surfaces.  With
it, we get a deterministic firing-rate per pack that reveals:

  * **Bucket-rate** — the structural ceiling: fraction of non-empty
    entries in the bucket.  A pack with ``openings=["", "X", "Y"]``
    has a 2/3 = 66.7% bucket-rate; selections are uniform across the
    bucket, so 1/3 of seeds will pick ``""`` (no firing).
  * **Observed firing rate** — fraction of cognition cases where the
    marker actually fires.  Should converge to bucket-rate as the
    case set grows; large deviations indicate a non-uniform seed
    space (rare; here we assume uniformity holds and treat deviation
    as noise).
  * **Cells where both markers fire** vs. cells where neither does.

Pack categories surfaced:

  * **Always-firing**  : opening_fires_rate == 1.0 (no ``""`` in
    bucket). Most expressive; users see character every turn.
  * **Sometimes-firing**: 0 < rate < 1.0. ``""`` is intentionally in
    the bucket so the register "feels lighter" — quiet turns mixed
    in.  This is by design for socratic_v1, terse_v1, convivial_v1.
  * **Never-firing**   : 0.0 (empty bucket or all-``""``). These
    packs depend entirely on ``realizer_overrides`` for stylistic
    differentiation.  Legitimate for terse_v1; suspicious elsewhere.

Output: human-readable table (default) or JSON (``--json``).
Operator-only utility; runs against ratified packs on disk.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any

from chat.register_variation import decorate_surface
from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.run_cognition_eval import load_cases
from packs.register.loader import RegisterPackError, load_register_pack
from scripts.ratify_register_packs import REGISTER_IDS


@dataclass(frozen=True, slots=True)
class PackFiringStats:
    """Diagnostic stats for one register pack across the cognition lane."""

    register_id: str

    # Structural (bucket geometry — independent of cases)
    opening_bucket_size: int
    opening_nonempty_count: int
    closing_bucket_size: int
    closing_nonempty_count: int

    # Observed (per cognition case)
    total_cases: int
    openings_fired: int
    closings_fired: int
    both_fired: int
    neither_fired: int

    # Distinct opening / closing strings actually selected
    distinct_openings_used: int
    distinct_closings_used: int

    @property
    def opening_bucket_rate(self) -> float:
        if self.opening_bucket_size == 0:
            return 0.0
        return self.opening_nonempty_count / self.opening_bucket_size

    @property
    def opening_observed_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.openings_fired / self.total_cases

    @property
    def closing_bucket_rate(self) -> float:
        if self.closing_bucket_size == 0:
            return 0.0
        return self.closing_nonempty_count / self.closing_bucket_size

    @property
    def closing_observed_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.closings_fired / self.total_cases

    @property
    def category(self) -> str:
        """Coarse pack category surfaced by the diagnostic."""
        opens_ever = self.openings_fired > 0
        closes_ever = self.closings_fired > 0
        if not opens_ever and not closes_ever:
            return "silent"  # markers never fire — pure overrides
        opens_always = self.openings_fired == self.total_cases
        closes_always = self.closings_fired == self.total_cases
        if opens_always and closes_always:
            return "always_firing"
        if opens_ever or closes_ever:
            return "sometimes_firing"
        return "uncategorised"  # unreachable

    def as_dict(self) -> dict[str, Any]:
        return {
            "register_id": self.register_id,
            "category": self.category,
            "opening": {
                "bucket_size": self.opening_bucket_size,
                "nonempty_in_bucket": self.opening_nonempty_count,
                "bucket_rate": round(self.opening_bucket_rate, 4),
                "fired": self.openings_fired,
                "observed_rate": round(self.opening_observed_rate, 4),
                "distinct_strings_used": self.distinct_openings_used,
            },
            "closing": {
                "bucket_size": self.closing_bucket_size,
                "nonempty_in_bucket": self.closing_nonempty_count,
                "bucket_rate": round(self.closing_bucket_rate, 4),
                "fired": self.closings_fired,
                "observed_rate": round(self.closing_observed_rate, 4),
                "distinct_strings_used": self.distinct_closings_used,
            },
            "cells": {
                "total": self.total_cases,
                "both_fired": self.both_fired,
                "neither_fired": self.neither_fired,
            },
        }


def _measure_pack(register_id: str, cases: list[dict]) -> PackFiringStats:
    """Run every cognition case under *register_id* and collect firing stats."""
    pack = load_register_pack(register_id, require_ratified=False)
    markers = pack.discourse_markers
    opening_bucket = tuple(markers.openings)
    closing_bucket = tuple(markers.closings)
    opening_nonempty = sum(1 for x in opening_bucket if x)
    closing_nonempty = sum(1 for x in closing_bucket if x)

    openings_fired = 0
    closings_fired = 0
    both_fired = 0
    neither_fired = 0
    openings_used: Counter[str] = Counter()
    closings_used: Counter[str] = Counter()

    # For each case, run a fresh runtime to get the pre-decoration
    # (canonical) surface, then call ``decorate_surface`` directly
    # against the pack to recover the byte-identical marker selection
    # the runtime would have used.  This avoids depending on TurnEvent
    # surfacing the chosen markers (which it currently does not — only
    # ``register_variant_id`` is exposed).
    for case in cases:
        rt_case = ChatRuntime(config=RuntimeConfig(register_pack_id=register_id))
        pipe_case = CognitiveTurnPipeline(rt_case)
        pipe_case.run(case["prompt"])
        turn = rt_case.turn_log[-1]
        canonical = getattr(turn, "register_canonical_surface", "") or turn.surface
        decoration = decorate_surface(canonical, pack, turn_idx=0)
        opened = bool(decoration.opening)
        closed = bool(decoration.closing)
        if opened:
            openings_fired += 1
            openings_used[decoration.opening] += 1
        if closed:
            closings_fired += 1
            closings_used[decoration.closing] += 1
        if opened and closed:
            both_fired += 1
        if not opened and not closed:
            neither_fired += 1

    return PackFiringStats(
        register_id=register_id,
        opening_bucket_size=len(opening_bucket),
        opening_nonempty_count=opening_nonempty,
        closing_bucket_size=len(closing_bucket),
        closing_nonempty_count=closing_nonempty,
        total_cases=len(cases),
        openings_fired=openings_fired,
        closings_fired=closings_fired,
        both_fired=both_fired,
        neither_fired=neither_fired,
        distinct_openings_used=len(openings_used),
        distinct_closings_used=len(closings_used),
    )


def run_diagnostic(
    cases: list[dict] | None = None,
    register_ids: tuple[str, ...] | None = None,
) -> list[PackFiringStats]:
    """Run firing diagnostic across every ratified register pack."""
    cases = cases if cases is not None else load_cases()
    ids = register_ids if register_ids is not None else REGISTER_IDS
    return [_measure_pack(rid, cases) for rid in ids]


def _print_human(stats: list[PackFiringStats]) -> None:
    print("=" * 100)
    print(
        f"  Register firing diagnostic — {len(stats)} packs × "
        f"{stats[0].total_cases if stats else 0} cognition cases"
    )
    print("=" * 100)
    print()
    header = (
        f"  {'register_id':24s}  "
        f"{'category':17s}  "
        f"{'open_b':>7s} {'open_o':>7s}  "
        f"{'clos_b':>7s} {'clos_o':>7s}  "
        f"{'both':>5s} {'none':>5s}  "
        f"{'dist_o':>6s} {'dist_c':>6s}"
    )
    print(header)
    print(f"  {'-' * 96}")
    cat_counts: Counter[str] = Counter()
    for s in stats:
        cat_counts[s.category] += 1
        print(
            f"  {s.register_id:24s}  "
            f"{s.category:17s}  "
            f"{s.opening_bucket_rate:>7.2%} {s.opening_observed_rate:>7.2%}  "
            f"{s.closing_bucket_rate:>7.2%} {s.closing_observed_rate:>7.2%}  "
            f"{s.both_fired:>5d} {s.neither_fired:>5d}  "
            f"{s.distinct_openings_used:>6d} {s.distinct_closings_used:>6d}"
        )
    print()
    print(f"  Pack category distribution:")
    for cat, n in cat_counts.most_common():
        print(f"    {cat:20s} {n:>4d}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    emit_json = "--json" in argv

    try:
        stats = run_diagnostic()
    except RegisterPackError as e:
        print(f"register pack error: {e}", file=sys.stderr)
        return 2

    if emit_json:
        print(json.dumps(
            [s.as_dict() for s in stats],
            indent=2, sort_keys=True, default=str,
        ))
    else:
        _print_human(stats)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
