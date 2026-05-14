"""core CLI — single entry point for the versor engine.

Subcommands
-----------
core chat              Start interactive chat session (delegates to python -m chat)
core test [args]       Run pytest suite with sane defaults
core check             Run ruff on the whole project
core trace <text>      Trace one turn: show field condition, dialogue role, proposition
core oov <token>       Ground a single unknown token and show the constructed versor info
core pack list         List mounted language packs
core pack verify <id>  Verify a language pack checksum
"""
from __future__ import annotations

import subprocess
import sys
from typing import NoReturn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True)


def _die(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _usage() -> NoReturn:
    print(__doc__)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_chat(argv: list[str]) -> None:
    """Launch the readline REPL backed by ChatRuntime."""
    _run(sys.executable, "-m", "chat", *argv, check=False)


def cmd_test(argv: list[str]) -> None:
    """Run the pytest suite.  Extra args are forwarded to pytest."""
    default_args = ["-q", "--tb=short"]
    _run(sys.executable, "-m", "pytest", *(argv or default_args), check=False)


def cmd_check(argv: list[str]) -> None:
    """Run ruff over the project source."""
    targets = argv or [
        "algebra", "ingest", "field", "vocab", "vault", "persona",
        "generate", "session", "chat", "core", "language_packs", "tests",
    ]
    _run(sys.executable, "-m", "ruff", "check", *targets, check=False)


def cmd_trace(argv: list[str]) -> None:
    """Trace one chat turn and print field telemetry."""
    if not argv:
        _die("usage: core trace <text>")
    text = " ".join(argv)

    from chat.runtime import ChatRuntime
    rt = ChatRuntime()
    resp = rt.chat(text)

    print(f"input          : {text}")
    print(f"surface        : {resp.surface}")
    print(f"dialogue_role  : {resp.dialogue_role}")
    print(f"versor_cond    : {resp.versor_condition:.2e}")
    p = resp.proposition
    print(f"proposition    : {p.surface!r}")
    print(f"  frame_id     : {p.frame_id}")
    print(f"  subject      : {p.subject_surface!r}")
    print(f"  predicate    : {p.predicate_surface!r}")
    if hasattr(p, "object_surface") and p.object_surface:
        print(f"  object       : {p.object_surface!r}")
    import numpy as np
    print(f"  relation_norm: {float(np.linalg.norm(p.relation)):.4f}")

    session = rt.session
    print(f"vault_entries  : {len(session.vault)}")
    oov = getattr(session.vocab, "unknown_token_log", [])
    if oov:
        print(f"oov_grounded   : {len(oov)} token(s)")
        for entry in oov:
            print(f"  {entry}")


def cmd_oov(argv: list[str]) -> None:
    """Ground a single unknown token and show the constructed versor info."""
    if not argv:
        _die("usage: core oov <token>")
    token = argv[0]

    from chat.runtime import ChatRuntime
    from algebra.versor import versor_condition
    rt = ChatRuntime()
    vocab = rt.session.vocab

    # Try known first
    try:
        v = vocab.get_versor(token)
        print(f"{token!r} is already in the manifold")
        import numpy as np
        print(f"  versor_cond: {versor_condition(v):.2e}")
        return
    except KeyError:
        pass

    # Ground it
    from ingest.gate import inject
    state = inject([token], vocab)

    import numpy as np
    print(f"{token!r} — grounded as transient")
    print(f"  versor_cond : {versor_condition(state.F):.2e}")
    oov_log = getattr(vocab, "unknown_token_log", [])
    if oov_log:
        last = oov_log[-1]
        print(f"  root_used   : {last.get('root_used', '?')}")
        print(f"  ops_applied : {last.get('operators_applied', [])}")


def cmd_pack(argv: list[str]) -> None:
    """Manage language packs."""
    if not argv:
        _die("usage: core pack [list | verify <pack_id>]")

    sub = argv[0]

    if sub == "list":
        from language_packs import list_packs
        packs = list_packs()
        if not packs:
            print("no compiled packs found")
        for pid in packs:
            print(pid)

    elif sub == "verify":
        if len(argv) < 2:
            _die("usage: core pack verify <pack_id>")
        pack_id = argv[1]
        _run(sys.executable, "-m", "language_packs", "verify", pack_id, check=False)

    else:
        _die(f"unknown pack subcommand: {sub!r}")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_COMMANDS = {
    "chat":  cmd_chat,
    "test":  cmd_test,
    "check": cmd_check,
    "trace": cmd_trace,
    "oov":   cmd_oov,
    "pack":  cmd_pack,
}


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        _usage()
    sub = args[0]
    if sub not in _COMMANDS:
        _die(f"unknown subcommand {sub!r}. Try: {', '.join(_COMMANDS)}")
    _COMMANDS[sub](args[1:])


if __name__ == "__main__":
    main()
