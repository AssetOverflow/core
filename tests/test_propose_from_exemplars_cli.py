"""ADR-0163 Phase C — propose-from-exemplars CLI tests.

Pins:
- the CLI loads a real Phase B JSONL and produces a pending proposal
- --all produces three pending proposals (one per Phase B corpus)
- proposal_id is deterministic across runs with the same corpus_digest
- the CLI does NOT mutate any corpus, pack, recognizer registry, or
  eval lane file outside the supplied tmp paths
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

import teaching.replay as replay_mod
from teaching.proposals import ProposalLog


_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLARS = _REPO_ROOT / "teaching" / "admissibility_exemplars"
_ACTIVE_CORPUS = (
    _REPO_ROOT / "teaching" / "cognition_chains" / "cognition_chains_v1.jsonl"
)
_GSM8K_TRAIN_REPORT = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"
)


def _stub_capability_axes() -> dict[str, dict[str, int]]:
    return {
        "G1_verb_classes": {"correct": 20, "wrong": 0, "refused": 0},
        "G2_comparatives": {"correct": 29, "wrong": 0, "refused": 0},
        "G3_numerics": {"correct": 20, "wrong": 0, "refused": 6},
        "G4_multi_clause": {"correct": 32, "wrong": 0, "refused": 0},
        "G5_aggregate": {"correct": 20, "wrong": 0, "refused": 0},
        "S1_rate_events": {"correct": 20, "wrong": 0, "refused": 0},
    }


def _stub_gsm8k() -> dict[str, int]:
    return {"correct": 3, "wrong": 0, "refused": 47}


def _stub_cognition() -> dict[str, float]:
    return {
        "intent_accuracy": 1.0,
        "surface_groundedness": 1.0,
        "term_capture_rate": 1.0,
        "versor_closure_rate": 1.0,
    }


@pytest.fixture(autouse=True)
def _stub_eval_lanes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the heavy eval lanes so CLI tests run in milliseconds.

    The CLI invokes :func:`teaching.replay.run_admissibility_replay_gate`
    via the existing :func:`propose_from_candidate` path.  Substituting
    the lane runners at module scope is enough; the gate calls them by
    name (``_run_capability_axes``, ``_run_gsm8k_train_sample``,
    ``_run_cognition_public``).
    """
    replay_mod._BASELINE_CACHE.clear()
    monkeypatch.setattr(replay_mod, "_run_capability_axes", _stub_capability_axes)
    monkeypatch.setattr(replay_mod, "_run_gsm8k_train_sample", _stub_gsm8k)
    monkeypatch.setattr(replay_mod, "_run_cognition_public", _stub_cognition)


# ---------------------------------------------------------------------------
# In-process CLI invocation
# ---------------------------------------------------------------------------


def _invoke_cli(args: list[str]) -> tuple[int, str, str]:
    """Run the CLI in-process by calling ``core.cli.main``.

    Captures argv + stdout/stderr; returns (exit_code, stdout, stderr).
    """
    import io
    import contextlib

    from core import cli as core_cli

    saved_argv = sys.argv
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        sys.argv = ["core", *args]
        with (
            contextlib.redirect_stdout(out_buf),
            contextlib.redirect_stderr(err_buf),
        ):
            try:
                code = core_cli.main()
            except SystemExit as exc:
                code = int(exc.code) if exc.code is not None else 0
    finally:
        sys.argv = saved_argv
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
    return code, out_buf.getvalue(), err_buf.getvalue()


def test_cli_single_corpus_produces_pending_proposal(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    code, out, _ = _invoke_cli([
        "teaching", "propose-from-exemplars",
        str(_EXEMPLARS / "rate_with_currency_v1.jsonl"),
        "--log", str(log_path),
        "--json",
    ])
    assert code == 0, f"CLI exited {code}; stdout={out!r}"
    payload = json.loads(out)
    assert len(payload["proposals"]) == 1
    p = payload["proposals"][0]
    assert p["shape_category"] == "rate_with_currency"
    assert p["state"] == "pending"
    assert p["replay_equivalent"] is True
    assert p["wrong_count_delta"] == 0
    # The proposal exists in the log.
    log = ProposalLog(log_path)
    rec = log.find(p["proposal_id"])
    assert rec is not None
    assert rec["state"] == "pending"
    assert rec["proposal"]["source"]["kind"] == "exemplar_corpus"


def test_cli_all_flag_proposes_all_exemplar_corpora(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    code, out, _ = _invoke_cli([
        "teaching", "propose-from-exemplars",
        "--all",
        "--log", str(log_path),
        "--json",
    ])
    assert code == 0
    payload = json.loads(out)
    cats = {p["shape_category"] for p in payload["proposals"]}
    # --all proposes one pending proposal per exemplar corpus. The set grew
    # from the original three as the ME-1..ME-5 matcher waves added
    # currency_amount, discrete_count_statement, and multiplicative_aggregation
    # exemplar corpora. Update this set when a new exemplar corpus is added.
    assert cats == {
        "currency_amount",
        "descriptive_setup_no_quantity",
        "discrete_count_statement",
        "multiplicative_aggregation",
        "rate_with_currency",
        "temporal_aggregation",
    }
    for p in payload["proposals"]:
        assert p["state"] == "pending"


def test_proposal_id_is_deterministic_for_same_corpus(tmp_path: Path) -> None:
    log_a = tmp_path / "log_a.jsonl"
    log_b = tmp_path / "log_b.jsonl"
    code_a, out_a, _ = _invoke_cli([
        "teaching", "propose-from-exemplars",
        str(_EXEMPLARS / "rate_with_currency_v1.jsonl"),
        "--log", str(log_a),
        "--json",
    ])
    code_b, out_b, _ = _invoke_cli([
        "teaching", "propose-from-exemplars",
        str(_EXEMPLARS / "rate_with_currency_v1.jsonl"),
        "--log", str(log_b),
        "--json",
    ])
    assert code_a == code_b == 0
    pid_a = json.loads(out_a)["proposals"][0]["proposal_id"]
    pid_b = json.loads(out_b)["proposals"][0]["proposal_id"]
    assert pid_a == pid_b


# ---------------------------------------------------------------------------
# Read-only snapshot — the CLI mutates nothing outside the supplied paths
# ---------------------------------------------------------------------------


def _digest(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_paths() -> list[Path]:
    """Files the CLI MUST NOT mutate."""
    out: list[Path] = []
    out.extend(sorted(_EXEMPLARS.glob("*_v1.jsonl")))
    if _ACTIVE_CORPUS.exists():
        out.append(_ACTIVE_CORPUS)
    if _GSM8K_TRAIN_REPORT.exists():
        out.append(_GSM8K_TRAIN_REPORT)
    # Capability axis reports are touched by the runners when run via
    # write_report; the CLI gate calls build_report() directly so
    # report.json must remain byte-identical.
    for report in (_REPO_ROOT / "evals" / "math_capability_axes").rglob("v1/report.json"):
        out.append(report)
    return out


def test_cli_does_not_mutate_input_files(tmp_path: Path) -> None:
    snapshot_before = {p: _digest(p) for p in _snapshot_paths()}
    log_path = tmp_path / "proposals.jsonl"
    code, _, _ = _invoke_cli([
        "teaching", "propose-from-exemplars",
        "--all",
        "--log", str(log_path),
        "--json",
    ])
    assert code == 0
    snapshot_after = {p: _digest(p) for p in _snapshot_paths()}
    for path in snapshot_before:
        assert snapshot_before[path] == snapshot_after[path], (
            f"CLI mutated read-only file: {path}"
        )
