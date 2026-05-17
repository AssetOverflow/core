"""Canonical JSON serialization + SHA-256 helpers for the Formation Pipeline.

Every artifact in the pipeline is content-addressed.  Two artifacts with the
same logical content must produce the same SHA byte-for-byte, across runs and
across Python sessions.  This module owns the canonical form.

Rules:
- ``canonical_json`` sorts keys and uses tight separators.
- Tuples and lists serialize identically (lists in JSON).
- Floats are not permitted in hashed payloads; use strings.  This avoids
  platform-dependent float repr.
- ``self_seal`` computes a SHA over a dict whose ``sha`` field has been
  blanked, then writes the SHA in.  Verifiers reverse the process.

No pickle anywhere.  Pickle defeats replay determinism and is a
code-execution attack surface (see CLAUDE.md trust doctrine).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> bytes:
    """Serialize ``payload`` to canonical UTF-8 JSON bytes.

    Sorted keys, tight separators, ensure_ascii=False, no trailing newline.
    Floats are rejected because their repr varies subtly across platforms.
    """
    _reject_floats(payload)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_of(payload: Any) -> str:
    """Return the lowercase hex SHA-256 of the canonical JSON of ``payload``."""
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def self_seal(payload: dict[str, Any], sha_field: str = "report_sha256") -> dict[str, Any]:
    """Return ``payload`` with ``sha_field`` set to its self-sealing SHA.

    The SHA is computed over the payload with ``sha_field`` blanked to the
    empty string.  This is the standard self-sealing convention; verifiers
    reproduce the SHA by blanking the field and re-hashing.
    """
    if sha_field not in payload:
        raise ValueError(f"self_seal: payload missing required field {sha_field!r}")
    sealed = dict(payload)
    sealed[sha_field] = ""
    digest = sha256_of(sealed)
    sealed[sha_field] = digest
    return sealed


def verify_seal(payload: dict[str, Any], sha_field: str = "report_sha256") -> bool:
    """Return True iff ``payload[sha_field]`` matches its self-sealing SHA."""
    if sha_field not in payload:
        return False
    claimed = payload[sha_field]
    if not isinstance(claimed, str) or not claimed:
        return False
    probe = dict(payload)
    probe[sha_field] = ""
    return sha256_of(probe) == claimed


def _reject_floats(payload: Any) -> None:
    """Walk ``payload`` and raise if any float is found.

    Floats are non-deterministic across platforms in subtle ways (and ``json``
    emits them with repr-style precision).  Pipeline artifacts must encode
    numeric quantities as strings or integers.
    """
    if isinstance(payload, float):
        raise TypeError(
            "canonical_json: float values are forbidden in hashed payloads; "
            "encode numbers as strings or integers"
        )
    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"canonical_json: dict keys must be strings, got {type(key).__name__}"
                )
            _reject_floats(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _reject_floats(item)
