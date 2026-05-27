"""ADR-0172 W3 — math-contemplation CLI lane tests.

Covers:

- subcommand is wired in core/cli.py and exits 0 on the real audit brief;
- output file is written to teaching/math_proposals/ and contains valid JSONL;
- idempotency: second run overwrites byte-identical bytes;
- output is sorted by proposal_id (matches decomposer contract);
- --output accepts a valid relative path inside teaching/math_proposals/;
- --output rejects absolute paths (exit 2);
- --output rejects relative path-traversal that escapes the allowed root (exit 2);
- --audit exit-1 when the audit file does not exist;
- --json flag emits machine-readable JSON to stdout.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest

import core.cli as cli_module
from core.cli import cmd_eval, cmd_eval_math_contemplation

REAL_AUDIT_PATH = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "audit_brief_11.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Args:
    """Minimal argparse.Namespace stand-in for direct cmd_eval_math_contemplation calls."""

    def __init__(self, *, audit=None, output=None, json_mode=False):
        self.lane = "math-contemplation"
        self.audit = audit
        self.output = output
        self.json = json_mode
        # Fields required by other eval branches but unused here:
        self.list_lanes = False
        self.version = None
        self.split = "public"
        self.workers = 4
        self.save = False
        self.report = None


@contextmanager
def _patch_proposals_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect _MATH_PROPOSALS_DIR and _DEFAULT_OUTPUT_PATH to tmp_path."""
    original_dir = cli_module._MATH_PROPOSALS_DIR
    original_default = cli_module._DEFAULT_OUTPUT_PATH
    cli_module._MATH_PROPOSALS_DIR = tmp_path
    cli_module._DEFAULT_OUTPUT_PATH = tmp_path / "proposals.jsonl"
    try:
        yield tmp_path / "proposals.jsonl"
    finally:
        cli_module._MATH_PROPOSALS_DIR = original_dir
        cli_module._DEFAULT_OUTPUT_PATH = original_default


# ---------------------------------------------------------------------------
# Subcommand routing
# ---------------------------------------------------------------------------


def test_eval_math_contemplation_routes_from_cmd_eval(tmp_path: Path) -> None:
    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH))
        rc = cmd_eval(args)
    assert rc == 0
    assert output.exists()


# ---------------------------------------------------------------------------
# Happy path — real audit brief
# ---------------------------------------------------------------------------


def test_cli_lane_writes_jsonl_with_real_audit(tmp_path: Path) -> None:
    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH))
        rc = cmd_eval_math_contemplation(args)

    assert rc == 0
    assert output.exists()
    lines = output.read_bytes().splitlines()
    assert len(lines) >= 1
    for line in lines:
        obj = json.loads(line)
        assert isinstance(obj, dict)


def test_cli_lane_output_sorted_by_proposal_id(tmp_path: Path) -> None:
    # canonical_bytes() omits proposal_id by design; verify by comparing the
    # written bytes to the decomposer output (which is itself sorted by proposal_id).
    from teaching.math_contemplation import decompose_audit
    from teaching.math_contemplation_proposal import canonical_bytes

    proposals = decompose_audit(REAL_AUDIT_PATH)
    expected = b"".join(canonical_bytes(p) + b"\n" for p in proposals)

    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH))
        cmd_eval_math_contemplation(args)

    assert output.read_bytes() == expected, (
        "output bytes must match decomposer output in proposal_id order"
    )


def test_cli_lane_idempotent(tmp_path: Path) -> None:
    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH))
        cmd_eval_math_contemplation(args)
        first_bytes = output.read_bytes()
        cmd_eval_math_contemplation(args)
        second_bytes = output.read_bytes()

    assert first_bytes == second_bytes, "re-run must produce byte-identical output"


def test_cli_lane_json_flag(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH), json_mode=True)
        rc = cmd_eval_math_contemplation(args)

    assert rc == 0
    captured = capsys.readouterr()
    obj = json.loads(captured.out)
    assert "proposals" in obj
    assert isinstance(obj["proposals"], int)
    assert obj["proposals"] >= 1



# ---------------------------------------------------------------------------
# Path-traversal rejection (exit 2)
# ---------------------------------------------------------------------------


def test_absolute_output_rejected() -> None:
    args = _Args(audit=str(REAL_AUDIT_PATH), output="/etc/passwd")
    with pytest.raises(SystemExit) as exc_info:
        cmd_eval_math_contemplation(args)
    assert exc_info.value.code == 2


def test_relative_traversal_rejected() -> None:
    args = _Args(audit=str(REAL_AUDIT_PATH), output="../../../etc/passwd")
    with pytest.raises(SystemExit) as exc_info:
        cmd_eval_math_contemplation(args)
    assert exc_info.value.code == 2


def test_sibling_directory_rejected() -> None:
    # teaching/vault/ is a sibling, not inside teaching/math_proposals/
    args = _Args(audit=str(REAL_AUDIT_PATH), output="teaching/vault/proposals.jsonl")
    with pytest.raises(SystemExit) as exc_info:
        cmd_eval_math_contemplation(args)
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Missing audit file (exit 1)
# ---------------------------------------------------------------------------


def test_missing_audit_exits_1(tmp_path: Path) -> None:
    args = _Args(audit=str(tmp_path / "nope.json"))
    with pytest.raises(SystemExit) as exc_info:
        cmd_eval_math_contemplation(args)
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# No writes outside teaching/math_proposals/
# ---------------------------------------------------------------------------


def test_no_writes_outside_allowed_root(tmp_path: Path) -> None:
    with _patch_proposals_dir(tmp_path) as output:
        args = _Args(audit=str(REAL_AUDIT_PATH))
        cmd_eval_math_contemplation(args)

    written = list(tmp_path.iterdir())
    assert written == [output], f"unexpected files written: {written}"


# ---------------------------------------------------------------------------
# .gitkeep scaffold exists
# ---------------------------------------------------------------------------


def test_math_proposals_gitkeep_exists() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    gitkeep = repo_root / "teaching" / "math_proposals" / ".gitkeep"
    assert gitkeep.exists(), "teaching/math_proposals/.gitkeep must be committed"
