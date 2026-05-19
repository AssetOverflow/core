"""Conversation demo — layperson-facing chat transcript.

Four scenes that show CORE actually being used, framed as a chat
transcript with plain-English notes between turns.  No metric tables,
no flag jargon — just ``You: …`` / ``CORE: …`` and a short caption
after each turn that explains what just happened.

Scenes:

  1. Pack lookup            — "What is truth?"
                              Shows the system answering from its
                              lexicon, deterministically.

  2. Teaching-chain         — "Walk me through recall."
                              Shows CORE chaining reviewed facts to
                              produce a multi-sentence answer.

  3. Compound prompt        — "What is truth, and why does it matter?"
                              Shows CORE handling both clauses,
                              composing two sub-answers in order.

  4. Cold turn → learn      — "Why does narrative exist?"
                              Shows CORE saying "I haven't learned
                              this yet", an operator teaching it, then
                              the same prompt answered.  The full
                              learning loop in plain English.

Stream mode (default) emits the response word-by-word with a small
inter-word delay so the layperson sees the answer "arriving live".
This is presentation only — the underlying surface is byte-identical
to the non-streamed version, because CORE's articulation path is
deterministic.

``--no-stream`` disables the delay (CI / tests / fast capture).
``--json`` emits a structured report and suppresses all chat output.
"""

from __future__ import annotations

import sys
import textwrap
import time
from dataclasses import dataclass
from typing import Any

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


# ---------------------------------------------------------------------------
# Streaming presentation
# ---------------------------------------------------------------------------


_WORD_DELAY_SECONDS: float = 0.04  # ~25 words/second; conversational pace
_CARET_DELAY_SECONDS: float = 0.012  # per-char delay for the "typed" prompt


def _stream_write(text: str, delay: float = _CARET_DELAY_SECONDS) -> None:
    """Write text to stdout with a per-character delay."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if delay > 0:
            time.sleep(delay)


def _stream_words(text: str, *, prefix: str = "         ", width: int = 60,
                  delay: float = _WORD_DELAY_SECONDS) -> None:
    """Emit ``text`` word-by-word, wrapped to ``width`` after ``prefix``.

    The caller is expected to have already written the first-line
    label (e.g. ``"  CORE:  "``), so no prefix is written on the very
    first line — only on wrapped continuation lines.
    """
    line = ""  # tracks rendered width on current line; caller wrote the label
    first_line = True
    for word in text.split():
        if first_line:
            sep = "" if not line else " "
            candidate_width = len(line) + len(sep) + len(word)
        else:
            sep = "" if not line else " "
            candidate_width = len(line) + len(sep) + len(word)
        if candidate_width > width and line:
            sys.stdout.write("\n")
            sys.stdout.write(prefix)
            line = ""
            first_line = False
            sep = ""
        sys.stdout.write(sep + word)
        sys.stdout.flush()
        line = line + sep + word
        if delay > 0:
            time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _stream_note(text: str, *, prefix: str = "         ← ", width: int = 56) -> None:
    """Emit a plain-English caption after a CORE turn."""
    wrapped = textwrap.fill(
        text,
        width=width,
        initial_indent=prefix,
        subsequent_indent="           ",
    )
    sys.stdout.write("\n")
    for line in wrapped.splitlines():
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        time.sleep(_WORD_DELAY_SECONDS)


def _scene_header(num: int, title: str) -> None:
    sys.stdout.write("\n")
    sys.stdout.write("─" * 64 + "\n")
    sys.stdout.write(f"  Scene {num} — {title}\n")
    sys.stdout.write("─" * 64 + "\n\n")
    sys.stdout.flush()


def _emit_turn(prompt: str, response_text: str, note: str, *, stream: bool) -> None:
    """Render one You/CORE turn with a caption.

    ``stream=True`` adds per-character / per-word delays (live feel).
    ``stream=False`` prints the same layout instantly (CI / tests /
    fast capture).
    """
    if stream:
        sys.stdout.write("  You:   ")
        _stream_write(prompt, _CARET_DELAY_SECONDS)
        sys.stdout.write("\n\n")
        sys.stdout.write("  CORE:  ")
        sys.stdout.flush()
        time.sleep(0.25)  # tiny "thinking" pause
        _stream_words(response_text, prefix="         ", width=58)
        _stream_note(note)
    else:
        sys.stdout.write(f"  You:   {prompt}\n\n")
        wrapped_response = textwrap.fill(
            response_text, width=58,
            initial_indent="         ", subsequent_indent="         ",
        )
        sys.stdout.write(f"  CORE:  {wrapped_response.lstrip()}\n\n")
        wrapped_note = textwrap.fill(
            note, width=56,
            initial_indent="         ← ", subsequent_indent="           ",
        )
        sys.stdout.write(f"{wrapped_note}\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Report shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TurnRecord:
    scene: str
    prompt: str
    surface: str
    grounding_source: str
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "prompt": self.prompt,
            "surface": self.surface,
            "grounding_source": self.grounding_source,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class ConversationReport:
    turns: tuple[TurnRecord, ...]
    learning_loop_closed: bool
    active_corpus_byte_identical: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "turns": [t.as_dict() for t in self.turns],
            "learning_loop_closed": self.learning_loop_closed,
            "active_corpus_byte_identical": self.active_corpus_byte_identical,
        }


# ---------------------------------------------------------------------------
# CORE wrappers
# ---------------------------------------------------------------------------


def _ask(prompt: str, *, planner: bool = True) -> tuple[str, str]:
    rt = ChatRuntime(config=RuntimeConfig(discourse_planner=planner))
    response = rt.chat(prompt)
    return response.surface, response.grounding_source


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def _scene1_pack_lookup(*, show: bool, stream: bool) -> TurnRecord:
    prompt = "What is truth?"
    if show:
        _scene_header(1, "Asking CORE to define a concept")
    surface, grounding = _ask(prompt, planner=False)
    note = (
        "CORE looked this up in its curated lexicon. Every word in the "
        "answer traces to a reviewed source — same answer every time, no "
        "internet, no guessing."
    )
    if show:
        _emit_turn(prompt, surface, note, stream=stream)
    return TurnRecord(
        scene="S1_pack_lookup", prompt=prompt, surface=surface,
        grounding_source=grounding, note=note,
    )


def _scene2_teaching_chain(*, show: bool, stream: bool) -> TurnRecord:
    prompt = "Walk me through recall."
    if show:
        _scene_header(2, "Asking CORE to walk through a concept")
    surface, grounding = _ask(prompt, planner=True)
    note = (
        "The second sentence wasn't memorised — CORE walked a reviewed "
        "teaching chain: recall → reveals → memory. Each hop is a fact "
        "an operator approved."
    )
    if show:
        _emit_turn(prompt, surface, note, stream=stream)
    return TurnRecord(
        scene="S2_teaching_chain", prompt=prompt, surface=surface,
        grounding_source=grounding, note=note,
    )


def _scene3_compound(*, show: bool, stream: bool) -> TurnRecord:
    prompt = "What is truth, and why does it matter?"
    if show:
        _scene_header(3, "Asking CORE a two-part question")
    surface, grounding = _ask(prompt, planner=True)
    note = (
        "CORE split the question at the comma, answered both halves, and "
        "stitched them together in order — every sentence still grounded "
        "in the lexicon or in a reviewed chain."
    )
    if show:
        _emit_turn(prompt, surface, note, stream=stream)
    return TurnRecord(
        scene="S3_compound", prompt=prompt, surface=surface,
        grounding_source=grounding, note=note,
    )


def _scene4_learning_loop(*, show: bool, stream: bool) -> tuple[TurnRecord, TurnRecord, bool, bool]:
    """Cold turn → operator teaches → re-ask.

    Reuses the production learning-loop demo so the underlying
    propose/replay/accept machinery is exactly what ships.
    """
    from evals.learning_loop.run_demo import run_demo as run_loop

    prompt = "Why does narrative exist?"
    if show:
        _scene_header(4, "Teaching CORE something new, then re-asking")
        sys.stdout.write("  (This scene runs CORE's reviewed-learning loop end-to-end:\n")
        sys.stdout.write("   cold turn → operator proposes a chain → safety/replay gate\n")
        sys.stdout.write("   confirms no regression → operator accepts → same prompt is\n")
        sys.stdout.write("   now grounded.  The active corpus on disk is not mutated.)\n\n")
        sys.stdout.flush()

    # Run the real learning-loop demo (suppressed output) to get the
    # before/after surfaces deterministically.
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        ll = run_loop(emit_json=True)

    before_surface = ll["before"]["surface"]
    before_grounding = ll["before"]["grounding_source"]
    after_surface = ll["after"]["surface"]
    after_grounding = ll["after"]["grounding_source"]
    loop_closed = bool(ll["learning_loop_closed"])
    byte_identical = bool(ll["active_corpus_byte_identical"])

    before_note = (
        "CORE refuses to make something up. It says it hasn't learned this "
        "yet and points to where a reviewed chain would help — instead of "
        "fabricating an answer."
    )
    after_note = (
        "An operator reviewed and accepted one new chain "
        "(narrative → reveals → meaning). A replay gate first confirmed it "
        "wouldn't regress anything CORE already knows. Now the same prompt "
        "is answered — with full provenance back to that one accept."
    )

    if show:
        _emit_turn(prompt, before_surface, before_note, stream=stream)
        sys.stdout.write("\n")
        sys.stdout.write("           ┄ ┄ ┄  operator teaches CORE one new fact  ┄ ┄ ┄\n\n")
        sys.stdout.flush()
        if stream:
            time.sleep(0.6)
        _emit_turn(prompt, after_surface, after_note, stream=stream)

    before = TurnRecord(
        scene="S4a_cold_turn", prompt=prompt, surface=before_surface,
        grounding_source=before_grounding, note=before_note,
    )
    after = TurnRecord(
        scene="S4b_after_teaching", prompt=prompt, surface=after_surface,
        grounding_source=after_grounding, note=after_note,
    )
    return before, after, loop_closed, byte_identical


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_demo(*, emit_json: bool = False, stream: bool = True) -> dict[str, Any]:
    """Run all four scenes and return a structured report.

    ``emit_json=True`` suppresses every chat-style print; only the
    final JSON object will be emitted by the caller.  ``stream=False``
    keeps the chat layout but skips the per-character / per-word
    delays (used by tests and ``--no-stream``).
    """
    show = not emit_json
    actual_stream = show and stream

    if show:
        sys.stdout.write("\n")
        sys.stdout.write("═" * 64 + "\n")
        sys.stdout.write("  Conversation with CORE — live walkthrough\n")
        sys.stdout.write("═" * 64 + "\n")
        sys.stdout.write(
            "\n  CORE is a deterministic cognitive engine. It doesn't run\n"
            "  an LLM, it doesn't sample, it doesn't search the web. Every\n"
            "  word in every answer below traces to a reviewed source.\n"
            "  Run this demo twice — you'll get the same surfaces.\n"
        )
        sys.stdout.flush()

    s1 = _scene1_pack_lookup(show=show, stream=actual_stream)
    s2 = _scene2_teaching_chain(show=show, stream=actual_stream)
    s3 = _scene3_compound(show=show, stream=actual_stream)
    s4_before, s4_after, loop_closed, byte_identical = _scene4_learning_loop(
        show=show, stream=actual_stream,
    )

    turns = (s1, s2, s3, s4_before, s4_after)
    report = ConversationReport(
        turns=turns,
        learning_loop_closed=loop_closed,
        active_corpus_byte_identical=byte_identical,
    )

    if show:
        sys.stdout.write("\n")
        sys.stdout.write("═" * 64 + "\n")
        sys.stdout.write("  Done. Everything above is deterministic and replayable.\n")
        sys.stdout.write("═" * 64 + "\n\n")
        sys.stdout.flush()

    return report.as_dict()


__all__ = ["run_demo"]
