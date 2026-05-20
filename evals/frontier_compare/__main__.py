from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cross_provider import run_prompt_battery
from .model_registry import require_model_card
from .providers import ProviderConfig, build_adapter, load_dotenv_if_present
from .runner import (
    BenchmarkReport,
    format_human_report,
    run_all,
    run_suite,
    write_report,
)


_CORE_ONLY_SUITES = ("determinism", "truth_lock", "axis_orthogonality", "all")
_CROSS_PROVIDER_SUITES = ("prompt_battery",)
_VALID_SUITES = _CORE_ONLY_SUITES + _CROSS_PROVIDER_SUITES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals.frontier_compare",
        description=(
            "Run frontier_compare benchmark suites.  Default --provider=core "
            "runs the existing CORE-native suites; specify a non-CORE "
            "--provider to run the cross-provider prompt_battery."
        ),
    )
    parser.add_argument(
        "--suite",
        choices=_VALID_SUITES,
        default="all",
        help=(
            "benchmark suite to run.  CORE-only suites: "
            f"{', '.join(_CORE_ONLY_SUITES)}.  Cross-provider suites: "
            f"{', '.join(_CROSS_PROVIDER_SUITES)}.  Default 'all' runs every "
            "CORE-only suite when --provider=core, otherwise prompt_battery."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("core", "openai", "anthropic", "ollama"),
        default="core",
        help=(
            "provider to benchmark.  'core' (default) runs the existing "
            "CORE-native suites with full telemetry.  Other providers run "
            "the cross-provider prompt_battery only — CORE-only suites "
            "(determinism/truth_lock/axis_orthogonality) are rejected with "
            "a clear error rather than silently producing degraded telemetry."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "explicit model id override (e.g. gpt-4o-2024-08-06).  When "
            "omitted, uses the provider's env-var default.  Validated "
            "against the model_registry — floating aliases are rejected."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the stable machine-readable JSON report on stdout.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=(
            "optional path to write the JSON report.  When --provider is "
            "non-core and --report is not set, the report is auto-written "
            "to evals/frontier_compare/results/<provider>_<model>_<utc>.json "
            "so cross-provider runs always leave a durable artifact."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="path to a .env file with provider credentials (default: ./.env).",
    )
    return parser


def _build_cfg(args: argparse.Namespace) -> ProviderConfig:
    """Build a validated ProviderConfig from --provider / --model flags."""
    load_dotenv_if_present(str(args.env_file))
    cfg = ProviderConfig.from_env(args.provider)
    if args.model is not None:
        # Operator-supplied model override — re-resolve through the registry.
        cfg = ProviderConfig(
            provider=cfg.provider,
            model=args.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            extra=cfg.extra,
        )
    # require_model_card raises on floating aliases / unregistered models.
    require_model_card(cfg.provider, cfg.model)
    return cfg


def _auto_report_path(cfg: ProviderConfig) -> Path:
    """Deterministic results-dir path when operator didn't supply --report."""
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = cfg.model.replace("/", "_").replace(":", "_")
    return Path("evals/frontier_compare/results") / (
        f"{cfg.provider}_{safe_model}_{stamp}.json"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Decide which lane this run belongs to.  Two orthogonal axes:
    #   - cross-provider suites (prompt_battery) ALWAYS go through the
    #     provider-adapter path, even when --provider=core (CORE is just
    #     one adapter among many for those suites).
    #   - CORE-only suites (determinism/truth_lock/axis_orthogonality)
    #     require --provider=core and pull CORE-internal telemetry that
    #     no other adapter can supply.
    cross_provider = args.suite in _CROSS_PROVIDER_SUITES or (
        args.suite == "all" and args.provider != "core"
    )

    if not cross_provider:
        # Existing CORE-native path.  Reject the obvious operator error
        # of asking for a CORE-only suite with a non-CORE provider.
        if args.provider != "core":
            print(
                f"error: suite {args.suite!r} is CORE-only; pass "
                f"--suite prompt_battery (the cross-provider suite) when "
                f"--provider={args.provider!r}.",
                file=sys.stderr,
            )
            return 2
        report = run_all() if args.suite == "all" else run_suite(args.suite)
    else:
        # Cross-provider path — runs over the provider adapter.
        cfg = _build_cfg(args)
        adapter = build_adapter(cfg)
        suite_report = run_prompt_battery(adapter, cfg=cfg)
        report = BenchmarkReport(
            benchmark_family="frontier_compare_wave1",
            model=cfg.model,
            mode=cfg.provider,
            suites=(suite_report,),
        )
        # Always persist non-CORE runs — they're rate-limited / paid, so
        # losing the artifact is genuinely costly.  CORE adapter runs of
        # prompt_battery only persist when --report is explicit.
        if args.report is None and cfg.provider != "core":
            args.report = _auto_report_path(cfg)

    if args.report is not None:
        write_report(report, args.report)
        print(f"report written: {args.report}", file=sys.stderr)

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_human_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
