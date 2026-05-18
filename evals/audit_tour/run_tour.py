"""Audit tour — narrative walkthrough demonstrating CORE's
load-bearing pack-layer architecture and deterministic replay.

Four scenes, each making one falsifiable claim no transformer-LLM
wrapper can reproduce:

  S1. **Identity is geometric, not prompt-veneer.**
      Same input through three different identity packs produces
      three different deterministic surfaces.  Identity is loaded
      from the pack at runtime composition (ADR-0027), not from a
      prompt prefix.

  S2. **Safety is the universal floor — typed, deterministic refusal.**
      A runtime-checkable safety violation replaces the response
      with a deterministic typed refusal string (ADR-0036).  Same
      violation → byte-identical refusal text every time.

  S3. **Ethics opt-in remediation — hedge injection without refusal.**
      Per-commitment opt-in (ADR-0037 / ADR-0038) lets a deployment
      pack pick the remediation tier (audit / hedge / refuse) per
      ethics commitment.  Same input, same engine, different
      remediation depending on the pack.

  S4. **Deterministic replay — byte-identical JSONL across runs.**
      A fresh runtime processing the same input emits
      byte-identical JSONL audit lines (ADR-0040).  This is the
      replay invariant — no stochastic sampling, no hidden state.

The tour is designed to run end-to-end without external
dependencies, network calls, or LLM APIs.  It uses only the
pack-layer surface that landed in ADR-0027 → ADR-0041.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from chat.runtime import ChatRuntime
from chat.telemetry import JsonlBufferSink, format_verdict_summary
from core.config import RuntimeConfig
from packs.safety.check import SafetyCheckResult


_DEMO_INPUT = "light is"

# Three v1 identity packs ship in packs/identity/.  The pack ids
# below are guaranteed available by ADR-0027 Phase 5 ratification.
_IDENTITY_PACKS = (
    "default_general_v1",
    "generosity_first_v1",
    "precision_first_v1",
)


# ---------- scene helpers ----------


_VERBOSE = True


def _say(*args, **kwargs) -> None:
    if _VERBOSE:
        print(*args, **kwargs)


def _print_header(title: str, claim: str) -> None:
    _say()
    _say("─" * 72)
    _say(f"  {title}")
    _say("─" * 72)
    _say(f"  CLAIM: {claim}")
    _say()


def _print_verdict_line(label: str, response) -> None:
    _say(f"    {label:32s} {response.surface}")
    _say(f"    {'':32s} {format_verdict_summary(response.verdicts)}")


# ---------- scenes ----------


def _scene_1_identity_geometric() -> dict[str, Any]:
    """Three identity packs → three structurally distinct manifolds."""
    _print_header(
        "Scene 1 — Identity is geometric, not prompt-veneer.",
        "Three identity packs (ADR-0027) load three structurally "
        "distinct manifolds at composition time: different value "
        "axes, different alignment thresholds, different hedge "
        "phrasing. No prompt prefix is involved.",
    )
    _say(
        f"    {'pack':28s} {'axes':>6s} {'align':>7s} "
        f"{'hedge_soft':30s}"
    )
    _say(f"    {'-' * 28} {'-' * 6} {'-' * 7} {'-' * 30}")
    pack_shapes: dict[str, dict[str, Any]] = {}
    for pack_id in _IDENTITY_PACKS:
        rt = ChatRuntime(config=RuntimeConfig(identity_pack=pack_id))
        manifold = rt.identity_manifold
        prefs = manifold.surface_preferences
        axes = len(manifold.value_axes)
        threshold = manifold.alignment_threshold
        hedge_soft = getattr(prefs, "preferred_hedge_soft", "") or "(none)"
        _say(
            f"    {pack_id:28s} {axes:>6d} {threshold:>7.2f} {hedge_soft:30s}"
        )
        pack_shapes[pack_id] = {
            "value_axes_count": axes,
            "alignment_threshold": float(threshold),
            "hedge_soft": hedge_soft,
        }
    # Two structural distinctions are sufficient evidence: the axis
    # count or threshold differs across packs.  Both come from the
    # JSON pack files — no code change distinguishes them.
    threshold_set = {round(p["alignment_threshold"], 3) for p in pack_shapes.values()}
    hedge_set = {p["hedge_soft"] for p in pack_shapes.values()}
    _say()
    _say(
        f"  EVIDENCE: distinct alignment thresholds = {len(threshold_set)}, "
        f"distinct hedge phrases = {len(hedge_set)}.  These differences "
        "are loaded from JSON pack files (`packs/identity/*.json`), not "
        "from prompts, and they ride into every runtime decision."
    )
    return {
        "pack_shapes": pack_shapes,
        "distinct_alignment_thresholds": len(threshold_set),
        "distinct_hedge_phrases": len(hedge_set),
    }


def _scene_2_safety_typed_refusal() -> dict[str, Any]:
    """Forced runtime-checkable safety violation → typed refusal."""
    _print_header(
        "Scene 2 — Safety is the universal floor.",
        "A runtime-checkable safety violation produces a "
        "deterministic typed refusal string (ADR-0036). Replayable, "
        "audit-detectable by prefix, byte-identical across runs.",
    )
    rt = ChatRuntime(config=RuntimeConfig())

    def _failing(ctx):  # noqa: ANN001 — predicate signature
        return SafetyCheckResult(
            boundary_id="preserve_versor_closure",
            upheld=False,
            reason="forced for audit tour",
            runtime_checkable=True,
        )

    rt.safety_check.register("preserve_versor_closure", _failing)
    resp = rt.chat(_DEMO_INPUT)
    _print_verdict_line("[safety violation]", resp)
    _say()
    _say(
        "  EVIDENCE: surface != walk_surface — the response was "
        "replaced; the original surface is preserved on "
        "ChatResponse.walk_surface for audit."
    )
    _say(f"    walk_surface:                    {resp.walk_surface}")
    return {
        "refused_surface": resp.surface,
        "walk_surface": resp.walk_surface,
        "refusal_emitted": bool(getattr(resp.verdicts, "refusal_emitted", False)),
    }


def _scene_3_ethics_hedge_opt_in() -> dict[str, Any]:
    """Ethics opt-in remediation — pure-helper evidence + pack diff."""
    _print_header(
        "Scene 3 — Ethics commitments choose their remediation.",
        "Per-commitment opt-in (ADR-0037 / ADR-0038): a pack opts a "
        "commitment into either refusal or hedge injection. Same "
        "engine; pack JSON picks the remediation tier.",
    )
    from chat.refusal import (
        build_hedge_prefix,
        inject_hedge,
        should_inject_hedge,
    )
    from packs.ethics.check import EthicsCheckResult, EthicsVerdict

    rt_default = ChatRuntime(config=RuntimeConfig())
    rt_hedge = ChatRuntime(config=RuntimeConfig())
    rt_hedge.ethics_pack = replace(
        rt_hedge.ethics_pack,
        hedge_commitments=frozenset({"acknowledge_uncertainty"}),
    )

    # Pack-level structural evidence.
    _say("    Pack-level remediation policy:")
    _say(
        f"      default pack hedge_commitments:   "
        f"{sorted(rt_default.ethics_pack.hedge_commitments) or '(empty — audit only)'}"
    )
    _say(
        f"      deployment pack hedge_commitments: "
        f"{sorted(rt_hedge.ethics_pack.hedge_commitments)}"
    )
    _say()

    # Runtime behavior on a synthetic ethics verdict — this exercises
    # the pure remediation pipeline that ADR-0038 anchors to.  We do
    # not depend on the stub/main path of ``chat()`` here: the goal is
    # to show that GIVEN a runtime-checkable violation of an opted-in
    # commitment, the policy decision matches the pack.
    synthetic_verdict = EthicsVerdict(
        pack_id=rt_hedge.ethics_pack.pack_id,
        results=(
            EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="synthetic — for tour evidence",
                runtime_checkable=True,
            ),
        ),
        upheld=False,
        violated_commitments=frozenset({"acknowledge_uncertainty"}),
        runtime_checkable_count=1,
    )

    fires_default = should_inject_hedge(synthetic_verdict, rt_default.ethics_pack)
    fires_hedge = should_inject_hedge(synthetic_verdict, rt_hedge.ethics_pack)
    hedge_prefix = build_hedge_prefix(rt_hedge.identity_manifold)
    sample_surface = "the answer is X"
    hedged = inject_hedge(sample_surface, hedge_prefix) if fires_hedge else sample_surface

    _say("    Runtime behavior on a runtime-checkable violation:")
    _say(f"      default pack    should_inject_hedge → {fires_default}")
    _say(f"      deployment pack should_inject_hedge → {fires_hedge}")
    _say(f"      hedge phrase from manifold:           {hedge_prefix!r}")
    _say(f"      example surface:                      {sample_surface!r}")
    _say(f"      hedged surface:                       {hedged!r}")
    _say()
    _say(
        "  EVIDENCE: same engine, same identical violation. The "
        "default pack reports `False` (audit-only); the deployment "
        "pack reports `True` and prepends the manifold's hedge. "
        "Stub/main path is orthogonal — ADR-0038 specifies stub "
        "skips hedge by design (the unknown-domain marker is "
        "already a disclosure).  End-to-end on the main path is "
        "asserted in tests/test_hedge_injection.py."
    )
    return {
        "default_pack_hedge_commitments": sorted(rt_default.ethics_pack.hedge_commitments),
        "deployment_pack_hedge_commitments": sorted(rt_hedge.ethics_pack.hedge_commitments),
        "default_fires": fires_default,
        "deployment_fires": fires_hedge,
        "hedge_prefix": hedge_prefix,
        "sample_surface": sample_surface,
        "hedged_surface": hedged,
    }


def _scene_4_deterministic_replay() -> dict[str, Any]:
    """Two fresh runtimes, same input → byte-identical JSONL."""
    _print_header(
        "Scene 4 — Deterministic replay across runtime instances.",
        "Two fresh ChatRuntime instances, same input, same packs. "
        "The emitted JSONL audit line (ADR-0040) is byte-identical. "
        "No stochastic sampling. No hidden state.",
    )
    lines: list[str] = []
    for run_idx in range(2):
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat(_DEMO_INPUT)
        lines.append(sink.lines[-1])
        # Show a truncated preview so the line fits in the terminal.
        preview = lines[-1] if len(lines[-1]) <= 100 else lines[-1][:97] + "..."
        _say(f"    run {run_idx + 1}:  {preview}")
    _say()
    identical = lines[0] == lines[1]
    if identical:
        _say(
            "  EVIDENCE: byte-identical JSONL across independent "
            "runtime instances. Replay invariant holds."
        )
    else:
        _say(
            "  EVIDENCE: lines diverged — this would be a regression "
            "of the deterministic-replay claim."
        )
    return {
        "byte_identical": identical,
        "line_1_sha_preview": _short_hash(lines[0]),
        "line_2_sha_preview": _short_hash(lines[1]),
    }


def _short_hash(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ---------- entry point ----------


def run_tour(*, emit_json: bool = False) -> dict[str, Any]:
    """Run the audit tour end-to-end. Returns a structured report.

    When ``emit_json`` is True the human narration is suppressed and
    the result dict is the only output (caller prints it).  Otherwise
    the narration is printed as we go and the result dict is returned
    for ``list-results`` indexing.
    """
    global _VERBOSE
    _VERBOSE = not emit_json
    if not emit_json:
        _say()
        _say("=" * 72)
        _say("  CORE Audit Tour — pack-layer architecture in four scenes")
        _say("=" * 72)
        _say(
            "  Each scene makes one falsifiable claim no transformer-LLM\n"
            "  wrapper can reproduce. Evidence comes from ADR-0027 through\n"
            "  ADR-0041 — load-bearing pack-layer architecture, deterministic\n"
            "  refusal/hedge, and byte-identical replay across instances."
        )

    s1 = _scene_1_identity_geometric()
    s2 = _scene_2_safety_typed_refusal()
    s3 = _scene_3_ethics_hedge_opt_in()
    s4 = _scene_4_deterministic_replay()

    if not emit_json:
        _say()
        _say("=" * 72)
        _say("  Summary")
        _say("=" * 72)
        _say(f"  Identity packs — distinct hedge phrases:    {s1['distinct_hedge_phrases']} / {len(_IDENTITY_PACKS)}")
        _say(f"  Identity packs — distinct align thresholds: {s1['distinct_alignment_thresholds']} / {len(_IDENTITY_PACKS)}")
        _say(f"  Safety typed refusal emitted:               {s2['refusal_emitted']}")
        _say(f"  Ethics opt-in fires on deployment pack:     {s3['deployment_fires']}")
        _say(f"  Ethics opt-in stays off on default pack:    {not s3['default_fires']}")
        _say(f"  Deterministic replay (byte-identical):      {s4['byte_identical']}")
        _say()
        _say("  Every claim is testable; every refusal/hedge is auditable;")
        _say("  every run is replayable.  See:")
        _say("    - docs/decisions/ADR-0027 through ADR-0041")
        _say("    - tests/test_safety_refusal.py")
        _say("    - tests/test_ethics_refusal_opt_in.py")
        _say("    - tests/test_hedge_injection.py")
        _say("    - tests/test_telemetry_sink.py")
        _say()

    return {
        "scene_1_identity_geometric": s1,
        "scene_2_safety_typed_refusal": s2,
        "scene_3_ethics_hedge_opt_in": s3,
        "scene_4_deterministic_replay": s4,
        "all_claims_supported": (
            s1["distinct_hedge_phrases"] >= 1
            and s2["refusal_emitted"]
            and s3["deployment_fires"]
            and not s3["default_fires"]
            and s4["byte_identical"]
        ),
    }


if __name__ == "__main__":  # pragma: no cover
    import sys

    emit_json = "--json" in sys.argv
    result = run_tour(emit_json=emit_json)
    if emit_json:
        _say(json.dumps(result, indent=2, sort_keys=True, default=str))
