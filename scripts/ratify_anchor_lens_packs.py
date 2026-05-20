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
    "grc_logos_v1",
    "he_logos_v1",
    "grc_zoe_v1",
    "grc_aletheia_v1",
    "grc_arche_v1",
    "he_dabar_v1",
    "he_chayyim_v1",
)

_SUBSTRATE_PACK_IDS: dict[str, tuple[str, ...]] = {
    "grc": ("grc_logos_cognition_v1", "grc_logos_micro_v1"),
    "he": ("he_core_cognition_v1", "he_logos_micro_v1"),
    "en": ("en_core_cognition_v1",),
}


def _atom_exists_in_substrate(atom: str, substrate: str) -> bool:
    """True iff some lemma in any pack matching ``substrate`` carries ``atom``."""
    import json as _json
    from pathlib import Path as _Path

    data_dir = _Path(__file__).resolve().parents[1] / "language_packs" / "data"
    for pack_id in _SUBSTRATE_PACK_IDS.get(substrate, ()):
        lexicon_path = data_dir / pack_id / "lexicon.jsonl"
        if not lexicon_path.is_file():
            continue
        for line in lexicon_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            if atom in entry.get("semantic_domains", []):
                return True
    return False


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

    # L1.3 gate: null lenses ratify under byte_identity_null_lift;
    # non-null lenses ratify under anchor_lens_lifts_proposition, with
    # the precondition that every preferred atom exists in at least one
    # lemma of the named substrate.  This is the trust boundary
    # preventing operators from shipping a lens that references
    # atoms not on disk.
    if _is_null_lens(pack):
        ratification_method = "byte_identity_null_lift"
        evidence: dict[str, Any] = {
            "primary_substrate": str(pack.get("primary_substrate", "")),
            "semantic_domain_preferences_empty": True,
            "semantic_domain_preferences_count": 0,
            "cognitive_mode_label_empty": True,
        }
    else:
        substrate = str(pack.get("primary_substrate", ""))
        if substrate not in ("grc", "he", "en"):
            raise SystemExit(
                f"L1.3 gate refuses {lens_id!r}: non-null lens "
                f"primary_substrate must be one of "
                f"{{'grc','he','en'}}, got {substrate!r}."
            )
        label = str(pack.get("cognitive_mode_label", ""))
        if not label:
            raise SystemExit(
                f"L1.3 gate refuses {lens_id!r}: non-null lens "
                "cognitive_mode_label must be non-empty."
            )
        prefs = pack.get("semantic_domain_preferences", []) or []
        if not isinstance(prefs, list) or not prefs:
            raise SystemExit(
                f"L1.3 gate refuses {lens_id!r}: non-null lens "
                "semantic_domain_preferences must be non-empty."
            )
        atoms_anchored: list[str] = []
        for atom in prefs:
            if _atom_exists_in_substrate(atom, substrate):
                atoms_anchored.append(atom)
            else:
                raise SystemExit(
                    f"L1.3 gate refuses {lens_id!r}: preferred atom "
                    f"{atom!r} does not appear in any "
                    f"{substrate!r} substrate lemma. Lenses must "
                    "point at atoms that exist on disk."
                )
        ratification_method = "anchor_lens_lifts_proposition"
        evidence = {
            "primary_substrate": substrate,
            "semantic_domain_preferences_empty": False,
            "semantic_domain_preferences_count": len(prefs),
            "cognitive_mode_label_empty": False,
            "cognitive_mode_label": label,
            "atoms_anchored_in_substrate": atoms_anchored,
        }

    report: dict[str, Any] = {
        "lens_id": lens_id,
        "schema_version": "1.0.0",
        "issued_at": ISSUED_AT,
        "pack_source_sha256": pack_source_sha,
        "ratification_method": ratification_method,
        "ratified": True,
        "evidence": evidence,
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
