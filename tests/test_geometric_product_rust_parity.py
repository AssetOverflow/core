"""ADR-0020 parity gate — geometric_product Python ⇔ Rust.

The Cl(4,1) geometric product is a deterministic table lookup over
32×32 component pairs.  Both the Python `algebra.cl41.geometric_product`
and the Rust `geometric_product_raw` execute the same f32 multiply-
accumulate sequence in the same component order.  This test asserts
bit-identity (raw f32 bytes equality, per output component) under
`CORE_BACKEND=rust` vs the Python default.

Coverage:
  - random pairs (5 seeds) — broad-spectrum drift catch
  - basis × basis (canonical structural cases) — table-correctness
  - scalar × multivector — identity check
  - pseudoscalar × pseudoscalar — sign convention

If this test fails, the Rust kernel has diverged from Python.
Fix the Rust kernel, not the test.

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
from algebra.backend import using_rust, geometric_product

mode = os.environ["FIXTURE_MODE"]
if mode == "random":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    a = rng.standard_normal(32).astype(np.float32)
    b = rng.standard_normal(32).astype(np.float32)
elif mode == "basis":
    i = int(os.environ["FIXTURE_I"])
    j = int(os.environ["FIXTURE_J"])
    a = np.zeros(32, dtype=np.float32); a[i] = 1.0
    b = np.zeros(32, dtype=np.float32); b[j] = 1.0
elif mode == "scalar_identity":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    a = np.zeros(32, dtype=np.float32); a[0] = 1.0
    b = rng.standard_normal(32).astype(np.float32)
else:
    raise SystemExit(f"unknown mode {mode!r}")

out = np.asarray(geometric_product(a, b), dtype=np.float32)
# Hex-encode each f32 component to preserve bit-identity through JSON.
encoded = [np.float32(v).tobytes().hex() for v in out]
print(json.dumps({"using_rust": using_rust(), "result": encoded}))
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
    assert py["using_rust"] is False
    assert rs["using_rust"] is True
    assert len(py["result"]) == len(rs["result"]) == 32
    for k, (p, r) in enumerate(zip(py["result"], rs["result"])):
        assert p == r, f"geometric_product divergence at component {k}: python={p} rust={r}"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234, 0xFACE, 0xDEAD])
def test_geometric_product_random_bit_identity(seed: int) -> None:
    py = _run_backend("python", FIXTURE_MODE="random", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="random", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("i,j", [
    (0, 0),    # 1·1
    (0, 31),   # 1·I
    (31, 31),  # I·I (sign convention check)
    (1, 2),    # e1·e2
    (2, 1),    # e2·e1 (anticommutation)
    (5, 5),    # e+ self
    (1, 1),    # e1 self
    (15, 16),  # arbitrary mid-grade pair
])
def test_geometric_product_basis_blade_bit_identity(i: int, j: int) -> None:
    py = _run_backend("python", FIXTURE_MODE="basis", FIXTURE_I=str(i), FIXTURE_J=str(j))
    rs = _run_backend("rust", FIXTURE_MODE="basis", FIXTURE_I=str(i), FIXTURE_J=str(j))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF])
def test_geometric_product_scalar_identity_bit_identity(seed: int) -> None:
    """1 · b == b — both backends must preserve the scalar identity bit-for-bit."""
    py = _run_backend("python", FIXTURE_MODE="scalar_identity", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="scalar_identity", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)
