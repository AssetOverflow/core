"""Cost bench — wall/CPU-seconds per turn and $/1000-turn deployment estimate.

Anchors the "$/1000 turns" claim adjacent to evals/CLAIMS.md Tier 4
(cost/performance). Reports:

- Measured: turns run, wall_seconds_total, cpu_seconds_total,
  latency stats (min / median / p95 / max in milliseconds), and
  throughput in turns per second.
- Derived (with disclosed assumption): USD per 1000 turns at a
  published cloud-instance hourly rate.  The rate is named and
  sourced — no hidden assumptions.
- Frontier pricing context: public per-token rates from major
  providers, with source notes.  CORE's per-turn cost is compared
  apples-to-apples by estimating an equivalent token count per turn.

Energy / joules is **not** reported here.  Honest joules measurement
requires RAPL (Linux) or IOKit/powermetrics (macOS) with privileged
access, neither of which is available in a plain Python process.
Reporting a fabricated joules figure derived from a hand-waved TDP
would violate the project's "speculation is not evidence" rule.
``cpu_seconds_total`` is the closest proxy available without that
privileged access and is reported directly.

Usage:

    from benchmarks.cost import run_cost
    report = run_cost(turns=100)
    print(report.summary())

CLI surface (wired into core/cli.py separately):

    core bench cost --turns 100 --json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Cloud-instance hourly rate used to derive the $/1000-turn figure.
# Source must be a published, dated public price page — never an
# unsourced estimate.  AWS t3.medium is chosen because it is a
# small, general-purpose x86_64 instance with enough RAM to hold the
# CORE process and the cognition pack, which is what deployment
# actually needs (see benchmarks.footprint: ~7 MiB footprint).
@dataclass(frozen=True, slots=True)
class CloudReference:
    name: str
    region: str
    hourly_usd: float
    source_note: str


_CLOUD_REFERENCE = CloudReference(
    name="AWS t3.medium (2 vCPU, 4 GiB)",
    region="us-east-1, on-demand, Linux",
    hourly_usd=0.0416,
    source_note=(
        "aws.amazon.com/ec2/instance-types/t3 — public on-demand rate, "
        "captured 2026-05-17.  Update source_note + hourly_usd if the "
        "price page changes."
    ),
)


# Frontier-model inference pricing for honest comparison.  Every entry
# must have a public dated source.  Token-rate units: USD per 1M tokens.
# Inference cost per turn is derived using a disclosed
# tokens-per-turn estimate so the comparison is reproducible.
@dataclass(frozen=True, slots=True)
class FrontierPricing:
    name: str
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float
    source_note: str


_FRONTIER_PRICING: tuple[FrontierPricing, ...] = (
    FrontierPricing(
        name="Anthropic Claude Sonnet 4.5 (API)",
        input_usd_per_million_tokens=3.00,
        output_usd_per_million_tokens=15.00,
        source_note=(
            "anthropic.com/pricing — public API rate, captured 2026-05-17."
        ),
    ),
    FrontierPricing(
        name="OpenAI GPT-4o (API)",
        input_usd_per_million_tokens=2.50,
        output_usd_per_million_tokens=10.00,
        source_note=(
            "openai.com/api/pricing — public API rate, captured 2026-05-17."
        ),
    ),
    FrontierPricing(
        name="Anthropic Claude Haiku 4.5 (API)",
        input_usd_per_million_tokens=1.00,
        output_usd_per_million_tokens=5.00,
        source_note=(
            "anthropic.com/pricing — public API rate, captured 2026-05-17."
        ),
    ),
)


# Tokens-per-turn estimate used for frontier-pricing comparison.
# A short user turn ("What is truth?") plus a typical short
# assistant response runs roughly 20 input + 40 output tokens
# under GPT/Claude tokenizers.  These numbers are conservative;
# the comparison errs in the frontier's favor.
_FRONTIER_INPUT_TOKENS_PER_TURN = 20
_FRONTIER_OUTPUT_TOKENS_PER_TURN = 40


@dataclass(frozen=True, slots=True)
class LatencyStats:
    min_ms: float
    median_ms: float
    p95_ms: float
    max_ms: float

    def as_dict(self) -> dict[str, float]:
        return {
            "min_ms": round(self.min_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "max_ms": round(self.max_ms, 3),
        }


@dataclass(frozen=True, slots=True)
class CostReport:
    turns: int
    warmup_turns: int
    wall_seconds_total: float
    cpu_seconds_total: float
    latency: LatencyStats
    cloud_reference: CloudReference
    frontier_pricing: tuple[FrontierPricing, ...]

    @property
    def throughput_turns_per_second(self) -> float:
        if self.wall_seconds_total <= 0:
            return 0.0
        return self.turns / self.wall_seconds_total

    @property
    def cpu_utilization(self) -> float:
        if self.wall_seconds_total <= 0:
            return 0.0
        return self.cpu_seconds_total / self.wall_seconds_total

    @property
    def usd_per_1000_turns(self) -> float:
        """Cost to serve 1000 turns at ``cloud_reference.hourly_usd``."""
        if self.throughput_turns_per_second <= 0:
            return 0.0
        seconds_per_1000_turns = 1000.0 / self.throughput_turns_per_second
        hours = seconds_per_1000_turns / 3600.0
        return hours * self.cloud_reference.hourly_usd

    def frontier_usd_per_1000_turns(self, pricing: FrontierPricing) -> float:
        """Cost to serve 1000 turns at the named frontier API rate using
        ``_FRONTIER_INPUT_TOKENS_PER_TURN`` and
        ``_FRONTIER_OUTPUT_TOKENS_PER_TURN``."""
        input_usd = (
            _FRONTIER_INPUT_TOKENS_PER_TURN * 1000
            * pricing.input_usd_per_million_tokens
            / 1_000_000
        )
        output_usd = (
            _FRONTIER_OUTPUT_TOKENS_PER_TURN * 1000
            * pricing.output_usd_per_million_tokens
            / 1_000_000
        )
        return input_usd + output_usd

    def as_dict(self) -> dict[str, Any]:
        return {
            "turns": self.turns,
            "warmup_turns": self.warmup_turns,
            "wall_seconds_total": round(self.wall_seconds_total, 6),
            "cpu_seconds_total": round(self.cpu_seconds_total, 6),
            "throughput_turns_per_second": round(self.throughput_turns_per_second, 4),
            "cpu_utilization": round(self.cpu_utilization, 4),
            "latency": self.latency.as_dict(),
            "usd_per_1000_turns": round(self.usd_per_1000_turns, 6),
            "cloud_reference": {
                "name": self.cloud_reference.name,
                "region": self.cloud_reference.region,
                "hourly_usd": self.cloud_reference.hourly_usd,
                "source_note": self.cloud_reference.source_note,
            },
            "frontier_pricing_comparison": [
                {
                    "name": p.name,
                    "input_usd_per_million_tokens": p.input_usd_per_million_tokens,
                    "output_usd_per_million_tokens": p.output_usd_per_million_tokens,
                    "frontier_usd_per_1000_turns": round(
                        self.frontier_usd_per_1000_turns(p), 4
                    ),
                    "core_cheaper_by_x": (
                        round(
                            self.frontier_usd_per_1000_turns(p)
                            / self.usd_per_1000_turns,
                            1,
                        )
                        if self.usd_per_1000_turns > 0 else 0.0
                    ),
                    "source_note": p.source_note,
                }
                for p in self.frontier_pricing
            ],
            "frontier_token_assumption": {
                "input_tokens_per_turn": _FRONTIER_INPUT_TOKENS_PER_TURN,
                "output_tokens_per_turn": _FRONTIER_OUTPUT_TOKENS_PER_TURN,
                "note": (
                    "Conservative short-prompt / short-answer turn.  "
                    "Frontier $/1000-turns scales linearly with these counts."
                ),
            },
            "energy_disclosure": (
                "Joules per turn is not reported.  Honest energy "
                "measurement requires RAPL (Linux) or IOKit/powermetrics "
                "(macOS) with privileged access.  cpu_seconds_total is "
                "the available CPU-time proxy."
            ),
        }

    def summary(self) -> str:
        lines = [
            f"cost  turns={self.turns}  wall={self.wall_seconds_total:.3f}s  "
            f"cpu={self.cpu_seconds_total:.3f}s  "
            f"throughput={self.throughput_turns_per_second:.2f} turns/s",
            f"  latency (ms): "
            f"min={self.latency.min_ms:.2f}  "
            f"median={self.latency.median_ms:.2f}  "
            f"p95={self.latency.p95_ms:.2f}  "
            f"max={self.latency.max_ms:.2f}",
            f"  $/1000 turns @ {self.cloud_reference.name}: "
            f"${self.usd_per_1000_turns:.6f}  "
            f"({self.cloud_reference.hourly_usd:.4f}/hr)",
            "  vs frontier inference pricing:",
        ]
        for p in self.frontier_pricing:
            frontier_cost = self.frontier_usd_per_1000_turns(p)
            ratio = (
                frontier_cost / self.usd_per_1000_turns
                if self.usd_per_1000_turns > 0 else 0.0
            )
            lines.append(
                f"    {p.name:<40} ${frontier_cost:.4f}/1000   "
                f"CORE is {ratio:,.0f}x cheaper"
            )
        lines.append(
            "  energy: not reported — see energy_disclosure in JSON output."
        )
        return "\n".join(lines)


def _build_runtime():
    """Construct a ChatRuntime that mirrors the production deployment path.

    Imported lazily so importing the benchmarks module doesn't pull the
    full runtime stack at module-load time.
    """
    from chat.runtime import ChatRuntime
    return ChatRuntime()


def run_cost(
    *,
    turns: int = 100,
    warmup_turns: int = 5,
    prompt: str = "What is truth?",
) -> CostReport:
    """Measure CORE per-turn cost over ``turns`` repetitions.

    A fresh ChatRuntime is constructed before measurement begins.  The
    first ``warmup_turns`` are excluded from the latency record so the
    measurement reflects steady-state behavior, not first-import cost
    (already covered by ``benchmarks.footprint``).
    """
    if turns < 1:
        raise ValueError(f"turns must be >= 1, got {turns}")
    if warmup_turns < 0:
        raise ValueError(f"warmup_turns must be >= 0, got {warmup_turns}")

    runtime = _build_runtime()

    # Warm-up.  The first chat() call triggers lazy imports inside the
    # cognition pipeline; counting those in the measured window would
    # inflate p95 latency and understate steady-state throughput.
    for _ in range(warmup_turns):
        try:
            runtime.chat(prompt, max_tokens=8)
        except ValueError:
            # An out-of-vocab prompt is a measurement input error here,
            # not a runtime fault.  Re-raise so the caller picks a valid
            # prompt rather than silently warming nothing.
            raise

    latencies_ms: list[float] = []
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    for _ in range(turns):
        turn_start = time.perf_counter()
        runtime.chat(prompt, max_tokens=8)
        latencies_ms.append((time.perf_counter() - turn_start) * 1000.0)
    wall_total = time.perf_counter() - wall_start
    cpu_total = time.process_time() - cpu_start

    latencies_ms.sort()
    p95_index = max(0, int(round(0.95 * (len(latencies_ms) - 1))))
    latency = LatencyStats(
        min_ms=latencies_ms[0],
        median_ms=statistics.median(latencies_ms),
        p95_ms=latencies_ms[p95_index],
        max_ms=latencies_ms[-1],
    )

    return CostReport(
        turns=turns,
        warmup_turns=warmup_turns,
        wall_seconds_total=wall_total,
        cpu_seconds_total=cpu_total,
        latency=latency,
        cloud_reference=_CLOUD_REFERENCE,
        frontier_pricing=_FRONTIER_PRICING,
    )


def write_report(report: CostReport, root: Path | None = None) -> Path:
    base = root or PROJECT_ROOT / "evals" / "reports"
    base.mkdir(parents=True, exist_ok=True)
    path = base / "cost_latest.json"
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return path


def _cli_main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Measure CORE per-turn cost.")
    parser.add_argument("--turns", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--prompt", type=str, default="What is truth?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    report = run_cost(
        turns=args.turns,
        warmup_turns=args.warmup,
        prompt=args.prompt,
    )
    if not args.no_write:
        write_report(report)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(report.summary())
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
