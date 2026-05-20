"""Ratify rhetorical-style packs (ADR-0087 substrate phase).

For each pack in ``packs/rhetorical_style/<pack_id>.json``:

1. Compute canonical ``pack_source_sha256`` with
   ``mastery_report_sha256`` blanked.
2. Build a self-sealed mastery report under the
   ``rhetorical_style_substrate`` ratification method.
3. Write ``<pack_id>.mastery_report.json``.
4. Seal the pack with the report's SHA.

Idempotent: re-running on an already-ratified pack rewrites both
files deterministically.  Output is byte-identical when content is
byte-identical (canonical JSON discipline from
:mod:`formation.hashing`).

Substrate-phase ratification is content-only — no L1 lexicon gate
(the ADR's consumer phase is what teaches the realizer to read the
frames; until that lands, "frame name is in the allow-list" is the
only check the substrate needs).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from formation.hashing import canonical_json, self_seal, sha256_of

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs" / "rhetorical_style"

# Pack ids to ratify, in declaration order.
PACK_IDS: tuple[str, ...] = (
    # Null-lift baseline — must be first; ADR-0087 byte-identity
    # invariant test pins this pack's structural equivalence to
    # rhetorical_style_id=None.
    "default_unstyled_v1",
)


def _pack_source_sha256(pack_payload: dict[str, Any]) -> str:
    """SHA-256 of the pack with ``mastery_report_sha256`` blanked."""
    probe = dict(pack_payload)
    probe["mastery_report_sha256"] = ""
    return sha256_of(probe)


def _ratify_one(pack_id: str) -> tuple[bool, str]:
    """Ratify a single pack.  Returns (changed, message)."""
    pack_path = PACKS_DIR / f"{pack_id}.json"
    if not pack_path.is_file():
        return False, f"{pack_id}: pack file missing at {pack_path}"
    try:
        pack_payload = json.loads(pack_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"{pack_id}: pack JSON malformed ({exc})"

    # Recompute pack_source_sha256 from the current pack content.
    pack_source = _pack_source_sha256(pack_payload)

    # Build the mastery report.
    report: dict[str, Any] = {
        "pack_id": pack_id,
        "schema_version": pack_payload.get("schema_version", "1.0.0"),
        "ratification_method": "rhetorical_style_substrate",
        "ratified": True,
        "issued_at": pack_payload.get("issued_at", ""),
        "pack_source_sha256": pack_source,
        "failure_reasons": [],
        "evidence": {
            "default_unstyled": pack_payload.get("default_unstyled", False),
            "permitted_frames": pack_payload.get("permitted_frames", []),
            "required_moves_per_claim": pack_payload.get("required_moves_per_claim", []),
            "forbidden_moves": pack_payload.get("forbidden_moves", []),
            "version": pack_payload.get("version", 0),
        },
        "report_sha256": "",
    }
    sealed_report = self_seal(report, sha_field="report_sha256")
    report_sha = sealed_report["report_sha256"]

    report_path = PACKS_DIR / f"{pack_id}.mastery_report.json"
    report_bytes = canonical_json(sealed_report) + b"\n"

    # Update the pack's mastery_report_sha256 and re-write.
    pack_payload["mastery_report_sha256"] = report_sha
    pack_bytes = canonical_json(pack_payload) + b"\n"

    existing_pack_bytes = pack_path.read_bytes() if pack_path.is_file() else b""
    existing_report_bytes = report_path.read_bytes() if report_path.is_file() else b""

    changed = (
        existing_pack_bytes != pack_bytes
        or existing_report_bytes != report_bytes
    )
    if changed:
        report_path.write_bytes(report_bytes)
        pack_path.write_bytes(pack_bytes)
        return True, f"{pack_id}: ratified (report_sha={report_sha[:12]}..)"
    return False, f"{pack_id}: already ratified (report_sha={report_sha[:12]}..)"


def main(argv: list[str]) -> int:
    any_changed = False
    for pack_id in PACK_IDS:
        changed, msg = _ratify_one(pack_id)
        print(msg)
        if changed:
            any_changed = True
    return 0 if not any_changed or "--check" not in argv else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
