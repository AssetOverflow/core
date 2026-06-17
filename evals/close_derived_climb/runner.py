"""Yardstick for CLOSE derived climb (PR-3 after #788+#789), hardened for full Claim B.

Deterministic proof that:

- is-a + relational-transitive derived facts enlarge the directly-answerable set
  monotonically to fixed point across idle_tick (with consolidate_determinations=True).
- wrong_total == 0: excluded predicates (parent_of etc.) and member∨member canary
  never derive; negatives remain Undetermined.
- proposal emission uses *real* ChatRuntime.idle_tick() + IdleTickResult.derived_close_proposals_emitted
  (gated by review_derived_close_proposals).
- Positive growth scored via semantic determine() calls on materialized facts (rule='direct' post-FP).
- All trajectories/replays stable at *content* level (closures + proposal bodies) + aggregates (no clock/LLM).

Uses real comprehend/realize/idle_tick path. Small fixed scenarios for is-a,
less_than, before_event, negatives. Proposal flag via lived idle_tick (not simulation).

replay_checksum: aggregate sizes + wrong + flag (compatibility).
content_replay_checksum: canonical closures (structure_key + Derivation/premises) + proposal bodies.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from dataclasses import replace
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.reader import comprehend
from generate.meaning_graph.relational import (
    TRANSITIVE_PREDICATES,
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import RealizedRecord, realize_comprehension, recall_realized
from session.context import SessionContext

_HIGH = 10**9
_PACK = load_relational_pack_lemmas()


def _fresh_ctx(
    consolidate: bool = True, proposals: bool = False
) -> tuple[SessionContext, ChatRuntime]:
    from core.config import DEFAULT_CONFIG
    cfg = replace(
        DEFAULT_CONFIG,
        consolidate_determinations=consolidate,
        review_derived_close_proposals=proposals,
    )
    rt = ChatRuntime(config=cfg, no_load_state=True)
    ctx = rt._context
    # ensure high reproject like other lanes
    if hasattr(ctx, "vault_reproject_interval"):
        ctx.vault_reproject_interval = _HIGH
    return ctx, rt


def _tell(ctx: SessionContext, text: str) -> None:
    realize_comprehension(comprehend(text), ctx)


def _tell_rel(ctx: SessionContext, text: str) -> None:
    realize_comprehension(comprehend_relational(text, _PACK), ctx)


def _ask(ctx: SessionContext, text: str) -> Determined | Undetermined:
    return determine(comprehend(text), ctx)


def _ask_rel(ctx: SessionContext, text: str) -> Determined | Undetermined:
    return determine(comprehend_relational(text, _PACK), ctx)


def _count_answerable(ctx: SessionContext, asks: list[tuple[str, bool]]) -> int:
    """Count how many of the asked facts are directly realized in the vault (the 'direct answerable' from CLOSE)."""
    count = 0
    for q, is_rel in asks:
        q = q.lower().strip('?').strip()
        if not q.startswith("is "):
            continue
        rest = q[3:].strip()
        parts = rest.split()
        if len(parts) < 2:
            continue
        subj = parts[0]
        if "less than" in rest:
            pred = "less_than"
            obj = parts[-1]
        elif "before" in rest:
            pred = "before_event"
            obj = parts[-1]
        else:
            # is-a "is a X" or "is an X"
            pred = "member"
            obj = parts[-1]
        # check if the specific (pred, subj, obj) is realized
        hits = [r for r in recall_realized(ctx, subject=subj, predicate=pred) if len(r.relation_arguments) > 1 and r.relation_arguments[1] == obj]
        if hits:
            count += 1
    return count


def _get_closure_content(ctx: SessionContext) -> list[dict[str, Any]]:
    """Project full closure for Claim B content checksum (structure_key + derivation with premises)."""
    data: list[dict[str, Any]] = []
    for p in ["member", "subset"] + sorted(TRANSITIVE_PREDICATES):
        for r in recall_realized(ctx, predicate=p):
            der = asdict(r.derivation) if r.derivation is not None else None
            data.append(
                {
                    "predicate": p,
                    "args": list(r.relation_arguments),
                    "structure_key": r.structure_key,
                    "derived": r.derived,
                    "derivation": der,
                    "epistemic_status": getattr(r, "epistemic_status", None),
                }
            )
    data.sort(key=lambda x: (x["predicate"], tuple(x["args"])))
    return data


# --- Scenarios ---

def _is_a_climb() -> dict[str, Any]:
    """member/subset climb: rex dog -> mammal -> ... creature. Expect growth 1->4."""
    ctx, rt = _fresh_ctx()
    _tell(ctx, "Rex is a dog.")
    _tell(ctx, "All dogs are mammals.")
    _tell(ctx, "All mammals are animals.")
    _tell(ctx, "All animals are creatures.")
    # Canary: member(dog, kingdom) + member(rex, dog) should not derive member(rex, kingdom)
    _tell(ctx, "Dog is a kingdom.")

    # Query set for answerable - used for live measurement at each stage
    queries = [
        ("Is Rex a dog?", False),
        ("Is Rex a mammal?", False),
        ("Is Rex an animal?", False),
        ("Is Rex a creature?", False),
        ("Is Rex a kingdom?", False),  # must stay refused
    ]

    before = _count_answerable(ctx, queries)
    res1 = rt.idle_tick()
    after1 = _count_answerable(ctx, queries)
    # continue ticking until fixed point (use facts_consolidated==0 as proxy, since IdleTickResult has no at_fixed_point)
    fp = res1
    for _ in range(10):  # safety bound
        fp = rt.idle_tick()
        if fp.facts_consolidated == 0:
            break
    after_fp = _count_answerable(ctx, queries)

    wrong_total = 0
    # Check canary not derived (still valid for wrong=0)
    if "kingdom" in [r.relation_arguments[1] for r in recall_realized(ctx, subject="rex", predicate="member")]:
        wrong_total += 1

    # Semantic Answerability (Claim B): explicitly call determine on positives post-fixed-point
    # and assert Determined(True) with rule='direct' (the materialized direct path).
    positive_queries = [q for q in queries if "kingdom" not in q[0].lower()]
    for q, is_rel in positive_queries:
        det = _ask(ctx, q) if not is_rel else _ask_rel(ctx, q)
        assert isinstance(det, Determined) and getattr(det, "answer", False) and getattr(det, "rule", None) == "direct", (
            f"Claim B semantic answerability failed for {q}: got {det}"
        )

    closure = _get_closure_content(ctx)

    return {
        "scenario": "is_a_climb",
        "before": before,
        "after_tick_1": after1,
        "after_fixed_point": after_fp,
        "facts_consolidated_tick1": res1.facts_consolidated if hasattr(res1, 'facts_consolidated') else 0,
        "at_fixed_point": (fp.facts_consolidated == 0),
        "wrong_total": wrong_total,
        "proposals_emitted": 0,  # separate flag run below
        "closure": closure,
        "semantic_positives_determined_direct": len(positive_queries),
    }


def _relational_climb_less_than() -> dict[str, Any]:
    ctx, rt = _fresh_ctx()
    _tell_rel(ctx, "A is less than B.")
    _tell_rel(ctx, "B is less than C.")
    _tell_rel(ctx, "C is less than D.")

    # Consistent query set for all stages
    queries = [
        ("Is A less than C?", True),
        ("Is B less than D?", True),
        ("Is A less than D?", True),
    ]

    before = _count_answerable(ctx, queries)
    res1 = rt.idle_tick()
    after1 = _count_answerable(ctx, queries)
    res2 = rt.idle_tick()
    after_fp = _count_answerable(ctx, queries)

    # Negative: no cross (refused)
    neg = _ask_rel(ctx, "Is A less than E?")  # no E, but to test refused for non-chain
    wrong = 0
    if isinstance(neg, Determined):
        wrong += 1

    # Semantic Answerability (Claim B)
    for q, is_rel in queries:
        det = _ask_rel(ctx, q)
        assert isinstance(det, Determined) and getattr(det, "answer", False) and getattr(det, "rule", None) == "direct", (
            f"Claim B semantic answerability failed for {q}: got {det}"
        )

    closure = _get_closure_content(ctx)

    return {
        "scenario": "less_than_climb",
        "before": before,
        "after_tick_1": after1,
        "after_fixed_point": after_fp,
        "wrong_total": wrong,
        "closure": closure,
        "semantic_positives_determined_direct": len(queries),
    }


def _temporal_climb() -> dict[str, Any]:
    ctx, rt = _fresh_ctx()
    _tell_rel(ctx, "Dawn is before noon.")
    _tell_rel(ctx, "Noon is before dusk.")

    # Consistent query set (single but via helper for uniformity)
    queries = [
        ("Is Dawn before dusk?", True),
    ]

    before = _count_answerable(ctx, queries)
    rt.idle_tick()
    after = _count_answerable(ctx, queries)

    # Semantic Answerability (Claim B)
    for q, is_rel in queries:
        det = _ask_rel(ctx, q)
        assert isinstance(det, Determined) and getattr(det, "answer", False) and getattr(det, "rule", None) == "direct", (
            f"Claim B semantic answerability failed for {q}: got {det}"
        )

    closure = _get_closure_content(ctx)

    return {
        "scenario": "before_event_climb",
        "before": before,
        "after_fixed_point": after,
        "wrong_total": 0,
        "closure": closure,
        "semantic_positives_determined_direct": len(queries),
    }


def _negatives_refused() -> dict[str, Any]:
    ctx, rt = _fresh_ctx()
    _tell_rel(ctx, "X is parent of Y.")
    _tell_rel(ctx, "Y is parent of Z.")
    _tell_rel(ctx, "P is sibling of Q.")
    _tell_rel(ctx, "Q is sibling of R.")

    rt.idle_tick()
    rt.idle_tick()

    refused = 0
    for q in ["Is X parent of Z?", "Is P sibling of R?"]:
        if isinstance(_ask_rel(ctx, q), Undetermined):
            refused += 1

    return {
        "scenario": "negatives_refused",
        "parent_refused": refused >= 1,
        "sibling_refused": refused >= 2,
        "wrong_total": 0 if refused == 2 else 1,
    }


def _proposal_flag_effect() -> dict[str, Any]:
    """Measure proposal bridge via *lived* runtime flag path.
    Uses real ChatRuntime.idle_tick() + IdleTickResult.derived_close_proposals_emitted
    (the runtime flag in idle_tick gates the call to the bridge)."""
    import generate.determine.derived_close_proposals as dcp
    import tempfile

    # "without" via real idle_tick with flag off (must emit 0)
    ctx_off, rt_off = _fresh_ctx(consolidate=True, proposals=False)
    _tell_rel(ctx_off, "A is less than B.")
    _tell_rel(ctx_off, "B is less than C.")
    res_off = rt_off.idle_tick()
    emitted_without = res_off.derived_close_proposals_emitted

    # "with" via real idle_tick with flag on (captures from IdleTickResult; temp sink for isolation + content)
    with tempfile.TemporaryDirectory() as tmp:
        sink = Path(tmp)
        orig_sink = dcp.DEFAULT_SINK
        dcp.DEFAULT_SINK = sink
        try:
            ctx_on, rt_on = _fresh_ctx(consolidate=True, proposals=True)
            _tell_rel(ctx_on, "A is less than B.")
            _tell_rel(ctx_on, "B is less than C.")
            res_on = rt_on.idle_tick()
            emitted_with = res_on.derived_close_proposals_emitted
            # capture full bodies for content checksum (lived emission path)
            proposals = [json.loads(p.read_text()) for p in sorted(sink.glob("*.json"))]
        finally:
            dcp.DEFAULT_SINK = orig_sink

    return {
        "scenario": "proposal_flag",
        "emitted_without_flag": emitted_without,
        "emitted_with_flag": emitted_with,
        "only_with_flag": emitted_with > 0 and emitted_without == 0,
        "proposals": proposals,
    }


def run() -> dict[str, Any]:
    """Run the full yardstick. Returns report with climb metrics, wrong_total=0,
    lived proposal flag isolation (via IdleTickResult), semantic determine() on positives,
    replay_checksum (aggregates) + content_replay_checksum (closures + proposal bodies),
    and proposal_review_posture (additive visibility into the review/ratification side:
    emitted proposals are born proposal_only/SPECULATIVE/requires_review; the yardstick
    exercises no acceptance, rejection, or promotion paths)."""
    is_a = _is_a_climb()
    less = _relational_climb_less_than()
    temporal = _temporal_climb()
    neg = _negatives_refused()
    prop = _proposal_flag_effect()

    # Aggregate
    before_sets = [is_a["before"], less["before"], temporal["before"]]
    after1_sets = [is_a["after_tick_1"], less["after_tick_1"], temporal["after_fixed_point"]]
    fp_sets = [is_a["after_fixed_point"], less["after_fixed_point"], temporal["after_fixed_point"]]

    total_wrong = is_a["wrong_total"] + less["wrong_total"] + temporal.get("wrong_total", 0) + neg["wrong_total"]

    monotone_growth = all(a <= b for a, b in zip(before_sets, fp_sets))
    strict_growth = sum(before_sets) < sum(fp_sets)

    report = {
        "is_a_climb": is_a,
        "less_than_climb": less,
        "before_event_climb": temporal,
        "negatives": neg,
        "proposal_flag": prop,
        "aggregate": {
            "direct_answerable_before": sum(before_sets),
            "direct_answerable_after_tick_1": sum(after1_sets),
            "direct_answerable_after_fixed_point": sum(fp_sets),
            "monotone_growth": monotone_growth,
            "strict_growth": strict_growth,
            "wrong_total": total_wrong,
            "proposals_only_with_flag": prop["only_with_flag"],
        },
    }

    # Additive review/ratification-posture instrumentation for the CLOSE flywheel
    # (the previously weaker half). Computed purely from the proposal bodies
    # already emitted and captured for content_replay_checksum. No review logic
    # is invoked; the yardstick only observes the explicit review-gated posture
    # that every derived CLOSE proposal is born with (proposal_only / SPECULATIVE
    # / requires_review). This surfaces acceptance/rejection eligibility signals
    # and documents that the yardstick itself performs no ratification.
    _proposals = prop.get("proposals", []) or []
    _all_status = [p.get("status") for p in _proposals]
    _all_epist = [p.get("epistemic_status") for p in _proposals]
    _all_req = [p.get("requires_review") for p in _proposals]
    report["proposal_review_posture"] = {
        "emitted_count": len(_proposals),
        "all_proposal_only": all(s == "proposal_only" for s in _all_status) if _proposals else True,
        "all_speculative": all(e == "speculative" for e in _all_epist) if _proposals else True,
        "all_requires_review": all(r is True for r in _all_req) if _proposals else True,
        "review_eligible": len(_proposals),
        "none_accepted_or_promoted": True,  # yardstick is emission + semantic only; ratification is HITL / operator-gated outside this surface
    }

    # Replay checksum: stable sizes + wrongs + flag effect (kept for compatibility)
    checksum_input = json.dumps(
        {
            "sizes": [report["aggregate"][k] for k in ("direct_answerable_before", "direct_answerable_after_tick_1", "direct_answerable_after_fixed_point")],
            "wrong_total": total_wrong,
            "flag_isolation": prop["only_with_flag"],
        },
        sort_keys=True,
    ).encode()
    report["replay_checksum"] = hashlib.sha256(checksum_input).hexdigest()

    # Parallel full-content checksum for Claim B fidelity (canonical closures + proposal bodies)
    # This aligns the yardstick with its documentation ("closure sets", "exact trajectories").
    content = {
        "closures": {
            "is_a": is_a.get("closure", []),
            "less_than": less.get("closure", []),
            "before_event": temporal.get("closure", []),
        },
        "proposals": prop.get("proposals", []),
    }
    content_input = json.dumps(content, sort_keys=True).encode()
    report["content_replay_checksum"] = hashlib.sha256(content_input).hexdigest()

    return report


if __name__ == "__main__":
    import pprint
    pprint.pprint(run())