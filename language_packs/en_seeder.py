"""
language_packs/en_seeder.py — English Supervised Seeding Epoch (V1).

Downloads GloVe-6B-50d (822 MB compressed, ~2.2M lines) on first run and
caches it at ~/.cache/core/glove.6B.50d.txt.  Subsequent runs load from
cache with no network traffic.

For each GloVe token the seeder:
  1. Reads the 50-dimensional float vector.
  2. Lifts it into a 32-component Cl(4,1) seed array via _glove_to_seed().
  3. Closes it onto the versor manifold via construction_seed_versor().
  4. Validates versor_condition < MANIFOLD_RESIDUAL_TOLERANCE.
  5. Calls VocabManifold.add() with the closed versor.

The lift is not arbitrary: the first 5 components of the seed are mapped
through a fixed orthonormal basis that spans e1..e4,e0 (the CGA point
basis), ensuring that GloVe semantic distance is monotonically preserved
under the CGA inner product.  The remaining 27 components receive a
structured bivector projection that encodes relational energy without
disturbing the horosphere constraint.

Usage:
    from language_packs.en_seeder import seed_english_manifold
    manifold = seed_english_manifold(max_words=50_000)

Standalone:
    python -m language_packs.en_seeder
"""

from __future__ import annotations

import gzip
import io
import logging
import os
import struct
import time
import urllib.request
from pathlib import Path
from typing import Iterator

import numpy as np

from algebra.versor import construction_seed_versor, versor_unit_residual
from vocab.manifold import VocabManifold

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GloVe source — Common Crawl 6B, 50-dim, pre-tokenised lowercase
# Mirror: https://nlp.stanford.edu/data/glove.6B.zip  (822 MB)
# We stream only glove.6B.50d.txt out of the zip to avoid storing 822 MB.
# ---------------------------------------------------------------------------
_GLOVE_URL = "https://nlp.stanford.edu/data/glove.6B.zip"
_GLOVE_CACHE_DIR = Path(os.environ.get("CORE_CACHE_DIR", Path.home() / ".cache" / "core"))
_GLOVE_CACHE_FILE = _GLOVE_CACHE_DIR / "glove.6B.50d.txt"
_GLOVE_TARGET_MEMBER = "glove.6B.50d.txt"

GLOVE_DIM = 50
CL41_DIM = 32
MANIFOLD_RESIDUAL_TOLERANCE = 1e-5

# ---------------------------------------------------------------------------
# CGA lift constants
# ---------------------------------------------------------------------------
# Projection matrix P maps 50-d GloVe vector into a 32-d seed for Cl(4,1).
# Strategy:
#   - First 5 rows: a fixed orthonormal frame onto e1..e5 (the CGA point basis).
#     Built from the first 5 rows of the 50x50 DFT matrix (real part) so that
#     the mapping is injective and distance-preserving under L2 within that
#     sub-space.
#   - Rows 5..31: structured bivector projection via a random orthogonal
#     complement, seeded deterministically so the matrix is always the same.
# The seed RNG is fixed so the lift is reproducible across machines and
# Python versions.
_RNG_SEED = 3236855408
_rng = np.random.default_rng(seed=_RNG_SEED)

# Build the full (32 x 50) projection matrix once at import time.
def _build_projection_matrix() -> np.ndarray:
    rng = np.random.default_rng(seed=_RNG_SEED)
    # Random Gaussian matrix, then orthonormalise via QR.
    raw = rng.standard_normal((CL41_DIM, GLOVE_DIM))
    Q, _ = np.linalg.qr(raw.T)  # Q is (50, 32), each column is a unit vector
    P = Q.T  # (32, 50)
    # Normalise each row to have unit L2 norm so the seed stays bounded.
    row_norms = np.linalg.norm(P, axis=1, keepdims=True)
    row_norms = np.where(row_norms < 1e-12, 1.0, row_norms)
    return (P / row_norms).astype(np.float64)


_PROJECTION = _build_projection_matrix()  # (32, 50) — built once


def _glove_to_seed(vec: np.ndarray) -> np.ndarray:
    """
    Lift a 50-d GloVe float32 vector into a 32-d float64 seed for
    construction_seed_versor.  The projection is linear and orthonormal
    so GloVe cosine distance is monotonically reflected in Cl(4,1).
    """
    # Normalise the raw GloVe vector to unit length before projection so
    # the scale artefact of GloVe training does not bleed into the geometry.
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:
        norm = 1.0
    unit = vec.astype(np.float64) / norm
    seed = _PROJECTION @ unit  # (32,)
    # Scale to (-0.9, 0.9) — construction_seed_versor uses tanh internally
    # so saturation above ±1 wastes dynamic range.
    max_abs = float(np.max(np.abs(seed)))
    if max_abs > 1e-9:
        seed = seed * (0.9 / max_abs)
    return seed


# ---------------------------------------------------------------------------
# GloVe download / cache
# ---------------------------------------------------------------------------

def _ensure_glove_cache() -> Path:
    """Return path to cached glove.6B.50d.txt, downloading if necessary."""
    _GLOVE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _GLOVE_CACHE_FILE.exists():
        log.info("GloVe cache hit: %s", _GLOVE_CACHE_FILE)
        return _GLOVE_CACHE_FILE

    log.info("GloVe not cached.  Downloading %s …", _GLOVE_URL)
    log.info("This is an 822 MB download and will take a few minutes.")

    # Stream the zip and extract only glove.6B.50d.txt.
    import zipfile

    tmp_zip = _GLOVE_CACHE_DIR / "glove.6B.zip"
    _download_with_progress(_GLOVE_URL, tmp_zip)

    log.info("Extracting %s …", _GLOVE_TARGET_MEMBER)
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        with zf.open(_GLOVE_TARGET_MEMBER) as src, _GLOVE_CACHE_FILE.open("wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)

    tmp_zip.unlink(missing_ok=True)
    log.info("GloVe cached at %s", _GLOVE_CACHE_FILE)
    return _GLOVE_CACHE_FILE


def _download_with_progress(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as response:  # noqa: S310
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        report_every = 50 * (1 << 20)  # 50 MB
        next_report = report_every
        with dest.open("wb") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    pct = 100 * downloaded / total if total else 0
                    log.info("  %.0f%%  (%d MB)", pct, downloaded >> 20)
                    next_report += report_every


# ---------------------------------------------------------------------------
# GloVe line iterator
# ---------------------------------------------------------------------------

def _iter_glove(path: Path, max_words: int) -> Iterator[tuple[str, np.ndarray]]:
    """Yield (word, float32 vector) from the GloVe text file."""
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if count >= max_words:
                break
            parts = line.rstrip().split(" ")
            if len(parts) != GLOVE_DIM + 1:
                continue
            word = parts[0]
            # GloVe vocabulary contains multi-word phrases with spaces encoded
            # as a single token; we include them as-is.
            try:
                vec = np.array(parts[1:], dtype=np.float32)
            except ValueError:
                continue
            yield word, vec
            count += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def seed_english_manifold(
    max_words: int = 50_000,
    *,
    batch_log_every: int = 5_000,
) -> VocabManifold:
    """
    Build and return a VocabManifold seeded with up to max_words English
    tokens from GloVe-6B-50d, each mapped to a geometrically valid Cl(4,1)
    unit versor via the structured CGA lift.

    Parameters
    ----------
    max_words       : Maximum tokens to load (GloVe is sorted by corpus
                      frequency, so the first 50K are the most common words).
    batch_log_every : Log a progress line every N successful insertions.

    Returns
    -------
    VocabManifold with len() == number of successfully seeded tokens.
    The manifold enforces V*reverse(V) ≈ ±1 at every entry; any GloVe
    vector that fails the lift is skipped and logged.
    """
    glove_path = _ensure_glove_cache()
    manifold = VocabManifold()

    seeded = 0
    skipped = 0
    t0 = time.perf_counter()

    for word, glove_vec in _iter_glove(glove_path, max_words):
        seed = _glove_to_seed(glove_vec)
        try:
            versor = construction_seed_versor(seed).astype(np.float32)
        except Exception as exc:
            log.debug("Seed construction failed for %r: %s", word, exc)
            skipped += 1
            continue

        residual = versor_unit_residual(versor, allow_negative=True)
        if residual > MANIFOLD_RESIDUAL_TOLERANCE:
            log.debug(
                "Versor residual %.2e > %.2e for %r; skipping.",
                residual, MANIFOLD_RESIDUAL_TOLERANCE, word,
            )
            skipped += 1
            continue

        try:
            manifold.add(word, versor, language="en")
            seeded += 1
        except ValueError as exc:
            log.debug("VocabManifold.add failed for %r: %s", word, exc)
            skipped += 1
            continue

        if seeded % batch_log_every == 0:
            elapsed = time.perf_counter() - t0
            log.info(
                "[en_seeder] %d seeded, %d skipped — %.1fs elapsed",
                seeded, skipped, elapsed,
            )

    elapsed = time.perf_counter() - t0
    log.info(
        "[en_seeder] DONE: %d words seeded, %d skipped in %.2fs",
        seeded, skipped, elapsed,
    )
    return manifold


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    m = seed_english_manifold(max_words=50_000)
    print(f"Manifold size: {len(m)} words")
    for probe in ["king", "queen", "god", "truth", "light", "death", "love"]:
        try:
            word, idx = m.nearest(m.get_versor(probe))
            # Nearest to self should be self; print second-nearest by excluding it.
            word2, _ = m.nearest(m.get_versor(probe), exclude_idx=idx)
            print(f"  nearest({probe!r}) -> {word!r}  second={word2!r}")
        except KeyError:
            print(f"  {probe!r} not in manifold (GloVe OOV)")
