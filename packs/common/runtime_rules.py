"""Deterministic runtime helpers for local language-pack rules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.physics.energy import EnergyClass
from core.physics.valence import lift_valence
from core_ingest.types import (
    CandidateGeometricPressure,
    DeterminismClass,
    FrontendTrace,
    Modality,
    ReviewLevel,
    SourceSpan,
)


@dataclass(frozen=True, slots=True)
class SurfaceRealization:
    surface: str
    language: str
    field_target: str | None = None
    energy_class: str | None = None
    valence: dict[str, object] | None = None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def analysis_payload(analysis: object) -> dict[str, Any]:
    if isinstance(analysis, dict):
        payload = dict(analysis.get("input", analysis))
    else:
        payload = dict(getattr(analysis, "__dict__", {}))
    if not payload:
        raise ValueError("analysis must expose lemma_id or sense_id fields")
    return payload


def lift_from_pack(pack_dir: Path, analysis: object, *, language: str) -> list[CandidateGeometricPressure]:
    payload = analysis_payload(analysis)
    senses = {record["sense_id"]: record for record in read_jsonl(pack_dir / "senses.jsonl")}
    lemmas = {record["lemma_id"]: record for record in read_jsonl(pack_dir / "lemmas.jsonl")}
    sense = senses.get(str(payload.get("sense_id", "")))
    lemma_id = str(payload.get("lemma_id") or (sense or {}).get("lemma_id") or "")
    lemma = lemmas.get(lemma_id)
    if lemma is None:
        raise KeyError(f"unknown lemma_id: {lemma_id}")
    field_target = str((sense or {}).get("field_target") or lemma["field_hooks"][0])
    pressure_kind = str(payload.get("pressure_kind", "semantic"))
    features = {
        "morph_class": lemma.get("morph_class", ""),
        "semantic_family": lemma.get("semantic_family", ""),
    }
    valence = lift_valence(
        lemma=str(lemma["script_form"]),
        language=language,
        features=features,
    ).to_payload()
    packet_payload = {
        "field_target": field_target,
        "pressure_kind": pressure_kind,
        "energy_class_hint": EnergyClass.E2.value,
        "valence": valence,
        "source": {
            "lemma_id": lemma_id,
            "sense_id": payload.get("sense_id"),
            "frame_id": payload.get("frame_id"),
        },
    }
    canonical = json.dumps(packet_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    span = SourceSpan(byte_start=0, byte_end=max(1, len(canonical.encode("utf-8"))), source_sha256=digest)
    packet = CandidateGeometricPressure(
        kind=pressure_kind,
        modality=Modality.SCRIPTURE if language in {"he", "el", "grc"} else Modality.TEXT,
        provenance=(span,),
        frontend=FrontendTrace(
            instrument_id=f"{language}.lift_rules",
            determinism=DeterminismClass.D0,
            version="1.0.0",
        ),
        review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
        confidence=1.0,
        uncertainty=0.0,
        lemma=str(lemma["script_form"]),
        payload_json=canonical,
    )
    return [packet]


def readback_from_intent(field_state: object, intent: object, *, language: str) -> SurfaceRealization:
    payload = analysis_payload(intent or {"surface": ""})
    surface = payload.get("surface")
    if surface is None and "tokens" in payload:
        surface = " ".join(str(token) for token in payload["tokens"])
    if surface is None and "lemma" in payload:
        surface = str(payload["lemma"])
    if surface is None and "script_form" in payload:
        surface = str(payload["script_form"])
    if surface is None:
        energy = getattr(field_state, "energy", None)
        surface = energy.energy_class.value if energy is not None else ""
    energy = getattr(field_state, "energy", None)
    valence = getattr(field_state, "valence", None)
    return SurfaceRealization(
        surface=str(surface),
        language=language,
        field_target=payload.get("field_target"),
        energy_class=None if energy is None else energy.energy_class.value,
        valence=None if valence is None else valence.to_payload(),
    )
