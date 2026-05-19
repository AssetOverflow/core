#!/usr/bin/env python3
"""Live probe script — reproducer for notes/live_probe_2026-05-19.txt.

Walks 51 prompts across 13 categories through fresh ChatRuntime()
instances and prints the rendered surfaces.  Deterministic: same code,
same packs, same glosses → byte-identical output every run.

Run:
    uv run python notes/live_probe_2026-05-19.py > /tmp/probe.txt
    diff notes/live_probe_2026-05-19.txt /tmp/probe.txt
        # → no diff (modulo the header comment in the .txt)
"""
from __future__ import annotations

from collections import Counter

from chat.pack_resolver import clear_resolver_cache
from chat.runtime import ChatRuntime


CATEGORIES: dict[str, list[str]] = {
    "Cognition": [
        "What is truth?", "Define knowledge.", "What is memory?",
        "What does meaning mean?", "What is wisdom?",
    ],
    "Speech-act / discourse": [
        "What is a fact?", "What is an idea?", "What is a statement?",
        "What does claim mean?", "Define argument.",
    ],
    "Mental-state": [
        "What is doubt?", "What does believe mean?", "What is the self?",
        "Define mind.", "What is a view?",
    ],
    "Adjectives (attitude)": [
        "What is true?", "What does important mean?", "Define evident.",
        "What is certain?", "What does necessary mean?",
    ],
    "Temporal": [
        "What is now?", "Define moment.", "What is the future?",
        "What does before mean?", "What is time?",
    ],
    "Spatial": [
        "What is here?", "What is a place?", "Define above.",
        "What does between mean?",
    ],
    "Action verbs (infinitive-stripped)": [
        "What is to create?", "What does make mean?", "What is to use?",
        "Define change.",
    ],
    "Quantitative": [
        "What does all mean?", "Define some.", "What is more?",
        "What does enough mean?",
    ],
    "Causation": [
        "What is an effect?", "Define outcome.", "What is a consequence?",
        "What does trigger mean?",
    ],
    "Polarity / frequency": [
        "What is yes?", "What does always mean?", "Define never.",
        "What is maybe?",
    ],
    "Teaching-chain (multi-clause)": [
        "Why is truth important?",
    ],
    "Genuinely OOV (honesty control)": [
        "What is a hypothesis?", "Define javascript.", "What is quasar?",
    ],
    "Cause without teaching chain (deferred SurfaceSelector target)": [
        "How does memory work?", "What causes doubt?",
    ],
}


_TAGS = {
    "pack":     "PACK    ",
    "teaching": "TEACH   ",
    "oov":      "OOV     ",
    "none":     "NONE    ",
    "vault":    "VAULT   ",
    "partial":  "PARTIAL ",
}


def _wrap(surface: str, indent: str = "            ", width: int = 78) -> str:
    out: list[str] = []
    while len(surface) > width:
        cut = surface.rfind(" ", 0, width)
        if cut == -1:
            cut = width
        out.append(f"{indent}{surface[:cut]}")
        surface = surface[cut + 1:]
    if surface:
        out.append(f"{indent}{surface}")
    return "\n".join(out)


def main() -> None:
    clear_resolver_cache()
    source_counts: Counter[str] = Counter()
    total = 0
    for category, prompts in CATEGORIES.items():
        print(f"\n=== {category} ===")
        for prompt in prompts:
            rt = ChatRuntime()
            response = rt.chat(prompt)
            tag = _TAGS.get(
                response.grounding_source,
                response.grounding_source.upper().ljust(8),
            )
            source_counts[response.grounding_source] += 1
            total += 1
            print(f"\n  [{tag}] {prompt}")
            print(_wrap(response.surface))

    print(f"\n\n{'=' * 70}")
    print(f"GROUNDING DISTRIBUTION over {total} prompts:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * count / total
        print(f"  {src:10s} {count:3d}  ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
