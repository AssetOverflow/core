"""English fluency OOD eval lane runner (Phase 5.1).

Verifies the deterministic realizer produces grammatical English
surfaces across all 13 grammatical-coverage constructions when the
(subject, predicate, object) vocabulary is **out of the
en_core_cognition_v1 distribution** — drawn from nature, tech,
domestic, and chemistry domains that the seed pack does not
contain.

The structural claim under test: fluency is mechanistic in the
realizer (templates over typed graph nodes), not lexical
(pack-bound).  If the claim holds, OOD vocabulary passes the same
syntactic gates as the seed vocabulary did at v1/v2 of
`grammatical_coverage`.

Scoring is delegated to the grammatical_coverage runner so the
rubric stays consistent across lanes.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

from typing import Any

from evals.grammatical_coverage.runner import LaneReport, run_lane as _run


def run_lane(cases: list[dict[str, Any]], *, config: Any = None) -> LaneReport:
    return _run(cases, config=config)
