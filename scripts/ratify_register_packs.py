"""Ratify register packs (ADR-0068, Plan Phase R1).

For each pack in ``packs/register/<register_id>.json``:

1. Verify schema fields are present and well-shaped (delegated to the
   loader, run with ``require_ratified=False``).
2. Compute the canonical ``pack_source_sha`` (SHA-256 of the pack with
   ``mastery_report_sha256`` blanked) — self-referential provenance.
3. Apply the R1 gate: only **null registers** (empty
   ``realizer_overrides`` + empty ``discourse_markers``) are ratifiable
   through this script.  R3 will widen this gate to cover non-null
   registers with their own ratification method.
4. Build a self-sealed ``MasteryReport``-shaped dict capturing the
   evidence claim (``byte_identity_null_lift``).
5. Write ``<register_id>.mastery_report.json``.
6. Update the pack's ``mastery_report_sha256`` field to match.

Idempotent: re-running on an already-ratified pack produces
byte-identical files.  Run whenever a register pack changes.

Trust boundary
--------------
This script writes to ``packs/register/`` on disk.  It is operator-only
(no runtime entrypoint).  Pack-id sanitisation, schema validation, and
seal verification all flow through ``packs/register/loader.py`` — see
``ADR-0051`` doctrine.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

from formation.hashing import self_seal
from packs.register.loader import (
    RegisterPackError,
    load_register_pack,
)

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs" / "register"
ISSUED_AT = "2026-05-20T00:00:00Z"
REGISTER_IDS: tuple[str, ...] = (
    "default_neutral_v1",
    "terse_v1",
    "convivial_v1",
    "pedagogical_v1",
    "precise_v1",
    "formal_v1",
    "socratic_v1",
    "succinct_v1",
    "expansive_v1",
    "exhaustive_v1",
    "warm_v1",
    "cool_v1",
    "casual_v1",
    "intense_v1",
    "playful_v1",
    "calm_v1",
    "urgent_v1",
    "serene_v1",
    "dramatic_v1",
    "sober_v1",
    "clinical_v1",
    "colloquial_v1",
    "literary_v1",
    "journalistic_v1",
    "poetic_v1",
    "assertive_v1",
    "hedged_v1",
    "inviting_v1",
    "exploratory_v1",
    "didactic_v1",
    "dialectic_v1",
    "probing_v1",
    "affirming_v1",
    "curious_v1",
    "skeptical_v1",
    "confident_uncertain_v1",
    "peer_v1",
    "mentor_v1",
    "student_v1",
    "expert_v1",
    "scholar_v1",
    "practitioner_v1",
    "novice_v1",
    "narrator_v1",
    "journalist_v1",
    "elder_v1",
    "academic_v1",
    "conversational_v1",
    "executive_v1",
    "technical_v1",
    "legal_v1",
    "medical_v1",
    "scientific_v1",
    "philosophical_v1",
    "devotional_v1",
    "mathematical_v1",
    "engineering_v1",
    "plainspoken_v1",
    "cosmopolitan_v1",
    "diplomatic_v1",
    "blunt_v1",
    "aristocratic_v1",
    "folksy_v1",
    "urbane_v1",
    "timeless_v1",
    "contemporary_v1",
    "classic_v1",
    "neoteric_v1",
    "lyrical_v1",
    "cheerful_v1",
    "somber_v1",
    "melancholic_v1",
    "awed_v1",
    "grave_v1",
    "light_v1",
    "wry_v1",
    "dry_v1",
    "gentle_v1",
    "earnest_v1",
)

#: Valid IntentTag names for ``per_intent`` keys (ADR-0071, R4).  This
#: is the trust-boundary whitelist — operators cannot ship unknown
#: intent names.  Sourced from ``generate.intent.IntentTag``.
def _valid_intent_names() -> frozenset[str]:
    from generate.intent import IntentTag
    return frozenset(t.name for t in IntentTag)

# Known realizer_overrides keys (ADR-0070, Phase R3 + R6).  The allow-list
# is the trust boundary against arbitrary operator-authored data driving
# realizer dispatch.  Each entry maps a key name to a validator that
# returns True iff the value is in-bounds.
#
# R6 boolean knobs (drop_provenance_tag, compress_gloss, drop_articles,
# append_semantic_domain_clause): validated as strict bool only.  The
# realizer dispatch code that *reads* these keys lands with R6; the gate
# must accept them before that merge so packs can ratify cleanly.
_KNOWN_OVERRIDE_KEYS: dict[str, Callable[[Any], bool]] = {
    "disclosure_domain_count": lambda v: isinstance(v, int)
    and not isinstance(v, bool)
    and v in (1, 2, 3),
    # R6 boolean knobs — strict bool, no int coercion
    "drop_provenance_tag": lambda v: isinstance(v, bool),
    "compress_gloss": lambda v: isinstance(v, bool),
    "drop_articles": lambda v: isinstance(v, bool),
    "append_semantic_domain_clause": lambda v: isinstance(v, bool),
}


def _canonical_pack_bytes_for_hashing(pack: dict) -> bytes:
    """Serialize the pack with ``mastery_report_sha256`` blanked."""
    cleaned = dict(pack)
    cleaned["mastery_report_sha256"] = ""
    return json.dumps(
        cleaned, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _pack_source_sha(pack: dict) -> str:
    return hashlib.sha256(_canonical_pack_bytes_for_hashing(pack)).hexdigest()


def _is_null_register(pack: dict) -> bool:
    overrides = pack.get("realizer_overrides", {})
    markers = pack.get("discourse_markers", {})
    if not isinstance(overrides, dict) or overrides:
        return False
    if not isinstance(markers, dict):
        return False
    for bucket in ("openings", "transitions", "closings"):
        if markers.get(bucket):
            return False
    return True


def _validate_overrides_known_keys(pack: dict, register_id: str) -> None:
    """R4 gate — allow-list known realizer_overrides keys + per_intent
    nested block.  Unknown keys are refused.
    """
    overrides = pack.get("realizer_overrides", {})
    if not isinstance(overrides, dict):
        raise SystemExit(
            f"R4 gate refuses {register_id!r}: realizer_overrides is not a dict"
        )
    valid_intents = _valid_intent_names()
    for k, v in overrides.items():
        if k == "per_intent":
            _validate_per_intent_block(v, register_id, valid_intents)
            continue
        validator = _KNOWN_OVERRIDE_KEYS.get(k)
        if validator is None:
            raise SystemExit(
                f"R4 gate refuses {register_id!r}: unknown realizer_overrides "
                f"key {k!r}. Known keys: "
                f"{sorted(list(_KNOWN_OVERRIDE_KEYS) + ['per_intent'])}"
            )
        if not validator(v):
            raise SystemExit(
                f"R4 gate refuses {register_id!r}: realizer_overrides[{k!r}]"
                f"={v!r} out of bounds"
            )


def _validate_per_intent_block(
    block: object, register_id: str, valid_intents: frozenset[str],
) -> None:
    """R4 gate — per_intent intents must be valid IntentTag names; each
    sub-dict's keys must be in the same allow-list as flat keys.
    """
    if not isinstance(block, dict):
        raise SystemExit(
            f"R4 gate refuses {register_id!r}: realizer_overrides.per_intent "
            "must be a dict"
        )
    for intent_name, sub in block.items():
        if intent_name not in valid_intents:
            raise SystemExit(
                f"R4 gate refuses {register_id!r}: realizer_overrides"
                f".per_intent[{intent_name!r}] is not a valid IntentTag. "
                f"Valid intents: {sorted(valid_intents)}"
            )
        if not isinstance(sub, dict):
            raise SystemExit(
                f"R4 gate refuses {register_id!r}: realizer_overrides"
                f".per_intent[{intent_name!r}] must be a dict"
            )
        for sub_k, sub_v in sub.items():
            validator = _KNOWN_OVERRIDE_KEYS.get(sub_k)
            if validator is None:
                raise SystemExit(
                    f"R4 gate refuses {register_id!r}: realizer_overrides"
                    f".per_intent[{intent_name!r}] unknown key {sub_k!r}. "
                    f"Known keys: {sorted(_KNOWN_OVERRIDE_KEYS)}"
                )
            if not validator(sub_v):
                raise SystemExit(
                    f"R4 gate refuses {register_id!r}: realizer_overrides"
                    f".per_intent[{intent_name!r}][{sub_k!r}]={sub_v!r} "
                    "out of bounds"
                )


def _markers_have_content(pack: dict) -> bool:
    """True iff openings or closings has at least one entry (R4 needs
    one of these populated for a marker-using ratification).

    Empty-string entries count as content — the seed may legitimately
    pick "no marker this turn" from a bucket like ``["", "So,"]``.
    """
    markers = pack.get("discourse_markers", {})
    if not isinstance(markers, dict):
        return False
    for bucket in ("openings", "closings"):
        items = markers.get(bucket, [])
        if isinstance(items, list) and len(items) >= 1:
            return True
    return False


def _ratify_one(pack_path: Path, register_id: str) -> tuple[dict, dict[str, Any]]:
    """Returns (updated_pack_dict, mastery_report_dict).  Does not write."""
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    load_register_pack(
        register_id,
        search_paths=(pack_path.parent,),
        require_ratified=False,
    )

    pack_source_sha = _pack_source_sha(pack)

    # R4 gate: realizer_overrides must contain only known keys
    # (including the per_intent nested block); discourse markers may
    # be populated, but a register claiming non-null marker status
    # must have at least one of openings/closings populated.  Null
    # registers pass trivially.
    _validate_overrides_known_keys(pack, register_id)

    null_register = _is_null_register(pack)
    overrides = pack.get("realizer_overrides", {}) or {}
    markers = pack.get("discourse_markers", {}) or {}
    markers_used = _markers_have_content(pack)
    transitions_reserved = bool(
        isinstance(markers, dict) and markers.get("transitions")
    )

    if markers_used:
        ratification_method = "seeded_variation_replay_equivalence"
    elif null_register:
        ratification_method = "byte_identity_null_lift"
    else:
        ratification_method = "known_key_overrides_invariant_grounding"

    bucket_sizes = {
        b: (
            len(markers.get(b, []))
            if isinstance(markers, dict)
            and isinstance(markers.get(b, []), list)
            else 0
        )
        for b in ("openings", "transitions", "closings")
    }

    report: dict[str, Any] = {
        "register_id": register_id,
        "schema_version": "1.0.0",
        "issued_at": ISSUED_AT,
        "pack_source_sha256": pack_source_sha,
        "ratification_method": ratification_method,
        "ratified": True,
        "evidence": {
            "realizer_overrides_empty": not bool(overrides),
            "realizer_overrides_keys": sorted(overrides.keys()),
            "discourse_markers_empty": not markers_used
            and not transitions_reserved,
            "marker_bucket_sizes": bucket_sizes,
            "transitions_reserved": transitions_reserved,
            "depth_preference": str(pack.get("depth_preference", "")),
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
    for register_id in REGISTER_IDS:
        pack_path = PACKS_DIR / f"{register_id}.json"
        if not pack_path.is_file():
            print(f"skip: {pack_path} not found", file=sys.stderr)
            continue
        try:
            pack_after, report_dict = _ratify_one(pack_path, register_id)
        except RegisterPackError as exc:
            print(f"refused: {register_id} — {exc}", file=sys.stderr)
            return 1

        report_path = PACKS_DIR / f"{register_id}.mastery_report.json"
        report_text = json.dumps(
            report_dict, indent=2, sort_keys=True, ensure_ascii=False,
        ) + "\n"
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
                f"idempotent: {register_id} already ratified at "
                f"{pack_after['mastery_report_sha256'][:12]}\u2026"
            )
            skipped += 1
            continue
        pack_path.write_text(
            json.dumps(pack_after, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        report_path.write_text(report_text, encoding="utf-8")
        print(
            f"ratified: {register_id} \u2192 "
            f"{pack_after['mastery_report_sha256'][:12]}\u2026"
        )
        updated += 1
    print(f"\nratified {updated} pack(s); {skipped} already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
