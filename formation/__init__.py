"""Formation Pipeline — content-addressed, trust-bounded data foundry.

Turns raw subject material into Ratified, replay-proof versor relations
through Mine -> Smelt -> Forge -> Compose -> Compile -> Run -> Ratify ->
Promote, running entirely on top of CORE's existing CognitiveTurnPipeline.

The architectural commitment: nothing crosses a trust boundary without a
content-addressed audit trail.  See ``docs/formation_pipeline_plan.md``
and ``docs/runtime_contracts.md`` (Formation trust boundaries section).
"""

from formation.candidate import (
    CandidateState,
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.course import (
    CourseYAML,
    FormationPlan,
    MasteryReport,
    OreBundle,
    SubjectSpec,
    ValidatedTripleSet,
)
from formation.hashing import canonical_json, self_seal, sha256_of
from formation.smelter import SmeltedBundle, smelt

__all__ = [
    "CandidateState",
    "ConceptCandidate",
    "CounterCandidate",
    "CourseYAML",
    "FormationPlan",
    "MasteryReport",
    "OreBundle",
    "OrderingHint",
    "RelationCandidate",
    "SmeltedBundle",
    "SourceRef",
    "SubjectSpec",
    "ValidatedTripleSet",
    "canonical_json",
    "self_seal",
    "sha256_of",
    "smelt",
]

SCHEMA_VERSION: str = "1.0.0"
