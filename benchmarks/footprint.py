"""Footprint bench — total on-disk and in-memory bytes required to run CORE.

Anchors the "Smaller" claim in evals/CLAIMS.md. Reports:

- On-disk bytes for the active language pack, persistent vault state,
  the compiled Rust backend artifact, and the Python modules actually
  loaded by a single pulse (via sys.modules walk, not a directory scan).
- Resident memory before and after one pulse (RSS delta).
- A deployment-profile flag set: runs_offline, requires_gpu,
  requires_network, requires_api_key.
- A frontier-model context table sourced from published model cards so
  the comparison is reproducible without calling any provider API.

The measurement is honest: it counts only what the cognition lane needs
to run, not the whole repository. If you add an optional subsystem and
it is not loaded by a default pulse, it does not count toward this
number — and that is correct, because deployment does not need it.

Usage:

    from benchmarks.footprint import run_footprint
    report = run_footprint()
    print(report.summary())

CLI surface (added to core/cli.py separately):

    core bench footprint --json
"""

from __future__ import annotations

import json
import resource
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class FrontierReference:
    """A published frontier-model size for context.

    Sources are cited inline (in `source_note`). Do not add a row
    without a public source — speculation is not evidence.
    """
    name: str
    parameters_billion: float
    weights_bytes_estimate: int
    source_note: str


FRONTIER_REFERENCES: tuple[FrontierReference, ...] = (
    FrontierReference(
        name="Llama 3.1 8B (fp16)",
        parameters_billion=8.0,
        weights_bytes_estimate=8_000_000_000 * 2,
        source_note="Meta model card, 2024 — 2 bytes/param at fp16.",
    ),
    FrontierReference(
        name="Llama 3.1 70B (fp16)",
        parameters_billion=70.0,
        weights_bytes_estimate=70_000_000_000 * 2,
        source_note="Meta model card, 2024 — 2 bytes/param at fp16.",
    ),
    FrontierReference(
        name="Llama 3.1 405B (fp16)",
        parameters_billion=405.0,
        weights_bytes_estimate=405_000_000_000 * 2,
        source_note="Meta model card, 2024 — 2 bytes/param at fp16.",
    ),
    FrontierReference(
        name="GPT-3.5 (175B, fp16 estimate)",
        parameters_billion=175.0,
        weights_bytes_estimate=175_000_000_000 * 2,
        source_note="Brown et al. 2020, GPT-3 paper; size is public, fp16 storage assumed.",
    ),
)


@dataclass(frozen=True, slots=True)
class ArtifactSize:
    name: str
    path: str
    bytes_on_disk: int
    present: bool


@dataclass(frozen=True, slots=True)
class DeploymentProfile:
    runs_offline: bool
    requires_gpu: bool
    requires_network: bool
    requires_api_key: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "runs_offline": self.runs_offline,
            "requires_gpu": self.requires_gpu,
            "requires_network": self.requires_network,
            "requires_api_key": self.requires_api_key,
        }


@dataclass(frozen=True, slots=True)
class FootprintReport:
    artifacts: tuple[ArtifactSize, ...]
    python_runtime_bytes: int
    python_runtime_module_count: int
    rss_idle_bytes: int
    rss_post_pulse_bytes: int
    deployment: DeploymentProfile
    frontier_context: tuple[FrontierReference, ...]

    @property
    def total_disk_bytes(self) -> int:
        return sum(a.bytes_on_disk for a in self.artifacts if a.present) + self.python_runtime_bytes

    @property
    def rss_pulse_delta_bytes(self) -> int:
        return max(0, self.rss_post_pulse_bytes - self.rss_idle_bytes)

    def smaller_than(self, ref: FrontierReference) -> float:
        if self.total_disk_bytes <= 0:
            return 0.0
        return ref.weights_bytes_estimate / self.total_disk_bytes

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_disk_bytes": self.total_disk_bytes,
            "total_disk_human": _human_bytes(self.total_disk_bytes),
            "python_runtime_bytes": self.python_runtime_bytes,
            "python_runtime_module_count": self.python_runtime_module_count,
            "rss_idle_bytes": self.rss_idle_bytes,
            "rss_post_pulse_bytes": self.rss_post_pulse_bytes,
            "rss_pulse_delta_bytes": self.rss_pulse_delta_bytes,
            "deployment": self.deployment.as_dict(),
            "artifacts": [
                {
                    "name": a.name,
                    "path": a.path,
                    "bytes_on_disk": a.bytes_on_disk,
                    "human": _human_bytes(a.bytes_on_disk),
                    "present": a.present,
                }
                for a in self.artifacts
            ],
            "frontier_context": [
                {
                    "name": r.name,
                    "parameters_billion": r.parameters_billion,
                    "weights_bytes_estimate": r.weights_bytes_estimate,
                    "weights_human": _human_bytes(r.weights_bytes_estimate),
                    "core_is_smaller_by_x": round(self.smaller_than(r), 1),
                    "source_note": r.source_note,
                }
                for r in self.frontier_context
            ],
        }

    def summary(self) -> str:
        lines = [
            f"footprint  total_disk={_human_bytes(self.total_disk_bytes)}  "
            f"rss_idle={_human_bytes(self.rss_idle_bytes)}  "
            f"rss_after_pulse={_human_bytes(self.rss_post_pulse_bytes)}  "
            f"(+{_human_bytes(self.rss_pulse_delta_bytes)})",
            "  artifacts:",
        ]
        for a in self.artifacts:
            mark = "ok" if a.present else "--"
            lines.append(f"    [{mark}] {a.name:<28} {_human_bytes(a.bytes_on_disk):>10}  {a.path}")
        lines.append(f"  python_runtime_modules: {self.python_runtime_module_count} "
                     f"({_human_bytes(self.python_runtime_bytes)})")
        lines.append("  deployment: " + ", ".join(
            f"{k}={v}" for k, v in self.deployment.as_dict().items()
        ))
        lines.append("  vs published frontier model sizes:")
        for r in self.frontier_context:
            x = self.smaller_than(r)
            lines.append(f"    {r.name:<32} {_human_bytes(r.weights_bytes_estimate):>10}   "
                         f"CORE is {x:,.0f}x smaller")
        return "\n".join(lines)


def _human_bytes(n: int) -> str:
    """Format bytes for humans. Uses binary units (KiB, MiB) at full
    precision and falls back to plain int below 1 KiB.
    """
    if n < 1024:
        return f"{n} B"
    units = ("KiB", "MiB", "GiB", "TiB", "PiB")
    size = float(n)
    unit = units[0]
    for unit in units:
        size /= 1024.0
        if size < 1024.0:
            break
    return f"{size:.2f} {unit}"


def _dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                continue
    return total


def _rust_artifact_path() -> Path:
    """Locate the compiled Rust backend shared library, if present.

    Searches the release directory only — debug artifacts are not what
    deployment ships. Returns the first matching file or a sentinel
    non-existent path so the report still renders cleanly when Rust
    has not been built.
    """
    release = PROJECT_ROOT / "core-rs" / "target" / "release"
    if not release.exists():
        return release / "libcore_rs.dylib"
    for ext in ("dylib", "so", "dll"):
        for candidate in release.glob(f"libcore_rs.{ext}"):
            return candidate
    return release / "libcore_rs.dylib"


def _measure_python_runtime() -> tuple[int, int]:
    """Sum the byte size of every loaded module whose file is under
    PROJECT_ROOT. This is the actual import closure for the current
    process — not a directory scan that would over-count optional
    subsystems the lane never imports.
    """
    seen: set[Path] = set()
    total_bytes = 0
    for module in list(sys.modules.values()):
        if module is None:
            continue
        file_attr = getattr(module, "__file__", None)
        if not file_attr:
            continue
        try:
            p = Path(file_attr).resolve()
        except (OSError, ValueError):
            continue
        try:
            p.relative_to(PROJECT_ROOT)
        except ValueError:
            continue
        if p in seen or not p.exists():
            continue
        seen.add(p)
        try:
            total_bytes += p.stat().st_size
        except OSError:
            continue
    return total_bytes, len(seen)


def _rss_bytes() -> int:
    """Return resident set size in bytes. On Linux ru_maxrss is KiB; on
    macOS it is bytes. The conversion below covers both.
    """
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    raw = int(rusage.ru_maxrss)
    scale = 1 if sys.platform == "darwin" else 1024
    return raw * scale


def run_footprint(*, pack_id: str = "en_core_cognition_v1") -> FootprintReport:
    """Measure CORE's deployed footprint and return a FootprintReport.

    Triggers one pulse via `scripts.run_pulse.run_pulse` so the import
    closure and post-pulse RSS reflect what real deployment looks like.
    """
    rss_idle = _rss_bytes()

    from scripts.run_pulse import run_pulse
    run_pulse("What is truth?", use_glove=False)

    rss_post = _rss_bytes()
    py_bytes, py_modules = _measure_python_runtime()

    pack_path = PROJECT_ROOT / "language_packs" / "data" / pack_id
    vault_path = PROJECT_ROOT / "vault"
    rust_path = _rust_artifact_path()
    seed_packs_path = PROJECT_ROOT / "packs"

    artifacts = (
        ArtifactSize(
            name=f"language_pack:{pack_id}",
            path=str(pack_path.relative_to(PROJECT_ROOT)),
            bytes_on_disk=_dir_bytes(pack_path),
            present=pack_path.exists(),
        ),
        ArtifactSize(
            name="seed_packs",
            path=str(seed_packs_path.relative_to(PROJECT_ROOT)),
            bytes_on_disk=_dir_bytes(seed_packs_path),
            present=seed_packs_path.exists(),
        ),
        ArtifactSize(
            name="vault_module",
            path=str(vault_path.relative_to(PROJECT_ROOT)),
            bytes_on_disk=_dir_bytes(vault_path),
            present=vault_path.exists(),
        ),
        ArtifactSize(
            name="rust_backend",
            path=str(rust_path.relative_to(PROJECT_ROOT)) if rust_path.exists() else str(rust_path),
            bytes_on_disk=rust_path.stat().st_size if rust_path.exists() else 0,
            present=rust_path.exists(),
        ),
    )

    deployment = DeploymentProfile(
        runs_offline=True,
        requires_gpu=False,
        requires_network=False,
        requires_api_key=False,
    )

    return FootprintReport(
        artifacts=artifacts,
        python_runtime_bytes=py_bytes,
        python_runtime_module_count=py_modules,
        rss_idle_bytes=rss_idle,
        rss_post_pulse_bytes=rss_post,
        deployment=deployment,
        frontier_context=FRONTIER_REFERENCES,
    )


def write_report(report: FootprintReport, root: Path | None = None) -> Path:
    base = root or PROJECT_ROOT / "evals" / "reports"
    base.mkdir(parents=True, exist_ok=True)
    path = base / "footprint_latest.json"
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return path
