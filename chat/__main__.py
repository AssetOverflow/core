from __future__ import annotations

try:
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform optional
    readline = None

from chat.runtime import ChatRuntime

_DIM = "\033[2m"
_RESET = "\033[0m"


def main() -> None:
    runtime = ChatRuntime()
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
            print(f"{_DIM}[{exc}]{_RESET}")
            continue
        print(response.surface)
        print(
            f"{_DIM}[role={response.dialogue_role} "
            f"versor_condition={response.versor_condition:.2e}]{_RESET}"
        )


if __name__ == "__main__":
    main()
