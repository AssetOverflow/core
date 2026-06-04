"""Vision compiler eval gate table."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from evals.vision_sensorium.synth import synthesize
from sensorium.adapters.vision import make_vision_pack
from sensorium.registry import ModalityRegistry
from sensorium.vision import VisionCompiler, canonicalize_image, vision_evidence_trace
from sensorium.vision.grid import iter_tile_signals
from sensorium.vision.types import VisionIR

_EVAL_DIR = Path("evals/vision_sensorium")
TOL = 1e-6


def _load_fixtures() -> list[dict]:
    return json.loads((_EVAL_DIR / "fixtures.json").read_text())["fixtures"]


def _load_expected_ir() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in (_EVAL_DIR / "expected_ir.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def _load_expected_projection() -> dict[str, list[dict]]:
    return json.loads((_EVAL_DIR / "expected_projection.json").read_text())


def _event_type_counts(ir: VisionIR) -> dict[str, int]:
    events = (
        *ir.regions,
        *ir.contour_arcs,
        *ir.orient_events,
        *ir.texture_atoms,
        *ir.salient_events,
        *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


FIXTURES = _load_fixtures()
EXPECTED_IR = _load_expected_ir()
EXPECTED_PROJ = _load_expected_projection()
IDS = [fx["id"] for fx in FIXTURES]


@pytest.fixture(scope="module")
def compiler() -> VisionCompiler:
    return VisionCompiler()


@pytest.mark.parametrize("fx", FIXTURES, ids=IDS)
def test_vision_gate_table(fx, compiler):
    image = canonicalize_image(synthesize(fx))
    units = compiler.compile_image(image)
    signals_by_coord = {signal.coord: signal for signal in iter_tile_signals(image)}
    fid = fx["id"]

    assert image.canonical_sha256 == EXPECTED_IR[fid]["canonical_sha256"]
    assert len(units) == EXPECTED_IR[fid]["unit_count"]

    counts = Counter()
    for idx, unit in enumerate(units):
        assert unit.versor.shape == (32,)
        assert unit.versor.dtype == np.float32
        assert unit.versor_condition < TOL

        again = compiler.compile_tile(signals_by_coord[unit.coord])
        assert np.array_equal(unit.versor, again.versor)
        assert unit.merge_key == again.merge_key

        replay = compiler.compile_ir(unit.vision_ir)
        assert np.array_equal(unit.versor, replay.versor)
        assert unit.ir_sha256 == replay.ir_sha256 == EXPECTED_IR[fid]["unit_ir_sha256"][idx]

        counts.update(_event_type_counts(unit.vision_ir))
        reference = np.asarray(EXPECTED_PROJ[fid][idx]["reference_versor"], dtype=np.float32)
        assert unit.projection_sha256 == EXPECTED_PROJ[fid][idx]["projection_sha256"]
        assert np.allclose(unit.versor, reference, atol=TOL)

    assert dict(sorted(counts.items())) == EXPECTED_IR[fid]["event_type_counts"]


@pytest.mark.parametrize("fx", FIXTURES, ids=IDS)
def test_vision_trace_hygiene_no_pixels(fx, compiler):
    image = canonicalize_image(synthesize(fx))
    for unit in compiler.compile_image(image):
        trace = vision_evidence_trace(unit)
        assert "pixels" not in trace
        for value in trace.values():
            assert not isinstance(value, (np.ndarray, bytes, bytearray))


def test_vision_gate_closure_refuses_projection():
    image = canonicalize_image(synthesize(FIXTURES[1]))
    tile = iter_tile_signals(image)[0]
    reg = ModalityRegistry()
    reg.mount(make_vision_pack("vision_core_v1"), sample=tile)
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.project("vision_core_v1", tile)


def test_semantic_expectations_match_designed_fixtures():
    required = {
        "flat_gray": {"region.flat"},
        "vertical_edge": {"region.contrast", "orient.edge_energy"},
        "corner_block": {"region.corner"},
        "center_blob": {"region.blob"},
        "checker_texture": {"texture.regularity"},
        "contrast_ramp": {"region.contrast"},
        "chroma_split": {"region.chroma"},
        "salient_spot": {"salient.figure_ground"},
        "contour_box": {"contour.closure"},
    }
    for fid, event_types in required.items():
        assert event_types <= set(EXPECTED_IR[fid]["event_type_counts"]), fid
