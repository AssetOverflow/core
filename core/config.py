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


DEFAULT_CONFIG = RuntimeConfig()
