"""Mandatory case 0050 hazard pin for the consumption wiring.

ADR-0169 §"Acceptance gates": ratifying any synthetic CompositionClaim
under the SAFE allowlist must NOT cause case 0050 to admit.

This test ratifies a synthetic CompositionClaim under each of the three
allowlist categories, in turn, and confirms that case 0050 (the canary
preventing pre_frame_filler "fixes" from drifting into wrong>0) remains
refused under each.

Because the composition wiring goes through ``inject_from_match`` and
case 0050's refusal happens upstream (the regex parser already declines
to admit), this is a structural hazard pin: ratifying compositions
through the registry can never *enable* case 0050 because the
recognizer doesn't bind ``composition_shape`` for that sentence shape.
The pin verifies that invariant holds after this PR — i.e. the wiring
is dormant for case 0050 specifically.

See [[feedback-wrong-zero-hazard-case-0050]].
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from language_packs.compile_compositions import compile_compositions
from teaching.math_composition_ratification import SAFE_COMPOSITION_CATEGORIES


def setup_function(_):
    clear_composition_cache()


def _stage_pack(tmp_path: Path) -> Path:
    """Materialize a clean copy of the en_core_math_v1 pack into tmp_path."""
    here = Path(__file__).resolve()
    repo = here
    while repo.parent != repo and not (repo / "pyproject.toml").exists():
        repo = repo.parent
    src = repo / "language_packs" / "data" / "en_core_math_v1"
    dst = tmp_path / "en_core_math_v1"
    shutil.copytree(src, dst)
    # Strip any pre-existing composition entries — start clean.
    comp_dir = dst / "compositions"
    if comp_dir.exists():
        for f in comp_dir.glob("*.jsonl"):
            f.unlink()
    if (dst / "compositions.jsonl").exists():
        (dst / "compositions.jsonl").unlink()
    return dst


@pytest.mark.parametrize("category", sorted(SAFE_COMPOSITION_CATEGORIES))
def test_case_0050_stays_refused_under_each_allowlist_category(
    monkeypatch, tmp_path: Path, category: str
):
    """Ratifying any allowlisted CompositionClaim must not enable case 0050."""
    pack = _stage_pack(tmp_path)
    comp_dir = pack / "compositions"
    comp_dir.mkdir(exist_ok=True)
    (comp_dir / f"{category}.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": "bound(x) op bound(y)",
                "composition_category": category,
                "polarity": "affirms",
                "provenance": f"test_case_0050_hazard_{category}",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_compositions(pack)
    manifest_path = pack / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["composition_checksum"] = sha
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    # Redirect composition registry default to our staged pack.
    from generate.comprehension import composition_registry as cr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))

    # Load the registry — confirms the ratified entry is admitted at load
    # under the allowlist defense in depth.
    reg = cr.load_composition_registry()
    assert not reg.is_empty()

    # The hazard pin: case 0050's refusal lives in math_candidate_graph
    # upstream of inject_from_match. The recognizer for case 0050's
    # sentences does not publish ``composition_shape`` in parsed_anchors,
    # so the composition consult cannot fire. Verify the contract:
    # without ``composition_shape``, the registry consult is a no-op.
    from evals.refusal_taxonomy.shape_categories import ShapeCategory
    from generate.recognizer_anchor_inject import inject_from_match
    from generate.recognizer_match import RecognizerMatch

    class _FakeRec:
        spec_id = "test"

    # Simulate the recognizer matching case 0050's sentence shape: an
    # anchor with NO composition_shape (the matcher hasn't been extended).
    match = RecognizerMatch(
        recognizer=_FakeRec(),  # type: ignore[arg-type]
        category=ShapeCategory.CURRENCY_AMOUNT,
        outcome="admissible",
        graph_intent="amount",
        parsed_anchors=({"kind": "currency_amount"},),
    )
    result = inject_from_match(match, "case 0050 sentence")
    # The hazard pin: registry is non-empty + affirms exists, but without
    # a matcher-published composition_shape the consult cannot fire.
    # Refusal-preserving by construction.
    assert result == ()
