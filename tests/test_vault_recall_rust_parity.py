"""ADR-0020 first-surface parity gate — vault_recall Python ⇔ Rust.

The Rust backend (`CORE_BACKEND=rust`) must produce bit-identical
results to the Python vectorised path on the same input.  This
test runs the same fixture under both backends in subprocesses
(so the backend env var is honoured at module import) and
asserts:

  - per-versor scores are exactly equal (float32 bit-identity)
  - top-k ordering matches, including ascending-index tie-break

If this test ever fails, the Rust path has diverged from the
Python source-of-truth path.  Fix the Rust kernel, not the test.
The Python path is the canonical implementation per CLAUDE.md
sequencing rule 5.

Test is skipped at collection time if the `core_rs` extension is
not importable.
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
from algebra.backend import using_rust, vault_recall

rng = np.random.default_rng(int(os.environ["FIXTURE_SEED"]))
n = int(os.environ["FIXTURE_N"])
top_k = int(os.environ["FIXTURE_TOPK"])
versors = [rng.standard_normal(32).astype(np.float32) for _ in range(n)]
q = rng.standard_normal(32).astype(np.float32)
result = vault_recall(versors, q, top_k=top_k)

# Encode scores as raw float32 bytes (hex) to preserve bit-identity
# through JSON.
encoded = [(i, np.float32(s).tobytes().hex()) for i, s in result]
print(json.dumps({"using_rust": using_rust(), "result": encoded}))
"""


def _run_backend(backend: str, seed: int, n: int, top_k: int) -> dict:
    env = os.environ.copy()
    if backend == "rust":
        env["CORE_BACKEND"] = "rust"
    else:
        env.pop("CORE_BACKEND", None)
    env["FIXTURE_SEED"] = str(seed)
    env["FIXTURE_N"] = str(n)
    env["FIXTURE_TOPK"] = str(top_k)
    script = SCRIPT.replace("__REPO__", str(REPO))
    out = subprocess.check_output(
        [sys.executable, "-c", script],
        env=env,
        cwd=str(REPO),
        text=True,
    )
    return json.loads(out.strip().splitlines()[-1])


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="core_rs extension not built")
@pytest.mark.parametrize("seed,n,top_k", [
    (0xC07E, 200, 200),
    (0xBEEF, 137, 50),
    (0x1234, 500, 10),
    (0xFACE, 50, 5),
])
def test_vault_recall_python_rust_bit_identity(seed: int, n: int, top_k: int) -> None:
    py = _run_backend("python", seed, n, top_k)
    rs = _run_backend("rust", seed, n, top_k)

    assert py["using_rust"] is False, "Python subprocess should not load Rust backend"
    assert rs["using_rust"] is True, "Rust subprocess should load Rust backend"

    assert len(py["result"]) == len(rs["result"]) == min(top_k, n)

    # Bit-identity on scores (hex-encoded f32 bytes) and ordering on
    # indices (including ascending-index tie-break).
    for (py_i, py_hex), (rs_i, rs_hex) in zip(py["result"], rs["result"]):
        assert py_i == rs_i, f"top-k order divergence: python={py_i} rust={rs_i}"
        assert py_hex == rs_hex, (
            f"score bit-identity broken at index {py_i}: "
            f"python={py_hex} rust={rs_hex}"
        )
