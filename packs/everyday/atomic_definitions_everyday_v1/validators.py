"""Executable validators for the atomic_definitions_everyday_v1 pack."""

from __future__ import annotations

from pathlib import Path

from packs.common.validator import validate_pack_dir

PACK_DIR = Path(__file__).parent
PACK_ID = "atomic_definitions_everyday_v1"


def validate_pack() -> dict:
    return validate_pack_dir(PACK_DIR, pack_id=PACK_ID, language="en")


if __name__ == "__main__":
    import pprint

    pprint.pprint(validate_pack())
