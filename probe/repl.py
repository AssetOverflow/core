from __future__ import annotations

from language_packs import load_pack


def field_walk(seed: str, steps: int = 4) -> list[str]:
    _, vocab = load_pack("en_minimal_v1")
    F = vocab.get_versor(seed)
    walk = [seed]
    idx = -1
    for _ in range(steps - 1):
        word, idx = vocab.nearest(F, exclude_idx=idx)
        walk.append(word)
        F = vocab.get_versor(word)
    return walk


def main() -> None:
    while True:
        text = input("> ").strip()
        if text in {"quit", "exit"}:
            break
        try:
            chain = field_walk(text)
            print(f"[field walk: {' → '.join(chain)}]")
        except KeyError:
            print("[unknown token]")


if __name__ == "__main__":
    main()
