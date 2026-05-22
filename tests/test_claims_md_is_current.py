"""CLAIMS.md must be deterministically regenerable from in-tree state.

The generator (``scripts/generate_claims.py``) reads only the capability
ledger and ``PINNED_SHAS`` — both already gated by other tests. This
test asserts the on-disk CLAIMS.md matches the freshly-rendered bytes,
so any drift between the file and its sources fails CI before merge.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.generate_claims import CLAIMS_PATH, render_claims


def test_claims_md_matches_generator_output() -> None:
    rendered = render_claims()
    on_disk = CLAIMS_PATH.read_bytes()
    if rendered != on_disk:
        raise AssertionError(
            "CLAIMS.md is stale. Regenerate with:\n"
            "  python3 scripts/generate_claims.py\n"
            f"  on-disk sha256:  {hashlib.sha256(on_disk).hexdigest()}\n"
            f"  computed sha256: {hashlib.sha256(rendered).hexdigest()}"
        )


def test_claims_md_render_is_deterministic() -> None:
    """Two render() calls in the same process must be byte-identical."""
    a = render_claims()
    b = render_claims()
    assert a == b


def test_claims_md_path_is_at_repo_root() -> None:
    assert CLAIMS_PATH.name == "CLAIMS.md"
    assert CLAIMS_PATH.parent == Path(__file__).resolve().parent.parent
