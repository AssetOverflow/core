from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    input_packs: tuple[str, ...] = (
        "en_minimal_v1",
        "en_core_cognition_v1",
        "he_logos_micro_v1",
        "grc_logos_micro_v1",
    )
    output_language: str = "en"
    frame_pack: str = "en"
    max_tokens: int = 32
    allow_cross_language_recall: bool = True
    allow_cross_language_generation: bool = False
    vault_reproject_interval: int = 20
    use_salience: bool = True
    salience_top_k: int = 16
    inhibition_threshold: float = 0.3
    inner_loop_admissibility: bool = False
    admissibility_threshold: float = 0.0
    # ADR-0026 / Phase 3 — margin-based admissibility.  ``mode``
    # selects between ADR-0024's per-candidate threshold check and
    # the ranked-with-margin check.  Default "threshold" preserves
    # ADR-0024 acceptance evidence; opt-in "margin" replaces the
    # static-threshold gate with a scale-invariant margin.
    admissibility_mode: str = "threshold"
    admissibility_margin: float = 0.4
    # ADR-0027 — Identity pack id loaded at runtime startup.  Empty string
    # resolves to ``DEFAULT_IDENTITY_PACK``.  CLI override on chat:
    # ``core chat --identity <pack_id>``.  See docs/identity_packs.md.
    identity_pack: str = ""
    # ADR-0033 — Ethics pack id loaded at runtime startup.  Empty string
    # resolves to ``DEFAULT_ETHICS_PACK``.  See docs/ethics_packs.md.
    ethics_pack: str = ""
    # ADR-0046 / ADR-0047 — forward graph constraint.  When True, the
    # PropositionGraph built from the classified intent + articulation
    # plan is converted into an AdmissibilityRegion BEFORE generate()
    # runs (Pillar 1→2→3 coupling closes on the live path).  Default
    # False preserves existing behavior during the transition window —
    # ADR-0024's honest-refusal exhaustion is the correct response when
    # the constraint geometry and the walk candidate pool do not
    # intersect, but operators must opt in to observing that behavior
    # on their workloads.  Enable to live the forward constraint;
    # disable to retain the pre-ADR-0046 unconstrained walk.
    forward_graph_constraint: bool = False


DEFAULT_IDENTITY_PACK: str = "default_general_v1"
DEFAULT_ETHICS_PACK: str = "default_general_ethics_v1"
DEFAULT_CONFIG = RuntimeConfig()
