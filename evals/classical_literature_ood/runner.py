"""Phase 5.7 domain fluency OOD eval lane runner.

Verifies the deterministic realizer produces grammatical English
surfaces across the 13 grammatical-coverage constructions when the
(subject, predicate, object) vocabulary is **out of the
en_core_cognition_v1 distribution** — drawn from the epic, tragedy, lyric
public domains and the held-out comedy domain.

Scoring is delegated to the grammatical_coverage runner so the
rubric stays consistent across all fluency-OOD lanes.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

from typing import Any

from evals.grammatical_coverage.runner import LaneReport, run_lane as _run


def run_lane(cases: list[dict[str, Any]], *, config: Any = None) -> LaneReport:
    return _run(cases, config=config)
