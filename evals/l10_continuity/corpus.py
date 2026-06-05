"""The deterministic scripted corpus that drives the L10 continuity soak.

The corpus is a fixed, committed sequence of in-vocabulary natural-language
prompts. Determinism is the point: turn N of a soak is always ``prompt_at(N)``,
so two independent runs over the same N are byte-identical in their inputs, and
a reboot leg replays the exact same tail it would have seen uninterrupted.

There is NO randomness here — "seeded/replayable" means a fixed cycle, not an
RNG. The prompts are hand-picked to be resident in the default cognition packs
so ``ChatRuntime.chat`` never raises ``no in-vocabulary tokens``; the runner
verifies this at turn 0 and fails loudly if a prompt drifts out of vocabulary.
"""

from __future__ import annotations

# A small, fixed ring of in-vocabulary prompts. Each is a complete cognition
# turn the default packs can tokenize and ground (mirrors the inputs used by
# the cognition lane and the ADR-0153 trace-hash tests). The ring is cycled to
# reach an arbitrary soak length; cycling (not appending novelty) is deliberate
# — the soak measures whether *repetition over a long horizon* stays closed,
# deterministic, bounded, and meaningful, not whether novel input is handled.
_BASE_PROMPTS: tuple[str, ...] = (
    "What causes light?",
    "What is a concept?",
    "Hello.",
    "What causes rain?",
    "What is a principle?",
    "What is memory?",
)


def base_prompts() -> tuple[str, ...]:
    """Return the immutable base ring of prompts (a safe copy of the tuple)."""
    return _BASE_PROMPTS


def prompt_at(turn_index: int) -> str:
    """The prompt for a given 0-based turn index, by cycling the base ring.

    Deterministic and total: any non-negative ``turn_index`` maps to exactly
    one base prompt, so the corpus is replayable across runs and reboots.
    """
    if turn_index < 0:
        raise ValueError(f"turn_index must be non-negative, got {turn_index}")
    return _BASE_PROMPTS[turn_index % len(_BASE_PROMPTS)]


def scripted_corpus(n_turns: int) -> tuple[str, ...]:
    """The first ``n_turns`` prompts of the deterministic soak corpus."""
    if n_turns < 0:
        raise ValueError(f"n_turns must be non-negative, got {n_turns}")
    return tuple(prompt_at(i) for i in range(n_turns))
