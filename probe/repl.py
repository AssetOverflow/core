from __future__ import annotations

from language_packs import load_mounted_packs

_TRILINGUAL_PACKS = ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
_SEED_ALIASES = {
    "logos": "λόγος",
    "dabar": "דבר",
    "or": "אור",
    "phos": "φῶς",
    "zoe": "ζωή",
    "arche": "ἀρχή",
    "aletheia": "ἀλήθεια",
}


def field_walk(seed: str, steps: int = 4) -> list[str]:
    vocab = load_mounted_packs(_TRILINGUAL_PACKS)
    surface = _SEED_ALIASES.get(seed.casefold(), seed)
    F = vocab.get_versor(surface)
    walk = [seed] if surface == seed else [seed, surface]
    idx = vocab.index_of(surface)
    for _ in range(max(0, steps - len(walk))):
        word, idx = vocab.nearest(F, exclude_idx=idx)
        walk.append(word)
        F = vocab.get_versor(word)
    return walk


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
            print(f"[field walk: {' → '.join(chain)}]")
        except KeyError:
            print("[unknown token]")


if __name__ == "__main__":
    main()
