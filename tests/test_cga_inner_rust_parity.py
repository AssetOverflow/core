"""ADR-0020 parity gate — cga_inner Python ⇔ Rust.

The CGA inner product is a diagonal weighted dot product on Cl(4,1)
basis blades; both the Python `algebra.cga.cga_inner` and the Rust
`cga_inner_raw` execute the same serial fold over 32 components.
This test asserts bit-identity (raw f32 bytes equality) under
`CORE_BACKEND=rust` vs the Python default, across deterministic
seeds plus structured edge cases (basis blades, scalar, pseudoscalar).

If this test ever fails, the Rust kernel has diverged from the
Python source-of-truth.  Fix the Rust kernel, not the test.
Python is canonical per CLAUDE.md sequencing rule 5.

Test is skipped at collection time if `core_rs` is not importable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

try:
    import core_rs  # noqa: F401

    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False


SCRIPT = r"""
import json, os, sys
import numpy as np
sys.path.insert(0, "__REPO__")
from algebra.backend import using_rust, cga_inner

mode = os.environ["FIXTURE_MODE"]
if mode == "random":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    x = rng.standard_normal(32).astype(np.float32)
    y = rng.standard_normal(32).astype(np.float32)
elif mode == "basis":
    i = int(os.environ["FIXTURE_I"])
    j = int(os.environ["FIXTURE_J"])
    x = np.zeros(32, dtype=np.float32); x[i] = 1.0
    y = np.zeros(32, dtype=np.float32); y[j] = 1.0
elif mode == "self":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    x = rng.standard_normal(32).astype(np.float32)
    y = x
else:
    raise SystemExit(f"unknown mode {mode!r}")

score = cga_inner(x, y)
print(json.dumps({
    "using_rust": using_rust(),
    "score_hex": np.float32(score).tobytes().hex(),
}))
"""


def _run_backend(backend: str, **env_extra: str) -> dict:
    env = os.environ.copy()
    if backend == "rust":
        env["CORE_BACKEND"] = "rust"
    else:
        env.pop("CORE_BACKEND", None)
    env.update(env_extra)
    script = SCRIPT.replace("__REPO__", str(REPO))
    out = subprocess.check_output(
        [sys.executable, "-c", script],
        env=env,
        cwd=str(REPO),
        text=True,
    )
    return json.loads(out.strip().splitlines()[-1])


def _assert_bit_identity(py: dict, rs: dict) -> None:
    assert py["using_rust"] is False, "Python subprocess should not load Rust backend"
    assert rs["using_rust"] is True, "Rust subprocess should load Rust backend"
    assert py["score_hex"] == rs["score_hex"], (
        f"cga_inner bit-identity broken: python={py['score_hex']} rust={rs['score_hex']}"
    )


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234, 0xFACE, 0xDEAD])
def test_cga_inner_random_bit_identity(seed: int) -> None:
    py = _run_backend("python", FIXTURE_MODE="random", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="random", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("i,j", [
    (0, 0),    # scalar self
    (31, 31),  # pseudoscalar self
    (1, 1),    # e1 e1 — Cl(4,1) signature check
    (5, 5),    # e+ self (positive null-cone direction)
    (1, 2),    # off-diagonal must vanish to exact zero
    (3, 7),    # another off-diagonal
])
def test_cga_inner_basis_blade_bit_identity(i: int, j: int) -> None:
    py = _run_backend("python", FIXTURE_MODE="basis", FIXTURE_I=str(i), FIXTURE_J=str(j))
    rs = _run_backend("rust", FIXTURE_MODE="basis", FIXTURE_I=str(i), FIXTURE_J=str(j))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234])
def test_cga_inner_self_norm_bit_identity(seed: int) -> None:
    """cga_inner(x, x) — self-norm — must match bit-for-bit."""
    py = _run_backend("python", FIXTURE_MODE="self", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="self", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)
