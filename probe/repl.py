from __future__ import annotations

from chat.runtime import ChatRuntime


def field_walk(seed: str, steps: int = 4) -> list[str]:
    runtime = ChatRuntime()
    injected_terms = runtime.tokenize(seed)
    response = runtime.chat(seed, max_tokens=max(1, steps))
    proposition_terms = [
        response.proposition.subject,
        response.proposition.predicate,
    ]
    if response.proposition.object_ is not None:
        proposition_terms.append(response.proposition.object_)
    walk = [seed, *injected_terms, *proposition_terms, *response.surface.split()]
    return walk[: max(1, steps)]


def main() -> None:
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if text in {"quit", "exit"}:
            break
        try:
            chain = field_walk(text)
            print(f"[field walk: {' -> '.join(chain)}]")
        except KeyError:
            print("[unknown token]")


if __name__ == "__main__":
    main()
