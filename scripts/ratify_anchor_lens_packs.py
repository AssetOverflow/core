"""Ratify anchor-lens packs (ADR-0073c).

For each pack in ``packs/anchor_lens/<lens_id>.json``:

1. L1 gate: substrate + atom must exist in the on-disk lexicon for that
   substrate (grc_logos_cognition_v1 for grc, he_core_cognition_v1 for he).
2. Compute canonical pack_source_sha (SHA-256 with mastery_report_sha256
   blanked).
3. Build a self-sealed MasteryReport under
   ``anchor_lens_lifts_proposition`` ratification method.
4. Write <lens_id>.mastery_report.json and seal the pack.

Idempotent: re-running on an already-ratified pack is a no-op.

Operator note
-------------
This script does NOT write runtime code.  All it does is verify that the
pack's declared atom exists in the named substrate lexicon and seal the
pack.  The realizer that reads lens packs is in ``generate/realizer.py``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from formation.hashing import self_seal

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs" / "anchor_lens"
LANG_DATA_DIR = Path(__file__).resolve().parents[1] / "language_packs" / "data"
ISSUED_AT = "2026-05-20T00:00:00Z"

# All anchor-lens pack ids to ratify, in declaration order.
LENS_IDS: tuple[str, ...] = (
    # null sentinel — must be first; ADR-0073b byte-identity invariant
    "default_unanchored_v1",
    # grc substrate
    "grc_logos_v1",
    "grc_aletheia_v1",
    "grc_zoe_v1",
    "grc_arche_v1",
    "grc_sophia_v1",
    "grc_epignosis_v1",
    "grc_episteme_v1",
    "grc_synesis_v1",
    # he substrate
    "he_logos_v1",
    "he_dabar_v1",
    "he_chayyim_v1",
    "he_emet_v1",
    "he_chokmah_v1",
    "he_chesed_v1",
    "he_shalom_v1",
    "he_tzedek_v1",
)

# Substrate -> lexicon pack directory name
_SUBSTRATE_LEXICON: dict[str, str] = {
    "grc": "grc_logos_cognition_v1",
    "he": "he_core_cognition_v1",
}


def _load_lexicon_atoms(substrate: str) -> frozenset[str]:
    """Return all semantic_domain values from the substrate lexicon."""
    lexicon_name = _SUBSTRATE_LEXICON.get(substrate)
    if lexicon_name is None:
        raise SystemExit(f"L1 gate: unknown substrate {substrate!r}")
    lexicon_path = LANG_DATA_DIR / lexicon_name / "lexicon.jsonl"
    if not lexicon_path.exists():
        raise SystemExit(f"L1 gate: lexicon not found at {lexicon_path}")
    atoms: set[str] = set()
    for line in lexicon_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        for domain in entry.get("semantic_domains", []):
            atoms.add(domain)
    return frozenset(atoms)


def _canonical_pack_bytes_for_hashing(pack: dict) -> bytes:
    cleaned = dict(pack)
    cleaned["mastery_report_sha256"] = ""
    return json.dumps(
        cleaned, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _pack_source_sha(pack: dict) -> str:
    return hashlib.sha256(_canonical_pack_bytes_for_hashing(pack)).hexdigest()


def _ratify_one(pack_path: Path, lens_id: str) -> tuple[dict, dict[str, Any]]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    substrate = pack.get("substrate", "")
    atom = pack.get("atom", "")

    # L1.3 gate: atom must exist in substrate lexicon
    lexicon_atoms = _load_lexicon_atoms(substrate)
    if atom not in lexicon_atoms:
        raise SystemExit(
            f"L1 gate refuses {lens_id!r}: atom {atom!r} not found in "
            f"{_SUBSTRATE_LEXICON[substrate]} lexicon. "
            f"Available atoms (sample): {sorted(lexicon_atoms)[:10]}"
        )

    pack_source_sha = _pack_source_sha(pack)

    report: dict[str, Any] = {
        "lens_id": lens_id,
        "schema_version": "1.0.0",
        "issued_at": ISSUED_AT,
        "pack_source_sha256": pack_source_sha,
        "ratification_method": pack.get(
            "ratification_method", "anchor_lens_lifts_proposition"
        ),
        "ratified": True,
        "evidence": {
            "substrate": substrate,
            "atom": atom,
            "source_entry_id": pack.get("source_entry_id", ""),
            "cognitive_mode": pack.get("cognitive_mode", ""),
            "pair_lens_id": pack.get("pair_lens_id"),
            "atom_in_lexicon": True,
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
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 1

        report_path = PACKS_DIR / f"{lens_id}.mastery_report.json"
        report_text = json.dumps(report_dict, indent=2, sort_keys=True) + "\n"
        prior_report = (
            report_path.read_text(encoding="utf-8")
            if report_path.is_file()
            else ""
        )
        prior_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        if (
            prior_pack.get("mastery_report_sha256")
            == pack_after["mastery_report_sha256"]
            and prior_report == report_text
        ):
            print(
                f"idempotent: {lens_id} already ratified at "
                f"{pack_after['mastery_report_sha256'][:12]}\u2026"
            )
            skipped += 1
            continue
        pack_path.write_text(
            json.dumps(pack_after, indent=2) + "\n", encoding="utf-8"
        )
        report_path.write_text(report_text, encoding="utf-8")
        print(
            f"ratified: {lens_id} \u2192 "
            f"{pack_after['mastery_report_sha256'][:12]}\u2026"
        )
        updated += 1
    print(f"\nratified {updated} lens pack(s); {skipped} already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
