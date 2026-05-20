from __future__ import annotations

from chat.atom_equivalence import compare_atom_sets
from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


def _run(prompt: str, *, register: str = "default_neutral_v1", lens: str | None = None):
    rt = ChatRuntime(
        config=RuntimeConfig(
            register_pack_id=register,
            anchor_lens_id=lens,
        )
    )
    pipeline = CognitiveTurnPipeline(runtime=rt)
    result = pipeline.run(prompt)
    response = rt.turn_log[-1]
    return result, response


def test_pack_definition_equivalence_observable():
    _, event = _run("What is truth?")
    assert event.grounding_source == "pack"
    assert event.composer_graph_atom_status in {"equivalent", "graph_unconstrained"}
    if event.composer_graph_atom_status == "equivalent":
        assert event.composer_atom_set_hash != ""
        assert event.graph_atom_set_hash != ""
        assert event.composer_graph_atom_overlap_count > 0


def test_corrupt_graph_divergence_observable_without_surface_behavior():
    eq = compare_atom_sets(
        composer_atoms=("logos.aletheia.verity",),
        graph_atoms=("logos.unrelated.test_atom",),
        graph_unconstrained=False,
        applicable=True,
    )
    assert eq.status == "divergent"
    assert eq.overlap_count == 0
    assert eq.composer_atom_set_hash != ""
    assert eq.graph_atom_set_hash != ""
    assert eq.composer_atom_set_hash != eq.graph_atom_set_hash


def test_register_invariance_of_atom_equivalence():
    prompt = "What is truth?"
    neutral_result, neutral = _run(prompt, register="default_neutral_v1")
    terse_result, terse = _run(prompt, register="terse_v1")
    convivial_result, convivial = _run(prompt, register="convivial_v1")

    assert neutral.composer_atom_set_hash == terse.composer_atom_set_hash == convivial.composer_atom_set_hash
    assert neutral.graph_atom_set_hash == terse.graph_atom_set_hash == convivial.graph_atom_set_hash
    assert neutral.composer_graph_atom_status == terse.composer_graph_atom_status == convivial.composer_graph_atom_status
    assert neutral_result.trace_hash == terse_result.trace_hash == convivial_result.trace_hash


def test_anchor_lens_engaged_case_telemetry_computes_without_glyph_leak():
    _, engaged = _run("What is knowledge?", lens="grc_logos_v1")
    _, unanchored = _run("What is knowledge?")

    assert engaged.composer_graph_atom_status != ""
    assert unanchored.composer_graph_atom_status != ""
    assert all(ord(ch) < 128 for ch in engaged.surface)
    assert all(ord(ch) < 128 for ch in unanchored.surface)


def test_no_final_surface_lemma_parser_symbols():
    import pathlib

    forbidden = (
        "extract_candidate_surface_lemmas",
        "surface_lemma",
        "parse_surface_atoms",
    )
    root = pathlib.Path(__file__).resolve().parent.parent
    runtime_src = (root / "chat" / "runtime.py").read_text(encoding="utf-8")
    for token in forbidden:
        assert token not in runtime_src
