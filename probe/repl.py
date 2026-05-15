"""probe/repl.py — Live conversational REPL for the CORE Versor Engine."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections.abc import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from chat.runtime import ChatRuntime


def _make_runtime(max_tokens: int) -> ChatRuntime:
    from core.config import RuntimeConfig
    config = RuntimeConfig(max_tokens=max_tokens)
    return ChatRuntime(config=config)


def field_walk(text: str, steps: int = 6) -> list[str]:
    """Return a deterministic probe walk beginning with the user surface.

    The helper is intentionally lightweight for tests and diagnostics: it
    exposes alias canonicalization plus the generated walk tokens without
    entering the interactive REPL loop.
    """
    runtime = ChatRuntime()
    walk = [text]
    walk.extend(runtime.tokenize(text))
    try:
        response = runtime.chat(text, max_tokens=max(0, steps - len(walk)))
        walk.extend(response.walk_surface.rstrip(".!?;").split())
    except Exception:
        pass
    return walk[: max(1, steps)]


def run_repl(max_tokens: int = 32, verbose: bool = False) -> None:
    runtime = _make_runtime(max_tokens)
    print("CORE Versor Engine — conversational REPL")
    print(f"  max_tokens={max_tokens}  verbose={verbose}")
    print("  Type 'quit' or 'exit' or Ctrl-D to end.")
    print()

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in {"quit", "exit"}:
            break

        try:
            response = runtime.chat(text, max_tokens=max_tokens)
        except Exception as exc:  # noqa: BLE001
            print(f"[error: {exc}]")
            continue

        print(f"[field walk: {' '.join(field_walk(text, steps=min(max_tokens, 8)))}]")
        role_tag = str(response.dialogue_role)
        flag_tag = " [flagged]" if response.flagged else ""
        print(f"CORE ({role_tag}{flag_tag}): {response.surface}")

        if verbose and runtime.turn_log:
            ev = runtime.turn_log[-1]
            print(f"  versor_condition : {ev.versor_condition:.6f}")
            if ev.identity_score is not None:
                print(f"  identity_score   : {ev.identity_score.score:.4f}")
                print(f"  flagged          : {ev.flagged}")
            if ev.elaboration:
                print(f"  elaboration      : {ev.elaboration}")
            print(f"  cycle_cost       : {ev.cycle_cost_total:.4f}")
            print(f"  vault_hits       : {ev.vault_hits}")

        print()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="CORE Versor Engine — conversational REPL",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=32, metavar="N",
        help="Maximum tokens per response (default: 32)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print TurnEvent provenance after each response",
    )
    if argv is None:
        argv = []
    args, _unknown = parser.parse_known_args(list(argv))
    run_repl(max_tokens=args.max_tokens, verbose=args.verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
