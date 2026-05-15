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
EPILOG = "Examples:\n  core chat\n  core trace \"word beginning truth\"\n  core trace --output-language grc --frame-pack grc --json \"logos\"\n  core rust status\n  core rust build\n  core oov covenant\n  core pack list\n  core pack verify en_minimal_v1\n  core test --suite smoke\n  core test --suite cognition\n  core test -- tests/test_alignment_graph.py -q"

_TEST_SUITES: dict[str, tuple[str, ...]] = {
    "smoke": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_cognitive_turn_pipeline.py",
    ),
    "runtime": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_chat_identity_telemetry.py",
        "tests/test_session_coherence.py",
    ),
    "cognition": (
        "tests/test_intent_proposition_graph.py",
        "tests/test_cognitive_turn_pipeline.py",
        "tests/test_articulation_realizer_v2.py",
    ),
    "teaching": (
        "tests/test_reviewed_teaching_loop.py",
        "tests/test_pipeline_teaching_integration.py",
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
    )


def cmd_chat(args: argparse.Namespace) -> int:
    """Launch a readline REPL backed by ChatRuntime."""
    try:
        from chat.runtime import ChatRuntime
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)

    runtime = ChatRuntime(config=_runtime_config_from_args(args))
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


def cmd_pack_validate(args: argparse.Namespace) -> int:
    """Run executable source-pack validation gates."""
    import importlib.util

    pack_dir = _REPO_ROOT / "packs" / args.pack_id
    validator_path = pack_dir / "validators.py"
    if not validator_path.exists():
        _die(f"source-pack validator not found: {validator_path}", code=1)
    spec = importlib.util.spec_from_file_location(f"{args.pack_id}_validators", validator_path)
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


def _add_runtime_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack", action="append", help="language pack to mount; repeat for multiple packs")
    parser.add_argument("--output-language", default="en", help="target output language code; default: en")
    parser.add_argument("--frame-pack", help="frame pack to use; defaults to output language")
    parser.add_argument("--max-tokens", type=int, default=32, help="maximum generated tokens; default: 32")
    parser.add_argument("--vault-reproject-interval", type=int, default=20, help="vault null-cone reprojection cadence; default: 20 stores")
    parser.add_argument("--salience-top-k", type=int, default=16, help="salience candidate budget; default: 16")
    parser.add_argument("--inhibition-threshold", type=float, default=0.3, help="attention inhibition threshold; default: 0.3")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="core",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="print package version and exit")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    chat = subparsers.add_parser("chat", help="start the interactive chat REPL")
    _add_runtime_policy_args(chat)
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
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.version:
        _print_version()
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
