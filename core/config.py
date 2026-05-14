from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    input_packs: tuple[str, ...] = ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
    output_language: str = "en"
    frame_pack: str = "en"
    max_tokens: int = 32
    allow_cross_language_recall: bool = True
    allow_cross_language_generation: bool = False


DEFAULT_CONFIG = RuntimeConfig()
