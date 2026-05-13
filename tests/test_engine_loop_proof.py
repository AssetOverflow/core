"""
tests/test_engine_loop_proof.py

Minimum executable proof that the CORE engine loop exists in running code:

    inject -> generate -> final_state -> vault.store -> vault.recall

This is intentionally narrow. It is not a benchmark suite and not a behavior
quality test. It proves the refined engine contract after the generation seam,
state immutability, backend routing, and assistant-final-state storage fixes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from algebra.versor import unitize_versor, versor_condition
from generate.result import GenerationResult
from generate.stream import generate
from ingest.gate import inject
from persona.motor import PersonaMotor
from session.context import SessionContext
from vault.store import VaultStore
from vocab.manifold import VocabManifold


ROOT = Path(__file__).resolve().parents[1]


def _positive_unit_reflector(seed: int) -> np.ndarray:
    """Construct a true positive-norm grade-1 versor in Cl(4,1)."""
    rng = np.random.default_rng(seed)
    vec4 = rng.standard_normal(4).astype(np.float32)
    norm4 = float(np.linalg.norm(vec4))
    if norm4 < 1e-6:
        vec4[0] = 1.0
        norm4 = 1.0

    vec = np.zeros(5, dtype=np.float32)
    vec[:4] = vec4
    vec[4] = 0.25 * norm4 * np.tanh(float(rng.standard_normal()))

    mv = np.zeros(32, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


def _minimal_vocab() -> VocabManifold:
    """
    Build a tiny deterministic manifold with non-identical true versors.

    VocabManifold owns points only and does not build transition operators.
    """
    vocab = VocabManifold()
    vocab.add("logos", _positive_unit_reflector(1))
    vocab.add("arche", _positive_unit_reflector(2))
    vocab.add("pneuma", _positive_unit_reflector(3))
    vocab.add("truth", _positive_unit_reflector(4))
    return vocab


def test_minimum_engine_loop_is_deterministic_and_stores_generated_state() -> None:
    vocab = _minimal_vocab()
    persona = PersonaMotor.identity()
    tokens = ["logos", "arche"]

    initial = inject(tokens, vocab)
    assert versor_condition(initial.F) < 1e-5

    result = generate(initial, vocab, persona, max_tokens=3)
    assert isinstance(result, GenerationResult)
    assert isinstance(result.tokens, tuple)
    assert result.tokens
    assert result.final_state.step == initial.step + 3
    assert not np.array_equal(result.final_state.F, initial.F)

    repeated = generate(inject(tokens, vocab), vocab, persona, max_tokens=3)
    assert repeated.tokens == result.tokens
    np.testing.assert_array_equal(repeated.final_state.F, result.final_state.F)

    vault = VaultStore()
    stored_idx = vault.store(result.final_state.F, metadata={"role": "assistant"})
    assert stored_idx == 0

    recalled = vault.recall(result.final_state.F, top_k=1)
    assert recalled[0]["metadata"]["role"] == "assistant"
    assert recalled[0]["index"] == stored_idx
    np.testing.assert_allclose(recalled[0]["versor"], result.final_state.F)
    assert not np.array_equal(recalled[0]["versor"], initial.F)


def test_session_context_respond_preserves_and_vaults_final_state() -> None:
    session = SessionContext(vocab=_minimal_vocab())
    initial = session.ingest(["logos", "arche"])

    result = session.respond(max_tokens=3)

    assert isinstance(result, GenerationResult)
    assert session.state is result.final_state
    assert not np.array_equal(result.final_state.F, initial.F)

    recalled = session.vault.recall(result.final_state.F, top_k=2)
    assistant_hits = [
        item for item in recalled
        if item["metadata"].get("role") == "assistant"
    ]
    assert assistant_hits, "Assistant final_state was not present in session vault recall."
    np.testing.assert_allclose(assistant_hits[0]["versor"], result.final_state.F)
    assert not np.array_equal(assistant_hits[0]["versor"], initial.F)


def test_hot_path_modules_route_through_backend_boundary() -> None:
    """
    Production hot paths must route through algebra.backend for dispatch.

    Direct algebra.cga/algebra.versor imports here would bypass Rust/Rayon when
    available and violate the acceleration boundary established by Commit 2.
    """
    checked = {
        "field/propagate.py": {
            "required": {("algebra.backend", "versor_apply")},
            "forbidden_modules": {"algebra.versor", ".versor"},
        },
        "vocab/manifold.py": {
            "required": {("algebra.backend", "cga_inner")},
            "forbidden_modules": {"algebra.cga", ".cga"},
        },
        "vault/store.py": {
            "required": {("algebra.backend", "vault_recall")},
            "forbidden_modules": set(),  # null_project may remain on algebra.cga.
        },
    }

    for rel, rule in checked.items():
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)
        imports: set[tuple[str, str]] = set()
        forbidden_hits: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in rule["forbidden_modules"]:
                    forbidden_hits.append(f"{rel}:{node.lineno}:{module}")
                for alias in node.names:
                    imports.add((module, alias.name))

        missing = rule["required"] - imports
        assert not missing, f"{rel} missing backend imports: {sorted(missing)}"
        assert not forbidden_hits, "Forbidden hot-path imports:\n" + "\n".join(forbidden_hits)
