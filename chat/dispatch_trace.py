from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DispatchAttempt:
    source: str             # "pack" | "teaching" | "partial" | "oov" | "universal_disclosure"
    outcome: str            # "admitted" | "skipped" | "fell_through"
    reason: str             # human-readable + machine-stable (no PII)

@dataclass(frozen=True, slots=True)
class DispatchTrace:
    attempts: tuple[DispatchAttempt, ...]
    selected: str           # source that produced the final surface
