"""Command line interface for the CORE versor engine."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn


# The `core` console script may be installed through stale editable metadata while
# this repo is moving quickly. Ensure sibling top-level packages such as
# alignment/, morphology/, and sensorium/ are importable from the checked-out
# source tree before any runtime imports execute.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CORE_RS_DIR = _REPO_ROOT / "core-rs"
_CORE_RS_MANIFEST = _CORE_RS_DIR / "Cargo.toml"

DESCRIPTION = "CORE versor engine command suite."
EPILOG = "Examples:\n  core chat\n  core pulse \"What is truth?\"\n  core pulse --no-glove --json \"Compare knowledge and wisdom\"\n  core bench\n  core bench --suite determinism --runs 50\n  core bench --suite speedup --json\n  core trace \"word beginning truth\"\n  core trace --output-language grc --frame-pack grc --json \"logos\"\n  core rust status\n  core rust build\n  core oov covenant\n  core pack list\n  core pack verify en_minimal_v1\n  core test --suite fast -q\n  core test --suite pulse -q\n  core test --suite proof -q\n  core test --suite cognition -q\n  core test -- tests/test_alignment_graph.py -q\n  core eval --list\n  core eval cognition\n  core eval cognition --json --save\n  core eval cognition --split dev --version v1"

_TEST_SUITES: dict[str, tuple[str, ...]] = {
    "fast": (
        "tests/test_cli_test_suites.py",
        "tests/test_runtime_config.py",
        "tests/test_core_semantic_seed_pack.py",
        "tests/test_intent_proposition_graph.py",
        "tests/test_articulation_realizer_v2.py",
        "tests/test_reviewed_teaching_loop.py",
        "tests/test_cognitive_eval_harness.py",
    ),
    "smoke": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_cognitive_turn_pipeline.py",
        "tests/test_architectural_invariants.py",
    ),
    "runtime": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_session_coherence.py",
    ),
    "cognition": (
        "tests/test_intent_proposition_graph.py",
        "tests/test_cognitive_turn_pipeline.py",
        "tests/test_articulation_realizer_v2.py",
        "tests/test_semantic_realizer_integration.py",
        "tests/test_cognitive_eval_harness.py",
        "tests/test_deterministic_hash.py",
        "tests/test_morphology_irregular.py",
        "tests/test_realizer_quantifier_agreement.py",
        "tests/test_benchmarks_profiler.py",
        "tests/test_compose_relations.py",
        "tests/test_replay_vs_llm_benchmark.py",
    ),
    "teaching": (
        "tests/test_reviewed_teaching_loop.py",
        "tests/test_pipeline_teaching_integration.py",
        "tests/test_epistemic_invariants.py",
    ),
    "packs": (
        "tests/test_core_semantic_seed_pack.py",
    ),
    "algebra": (
        "tests/test_versor_closure.py",
        "tests/test_holonomy.py",
        "tests/test_holonomy_resonance.py",
        "tests/test_energy.py",
        "tests/test_motor.py",
        "tests/test_null_cone.py",
        "tests/test_vault_recall.py",
        "tests/test_vault_recall_vectorised.py",
        "tests/test_vault_recall_rust_parity.py",
        "tests/test_cga_inner_rust_parity.py",
        "tests/test_geometric_product_rust_parity.py",
        "tests/test_versor_condition_rust_parity.py",
        "tests/test_versor_apply_rust_parity.py",
    ),
    "pulse": (
        "tests/test_pulse_integration.py",
        "tests/test_graph_diffusion.py",
    ),
    "formation": (
        "tests/formation",
    ),
    "proof": (
        "tests/test_proof_properties.py",
    ),
    # ADR-0024 chain suites (Phases 2-6).  Each phase has its own
    # contract tests so investors / reviewers can run them
    # independently; ``adr-0024`` runs the full chain end-to-end.
    "refusal": (
        "tests/test_refusal_contract.py",
    ),
    "margin": (
        "tests/test_margin_admissibility.py",
    ),
    "rotor": (
        "tests/test_rotor_admissibility.py",
    ),
    "inner-loop": (
        "tests/test_inner_loop_admissibility.py",
        "tests/test_inner_loop_phase2.py",
        "tests/test_inner_loop_phase3.py",
        "tests/test_inner_loop_phase4.py",
    ),
    "phase5": (
        "tests/test_phase5_corpus.py",
    ),
    "phase6": (
        "tests/test_phase6_demo.py",
    ),
    "adr-0024": (
        "tests/test_refusal_contract.py",
        "tests/test_margin_admissibility.py",
        "tests/test_rotor_admissibility.py",
        "tests/test_inner_loop_admissibility.py",
        "tests/test_inner_loop_phase2.py",
        "tests/test_inner_loop_phase3.py",
        "tests/test_inner_loop_phase4.py",
        "tests/test_phase5_corpus.py",
        "tests/test_phase6_demo.py",
    ),
    "full": ("tests/",),
}


def _run(*args: str, check: bool = False, cwd: Path | None = None) -> int:
    """Run a child command and return its exit code."""
    completed = subprocess.run(args, check=check, text=True, cwd=cwd)
    return int(completed.returncode)


def _die(message: str, *, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _print_runtime_import_hint(exc: BaseException) -> NoReturn:
    _die(
        "runtime import failed. Run `core doctor` to inspect packaging. Root cause: "
        f"{exc.__class__.__name__}: {exc}",
        code=1,
    )


def _runtime_config_from_args(args: argparse.Namespace):
    from core.config import DEFAULT_CONFIG, RuntimeConfig

    output_language = args.output_language
    frame_pack = args.frame_pack or output_language
    input_packs = tuple(args.pack) if getattr(args, "pack", None) else DEFAULT_CONFIG.input_packs
    return RuntimeConfig(
        input_packs=input_packs,
        output_language=output_language,
        frame_pack=frame_pack,
        max_tokens=args.max_tokens,
        allow_cross_language_recall=not args.no_cross_language_recall,
        allow_cross_language_generation=args.allow_cross_language_generation,
        vault_reproject_interval=args.vault_reproject_interval,
        use_salience=not args.no_salience,
        salience_top_k=args.salience_top_k,
        inhibition_threshold=args.inhibition_threshold,
        inner_loop_admissibility=getattr(args, "inner_loop_admissibility", False),
        admissibility_threshold=getattr(args, "admissibility_threshold", 0.0),
        identity_pack=getattr(args, "identity", "") or "",
    )


def _print_identity_packs(use_json: bool) -> int:
    """Print discoverable identity packs.  Returns process exit code."""
    from packs.identity.loader import available_packs

    packs = available_packs()
    if use_json:
        import json as _json
        print(_json.dumps(packs, indent=2, sort_keys=True))
        return 0
    if not packs:
        print("(no identity packs found on default search path)")
        return 0
    pack_w = max(len("pack_id"), max(len(str(p["pack_id"])) for p in packs))
    ver_w = max(len("version"), max(len(str(p["version"])) for p in packs))
    print(f"{'pack_id':<{pack_w}}  {'version':<{ver_w}}  ratified  description")
    print(f"{'-' * pack_w}  {'-' * ver_w}  --------  -----------")
    for p in packs:
        flag = "yes" if p["ratified"] else "no "
        print(
            f"{str(p['pack_id']):<{pack_w}}  "
            f"{str(p['version']):<{ver_w}}  "
            f"{flag:<8}  {p['description']}"
        )
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """Launch a readline REPL backed by ChatRuntime."""
    if getattr(args, "list_identity_packs", False):
        return _print_identity_packs(use_json=getattr(args, "json", False))
    try:
        from chat.runtime import ChatRuntime
        # ADR-0041 — operator-facing verdict readout.  Imported lazily
        # so a broken telemetry module doesn't block REPL startup.
        from chat.telemetry import format_verdict_summary
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)

    runtime = ChatRuntime(config=_runtime_config_from_args(args))
    show_verdicts = bool(getattr(args, "show_verdicts", False))
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            print()
            break
        if text in {"quit", "exit"}:
            break
        if not text:
            continue
        try:
            response = runtime.chat(text)
        except (KeyError, ValueError) as exc:
            print(f"[{exc}]", file=sys.stderr)
            continue
        print(response.surface)
        if show_verdicts:
            # ADR-0041 — print the verdict bundle to stderr so the
            # response surface on stdout stays parseable by tooling
            # that pipes through ``core chat``.
            summary = format_verdict_summary(response.verdicts)
            if summary:
                print(summary, file=sys.stderr)
    return 0


def _pytest_args_for_suite(suite: str, extra_args: Sequence[str]) -> list[str]:
    paths = _TEST_SUITES[suite]
    forwarded = list(extra_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    return [*paths, *forwarded]


def cmd_test(args: argparse.Namespace) -> int:
    """Run pytest through curated suite aliases or direct passthrough args."""
    default_args = ["-q", "--tb=short"]
    if args.list_suites:
        for name in sorted(_TEST_SUITES):
            print(name)
        return 0
    if args.suite:
        forwarded = _pytest_args_for_suite(args.suite, args.args or default_args)
    else:
        forwarded = list(args.args or default_args)
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
    return _run(sys.executable, "-m", "pytest", *forwarded)


def cmd_check(args: argparse.Namespace) -> int:
    """Run ruff over selected project paths."""
    targets = args.paths or [
        "algebra",
        "alignment",
        "chat",
        "core",
        "field",
        "generate",
        "ingest",
        "language_packs",
        "morphology",
        "persona",
        "sensorium",
        "session",
        "vault",
        "vocab",
        "tests",
    ]
    return _run(sys.executable, "-m", "ruff", "check", *targets)


def _runtime_for_trace(args: argparse.Namespace):
    try:
        from chat.runtime import ChatRuntime
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)
    try:
        return ChatRuntime(config=_runtime_config_from_args(args))
    except Exception as exc:
        _die(
            "failed to initialize ChatRuntime. Check mounted language packs with "
            "`core pack list` and `core pack verify <pack_id>`. Root cause: "
            f"{exc.__class__.__name__}: {exc}",
            code=1,
        )


def _trace_payload(text: str, resp: Any, runtime: Any) -> dict[str, Any]:
    proposition = resp.proposition
    articulation = resp.articulation
    vault = runtime.session.vault
    payload: dict[str, Any] = {
        "input": text,
        "surface": resp.surface,
        "walk_surface": resp.walk_surface,
        "output_language": resp.output_language,
        "frame_pack": resp.frame_pack,
        "dialogue_role": str(resp.dialogue_role),
        "versor_condition": float(resp.versor_condition),
        "salience_top_k": resp.salience_top_k,
        "candidates_used": resp.candidates_used,
        "articulation": {
            "surface": articulation.surface,
            "frame_id": articulation.frame_id,
            "subject": articulation.subject,
            "predicate": articulation.predicate,
            "object": articulation.object,
            "output_language": articulation.output_language,
        },
        "proposition": {
            "surface": proposition.surface,
            "frame_id": proposition.frame_id,
            "subject": proposition.subject,
            "predicate": proposition.predicate,
            "object": proposition.object_,
            "relation_norm": proposition.relation_norm,
        },
        "vault_entries": len(vault),
        "vault_reproject_every": vault.reproject_interval,
        "vault_store_count": vault.store_count,
        "oov_grounded": list(getattr(runtime.session.vocab, "unknown_token_log", [])),
    }
    return payload


def _print_trace(payload: dict[str, Any]) -> None:
    print(f"input          : {payload['input']}")
    print(f"surface        : {payload['surface']}")
    print(f"raw_walk       : {payload['walk_surface']}")
    print(f"output_language: {payload['output_language']}")
    print(f"frame_pack     : {payload['frame_pack']}")
    print(f"salience_top_k : {payload['salience_top_k']}")
    print(f"candidates_used: {payload['candidates_used']}")
    print(f"dialogue_role  : {payload['dialogue_role']}")
    print(f"versor_cond    : {payload['versor_condition']:.2e}")
    articulation = payload["articulation"]
    print(f"articulation   : {articulation['surface']!r}")
    print(f"  subject      : {articulation['subject']!r}")
    print(f"  predicate    : {articulation['predicate']!r}")
    if articulation.get("object"):
        print(f"  object       : {articulation['object']!r}")
    proposition = payload["proposition"]
    print(f"proposition    : {proposition['surface']!r}")
    print(f"  frame_id     : {proposition['frame_id']}")
    print(f"  subject      : {proposition['subject']!r}")
    print(f"  predicate    : {proposition['predicate']!r}")
    if proposition.get("object"):
        print(f"  object       : {proposition['object']!r}")
    print(f"  relation_norm: {proposition['relation_norm']:.4f}")
    print(f"vault_entries  : {payload['vault_entries']}")
    print(f"vault_reproject_every: {payload['vault_reproject_every']}")
    print(f"vault_store_count    : {payload['vault_store_count']}")
    oov_entries = payload["oov_grounded"]
    if oov_entries:
        print(f"oov_grounded   : {len(oov_entries)} token(s)")
        for entry in oov_entries:
            print(f"  {entry}")


def cmd_trace(args: argparse.Namespace) -> int:
    """Trace one chat turn and print field telemetry."""
    text = " ".join(args.text).strip()
    if not text:
        _die("trace requires input text. Try: core trace \"word beginning truth\"")

    runtime = _runtime_for_trace(args)
    try:
        response = runtime.chat(text, max_tokens=args.max_tokens)
    except Exception as exc:
        _die(f"trace failed: {exc.__class__.__name__}: {exc}", code=1)

    payload = _trace_payload(text, response, runtime)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_trace(payload)
    return 0


def cmd_oov(args: argparse.Namespace) -> int:
    """Ground a single unknown token and show constructed versor info."""
    try:
        from algebra.versor import versor_condition
        from chat.runtime import ChatRuntime
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)

    runtime = ChatRuntime(config=_runtime_config_from_args(args))
    vocab = runtime.session.vocab

    try:
        versor = vocab.get_versor(args.token)
    except KeyError:
        from ingest.gate import inject

        state = inject([args.token], vocab)
        print(f"{args.token!r} — grounded as transient")
        print(f"  versor_cond : {versor_condition(state.F):.2e}")
        oov_log = getattr(vocab, "unknown_token_log", [])
        if oov_log:
            last = oov_log[-1]
            print(f"  root_used   : {last.get('root_used', '?')}")
            print(f"  ops_applied : {last.get('operators_applied', [])}")
    else:
        print(f"{args.token!r} is already in the manifold")
        print(f"  versor_cond: {versor_condition(versor):.2e}")
    return 0


def cmd_pack_list(args: argparse.Namespace) -> int:
    """List compiled language packs."""
    from language_packs import list_packs

    packs = list_packs()
    if not packs:
        print("no compiled packs found")
        return 0
    for pack_id in packs:
        print(pack_id)
    return 0


def cmd_pack_verify(args: argparse.Namespace) -> int:
    """Verify one language pack checksum."""
    return _run(sys.executable, "-m", "language_packs", "verify", args.pack_id)


def _safe_pack_id(pack_id: str) -> str:
    """Reject pack IDs containing path traversal or separator characters."""
    if not pack_id:
        _die("pack_id is required", code=2)

    path = Path(pack_id)

    if path.is_absolute():
        _die("pack_id must not be an absolute path", code=2)

    if pack_id in {".", ".."}:
        _die("pack_id must name a pack, not a relative path", code=2)

    if any(part in {"", ".", ".."} for part in path.parts):
        _die("pack_id must not contain path traversal", code=2)

    if "/" in pack_id or "\\" in pack_id:
        _die("pack_id must be a simple pack id, not a path", code=2)

    return pack_id


def cmd_pack_validate(args: argparse.Namespace) -> int:
    """Run executable source-pack validation gates."""
    pack_id = _safe_pack_id(args.pack_id)
    pack_dir = _REPO_ROOT / "packs" / pack_id
    validator_path = pack_dir / "validators.py"

    if not validator_path.exists():
        _die(f"source-pack validator not found: {validator_path}", code=1)

    if getattr(args, "dry_run", False):
        if args.json:
            print(json.dumps({
                "pack_id": pack_id,
                "validator_path": str(validator_path),
                "would_execute": False,
                "exists": True,
            }, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"dry-run: pack_id={pack_id}")
            print(f"validator: {validator_path}")
            print("status: validator exists, would not execute")
        return 0

    if not getattr(args, "allow_arbitrary_code", False):
        _die(
            "dynamic validator execution requires --allow-arbitrary-code",
            code=2,
        )

    import importlib.util

    spec = importlib.util.spec_from_file_location(f"{pack_id}_validators", validator_path)
    if spec is None or spec.loader is None:
        _die(f"cannot load source-pack validator: {validator_path}", code=1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.validate_pack()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"pack_id: {report['pack_id']}")
        print(f"active : {report['active']}")
        for name, result in report["gates"].items():
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} {name:<12} {result['reason']}")
    return 0 if report["active"] else 1


def _print_rust_status() -> bool:
    from algebra.backend import using_rust

    active = using_rust()
    print(f"core_rs crate : {_CORE_RS_DIR}")
    print(f"cargo manifest: {_CORE_RS_MANIFEST}")
    print(f"rust backend  : {'active' if active else 'inactive'}")
    if active:
        import core_rs

        print(f"core_rs module: {getattr(core_rs, '__file__', '<built-in>')}")
    else:
        print("activation    : run `core rust build`")
    return active


def cmd_rust_status(args: argparse.Namespace) -> int:
    """Print Rust backend activation status."""
    return 0 if _print_rust_status() or not args.require_active else 1


def cmd_rust_build(args: argparse.Namespace) -> int:
    """Build/install core_rs into the active Python environment."""
    if not _CORE_RS_MANIFEST.exists():
        _die(f"core-rs manifest not found: {_CORE_RS_MANIFEST}", code=1)
    if shutil.which("uv") is not None:
        rc = _run("uv", "pip", "install", "maturin")
        if rc != 0:
            return rc
    cmd = [
        sys.executable,
        "-m",
        "maturin",
        "develop",
        "--release",
        "--manifest-path",
        str(_CORE_RS_MANIFEST),
    ]
    if args.skip_auditwheel:
        cmd.append("--skip-auditwheel")
    return _run(*cmd)


def cmd_rust_test(args: argparse.Namespace) -> int:
    """Run Rust crate tests."""
    if shutil.which("cargo") is None:
        _die("cargo not found. Install a Rust toolchain first.", code=1)
    return _run("cargo", "test", "--release", cwd=_CORE_RS_DIR)


def cmd_doctor(args: argparse.Namespace) -> int:
    """Inspect import/package health for the CLI runtime path."""
    checks = [
        ("algebra", "algebra"),
        ("alignment", "alignment.graph"),
        ("chat", "chat.runtime"),
        ("language_packs", "language_packs"),
        ("morphology", "morphology.registry"),
        ("sensorium", "sensorium.protocol"),
    ]
    ok = True
    print(f"repo_root: {_REPO_ROOT}")
    for label, module_name in checks:
        try:
            __import__(module_name)
        except Exception as exc:
            ok = False
            print(f"FAIL {label:<14} {module_name}: {exc.__class__.__name__}: {exc}")
        else:
            print(f"OK   {label:<14} {module_name}")

    if args.packs:
        try:
            from language_packs import list_packs

            packs = list_packs()
        except Exception as exc:
            ok = False
            print(f"FAIL packs          language_packs.list_packs: {exc.__class__.__name__}: {exc}")
        else:
            print("packs:")
            if packs:
                for pack_id in packs:
                    print(f"  {pack_id}")
            else:
                print("  none found")
    if args.rust:
        rust_active = _print_rust_status()
        if args.require_rust and not rust_active:
            ok = False
    return 0 if ok else 1


def cmd_eval(args: argparse.Namespace) -> int:
    """Run an eval lane by name, or list available lanes."""
    from evals.framework import discover_lanes, get_lane, run_lane, write_result

    if args.list_lanes:
        lanes = discover_lanes()
        if not lanes:
            print("no eval lanes found")
        for lane in lanes:
            versions = ", ".join(lane.versions) if lane.versions else "none"
            print(f"  {lane.name:20s}  versions: {versions}")
        return 0

    lane_name = args.lane
    if not lane_name:
        _die("eval requires a lane name. Use `core eval --list` to see available lanes.")

    try:
        lane = get_lane(lane_name)
    except FileNotFoundError as exc:
        _die(str(exc))

    version = args.version or (lane.versions[0] if lane.versions else "v1")
    split = args.split

    try:
        result = run_lane(lane, version=version, split=split)
    except FileNotFoundError as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"lane           : {result.lane}")
        print(f"version        : {result.version}")
        print(f"split          : {result.split}")
        print(f"cases          : {result.metrics.get('total', 0)}")
        for key, value in result.metrics.items():
            if key == "total":
                continue
            if isinstance(value, float):
                print(f"{key:15s}: {value:.1%}")
            else:
                print(f"{key:15s}: {value}")
        failures = [c for c in result.case_details if not c.get("intent_correct") or not c.get("versor_closure")]
        if failures:
            print(f"\nfailures ({len(failures)}):")
            for c in failures:
                issues = []
                if not c.get("intent_correct"):
                    issues.append("intent")
                if not c.get("versor_closure"):
                    vc = c.get("versor_condition", 0)
                    issues.append(f"versor={vc:.2e}")
                cid = c.get("case_id") or c.get("id") or "<unknown>"
                print(f"  {cid}: {', '.join(issues)}")

    if args.save:
        result_path = write_result(lane, result)
        print(f"\nresult written: {result_path}", file=sys.stderr)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        )
        print(f"\nreport written: {report_path}", file=sys.stderr)

    return 0


def cmd_pulse(args: argparse.Namespace) -> int:
    """Run a cognitive pulse and display recalled words + realized surface."""
    from scripts.run_pulse import run_pulse

    text = " ".join(args.text) if args.text else "What is truth?"
    result = run_pulse(
        text,
        top_k=args.top_k,
        use_glove=not args.no_glove,
        use_correction=not args.no_correction,
        correction_rate=args.correction_rate,
    )

    if args.json:
        import json as _json
        print(_json.dumps({
            "prompt": text,
            "recalled_words": list(result.recalled_words),
            "surface": result.surface,
            "steps": result.steps,
            "converged": result.converged,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\nsurface: {result.surface}")
        print(f"steps  : {result.steps}  converged: {result.converged}")

    return 0


_DEMO_RESULTS_DIR = Path("evals/forward_semantic_control/results")
_DEMO_CORPUS_DIR = Path("evals/forward_semantic_control/public")


_PHASE5_PREAMBLE = """
================================================================================
  Phase 5 Demo — Stratified Mechanism-Isolation
================================================================================

WHAT THIS DEMO TESTS
  CORE's inner-loop admissibility mechanism is supposed to behave correctly
  across five distinct geometric failure modes — not just on average, but
  per-family. This demo runs a hand-curated 20-case corpus that stratifies
  the chain's behaviour across those five families:

    A. near_forbidden_correct_endpoint  Expected and forbidden tokens have
                                        nearly equal blade-scores. Tests
                                        margin sensitivity at the boundary.
    B. near_equal_admissible            Two admissible candidates with
                                        near-identical scores. Tests the
                                        margin gate's determinism under tie.
    C. no_admissible_path               All candidates score ≤ 0 against the
                                        blade. Tests honest refusal.
    D. multi_step_admissibility         Chained Family-A configurations.
                                        Tests step-to-step composition.
    E. heterogeneous_relation           Chained steps with DIFFERENT blades.
                                        Tests blade-switching cleanliness.

  Each case is run under TWO modes:
    threshold mode  (ADR-0024 — per-case static admissibility_threshold)
    margin mode     (ADR-0026 — scale-invariant δ-margin, δ=0.4 default)

WHAT TO EXPECT IF THE MECHANISM IS WORKING
  - Overall pass_rate (threshold) = 100%
  - Overall pass_rate (margin)    = 100%
  - mechanism_isolated (both modes) = True
  - Per-family pass_rate = 100% for ALL five families
  - Family B refusal_rate (margin) = 100% (near-equal candidates must
    refuse under δ-margin by construction)
  - Family C refusal_rate (both modes) = 100% (no admissible path)

WHAT TO LOOK FOR
  - If any family's pass_rate < 100%, the mechanism failed THAT family
    specifically — not a general regression. Dig into the per-case
    detail in the report JSON to see which case and what selection.
  - If Family B does NOT refuse under margin mode, the δ gate has
    silently broken — check generate/admissibility.py::check_margin.
  - If Family C admits anything, honest refusal has regressed — check
    generate/exhaustion.py and the InnerLoopExhaustion raise sites in
    generate/stream.py.

WHEN TO TWEAK
  - δ = 0.4 (the margin default) is FALSIFIABLE: if a case surfaces a
    blade-gap below δ where margin-mode refusal is the WRONG behaviour,
    that is an architectural finding to REPORT in
    docs/evals/phase5_stratified_findings.md, NOT a value to patch.
  - Adding new failure-mode families requires editing
    evals/forward_semantic_control/phase5_runner.py::_passed_single
    and authoring stratified cases in
    evals/forward_semantic_control/public/v2_phase5/cases.jsonl.
================================================================================
"""

_PHASE6_PREAMBLE = """
================================================================================
  Phase 6 Demo — Comparative Demo: CORE vs In-System Baseline
================================================================================

WHAT THIS DEMO TESTS
  Three head-to-head claims about what CORE adds OVER an in-system baseline
  (the same codebase with inner-loop / margin / rotor admissibility DISABLED
  — i.e. an ADR-0023 ablation). Each claim is run on a focused 8-case
  corpus and pinned by 17 CI contract tests:

    C1 Replay determinism   Both baseline AND CORE produce byte-identical
                            trace hashes across 5 reruns. CORE additionally
                            folds refusal_reason into trace_hash, so refusal
                            events themselves are replayable evidence.

    C2 Traced rejection     On adversarial cases where the boundary picks
                            the forbidden token: baseline emits it (with
                            admitted=False, silent emit). CORE overrides
                            and the rejection appears in rejected_attempts.

    C3 Coherent refusal     On no-admissible-path cases: baseline emits an
                            inadmissible candidate. CORE raises
                            InnerLoopExhaustion with a typed RefusalReason.

WHY THE BASELINE IS IN-SYSTEM (NOT AN LLM)
  A transformer-LLM comparison would be non-deterministic, could not be
  CI-enforced, and would be apples-to-oranges (different corpus / training
  / sampling). The honest comparison is the ablation: same code, same
  field state, same vocab, same persona — only the Phase 2-5 mechanisms
  toggled off. Anything CORE produces that the baseline does not produce
  is therefore attributable to the mechanisms themselves.

WHAT TO EXPECT IF EVERYTHING IS WORKING
  - C1: BOTH baseline_stable AND CORE_stable = 8/8 (replay is preserved,
    not added, by Phase 2-5)
  - C2: baseline_emits_forbidden = 3/3, baseline_admits_forbidden = 0/3
        CORE_corrects_or_refuses = 3/3, CORE_rejection_in_trace = 3/3
  - C3: baseline_typed_refusals = 0/3, baseline_emits_inadmissible = 3/3
        CORE_typed_refusals = 3/3
  - ALL THREE CONDITIONS = PASS

WHAT TO LOOK FOR
  - If C1 baseline fails, the algebra layer's replay has regressed —
    unrelated to the chain. Investigate algebra/ first.
  - If C1 CORE fails but baseline holds, the trace fold or refusal
    plumbing has broken determinism. Check trace.py + exhaustion.py.
  - If C2 baseline_admits_forbidden > 0, the boundary-only gate is
    accidentally admitting things — unrelated to the chain, but worth
    investigating.
  - If C3 baseline_typed_refusals > 0, baseline is somehow raising
    InnerLoopExhaustion — investigate whether inner_loop_admissibility
    actually got disabled in the ablation.
  - If C3 CORE_typed_refusals < case_count, CORE is NOT refusing where
    it should — the honest-refusal contract has regressed.

WHEN TO TWEAK
  - If a C2/C3 case stops surfacing the intended baseline failure mode
    (e.g. boundary stops picking the forbidden), it has aged out — the
    cure is to add a NEW case that surfaces the failure, NOT to relax
    the predicate. See docs/evals/phase6_comparative_demo.md.
================================================================================
"""

_ALL_PREAMBLE = """
================================================================================
  Combined Demo — Full ADR-0024 Chain Evidence
================================================================================

This runs BOTH Phase 5 (stratified mechanism-isolation, 20 cases, 5 failure-
mode families, threshold + margin modes) AND Phase 6 (three-condition head-
to-head vs in-system baseline, 8 cases). A combined summary line at the end
reports the chain's overall verdict.

For a thorough explanation of each phase, run them individually:
  core demo phase5
  core demo phase6

For the central evidence index:
  core demo list-results
================================================================================
"""


def _print_preamble(text: str) -> None:
    """Print a demo preamble to stdout (suppressed under --json)."""
    print(text)


def _format_phase5_table(metrics: dict[str, Any], per_family: dict[str, Any]) -> str:
    lines = [
        "",
        "Phase 5 — Stratified Mechanism-Isolation (ADR-0024 / ADR-0026)",
        "=" * 68,
        f"  cases:                     {metrics.get('case_count', 0)}",
        f"  margin (δ):                {metrics.get('margin', 0)}",
        f"  pass_rate (threshold):     {metrics.get('pass_rate_threshold', 0):.2%}",
        f"  pass_rate (margin):        {metrics.get('pass_rate_margin', 0):.2%}",
        f"  mechanism_isolated (thr):  {metrics.get('mechanism_isolated_threshold', False)}",
        f"  mechanism_isolated (mgn):  {metrics.get('mechanism_isolated_margin', False)}",
        "",
        f"  {'family':38s} {'cases':>6s} {'pass(thr)':>11s} {'pass(mgn)':>11s} {'refuse(mgn)':>13s}",
        "  " + "-" * 84,
    ]
    for fam, b in per_family.items():
        lines.append(
            f"  {fam:38s} {b.get('case_count', 0):>6d} "
            f"{b.get('pass_rate_threshold', 0):>10.2%} "
            f"{b.get('pass_rate_margin', 0):>10.2%} "
            f"{b.get('refusal_rate_margin', 0):>12.2%}"
        )
    return "\n".join(lines) + "\n"


def _format_phase6_table(metrics: dict[str, Any]) -> str:
    def pf(b: bool) -> str:
        return "PASS" if b else "FAIL"
    lines = [
        "",
        "Phase 6 — Comparative Demo: CORE vs In-System Baseline (ADR-0023 ablation)",
        "=" * 76,
        f"  total cases:                  {metrics.get('case_count', 0)}",
        f"  replay reruns:                {metrics.get('replay_reruns', 0)}",
        "",
        "  C1 Replay determinism",
        f"    baseline stable:            {metrics.get('c1_replay_stable_baseline', 0)} / {metrics.get('c1_eligible', 0)}",
        f"    CORE stable:                {metrics.get('c1_replay_stable_core', 0)} / {metrics.get('c1_eligible', 0)}",
        f"    verdict:                    {pf(metrics.get('c1_pass', False))}",
        "",
        "  C2 Traced rejection",
        f"    baseline emits forbidden:   {metrics.get('c2_baseline_emits_forbidden', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    baseline admits forbidden:  {metrics.get('c2_baseline_admits_forbidden', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    CORE corrects-or-refuses:   {metrics.get('c2_core_corrects_or_refuses', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    CORE rejection in trace:    {metrics.get('c2_core_rejection_traced', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    verdict:                    {pf(metrics.get('c2_pass', False))}",
        "",
        "  C3 Coherent refusal",
        f"    baseline typed refusals:    {metrics.get('c3_baseline_refused_typed', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    baseline emits inadmiss.:   {metrics.get('c3_baseline_emitted_inadmissible', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    CORE typed refusals:        {metrics.get('c3_core_refused_typed', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    verdict:                    {pf(metrics.get('c3_pass', False))}",
        "",
        f"  ALL THREE CONDITIONS:         {pf(metrics.get('all_three_conditions_pass', False))}",
    ]
    return "\n".join(lines) + "\n"


def _write_results_index() -> Path:
    """Write/refresh the results index manifest.

    Lists every ``*_report.json`` in the results directory with its
    headline metric (or a short summary).  Reviewers can read this to
    discover all available evidence in one place.
    """
    results_dir = _DEMO_RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for p in sorted(results_dir.glob("*.json")):
        if p.name == "index.json":
            continue
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
        entries.append({
            "file": p.name,
            "size_bytes": p.stat().st_size,
            "headline": {
                k: v for k, v in metrics.items()
                if k in (
                    "case_count", "pass_rate", "pass_rate_threshold",
                    "pass_rate_margin", "mechanism_isolated",
                    "mechanism_isolated_threshold", "mechanism_isolated_margin",
                    "all_three_conditions_pass", "c1_pass", "c2_pass", "c3_pass",
                    "best_threshold", "best_separation_quality",
                )
            },
        })
    index_path = results_dir / "index.json"
    index_path.write_text(json.dumps({
        "results_dir": str(results_dir),
        "reports": entries,
    }, indent=2))
    return index_path


def _run_demo_phase5(emit_json: bool, *, with_preamble: bool = True) -> dict[str, Any]:
    from evals.forward_semantic_control.phase5_runner import run_lane
    if with_preamble and not emit_json:
        _print_preamble(_PHASE5_PREAMBLE)
    cases_path = _DEMO_CORPUS_DIR / "v2_phase5" / "cases.jsonl"
    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    report = run_lane(cases)
    out = _DEMO_RESULTS_DIR / "phase5_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "metrics": report.metrics,
        "per_family": report.per_family,
        "case_details": report.case_details,
    }, indent=2))
    if emit_json:
        print(json.dumps({"metrics": report.metrics, "per_family": report.per_family}, indent=2))
    else:
        print(_format_phase5_table(report.metrics, report.per_family))
        print(f"  full report: {out}")
    return report.metrics


def _run_demo_phase6(emit_json: bool, *, with_preamble: bool = True) -> dict[str, Any]:
    from evals.forward_semantic_control.phase6_demo import run_lane
    if with_preamble and not emit_json:
        _print_preamble(_PHASE6_PREAMBLE)
    cases_path = _DEMO_CORPUS_DIR / "v2_phase6_demo" / "cases.jsonl"
    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    report = run_lane(cases)
    out = _DEMO_RESULTS_DIR / "phase6_demo_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "metrics": report.metrics,
        "case_details": report.case_details,
    }, indent=2))
    if emit_json:
        print(json.dumps({"metrics": report.metrics}, indent=2))
    else:
        print(_format_phase6_table(report.metrics))
        print(f"  full report: {out}")
    return report.metrics


def cmd_demo(args: argparse.Namespace) -> int:
    """Run the ADR-0024 chain comparative demos for investors / reviewers."""
    target = args.target
    if target == "list-results":
        index_path = _write_results_index()
        data = json.loads(index_path.read_text())
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\nresults directory: {data['results_dir']}\n")
            for entry in data["reports"]:
                print(f"  {entry['file']:55s}  {entry['size_bytes']:>9d} bytes")
                for k, v in entry["headline"].items():
                    print(f"    {k}: {v}")
        return 0

    if target == "phase5":
        _run_demo_phase5(args.json)
    elif target == "phase6":
        _run_demo_phase6(args.json)
    elif target == "all":
        if not args.json:
            _print_preamble(_ALL_PREAMBLE)
        p5 = _run_demo_phase5(args.json)
        p6 = _run_demo_phase6(args.json)
        if not args.json:
            print("\n" + "=" * 76)
            print("Combined demo summary")
            print("=" * 76)
            print(f"  Phase 5 pass_rate (margin):    {p5.get('pass_rate_margin', 0):.2%}")
            print(f"  Phase 5 mechanism_isolated:    {p5.get('mechanism_isolated_margin', False)}")
            print(f"  Phase 6 all three conditions:  {p6.get('all_three_conditions_pass', False)}")
            print("")
            print("  What this means:")
            print("    Phase 5 verifies CORE handles five distinct geometric")
            print("    failure modes correctly under both threshold and margin gates.")
            print("    Phase 6 verifies CORE adds three capabilities the in-system")
            print("    baseline cannot exhibit: deterministic replay of refusals,")
            print("    traced rejection of inadmissible candidates, and coherent")
            print("    typed refusal when no admissible path exists.")
            print("    Together they are the load-bearing claim of the ADR-0024 chain.")
            print("")
    else:
        _die(f"unknown demo target: {target}")

    _write_results_index()
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Run benchmark harness."""
    # "cost" suite has its own runtime contract — wall/CPU-seconds and
    # $/1000-turns derivation.  Dispatch separately so the report
    # structure stays honest (no fake PASS/FAIL on a measurement bench).
    if args.suite == "cost":
        from benchmarks.cost import run_cost, write_report
        report = run_cost(turns=args.runs)
        if args.json:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(report.summary())
        if args.report:
            write_report(report, root=Path(args.report).parent)
        else:
            write_report(report)
        return 0

    from benchmarks.run_benchmarks import run_benchmarks

    report = run_benchmarks(
        suite=args.suite,
        runs=args.runs,
    )

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        for r in report.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name:25s}  {r.metric:>12.4f} {r.unit}")
            print(f"         {r.detail}")
        all_pass = all(r.passed for r in report.results)
        print(f"\n{'ALL PASSED' if all_pass else 'FAILURES DETECTED'}")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
        )
        print(f"report written: {report_path}")

    return 0 if all(r.passed for r in report.results) else 1


def _add_runtime_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack", action="append", help="language pack to mount; repeat for multiple packs")
    parser.add_argument("--output-language", default="en", help="target output language code; default: en")
    parser.add_argument("--frame-pack", help="frame pack to use; defaults to output language")
    parser.add_argument("--max-tokens", type=int, default=32, help="maximum generated tokens; default: 32")
    parser.add_argument("--vault-reproject-interval", type=int, default=20, help="vault null-cone reprojection cadence; default: 20 stores")
    parser.add_argument("--salience-top-k", type=int, default=16, help="salience candidate budget; default: 16")
    parser.add_argument("--inhibition-threshold", type=float, default=0.3, help="attention inhibition threshold; default: 0.3")
    parser.add_argument(
        "--inner-loop-admissibility",
        action="store_true",
        help="enable ADR-0024 per-rotor inner-loop admissibility (re-select on rejection)",
    )
    parser.add_argument(
        "--admissibility-threshold",
        type=float,
        default=0.0,
        help="inner-loop admissibility score threshold; default: 0.0",
    )
    parser.add_argument("--no-salience", action="store_true", help="disable salience attention and use full-manifold generation")
    parser.add_argument(
        "--allow-cross-language-generation",
        action="store_true",
        help="allow generated walk tokens from any mounted language",
    )
    parser.add_argument(
        "--no-cross-language-recall",
        action="store_true",
        help="disable vault recall during generation",
    )
    parser.add_argument(
        "--identity",
        default="",
        metavar="PACK_ID",
        help="identity pack id to load (default: default_general_v1); see "
        "docs/identity_packs.md",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="core",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", dest="print_version", help="print package version and exit")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    chat = subparsers.add_parser("chat", help="start the interactive chat REPL")
    _add_runtime_policy_args(chat)
    chat.add_argument(
        "--list-identity-packs",
        action="store_true",
        help="list discoverable identity packs and exit (no REPL launched)",
    )
    chat.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON (with --list-identity-packs)",
    )
    chat.add_argument(
        "--show-verdicts",
        action="store_true",
        help=(
            "after each turn, print the TurnVerdicts bundle summary to "
            "stderr (ADR-0041 operator-facing audit readout)"
        ),
    )
    chat.set_defaults(func=cmd_chat)

    test = subparsers.add_parser("test", help="run pytest with curated suite aliases or direct passthrough")
    test.add_argument("--suite", choices=sorted(_TEST_SUITES), help="curated suite alias to run")
    test.add_argument("--list-suites", action="store_true", help="list curated test suite aliases and exit")
    test.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to pytest")
    test.set_defaults(func=cmd_test)

    check = subparsers.add_parser("check", help="run ruff check")
    check.add_argument("paths", nargs="*", help="optional paths to check")
    check.set_defaults(func=cmd_check)

    trace = subparsers.add_parser(
        "trace",
        help="trace one chat turn with field telemetry",
        description="trace one chat turn with field telemetry",
    )
    _add_runtime_policy_args(trace)
    trace.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    trace.add_argument("text", nargs=argparse.REMAINDER, help="input text to trace")
    trace.set_defaults(func=cmd_trace)

    oov = subparsers.add_parser("oov", help="ground or inspect one token")
    _add_runtime_policy_args(oov)
    oov.add_argument("token", help="token to inspect or ground")
    oov.set_defaults(func=cmd_oov)

    pack = subparsers.add_parser("pack", help="inspect and verify language packs")
    pack_sub = pack.add_subparsers(dest="pack_command", metavar="pack-command", required=True)
    pack_list = pack_sub.add_parser("list", help="list compiled packs")
    pack_list.set_defaults(func=cmd_pack_list)
    pack_verify = pack_sub.add_parser("verify", help="verify a pack checksum")
    pack_verify.add_argument("pack_id", help="pack id, e.g. en_minimal_v1")
    pack_verify.set_defaults(func=cmd_pack_verify)
    pack_validate = pack_sub.add_parser("validate", help="validate a source pack under packs/")
    pack_validate.add_argument("pack_id", help="source pack id, e.g. en, he, grc, el")
    pack_validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    pack_validate.add_argument("--dry-run", action="store_true", help="check validator exists without executing")
    pack_validate.add_argument(
        "--allow-arbitrary-code",
        action="store_true",
        help="permit dynamic validator execution (required to run validators)",
    )
    pack_validate.set_defaults(func=cmd_pack_validate)

    rust = subparsers.add_parser(
        "rust",
        help="build, test, and inspect the Rust backend",
        description="build, test, and inspect the Rust backend",
    )
    rust_sub = rust.add_subparsers(dest="rust_command", metavar="rust-command", required=True)
    rust_status = rust_sub.add_parser("status", help="show whether core_rs is active")
    rust_status.add_argument("--require-active", action="store_true", help="exit nonzero if core_rs is inactive")
    rust_status.set_defaults(func=cmd_rust_status)
    rust_build = rust_sub.add_parser("build", help="build/install core_rs with maturin")
    rust_build.add_argument("--skip-auditwheel", action="store_true", help="pass --skip-auditwheel to maturin")
    rust_build.set_defaults(func=cmd_rust_build)
    rust_test = rust_sub.add_parser("test", help="run cargo test --release for core-rs")
    rust_test.set_defaults(func=cmd_rust_test)

    pulse = subparsers.add_parser(
        "pulse",
        help="run a cognitive pulse from injection to realized surface",
        description="run a cognitive pulse from injection to realized surface",
    )
    pulse.add_argument("text", nargs="*", default=["What is truth?"])
    pulse.add_argument("--top-k", type=int, default=5, metavar="N")
    pulse.add_argument("--no-glove", action="store_true", help="use compiled pack only (no GloVe download)")
    pulse.add_argument("--no-correction", action="store_true", help="disable correction (V3 mode)")
    pulse.add_argument("--correction-rate", type=float, default=0.3, metavar="R")
    pulse.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    pulse.set_defaults(func=cmd_pulse)

    bench = subparsers.add_parser(
        "bench",
        help="run benchmark harness (determinism, latency, speedup, versor audit)",
        description="run benchmark harness",
    )
    bench.add_argument("--suite", choices=["determinism", "latency", "speedup", "versor", "convergence", "realizer", "cost"],
                       help="run a specific benchmark suite")
    bench.add_argument("--runs", type=int, default=20, metavar="N", help="run count for determinism benchmark (also turns count for cost suite)")
    bench.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    bench.add_argument("--report", metavar="PATH", help="write JSON report to file")
    bench.set_defaults(func=cmd_bench)

    demo = subparsers.add_parser(
        "demo",
        help="run ADR-0024 chain comparative demos (phase5 / phase6 / all)",
        description=(
            "Run the comparative demo evidence for the ADR-0024 chain.  "
            "Designed for showcasing CORE's deterministic-cognition mechanisms "
            "to reviewers / investors / industry observers."
        ),
    )
    demo.add_argument(
        "target",
        choices=["phase5", "phase6", "all", "list-results"],
        help=(
            "phase5: stratified 5-family mechanism-isolation.  "
            "phase6: 3-condition head-to-head vs in-system baseline.  "
            "all: run both and print a combined summary.  "
            "list-results: index every JSON report in the results directory."
        ),
    )
    demo.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    demo.set_defaults(func=cmd_demo)

    eval_cmd = subparsers.add_parser("eval", help="run eval lanes")
    eval_cmd.add_argument("lane", nargs="?", help="eval lane name (e.g. cognition)")
    eval_cmd.add_argument("--list", dest="list_lanes", action="store_true", help="list available eval lanes")
    eval_cmd.add_argument("--version", help="version to evaluate (default: latest)")
    eval_cmd.add_argument("--split", default="public", choices=["dev", "public"], help="which split to score (default: public)")
    eval_cmd.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    eval_cmd.add_argument("--save", action="store_true", help="write result to lane results/ directory")
    eval_cmd.add_argument("--report", metavar="PATH", help="write JSON report to file")
    eval_cmd.set_defaults(func=cmd_eval)

    from formation.cli import register as _register_formation
    _register_formation(subparsers)

    doctor = subparsers.add_parser("doctor", help="check runtime imports and packaging health")
    doctor.add_argument("--packs", action="store_true", help="also list discovered language packs")
    doctor.add_argument("--rust", action="store_true", help="also show Rust backend activation status")
    doctor.add_argument("--require-rust", action="store_true", help="exit nonzero when --rust shows inactive backend")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def _print_version() -> None:
    try:
        from importlib.metadata import version

        print(version("core-versor"))
    except Exception:
        print("core-versor unknown")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    args, unknown = parser.parse_known_args(raw_args)
    if unknown:
        if getattr(args, "command", None) != "test":
            parser.error(f"unrecognized arguments: {' '.join(unknown)}")
        args.args = [*(getattr(args, "args", None) or ()), *unknown]
    if args.print_version:
        _print_version()
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
