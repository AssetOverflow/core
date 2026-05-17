"""ADR-0020 parity gate — versor_condition Python ⇔ Rust.

`versor_condition(F)` returns the field's deviation from unit-versor
closure — the non-negotiable invariant CLAUDE.md gates on
(< 1e-6).  Both the Python `algebra.versor.versor_condition` and the
Rust `versor_condition_raw` compose geometric_product + reverse +
grade-0 extraction and reduce to a single float.  This test asserts
bit-identity (raw f32 bytes equality) under `CORE_BACKEND=rust` vs
the Python default.

Coverage:
  - normalized versors from deterministic seeds (the runtime hot path)
  - raw fields before closure (catches divergence on out-of-shell input)
  - identity element (scalar 1.0) — must return 0.0 on both sides

If this gate fails, the field invariant itself is at risk under
Rust — the Rust path must be fixed, not the test.  Python is the
canonical closure check per CLAUDE.md sequencing rule 5.

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
from algebra.backend import using_rust, versor_condition
from algebra.versor import normalize_to_versor

mode = os.environ["FIXTURE_MODE"]
if mode == "normalized":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    seed_v = rng.standard_normal(32).astype(np.float32)
    v = normalize_to_versor(seed_v).astype(np.float32)
elif mode == "raw":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    v = rng.standard_normal(32).astype(np.float32)
elif mode == "scalar_one":
    v = np.zeros(32, dtype=np.float32); v[0] = 1.0
else:
    raise SystemExit(f"unknown mode {mode!r}")

cond = versor_condition(v)
print(json.dumps({
    "using_rust": using_rust(),
    "cond_hex": np.float32(cond).tobytes().hex(),
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
    assert py["using_rust"] is False
    assert rs["using_rust"] is True
    assert py["cond_hex"] == rs["cond_hex"], (
        f"versor_condition divergence: python={py['cond_hex']} rust={rs['cond_hex']}"
    )


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234, 0xFACE, 0xDEAD])
def test_versor_condition_normalized_bit_identity(seed: int) -> None:
    """The runtime hot path — normalized versors fed into the closure check."""
    py = _run_backend("python", FIXTURE_MODE="normalized", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="normalized", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234])
def test_versor_condition_raw_field_bit_identity(seed: int) -> None:
    """Out-of-shell input — divergence here would mean different closure math."""
    py = _run_backend("python", FIXTURE_MODE="raw", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="raw", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
def test_versor_condition_scalar_one_bit_identity() -> None:
    """The identity element must be at zero condition on both sides."""
    py = _run_backend("python", FIXTURE_MODE="scalar_one")
    rs = _run_backend("rust", FIXTURE_MODE="scalar_one")
    _assert_bit_identity(py, rs)
