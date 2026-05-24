"""Versioned metric carrier for replay evidence gates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricSet:
    version: int
    metrics: tuple[str, ...]


__all__ = ["MetricSet"]
