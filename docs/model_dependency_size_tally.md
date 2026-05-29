# Model & Dependency Size Tally

A running ledger of how big CORE's model/architecture and its dependency
footprint get. The headline metric is **learned parameters** — CORE's thesis is a
deterministic, algebra-based engine, so this number should stay **0** for the
substrate, forever. Everything else here is secondary footprint.

**Update this doc in the same PR** whenever you: add/remove a runtime dependency,
wire a learned model (teacher/shadow lane), change a model size, or add weight
files. Append a dated line to the [Changelog](#changelog).

---

## Tally summary (headline)

| Metric | Value | Trend |
|---|---|---|
| **CORE substrate learned parameters** | **0** | flat (by design — must stay 0) |
| **Model weights on disk (committed or required)** | **0 bytes** | flat |
| **Learned models wired (runtime)** | **0** | — |
| **Learned models declared but inert (optional, gated)** | 4 (whisper, nemo, clap, encodec) | — |
| Python runtime dependencies | 10 | see §3 |
| Rust crate dependencies | 8 | see §4 |

> **The number that matters:** CORE is a **0-parameter architecture**. The
> reasoning substrate is geometric algebra (Cl(4,1) versors + deterministic
> operators), not weights. The versor-invariance test
> (`tests/test_audio_teachers.py::test_teacher_hint_does_not_change_versor`)
> structurally guarantees that even when a teacher model is wired, it **cannot
> fold into the substrate** — so this stays 0 regardless of teachers.

---

## 1. CORE architecture — learned parameters

| Component | Learned params | Weights | Notes |
|---|---|---|---|
| Algebra / versor engine (`algebra/`, `core-rs/`) | 0 | 0 | pure Cl(4,1) math |
| Field / propagation / vault (`field/`, `vault/`) | 0 | 0 | exact CGA recall, no ANN/embeddings |
| Language packs (`language_packs/`, `packs/`) | 0 | 0 | curated symbolic data, not trained |
| Audio compiler substrate (`sensorium/audio/`) | 0 | 0 | DSP + frozen operator rotor table |
| Generation / comprehension (`generate/`) | 0 | 0 | deterministic |
| **Total** | **0** | **0** | — |

**Principle:** capability comes from strengthening the deterministic path, not
from adding parameters. If a "learned weights" line ever appears in this table,
it is a doctrinal change and belongs in an ADR, not a quiet dependency bump.

---

## 2. Optional learned models (teacher / shadow lanes)

These are **bolt-on evidence lanes**, never the substrate (ADR-0181 §2, eval-plan
§4). They are *declared and gated* behind optional extras; **none is currently
wired** (`load_teacher(...)` raises `TeacherUnavailable`, no weights downloaded).
Track these as a **dependency footprint**, separate from the architecture tally
above — they are removable and never part of the engine's reasoning.

| Lane | Status | Extra | Model selected | Params / disk |
|---|---|---|---|---|
| Whisper | declared, **inert** | `audio-whisper` | **none chosen** | 0 (not installed) |
| NeMo (Parakeet/Canary) | declared, **inert** | `audio-nemo` | none | 0 |
| CLAP | declared, **inert** | `audio-clap` | none | 0 |
| EnCodec | declared, **inert** | `audio-encodec` | none | 0 |

### Whisper size reference (for when/if it is wired)

Only declare a size here once an adapter is actually wired and the size is pinned
in the audio pack manifest (with checksum). Pick the smallest size that clears
the transcript-evidence bar — teachers produce *labels*, not comprehension.

| Model | Params | ~Disk | Notes |
|---|---|---|---|
| `tiny(.en)` | 39M | ~75 MB | fastest, CPU-friendly, weakest |
| `base(.en)` | 74M | ~145 MB | likely sweet spot for label-only use |
| `small(.en)` | 244M | ~0.5 GB | |
| `medium(.en)` | 769M | ~1.5 GB | |
| `large-v3` | 1550M | ~3 GB | best, heaviest |

> When a lane goes live: change its **Status** to "wired", fill **Model
> selected** + **Params / disk**, bump the §0 summary counts, and log it in the
> Changelog with the pinned size + manifest checksum.

---

## 3. Python runtime dependencies

From `pyproject.toml` `[project].dependencies`. Disk sizes are **approximate
installed footprints** (order-of-magnitude); the exact, auditable number is the
learned-params tally above. Measure precisely with
`du -sh .venv/lib/python*/site-packages/<pkg>` if needed.

| Package | Pin | Purpose | ~Installed |
|---|---|---|---|
| `numpy` | >=1.26 | core array math | ~30–40 MB |
| `datasets` | >=4.8.5 | GSM8K eval corpus loading (pulls pyarrow/pandas) | **~300–500 MB** (heaviest) |
| `ruff` | >=0.15.12 | lint/format (Rust binary) | ~25–40 MB |
| `pytest` | >=9.0.3 | test runner | ~5 MB |
| `pytest-asyncio` | >=1.3.0 | async tests | <1 MB |
| `pytest-xdist` | >=3.6 | parallel tests | <1 MB |
| `hypothesis` | >=6.152.7 | property tests | ~5 MB |
| `psutil` | >=7.0 | process/resource probing | ~2 MB |
| `pyrage` | ==1.2.3 | age encryption (Rust binding) | ~3 MB |
| `pyyaml` | >=6.0 | config/manifest parsing | ~1 MB |

> **Footprint note:** `datasets` dominates the Python install. If the GSM8K
> loading path is ever isolated behind an extra, the base runtime footprint drops
> sharply. None of these carry learned weights.

---

## 4. Rust crate dependencies

From `core-rs/Cargo.toml`. Compiled into the `core_rs` extension; contribute to
binary size, not learned params.

| Crate | Version | Purpose |
|---|---|---|
| `pyo3` | 0.21 | Python↔Rust bindings |
| `numpy` | 0.21 | zero-copy numpy views |
| `rayon` | 1.10 | data-parallel scoring |
| `nalgebra` | 0.33 | linear algebra |
| `ndarray` | 0.16 | n-d arrays (diffusion) |
| `ndarray-rand` | 0.15 | rng for arrays |
| `bytemuck` | 1.16 | zero-copy slice casts |
| `thiserror` | 1.0 | error types |

---

## 5. Model weights on disk

| Path | Type | Size |
|---|---|---|
| — | — | **none** |

No `.pt` / `.safetensors` / `.onnx` / `.gguf` / `.ckpt` / `.bin` weight files are
committed or required. (Verify: `git ls-tree -r --name-only HEAD | grep -iE
'\.(pt|onnx|bin|safetensors|ckpt|gguf|pth)$'` → empty.)

---

## Changelog

Append one dated line per change. Newest first.

- **2026-05-29** — Doc created. Tally baseline: **0 learned params, 0 model
  weights**. 4 teacher lanes (whisper/nemo/clap/encodec) declared but inert
  (ADR-0181 PR-6, merged #479); no model size chosen for any. 10 Python runtime
  deps, 8 Rust crates.
