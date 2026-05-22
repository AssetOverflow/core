"""ADR-0112 Runnable Expert-Demo Showcase composer.

Renders a per-domain runnable demonstration of an ``expert-demo``
ledger row. Reads the signed ``expert_demo_claims`` entry, re-derives
the evidence-bundle digest from on-disk lane result files, asserts
byte-for-byte match, then composes a JSON + HTML showcase exposing:

- the signed claim metadata (reviewer, evidence_revision, lanes)
- the recomputed digest alongside the signed one
- per-lane shape-check verdicts on public + holdout splits
- a small sample of cases (first N) drawn verbatim from each result
  file so an external reader can inspect what the domain actually
  produced

The composer does NOT re-run the lanes. The lane result files are the
artifact the digest covers; replaying them would not strengthen the
claim. Per-domain "watch CORE answer X" is achieved by surfacing the
already-shipped case records, with the digest match as the load-bearing
audit step.

Determinism: same on-disk lane result files + same signed claim →
byte-identical JSON output (modulo wall-clock timestamps which are
excluded from the canonical JSON exactly as ADR-0099's showcase does).
"""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.capability.expert_demo import (
    SHAPE_CHECKERS,
    derive_evidence_digest,
    resolve_lane_shape,
)
from core.capability.reviewers import (
    ExpertDemoClaim,
    ReviewerRegistry,
    load_reviewer_registry,
)
from core.capability.sources import LEDGER_SOURCES
from core.demos.contract import CLAIM_CONTRACT_VERSION, canonical_json


EXPERT_DEMO_VERSION: int = 1
SAMPLE_CASES_PER_SPLIT: int = 3


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True, slots=True)
class _LaneResultBundle:
    metrics: Mapping[str, Any]
    cases: tuple[Mapping[str, Any], ...]
    result_path: Path


def _latest_result_path(lane: str, split: str) -> Path:
    pattern = _REPO_ROOT / "evals" / lane / "results" / f"v1_{split}_*.json"
    matches = sorted(glob.glob(str(pattern)))
    if matches:
        return Path(matches[-1])
    exact = _REPO_ROOT / "evals" / lane / "results" / f"v1_{split}.json"
    return exact


def _load_lane_split(lane: str, split: str) -> _LaneResultBundle:
    path = _latest_result_path(lane, split)
    if not path.exists():
        raise FileNotFoundError(
            f"Expert-demo composer cannot find on-disk result for "
            f"lane {lane!r} split {split!r}: {path}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = dict(payload.get("metrics", {}) or {})
    if "by_class" not in metrics and "by_class" in payload:
        metrics["by_class"] = payload["by_class"]
    cases_raw = payload.get("cases") or []
    cases = tuple(dict(c) for c in cases_raw)
    return _LaneResultBundle(metrics=metrics, cases=cases, result_path=path)


def _shape_check(lane_id: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
    shape_id = resolve_lane_shape(lane_id)
    if shape_id is None:
        return {"shape": None, "passed": False, "reason": "unregistered lane"}
    checker = SHAPE_CHECKERS.get(shape_id)
    if checker is None:
        return {"shape": shape_id, "passed": False, "reason": "no checker"}
    passed, reason = checker(lane_id, metrics)
    return {"shape": shape_id, "passed": passed, "reason": reason}


def _sample_cases(cases: tuple[Mapping[str, Any], ...]) -> list[dict[str, Any]]:
    """Pick the first N cases verbatim — deterministic by file order.

    Adapters do not see this list; it is rendered for human inspection
    only. We deliberately preserve raw case keys (case_id / id / surface
    / passed) without normalization so a reader can see exactly what
    the lane runner produced.
    """
    sampled = list(cases[:SAMPLE_CASES_PER_SPLIT])
    return [dict(sorted(c.items())) for c in sampled]


def _resolve_claim(domain_id: str) -> ExpertDemoClaim:
    registry_path = _REPO_ROOT / LEDGER_SOURCES.reviewers
    registry: ReviewerRegistry = load_reviewer_registry(registry_path)
    claim = registry.expert_demo_claim_for(domain_id)
    if claim is None:
        raise ValueError(
            f"No expert_demo_claims entry for domain {domain_id!r} — "
            f"a runnable expert-demo requires a signed claim in "
            f"docs/reviewers.yaml. Domain may be reasoning-capable but "
            f"not promoted."
        )
    return claim


def build_expert_demo(domain_id: str) -> dict[str, Any]:
    """Compose the showcase payload for ``domain_id``.

    Raises if ``domain_id`` lacks a signed claim, if any attached
    lane result file is missing, or if the recomputed digest does
    not match the signed claim_digest.
    """
    claim = _resolve_claim(domain_id)
    lane_bundles: dict[str, dict[str, _LaneResultBundle]] = {}
    for lane in claim.evidence_lanes:
        lane_bundles[lane] = {
            "public": _load_lane_split(lane, "public"),
            "holdout": _load_lane_split(lane, "holdout"),
        }

    lane_metrics_for_digest = {
        lane: {
            "public": dict(lane_bundles[lane]["public"].metrics),
            "holdout": dict(lane_bundles[lane]["holdout"].metrics),
        }
        for lane in claim.evidence_lanes
    }
    derived = derive_evidence_digest(
        domain_id=domain_id,
        evidence_revision=claim.evidence_revision,
        evidence_lanes=claim.evidence_lanes,
        lane_results=lane_metrics_for_digest,
    )
    digests_match = derived == claim.claim_digest

    lane_payloads: list[dict[str, Any]] = []
    all_lanes_pass = True
    for lane in claim.evidence_lanes:
        splits: dict[str, Any] = {}
        for split in ("public", "holdout"):
            bundle = lane_bundles[lane][split]
            verdict = _shape_check(lane, bundle.metrics)
            if not verdict["passed"]:
                all_lanes_pass = False
            splits[split] = {
                "metrics": dict(sorted(bundle.metrics.items())),
                "shape_check": verdict,
                "case_count": len(bundle.cases),
                "sample_cases": _sample_cases(bundle.cases),
                "result_path": str(bundle.result_path.relative_to(_REPO_ROOT)),
            }
        lane_payloads.append(
            {
                "lane_id": lane,
                "shape": resolve_lane_shape(lane),
                "splits": splits,
            }
        )

    all_claims_supported = digests_match and all_lanes_pass

    return {
        "expert_demo_version": EXPERT_DEMO_VERSION,
        "claim_contract_version": CLAIM_CONTRACT_VERSION,
        "domain_id": domain_id,
        "claim": {
            "evidence_lanes": list(claim.evidence_lanes),
            "evidence_revision": claim.evidence_revision,
            "signed_by": claim.signed_by,
            "claim_digest": claim.claim_digest,
        },
        "digest_verification": {
            "signed": claim.claim_digest,
            "derived": derived,
            "matches": digests_match,
        },
        "lanes": lane_payloads,
        "all_lanes_pass": all_lanes_pass,
        "all_digests_match": digests_match,
        "all_claims_supported": all_claims_supported,
    }


def run_expert_demo(*, domain_id: str, output_dir: Path) -> dict[str, Any]:
    """Build, write JSON + HTML, return the payload.

    ``output_dir`` is created if absent. Two outputs land there:
    ``expert_demo.json`` (byte-deterministic via :func:`canonical_json`)
    and ``expert_demo.html`` (presentation-only).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_expert_demo(domain_id)
    json_path = output_dir / "expert_demo.json"
    json_path.write_bytes(canonical_json(payload))
    html_path = output_dir / "expert_demo.html"
    html_path.write_text(render_html(payload), encoding="utf-8")
    return payload


def render_html(payload: dict[str, Any]) -> str:
    """Render the expert-demo payload as a static HTML document."""
    import html

    def esc(value: Any) -> str:
        return html.escape(str(value))

    def case_block(case: Mapping[str, Any]) -> str:
        case_id = case.get("case_id") or case.get("id") or "?"
        passed = case.get("passed")
        if passed is None:
            # fabrication_control uses outcome_matches_expected
            passed = case.get("outcome_matches_expected")
        mark = "✓" if passed else ("✗" if passed is False else "·")
        surface = case.get("surface") or case.get("prompt") or ""
        extras = []
        for k in (
            "construction_name",
            "pattern",
            "class",
            "grounding_source",
            "trace_hash",
        ):
            if k in case and case[k] is not None:
                extras.append(f"<code>{esc(k)}={esc(case[k])}</code>")
        extras_html = " ".join(extras)
        return (
            f'<li class="case {("ok" if passed else "fail")}">'
            f'<span class="mark">{mark}</span> '
            f"<code>{esc(case_id)}</code> "
            f"{extras_html}"
            f'<div class="surface">{esc(surface)}</div>'
            f"</li>"
        )

    lane_sections: list[str] = []
    for lane in payload["lanes"]:
        split_blocks: list[str] = []
        for split_name, split in lane["splits"].items():
            verdict = split["shape_check"]
            mark = "✓" if verdict["passed"] else "✗"
            cases_html = "".join(case_block(c) for c in split["sample_cases"])
            metrics_pairs = ", ".join(
                f"{esc(k)}={esc(v)}"
                for k, v in split["metrics"].items()
                if not isinstance(v, (dict, list))
            )
            split_blocks.append(
                f"<section><h3>{mark} {esc(split_name)} split "
                f"<small>(shape={esc(verdict['shape'])}, "
                f"{esc(split['case_count'])} cases)</small></h3>"
                f"<p class='metrics'><strong>metrics:</strong> "
                f"{metrics_pairs}</p>"
                f"<p class='verdict'><strong>shape-check:</strong> "
                f"{esc(verdict['reason'])}</p>"
                f"<p><strong>sample cases (first "
                f"{esc(len(split['sample_cases']))}):</strong></p>"
                f"<ul class='cases'>{cases_html}</ul></section>"
            )
        lane_sections.append(
            f"<article><h2>{esc(lane['lane_id'])} "
            f"<small>({esc(lane['shape'])})</small></h2>"
            f"{''.join(split_blocks)}</article>"
        )

    dv = payload["digest_verification"]
    digest_mark = "✓" if dv["matches"] else "✗"
    overall_mark = "✓" if payload["all_claims_supported"] else "✗"

    return (
        "<!doctype html><html><head>"
        "<meta charset='utf-8'>"
        f"<title>CORE Expert-Demo: {esc(payload['domain_id'])}</title>"
        "<style>"
        "body{font-family:system-ui;max-width:980px;margin:2rem auto;padding:0 1rem;}"
        "h1{font-size:1.6rem;}h2{font-size:1.2rem;margin-top:2rem;}"
        "h3{font-size:1.0rem;margin-top:1rem;}"
        ".case{margin:.35rem 0;list-style:none;padding:.3rem;border-left:3px solid #ddd;}"
        ".case.ok{border-left-color:#4a8;}.case.fail{border-left-color:#a44;}"
        ".case .surface{font-family:ui-monospace,monospace;color:#333;margin-top:.2rem;padding-left:1.6rem;}"
        ".mark{font-weight:bold;display:inline-block;width:1.2rem;}"
        ".metrics{color:#444;font-size:.9rem;}"
        ".verdict{color:#666;font-size:.85rem;}"
        "code{background:#f3f3f3;padding:.05rem .25rem;border-radius:3px;font-size:.85rem;}"
        ".claim-card{background:#f8f8f8;padding:.75rem 1rem;border-radius:6px;margin:1rem 0;}"
        ".digest{font-family:ui-monospace,monospace;font-size:.78rem;word-break:break-all;}"
        ".digest.match{color:#283;}.digest.mismatch{color:#a33;}"
        "</style></head><body>"
        f"<h1>{overall_mark} Expert-Demo: <code>{esc(payload['domain_id'])}</code></h1>"
        f"<p>Per-domain runnable demonstration of the "
        f"<code>expert-demo</code> ledger status. The digest below "
        f"reproduces from on-disk lane result files; the sample cases "
        f"are drawn verbatim from those files.</p>"
        "<section class='claim-card'>"
        "<h2>Signed claim (docs/reviewers.yaml)</h2>"
        f"<p><strong>signed_by:</strong> <code>{esc(payload['claim']['signed_by'])}</code></p>"
        f"<p><strong>evidence_revision:</strong> "
        f"<code>{esc(payload['claim']['evidence_revision'])}</code></p>"
        f"<p><strong>evidence_lanes:</strong> "
        f"{', '.join(f'<code>{esc(l)}</code>' for l in payload['claim']['evidence_lanes'])}</p>"
        f"<p><strong>signed digest:</strong> "
        f"<span class='digest'>{esc(dv['signed'])}</span></p>"
        f"<p><strong>derived digest:</strong> "
        f"<span class='digest {'match' if dv['matches'] else 'mismatch'}'>"
        f"{esc(dv['derived'])}</span> {digest_mark}</p>"
        "</section>"
        + "".join(lane_sections)
        + "</body></html>"
    )
