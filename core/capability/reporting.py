from __future__ import annotations

import dataclasses
import glob
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat.cross_pack_grounding import CROSS_PACK_CORPUS_ID, _all_cross_pack_chains
from chat.teaching_grounding import TEACHING_CORPORA, _all_chains_index
from core.capability.domains import (
    DOMAIN_CAPABILITY_CORPORA,
    DOMAIN_CORPORA,
    DOMAIN_OPERATOR_CLAIMS,
    DOMAIN_PACKS,
)
from core.capability.reviewers import (
    ReviewerRegistryError,
    load_reviewer_registry,
)
from core.capability.sources import LEDGER_SOURCES
from core.config import DEFAULT_CONFIG
from language_packs.domain_contract import validate_domain_contract_pack

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CHAINS_PER_OPERATOR_DOMAIN = 8
_TARGET_INTENT_SHAPES = ("cause", "verification", "comparison", "procedure", "correction")
_EXPERT_DOMAIN_STATUSES = ("blocked", "seeded", "grounded", "reasoning-capable", "expert-demo")
_DOMAIN_FOUNDATION_GAPS: dict[str, tuple[str, ...]] = {
    "hebrew_greek_textual_reasoning": (
        "gap:grc_he_glosses_absent",
        "gap:grc_he_chains_absent",
    ),
}

_FLAG_CATALOG: dict[str, dict[str, str]] = {
    "realizer_grounded_authority": {"state": "flag_shipped_default_off", "adr": "ADR-0088"},
    "stop_tokens": {"state": "flag_shipped_default_off", "adr": "ADR-0087"},
    "composed_surface": {"state": "flag_shipped_default_off", "adr": "ADR-0062"},
    "transitive_surface": {"state": "flag_shipped_default_off", "adr": "ADR-0083"},
    "gloss_aware_cause": {"state": "flag_shipped_default_off", "adr": "ADR-0085"},
    "thread_anaphora": {"state": "flag_shipped_default_off", "adr": "P3.2"},
    "discourse_planner": {"state": "flag_shipped_default_off", "adr": "ADR-0089"},
    "compound_intent_dispatch": {"state": "substrate_shipped_flag_missing", "adr": "ADR-0089-C2"},
    "inference_trace": {"state": "substrate_missing", "adr": "ADR-0024"},
}


@dataclass(frozen=True, slots=True)
class CapabilityArtifactQuery:
    lane: str
    split: str
    version: str


def _sha256_json(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _commit_sha() -> str:
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()
    except Exception:
        return "unknown"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _latest_eval_result(lane: str, version: str, split: str) -> dict[str, Any]:
    pattern = _REPO_ROOT / "evals" / lane / "results" / f"{version}_{split}_*.json"
    matches = sorted(glob.glob(str(pattern)))
    if not matches:
        exact = _REPO_ROOT / "evals" / lane / "results" / f"{version}_{split}.json"
        return _load_json(exact)
    return _load_json(Path(matches[-1]))


def _manifest_for_pack(pack_id: str) -> dict[str, Any]:
    path = _REPO_ROOT / "language_packs" / "data" / pack_id / "manifest.json"
    return _load_json(path)


def _pack_lemmas(pack_id: str) -> set[str]:
    root = _REPO_ROOT / "language_packs" / "data" / pack_id
    path = root / "lexicon.jsonl"
    lemmas: set[str] = set()
    if not path.exists():
        return lemmas
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        lemma = row.get("lemma") if isinstance(row, dict) else None
        if isinstance(lemma, str):
            lemmas.add(lemma)
    return lemmas


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _pack_metrics(pack_id: str) -> dict[str, Any]:
    root = _REPO_ROOT / "language_packs" / "data" / pack_id
    manifest = _manifest_for_pack(pack_id)
    lexicon_path = root / str(manifest.get("lexicon", "lexicon.jsonl"))
    glosses_path = root / "glosses.jsonl"
    lemma_count = _count_jsonl(lexicon_path)
    gloss_count = _count_jsonl(glosses_path)
    coverage = (gloss_count / lemma_count) if lemma_count else 0.0
    return {
        "pack_id": pack_id,
        "manifest_present": bool(manifest),
        "checksum_present": bool(manifest.get("checksum")),
        "glosses_checksum_present": bool(manifest.get("glosses_checksum")),
        "lemma_count": lemma_count,
        "gloss_count": gloss_count,
        "gloss_coverage": round(coverage, 4),
        "mount_eligible": bool(manifest and manifest.get("checksum") and coverage >= 0.85),
    }


def _gap_registry() -> dict[str, str]:
    path = _REPO_ROOT / LEDGER_SOURCES.gaps
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        status = "closed" if stripped.startswith("- [x]") else "open"
        marker = stripped.split("`", 2)
        if len(marker) >= 2 and marker[1].startswith("gap:"):
            out[marker[1]] = status
    return out


def _operator_family_for_chain(intent: str, connective: str) -> str:
    intent_l = intent.strip().lower()
    conn_l = connective.strip().lower()
    if intent_l == "verification" or conn_l in {"supports", "verifies", "confirms"}:
        return "proof_chain"
    if intent_l == "cause" or conn_l in {"causes", "grounds", "reveals", "requires", "enables"}:
        return "causal"
    if "contradict" in conn_l or "opposes" in conn_l:
        return "contradiction"
    if "transitive" in conn_l or "entails" in conn_l:
        return "transitive"
    if "modal" in conn_l or "permits" in conn_l or "requires" in conn_l:
        return "modal"
    return "unclassified"


def _domain_chain_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for corpus_id, rel_path in sorted(DOMAIN_CAPABILITY_CORPORA.items()):
        path = _REPO_ROOT / rel_path
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("review_status") != "reviewed":
                continue
            intent = str(row.get("intent", "")).strip().lower()
            connective = str(row.get("connective", "")).strip()
            operator_family = str(row.get("operator_family") or "").strip() or _operator_family_for_chain(intent, connective)
            domain = str(row.get("domain") or "").strip()
            if domain not in DOMAIN_PACKS:
                continue
            subject = str(row.get("subject") or "").strip()
            obj = str(row.get("object") or "").strip()
            subject_pack = str(row.get("subject_pack_id") or "").strip()
            object_pack = str(row.get("object_pack_id") or "").strip()
            if subject_pack and subject not in _pack_lemmas(subject_pack):
                continue
            if object_pack and obj not in _pack_lemmas(object_pack):
                continue
            out.append(
                {
                    "chain_id": str(row.get("chain_id") or f"{corpus_id}:{line_no}"),
                    "corpus_id": corpus_id,
                    "domain": domain,
                    "intent": intent,
                    "connective": connective,
                    "operator_family": operator_family,
                    "subject_pack_id": subject_pack,
                    "object_pack_id": object_pack,
                }
            )
    return out


def _chain_inventory() -> dict[str, Any]:
    chains = list(_all_chains_index().values())
    chains.extend(_all_cross_pack_chains())
    domain_records = _domain_chain_records()
    corpus_pack: dict[str, str] = {spec.corpus_id: spec.pack_id for spec in TEACHING_CORPORA}
    by_intent: dict[str, int] = {}
    by_connective: dict[str, int] = {}
    by_operator: dict[str, int] = {}
    by_corpus: dict[str, int] = {}
    by_pack: dict[str, int] = {}
    by_domain_operator: dict[str, dict[str, int]] = {}
    by_domain_intent: dict[str, dict[str, int]] = {}
    corpus_domains: dict[str, list[str]] = {}
    for domain, corpora in DOMAIN_CORPORA.items():
        for corpus_id in corpora:
            corpus_domains.setdefault(corpus_id, []).append(domain)
    for chain in chains:
        by_intent[chain.intent] = by_intent.get(chain.intent, 0) + 1
        by_connective[chain.connective] = by_connective.get(chain.connective, 0) + 1
        op = _operator_family_for_chain(chain.intent, chain.connective)
        by_operator[op] = by_operator.get(op, 0) + 1
        by_corpus[chain.corpus_id] = by_corpus.get(chain.corpus_id, 0) + 1
        if hasattr(chain, "subject_pack_id"):
            for pack_id in (chain.subject_pack_id, chain.object_pack_id):
                by_pack[pack_id] = by_pack.get(pack_id, 0) + 1
        else:
            pack_id = corpus_pack.get(chain.corpus_id, "unknown")
            by_pack[pack_id] = by_pack.get(pack_id, 0) + 1
        for domain in corpus_domains.get(chain.corpus_id, ()):
            by_domain_operator.setdefault(domain, {})
            by_domain_operator[domain][op] = by_domain_operator[domain].get(op, 0) + 1
            by_domain_intent.setdefault(domain, {})
            by_domain_intent[domain][chain.intent] = by_domain_intent[domain].get(chain.intent, 0) + 1
    for record in domain_records:
        intent = str(record["intent"])
        connective = str(record["connective"])
        op = str(record["operator_family"])
        domain = str(record["domain"])
        corpus_id = str(record["corpus_id"])
        by_intent[intent] = by_intent.get(intent, 0) + 1
        by_connective[connective] = by_connective.get(connective, 0) + 1
        by_operator[op] = by_operator.get(op, 0) + 1
        by_corpus[corpus_id] = by_corpus.get(corpus_id, 0) + 1
        by_domain_operator.setdefault(domain, {})
        by_domain_operator[domain][op] = by_domain_operator[domain].get(op, 0) + 1
        by_domain_intent.setdefault(domain, {})
        by_domain_intent[domain][intent] = by_domain_intent[domain].get(intent, 0) + 1
        for pack_id in (record.get("subject_pack_id"), record.get("object_pack_id")):
            if pack_id:
                by_pack[str(pack_id)] = by_pack.get(str(pack_id), 0) + 1
    by_domain = {
        domain: sum(by_corpus.get(corpus_id, 0) for corpus_id in DOMAIN_CORPORA.get(domain, ()))
        for domain in DOMAIN_PACKS
    }
    return {
        "chains": chains,
        "by_intent": dict(sorted(by_intent.items())),
        "by_connective": dict(sorted(by_connective.items())),
        "by_operator_family": dict(sorted(by_operator.items())),
        "by_corpus": dict(sorted(by_corpus.items())),
        "by_pack": dict(sorted(by_pack.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "by_domain_operator_family": {
            domain: dict(sorted(counts.items()))
            for domain, counts in sorted(by_domain_operator.items())
        },
        "by_domain_intent_shape": {
            domain: dict(sorted(counts.items()))
            for domain, counts in sorted(by_domain_intent.items())
        },
    }


def _pack_hash(pack_ids: tuple[str, ...]) -> str:
    material: list[tuple[str, str, str, str]] = []
    for pack_id in sorted(pack_ids):
        m = _manifest_for_pack(pack_id)
        mastery_hash = str(m.get("mastery_report_sha256", ""))
        material.append(
            (
                pack_id,
                str(m.get("checksum", "")),
                str(m.get("glosses_checksum", "")),
                mastery_hash,
            )
        )
    return hashlib.sha256(repr(tuple(material)).encode("utf-8")).hexdigest()


def _config_hash() -> str:
    material = {
        "artifact_contract_version": 1,
        "runtime_config": dataclasses.asdict(DEFAULT_CONFIG),
    }
    return _sha256_json(material)


def chain_report() -> dict[str, Any]:
    inventory = _chain_inventory()
    teaching_counts: dict[str, int] = dict(inventory["by_corpus"])
    for spec in TEACHING_CORPORA:
        teaching_counts.setdefault(spec.corpus_id, 0)
    teaching_counts.setdefault(CROSS_PACK_CORPUS_ID, 0)
    active = sum(teaching_counts.values())
    operator_count = 5
    domain_count = len(DOMAIN_PACKS)
    required = _CHAINS_PER_OPERATOR_DOMAIN * operator_count * domain_count
    return {
        "active_chains": active,
        "by_corpus": teaching_counts,
        "by_intent_shape": inventory["by_intent"],
        "by_connective": inventory["by_connective"],
        "by_operator_family": inventory["by_operator_family"],
        "by_pack": inventory["by_pack"],
        "by_domain": inventory["by_domain"],
        "by_domain_operator_family": inventory["by_domain_operator_family"],
        "by_domain_intent_shape": inventory["by_domain_intent_shape"],
        "target_intent_shapes": list(_TARGET_INTENT_SHAPES),
        "missing_target_intent_shapes": [
            shape for shape in _TARGET_INTENT_SHAPES if shape not in inventory["by_intent"]
        ],
        "formula": {
            "operators": operator_count,
            "domains": domain_count,
            "chains_per_operator_domain": _CHAINS_PER_OPERATOR_DOMAIN,
            "chains_required": required,
            "chains_present": active,
            "chains_remaining": max(0, required - active),
        },
    }


def flag_report() -> dict[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = {
        "flag_shipped_default_off": [],
        "substrate_shipped_flag_missing": [],
        "substrate_missing": [],
    }
    for name, meta in sorted(_FLAG_CATALOG.items()):
        grouped[meta["state"]].append({"flag": name, "adr": meta["adr"]})
    return grouped


def ledger_report() -> dict[str, Any]:
    sources = LEDGER_SOURCES
    resolved = sources.resolve(_REPO_ROOT)
    missing_sources = [k for k, p in resolved.items() if not p.exists()]
    gaps = _gap_registry()
    chain_inventory = _chain_inventory()
    domain_rows: list[dict[str, Any]] = []
    for domain, packs in DOMAIN_PACKS.items():
        pack_metrics = [_pack_metrics(pack_id) for pack_id in packs]
        domain_contracts = [
            validate_domain_contract_pack(pack_id).as_dict()
            for pack_id in packs
        ]
        domain_gaps: list[str] = []
        if not packs:
            domain_gaps.append(f"gap:{domain}_pack_absent")
        domain_gaps.extend(_DOMAIN_FOUNDATION_GAPS.get(domain, ()))
        domain_gaps.extend(
            f"gap:{metric['pack_id']}_gloss_coverage_below_threshold"
            for metric in pack_metrics
            if metric["manifest_present"] and not metric["mount_eligible"]
        )
        domain_gaps.extend(f"gap:ledger-source-missing:{src}" for src in missing_sources)
        seeded = bool(packs) and all(p["manifest_present"] and p["checksum_present"] for p in pack_metrics)
        grounded = seeded and all(p["mount_eligible"] for p in pack_metrics)
        claimed = DOMAIN_OPERATOR_CLAIMS.get(domain, ())
        op_counts = {
            op: int(chain_inventory["by_domain_operator_family"].get(domain, {}).get(op, 0))
            for op in claimed
        }
        op_required = {op: _CHAINS_PER_OPERATOR_DOMAIN for op in claimed}
        domain_gaps.extend(
            f"gap:{domain}_{op}_chains_below_threshold"
            for op in claimed
            if op_counts[op] < op_required[op]
        )
        intent_shapes_present = len(chain_inventory["by_domain_intent_shape"].get(domain, {}))
        holdout_present = (_REPO_ROOT / "evals" / "cognition" / "holdouts" / "cases_plaintext.jsonl").exists()
        if intent_shapes_present < 3:
            domain_gaps.append(f"gap:{domain}_intent_shapes_below_threshold")
        if not holdout_present:
            domain_gaps.append(f"gap:{domain}_holdout_absent")
        domain_gaps = sorted(dict.fromkeys(domain_gaps))
        open_gaps = [gap for gap in domain_gaps if gaps.get(gap, "open") != "closed"]
        reasoning_capable = (
            grounded
            and bool(claimed)
            and all(op_counts[op] >= op_required[op] for op in claimed)
            and intent_shapes_present >= 3
            and holdout_present
        )
        expert_demo = False
        if reasoning_capable:
            public = _latest_eval_result("cognition", "v1", "public").get("metrics", {})
            holdout = _latest_eval_result("cognition", "v1", "holdout").get("metrics", {})
            expert_demo = bool(
                public
                and holdout
                and public.get("surface_groundedness", 0) >= 0.95
                and holdout.get("surface_groundedness", 0) >= 0.95
                and public.get("term_capture_rate", 0) >= 0.85
                and holdout.get("term_capture_rate", 0) >= 0.85
                and public.get("intent_accuracy", 0) >= 0.95
                and holdout.get("intent_accuracy", 0) >= 0.95
                and public.get("versor_closure_rate", 0) >= 1.0
                and holdout.get("versor_closure_rate", 0) >= 1.0
            )
        if expert_demo:
            status = "expert-demo"
        elif reasoning_capable:
            status = "reasoning-capable"
        elif grounded:
            status = "grounded"
        elif seeded:
            status = "seeded"
        else:
            status = "blocked"
        if open_gaps and status == "blocked":
            blocked_lift = "gap closes and seeded predicate passes"
        elif open_gaps:
            blocked_lift = "open gaps explain missing next-status predicates"
        else:
            blocked_lift = "no open gap; next status requires failing predicate to pass"
        domain_rows.append(
            {
                "domain": domain,
                "status": status,
                "status_order": list(_EXPERT_DOMAIN_STATUSES),
                "packs": list(packs),
                "pack_metrics": pack_metrics,
                "domain_contracts": domain_contracts,
                "corpora": list(DOMAIN_CORPORA.get(domain, ())),
                "claimed_operators": list(DOMAIN_OPERATOR_CLAIMS.get(domain, ())),
                "operator_chain_coverage": {
                    op: {
                        "chains_present": op_counts[op],
                        "chains_required": op_required[op],
                        "ready": op_counts[op] >= op_required[op],
                    }
                    for op in claimed
                },
                "intent_shapes_present": intent_shapes_present,
                "intent_shapes_required": 3,
                "holdout_present": holdout_present,
                "predicates": {
                    "seeded": seeded,
                    "grounded": grounded,
                    "reasoning_capable": reasoning_capable,
                    "expert_demo": expert_demo,
                },
                "known_gaps": domain_gaps,
                "open_gaps": open_gaps,
                "blocked_lift": blocked_lift,
            }
        )
    eval_files = glob.glob(str(_REPO_ROOT / "evals" / "*" / "results" / "v*_*.json"))
    mastery_files = glob.glob(str(_REPO_ROOT / "packs" / "**" / "*.mastery_report.json"), recursive=True)
    identity_files = glob.glob(str(_REPO_ROOT / "evals" / "identity_divergence" / "results" / "*.json"))
    refusal_files = glob.glob(str(_REPO_ROOT / "evals" / "refusal_calibration" / "results" / "*.json"))
    audit_files = glob.glob(str(_REPO_ROOT / "evals" / "audit_tour" / "results" / "*.json"))
    return {
        "sources": dataclasses.asdict(sources),
        "missing_sources": missing_sources,
        "thresholds": {
            "gloss_coverage": 0.85,
            "surface_groundedness": 0.95,
            "term_capture": 0.85,
            "intent_accuracy": 0.95,
            "versor_closure_rate": 1.0,
            "replay_determinism": 0.99,
        },
        "evidence_counts": {
            "eval_results": len(eval_files),
            "mastery_reports": len(mastery_files),
            "identity_div": len(identity_files),
            "refusal_cal": len(refusal_files),
            "audit_tour": len(audit_files),
            "pack_measurements_present": (_REPO_ROOT / LEDGER_SOURCES.pack_measurements).exists(),
            "reviewers_present": (_REPO_ROOT / LEDGER_SOURCES.reviewers).exists(),
            "reviewer_registry": _reviewer_registry_status(),
            "gaps_present": (_REPO_ROOT / LEDGER_SOURCES.gaps).exists(),
        },
        "domains": domain_rows,
        "day1_expected_output": True,
    }


def artifact_report(query: CapabilityArtifactQuery) -> dict[str, Any]:
    commit_sha = _commit_sha()
    cfg_hash = _config_hash()
    p_hash = _pack_hash(tuple(sorted({p for packs in DOMAIN_PACKS.values() for p in packs})))
    artifact_material = {
        "artifact_contract_version": 1,
        "commit_sha": commit_sha,
        "pack_hash": p_hash,
        "eval_lane": query.lane,
        "version": query.version,
        "split": query.split,
        "config_hash": cfg_hash,
    }
    artifact_id = _sha256_json(artifact_material)
    exact = _REPO_ROOT / "evals" / query.lane / "results" / f"{query.version}_{query.split}.json"
    matches = sorted(glob.glob(str(_REPO_ROOT / "evals" / query.lane / "results" / f"{query.version}_{query.split}_*.json")))
    result_path = Path(matches[-1]) if matches else exact
    if not result_path.exists():
        return {
            "artifact_id": artifact_id,
            "exists": False,
            "would_run": artifact_material,
            "result_path": str(result_path),
        }
    return {
        "artifact_id": artifact_id,
        "exists": True,
        "result_path": str(result_path),
        "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
    }


def evidence_plan_report() -> dict[str, Any]:
    commit_sha = _commit_sha()
    cfg_hash = _config_hash()
    pack_hash = _pack_hash(tuple(sorted({p for packs in DOMAIN_PACKS.values() for p in packs})))
    lanes = (
        ("pack_validation", "packs", "public"),
        ("eval_matrix", "cognition", "public"),
        ("eval_matrix", "cognition", "holdout"),
        ("replay_sweep", "cognition", "public"),
        ("vault_benchmark", "vault", "public"),
        ("curriculum_experiment", "capability", "dev"),
    )
    jobs: list[dict[str, Any]] = []
    for job_type, lane, split in lanes:
        material = {
            "artifact_contract_version": 1,
            "commit_sha": commit_sha,
            "pack_hash": pack_hash,
            "job_type": job_type,
            "eval_lane": lane,
            "version": "v1",
            "split": split,
            "config_hash": cfg_hash,
        }
        jobs.append(
            {
                "job_id": _sha256_json(material),
                "job_type": job_type,
                "lane": lane,
                "version": "v1",
                "split": split,
                "artifact_key": material,
                "execution": "local-or-worker",
                "promotion": "reviewed-mainline-only",
                "mutates_packs": False,
            }
        )
    return {
        "artifact_contract_version": 1,
        "commit_sha": commit_sha,
        "pack_hash": pack_hash,
        "config_hash": cfg_hash,
        "scheduler": "local-first",
        "workers_promote_packs": False,
        "jobs": jobs,
    }


def _reviewer_registry_status() -> dict[str, Any]:
    """Report Reviewer Registry v1 validity for the capability ledger (ADR-0092).

    Returns a structured object containing the parsed schema version,
    reviewer count, and a list of registered reviewer ids. If the
    registry is missing or fails ADR-0092 schema validation, the object
    reports ``valid: False`` and names the error rather than raising,
    so the ledger surface remains generatable on a broken registry.
    """
    path = _REPO_ROOT / LEDGER_SOURCES.reviewers
    if not path.exists():
        return {
            "valid": False,
            "error": "reviewers.yaml not found",
            "schema_version": None,
            "reviewer_count": 0,
            "reviewer_ids": [],
        }
    try:
        registry = load_reviewer_registry(path)
    except ReviewerRegistryError as exc:
        return {
            "valid": False,
            "error": str(exc),
            "schema_version": None,
            "reviewer_count": 0,
            "reviewer_ids": [],
        }
    return {
        "valid": True,
        "error": None,
        "schema_version": registry.schema_version,
        "reviewer_count": len(registry.reviewers),
        "reviewer_ids": sorted(r.reviewer_id for r in registry.reviewers),
    }
