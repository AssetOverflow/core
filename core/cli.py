"""Command line interface for the CORE versor engine."""
from __future__ import annotations

import argparse
import json
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


DESCRIPTION = "CORE versor engine command suite."
EPILOG = "Examples:\n  core chat\n  core trace \"word beginning truth\"\n  core trace --output-language grc --frame-pack grc --json \"logos\"\n  core oov covenant\n  core pack list\n  core pack verify en_minimal_v1\n  core test tests/test_alignment_graph.py -q"


def _run(*args: str, check: bool = False) -> int:
    """Run a child command and return its exit code."""
    completed = subprocess.run(args, check=check, text=True)
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


def cmd_test(args: argparse.Namespace) -> int:
    """Run pytest. Extra args are forwarded unchanged."""
    default_args = ["-q", "--tb=short"]
    return _run(sys.executable, "-m", "pytest", *(args.args or default_args))


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
    import numpy as np

    proposition = resp.proposition
    payload: dict[str, Any] = {
        "input": text,
        "surface": resp.surface,
        "walk_surface": resp.walk_surface,
        "output_language": resp.output_language,
        "frame_pack": resp.frame_pack,
        "dialogue_role": str(resp.dialogue_role),
        "versor_condition": float(resp.versor_condition),
        "proposition": {
            "surface": proposition.surface,
            "frame_id": proposition.frame_id,
            "subject": proposition.subject,
            "predicate": proposition.predicate,
            "object": proposition.object_,
            "relation_norm": float(np.linalg.norm(proposition.relation)),
        },
        "vault_entries": len(runtime.session.vault),
        "oov_grounded": list(getattr(runtime.session.vocab, "unknown_token_log", [])),
    }
    return payload


def _print_trace(payload: dict[str, Any]) -> None:
    print(f"input          : {payload['input']}")
    print(f"surface        : {payload['surface']}")
    print(f"walk_surface   : {payload['walk_surface']}")
    print(f"output_language: {payload['output_language']}")
    print(f"frame_pack     : {payload['frame_pack']}")
    print(f"dialogue_role  : {payload['dialogue_role']}")
    print(f"versor_cond    : {payload['versor_condition']:.2e}")
    proposition = payload["proposition"]
    print(f"proposition    : {proposition['surface']!r}")
    print(f"  frame_id     : {proposition['frame_id']}")
    print(f"  subject      : {proposition['subject']!r}")
    print(f"  predicate    : {proposition['predicate']!r}")
    if proposition.get("object"):
        print(f"  object       : {proposition['object']!r}")
    print(f"  relation_norm: {proposition['relation_norm']:.4f}")
    print(f"vault_entries  : {payload['vault_entries']}")
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
    return 0 if ok else 1


def _add_runtime_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack", action="append", help="language pack to mount; repeat for multiple packs")
    parser.add_argument("--output-language", default="en", help="target output language code; default: en")
    parser.add_argument("--frame-pack", help="frame pack to use; defaults to output language")
    parser.add_argument("--max-tokens", type=int, default=32, help="maximum generated tokens; default: 32")
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

    test = subparsers.add_parser("test", help="run pytest with sane defaults")
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

    doctor = subparsers.add_parser("doctor", help="check runtime imports and packaging health")
    doctor.add_argument("--packs", action="store_true", help="also list discovered language packs")
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
