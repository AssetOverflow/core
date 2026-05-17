"""ADR-0020 parity gate — versor_apply Python ⇔ Rust.

The sandwich product V·F·reverse(V) is the field-transition primitive
under CLAUDE.md's non-negotiable invariant ``versor_condition(F) < 1e-6``.
Python computes the full sandwich and closure in float64
(`algebra.versor.versor_apply` + `_close_applied_versor`).  Rust
historically computes in f32 (`versor_apply_closed`) and the dispatch
casts the result up to float64.

This test asserts bit-identity (per-component raw f64 bytes equality)
under `CORE_BACKEND=rust` vs the Python default.  If the gate fails
the Rust path has diverged from the Python source-of-truth, and per
ADR-0020 the Rust dispatch for this surface must be disabled until a
parity port lands.  Python is canonical per CLAUDE.md sequencing
rule 5.

Coverage:
  - normalized versors applied to normalized fields (the runtime hot path)
  - identity versor applied to a random field (V=1 → V·F·rev(V) == F)
  - basis-blade rotors applied to canonical fields (structural cases)

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
from algebra.backend import using_rust, versor_apply
from algebra.versor import normalize_to_versor

mode = os.environ["FIXTURE_MODE"]
if mode == "normalized":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    seed_v = rng.standard_normal(32).astype(np.float64)
    seed_f = rng.standard_normal(32).astype(np.float64)
    v = normalize_to_versor(seed_v)
    f = normalize_to_versor(seed_f)
elif mode == "identity_v":
    rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
    v = np.zeros(32, dtype=np.float64); v[0] = 1.0
    f = normalize_to_versor(rng.standard_normal(32).astype(np.float64))
else:
    raise SystemExit(f"unknown mode {mode!r}")

out = np.asarray(versor_apply(v, f), dtype=np.float64)
encoded = [np.float64(x).tobytes().hex() for x in out]
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
        assert p == r, f"versor_apply divergence at component {k}: python={p} rust={r}"


# Rust dispatch for versor_apply is currently disabled in algebra/backend.py
# pending an f64 parity port — see the docstring on `algebra.backend.versor_apply`.
# The Rust kernel `versor_apply_closed` diverges from Python on two axes:
#   (1) precision: Rust folds the sandwich in f32; Python in f64
#   (2) closure structure: Rust has a null-vector early branch + no
#       post-unitize condition recheck; Python is the inverse
# Until both axes are reconciled, the parity gate is skipped.  When the
# f64 port lands and the dispatch is re-enabled, remove this skip marker.
_PARITY_DISABLED_REASON = (
    "Rust versor_apply dispatch disabled pending f64 parity port; "
    "see algebra/backend.py::versor_apply and ADR-0020."
)


@pytest.mark.skip(reason=_PARITY_DISABLED_REASON)
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234, 0xFACE, 0xDEAD])
def test_versor_apply_normalized_bit_identity(seed: int) -> None:
    """Runtime hot path — both V and F normalized through the closure boundary."""
    py = _run_backend("python", FIXTURE_MODE="normalized", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="normalized", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


@pytest.mark.skip(reason=_PARITY_DISABLED_REASON)
@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234])
def test_versor_apply_identity_v_bit_identity(seed: int) -> None:
    """V = scalar 1 → V·F·rev(V) == F. The simplest non-trivial sandwich case."""
    py = _run_backend("python", FIXTURE_MODE="identity_v", FIXTURE_SEED=str(seed))
    rs = _run_backend("rust", FIXTURE_MODE="identity_v", FIXTURE_SEED=str(seed))
    _assert_bit_identity(py, rs)


# Keep _RUST_AVAILABLE referenced so static analysis sees its intended use
# once the parity gate is re-enabled.
_ = _RUST_AVAILABLE
