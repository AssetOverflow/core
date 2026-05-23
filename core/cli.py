"""Command line interface for the CORE versor engine."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn


# The `core` console script may be installed through stale editable metadata while
# this repo is moving quickly. Ensure sibling top-level packages such as
# alignment/, morphology/, and sensorium/ are importable from the checked-out
# source tree before any runtime imports execute.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CORE_RS_DIR = _REPO_ROOT / "core-rs"
_CORE_RS_MANIFEST = _CORE_RS_DIR / "Cargo.toml"

DESCRIPTION = "CORE versor engine command suite."
EPILOG = "Examples:\n  core chat\n  core pulse \"What is truth?\"\n  core pulse --no-glove --json \"Compare knowledge and wisdom\"\n  core bench\n  core bench --suite all\n  core bench --suite all --json --report bench_all.json\n  core bench --suite determinism --runs 50\n  core bench --suite speedup --json\n  core trace \"word beginning truth\"\n  core trace --output-language grc --frame-pack grc --json \"logos\"\n  core rust status\n  core rust build\n  core oov covenant\n  core pack list\n  core pack verify en_minimal_v1\n  core teaching audit\n  core teaching audit --json\n  core teaching gaps --top 10\n  core teaching queue --threshold 3\n  core teaching propose <candidate-jsonl-path>\n  core teaching proposals --state pending\n  core teaching review <proposal_id> --accept --review-date 2026-05-18\n  core teaching supersede cause_light_reveals_truth --subject light --intent cause --connective grounds --object truth --review-date 2026-05-18\n  core teaching supersessions\n  core teaching supersessions --json\n  core test --suite fast -q\n  core test --suite pulse -q\n  core test --suite proof -q\n  core test --suite cognition -q\n  core test -- tests/test_alignment_graph.py -q\n  core demo audit-tour\n  core demo register-tour\n  core demo anchor-lens-tour\n  core demo orthogonality-tour\n  core demo pack-measurements\n  core demo long-context-comparison\n  core demo anti-regression\n  core demo learning-loop\n  core demo articulation\n  core demo conversation\n  core demo conversation --no-stream\n  core demo all\n  core demo adr-0024-chain\n  core eval --list\n  core eval cognition\n  core eval cognition --json --save\n  core eval cognition --split dev --version v1\n  core eval cognition --split holdout"

_TEST_SUITES: dict[str, tuple[str, ...]] = {
    "fast": (
        "tests/test_cli_test_suites.py",
        "tests/test_runtime_config.py",
        "tests/test_core_semantic_seed_pack.py",
        "tests/test_intent_proposition_graph.py",
        "tests/test_articulation_realizer_v2.py",
        "tests/test_reviewed_teaching_loop.py",
        "tests/test_cognitive_eval_harness.py",
    ),
    "smoke": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_cognitive_turn_pipeline.py",
        "tests/test_architectural_invariants.py",
    ),
    "runtime": (
        "tests/test_chat_runtime.py",
        "tests/test_achat.py",
        "tests/test_runtime_config.py",
        "tests/test_session_coherence.py",
    ),
    "cognition": (
        "tests/test_intent_proposition_graph.py",
        "tests/test_cognitive_turn_pipeline.py",
        "tests/test_articulation_realizer_v2.py",
        "tests/test_semantic_realizer_integration.py",
        "tests/test_cognitive_eval_harness.py",
        "tests/test_deterministic_hash.py",
        "tests/test_morphology_irregular.py",
        "tests/test_realizer_quantifier_agreement.py",
        "tests/test_benchmarks_profiler.py",
        "tests/test_compose_relations.py",
        "tests/test_replay_vs_llm_benchmark.py",
    ),
    "teaching": (
        "tests/test_reviewed_teaching_loop.py",
        "tests/test_pipeline_teaching_integration.py",
        "tests/test_epistemic_invariants.py",
    ),
    "packs": (
        "tests/test_core_semantic_seed_pack.py",
        "tests/test_adr_0127_pack_ratification.py",
    ),
    "algebra": (
        "tests/test_versor_closure.py",
        "tests/test_holonomy.py",
        "tests/test_holonomy_resonance.py",
        "tests/test_energy.py",
        "tests/test_motor.py",
        "tests/test_null_cone.py",
        "tests/test_vault_recall.py",
        "tests/test_vault_recall_vectorised.py",
        "tests/test_vault_recall_rust_parity.py",
        "tests/test_cga_inner_rust_parity.py",
        "tests/test_geometric_product_rust_parity.py",
        "tests/test_versor_condition_rust_parity.py",
        "tests/test_versor_apply_rust_parity.py",
    ),
    "pulse": (
        "tests/test_pulse_integration.py",
        "tests/test_graph_diffusion.py",
    ),
    "formation": (
        "tests/formation",
    ),
    "proof": (
        "tests/test_proof_properties.py",
    ),
    # ADR-0024 chain suites (Phases 2-6).  Each phase has its own
    # contract tests so investors / reviewers can run them
    # independently; ``adr-0024`` runs the full chain end-to-end.
    "refusal": (
        "tests/test_refusal_contract.py",
    ),
    "margin": (
        "tests/test_margin_admissibility.py",
    ),
    "rotor": (
        "tests/test_rotor_admissibility.py",
    ),
    "inner-loop": (
        "tests/test_inner_loop_admissibility.py",
        "tests/test_inner_loop_phase2.py",
        "tests/test_inner_loop_phase3.py",
        "tests/test_inner_loop_phase4.py",
    ),
    "phase5": (
        "tests/test_phase5_corpus.py",
    ),
    "phase6": (
        "tests/test_phase6_demo.py",
    ),
    "adr-0024": (
        "tests/test_refusal_contract.py",
        "tests/test_margin_admissibility.py",
        "tests/test_rotor_admissibility.py",
        "tests/test_inner_loop_admissibility.py",
        "tests/test_inner_loop_phase2.py",
        "tests/test_inner_loop_phase3.py",
        "tests/test_inner_loop_phase4.py",
        "tests/test_phase5_corpus.py",
        "tests/test_phase6_demo.py",
    ),
    # ADR-0126 P6 — measurement harness for the GSM8K candidate-graph
    # parser exit criterion.  ``wrong == 0`` is a hard gate (Obligation
    # #4: refuse rather than confabulate).
    "math": (
        "tests/test_adr_0126_train_sample_runner.py",
    ),
    "full": ("tests/",),
}


def _run(*args: str, check: bool = False, cwd: Path | None = None) -> int:
    """Run a child command and return its exit code."""
    completed = subprocess.run(args, check=check, text=True, cwd=cwd)
    return int(completed.returncode)


def _die(message: str, *, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _print_runtime_import_hint(exc: BaseException) -> NoReturn:
    _die(
        "runtime import failed. Run `core doctor` to inspect packaging. Root cause: "
        f"{exc.__class__.__name__}: {exc}",
        code=1,
    )


def _runtime_config_from_args(args: argparse.Namespace):
    from core.config import DEFAULT_CONFIG, RuntimeConfig

    output_language = args.output_language
    frame_pack = args.frame_pack or output_language
    input_packs = tuple(args.pack) if getattr(args, "pack", None) else DEFAULT_CONFIG.input_packs
    return RuntimeConfig(
        input_packs=input_packs,
        output_language=output_language,
        frame_pack=frame_pack,
        max_tokens=args.max_tokens,
        allow_cross_language_recall=not args.no_cross_language_recall,
        allow_cross_language_generation=args.allow_cross_language_generation,
        vault_reproject_interval=args.vault_reproject_interval,
        use_salience=not args.no_salience,
        salience_top_k=args.salience_top_k,
        inhibition_threshold=args.inhibition_threshold,
        inner_loop_admissibility=getattr(args, "inner_loop_admissibility", False),
        admissibility_threshold=getattr(args, "admissibility_threshold", 0.0),
        identity_pack=getattr(args, "identity", "") or "",
        register_pack_id=(getattr(args, "register", None) or None),
        anchor_lens_id=(getattr(args, "anchor_lens", None) or None),
    )


def _print_identity_packs(use_json: bool) -> int:
    """Print discoverable identity packs.  Returns process exit code."""
    from packs.identity.loader import available_packs

    packs = available_packs()
    if use_json:
        import json as _json
        print(_json.dumps(packs, indent=2, sort_keys=True))
        return 0
    if not packs:
        print("(no identity packs found on default search path)")
        return 0
    pack_w = max(len("pack_id"), max(len(str(p["pack_id"])) for p in packs))
    ver_w = max(len("version"), max(len(str(p["version"])) for p in packs))
    print(f"{'pack_id':<{pack_w}}  {'version':<{ver_w}}  ratified  description")
    print(f"{'-' * pack_w}  {'-' * ver_w}  --------  -----------")
    for p in packs:
        flag = "yes" if p["ratified"] else "no "
        print(
            f"{str(p['pack_id']):<{pack_w}}  "
            f"{str(p['version']):<{ver_w}}  "
            f"{flag:<8}  {p['description']}"
        )
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """Launch a readline REPL backed by ChatRuntime."""
    if getattr(args, "list_identity_packs", False):
        return _print_identity_packs(use_json=getattr(args, "json", False))
    try:
        from chat.runtime import ChatRuntime
        # ADR-0041 — operator-facing verdict readout.  Imported lazily
        # so a broken telemetry module doesn't block REPL startup.
        from chat.telemetry import format_verdict_summary
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)

    try:
        runtime = ChatRuntime(config=_runtime_config_from_args(args))
    except Exception as exc:  # noqa: BLE001 — surface pack-load errors
        from packs.anchor_lens.loader import AnchorLensError
        from packs.register.loader import RegisterPackError
        if isinstance(exc, RegisterPackError):
            _die(f"invalid --register pack id: {exc}", code=2)
        if isinstance(exc, AnchorLensError):
            _die(f"invalid --anchor-lens pack id: {exc}", code=2)
        raise
    show_verdicts = bool(getattr(args, "show_verdicts", False))
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            print()
            break
        if text in {"quit", "exit"}:
            break
        if not text:
            continue
        try:
            response = runtime.chat(text)
        except (KeyError, ValueError) as exc:
            print(f"[{exc}]", file=sys.stderr)
            continue
        print(response.surface)
        if show_verdicts:
            # ADR-0041 — print the verdict bundle to stderr so the
            # response surface on stdout stays parseable by tooling
            # that pipes through ``core chat``.
            summary = format_verdict_summary(response.verdicts)
            if summary:
                print(summary, file=sys.stderr)
    return 0


def _pytest_args_for_suite(suite: str, extra_args: Sequence[str]) -> list[str]:
    paths = _TEST_SUITES[suite]
    forwarded = list(extra_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    return [*paths, *forwarded]


def _xdist_available() -> bool:
    """Return True iff ``pytest-xdist`` is importable."""
    try:
        import xdist  # noqa: F401
    except ImportError:
        return False
    return True


def _maybe_inject_xdist(forwarded: list[str], suite: str | None) -> list[str]:
    """Inject ``-n auto`` for suites large enough to benefit from
    parallelism.  ``--suite full`` always gets it (when xdist is
    installed); curated suites stay single-process because they are
    already small and the worker-spawn overhead is net-negative on
    them.  Operators can override by passing ``-n <N>`` or
    ``--no-parallel`` (here stripped) in ``args``."""
    if not _xdist_available():
        return forwarded
    # Honour explicit operator override.
    if any(a.startswith("-n") or a == "--dist" for a in forwarded):
        return forwarded
    if suite == "full":
        return ["-n", "auto", *forwarded]
    return forwarded


def cmd_test(args: argparse.Namespace) -> int:
    """Run pytest through curated suite aliases or direct passthrough args."""
    default_args = ["-q", "--tb=short"]
    if args.list_suites:
        for name in sorted(_TEST_SUITES):
            print(name)
        return 0
    if args.suite:
        forwarded = _pytest_args_for_suite(args.suite, args.args or default_args)
    else:
        forwarded = list(args.args or default_args)
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
    forwarded = _maybe_inject_xdist(forwarded, args.suite)
    return _run(sys.executable, "-m", "pytest", *forwarded)


def cmd_check(args: argparse.Namespace) -> int:
    """Run ruff over selected project paths."""
    targets = args.paths or [
        "algebra",
        "alignment",
        "chat",
        "core",
        "field",
        "generate",
        "ingest",
        "language_packs",
        "morphology",
        "persona",
        "sensorium",
        "session",
        "vault",
        "vocab",
        "tests",
    ]
    return _run(sys.executable, "-m", "ruff", "check", *targets)


def _runtime_for_trace(args: argparse.Namespace):
    try:
        from chat.runtime import ChatRuntime
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)
    try:
        return ChatRuntime(config=_runtime_config_from_args(args))
    except Exception as exc:
        _die(
            "failed to initialize ChatRuntime. Check mounted language packs with "
            "`core pack list` and `core pack verify <pack_id>`. Root cause: "
            f"{exc.__class__.__name__}: {exc}",
            code=1,
        )


def _trace_payload(text: str, resp: Any, runtime: Any) -> dict[str, Any]:
    proposition = resp.proposition
    articulation = resp.articulation
    vault = runtime.session.vault
    payload: dict[str, Any] = {
        "input": text,
        "surface": resp.surface,
        "walk_surface": resp.walk_surface,
        "output_language": resp.output_language,
        "frame_pack": resp.frame_pack,
        "dialogue_role": str(resp.dialogue_role),
        "versor_condition": float(resp.versor_condition),
        "salience_top_k": resp.salience_top_k,
        "candidates_used": resp.candidates_used,
        "articulation": {
            "surface": articulation.surface,
            "frame_id": articulation.frame_id,
            "subject": articulation.subject,
            "predicate": articulation.predicate,
            "object": articulation.object,
            "output_language": articulation.output_language,
        },
        "proposition": {
            "surface": proposition.surface,
            "frame_id": proposition.frame_id,
            "subject": proposition.subject,
            "predicate": proposition.predicate,
            "object": proposition.object_,
            "relation_norm": proposition.relation_norm,
        },
        "vault_entries": len(vault),
        "vault_reproject_every": vault.reproject_interval,
        "vault_store_count": vault.store_count,
        "oov_grounded": list(getattr(runtime.session.vocab, "unknown_token_log", [])),
    }
    return payload


def _print_trace(payload: dict[str, Any]) -> None:
    print(f"input          : {payload['input']}")
    print(f"surface        : {payload['surface']}")
    print(f"raw_walk       : {payload['walk_surface']}")
    print(f"output_language: {payload['output_language']}")
    print(f"frame_pack     : {payload['frame_pack']}")
    print(f"salience_top_k : {payload['salience_top_k']}")
    print(f"candidates_used: {payload['candidates_used']}")
    print(f"dialogue_role  : {payload['dialogue_role']}")
    print(f"versor_cond    : {payload['versor_condition']:.2e}")
    articulation = payload["articulation"]
    print(f"articulation   : {articulation['surface']!r}")
    print(f"  subject      : {articulation['subject']!r}")
    print(f"  predicate    : {articulation['predicate']!r}")
    if articulation.get("object"):
        print(f"  object       : {articulation['object']!r}")
    proposition = payload["proposition"]
    print(f"proposition    : {proposition['surface']!r}")
    print(f"  frame_id     : {proposition['frame_id']}")
    print(f"  subject      : {proposition['subject']!r}")
    print(f"  predicate    : {proposition['predicate']!r}")
    if proposition.get("object"):
        print(f"  object       : {proposition['object']!r}")
    print(f"  relation_norm: {proposition['relation_norm']:.4f}")
    print(f"vault_entries  : {payload['vault_entries']}")
    print(f"vault_reproject_every: {payload['vault_reproject_every']}")
    print(f"vault_store_count    : {payload['vault_store_count']}")
    oov_entries = payload["oov_grounded"]
    if oov_entries:
        print(f"oov_grounded   : {len(oov_entries)} token(s)")
        for entry in oov_entries:
            print(f"  {entry}")


def cmd_trace(args: argparse.Namespace) -> int:
    """Trace one chat turn and print field telemetry."""
    text = " ".join(args.text).strip()
    if not text:
        _die("trace requires input text. Try: core trace \"word beginning truth\"")

    runtime = _runtime_for_trace(args)
    try:
        response = runtime.chat(text, max_tokens=args.max_tokens)
    except Exception as exc:
        _die(f"trace failed: {exc.__class__.__name__}: {exc}", code=1)

    payload = _trace_payload(text, response, runtime)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_trace(payload)
    return 0


def cmd_oov(args: argparse.Namespace) -> int:
    """Ground a single unknown token and show constructed versor info."""
    try:
        from algebra.versor import versor_condition
        from chat.runtime import ChatRuntime
    except Exception as exc:  # pragma: no cover - exercised by CLI in broken envs
        _print_runtime_import_hint(exc)

    runtime = ChatRuntime(config=_runtime_config_from_args(args))
    vocab = runtime.session.vocab

    try:
        versor = vocab.get_versor(args.token)
    except KeyError:
        from ingest.gate import inject

        state = inject([args.token], vocab)
        print(f"{args.token!r} — grounded as transient")
        print(f"  versor_cond : {versor_condition(state.F):.2e}")
        oov_log = getattr(vocab, "unknown_token_log", [])
        if oov_log:
            last = oov_log[-1]
            print(f"  root_used   : {last.get('root_used', '?')}")
            print(f"  ops_applied : {last.get('operators_applied', [])}")
    else:
        print(f"{args.token!r} is already in the manifold")
        print(f"  versor_cond: {versor_condition(versor):.2e}")
    return 0


def cmd_capability_chains(args: argparse.Namespace) -> int:
    from core.capability import chain_report

    report = chain_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
    return 0


def cmd_capability_flags(args: argparse.Namespace) -> int:
    from core.capability import flag_report

    report = flag_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
    return 0


def cmd_capability_ledger(args: argparse.Namespace) -> int:
    from core.capability import ledger_report

    report = ledger_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
    return 0


def cmd_capability_artifact(args: argparse.Namespace) -> int:
    from core.capability import CapabilityArtifactQuery, artifact_report

    report = artifact_report(
        CapabilityArtifactQuery(lane=args.lane, split=args.split, version=args.version)
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
    return 0


def cmd_capability_domain_contract(args: argparse.Namespace) -> int:
    """ADR-0093 domain-contract dry-run validator.

    Default behavior runs the nine ADR-0091 predicates plus eval-lane
    artifact resolution and exits non-zero on any predicate failure.
    The legacy structural-only output remains available via
    ``--structural-only`` for callers that depend on the prior shape.
    """
    from language_packs.domain_contract import validate_domain_contract_pack

    if getattr(args, "structural_only", False):
        report = validate_domain_contract_pack(args.pack_id).as_dict()
        print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
        return 0 if report["valid"] else 1

    from core.capability.domain_contract_predicates import evaluate_domain_contract

    predicate_report = evaluate_domain_contract(args.pack_id).as_dict()
    print(
        json.dumps(predicate_report, indent=2, sort_keys=True)
        if args.json
        else predicate_report
    )
    return 0 if predicate_report["all_passed"] else 1


def cmd_capability_evidence_plan(args: argparse.Namespace) -> int:
    from core.capability import evidence_plan_report

    report = evidence_plan_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report)
    return 0


def cmd_capability_perturbation(args: argparse.Namespace) -> int:
    """ADR-0114a Obligation #5 — reasoning-isolation perturbation suite for B3.

    Generates and scores invariance-preserving and invariance-breaking
    perturbations over B3 (bounded grammar) expected-correct cases.
    Writes the report to ``evals/obligation_5_perturbation/<lane_id>.json``.
    Exit 0 iff both preserving_rate == 1.0 AND breaking_rate == 1.0.
    """
    from pathlib import Path as _Path
    from core.capability.perturbation_b3 import (
        validate_perturbation_suite,
        emit_perturbation_report,
    )

    lane_id = args.lane_id
    report = validate_perturbation_suite(lane_id=lane_id)

    out_dir = _Path(__file__).resolve().parent.parent / "evals" / "obligation_5_perturbation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{lane_id}.json"
    emit_perturbation_report(report, out_path)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"lane_id:             {report.lane_id}")
        print(f"cases_total:         {report.cases_total}")
        print(f"cases_expected_correct: {report.cases_expected_correct}")
        print(
            f"preserving: {report.preserving_correct}/{report.preserving_attempted} "
            f"= {report.preserving_rate:.4f}"
        )
        print(
            f"breaking:   {report.breaking_correct}/{report.breaking_attempted} "
            f"= {report.breaking_rate:.4f}"
        )
        print(f"obligation_5_passed: {report.obligation_5_passed}")
        print(f"report_digest:       {report.report_digest}")
        print(f"artifact:            {out_path}")
        if not report.obligation_5_passed:
            print(f"refusal_reason: {report.refusal_reason}")
    return 0 if report.obligation_5_passed else 1


def cmd_capability_math_expert_gate(args: argparse.Namespace) -> int:
    """ADR-0131.4 — evaluate the composite math-expert promotion gate
    (Benchmark 1 + 2 + 3, ADR-0131's revision of ADR-0120's single-lane
    coverage check). Emits ``expert_claims_math_v1.json`` to ``--out``
    (default: ``evals/math_expert_claims/v1/expert_claims_math_v1.json``).
    Exit 0 iff every benchmark passes."""
    from pathlib import Path
    from core.capability.composite_math_gate import (
        emit_expert_claims_artifact,
        evaluate_composite_math_gate,
    )

    verdict = evaluate_composite_math_gate()
    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent
        / "evals" / "math_expert_claims" / "v1" / "expert_claims_math_v1.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    emit_expert_claims_artifact(verdict, out_path)

    if args.json:
        print(json.dumps(verdict.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"composite_gate_passed: {verdict.composite_gate_passed}")
        print(f"claim_digest:          {verdict.claim_digest}")
        print(f"artifact:              {out_path}")
        for b in verdict.benchmarks:
            print(
                f"  {b.benchmark_id:>20}  passed={b.passed}  "
                f"correct={b.correct}/{b.cases_total}  wrong={b.wrong}  "
                f"rate={b.correct_rate:.4f}"
            )
        hd = verdict.honest_disclosure
        print(
            f"GSM8K honest disclosure: admission={hd.get('admitted_solved', 0)}/"
            f"{hd.get('cases_total', 0)}, wrong={hd.get('admitted_wrong', 0)}, "
            f"substrate={hd.get('substrate', '?')}"
        )
        if not verdict.composite_gate_passed:
            print(f"refusal_reason: {verdict.refusal_reason}")
    return 0 if verdict.composite_gate_passed else 1


def cmd_capability_pack_provenance(args: argparse.Namespace) -> int:
    """ADR-0114a Obligation #10 — external audit that every solver
    step's ``pack_lemma_id`` resolves to a real entry in the domain's
    operator pack lexicon. Defaults to B3 (bounded grammar) under
    ``en_arithmetic_v1``. Emits report to ``--out`` (default:
    ``evals/obligation_10_pack_provenance/<lane_id>.json``).
    Exit 0 iff obligation passes."""
    from pathlib import Path
    from core.capability.pack_provenance import (
        emit_provenance_report,
        validate_lane,
    )

    report = validate_lane()
    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent
        / "evals" / "obligation_10_pack_provenance"
        / f"{report.lane_id}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    emit_provenance_report(report, out_path)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"lane:                       {report.lane_id}")
        print(f"pack_id:                    {report.pack_id}")
        print(f"cases_total:                {report.cases_total}")
        print(f"cases_validated:            {report.cases_validated}")
        print(f"cases_skipped_unsolved:     {report.cases_skipped_unsolved}")
        print(f"cases_violated:             {report.cases_violated}")
        print(f"obligation_10_passed:       {report.obligation_10_passed}")
        print(f"distinct_lemma_ids_observed:")
        for lid in report.distinct_lemma_ids_observed:
            print(f"  - {lid}")
        print(f"artifact:                   {out_path}")
        if report.refusal_reason:
            print(f"refusal_reason:             {report.refusal_reason}")
    return 0 if report.obligation_10_passed else 1


def cmd_capability_adversarial(args: argparse.Namespace) -> int:
    """ADR-0114a Obligation #8 — adversarial generation auditor. Runs
    a committed adversarial case set through the candidate-graph
    pipeline; gate is ``wrong == 0`` across all families AND
    ``cases_total >= 30`` AND ``families_total >= 8``. Default cases
    set ``evals/obligation_8_adversarial/v1/cases.jsonl``; writes
    report to ``--out`` (default
    ``evals/obligation_8_adversarial/<lane_id>.json``). Exit 0 iff
    obligation passes."""
    from pathlib import Path
    from core.capability.adversarial import (
        emit_adversarial_report,
        evaluate_adversarial,
    )

    report = evaluate_adversarial()
    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent
        / "evals" / "obligation_8_adversarial"
        / f"{report.lane_id}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    emit_adversarial_report(report, out_path)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"lane:                {report.lane_id}")
        print(f"cases_total:         {report.cases_total}  (min {report.cases_total >= 30 and 'OK' or 'FAIL'})")
        print(f"families_total:      {report.families_total}  ({'OK' if report.families_total >= 8 else 'FAIL'})")
        print(f"cases_refused:       {report.cases_refused}")
        print(f"cases_solved:        {report.cases_solved}")
        print(f"cases_wrong:         {report.cases_wrong} (gate: must be 0)")
        print(f"obligation_8_passed: {report.obligation_8_passed}")
        print()
        print(f"  {'family':<22} {'total':<7} {'refused':<8} {'solved':<8} {'wrong'}")
        for f in report.families:
            print(f"  {f.family:<22} {f.cases_total:<7} {f.cases_refused:<8} {f.cases_solved:<8} {f.cases_wrong}")
        print(f"\nartifact: {out_path}")
        if report.refusal_reason:
            print(f"refusal_reason: {report.refusal_reason}")
    return 0 if report.obligation_8_passed else 1


def cmd_capability_depth_curve(args: argparse.Namespace) -> int:
    """ADR-0114a Obligation #6 — compositional-depth curve. Re-runs the
    lane's expected-correct cases, buckets by ``len(trace.steps)``,
    asserts ``accuracy(N) >= accuracy(depth_1) * (1 - eps)^(N-1)`` for
    eps = 0.05. Defaults to B3 (bounded grammar). Emits report to
    ``--out`` (default ``evals/obligation_6_depth_curve/<lane_id>.json``).
    Exit 0 iff the assertion holds."""
    from pathlib import Path
    from core.capability.depth_curve import (
        emit_depth_curve_report,
        evaluate_depth_curve,
    )

    report = evaluate_depth_curve()
    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent
        / "evals" / "obligation_6_depth_curve"
        / f"{report.lane_id}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    emit_depth_curve_report(report, out_path)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"lane:                          {report.lane_id}")
        print(f"cases_total:                   {report.cases_total}")
        print(f"cases_solved:                  {report.cases_solved}")
        print(f"epsilon:                       {report.epsilon}")
        print(f"mechanism_wired:               {report.obligation_6_mechanism_wired}")
        print(f"assertion_holds:               {report.obligation_6_assertion_holds}")
        print(f"coverage_sufficient:           {report.coverage_sufficient}")
        print(f"populated_buckets:             {list(report.populated_buckets)}")
        print()
        print(f"  {'bucket':<12} {'total':<7} {'correct':<8} {'accuracy':<10} {'bound':<10} {'satisfied'}")
        for b in report.buckets:
            bound = f"{b.bound_required:.4f}" if b.bound_required is not None else "(anchor)"
            print(f"  {b.bucket:<12} {b.cases_total:<7} {b.cases_correct:<8} {b.accuracy:<10.4f} {bound:<10} {b.bound_satisfied}")
        print(f"\nartifact: {out_path}")
        if report.refusal_reason:
            print(f"refusal_reason: {report.refusal_reason}")
    return 0 if report.obligation_6_assertion_holds else 1


def cmd_pack_list(args: argparse.Namespace) -> int:
    """List compiled language packs."""
    from language_packs import list_packs

    packs = list_packs()
    if not packs:
        print("no compiled packs found")
        return 0
    for pack_id in packs:
        print(pack_id)
    return 0


def cmd_pack_verify(args: argparse.Namespace) -> int:
    """Verify one language pack checksum."""
    return _run(sys.executable, "-m", "language_packs", "verify", args.pack_id)


def _safe_pack_id(pack_id: str) -> str:
    """Reject pack IDs containing path traversal or separator characters."""
    if not pack_id:
        _die("pack_id is required", code=2)

    path = Path(pack_id)

    if path.is_absolute():
        _die("pack_id must not be an absolute path", code=2)

    if pack_id in {".", ".."}:
        _die("pack_id must name a pack, not a relative path", code=2)

    if any(part in {"", ".", ".."} for part in path.parts):
        _die("pack_id must not contain path traversal", code=2)

    if "/" in pack_id or "\\" in pack_id:
        _die("pack_id must be a simple pack id, not a path", code=2)

    return pack_id


def cmd_teaching_audit(args: argparse.Namespace) -> int:
    """ADR-0055 Phase A — surface load decisions on the reviewed teaching corpus.

    Re-parses the cognition-chains JSONL with the same gates as the
    runtime loader, but keeps drop reasons so silent shrinkage (pack
    skew, supersession, schema drift) is inspectable.  Pure read.
    """
    from teaching.audit import audit_corpus

    report = audit_corpus()
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not report.dropped else 1
    print(f"corpus_id      : {report.corpus_id}")
    print(f"corpus_path    : {report.corpus_path}")
    print(f"lines_on_disk  : {report.lines_on_disk}")
    print(f"lines_loaded   : {report.lines_loaded}")
    if report.dropped:
        print(f"\ndropped ({len(report.dropped)}):")
        for d in report.dropped:
            cid = d.chain_id or "<unknown>"
            print(f"  L{d.line_no:>4}  {cid:<40}  {d.reason}")
        return 1
    return 0


def cmd_teaching_gaps(args: argparse.Namespace) -> int:
    """Phase 1.1 — rank (subject, intent) cells the runtime would have
    grounded but couldn't, aggregated from emitted DiscoveryCandidates.

    Reads JSONL files written by
    :class:`teaching.discovery_sink.DiscoveryMonthlyFileSink` under
    *root* (default ``teaching/discovery_log``) and emits a ranked
    table of cells ordered by emission count.

    Pure read — never mutates the sink.
    """
    from teaching.gaps import _DEFAULT_ROOT, aggregate_gaps

    root = Path(args.root) if args.root else _DEFAULT_ROOT
    try:
        rows = aggregate_gaps(
            root=root,
            since=args.since,
            sample_limit=max(1, int(args.sample_limit)),
        )
    except ValueError as exc:
        _die(str(exc), code=2)

    if args.top is not None and args.top > 0:
        rows = rows[: args.top]

    if args.json:
        payload = {
            "root": str(root) if root is not None else None,
            "since": args.since,
            "total_cells": len(rows),
            "gaps": [g.as_dict() for g in rows],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if rows else 1

    if not rows:
        print("No discovery candidates found.")
        if root is not None and not root.exists():
            print(f"  (root path does not exist: {root})")
        return 1

    print(f"{'rank':>4}  {'subject':<24}{'intent':<14}{'count':>6}  {'clean':>6}  months")
    print("-" * 80)
    for i, gap in enumerate(rows, 1):
        months = ",".join(gap.months_seen) if gap.months_seen else "—"
        print(
            f"{i:>4}  {gap.subject[:24]:<24}{gap.intent[:14]:<14}"
            f"{gap.count:>6}  {gap.boundary_clean_count:>6}  {months}"
        )
    return 0


def cmd_teaching_oov_gaps(args: argparse.Namespace) -> int:
    """Phase 2.3 — rank OOV tokens emitted by the runtime's
    OOV "teach me" surface.

    Reads JSONL files written by
    :class:`teaching.oov_sink.OOVMonthlyFileSink` under *root*
    (default ``teaching/oov_log``) and emits a ranked table of
    tokens ordered by emission count.

    Pure read — never mutates the sink.
    """
    from teaching.oov_gaps import _DEFAULT_ROOT, aggregate_oov_gaps

    root = Path(args.root) if args.root else _DEFAULT_ROOT
    try:
        rows = aggregate_oov_gaps(
            root=root,
            since=args.since,
            sample_limit=max(1, int(args.sample_limit)),
        )
    except ValueError as exc:
        _die(str(exc), code=2)

    if args.top is not None and args.top > 0:
        rows = rows[: args.top]

    if args.json:
        payload = {
            "root": str(root),
            "since": args.since,
            "total_tokens": len(rows),
            "oov_gaps": [g.as_dict() for g in rows],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if rows else 1

    if not rows:
        print("No OOV candidates found.")
        if root is not None and not root.exists():
            print(f"  (root path does not exist: {root})")
        return 1

    print(f"{'rank':>4}  {'token':<28}{'count':>6}  {'clean':>6}  intents")
    print("-" * 80)
    for i, gap in enumerate(rows, 1):
        intents = ",".join(gap.intents) if gap.intents else "—"
        print(
            f"{i:>4}  {gap.token[:28]:<28}{gap.count:>6}  "
            f"{gap.boundary_clean_count:>6}  {intents}"
        )
    return 0


def cmd_teaching_oov_queue(args: argparse.Namespace) -> int:
    """Phase 2.3 — show the auto-promoted OOV-token queue.

    Same shape as ``core teaching queue`` but for vocabulary gaps:
    tokens whose boundary-clean emission count meets ``--threshold``
    are surfaced as PackMutationProposal candidates that an operator
    can author via the reviewed ADR-0027 path.

    Never auto-mutates a pack — operator-visible signal only.
    """
    from teaching.oov_gaps import _DEFAULT_ROOT, aggregate_oov_gaps
    from teaching.oov_promotion import promote_oov_gaps

    root = Path(args.root) if args.root else _DEFAULT_ROOT
    try:
        gaps = aggregate_oov_gaps(root=root, since=args.since, sample_limit=5)
    except ValueError as exc:
        _die(str(exc), code=2)

    if args.threshold < 1:
        _die(f"--threshold must be >= 1 (got {args.threshold})", code=2)

    promoted = promote_oov_gaps(
        gaps,
        threshold=args.threshold,
        include_tainted=args.include_tainted,
    )

    if args.json:
        payload = {
            "root": str(root),
            "since": args.since,
            "threshold": args.threshold,
            "include_tainted": args.include_tainted,
            "total_promoted": len(promoted),
            "queue": [p.as_dict() for p in promoted],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if promoted else 1

    if not promoted:
        print(f"No OOV tokens met threshold {args.threshold}.")
        return 1

    print(f"{'rank':>4}  {'queue_id':<40}{'count':>6}  {'clean':>6}  intents")
    print("-" * 96)
    for i, p in enumerate(promoted, 1):
        intents = ",".join(p.intents) if p.intents else "—"
        print(
            f"{i:>4}  {p.queue_id[:40]:<40}{p.count:>6}  "
            f"{p.boundary_clean_count:>6}  {intents}"
        )
    print()
    print(
        f"Add each token to one of: {', '.join(promoted[0].suggested_packs)}.  "
        f"Use a reviewed PackMutationProposal — never auto-applies."
    )
    return 0


def cmd_teaching_queue(args: argparse.Namespace) -> int:
    """Phase 1.2 — show the auto-promoted gap queue.

    Reads the discovery sink (same path as ``core teaching gaps``),
    aggregates by cell, and emits cells whose boundary-clean
    emission count meets ``--threshold``.

    Boundary-tainted emissions (refusal/hedge fired during the
    contributing turn) are excluded by default; ``--include-tainted``
    counts every emission toward the threshold.  Operators reach for
    that flag deliberately, not by accident.
    """
    from teaching.gaps import _DEFAULT_ROOT, aggregate_gaps
    from teaching.promotion import promote_gaps

    root = Path(args.root) if args.root else _DEFAULT_ROOT
    try:
        gaps = aggregate_gaps(
            root=root,
            since=args.since,
            sample_limit=5,
        )
    except ValueError as exc:
        _die(str(exc), code=2)

    if args.threshold < 1:
        _die(f"--threshold must be >= 1 (got {args.threshold})", code=2)

    promoted = promote_gaps(
        gaps,
        threshold=args.threshold,
        include_tainted=args.include_tainted,
    )

    if args.json:
        payload = {
            "root": str(root),
            "since": args.since,
            "threshold": args.threshold,
            "include_tainted": args.include_tainted,
            "total_promoted": len(promoted),
            "queue": [p.as_dict() for p in promoted],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if promoted else 1

    if not promoted:
        print(f"No cells met threshold {args.threshold}.")
        return 1

    print(
        f"{'rank':>4}  {'queue_id':<48}{'count':>6}  {'clean':>6}  months"
    )
    print("-" * 96)
    for i, p in enumerate(promoted, 1):
        months = ",".join(p.months_seen) if p.months_seen else "—"
        print(
            f"{i:>4}  {p.queue_id[:48]:<48}{p.count:>6}  {p.boundary_clean_count:>6}  {months}"
        )
    print()
    print(
        "Author chains with: core teaching propose <candidate-jsonl> "
        "(or hand-author + supersede)."
    )
    return 0


def _load_candidate_jsonl(path: str) -> Any:
    """Read one enriched DiscoveryCandidate JSONL line from *path*."""
    from teaching.discovery import DiscoveryCandidate, EvidencePointer, SubQuestion

    p = Path(path)
    if not p.exists():
        _die(f"candidate file not found: {path}", code=2)
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        _die("candidate file is empty", code=2)
    first = raw.splitlines()[0].strip()
    try:
        payload = json.loads(first)
    except json.JSONDecodeError as exc:
        _die(f"invalid JSON: {exc}", code=2)
    try:
        evidence = tuple(
            EvidencePointer(**e) for e in payload.get("evidence", [])
        )
        sub_questions = tuple(
            SubQuestion(
                sub_id=s["sub_id"],
                proposed_subject=s["proposed_subject"],
                proposed_intent=s["proposed_intent"],
                outcome=s["outcome"],
                evidence=tuple(EvidencePointer(**e) for e in s.get("evidence", [])),
            )
            for s in payload.get("sub_questions", [])
        )
        return DiscoveryCandidate(
            candidate_id=payload["candidate_id"],
            proposed_chain=payload["proposed_chain"],
            trigger=payload["trigger"],
            source_turn_trace=payload.get("source_turn_trace", ""),
            pack_consistent=bool(payload.get("pack_consistent", True)),
            boundary_clean=bool(payload.get("boundary_clean", True)),
            review_state=payload.get("review_state", "unreviewed"),
            polarity=payload.get("polarity", "undetermined"),
            claim_domain=payload.get("claim_domain", "factual"),
            evidence=evidence,
            sub_questions=sub_questions,
            contemplation_depth=int(payload.get("contemplation_depth", 0)),
            recursion_overflow=bool(payload.get("recursion_overflow", False)),
        )
    except (KeyError, TypeError) as exc:
        _die(f"candidate JSON missing required field: {exc}", code=2)


def cmd_teaching_propose(args: argparse.Namespace) -> int:
    """ADR-0057 Phase C2 — build a proposal from an enriched candidate JSONL."""
    from teaching.proposals import (
        ProposalError, ProposalLog, propose_from_candidate,
    )

    candidate = _load_candidate_jsonl(args.candidate_path)
    log_path = Path(args.log) if args.log else None
    log = ProposalLog(log_path)
    try:
        proposal = propose_from_candidate(
            candidate, log=log, allow_evaluative=args.allow_evaluative,
        )
    except ProposalError as exc:
        _die(f"ineligible: {exc}", code=1)
    rec = log.find(proposal.proposal_id)
    print(f"proposal_id    : {proposal.proposal_id}")
    print(f"state          : {rec['state']}")
    if rec.get("replay_evidence"):
        ev = rec["replay_evidence"]
        print(f"replay_equivalent: {ev['replay_equivalent']}")
        if ev.get("regressed_metrics"):
            print(f"regressed       : {', '.join(ev['regressed_metrics'])}")
    if rec.get("operator_note"):
        print(f"note           : {rec['operator_note']}")
    return 0 if rec["state"] in ("pending", "accepted") else 1


def cmd_teaching_proposals(args: argparse.Namespace) -> int:
    from teaching.proposals import ProposalLog

    log_path = Path(args.log) if args.log else None
    log = ProposalLog(log_path)
    state = log.current_state()
    if args.state:
        state = {pid: rec for pid, rec in state.items() if rec["state"] == args.state}
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not state:
        print("(no proposals)")
        return 0
    for pid, rec in state.items():
        chain = rec["proposal"]["proposed_chain"]
        print(
            f"{pid}  {rec['state']:<10}  "
            f"{chain.get('subject')} {chain.get('connective')} {chain.get('object')} "
            f"({chain.get('intent')})"
        )
    return 0


def cmd_teaching_review(args: argparse.Namespace) -> int:
    from teaching.proposals import (
        ProposalError, ProposalLog,
        accept_proposal, reject_proposal, withdraw_proposal,
    )

    log_path = Path(args.log) if args.log else None
    log = ProposalLog(log_path)
    try:
        if args.accept:
            if not args.review_date:
                _die("--accept requires --review-date YYYY-MM-DD", code=2)
            from chat.teaching_grounding import _CORPUS_PATH
            chain_id = accept_proposal(
                args.proposal_id, log=log,
                corpus_path=_CORPUS_PATH,
                review_date=args.review_date,
                operator_note=args.note,
            )
            print(f"accepted; appended chain_id = {chain_id}")
        elif args.reject:
            reject_proposal(args.proposal_id, log=log, operator_note=args.note)
            print(f"{args.proposal_id} rejected")
        elif args.withdraw:
            withdraw_proposal(args.proposal_id, log=log, operator_note=args.note)
            print(f"{args.proposal_id} withdrawn")
    except ProposalError as exc:
        _die(str(exc), code=1)
    return 0


def cmd_teaching_supersessions(args: argparse.Namespace) -> int:
    """Pair each retired chain with its active replacement.

    Derived view over ``teaching.audit.audit_corpus`` — pure, read-only.
    Surfaces orphan supersessions (retired chain with no live replacement
    carrying the matching ``superseded_by``) so silent corpus drift is
    inspectable.
    """
    from teaching.audit import audit_corpus, supersession_history

    report = audit_corpus()
    records = supersession_history(report)

    if args.json:
        print(json.dumps(
            {
                "corpus_id": report.corpus_id,
                "corpus_path": report.corpus_path,
                "supersessions": [r.as_dict() for r in records],
            },
            ensure_ascii=False, indent=2, sort_keys=True,
        ))
        return 0

    if not records:
        print("(no supersessions)")
        return 0

    has_orphan = False
    for r in records:
        if r.replacement is None:
            has_orphan = True
            print(
                f"retired: {r.retired_chain_id}  (line {r.retired_line_no})\n"
                f"  replaced_by: <ORPHAN — no live entry carries this superseded_by>"
            )
            continue
        rep = r.replacement
        prov = rep.provenance.raw or "(unknown)"
        print(
            f"retired: {r.retired_chain_id}  (line {r.retired_line_no})\n"
            f"  replaced_by: {rep.chain_id}  (line {rep.line_no})\n"
            f"    {rep.subject} {rep.connective} {rep.object}  [{rep.intent}]\n"
            f"    provenance: {prov}"
        )
    return 1 if has_orphan else 0


def cmd_teaching_supersede(args: argparse.Namespace) -> int:
    """ADR-0057 follow-up — retire an active corpus chain by appending
    a new chain marked ``superseded_by``.

    Distinct from accept-a-proposal (no replay gate; this is a direct
    operator action).  Validates pack-consistency / intent / completeness
    before the append, and rolls back the corpus byte-identically on any
    post-audit failure.
    """
    from chat.teaching_grounding import _CORPUS_PATH
    from teaching.supersede import SupersessionError, supersede_chain

    cross_pack = bool(getattr(args, "cross_pack", False))
    subj_pack = (getattr(args, "subject_pack_id", "") or "").strip()
    obj_pack = (getattr(args, "object_pack_id", "") or "").strip()

    if cross_pack or subj_pack or obj_pack:
        # ADR-0067 — cross-pack supersede.  Both pack ids are required
        # when any cross-pack flag is set.
        if not subj_pack or not obj_pack:
            _die(
                "cross-pack supersede requires --subject-pack-id and "
                "--object-pack-id",
                code=2,
            )
        from teaching.cross_pack_supersede import supersede_cross_pack_chain
        try:
            new_chain_id = supersede_cross_pack_chain(
                old_chain_id=args.old_chain_id,
                subject=args.subject,
                intent=args.intent,
                connective=args.connective,
                object_=args.object,
                subject_pack_id=subj_pack,
                object_pack_id=obj_pack,
                review_date=args.review_date,
                new_chain_id=args.new_chain_id,
            )
        except SupersessionError as exc:
            _die(str(exc), code=1)
    else:
        try:
            new_chain_id = supersede_chain(
                old_chain_id=args.old_chain_id,
                subject=args.subject,
                intent=args.intent,
                connective=args.connective,
                object_=args.object,
                review_date=args.review_date,
                corpus_path=_CORPUS_PATH,
                operator_note=args.note,
                new_chain_id=args.new_chain_id,
            )
        except SupersessionError as exc:
            _die(str(exc), code=1)

    print(f"superseded     : {args.old_chain_id}")
    print(f"new chain_id   : {new_chain_id}")
    print(f"review_date    : {args.review_date}")
    if args.note:
        print(f"note           : {args.note}")
    return 0


def cmd_pack_validate(args: argparse.Namespace) -> int:
    """Run executable source-pack validation gates."""
    pack_id = _safe_pack_id(args.pack_id)
    pack_dir = _REPO_ROOT / "packs" / pack_id
    validator_path = pack_dir / "validators.py"

    if not validator_path.exists():
        _die(f"source-pack validator not found: {validator_path}", code=1)

    if getattr(args, "dry_run", False):
        if args.json:
            print(json.dumps({
                "pack_id": pack_id,
                "validator_path": str(validator_path),
                "would_execute": False,
                "exists": True,
            }, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"dry-run: pack_id={pack_id}")
            print(f"validator: {validator_path}")
            print("status: validator exists, would not execute")
        return 0

    if not getattr(args, "allow_arbitrary_code", False):
        _die(
            "dynamic validator execution requires --allow-arbitrary-code",
            code=2,
        )

    import importlib.util

    spec = importlib.util.spec_from_file_location(f"{pack_id}_validators", validator_path)
    if spec is None or spec.loader is None:
        _die(f"cannot load source-pack validator: {validator_path}", code=1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.validate_pack()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"pack_id: {report['pack_id']}")
        print(f"active : {report['active']}")
        for name, result in report["gates"].items():
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} {name:<12} {result['reason']}")
    return 0 if report["active"] else 1


def _print_rust_status() -> bool:
    from algebra.backend import using_rust

    active = using_rust()
    print(f"core_rs crate : {_CORE_RS_DIR}")
    print(f"cargo manifest: {_CORE_RS_MANIFEST}")
    print(f"rust backend  : {'active' if active else 'inactive'}")
    if active:
        import core_rs

        print(f"core_rs module: {getattr(core_rs, '__file__', '<built-in>')}")
    else:
        print("activation    : run `core rust build`")
    return active


def cmd_rust_status(args: argparse.Namespace) -> int:
    """Print Rust backend activation status."""
    return 0 if _print_rust_status() or not args.require_active else 1


def cmd_rust_build(args: argparse.Namespace) -> int:
    """Build/install core_rs into the active Python environment."""
    if not _CORE_RS_MANIFEST.exists():
        _die(f"core-rs manifest not found: {_CORE_RS_MANIFEST}", code=1)
    if shutil.which("uv") is not None:
        rc = _run("uv", "pip", "install", "maturin")
        if rc != 0:
            return rc
    cmd = [
        sys.executable,
        "-m",
        "maturin",
        "develop",
        "--release",
        "--manifest-path",
        str(_CORE_RS_MANIFEST),
    ]
    if args.skip_auditwheel:
        cmd.append("--skip-auditwheel")
    return _run(*cmd)


def cmd_rust_test(args: argparse.Namespace) -> int:
    """Run Rust crate tests."""
    if shutil.which("cargo") is None:
        _die("cargo not found. Install a Rust toolchain first.", code=1)
    return _run("cargo", "test", "--release", cwd=_CORE_RS_DIR)


def cmd_contemplation(args: argparse.Namespace) -> int:
    """Delegate to core.contemplation.__main__:main().

    The contemplation module already owns its argparse surface (lane,
    sink-root, report, pack-id, note); duplicating it here would
    drift.  We rebuild the inner argv from the parsed Namespace and
    hand off.
    """
    from core.contemplation.__main__ import main as _contemplation_main

    inner: list[str] = [str(p) for p in (args.reports or ())]
    if getattr(args, "lane", None):
        inner.extend(["--lane", args.lane])
    for pack_id in args.pack_id or ():
        inner.extend(["--pack-id", pack_id])
    for note in args.note or ():
        inner.extend(["--note", note])
    if args.report is not None:
        inner.extend(["--report", str(args.report)])
    if args.sink_root is not None:
        inner.extend(["--sink-root", str(args.sink_root)])
    return _contemplation_main(inner)


def cmd_doctor(args: argparse.Namespace) -> int:
    """Inspect import/package health for the CLI runtime path."""
    checks = [
        ("algebra", "algebra"),
        ("alignment", "alignment.graph"),
        ("chat", "chat.runtime"),
        ("language_packs", "language_packs"),
        ("morphology", "morphology.registry"),
        ("sensorium", "sensorium.protocol"),
    ]
    ok = True
    print(f"repo_root: {_REPO_ROOT}")
    for label, module_name in checks:
        try:
            __import__(module_name)
        except Exception as exc:
            ok = False
            print(f"FAIL {label:<14} {module_name}: {exc.__class__.__name__}: {exc}")
        else:
            print(f"OK   {label:<14} {module_name}")

    if args.packs:
        try:
            from language_packs import list_packs

            packs = list_packs()
        except Exception as exc:
            ok = False
            print(f"FAIL packs          language_packs.list_packs: {exc.__class__.__name__}: {exc}")
        else:
            print("packs:")
            if packs:
                for pack_id in packs:
                    print(f"  {pack_id}")
            else:
                print("  none found")
    if args.rust:
        rust_active = _print_rust_status()
        if args.require_rust and not rust_active:
            ok = False
    return 0 if ok else 1


def cmd_eval(args: argparse.Namespace) -> int:
    """Run an eval lane by name, or list available lanes."""
    from evals._parallel import normalize_workers
    from evals.framework import (
        discover_lanes,
        get_lane,
        load_cases,
        run_lane,
        write_result,
    )

    if args.list_lanes:
        lanes = discover_lanes()
        if not lanes:
            print("no eval lanes found")
        for lane in lanes:
            versions = ", ".join(lane.versions) if lane.versions else "none"
            print(f"  {lane.name:20s}  versions: {versions}")
        return 0

    lane_name = args.lane
    if not lane_name:
        _die("eval requires a lane name. Use `core eval --list` to see available lanes.")

    try:
        lane = get_lane(lane_name)
    except FileNotFoundError as exc:
        _die(str(exc))

    version = args.version or (lane.versions[0] if lane.versions else "v1")
    split = args.split

    if not args.json and lane_name == "cognition":
        if split == "dev":
            cases_path = lane.dev_cases_path()
        elif split == "public":
            cases_path = lane.public_cases_path(version)
        else:
            cases_path = lane.holdout_cases_path(version)
        cases = load_cases(cases_path)
        effective_workers = normalize_workers(
            args.workers if args.workers is not None else 4,
            len(cases),
        )
        print(f"workers        : {effective_workers}")

    try:
        result = run_lane(
            lane,
            version=version,
            split=split,
            workers=args.workers,
        )
    except FileNotFoundError as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"lane           : {result.lane}")
        print(f"version        : {result.version}")
        print(f"split          : {result.split}")
        print(f"cases          : {result.metrics.get('total', 0)}")
        for key, value in result.metrics.items():
            if key == "total":
                continue
            if isinstance(value, float):
                print(f"{key:15s}: {value:.1%}")
            else:
                print(f"{key:15s}: {value}")
        failures = [c for c in result.case_details if not c.get("intent_correct") or not c.get("versor_closure")]
        if failures:
            print(f"\nfailures ({len(failures)}):")
            for c in failures:
                issues = []
                if not c.get("intent_correct"):
                    issues.append("intent")
                if not c.get("versor_closure"):
                    vc = c.get("versor_condition", 0)
                    issues.append(f"versor={vc:.2e}")
                cid = c.get("case_id") or c.get("id") or "<unknown>"
                print(f"  {cid}: {', '.join(issues)}")

    if args.save:
        result_path = write_result(lane, result)
        print(f"\nresult written: {result_path}", file=sys.stderr)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        )
        print(f"\nreport written: {report_path}", file=sys.stderr)

    return 0


def cmd_pulse(args: argparse.Namespace) -> int:
    """Run a cognitive pulse and display recalled words + realized surface."""
    from scripts.run_pulse import run_pulse

    text = " ".join(args.text) if args.text else "What is truth?"
    result = run_pulse(
        text,
        top_k=args.top_k,
        use_glove=not args.no_glove,
        use_correction=not args.no_correction,
        correction_rate=args.correction_rate,
    )

    if args.json:
        import json as _json
        print(_json.dumps({
            "prompt": text,
            "recalled_words": list(result.recalled_words),
            "surface": result.surface,
            "steps": result.steps,
            "converged": result.converged,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\nsurface: {result.surface}")
        print(f"steps  : {result.steps}  converged: {result.converged}")

    return 0


_DEMO_RESULTS_DIR = Path("evals/forward_semantic_control/results")
_DEMO_CORPUS_DIR = Path("evals/forward_semantic_control/public")


_PHASE5_PREAMBLE = """
================================================================================
  Phase 5 Demo — Stratified Mechanism-Isolation
================================================================================

WHAT THIS DEMO TESTS
  CORE's inner-loop admissibility mechanism is supposed to behave correctly
  across five distinct geometric failure modes — not just on average, but
  per-family. This demo runs a hand-curated 20-case corpus that stratifies
  the chain's behaviour across those five families:

    A. near_forbidden_correct_endpoint  Expected and forbidden tokens have
                                        nearly equal blade-scores. Tests
                                        margin sensitivity at the boundary.
    B. near_equal_admissible            Two admissible candidates with
                                        near-identical scores. Tests the
                                        margin gate's determinism under tie.
    C. no_admissible_path               All candidates score ≤ 0 against the
                                        blade. Tests honest refusal.
    D. multi_step_admissibility         Chained Family-A configurations.
                                        Tests step-to-step composition.
    E. heterogeneous_relation           Chained steps with DIFFERENT blades.
                                        Tests blade-switching cleanliness.

  Each case is run under TWO modes:
    threshold mode  (ADR-0024 — per-case static admissibility_threshold)
    margin mode     (ADR-0026 — scale-invariant δ-margin, δ=0.4 default)

WHAT TO EXPECT IF THE MECHANISM IS WORKING
  - Overall pass_rate (threshold) = 100%
  - Overall pass_rate (margin)    = 100%
  - mechanism_isolated (both modes) = True
  - Per-family pass_rate = 100% for ALL five families
  - Family B refusal_rate (margin) = 100% (near-equal candidates must
    refuse under δ-margin by construction)
  - Family C refusal_rate (both modes) = 100% (no admissible path)

WHAT TO LOOK FOR
  - If any family's pass_rate < 100%, the mechanism failed THAT family
    specifically — not a general regression. Dig into the per-case
    detail in the report JSON to see which case and what selection.
  - If Family B does NOT refuse under margin mode, the δ gate has
    silently broken — check generate/admissibility.py::check_margin.
  - If Family C admits anything, honest refusal has regressed — check
    generate/exhaustion.py and the InnerLoopExhaustion raise sites in
    generate/stream.py.

WHEN TO TWEAK
  - δ = 0.4 (the margin default) is FALSIFIABLE: if a case surfaces a
    blade-gap below δ where margin-mode refusal is the WRONG behaviour,
    that is an architectural finding to REPORT in
    docs/evals/phase5_stratified_findings.md, NOT a value to patch.
  - Adding new failure-mode families requires editing
    evals/forward_semantic_control/phase5_runner.py::_passed_single
    and authoring stratified cases in
    evals/forward_semantic_control/public/v2_phase5/cases.jsonl.
================================================================================
"""

_PHASE6_PREAMBLE = """
================================================================================
  Phase 6 Demo — Comparative Demo: CORE vs In-System Baseline
================================================================================

WHAT THIS DEMO TESTS
  Three head-to-head claims about what CORE adds OVER an in-system baseline
  (the same codebase with inner-loop / margin / rotor admissibility DISABLED
  — i.e. an ADR-0023 ablation). Each claim is run on a focused 8-case
  corpus and pinned by 17 CI contract tests:

    C1 Replay determinism   Both baseline AND CORE produce byte-identical
                            trace hashes across 5 reruns. CORE additionally
                            folds refusal_reason into trace_hash, so refusal
                            events themselves are replayable evidence.

    C2 Traced rejection     On adversarial cases where the boundary picks
                            the forbidden token: baseline emits it (with
                            admitted=False, silent emit). CORE overrides
                            and the rejection appears in rejected_attempts.

    C3 Coherent refusal     On no-admissible-path cases: baseline emits an
                            inadmissible candidate. CORE raises
                            InnerLoopExhaustion with a typed RefusalReason.

WHY THE BASELINE IS IN-SYSTEM (NOT AN LLM)
  A transformer-LLM comparison would be non-deterministic, could not be
  CI-enforced, and would be apples-to-oranges (different corpus / training
  / sampling). The honest comparison is the ablation: same code, same
  field state, same vocab, same persona — only the Phase 2-5 mechanisms
  toggled off. Anything CORE produces that the baseline does not produce
  is therefore attributable to the mechanisms themselves.

WHAT TO EXPECT IF EVERYTHING IS WORKING
  - C1: BOTH baseline_stable AND CORE_stable = 8/8 (replay is preserved,
    not added, by Phase 2-5)
  - C2: baseline_emits_forbidden = 3/3, baseline_admits_forbidden = 0/3
        CORE_corrects_or_refuses = 3/3, CORE_rejection_in_trace = 3/3
  - C3: baseline_typed_refusals = 0/3, baseline_emits_inadmissible = 3/3
        CORE_typed_refusals = 3/3
  - ALL THREE CONDITIONS = PASS

WHAT TO LOOK FOR
  - If C1 baseline fails, the algebra layer's replay has regressed —
    unrelated to the chain. Investigate algebra/ first.
  - If C1 CORE fails but baseline holds, the trace fold or refusal
    plumbing has broken determinism. Check trace.py + exhaustion.py.
  - If C2 baseline_admits_forbidden > 0, the boundary-only gate is
    accidentally admitting things — unrelated to the chain, but worth
    investigating.
  - If C3 baseline_typed_refusals > 0, baseline is somehow raising
    InnerLoopExhaustion — investigate whether inner_loop_admissibility
    actually got disabled in the ablation.
  - If C3 CORE_typed_refusals < case_count, CORE is NOT refusing where
    it should — the honest-refusal contract has regressed.

WHEN TO TWEAK
  - If a C2/C3 case stops surfacing the intended baseline failure mode
    (e.g. boundary stops picking the forbidden), it has aged out — the
    cure is to add a NEW case that surfaces the failure, NOT to relax
    the predicate. See docs/evals/phase6_comparative_demo.md.
================================================================================
"""

_AUDIT_TOUR_PREAMBLE = """
================================================================================
  Audit Tour — Pack-Layer Architecture in Four Scenes
================================================================================

Four scenes, each making one falsifiable claim no transformer-LLM wrapper
can reproduce:

  Scene 1 — Identity is geometric, not prompt-veneer.
            Three identity packs load three structurally distinct manifolds
            (ADR-0027).  Different alignment thresholds, different hedge
            phrases.  Differences come from JSON pack files, not prompts.

  Scene 2 — Safety is the universal floor.
            A runtime-checkable safety violation produces a deterministic
            typed refusal string (ADR-0036).  walk_surface preserved for
            audit.  Byte-identical across runs.

  Scene 3 — Ethics commitments choose their remediation.
            Per-commitment opt-in (ADR-0037 / ADR-0038): same engine, same
            input, different policy.  Pack JSON picks the remediation tier
            (audit / hedge / refuse).

  Scene 4 — Deterministic replay across runtime instances.
            Two fresh ChatRuntime instances, same input, same packs.  The
            emitted JSONL audit line (ADR-0040) is byte-identical.  No
            stochastic sampling.  No hidden state.

Every claim is testable (tests/test_audit_tour.py asserts
all_claims_supported is True), every refusal/hedge is auditable, every run
is replayable.

For machine-readable output:
  core demo audit-tour --json
================================================================================
"""


_PACK_MEASUREMENTS_PREAMBLE = """
================================================================================
  Pack Measurements (ADR-0043)
================================================================================

Reference: ADR-0027 through ADR-0042 (the pack-layer architecture).

Two pack-driven runners produce per-pack measurements across the three
ratified identity packs (default_general_v1, precision_first_v1,
generosity_first_v1):

  Runner 1 — Identity divergence
    Invokes the production SentenceAssembler with each pack's SurfaceContext
    over 10 cases × 5 alignment bands.  Reports per-pack rates of bare /
    hedged / qualified surfaces and pairwise distinct_rate.  No mocks; the
    same code path used by the runtime.

  Runner 2 — Pack-aware refusal calibration
    Re-runs the grounding-refusal lane with each identity pack selected via
    RuntimeConfig.  Reports per-pack refusal_rate, fabrication_rate, and
    pack_invariant_gate (byte-identical out-of-grounding surfaces across
    packs).

Combined artifact:
  evals/results/phase2_pack_measurements.json

Test gate:
  tests/test_pack_measurements_phase2.py (schema, load-bearing flags,
  precision.hedge_rate > generosity.hedge_rate).

Machine-readable output:
  core demo pack-measurements --json
================================================================================
"""


_LONG_CONTEXT_COMPARISON_PREAMBLE = """
================================================================================
  Long-Context Recall Comparison (ADR-0045)
================================================================================

Reference: vault/store.py (cga_inner exact scan); CLAUDE.md long-context
doctrine ("Vault recall is exact and deterministic").

This report combines a controlled CORE measurement with frozen citations of
published transformer long-context recall figures.  The two measurements use
different inputs (synthetic float32 versors vs natural-language needles) and
are not directly comparable on benchmark-for-benchmark grounds; the
comparison is at the architectural level — exact-scan recall vs
attention-based probabilistic recall.

  Component 1 — CORE controlled measurement
    Procedure: for each N ∈ {100, 1_000, 10_000, 100_000}, populate a fresh
    VaultStore with N-1 random float32 versors and one distinguished needle
    at a known index; query the vault with the needle vector; verify the
    top-1 result is the planted index.  Determinism: fixed seed schedule.

  Component 2 — Published transformer baselines (frozen citations)
    Anthropic Claude 2.1, OpenAI GPT-4 Turbo 128k, Google Gemini 1.5 Pro,
    NVIDIA RULER.  Each baseline carries source citation and URL; figures
    are not re-measured here.  See
    evals/long_context_cost/baselines/transformer_long_context.json.

Combined artifact:
  evals/long_context_cost/results/comparison_v1.json

Test gate:
  tests/test_long_context_comparison.py (schema; CORE recall = 100%; every
  baseline retains source + url).

Machine-readable output:
  core demo long-context-comparison --json
================================================================================
"""


_ARTICULATION_PREAMBLE = """
================================================================================
  Articulation — Discourse-Planner Spine, End-to-End
================================================================================

Reference: docs/evals/articulation_bench_2026-05-19.md, commits 7af7892
(CompoundIntent), 4e3ddee (WALKTHROUGH v1), e985790 (planner-on bench),
07fefb9 (articulate/disclosure/unarticulate partition).

The discourse-planner spine turns a classified intent + grounding bundle
into a deterministic multi-sentence surface without an LLM, without
sampling, and without approximate retrieval.  Every sentence traces to a
pack lemma, a reviewed teaching chain, or a fixed connective vocabulary.

  S1.  EXPLAIN       — "Explain truth."
                       Flag-on: ANCHOR + SUPPORT multi-sentence paragraph
                                grounded in teaching (>=3 sentences).
                       Flag-off: BRIEF pack anchor only (2 sentences,
                                 incl. pack-grounded tag).

  S2.  COMPOUND      — "What is truth, and why does it matter?"
                       Flag-on: source-ordered sub-plans + TRANSITION
                                bridge (>=4 sentences, teaching-grounded).
                       Flag-off: OOV disclosure (the flat classifier
                                 cannot parse the second clause).

  S3.  WALKTHROUGH   — "Walk me through recall."
                       Flag-on: pack anchor + teaching-chain CLOSURE
                                ("Recall reveals memory.").
                       Flag-off: pack anchor only, no chain hop.

  S4.  Determinism   — Each prompt re-run N=3 with a fresh ChatRuntime;
                       unique(surface) == 1 for every prompt.

Trust boundary:
  This demo does not mutate any corpus, pack, or vault.  Read-only
  against live packs + active teaching corpus.

What to expect:
  Per-scene printout with CLAIM, prompt, flag-off baseline, flag-on
  surface, sentence counts, grounding source.  Final summary lists each
  scene's claim_supported flag.

Test gate:
  tests/test_articulation_demo.py (7 tests — per-scene claim +
  all_claims_supported + determinism invariant).

Machine-readable output:
  core demo articulation --json
================================================================================
"""


_ANTI_REGRESSION_PREAMBLE = """
================================================================================
  Anti-Regression — Three-Gate Defense Against Learning Harm (ADR-0057)
================================================================================

Reference: ADR-0055 (inter-session memory), ADR-0056 (contemplation),
ADR-0057 (TeachingChainProposal + replay-equivalence gate).

When a system extends its own knowledge, the gate that decides what to
admit is the load-bearing part — not the proposer.  CORE's reviewed-
corpus extension path has three independent gates that each must pass
before any byte is written to the active teaching corpus:

  S1.  Eligibility predicate  (mechanical, pre-replay)
       Five mechanical checks on candidate shape — polarity in
       {affirms, falsifies}, ≥1 source='corpus' evidence pointer,
       claim_domain != evaluative (unless --allow-evaluative),
       boundary_clean=True, proposed_chain complete.
       Ineligible candidates raise ProposalError; they never enter
       the proposal log.

  S2.  Replay-equivalence gate  (mechanical, post-eligibility)
       The full cognition lane runs against the active corpus AND
       against a transient copy with the proposed chain appended.
       Any strict-decrease in a watched metric (intent_accuracy,
       surface_groundedness, term_capture_rate, versor_closure_rate)
       auto-rejects with the metrics named in the operator note.
       Active corpus file bytes byte-identical pre/post.

  S3.  Operator review  (manual, post-replay)
       Even a replay-equivalent proposal only reaches the 'pending'
       state.  Explicit `core teaching review <id> --accept` is
       required to write to the active corpus.

What to expect:
  Three scenes, each printed with its CLAIM, candidate, outcome, and
  the byte-identical-corpus assertion.  Scenes 1 and 3 use the real
  replay function; scene 2 injects a controlled replay (via the
  documented run_replay= kwarg) to deterministically demonstrate the
  auto-rejection lifecycle on a synthetic regression.

Test gate:
  tests/test_anti_regression_demo.py (5 tests — per-scene claim +
  active-corpus-byte-identical invariant).

Machine-readable output:
  core demo anti-regression --json
================================================================================
"""


_LEARNING_LOOP_PREAMBLE = """
================================================================================
  Learning Loop — Cold Turn to Grounded Surface, End-to-End (ADR-0055..0057)
================================================================================

Reference: ADR-0055 (Phase B DiscoveryCandidate emission, Phase A audit
+ provenance), ADR-0056 (Phase C1 contemplation), ADR-0057 (Phase C2
TeachingChainProposal + replay gate + operator review).

A single deterministic prompt drives every scene:

    "Why does narrative exist?"

Headline claim: CORE, asked a question it cannot ground, emits
structured evidence that a reviewed chain would have helped.  An
operator authors a proposal from that evidence.  The replay-
equivalence gate confirms no regression.  The operator accepts.  The
**same prompt now produces a deterministic teaching-grounded surface**
— replayable, with full provenance back to the operator's accept.

  S1.  Cold turn          — runtime returns the universal disclosure;
                            grounding_source = none.
  S2.  Discovery emission — DiscoveryCandidate emitted to the attached
                            sink; contemplation enriches with pack/
                            corpus evidence.  Active corpus untouched.
  S3.  Operator proposal  — complete chain authored + real replay gate
                            run + replay_equivalent=True → pending.
  S4.  Operator accept    — accept_proposal writes ONE line to a
                            transient corpus (copy of active + new
                            chain).  Active corpus byte-identical.
  S5.  Replay the prompt  — _CORPUS_PATH swapped to the transient;
                            same prompt now teaching-grounded with the
                            new chain's subject / connective / object.

Trust boundary:
  The demo writes ONLY to a tempdir-scoped transient corpus.  The
  active teaching corpus on disk is byte-identical pre/post — same
  swap pattern the replay-equivalence gate uses.  No clock-time read.

What to expect:
  Per-scene printout with CLAIM, prompt/inputs, outputs, and the
  byte-identical-corpus assertion.  Final BEFORE / AFTER block shows
  the deterministic surface change on the same prompt.

Test gate:
  tests/test_learning_loop_demo.py (7 tests — loop closes, before is
  ungrounded, after contains new chain atoms, discovery emits ≥1,
  replay gate reports no regression, transient adds exactly 1 line
  while active is byte-identical, same prompt drives both surfaces).

Machine-readable output:
  core demo learning-loop --json
================================================================================
"""


_TEACHING_LOOP_BENCH_PREAMBLE = """
================================================================================
  Teaching-Loop Determinism Benchmark (ADR-0055..0057)
================================================================================

Reference: benchmarks/teaching_loop.py, ADR-0057 (the propose →
replay → accept pipeline).  Pairs naturally with ADR-0045's 100%
exact-NIAH recall numbers — same epistemic class of guarantee,
applied to the *learning loop* rather than only to retrieval.

For an identical candidate, the bench runs the full reviewed-corpus
extension pipeline (propose_from_candidate → real run_replay_equivalence
→ accept_proposal) N times against tempdir-scoped paths, and asserts
byte-identical artifacts every iteration:

  - proposal_id           (SHA-256 of canonical-JSON payload)
  - replay_baseline       (cognition lane metrics on active corpus)
  - replay_candidate      (cognition lane metrics on transient corpus)
  - regressed_metrics     (sorted tuple)
  - chain_id_written

Also reports per-iteration wall-time (mean / p50 / p95) and total.

Trust boundary:
  Every write is confined to a tempdir created inside the bench loop.
  Active corpus file bytes are byte-identical pre/post regardless of
  N.  Asserted in the bench report and re-pinned in the test.

100-run reference result on today's main:
  unique(proposal_id) = 1     unique(chain_id) = 1
  unique(baseline)    = 1     unique(candidate) = 1
  active_corpus_byte_eq = True
  mean = 1.85s    p50 = 1.84s    p95 = 1.85s

Test gate:
  tests/test_teaching_loop_bench.py (5 tests — determinism at small N,
  proposal_id SHA-256 shape, canonical chain_id layout, latency stats
  well-formed, JSON serialisation).

Usage:
  core bench --suite teaching-loop --runs 100
  core bench --suite teaching-loop --runs 10 --json
================================================================================
"""


_ARTICULATION_BENCH_PREAMBLE = """
================================================================================
  Articulation Benchmark Suite (Phase 4 capability proof)
================================================================================

Reference: benchmarks/articulation.py + benchmarks/README.md.

Anchors the post-ADR-0067 claim set in numbers:

  [1] Intent breadth        — every supported intent shape fires (9 + OOV
                              + cross-pack), grounding tier matches prompt.
  [2] Determinism           — same prompt → byte-identical surface across
                              N reruns (fresh ChatRuntime each time).
  [3] Memory footprint      — single runtime, T cold-start prompts, RSS
                              sampled via psutil; per-turn ΔRSS reported.
  [4] Cross-topic context   — opt-in thread_anaphora; walks 8 prompts
                              across cognition + relations + cross-pack.
  [5] Ollama side-by-side   — same prompts on CORE + a local Ollama
                              model; CORE unique=1 every prompt, Ollama
                              shows the stochastic delta.

Read it like this:

  GOOD     — determinism_all_identical=True, per-turn ΔRSS in KiB, every
             intent grounds, Ollama unique>1 on most prompts.
  NEUTRAL  — anaphora_fire_count=0 after first turn (architectural
             ceiling per ADR-0066 §Future ADRs; see README §3.4).
  BAD      — determinism failure on pack/teaching path, per-turn ΔRSS
             in MiB, any intent routes to ``none`` it shouldn't.

Comparison caveat:
  CORE and Ollama optimise different objectives.  CORE: traceable,
  deterministic, every token sourced.  Ollama: fluent, broad,
  stochastic, no provenance.  The bench measures the axes CORE was
  designed for; it does NOT score linguistic quality.

Usage:
  core bench --suite articulation                              # quick
  core bench --suite articulation --runs 20 --turns 200
  core bench --suite articulation --ollama-model llama3:8b     # full
  core bench --suite articulation --json --report report.json
================================================================================
"""


_ADR_0024_CHAIN_PREAMBLE = """
================================================================================
  ADR-0024 Chain — Phase 5 + Phase 6 Combined Evidence
================================================================================

This runs BOTH Phase 5 (stratified mechanism-isolation, 20 cases, 5 failure-
mode families, threshold + margin modes) AND Phase 6 (three-condition head-
to-head vs in-system baseline, 8 cases). A combined summary line at the end
reports the chain's overall verdict.

For a thorough explanation of each phase, run them individually:
  core demo phase5
  core demo phase6

For the central evidence index:
  core demo list-results
================================================================================
"""


_ALL_PREAMBLE = """
================================================================================
  core demo all — Combined Demo, End-to-End
================================================================================

Runs the full demo suite in sequence and prints a consolidated PASS/FAIL
table.  This is the "show me everything" entry point.

  1. phase5                  — stratified mechanism isolation (ADR-0024)
  2. phase6                  — 3-condition head-to-head (ADR-0024)
  3. audit-tour              — pack-layer story (ADR-0027..0041)
  4. pack-measurements       — pack-layer claims → numbers (ADR-0043)
  5. long-context-comparison — exact NIAH vs transformer baselines (ADR-0045)
  6. anti-regression         — three-gate defense (ADR-0057)
  7. learning-loop           — cold turn → grounded surface (ADR-0055..0057)
  8. articulation            — discourse-planner spine (multi-sentence)

Each demo retains its own preamble + report.  The final summary surfaces
one boolean per demo and an overall ``all_demos_passed`` flag.

Trust boundary:
  No corpus / pack / vault mutation across any of the eight demos.

JSON mode:
  core demo all --json
  Emits a consolidated dict with one key per demo (full per-demo report)
  plus ``all_demos_passed``.

For just the original ADR-0024 chain (Phase 5 + Phase 6), use:
  core demo adr-0024-chain
================================================================================
"""


def _print_preamble(text: str) -> None:
    """Print a demo preamble to stdout (suppressed under --json)."""
    print(text)


def _format_phase5_table(metrics: dict[str, Any], per_family: dict[str, Any]) -> str:
    lines = [
        "",
        "Phase 5 — Stratified Mechanism-Isolation (ADR-0024 / ADR-0026)",
        "=" * 68,
        f"  cases:                     {metrics.get('case_count', 0)}",
        f"  margin (δ):                {metrics.get('margin', 0)}",
        f"  pass_rate (threshold):     {metrics.get('pass_rate_threshold', 0):.2%}",
        f"  pass_rate (margin):        {metrics.get('pass_rate_margin', 0):.2%}",
        f"  mechanism_isolated (thr):  {metrics.get('mechanism_isolated_threshold', False)}",
        f"  mechanism_isolated (mgn):  {metrics.get('mechanism_isolated_margin', False)}",
        "",
        f"  {'family':38s} {'cases':>6s} {'pass(thr)':>11s} {'pass(mgn)':>11s} {'refuse(mgn)':>13s}",
        "  " + "-" * 84,
    ]
    for fam, b in per_family.items():
        lines.append(
            f"  {fam:38s} {b.get('case_count', 0):>6d} "
            f"{b.get('pass_rate_threshold', 0):>10.2%} "
            f"{b.get('pass_rate_margin', 0):>10.2%} "
            f"{b.get('refusal_rate_margin', 0):>12.2%}"
        )
    return "\n".join(lines) + "\n"


def _format_phase6_table(metrics: dict[str, Any]) -> str:
    def pf(b: bool) -> str:
        return "PASS" if b else "FAIL"
    lines = [
        "",
        "Phase 6 — Comparative Demo: CORE vs In-System Baseline (ADR-0023 ablation)",
        "=" * 76,
        f"  total cases:                  {metrics.get('case_count', 0)}",
        f"  replay reruns:                {metrics.get('replay_reruns', 0)}",
        "",
        "  C1 Replay determinism",
        f"    baseline stable:            {metrics.get('c1_replay_stable_baseline', 0)} / {metrics.get('c1_eligible', 0)}",
        f"    CORE stable:                {metrics.get('c1_replay_stable_core', 0)} / {metrics.get('c1_eligible', 0)}",
        f"    verdict:                    {pf(metrics.get('c1_pass', False))}",
        "",
        "  C2 Traced rejection",
        f"    baseline emits forbidden:   {metrics.get('c2_baseline_emits_forbidden', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    baseline admits forbidden:  {metrics.get('c2_baseline_admits_forbidden', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    CORE corrects-or-refuses:   {metrics.get('c2_core_corrects_or_refuses', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    CORE rejection in trace:    {metrics.get('c2_core_rejection_traced', 0)} / {metrics.get('c2_case_count', 0)}",
        f"    verdict:                    {pf(metrics.get('c2_pass', False))}",
        "",
        "  C3 Coherent refusal",
        f"    baseline typed refusals:    {metrics.get('c3_baseline_refused_typed', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    baseline emits inadmiss.:   {metrics.get('c3_baseline_emitted_inadmissible', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    CORE typed refusals:        {metrics.get('c3_core_refused_typed', 0)} / {metrics.get('c3_case_count', 0)}",
        f"    verdict:                    {pf(metrics.get('c3_pass', False))}",
        "",
        f"  ALL THREE CONDITIONS:         {pf(metrics.get('all_three_conditions_pass', False))}",
    ]
    return "\n".join(lines) + "\n"


def _write_results_index() -> Path:
    """Write/refresh the results index manifest.

    Lists every ``*_report.json`` in the results directory with its
    headline metric (or a short summary).  Reviewers can read this to
    discover all available evidence in one place.
    """
    results_dir = _DEMO_RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for p in sorted(results_dir.glob("*.json")):
        if p.name == "index.json":
            continue
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
        entries.append({
            "file": p.name,
            "size_bytes": p.stat().st_size,
            "headline": {
                k: v for k, v in metrics.items()
                if k in (
                    "case_count", "pass_rate", "pass_rate_threshold",
                    "pass_rate_margin", "mechanism_isolated",
                    "mechanism_isolated_threshold", "mechanism_isolated_margin",
                    "all_three_conditions_pass", "c1_pass", "c2_pass", "c3_pass",
                    "best_threshold", "best_separation_quality",
                )
            },
        })
    index_path = results_dir / "index.json"
    index_path.write_text(json.dumps({
        "results_dir": str(results_dir),
        "reports": entries,
    }, indent=2))
    return index_path


def _run_demo_phase5(emit_json: bool, *, with_preamble: bool = True) -> dict[str, Any]:
    from evals.forward_semantic_control.phase5_runner import run_lane
    if with_preamble and not emit_json:
        _print_preamble(_PHASE5_PREAMBLE)
    cases_path = _DEMO_CORPUS_DIR / "v2_phase5" / "cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text().splitlines() if line.strip()]
    report = run_lane(cases)
    out = _DEMO_RESULTS_DIR / "phase5_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "metrics": report.metrics,
        "per_family": report.per_family,
        "case_details": report.case_details,
    }, indent=2))
    if emit_json:
        print(json.dumps({"metrics": report.metrics, "per_family": report.per_family}, indent=2))
    else:
        print(_format_phase5_table(report.metrics, report.per_family))
        print(f"  full report: {out}")
    return report.metrics


def _run_demo_phase6(emit_json: bool, *, with_preamble: bool = True) -> dict[str, Any]:
    from evals.forward_semantic_control.phase6_demo import run_lane
    if with_preamble and not emit_json:
        _print_preamble(_PHASE6_PREAMBLE)
    cases_path = _DEMO_CORPUS_DIR / "v2_phase6_demo" / "cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text().splitlines() if line.strip()]
    report = run_lane(cases)
    out = _DEMO_RESULTS_DIR / "phase6_demo_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "metrics": report.metrics,
        "case_details": report.case_details,
    }, indent=2))
    if emit_json:
        print(json.dumps({"metrics": report.metrics}, indent=2))
    else:
        print(_format_phase6_table(report.metrics))
        print(f"  full report: {out}")
    return report.metrics


def cmd_demo(args: argparse.Namespace) -> int:
    """Run the ADR-0024 chain comparative demos for investors / reviewers."""
    target = args.target
    if target == "list-results":
        index_path = _write_results_index()
        data = json.loads(index_path.read_text())
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\nresults directory: {data['results_dir']}\n")
            for entry in data["reports"]:
                print(f"  {entry['file']:55s}  {entry['size_bytes']:>9d} bytes")
                for k, v in entry["headline"].items():
                    print(f"    {k}: {v}")
        return 0

    if target == "audit-tour":
        from evals.audit_tour.run_tour import run_tour

        if not args.json:
            _print_preamble(_AUDIT_TOUR_PREAMBLE)
        result = run_tour(emit_json=args.json)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0

    if target == "register-tour":
        from evals.register_tour.run_tour import run_tour as run_register_tour

        result = run_register_tour(emit_json=args.json)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if result.get("all_claims_supported", False) else 1

    if target == "anchor-lens-tour":
        from evals.anchor_lens_tour.run_tour import run_tour as run_lens_tour

        result = run_lens_tour(emit_json=args.json, workers=args.workers)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if result.get("all_claims_supported", False) else 1

    if target == "orthogonality-tour":
        from evals.orthogonality_tour.run_tour import run_tour as run_ortho_tour

        result = run_ortho_tour(emit_json=args.json, workers=args.workers)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if result.get("all_claims_supported", False) else 1

    if target == "audit-passed":
        from core.demos.expert_demo import run_expert_demo

        domain_id = getattr(args, "domain", None)
        if not domain_id:
            print(
                "core demo audit-passed: --domain required",
                file=sys.stderr,
            )
            return 2
        out_dir = args.output_dir
        if out_dir is None:
            out_dir = Path("evals/audit_passed") / domain_id / "latest"
        try:
            result = run_expert_demo(domain_id=domain_id, output_dir=out_dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"core demo audit-passed: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        else:
            print(f"audit-passed: {out_dir / 'audit_passed.json'}")
            print(f"        html: {out_dir / 'audit_passed.html'}")
            dv = result["digest_verification"]
            mark = "✓" if dv["matches"] else "✗"
            print(
                f"  digest_match: {mark}  "
                f"signed={dv['signed'][:16]}…  derived={dv['derived'][:16]}…"
            )
            for lane in result["lanes"]:
                for split_name, split in lane["splits"].items():
                    sc = split["shape_check"]
                    smark = "✓" if sc["passed"] else "✗"
                    print(
                        f"  {smark} {lane['lane_id']:32s} {split_name:8s} "
                        f"({sc['shape']}): {sc['reason']}"
                    )
            print(f"all_claims_supported: {result['all_claims_supported']}")
        return 0 if result["all_claims_supported"] else 1

    if target == "showcase":
        from core.demos.showcase import render_html, run_showcase

        out_dir = args.output_dir
        if out_dir is None:
            out_dir = Path("evals/public_demo/results/latest")
        out_dir.mkdir(parents=True, exist_ok=True)

        result = run_showcase(output_dir=out_dir)
        # HTML render is presentation-only; JSON is the truth-path.
        html_path = out_dir / "showcase.html"
        html_path.write_text(render_html(result), encoding="utf-8")

        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        else:
            print(f"showcase: {out_dir / 'showcase.json'}")
            print(f"   html : {html_path}")
            print(f"all_claims_supported: {result['all_claims_supported']}")
            print(f"total_runtime_ms    : {result.get('total_runtime_ms')}")
        return 0 if result["all_claims_supported"] else 1

    if target == "pack-measurements":
        from scripts.publish_pack_measurements import (
            build_combined_report,
            write_report,
            _print_human,
        )

        if not args.json:
            _print_preamble(_PACK_MEASUREMENTS_PREAMBLE)
        report = build_combined_report()
        write_report(report, Path("evals/results/phase2_pack_measurements.json"))
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_human(report)
        return 0

    if target == "anti-regression":
        from evals.anti_regression.run_demo import run_demo

        if not args.json:
            _print_preamble(_ANTI_REGRESSION_PREAMBLE)
        report = run_demo(emit_json=args.json)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if target == "learning-loop":
        from evals.learning_loop.run_demo import run_demo as run_loop_demo

        if not args.json:
            _print_preamble(_LEARNING_LOOP_PREAMBLE)
        report = run_loop_demo(emit_json=args.json)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if target == "articulation":
        from evals.articulation.run_demo import run_demo as run_articulation_demo

        if not args.json:
            _print_preamble(_ARTICULATION_PREAMBLE)
        report = run_articulation_demo(emit_json=args.json)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if target == "conversation":
        from evals.conversation.run_demo import run_demo as run_conversation_demo

        # Stream by default; --no-stream disables per-character/per-word
        # delays for CI / tests / fast capture.
        stream = not getattr(args, "no_stream", False)
        report = run_conversation_demo(emit_json=args.json, stream=stream)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if target == "long-context-comparison":
        from evals.long_context_cost.comparison_runner import (
            run_comparison,
            _write_report as _write_lc_report,
        )

        if not args.json:
            _print_preamble(_LONG_CONTEXT_COMPARISON_PREAMBLE)
        report = run_comparison()
        _write_lc_report(
            report,
            Path("evals/long_context_cost/results"),
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            core = report["core_measurements"]
            print(
                f"CORE needle-in-a-haystack recall: {core['recall_pct']:.2f}%  "
                f"(N={core['n_values']})"
            )
            for entry in core["per_n"]:
                mark = "✓" if entry["top1_correct"] else "✗"
                print(f"  {mark}  N={entry['n']}")
            print()
            for b in report["transformer_baselines"]["baselines"]:
                rec = b["reported_recall_pct"]
                rec_str = f"{rec:.1f}%" if rec is not None else "n/a"
                print(
                    f"  {b['system']:<32}  ctx={b['context_window_tokens']:<8}  "
                    f"recall={rec_str}"
                )
            print()
            print(f"claim_supported = {report['claim_supported']}")
        return 0

    if target == "phase5":
        _run_demo_phase5(args.json)
    elif target == "phase6":
        _run_demo_phase6(args.json)
    elif target == "adr-0024-chain":
        _run_adr_0024_chain(args.json)
    elif target == "all":
        return _run_demo_all(args.json)
    else:
        _die(f"unknown demo target: {target}")

    _write_results_index()
    return 0


def _run_adr_0024_chain(emit_json: bool) -> None:
    """Phase 5 + Phase 6 — the original ADR-0024 combined evidence."""
    if not emit_json:
        _print_preamble(_ADR_0024_CHAIN_PREAMBLE)
    p5 = _run_demo_phase5(emit_json)
    p6 = _run_demo_phase6(emit_json)
    if emit_json:
        return
    print("\n" + "=" * 76)
    print("ADR-0024 chain — combined summary")
    print("=" * 76)
    print(f"  Phase 5 pass_rate (margin):    {p5.get('pass_rate_margin', 0):.2%}")
    print(f"  Phase 5 mechanism_isolated:    {p5.get('mechanism_isolated_margin', False)}")
    print(f"  Phase 6 all three conditions:  {p6.get('all_three_conditions_pass', False)}")
    print("")
    print("  What this means:")
    print("    Phase 5 verifies CORE handles five distinct geometric")
    print("    failure modes correctly under both threshold and margin gates.")
    print("    Phase 6 verifies CORE adds three capabilities the in-system")
    print("    baseline cannot exhibit: deterministic replay of refusals,")
    print("    traced rejection of inadmissible candidates, and coherent")
    print("    typed refusal when no admissible path exists.")
    print("    Together they are the load-bearing claim of the ADR-0024 chain.")
    print("")


def _run_demo_all(emit_json: bool) -> int:
    """``core demo all`` — run every demo, print a consolidated PASS/FAIL table.

    Each section uses its native runner; the consolidated boolean is the
    load-bearing field already pinned by that demo's test gate.

    Under ``--json``, sub-runner stdout is suppressed and a single
    consolidated JSON object is emitted at the end.
    """
    import contextlib
    import os

    if not emit_json:
        _print_preamble(_ALL_PREAMBLE)

    consolidated: dict[str, Any] = {}
    passed: dict[str, bool] = {}

    @contextlib.contextmanager
    def _maybe_suppress():
        """Suppress sub-runner stdout when emitting JSON."""
        if emit_json:
            with open(os.devnull, "w") as null, contextlib.redirect_stdout(null):
                yield
        else:
            yield

    def _section(title: str) -> None:
        if not emit_json:
            print("\n" + "█" * 76)
            print(f"█  {title}")
            print("█" * 76)

    # 1. phase5
    _section("1/8  phase5 — stratified mechanism isolation")
    with _maybe_suppress():
        p5 = _run_demo_phase5(emit_json, with_preamble=not emit_json)
    consolidated["phase5"] = p5
    passed["phase5"] = bool(p5.get("mechanism_isolated_margin", False))

    # 2. phase6
    _section("2/8  phase6 — three-condition head-to-head")
    with _maybe_suppress():
        p6 = _run_demo_phase6(emit_json, with_preamble=not emit_json)
    consolidated["phase6"] = p6
    passed["phase6"] = bool(p6.get("all_three_conditions_pass", False))

    # 3. audit-tour
    _section("3/8  audit-tour — pack-layer story")
    from evals.audit_tour.run_tour import run_tour
    if not emit_json:
        _print_preamble(_AUDIT_TOUR_PREAMBLE)
    with _maybe_suppress():
        audit_report = run_tour(emit_json=emit_json)
    consolidated["audit_tour"] = audit_report
    passed["audit_tour"] = bool(audit_report.get("all_claims_supported", False))

    # 4. pack-measurements
    _section("4/8  pack-measurements — pack-layer claims → numbers")
    from scripts.publish_pack_measurements import (
        build_combined_report,
        write_report,
        _print_human,
    )
    if not emit_json:
        _print_preamble(_PACK_MEASUREMENTS_PREAMBLE)
    with _maybe_suppress():
        pm_report = build_combined_report()
        write_report(pm_report, Path("evals/results/phase2_pack_measurements.json"))
        if not emit_json:
            _print_human(pm_report)
    consolidated["pack_measurements"] = pm_report
    passed["pack_measurements"] = bool(pm_report.get("claims_supported", False))

    # 5. long-context-comparison
    _section("5/8  long-context-comparison — exact NIAH vs baselines")
    from evals.long_context_cost.comparison_runner import (
        run_comparison,
        _write_report as _write_lc_report,
    )
    if not emit_json:
        _print_preamble(_LONG_CONTEXT_COMPARISON_PREAMBLE)
    with _maybe_suppress():
        lc_report = run_comparison()
        _write_lc_report(lc_report, Path("evals/long_context_cost/results"))
    if not emit_json:
        core_lc = lc_report["core_measurements"]
        print(
            f"CORE needle-in-a-haystack recall: {core_lc['recall_pct']:.2f}%  "
            f"(N={core_lc['n_values']})"
        )
        print(f"claim_supported = {lc_report['claim_supported']}")
    consolidated["long_context_comparison"] = lc_report
    passed["long_context_comparison"] = bool(lc_report.get("claim_supported", False))

    # 6. anti-regression
    _section("6/8  anti-regression — three-gate defense")
    from evals.anti_regression.run_demo import run_demo as run_ar
    if not emit_json:
        _print_preamble(_ANTI_REGRESSION_PREAMBLE)
    with _maybe_suppress():
        ar_report = run_ar(emit_json=emit_json)
    consolidated["anti_regression"] = ar_report
    passed["anti_regression"] = bool(ar_report.get("all_gates_held", False))

    # 7. learning-loop
    _section("7/8  learning-loop — cold turn → grounded surface")
    from evals.learning_loop.run_demo import run_demo as run_loop
    if not emit_json:
        _print_preamble(_LEARNING_LOOP_PREAMBLE)
    with _maybe_suppress():
        ll_report = run_loop(emit_json=emit_json)
    consolidated["learning_loop"] = ll_report
    passed["learning_loop"] = bool(ll_report.get("learning_loop_closed", False))

    # 8. articulation
    _section("8/8  articulation — discourse-planner spine")
    from evals.articulation.run_demo import run_demo as run_art
    if not emit_json:
        _print_preamble(_ARTICULATION_PREAMBLE)
    with _maybe_suppress():
        art_report = run_art(emit_json=emit_json)
    consolidated["articulation"] = art_report
    passed["articulation"] = bool(art_report.get("all_claims_supported", False))

    all_passed = all(passed.values())
    consolidated["passed"] = passed
    consolidated["all_demos_passed"] = all_passed

    if emit_json:
        print(json.dumps(consolidated, indent=2, sort_keys=True, default=str))
    else:
        print("\n" + "═" * 76)
        print("  core demo all — Combined demo summary")
        print("═" * 76)
        for name, ok in passed.items():
            mark = "✓ PASS" if ok else "✗ FAIL"
            print(f"  {mark}  {name}")
        print()
        print(f"  all_demos_passed : {all_passed}")
        print("  load-bearing claim of the ADR-0024 chain")
        print()

    _write_results_index()
    return 0 if all_passed else 1


def _cmd_bench_all(args: argparse.Namespace) -> int:
    """``core bench --suite all`` — run every benchmark in one shot.

    Order:
      1. Core six (determinism / latency / speedup / versor /
         convergence / realizer) via :func:`run_benchmarks`.
      2. Teaching-loop determinism.
      3. Articulation suite (skips footprint when psutil is missing).
      4. Cost (measurement bench, no PASS/FAIL).

    Each section keeps its native report shape; consolidated PASS/FAIL
    tallies the boolean ``passed`` field across the first three groups.
    Cost is reported as a separate measurement section because it
    deliberately does not produce PASS/FAIL.
    """

    from benchmarks.run_benchmarks import run_benchmarks
    from benchmarks.articulation import (
        format_summary as articulation_format_summary,
        run_articulation_suite,
    )
    from benchmarks.cost import run_cost

    json_out = bool(args.json)
    if not json_out:
        print("=" * 78)
        print(" core bench --suite all".ljust(77) + "")
        print("=" * 78)

    overall_results: list[Any] = []

    # 1. Core six.
    if not json_out:
        print("\n[1/4] Core six (determinism / latency / speedup / versor / convergence / realizer)")
        print("-" * 78)
    with _bench_stdout_guard(json_out):
        core_report = run_benchmarks(suite=None, runs=args.runs)
    overall_results.extend(core_report.results)
    if not json_out:
        for r in core_report.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name:25s}  {r.metric:>12.4f} {r.unit}")
            print(f"         {r.detail}")

    # 2. Teaching-loop determinism.
    if not json_out:
        print("\n[2/4] Teaching-loop determinism")
        print("-" * 78)
    with _bench_stdout_guard(json_out):
        tl_report = run_benchmarks(suite="teaching-loop", runs=args.runs)
    overall_results.extend(tl_report.results)
    if not json_out:
        for r in tl_report.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name:25s}  {r.metric:>12.4f} {r.unit}")
            print(f"         {r.detail}")

    # 3. Articulation suite.  psutil is optional — skip the footprint
    # sub-bench when unavailable rather than aborting the whole run.
    try:
        import psutil  # noqa: F401
        skip_fp = False
    except ImportError:
        skip_fp = True
    if not json_out:
        print("\n[3/4] Articulation suite" + (" (footprint skipped — psutil not installed)" if skip_fp else ""))
        print("-" * 78)
    with _bench_stdout_guard(json_out):
        a_report = run_articulation_suite(
            determinism_runs=args.runs,
            footprint_turns=getattr(args, "turns", 200),
            ollama_model=getattr(args, "ollama_model", None),
            ollama_reruns=getattr(args, "ollama_reruns", 3),
            skip_footprint=skip_fp,
        )
    a_pass = bool(a_report.determinism_all_identical) and (
        a_report.discourse_planner_metrics.get("articulate_sentence_rate", 0.0) == 1.0
        and a_report.discourse_planner_metrics.get("disclosure_sentence_rate", 0.0) == 0.0
    )
    if not json_out:
        if skip_fp:
            print(articulation_format_summary(a_report))
        else:
            print(articulation_format_summary(a_report))
        marker = "PASS" if a_pass else "FAIL"
        print(f"  [{marker}] articulation_suite_overall")

    # 4. Cost — measurement bench, no PASS/FAIL.
    if not json_out:
        print("\n[4/4] Cost (measurement)")
        print("-" * 78)
    with _bench_stdout_guard(json_out):
        cost_report = run_cost(turns=args.runs)
    if not json_out:
        print(cost_report.summary())

    if json_out:
        consolidated = {
            "core": core_report.as_dict(),
            "teaching_loop": tl_report.as_dict(),
            "articulation": a_report.as_dict(),
            "articulation_passed": a_pass,
            "cost": cost_report.as_dict(),
        }
        print(json.dumps(consolidated, ensure_ascii=False, indent=2, sort_keys=True, default=str))

    all_pass = all(r.passed for r in overall_results) and a_pass
    if not json_out:
        print("\n" + "=" * 78)
        print(f"{'ALL PASSED' if all_pass else 'FAILURES DETECTED'} across "
              f"{len(overall_results) + 1} pass/fail benches "
              f"(plus cost measurement section)")
        print("=" * 78)
    return 0 if all_pass else 1


def _bench_stdout_guard(json_mode: bool):
    """Route benchmark pulse/runtime stdout to stderr in --json mode.

    Several benchmarks call ``scripts.run_pulse.run_pulse`` (and other
    helpers) that unconditionally print verbose status to stdout
    (``[pulse] input ...``, ``[pulse] step ...``).  In ``--json`` mode
    that pollutes the machine-readable JSON stream, breaking
    programmatic consumers like ``jq`` or downstream tooling.

    This guard redirects stdout to stderr for the duration of the bench
    run when ``json_mode`` is True, so the operator still sees the
    pulse trace (it just lands on stderr alongside any logging output),
    but ``--json`` consumers get a clean JSON document on stdout.
    """
    import contextlib

    if json_mode:
        return contextlib.redirect_stdout(sys.stderr)
    return contextlib.nullcontext()


def cmd_bench(args: argparse.Namespace) -> int:
    """Run benchmark harness."""
    if args.suite == "all":
        return _cmd_bench_all(args)
    # "cost" suite has its own runtime contract — wall/CPU-seconds and
    # $/1000-turns derivation.  Dispatch separately so the report
    # structure stays honest (no fake PASS/FAIL on a measurement bench).
    if args.suite == "cost":
        from benchmarks.cost import run_cost, write_report
        with _bench_stdout_guard(args.json):
            report = run_cost(turns=args.runs)
        if args.json:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(report.summary())
        if args.report:
            write_report(report, root=Path(args.report).parent)
        else:
            write_report(report)
        return 0

    if args.suite == "articulation":
        from benchmarks.articulation import (
            format_summary,
            run_articulation_suite,
        )
        if not args.json:
            _print_preamble(_ARTICULATION_BENCH_PREAMBLE)
        with _bench_stdout_guard(args.json):
            a_report = run_articulation_suite(
                determinism_runs=args.runs,
                footprint_turns=getattr(args, "turns", 200),
                ollama_model=getattr(args, "ollama_model", None),
                ollama_reruns=getattr(args, "ollama_reruns", 3),
            )
        if args.json:
            print(json.dumps(a_report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_summary(a_report))
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(a_report.as_dict(), ensure_ascii=False, indent=2)
            )
            print(f"report written: {report_path}")
        return 0

    from benchmarks.run_benchmarks import run_benchmarks

    if args.suite == "teaching-loop" and not args.json:
        _print_preamble(_TEACHING_LOOP_BENCH_PREAMBLE)

    with _bench_stdout_guard(args.json):
        report = run_benchmarks(
            suite=args.suite,
            runs=args.runs,
        )

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        for r in report.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name:25s}  {r.metric:>12.4f} {r.unit}")
            print(f"         {r.detail}")
        all_pass = all(r.passed for r in report.results)
        print(f"\n{'ALL PASSED' if all_pass else 'FAILURES DETECTED'}")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
        )
        print(f"report written: {report_path}")

    return 0 if all(r.passed for r in report.results) else 1


def _add_runtime_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack", action="append", help="language pack to mount; repeat for multiple packs")
    parser.add_argument("--output-language", default="en", help="target output language code; default: en")
    parser.add_argument("--frame-pack", help="frame pack to use; defaults to output language")
    parser.add_argument("--max-tokens", type=int, default=32, help="maximum generated tokens; default: 32")
    parser.add_argument("--vault-reproject-interval", type=int, default=20, help="vault null-cone reprojection cadence; default: 20 stores")
    parser.add_argument("--salience-top-k", type=int, default=16, help="salience candidate budget; default: 16")
    parser.add_argument("--inhibition-threshold", type=float, default=0.3, help="attention inhibition threshold; default: 0.3")
    parser.add_argument(
        "--inner-loop-admissibility",
        action="store_true",
        help="enable ADR-0024 per-rotor inner-loop admissibility (re-select on rejection)",
    )
    parser.add_argument(
        "--admissibility-threshold",
        type=float,
        default=0.0,
        help="inner-loop admissibility score threshold; default: 0.0",
    )
    parser.add_argument("--no-salience", action="store_true", help="disable salience attention and use full-manifold generation")
    parser.add_argument(
        "--allow-cross-language-generation",
        action="store_true",
        help="allow generated walk tokens from any mounted language",
    )
    parser.add_argument(
        "--no-cross-language-recall",
        action="store_true",
        help="disable vault recall during generation",
    )
    parser.add_argument(
        "--identity",
        default="",
        metavar="PACK_ID",
        help="identity pack id to load (default: default_general_v1); see "
        "docs/identity_packs.md",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="core",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", dest="print_version", help="print package version and exit")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    chat = subparsers.add_parser("chat", help="start the interactive chat REPL")
    _add_runtime_policy_args(chat)
    chat.add_argument(
        "--list-identity-packs",
        action="store_true",
        help="list discoverable identity packs and exit (no REPL launched)",
    )
    chat.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON (with --list-identity-packs)",
    )
    chat.add_argument(
        "--show-verdicts",
        action="store_true",
        help=(
            "after each turn, print the TurnVerdicts bundle summary to "
            "stderr (ADR-0041 operator-facing audit readout)"
        ),
    )
    chat.add_argument(
        "--register",
        metavar="REGISTER_ID",
        default=None,
        help=(
            "optional register pack id (ADR-0068+); default: no "
            "register (unregistered sentinel, byte-identical to "
            "default_neutral_v1).  Examples: default_neutral_v1, "
            "terse_v1, convivial_v1.  Invalid ids fail-fast at "
            "runtime init before the REPL starts."
        ),
    )
    chat.add_argument(
        "--anchor-lens",
        metavar="LENS_ID",
        default=None,
        dest="anchor_lens",
        help=(
            "optional anchor-lens pack id (ADR-0073+); default: no "
            "lens (unanchored sentinel, byte-identical to "
            "default_unanchored_v1).  Examples: default_unanchored_v1, "
            "grc_logos_v1, he_logos_v1.  Invalid ids fail-fast at "
            "runtime init before the REPL starts."
        ),
    )
    chat.set_defaults(func=cmd_chat)

    test = subparsers.add_parser("test", help="run pytest with curated suite aliases or direct passthrough")
    test.add_argument("--suite", choices=sorted(_TEST_SUITES), help="curated suite alias to run")
    test.add_argument("--list-suites", action="store_true", help="list curated test suite aliases and exit")
    test.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to pytest")
    test.set_defaults(func=cmd_test)

    check = subparsers.add_parser("check", help="run ruff check")
    check.add_argument("paths", nargs="*", help="optional paths to check")
    check.set_defaults(func=cmd_check)

    trace = subparsers.add_parser(
        "trace",
        help="trace one chat turn with field telemetry",
        description="trace one chat turn with field telemetry",
    )
    _add_runtime_policy_args(trace)
    trace.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    trace.add_argument("text", nargs=argparse.REMAINDER, help="input text to trace")
    trace.set_defaults(func=cmd_trace)

    oov = subparsers.add_parser("oov", help="ground or inspect one token")
    _add_runtime_policy_args(oov)
    oov.add_argument("token", help="token to inspect or ground")
    oov.set_defaults(func=cmd_oov)

    capability = subparsers.add_parser("capability", help="capability readiness reports")
    capability_sub = capability.add_subparsers(dest="capability_command", metavar="capability-command", required=True)
    capability_chains = capability_sub.add_parser("chains", help="report teaching chain readiness")
    capability_chains.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_chains.set_defaults(func=cmd_capability_chains)
    capability_flags = capability_sub.add_parser("flags", help="report runtime flag readiness")
    capability_flags.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_flags.set_defaults(func=cmd_capability_flags)
    capability_ledger = capability_sub.add_parser("ledger", help="generated capability ledger")
    capability_ledger.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_ledger.set_defaults(func=cmd_capability_ledger)
    capability_artifact = capability_sub.add_parser("artifact", help="content-addressed artifact metadata")
    capability_artifact.add_argument("--lane", required=True, help="eval lane id (e.g. cognition)")
    capability_artifact.add_argument("--split", required=True, choices=("dev", "public", "holdout"))
    capability_artifact.add_argument("--version", required=True, help="eval version id (e.g. v1)")
    capability_artifact.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_artifact.set_defaults(func=cmd_capability_artifact)
    capability_domain_contract = capability_sub.add_parser(
        "domain-contract",
        help="ADR-0093 dry-run validate Domain Pack Contract v1 (9 predicates)",
    )
    capability_domain_contract.add_argument("--pack-id", required=True, help="language pack id")
    capability_domain_contract.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_domain_contract.add_argument(
        "--structural-only",
        action="store_true",
        help="emit legacy parse-only report (skips ADR-0091 9-predicate evaluation)",
    )
    capability_domain_contract.set_defaults(func=cmd_capability_domain_contract)
    capability_evidence_plan = capability_sub.add_parser(
        "evidence-plan",
        help="content-addressed local/worker evidence job plan",
    )
    capability_evidence_plan.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_evidence_plan.set_defaults(func=cmd_capability_evidence_plan)
    capability_perturbation = capability_sub.add_parser(
        "perturbation",
        help="ADR-0114a Obligation #5 — reasoning-isolation perturbation suite for B3",
    )
    capability_perturbation.add_argument(
        "--lane-id",
        default="B3_bounded_grammar",
        help="lane identifier (default: B3_bounded_grammar)",
    )
    capability_perturbation.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    capability_perturbation.set_defaults(func=cmd_capability_perturbation)

    capability_math_expert_gate = capability_sub.add_parser(
        "math-expert-gate",
        help="ADR-0131.4 evaluate the composite math-expert promotion gate (B1+B2+B3)",
    )
    capability_math_expert_gate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_math_expert_gate.add_argument(
        "--out",
        default=None,
        help="output path for expert_claims artifact (default: evals/math_expert_claims/v1/expert_claims_math_v1.json)",
    )
    capability_math_expert_gate.set_defaults(func=cmd_capability_math_expert_gate)
    capability_pack_provenance = capability_sub.add_parser(
        "pack-provenance",
        help="ADR-0114a Obligation #10 — audit solver-step pack_lemma_ids against on-disk lexicon",
    )
    capability_pack_provenance.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_pack_provenance.add_argument(
        "--out",
        default=None,
        help="output path for the audit report (default: evals/obligation_10_pack_provenance/<lane_id>.json)",
    )
    capability_pack_provenance.set_defaults(func=cmd_capability_pack_provenance)
    capability_adversarial = capability_sub.add_parser(
        "adversarial",
        help="ADR-0114a Obligation #8 — adversarial generation auditor (wrong==0 across families)",
    )
    capability_adversarial.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_adversarial.add_argument(
        "--out",
        default=None,
        help="output path for the adversarial audit report (default: evals/obligation_8_adversarial/<lane_id>.json)",
    )
    capability_adversarial.set_defaults(func=cmd_capability_adversarial)
    capability_depth_curve = capability_sub.add_parser(
        "depth-curve",
        help="ADR-0114a Obligation #6 — compositional-depth vs accuracy curve",
    )
    capability_depth_curve.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    capability_depth_curve.add_argument(
        "--out",
        default=None,
        help="output path for the depth-curve report (default: evals/obligation_6_depth_curve/<lane_id>.json)",
    )
    capability_depth_curve.set_defaults(func=cmd_capability_depth_curve)

    pack = subparsers.add_parser("pack", help="inspect and verify language packs")
    pack_sub = pack.add_subparsers(dest="pack_command", metavar="pack-command", required=True)
    pack_list = pack_sub.add_parser("list", help="list compiled packs")
    pack_list.set_defaults(func=cmd_pack_list)
    pack_verify = pack_sub.add_parser("verify", help="verify a pack checksum")
    pack_verify.add_argument("pack_id", help="pack id, e.g. en_minimal_v1")
    pack_verify.set_defaults(func=cmd_pack_verify)
    pack_validate = pack_sub.add_parser("validate", help="validate a source pack under packs/")
    pack_validate.add_argument("pack_id", help="source pack id, e.g. en, he, grc, el")
    pack_validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    pack_validate.add_argument("--dry-run", action="store_true", help="check validator exists without executing")
    pack_validate.add_argument(
        "--allow-arbitrary-code",
        action="store_true",
        help="permit dynamic validator execution (required to run validators)",
    )
    pack_validate.set_defaults(func=cmd_pack_validate)

    teaching = subparsers.add_parser(
        "teaching",
        help="inspect the reviewed teaching corpus",
    )
    teaching_sub = teaching.add_subparsers(
        dest="teaching_command", metavar="teaching-command", required=True,
    )
    teaching_audit = teaching_sub.add_parser(
        "audit",
        help="surface load decisions and drop reasons for the cognition-chains corpus",
    )
    teaching_audit.add_argument(
        "--json", action="store_true",
        help="emit machine-readable JSON",
    )
    teaching_audit.set_defaults(func=cmd_teaching_audit)

    teaching_oov_gaps = teaching_sub.add_parser(
        "oov-gaps",
        help="rank OOV tokens emitted by the runtime's teach-me surface",
    )
    teaching_oov_gaps.add_argument(
        "--root", default=None,
        help="OOV-sink root (default: teaching/oov_log)",
    )
    teaching_oov_gaps.add_argument(
        "--since", default=None,
        help="lower-bound month token YYYY-MM",
    )
    teaching_oov_gaps.add_argument(
        "--top", type=int, default=None,
        help="show only the top N tokens by emission count",
    )
    teaching_oov_gaps.add_argument(
        "--sample-limit", type=int, default=5,
        help="max candidate_ids retained per token as samples (default: 5)",
    )
    teaching_oov_gaps.add_argument(
        "--json", action="store_true", help="machine-readable output",
    )
    teaching_oov_gaps.set_defaults(func=cmd_teaching_oov_gaps)

    teaching_oov_queue = teaching_sub.add_parser(
        "oov-queue",
        help="show auto-promoted OOV-token queue (tokens crossing --threshold)",
    )
    teaching_oov_queue.add_argument(
        "--root", default=None,
        help="OOV-sink root (default: teaching/oov_log)",
    )
    teaching_oov_queue.add_argument(
        "--since", default=None,
        help="lower-bound month token YYYY-MM",
    )
    teaching_oov_queue.add_argument(
        "--threshold", type=int, default=3,
        help="minimum (boundary-clean) emissions to promote (default: 3)",
    )
    teaching_oov_queue.add_argument(
        "--include-tainted", action="store_true",
        help="count refusal/hedge-tainted emissions toward the threshold",
    )
    teaching_oov_queue.add_argument(
        "--json", action="store_true", help="machine-readable output",
    )
    teaching_oov_queue.set_defaults(func=cmd_teaching_oov_queue)

    teaching_queue = teaching_sub.add_parser(
        "queue",
        help="show auto-promoted high-priority gaps (cells crossing --threshold)",
    )
    teaching_queue.add_argument(
        "--root", default=None,
        help="discovery-sink root (default: teaching/discovery_log)",
    )
    teaching_queue.add_argument(
        "--since", default=None,
        help="lower-bound month token YYYY-MM",
    )
    teaching_queue.add_argument(
        "--threshold", type=int, default=3,
        help="minimum (boundary-clean) emissions to promote a cell (default: 3)",
    )
    teaching_queue.add_argument(
        "--include-tainted", action="store_true",
        help="count refusal/hedge-tainted emissions toward the threshold",
    )
    teaching_queue.add_argument(
        "--json", action="store_true", help="machine-readable output",
    )
    teaching_queue.set_defaults(func=cmd_teaching_queue)

    teaching_gaps = teaching_sub.add_parser(
        "gaps",
        help="rank (subject, intent) cells discovery candidates would have grounded",
    )
    teaching_gaps.add_argument(
        "--root", default=None,
        help="discovery-sink root (default: teaching/discovery_log)",
    )
    teaching_gaps.add_argument(
        "--since", default=None,
        help="lower-bound month token YYYY-MM (default: include every available month)",
    )
    teaching_gaps.add_argument(
        "--top", type=int, default=None,
        help="show only the top N cells by emission count",
    )
    teaching_gaps.add_argument(
        "--sample-limit", type=int, default=5,
        help="max candidate_ids retained per cell as samples (default: 5)",
    )
    teaching_gaps.add_argument(
        "--json", action="store_true", help="machine-readable output",
    )
    teaching_gaps.set_defaults(func=cmd_teaching_gaps)

    teaching_propose = teaching_sub.add_parser(
        "propose",
        help="convert an enriched DiscoveryCandidate (JSONL) into a TeachingChainProposal",
    )
    teaching_propose.add_argument(
        "candidate_path",
        help="path to a JSONL file containing one enriched candidate line",
    )
    teaching_propose.add_argument(
        "--allow-evaluative", action="store_true",
        help="permit claim_domain=evaluative proposals (operator override)",
    )
    teaching_propose.add_argument(
        "--log", default=None,
        help="proposal log path (default: teaching/proposals/proposals.jsonl)",
    )
    teaching_propose.set_defaults(func=cmd_teaching_propose)

    teaching_proposals = teaching_sub.add_parser(
        "proposals",
        help="list proposals in the append-only log",
    )
    teaching_proposals.add_argument(
        "--state", default=None,
        choices=("pending", "accepted", "rejected", "withdrawn"),
        help="filter by review state",
    )
    teaching_proposals.add_argument(
        "--log", default=None, help="proposal log path",
    )
    teaching_proposals.add_argument(
        "--json", action="store_true", help="machine-readable output",
    )
    teaching_proposals.set_defaults(func=cmd_teaching_proposals)

    teaching_review = teaching_sub.add_parser(
        "review",
        help="operator review action: accept / reject / withdraw a pending proposal",
    )
    teaching_review.add_argument("proposal_id")
    grp = teaching_review.add_mutually_exclusive_group(required=True)
    grp.add_argument("--accept", action="store_true")
    grp.add_argument("--reject", action="store_true")
    grp.add_argument("--withdraw", action="store_true")
    teaching_review.add_argument("--note", default="", help="operator note")
    teaching_review.add_argument(
        "--review-date", default=None,
        help="review date (YYYY-MM-DD) — required on --accept",
    )
    teaching_review.add_argument(
        "--log", default=None, help="proposal log path",
    )
    teaching_review.set_defaults(func=cmd_teaching_review)

    teaching_supersede = teaching_sub.add_parser(
        "supersede",
        help="retire an active corpus chain by appending a replacement (operator action)",
    )
    teaching_supersede.add_argument(
        "old_chain_id",
        help="chain_id currently active in the corpus that this action retires",
    )
    teaching_supersede.add_argument("--subject", required=True)
    teaching_supersede.add_argument("--intent", required=True)
    teaching_supersede.add_argument("--connective", required=True)
    teaching_supersede.add_argument("--object", required=True)
    teaching_supersede.add_argument(
        "--review-date", required=True, help="YYYY-MM-DD",
    )
    teaching_supersede.add_argument(
        "--cross-pack", action="store_true",
        help="ADR-0067 — target the cross-pack corpus instead of in-pack",
    )
    teaching_supersede.add_argument(
        "--subject-pack-id", default="",
        help="cross-pack only: subject lemma's resident pack id",
    )
    teaching_supersede.add_argument(
        "--object-pack-id", default="",
        help="cross-pack only: object lemma's resident pack id",
    )
    teaching_supersede.add_argument("--note", default="", help="operator note")
    teaching_supersede.add_argument(
        "--new-chain-id", default=None,
        help="explicit new chain_id (default: <intent>_<subject>_<connective>_<object>)",
    )
    teaching_supersede.set_defaults(func=cmd_teaching_supersede)

    teaching_supersessions = teaching_sub.add_parser(
        "supersessions",
        help="pair each retired chain with its active replacement (derived view)",
    )
    teaching_supersessions.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON",
    )
    teaching_supersessions.set_defaults(func=cmd_teaching_supersessions)

    rust = subparsers.add_parser(
        "rust",
        help="build, test, and inspect the Rust backend",
        description="build, test, and inspect the Rust backend",
    )
    rust_sub = rust.add_subparsers(dest="rust_command", metavar="rust-command", required=True)
    rust_status = rust_sub.add_parser("status", help="show whether core_rs is active")
    rust_status.add_argument("--require-active", action="store_true", help="exit nonzero if core_rs is inactive")
    rust_status.set_defaults(func=cmd_rust_status)
    rust_build = rust_sub.add_parser("build", help="build/install core_rs with maturin")
    rust_build.add_argument("--skip-auditwheel", action="store_true", help="pass --skip-auditwheel to maturin")
    rust_build.set_defaults(func=cmd_rust_build)
    rust_test = rust_sub.add_parser("test", help="run cargo test --release for core-rs")
    rust_test.set_defaults(func=cmd_rust_test)

    pulse = subparsers.add_parser(
        "pulse",
        help="run a cognitive pulse from injection to realized surface",
        description="run a cognitive pulse from injection to realized surface",
    )
    pulse.add_argument("text", nargs="*", default=["What is truth?"])
    pulse.add_argument("--top-k", type=int, default=5, metavar="N")
    pulse.add_argument("--no-glove", action="store_true", help="use compiled pack only (no GloVe download)")
    pulse.add_argument("--no-correction", action="store_true", help="disable correction (V3 mode)")
    pulse.add_argument("--correction-rate", type=float, default=0.3, metavar="R")
    pulse.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    pulse.set_defaults(func=cmd_pulse)

    bench = subparsers.add_parser(
        "bench",
        help="run benchmark harness (determinism, latency, speedup, versor audit)",
        description="run benchmark harness",
    )
    bench.add_argument("--suite", choices=["determinism", "latency", "speedup", "versor", "convergence", "realizer", "cost", "teaching-loop", "articulation", "all"],
                       help="run a specific benchmark suite")
    bench.add_argument("--runs", type=int, default=20, metavar="N", help="run count for determinism benchmark (also turns count for cost suite)")
    bench.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    bench.add_argument("--report", metavar="PATH", help="write JSON report to file")
    bench.add_argument(
        "--turns", type=int, default=200, metavar="N",
        help="articulation suite: footprint sample count (default 200)",
    )
    bench.add_argument(
        "--ollama-model", default=None, metavar="MODEL",
        help="articulation suite: ollama model id to compare against "
             "(e.g. llama3:8b); omit to skip the Ollama sub-bench",
    )
    bench.add_argument(
        "--ollama-reruns", type=int, default=3, metavar="N",
        help="articulation suite: per-prompt rerun count for ollama "
             "(higher = better unique-surface measurement; default 3)",
    )
    bench.set_defaults(func=cmd_bench)

    demo = subparsers.add_parser(
        "demo",
        help="run ADR-0024 chain comparative demos (phase5 / phase6 / all)",
        description=(
            "Run the comparative demo evidence for the ADR-0024 chain.  "
            "Designed for showcasing CORE's deterministic-cognition mechanisms "
            "to reviewers / investors / industry observers."
        ),
    )
    demo.add_argument(
        "target",
        choices=[
            "phase5",
            "phase6",
            "adr-0024-chain",
            "audit-tour",
            "register-tour",
            "anchor-lens-tour",
            "orthogonality-tour",
            "pack-measurements",
            "long-context-comparison",
            "anti-regression",
            "learning-loop",
            "articulation",
            "conversation",
            "showcase",
            "audit-passed",
            "all",
            "list-results",
        ],
        help=(
            "phase5: stratified 5-family mechanism-isolation.  "
            "phase6: 3-condition head-to-head vs in-system baseline.  "
            "adr-0024-chain: phase5 + phase6 combined evidence.  "
            "all: run every demo (eight in total) and print a "
            "consolidated PASS/FAIL table; exits non-zero if any demo fails.  "
            "audit-tour: ADR-0027..0041 pack-layer architecture in four "
            "scenes (identity / safety / ethics / replay).  "
            "register-tour: ADR-0068..0072 presentation-axis seam — same "
            "prompts × three registers; surface varies, grounding_source "
            "and trace_hash byte-identical.  "
            "anchor-lens-tour: ADR-0073 substantive-axis seam — same "
            "prompts × three lenses; trace_hash DISTINCT across lenses, "
            "no substrate glyph leak.  Opposite invariant from register-tour; "
            "both must hold continuously.  "
            "orthogonality-tour: ADR-0074 composition demo — full 3 × 3 × 2 "
            "matrix (register × lens × prompts, 18 cells); pins five "
            "claims simultaneously including both single-axis invariants.  "
            "pack-measurements: ADR-0043 — pack-layer claims → CI-enforced "
            "numbers across the three ratified identity packs.  "
            "long-context-comparison: ADR-0045 — CORE exact recall NIAH at "
            "N∈{100,1k,10k,100k} paired with frozen transformer baselines.  "
            "anti-regression: ADR-0057 — three-gate defense against learning "
            "harmful chains (eligibility / replay-equivalence / operator).  "
            "learning-loop: ADR-0055..0057 — full cold-turn → discovery → "
            "propose → accept → same-prompt-now-grounded walkthrough.  "
            "articulation: discourse-planner spine — EXPLAIN / COMPOUND / "
            "WALKTHROUGH multi-sentence articulation + determinism gate.  "
            "conversation: layperson-facing chat transcript with live "
            "word-by-word streaming and plain-English captions.  "
            "audit-passed <domain>: per-domain runnable audit-passed "
            "showcase (ADR-0112 + ADR-0113). Reads the signed "
            "audit_passed_claims entry, re-derives the digest from "
            "on-disk lane result files, asserts byte-for-byte match, "
            "surfaces sample cases per attached lane × split. The "
            "audit-passed gate verifies CORE claim-shape compliance "
            "(signed digest, replay determinism, typed refusal, exact "
            "recall) — claim shapes a transformer LLM cannot "
            "structurally produce regardless of raw accuracy. NOT a "
            "raw-capability claim. Pair with --domain <id>.  "
            "list-results: index every JSON report in the results directory."
        ),
    )
    demo.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    demo.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help=(
            "parallel worker count for supported demos "
            "(0/1 => sequential; default 4)"
        ),
    )
    demo.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "for `showcase` target: directory where the showcase JSON, "
            "HTML, and per-scene artifacts are written "
            "(default: evals/public_demo/results/<sha>/)"
        ),
    )
    demo.add_argument(
        "--domain",
        type=str,
        default=None,
        metavar="ID",
        help=(
            "for `expert` target: domain id whose signed expert_demo "
            "claim should be rendered (e.g. `mathematics_logic`, `physics`)"
        ),
    )
    demo.add_argument(
        "--no-stream",
        dest="no_stream",
        action="store_true",
        help=(
            "for `conversation` target: disable per-character/per-word "
            "streaming delays (used by CI / tests / fast capture)"
        ),
    )
    demo.set_defaults(func=cmd_demo)

    eval_cmd = subparsers.add_parser("eval", help="run eval lanes")
    eval_cmd.add_argument("lane", nargs="?", help="eval lane name (e.g. cognition)")
    eval_cmd.add_argument("--list", dest="list_lanes", action="store_true", help="list available eval lanes")
    eval_cmd.add_argument("--version", help="version to evaluate (default: latest)")
    eval_cmd.add_argument("--split", default="public", choices=["dev", "public", "holdout"], help="which split to score (default: public)")
    eval_cmd.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help=(
            "parallel worker count for cognition lane "
            "(0/1 => sequential; default 4)"
        ),
    )
    eval_cmd.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    eval_cmd.add_argument("--save", action="store_true", help="write result to lane results/ directory")
    eval_cmd.add_argument("--report", metavar="PATH", help="write JSON report to file")
    eval_cmd.set_defaults(func=cmd_eval)

    from formation.cli import register as _register_formation
    _register_formation(subparsers)

    contemplation = subparsers.add_parser(
        "contemplation",
        help="run ADR-0080 read-only contemplation over explicit evidence files",
    )
    contemplation.add_argument(
        "reports",
        nargs="+",
        type=Path,
        help="report JSON path(s) to contemplate; must share --lane",
    )
    contemplation.add_argument(
        "--lane",
        choices=("frontier_compare", "contradiction_detection"),
        default="frontier_compare",
        help="evidence lane the reports belong to (default: frontier_compare)",
    )
    contemplation.add_argument(
        "--pack-id",
        action="append",
        default=(),
        help="optional pack id to include in substrate snapshot; may repeat",
    )
    contemplation.add_argument(
        "--note",
        action="append",
        default=(),
        help="optional operator note included in substrate snapshot; may repeat",
    )
    contemplation.add_argument(
        "--report",
        type=Path,
        default=None,
        help="optional output path for the contemplation run JSON blob",
    )
    contemplation.add_argument(
        "--sink-root",
        type=Path,
        default=None,
        help=(
            "optional append-only JSONL sink root; findings land at "
            "<root>/<YYYY>/<YYYY-MM>.jsonl alongside discovery candidates"
        ),
    )
    contemplation.set_defaults(func=cmd_contemplation)

    doctor = subparsers.add_parser("doctor", help="check runtime imports and packaging health")
    doctor.add_argument("--packs", action="store_true", help="also list discovered language packs")
    doctor.add_argument("--rust", action="store_true", help="also show Rust backend activation status")
    doctor.add_argument("--require-rust", action="store_true", help="exit nonzero when --rust shows inactive backend")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def _print_version() -> None:
    try:
        from importlib.metadata import version

        print(version("core-versor"))
    except Exception:
        print("core-versor unknown")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    args, unknown = parser.parse_known_args(raw_args)
    if unknown:
        if getattr(args, "command", None) != "test":
            parser.error(f"unrecognized arguments: {' '.join(unknown)}")
        args.args = [*(getattr(args, "args", None) or ()), *unknown]
    if args.print_version:
        _print_version()
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
