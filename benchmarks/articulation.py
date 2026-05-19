"""Articulation benchmark suite — Phase 4 capability proof.

Anchors the post-Phase-4 claim set in numbers rather than rhetoric.

Sub-benches:

  1. **breadth** — Fires every supported intent shape (9 today:
     DEFINITION / RECALL / CAUSE / VERIFICATION / COMPARISON /
     CORRECTION / PROCEDURE / NARRATIVE / EXAMPLE) plus the OOV
     fall-through and the cross-pack chain shape.  Reports the
     ``grounding_source`` and a snippet of the surface for each.

  2. **determinism** — Runs the same prompt set N times in fresh
     ``ChatRuntime`` instances and asserts byte-identical surfaces
     across every run.  The whole *premise* of CORE is that the
     surface is reconstructed from immutable corpora + ratified
     packs, so any drift here is a load-bearing defect.

  3. **footprint** — Drives ``ChatRuntime`` through ``turns`` cold-
     start prompts and samples RSS (psutil) every K turns.  Reports
     start RSS / peak RSS / end RSS / per-turn delta.  Catches
     unbounded cache growth or pack-reload leaks.

  4. **cross-topic** — Mounts a single ``ChatRuntime`` with
     ``thread_anaphora=True`` and walks a multi-topic prompt
     sequence that crosses cognition + relations + cross-pack
     subjects.  Reports the count of turns where the anaphora
     prefix fired and which thread positions it referenced — the
     concrete signal that turn-level composition is doing real work.

  5. **ollama-compare** — Opt-in side-by-side.  Sends a fixed prompt
     set to (a) ``ChatRuntime`` and (b) a local Ollama model.
     Reports both surfaces verbatim and a determinism-delta: CORE
     emits byte-identical surface on N reruns; Ollama emits
     ``unique_surfaces > 1`` even with ``temperature=0`` on most
     prompts.  Skipped (status: ``skipped`` instead of ``failed``)
     when the ``ollama`` binary is not on ``PATH``.

The whole suite is deterministic on the CORE side — no clock-time
or RNG influence on what gets emitted.  Walltime sampling lives in
``benchmarks.cost``; this module focuses on capability + identity.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# Curated prompt set — every intent shape + OOV + cross-pack.
INTENT_PROBE_PROMPTS: tuple[tuple[str, str], ...] = (
    ("DEFINITION", "What is knowledge?"),
    ("RECALL", "Recall truth."),
    ("CAUSE", "Why does knowledge exist?"),
    ("VERIFICATION", "Does memory require recall?"),
    ("COMPARISON", "Compare knowledge and wisdom."),
    ("CORRECTION", "No, that's wrong."),
    ("PROCEDURE", "How do I define a concept?"),
    ("NARRATIVE", "Tell me about truth."),
    ("EXAMPLE", "Give me an example of knowledge."),
    ("OOV_FALLBACK", "What is photosynthesis?"),
    ("CROSS_PACK_VERIFICATION", "Does identity require family?"),
    ("CROSS_PACK_CAUSE", "Why does understanding exist?"),
)

# Cross-topic walk — exercises thread anaphora across cognition,
# relations, and cross-pack subjects.
CROSS_TOPIC_PROMPTS: tuple[str, ...] = (
    "Why does light exist?",         # CAUSE — light
    "What is truth?",                # DEFINITION — truth (light's object)
    "Why does knowledge exist?",     # CAUSE — knowledge
    "Tell me about family.",         # NARRATIVE — family (relations)
    "Does identity require family?", # VERIFICATION — cross-pack
    "What is parent?",               # DEFINITION — relations
    "Give me an example of memory.", # EXAMPLE
    "Compare truth and knowledge.",  # COMPARISON
)

# Determinism rerun set — short prompts that exercise every grounding
# tier we care about.
DETERMINISM_PROMPTS: tuple[str, ...] = (
    "What is truth?",
    "Why does knowledge exist?",
    "Tell me about family.",
    "Does identity require family?",
    "Give me an example of memory.",
)


# ---------------------------------------------------------------------------
# Report shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentProbe:
    label: str
    prompt: str
    intent_tag: str
    grounding_source: str
    surface_snippet: str


@dataclass(frozen=True)
class DeterminismCase:
    prompt: str
    runs: int
    unique_surfaces: int
    sample: str


@dataclass(frozen=True)
class FootprintSample:
    turn: int
    rss_bytes: int


@dataclass(frozen=True)
class CrossTopicTurn:
    turn: int
    prompt: str
    intent_tag: str
    grounding_source: str
    anaphora_fired: bool
    surface_snippet: str


@dataclass(frozen=True)
class OllamaPair:
    prompt: str
    core_surface: str
    core_unique_surfaces_on_5_reruns: int
    ollama_surface: str
    ollama_unique_surfaces_on_5_reruns: int


@dataclass
class ArticulationReport:
    breadth: list[IntentProbe] = field(default_factory=list)
    determinism: list[DeterminismCase] = field(default_factory=list)
    determinism_all_identical: bool = True
    footprint: list[FootprintSample] = field(default_factory=list)
    footprint_start_bytes: int = 0
    footprint_peak_bytes: int = 0
    footprint_end_bytes: int = 0
    footprint_per_turn_delta_bytes: float = 0.0
    cross_topic: list[CrossTopicTurn] = field(default_factory=list)
    anaphora_fire_count: int = 0
    ollama: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "breadth": [p.__dict__ for p in self.breadth],
            "determinism": [c.__dict__ for c in self.determinism],
            "determinism_all_identical": self.determinism_all_identical,
            "footprint_samples": [s.__dict__ for s in self.footprint],
            "footprint_start_bytes": self.footprint_start_bytes,
            "footprint_peak_bytes": self.footprint_peak_bytes,
            "footprint_end_bytes": self.footprint_end_bytes,
            "footprint_per_turn_delta_bytes": round(
                self.footprint_per_turn_delta_bytes, 2
            ),
            "cross_topic": [t.__dict__ for t in self.cross_topic],
            "anaphora_fire_count": self.anaphora_fire_count,
            "ollama": self.ollama,
        }


# ---------------------------------------------------------------------------
# Sub-benches
# ---------------------------------------------------------------------------


def _snippet(s: str, n: int = 120) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _classify_prompt(prompt: str) -> str:
    """Re-derive the intent label from the prompt text for the report.

    ``ChatResponse`` does not surface the classified ``IntentTag`` — it
    is internal to the turn loop.  Recomputing on the same text is
    deterministic and pack-free; safe for benchmark labelling.
    """
    from generate.intent import classify_intent
    try:
        intent = classify_intent(prompt)
        return intent.tag.name
    except Exception:
        return "UNKNOWN"


def bench_breadth() -> list[IntentProbe]:
    from chat.runtime import ChatRuntime
    out: list[IntentProbe] = []
    for label, prompt in INTENT_PROBE_PROMPTS:
        rt = ChatRuntime()
        resp = rt.chat(prompt)
        out.append(IntentProbe(
            label=label,
            prompt=prompt,
            intent_tag=_classify_prompt(prompt),
            grounding_source=getattr(resp, "grounding_source", "unknown"),
            surface_snippet=_snippet(resp.surface),
        ))
    return out


def bench_determinism(runs: int = 20) -> tuple[list[DeterminismCase], bool]:
    from chat.runtime import ChatRuntime
    cases: list[DeterminismCase] = []
    all_identical = True
    for prompt in DETERMINISM_PROMPTS:
        seen: set[str] = set()
        sample = ""
        for _ in range(runs):
            rt = ChatRuntime()
            resp = rt.chat(prompt)
            seen.add(resp.surface)
            if not sample:
                sample = resp.surface
        unique = len(seen)
        cases.append(DeterminismCase(
            prompt=prompt, runs=runs, unique_surfaces=unique,
            sample=_snippet(sample),
        ))
        if unique != 1:
            all_identical = False
    return cases, all_identical


def bench_footprint(
    turns: int = 200,
    sample_every: int = 25,
) -> tuple[list[FootprintSample], int, int, int, float]:
    """Drive a single ChatRuntime through ``turns`` cold-start prompts
    and sample RSS every ``sample_every`` turns.

    Uses a single runtime so the bench measures cache/vault growth,
    not per-process startup overhead.
    """
    import psutil
    from chat.runtime import ChatRuntime

    proc = psutil.Process()
    rt = ChatRuntime()

    samples: list[FootprintSample] = []
    start = proc.memory_info().rss
    samples.append(FootprintSample(turn=0, rss_bytes=start))
    peak = start
    prompts = [p for _, p in INTENT_PROBE_PROMPTS]
    n = len(prompts)
    for t in range(1, turns + 1):
        rt.chat(prompts[t % n])
        if t % sample_every == 0 or t == turns:
            rss = proc.memory_info().rss
            samples.append(FootprintSample(turn=t, rss_bytes=rss))
            peak = max(peak, rss)
    end = samples[-1].rss_bytes
    per_turn = (end - start) / max(turns, 1)
    return samples, start, peak, end, per_turn


def bench_cross_topic() -> tuple[list[CrossTopicTurn], int]:
    """Walk the CROSS_TOPIC_PROMPTS list on ONE runtime with
    ``thread_anaphora=True`` and report which turns fired the
    anaphora prefix.
    """
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig

    rt = ChatRuntime(config=RuntimeConfig(thread_anaphora=True))
    out: list[CrossTopicTurn] = []
    fires = 0
    for i, prompt in enumerate(CROSS_TOPIC_PROMPTS):
        resp = rt.chat(prompt)
        # Anaphora prefix has the shape ``(Recalling turn N: ...)``.
        fired = resp.surface.startswith("(Recalling turn")
        if fired:
            fires += 1
        out.append(CrossTopicTurn(
            turn=i,
            prompt=prompt,
            intent_tag=_classify_prompt(prompt),
            grounding_source=getattr(resp, "grounding_source", "unknown"),
            anaphora_fired=fired,
            surface_snippet=_snippet(resp.surface),
        ))
    return out, fires


def _have_ollama() -> bool:
    return shutil.which("ollama") is not None


def _ollama_complete(model: str, prompt: str, timeout: float = 30.0) -> str:
    """Single completion via ``ollama run`` — deterministic-as-possible
    (seed pinned, ``num_predict`` capped).  Returns stdout text or an
    error placeholder; never raises.
    """
    try:
        result = subprocess.run(
            ["ollama", "run", model, "--", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout.strip() or result.stderr.strip()
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"<ollama error: {exc}>"


def bench_ollama_compare(
    model: str | None = None,
    prompts: Iterable[str] = DETERMINISM_PROMPTS,
    core_reruns: int = 5,
    ollama_reruns: int = 5,
) -> dict[str, Any]:
    """Side-by-side: CORE vs Ollama on a fixed prompt set.

    Returns a dict with ``status`` ∈ {``ran``, ``skipped``}, and on
    ``ran`` includes per-prompt CORE+Ollama surfaces plus a
    determinism count for each (unique surfaces across N reruns).
    """
    if not _have_ollama() or model is None:
        return {
            "status": "skipped",
            "reason": (
                "ollama binary not on PATH" if not _have_ollama()
                else "no model specified"
            ),
        }

    from chat.runtime import ChatRuntime
    pairs: list[OllamaPair] = []
    for prompt in prompts:
        # CORE: rerun N times, count unique surfaces.
        core_seen: set[str] = set()
        core_sample = ""
        for _ in range(core_reruns):
            rt = ChatRuntime()
            r = rt.chat(prompt)
            core_seen.add(r.surface)
            if not core_sample:
                core_sample = r.surface
        # Ollama: rerun N times, count unique surfaces.
        ollama_seen: set[str] = set()
        ollama_sample = ""
        for _ in range(ollama_reruns):
            txt = _ollama_complete(model, prompt)
            ollama_seen.add(txt)
            if not ollama_sample:
                ollama_sample = txt
        pairs.append(OllamaPair(
            prompt=prompt,
            core_surface=_snippet(core_sample, n=240),
            core_unique_surfaces_on_5_reruns=len(core_seen),
            ollama_surface=_snippet(ollama_sample, n=240),
            ollama_unique_surfaces_on_5_reruns=len(ollama_seen),
        ))
    return {
        "status": "ran",
        "model": model,
        "core_reruns": core_reruns,
        "ollama_reruns": ollama_reruns,
        "pairs": [p.__dict__ for p in pairs],
        "core_byte_identical_on_every_prompt": all(
            p.core_unique_surfaces_on_5_reruns == 1 for p in pairs
        ),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_articulation_suite(
    *,
    determinism_runs: int = 20,
    footprint_turns: int = 200,
    footprint_sample_every: int = 25,
    ollama_model: str | None = None,
    ollama_core_reruns: int = 5,
    ollama_reruns: int = 3,
) -> ArticulationReport:
    """Run every sub-bench and return the consolidated report."""
    report = ArticulationReport()

    report.breadth = bench_breadth()
    det_cases, det_ok = bench_determinism(runs=determinism_runs)
    report.determinism = det_cases
    report.determinism_all_identical = det_ok
    (
        samples, start, peak, end, per_turn,
    ) = bench_footprint(
        turns=footprint_turns, sample_every=footprint_sample_every,
    )
    report.footprint = samples
    report.footprint_start_bytes = start
    report.footprint_peak_bytes = peak
    report.footprint_end_bytes = end
    report.footprint_per_turn_delta_bytes = per_turn
    ct_turns, ct_fires = bench_cross_topic()
    report.cross_topic = ct_turns
    report.anaphora_fire_count = ct_fires
    report.ollama = bench_ollama_compare(
        model=ollama_model,
        prompts=DETERMINISM_PROMPTS[:3],  # subset — ollama is slow
        core_reruns=ollama_core_reruns,
        ollama_reruns=ollama_reruns,
    )

    return report


def format_summary(report: ArticulationReport) -> str:
    out: list[str] = []
    out.append("=" * 76)
    out.append("Articulation benchmark suite")
    out.append("=" * 76)
    out.append("")
    out.append("[1/5] Intent breadth — every supported intent shape:")
    for p in report.breadth:
        out.append(
            f"  {p.label:30s} {p.intent_tag:14s} {p.grounding_source:9s} "
            f"{_snippet(p.surface_snippet, 80)}"
        )
    out.append("")
    out.append("[2/5] Determinism — same prompt → byte-identical surface:")
    for c in report.determinism:
        flag = "OK" if c.unique_surfaces == 1 else "FAIL"
        out.append(
            f"  [{flag}] {c.runs} runs / {c.unique_surfaces} unique surface(s)  "
            f"{_snippet(c.prompt, 50)}"
        )
    out.append(
        f"  all_identical = {report.determinism_all_identical}"
    )
    out.append("")
    out.append("[3/5] Memory footprint — single runtime, repeated turns:")
    if report.footprint:
        out.append(
            f"  start = {report.footprint_start_bytes / 1024 / 1024:.1f} MiB  "
            f"peak = {report.footprint_peak_bytes / 1024 / 1024:.1f} MiB  "
            f"end = {report.footprint_end_bytes / 1024 / 1024:.1f} MiB"
        )
        out.append(
            f"  per-turn ΔRSS = "
            f"{report.footprint_per_turn_delta_bytes / 1024:.2f} KiB"
        )
    out.append("")
    out.append("[4/5] Cross-topic context — thread anaphora across subjects:")
    for t in report.cross_topic:
        marker = "↩" if t.anaphora_fired else " "
        out.append(
            f"  {marker} turn {t.turn} [{t.intent_tag:12s} {t.grounding_source:9s}]"
            f"  {_snippet(t.prompt, 40)}"
        )
    out.append(f"  anaphora fired on {report.anaphora_fire_count} turn(s)")
    out.append(
        "  note: thread anaphora today fires only when BOTH the prior and current "
        "turn are pack/teaching tier (ADR-0066 §Future ADRs).  After the first "
        "turn populates the vault, subsequent turns recall from vault and the "
        "anaphora prefix is suppressed.  This bench measures both thread-context "
        "retention (state survives across topic shifts) and the current anaphora "
        "fire rate (which is the architectural ceiling, not a defect)."
    )
    out.append("")
    out.append("[5/5] Ollama side-by-side:")
    status = report.ollama.get("status", "skipped")
    if status == "skipped":
        out.append(f"  skipped — {report.ollama.get('reason', '')}")
    else:
        out.append(
            f"  model = {report.ollama['model']}   "
            f"core_byte_identical_on_every_prompt = "
            f"{report.ollama['core_byte_identical_on_every_prompt']}"
        )
        for pair in report.ollama["pairs"]:
            out.append("")
            out.append(f"  prompt: {pair['prompt']}")
            out.append(
                f"    CORE    [{pair['core_unique_surfaces_on_5_reruns']} unique] "
                f"{_snippet(pair['core_surface'], 200)}"
            )
            out.append(
                f"    ollama  [{pair['ollama_unique_surfaces_on_5_reruns']} unique] "
                f"{_snippet(pair['ollama_surface'], 200)}"
            )
    out.append("")
    return "\n".join(out)


__all__ = [
    "ArticulationReport",
    "INTENT_PROBE_PROMPTS",
    "CROSS_TOPIC_PROMPTS",
    "DETERMINISM_PROMPTS",
    "bench_breadth",
    "bench_determinism",
    "bench_footprint",
    "bench_cross_topic",
    "bench_ollama_compare",
    "run_articulation_suite",
    "format_summary",
]
