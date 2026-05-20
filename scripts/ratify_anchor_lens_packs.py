"""Ratify anchor-lens packs (ADR-0073b, Plan Phase L1.2).

For each pack in ``packs/anchor_lens/<lens_id>.json``:

1. Verify schema fields are present and well-shaped (delegated to the
   loader, run with ``require_ratified=False``).
2. Compute the canonical ``pack_source_sha`` (SHA-256 of the pack with
   ``mastery_report_sha256`` blanked) — self-referential provenance.
3. Apply the L1.2 gate: only **null lenses** (``primary_substrate='none'``
   + empty ``semantic_domain_preferences`` + empty
   ``cognitive_mode_label``) are ratifiable through this script.  Later
   sub-phases (L1.3) will widen this gate to cover non-null lenses
   with their own ratification method.
4. Build a self-sealed ``MasteryReport``-shaped dict capturing the
   evidence claim (``byte_identity_null_lift``).
5. Write ``<lens_id>.mastery_report.json``.
6. Update the pack's ``mastery_report_sha256`` field to match.

Idempotent: re-running on an already-ratified pack produces
byte-identical files.  Run whenever an anchor-lens pack changes.

Trust boundary
--------------
This script writes to ``packs/anchor_lens/`` on disk.  It is
operator-only (no runtime entrypoint).  Pack-id sanitisation, schema
validation, and seal verification all flow through
``packs/anchor_lens/loader.py`` — see ``ADR-0051`` doctrine.

Mirror of ``scripts/ratify_register_packs.py`` — anchor lens is the
substantive-axis sibling of the presentation-axis register class.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from formation.hashing import self_seal
from packs.anchor_lens.loader import (
    AnchorLensError,
    load_anchor_lens,
)

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs" / "anchor_lens"
ISSUED_AT = "2026-05-19T00:00:00Z"
LENS_IDS: tuple[str, ...] = (
    "default_unanchored_v1",
)


def _canonical_pack_bytes_for_hashing(pack: dict) -> bytes:
    """Serialize the pack with ``mastery_report_sha256`` blanked."""
    cleaned = dict(pack)
    cleaned["mastery_report_sha256"] = ""
    return json.dumps(
        cleaned, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _pack_source_sha(pack: dict) -> str:
    return hashlib.sha256(_canonical_pack_bytes_for_hashing(pack)).hexdigest()


def _is_null_lens(pack: dict) -> bool:
    if pack.get("primary_substrate") != "none":
        return False
    prefs = pack.get("semantic_domain_preferences", [])
    if not isinstance(prefs, list) or prefs:
        return False
    label = pack.get("cognitive_mode_label", "")
    if not isinstance(label, str) or label:
        return False
    return True


def _ratify_one(pack_path: Path, lens_id: str) -> tuple[dict, dict[str, Any]]:
    """Returns (updated_pack_dict, mastery_report_dict).  Does not write."""
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    # Validate through loader with require_ratified=False so we can
    # ratify packs whose mastery_report_sha256 is empty.
    load_anchor_lens(
        lens_id,
        search_paths=(pack_path.parent,),
        require_ratified=False,
    )

    pack_source_sha = _pack_source_sha(pack)

    # L1.2 gate: only null lenses are ratifiable here.  L1.3 will
    # widen this to cover non-null lenses with a different
    # ratification method.
    if not _is_null_lens(pack):
        raise SystemExit(
            f"L1.2 gate refuses {lens_id!r}: not a null lens. "
            "primary_substrate must be 'none', semantic_domain_preferences "
            "must be empty, and cognitive_mode_label must be empty."
        )

    ratification_method = "byte_identity_null_lift"

    report: dict[str, Any] = {
        "lens_id": lens_id,
        "schema_version": "1.0.0",
        "issued_at": ISSUED_AT,
        "pack_source_sha256": pack_source_sha,
        "ratification_method": ratification_method,
        "ratified": True,
        "evidence": {
            "primary_substrate": str(pack.get("primary_substrate", "")),
            "semantic_domain_preferences_empty": True,
            "semantic_domain_preferences_count": 0,
            "cognitive_mode_label_empty": True,
        },
        "failure_reasons": [],
        "report_sha256": "",
    }
    sealed = self_seal(report, sha_field="report_sha256")

    pack["mastery_report_sha256"] = sealed["report_sha256"]
    return pack, sealed


def main() -> int:
    updated = 0
    skipped = 0
    for lens_id in LENS_IDS:
        pack_path = PACKS_DIR / f"{lens_id}.json"
        if not pack_path.is_file():
            print(f"skip: {pack_path} not found", file=sys.stderr)
            continue
        try:
            pack_after, report_dict = _ratify_one(pack_path, lens_id)
        except AnchorLensError as exc:
            print(f"refused: {lens_id} — {exc}", file=sys.stderr)
            return 1

        report_path = PACKS_DIR / f"{lens_id}.mastery_report.json"
        report_text = json.dumps(report_dict, indent=2, sort_keys=True) + "\n"
        prior_report = (
            report_path.read_text(encoding="utf-8")
            if report_path.is_file()
            else ""
        )
        prior_pack = json.loads(pack_path.read_text(encoding="utf-8"))

        pack_text = json.dumps(pack_after, indent=2, sort_keys=True) + "\n"
        prior_pack_text = json.dumps(prior_pack, indent=2, sort_keys=True) + "\n"

        if report_text == prior_report and pack_text == prior_pack_text:
            skipped += 1
            print(f"{lens_id}: already up-to-date (idempotent)")
            continue

        report_path.write_text(report_text, encoding="utf-8")
        pack_path.write_text(pack_text, encoding="utf-8")
        updated += 1
        print(f"{lens_id}: ratified → {report_dict['report_sha256'][:16]}...")

    print(f"\n{updated} updated, {skipped} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
