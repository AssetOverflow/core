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


DEFAULT_CONFIG = RuntimeConfig()
