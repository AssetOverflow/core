"""Vault P2 — exact-CGA recall evidence (read-only).

The recall endpoint proves a persisted vault entry is recallable by CORE's
*actual* exact CGA machinery: it rehydrates the persisted ``VaultStore``
(bit-exact versors, no reprojection) and runs the real ``VaultStore.recall``
using the entry's own stored versor as the query. These tests fail under the
specific violations the surface must never commit:

- claiming evidence when no persisted snapshot exists (must 501);
- accepting a caller-controlled index out of range / non-integer (must 404);
- losing the self-recall proof (the entry must recall itself);
- leaking ``recall``'s ``+inf`` self-match sentinel into the JSON (the score
  must be the genuine finite ``cga_inner``);
- mutating the persisted file (the surface is read-only);
- non-determinism across identical reads.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore
from workbench import readers
from workbench.api import WorkbenchApi
from workbench.schemas import to_data


def _build_vault(n: int = 3) -> VaultStore:
    """A real vault of ``n`` distinct 32-dim (Cl(4,1)) versors."""
    store = VaultStore(reproject_interval=0)
    for i in range(n):
        f = np.zeros(32, dtype=np.float32)
        f[0] = 1.0
        f[i + 1] = 0.25 * (i + 1)
        store.store(f, {"turn": i, "role": "assistant"}, epistemic_status=EpistemicStatus.COHERENT)
    return store


def _persist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, store: VaultStore | None) -> Path:
    engine_state = tmp_path / "engine_state"
    engine_state.mkdir(exist_ok=True)
    path = engine_state / "session_state.json"
    if store is not None:
        path.write_text(json.dumps({"vault": store.to_dict()}, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", engine_state)
    return path


def test_absent_snapshot_is_evidence_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _persist(tmp_path, monkeypatch, store=None)  # no file written
    with pytest.raises(readers.EvidenceUnavailableError):
        readers.vault_entry_recall(0)


@pytest.mark.parametrize("bad_index", [99, -1])
def test_out_of_range_index_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_index: int
) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(3))
    with pytest.raises(FileNotFoundError):
        readers.vault_entry_recall(bad_index)


def test_entry_recalls_itself_by_exact_byte_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(3))
    result = readers.vault_entry_recall(1)

    assert result.self_hit_found is True
    assert result.self_hit_rank == 0  # exact self-match promoted ahead of metric ranking
    assert result.hits, "recall returned no hits"
    top = result.hits[0]
    assert top.entry_index == 1
    assert top.exact_self_match is True
    # The query digest is the same content-addressed digest the entry carries.
    assert result.query_versor_digest == readers.list_vault_entries()[1].versor_digest
    assert top.versor_digest == result.query_versor_digest


def test_score_is_finite_exact_cga_never_the_inf_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(3))
    result = readers.vault_entry_recall(0)

    for hit in result.hits:
        assert math.isfinite(hit.cga_inner), "recall's +inf self-match sentinel leaked into the score"
    # And the whole payload survives strict JSON (no Infinity / NaN).
    json.dumps(to_data(result), allow_nan=False)


def test_exact_cga_flags_are_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(2))
    result = readers.vault_entry_recall(0)
    assert result.exact_cga is True
    assert result.approximate is False


def test_recall_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(3))
    first = to_data(readers.vault_entry_recall(2))
    second = to_data(readers.vault_entry_recall(2))
    assert first == second


def test_recall_does_not_mutate_the_persisted_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _persist(tmp_path, monkeypatch, _build_vault(3))
    before = path.read_bytes()
    readers.vault_entry_recall(0)
    assert path.read_bytes() == before


def test_api_route_status_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _persist(tmp_path, monkeypatch, _build_vault(2))
    api = WorkbenchApi()

    ok = api.handle("GET", "/vault/entries/0/recall")
    assert ok.status == 200
    assert ok.payload["ok"] is True
    assert ok.payload["data"]["exact_cga"] is True
    assert ok.payload["data"]["approximate"] is False
    assert ok.payload["data"]["self_hit_found"] is True

    assert api.handle("GET", "/vault/entries/99/recall").status == 404
    assert api.handle("GET", "/vault/entries/not-an-int/recall").status == 404


def test_api_route_absent_snapshot_is_501(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", tmp_path / "engine_state")
    api = WorkbenchApi()
    response = api.handle("GET", "/vault/entries/0/recall")
    assert response.status == 501
    assert response.payload["error"]["code"] == "evidence_unavailable"
