"""Executable validators for the Koine Greek depth pack."""

from __future__ import annotations

from pathlib import Path

from packs.common.validator import validate_pack_dir

PACK_DIR = Path(__file__).parent


def validate_pack() -> dict:
    return validate_pack_dir(PACK_DIR, pack_id="grc", language="grc")


if __name__ == "__main__":
    import pprint

    pprint.pprint(validate_pack())
