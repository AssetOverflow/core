"""DETERMINE — reason over realized structure → assert (as-told) / refuse (roadmap Step 4).

Step D (CLOSE) adds ``consolidate_once``: idle deductive consolidation of soundly-derived
facts back into the held self, so the loop learns from determined facts.
"""

from generate.determine.consolidate import ConsolidationResult, consolidate_once
from generate.determine.determine import Determined, Undetermined, determine
from generate.determine.render import render_determination

__all__ = [
    "ConsolidationResult",
    "Determined",
    "Undetermined",
    "consolidate_once",
    "determine",
    "render_determination",
]
