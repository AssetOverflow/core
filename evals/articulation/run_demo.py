"""Articulation demo — discourse-planner spine, end-to-end.

The thesis (the demo's headline claim):

  > With ``RuntimeConfig.discourse_planner=True``, CORE produces
  > deterministic, grounded, multi-sentence articulation across three
  > distinct prompt shapes — EXPLAIN, COMPOUND, WALKTHROUGH — and the
  > exact same prompts under the flag-off baseline collapse to
  > single-sentence (or disclosure) surfaces.  The lift is load-bearing,
  > not cosmetic.  Every multi-sentence surface is byte-identical across
  > reruns.

The discourse-planner spine is:

  DialogueIntent + ResponseMode + GroundingBundle
    -> DiscoursePlan         (canonical move ordering)
    -> PropositionGraph      (pack/teaching-resident atoms)
    -> ArticulationTarget    (selected facts + connectives)
    -> RealizedPlan          (deterministic surface)

No LLM, no stochastic sampling, no approximate retrieval.  Every
sentence traces to a pack lemma, a reviewed teaching chain, or a
fixed connective vocabulary.

Four scenes, each on a real ``ChatRuntime`` against the live active
corpus and packs.  The active corpus file bytes are byte-identical
pre/post — this demo does not mutate any corpus.

  S1.  EXPLAIN       — ``Explain truth.``
                       Flag-on: ANCHOR + SUPPORT multi-sentence paragraph.
                       Flag-off: BRIEF single-sentence baseline.
  S2.  COMPOUND      — ``What is truth, and why does it matter?``
                       Flag-on: source-ordered sub-plans + TRANSITION bridge.
                       Flag-off: OOV disclosure (compound subject pollution).
  S3.  WALKTHROUGH   — ``Walk me through recall.``
                       Flag-on: sequential teaching-chain walk with CLOSURE.
                       Flag-off: BRIEF single-sentence baseline.
  S4.  Determinism   — Each prompt re-run N times under flag-on;
                       unique(surface) == 1 for every prompt.

The test gates pin each scene's load-bearing assertion.  If any of them
break, the demo's headline claim no longer holds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


_EXPLAIN_PROMPT: str = "Explain truth."
_COMPOUND_PROMPT: str = "What is truth, and why does it matter?"
_WALKTHROUGH_PROMPT: str = "Walk me through recall."

_DETERMINISM_RERUNS: int = 3

_VERBOSE = True


def _say(*args: Any, **kwargs: Any) -> None:
    if _VERBOSE:
        print(*args, **kwargs)


def _print_header(title: str, claim: str) -> None:
    _say()
    _say("─" * 72)
    _say(f"  {title}")
    _say("─" * 72)
    _say(f"  CLAIM: {claim}")
    _say()


def _sentence_count(surface: str) -> int:
    """Sentence count by terminal punctuation.

    Matches the convention used by the articulation bench
    (``benchmarks/articulation._sentence_count``) so demo claims and
    bench claims compose without arithmetic drift.
    """
    if not surface:
        return 0
    text = surface.strip()
    count = 0
    for ch in text:
        if ch in ".!?":
            count += 1
    return max(count, 1)


def _chat_once(prompt: str, *, flag: bool) -> tuple[str, str]:
    """Single deterministic turn.  Returns ``(surface, grounding_source)``."""
    rt = ChatRuntime(config=RuntimeConfig(discourse_planner=flag))
    response = rt.chat(prompt)
    return response.surface, response.grounding_source


# ---------------------------------------------------------------------------
# Report shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SceneResult:
    scene: str
    claim: str
    detail: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"scene": self.scene, "claim": self.claim, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class DemoReport:
    scenes: tuple[SceneResult, ...]
    all_claims_supported: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenes": [s.as_dict() for s in self.scenes],
            "all_claims_supported": self.all_claims_supported,
        }


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def _scene1_explain() -> SceneResult:
    _print_header(
        "S1.  EXPLAIN — ANCHOR + SUPPORT multi-sentence paragraph",
        "Under discourse_planner=True, an EXPLAIN prompt produces a "
        "grounded multi-sentence paragraph composed from pack atoms + "
        "reviewed teaching chains.  Under flag-off, the same prompt "
        "collapses to a single-sentence baseline.  The lift is the "
        "discourse planner spine doing the work.",
    )
    off_surface, off_grounding = _chat_once(_EXPLAIN_PROMPT, flag=False)
    on_surface, on_grounding = _chat_once(_EXPLAIN_PROMPT, flag=True)
    off_count = _sentence_count(off_surface)
    on_count = _sentence_count(on_surface)

    _say(f"  prompt              : {_EXPLAIN_PROMPT}")
    _say(f"  flag=False (BRIEF)  : [{off_grounding}] ({off_count} sent.) {off_surface}")
    _say(f"  flag=True  (EXPLAIN): [{on_grounding}] ({on_count} sent.) {on_surface}")

    claim_supported = (
        on_count >= off_count + 2
        and on_count >= 3
        and on_grounding == "teaching"
        and off_grounding == "pack"
        and "truth" in on_surface.lower()
    )
    if not claim_supported:
        raise RuntimeError(
            f"S1 invariant broken: on_count={on_count}, off_count={off_count}, "
            f"on_grounding={on_grounding!r}, off_grounding={off_grounding!r}"
        )
    return SceneResult(
        scene="S1_explain",
        claim=(
            "Flag-on yields at least +2 sentences over flag-off and upgrades "
            "grounding from pack to teaching by chaining reviewed chains "
            "onto the pack anchor.  The added sentences are pack/teaching-"
            "grounded continuations, not template padding."
        ),
        detail={
            "prompt": _EXPLAIN_PROMPT,
            "flag_on": {
                "surface": on_surface,
                "grounding_source": on_grounding,
                "sentence_count": on_count,
            },
            "flag_off": {
                "surface": off_surface,
                "grounding_source": off_grounding,
                "sentence_count": off_count,
            },
            "claim_supported": claim_supported,
        },
    )


def _scene2_compound() -> SceneResult:
    _print_header(
        "S2.  COMPOUND — source-ordered sub-plans, no clause dropped",
        "Under discourse_planner=True, a compound prompt decomposes via "
        "classify_compound_intent() into ordered sub-intents.  Each "
        "sub-plan composes its own grounded surface, fact-deduped across "
        "parts, joined with TRANSITION bridges.  Under flag-off, the "
        "flat classifier sees a polluted subject (\"truth, and why does "
        "it matter\") and routes to OOV.  Compound handling is therefore "
        "load-bearing, not stylistic.",
    )
    off_surface, off_grounding = _chat_once(_COMPOUND_PROMPT, flag=False)
    on_surface, on_grounding = _chat_once(_COMPOUND_PROMPT, flag=True)
    off_count = _sentence_count(off_surface)
    on_count = _sentence_count(on_surface)

    _say(f"  prompt              : {_COMPOUND_PROMPT}")
    _say(f"  flag=False (flat)   : [{off_grounding}] ({off_count} sent.) {off_surface[:140]}...")
    _say(f"  flag=True  (compound): [{on_grounding}] ({on_count} sent.) {on_surface}")

    claim_supported = (
        on_count >= 4
        and on_grounding in {"pack", "teaching"}
        and off_grounding in {"oov", "none"}
        and "truth" in on_surface.lower()
        and "haven't learned" in off_surface.lower()
    )
    if not claim_supported:
        raise RuntimeError(
            f"S2 invariant broken: on_count={on_count}, "
            f"on_grounding={on_grounding!r}, off_grounding={off_grounding!r}"
        )
    return SceneResult(
        scene="S2_compound",
        claim=(
            "Flag-on yields >=4 grounded sentences spanning both clauses "
            "of the compound prompt; flag-off routes to OOV because the "
            "flat classifier cannot parse the second clause.  Compound "
            "decomposition is the load-bearing step."
        ),
        detail={
            "prompt": _COMPOUND_PROMPT,
            "flag_on": {
                "surface": on_surface,
                "grounding_source": on_grounding,
                "sentence_count": on_count,
            },
            "flag_off": {
                "surface": off_surface,
                "grounding_source": off_grounding,
                "sentence_count": off_count,
            },
            "claim_supported": claim_supported,
        },
    )


def _scene3_walkthrough() -> SceneResult:
    _print_header(
        "S3.  WALKTHROUGH — sequential teaching-chain walk with CLOSURE",
        "Under discourse_planner=True, a walkthrough prompt drives the "
        "planner's WALKTHROUGH mode: anchor on the subject's pack "
        "definition, then walk reviewed teaching chains "
        "(subject, *, obj) -> (obj, *, *) up to 4 hops, terminating in "
        "a CLOSURE move.  Under flag-off, the same prompt collapses to "
        "the brief definition only.",
    )
    off_surface, off_grounding = _chat_once(_WALKTHROUGH_PROMPT, flag=False)
    on_surface, on_grounding = _chat_once(_WALKTHROUGH_PROMPT, flag=True)
    off_count = _sentence_count(off_surface)
    on_count = _sentence_count(on_surface)

    _say(f"  prompt                 : {_WALKTHROUGH_PROMPT}")
    _say(f"  flag=False (BRIEF)     : [{off_grounding}] ({off_count} sent.) {off_surface}")
    _say(f"  flag=True  (WALKTHROUGH): [{on_grounding}] ({on_count} sent.) {on_surface}")

    on_lower = on_surface.lower()
    off_lower = off_surface.lower()
    # Walkthrough load-bearing test: the chain-walk CLOSURE sentence
    # ("Recall reveals memory.") appears flag-on but not flag-off.
    # Flag-off emits only the pack anchor.
    chain_hop_on = "reveals memory" in on_lower
    chain_hop_off = "reveals memory" in off_lower
    claim_supported = (
        on_grounding == "teaching"
        and chain_hop_on
        and not chain_hop_off
        and "recall" in on_lower
    )
    if not claim_supported:
        raise RuntimeError(
            f"S3 invariant broken: on_grounding={on_grounding!r}, "
            f"chain_hop_on={chain_hop_on}, chain_hop_off={chain_hop_off}, "
            f"surface={on_surface!r}"
        )
    return SceneResult(
        scene="S3_walkthrough",
        claim=(
            "Flag-on emits the chain-walk CLOSURE sentence "
            "'Recall reveals memory.' from the reviewed teaching chain; "
            "flag-off emits only the pack anchor.  The chain walk is "
            "the load-bearing step."
        ),
        detail={
            "prompt": _WALKTHROUGH_PROMPT,
            "flag_on": {
                "surface": on_surface,
                "grounding_source": on_grounding,
                "sentence_count": on_count,
            },
            "flag_off": {
                "surface": off_surface,
                "grounding_source": off_grounding,
                "sentence_count": off_count,
            },
            "claim_supported": claim_supported,
        },
    )


def _scene4_determinism() -> SceneResult:
    _print_header(
        "S4.  Determinism — byte-identical across reruns, every prompt",
        "Each of the three discourse-planner prompts is re-run N times "
        "with a fresh ChatRuntime per turn.  unique(surface) must equal "
        "1 for every prompt.  No LLM, no sampling, no clock-time reads "
        "in the articulation path — same plan, same proposition graph, "
        "same realizer, same bytes.",
    )
    prompts = [
        ("EXPLAIN", _EXPLAIN_PROMPT),
        ("COMPOUND", _COMPOUND_PROMPT),
        ("WALKTHROUGH", _WALKTHROUGH_PROMPT),
    ]
    per_prompt: list[dict[str, Any]] = []
    all_identical = True
    for label, prompt in prompts:
        seen: set[str] = set()
        for _ in range(_DETERMINISM_RERUNS):
            surface, _ = _chat_once(prompt, flag=True)
            seen.add(surface)
        unique = len(seen)
        identical = unique == 1
        all_identical = all_identical and identical
        _say(f"  {label:<12}  runs={_DETERMINISM_RERUNS}  unique={unique}  identical={identical}")
        per_prompt.append({
            "label": label,
            "prompt": prompt,
            "runs": _DETERMINISM_RERUNS,
            "unique_surfaces": unique,
            "identical": identical,
        })

    if not all_identical:
        raise RuntimeError(
            f"S4 invariant broken: not every prompt produced unique=1; "
            f"per_prompt={per_prompt}"
        )
    return SceneResult(
        scene="S4_determinism",
        claim=(
            "Every discourse-planner prompt produces byte-identical "
            "surface across reruns.  Replayability is architectural, "
            "not configurational."
        ),
        detail={
            "reruns_per_prompt": _DETERMINISM_RERUNS,
            "per_prompt": per_prompt,
            "all_identical": all_identical,
        },
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_demo(*, emit_json: bool = False) -> dict[str, Any]:
    """Run all four scenes and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    s1 = _scene1_explain()
    s2 = _scene2_compound()
    s3 = _scene3_walkthrough()
    s4 = _scene4_determinism()
    scenes = (s1, s2, s3, s4)

    all_claims_supported = all(
        bool(scene.detail.get("claim_supported", scene.detail.get("all_identical", False)))
        for scene in scenes
    )

    report = DemoReport(
        scenes=scenes,
        all_claims_supported=all_claims_supported,
    )

    if _VERBOSE:
        _say()
        _say("═" * 72)
        _say("  ARTICULATION DEMO — summary")
        _say("═" * 72)
        for scene in scenes:
            supported = scene.detail.get(
                "claim_supported",
                scene.detail.get("all_identical", False),
            )
            mark = "✓" if supported else "✗"
            _say(f"  {mark}  {scene.scene}")
        _say()
        _say(f"  all_claims_supported : {report.all_claims_supported}")
        _say()

    return report.as_dict()


__all__ = ["run_demo"]
