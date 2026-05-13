"""
Content-addressed identifier computation for CandidateGeometricPressure.

Two functions:
  make_pressure_id   — SHA-256 over the full canonical packet (structural identity)
  make_semantic_key  — SHA-256 over semantic fields only (claim-level identity)

This module transparently attempts to import core_ingest_rs (the PyO3/Rust
backend) for these operations. If the Rust extension is not built, pure-Python
fallbacks handle every case with identical behavior.

The Rust path is a compilation target chosen after the data model was locked —
Axiom 6, Compilation-Last.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    from core_ingest_rs import sha256_hex, canonical_json  # type: ignore[import]
    _RUST = True
except ImportError:
    _RUST = False


# ---------------------------------------------------------------------------
# Pure-Python fallbacks
# ---------------------------------------------------------------------------

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_pressure_id(
    *,
    kind: str,
    modality: str,
    provenance: list[dict],
    frontend_id: str,
    frontend_version: str,
    determinism: str,
    review_level: str,
    confidence: float,
    uncertainty: float,
    lemma: str,
    subject: str,
    verb: str,
    object_: str,
    payload_json: str,
) -> str:
    """
    SHA-256 over all canonical packet fields.

    Two packets are structurally identical (same pressure_id) iff every field
    is identical, including provenance. Two packets asserting the same claim
    from different sources will have different pressure_ids but the same
    semantic_key.
    """
    payload = _canonical_json({
        "kind": kind,
        "modality": modality,
        "lemma": lemma,
        "subject": subject,
        "verb": verb,
        "object": object_ or None,
        "payload_json": payload_json,
        "provenance": provenance,
        "frontend": {
            "instrument_id": frontend_id,
            "determinism": determinism,
            "version": frontend_version,
        },
        "confidence": confidence,
        "uncertainty": uncertainty,
        "review_level": review_level,
    })
    fn = sha256_hex if _RUST else _sha256_hex
    return fn(payload.encode("utf-8"))


def make_semantic_key(
    *,
    kind: str,
    modality: str,
    lemma: str,
    subject: str,
    verb: str,
    object_: str,
    payload_json: str,
) -> str:
    """
    SHA-256 over semantic fields only.

    Two packets with the same semantic_key assert the same claim regardless
    of where or by whom they were proposed. The IngestCompiler uses this for
    convergent-evidence detection.
    """
    payload = _canonical_json({
        "kind": kind,
        "modality": modality,
        "lemma": lemma,
        "subject": subject,
        "verb": verb,
        "object": object_,
        "payload_json": payload_json,
    })
    fn = sha256_hex if _RUST else _sha256_hex
    return fn(payload.encode("utf-8"))
