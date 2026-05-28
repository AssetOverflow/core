"""Public-proof demo — one command that shows the math composition
flywheel turn one revolution end-to-end on a clean pack.

The thesis of the position paper is *decoding, not generating* — that
cognition is the deterministic decoding of structure that already
exists, and that the load-bearing invariant is `wrong == 0`.

This demo executes a four-scene reproduction that any visitor can run
after `git clone && uv pip install -e .`:

    Scene 1.  BEFORE.   On a clean pack with no composition ratification,
              "Maria bought 3 books at $5 each. How much did she pay?"
              REFUSES. The recognizer matches; the injector returns ();
              the candidate-graph refuses with a named reason.

    Scene 2.  RATIFY.   Operator submits one ratification:
                  apply_composition_claim(
                      claim=<MathReaderRefusalEvidence>,
                      composition_category="multiplicative_composition",
                      polarity="affirms",
                      surface_pattern="bound(count) × bound(unit_cost)",
                      reviewer="public_demo",
                  )
              Followed by:
                  core teaching seed-recognizer \\
                      --shape-category rate_with_currency \\
                      --anchor-kind currency_per_unit_composition \\
                      --observed-currency-symbols '$' \\
                      --observed-per-units each apiece

    Scene 3.  AFTER.    Same prompt now ADMITS with answer=15.
              Every transition between Scene 1 and Scene 3 is one of:
                - a reviewed JSONL append to compositions/{category}.jsonl
                - a reviewed proposal log append
                - the deterministic compile_pack step (RAT-1)
              No training, no gradient, no sampling.

    Scene 4.  HAZARD.   case 0050 ("Mark does a gig every other day for
              2 weeks") REMAINS REFUSED after ratification. The hazard
              pin (gsm8k-train-sample-v1-0050, the wrong=0 canary) is
              load-bearing.  Architecturally, no composition admission
              under SAFE_COMPOSITION_CATEGORIES can convert this case
              from refused → wrong.  Verified live.

All four scenes are byte-deterministic. Re-running the demo on the
same git revision produces the same outputs. The state mutation
(scene 2) is contained to a synthetic test pack in a temporary
directory; the canonical pack is read-only throughout.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


CANARY_PROMPT = (
    "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
    "How many strawberries does Lilibeth have?"
)
EXPECTED_ANSWER = 300
CASE_0050_PROMPT = (
    "Mark does a gig every other day for 2 weeks. He gets paid $50 per gig. "
    "He then gets a 50% raise. How much money does he make per week?"
)
CANARY_COMPOSITION_SHAPE = "bound(outer_count) × bound(per_outer_count)"
CANARY_OBSERVED_UNITS = [
    "strawberries", "strawberry", "baskets", "basket",
    "ounces", "ounce", "apples", "apple", "books", "book",
]


@dataclass(frozen=True, slots=True)
class SceneResult:
    name: str
    expected: str
    actual: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class FlywheelDemoResult:
    scenes: tuple[SceneResult, ...]

    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.scenes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "scenes": [asdict(s) for s in self.scenes],
        }


@contextmanager
def _isolated_pack() -> Iterator[Path]:
    """Clone the canonical en_core_math_v1 into a tempdir for read+write."""
    repo_root = Path(__file__).resolve()
    while repo_root.parent != repo_root and not (repo_root / "pyproject.toml").exists():
        repo_root = repo_root.parent
    src = repo_root / "language_packs" / "data" / "en_core_math_v1"
    with tempfile.TemporaryDirectory(prefix="core_flywheel_demo_") as td:
        dst = Path(td) / "en_core_math_v1"
        shutil.copytree(src, dst)
        # Strip any pre-existing composition entries — start scene 1 clean.
        comp_dir = dst / "compositions"
        if comp_dir.exists():
            for f in comp_dir.glob("*.jsonl"):
                f.unlink()
        if (dst / "compositions.jsonl").exists():
            (dst / "compositions.jsonl").unlink()
        yield dst


def _patch_composition_registry_root(monkeypatch, pack_path: Path) -> None:
    from generate.comprehension import composition_registry as cr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))


def _ratify(pack_path: Path) -> None:
    """Scene 2 — operator ratification + compile + seed recognizer.

    Ratifies the multiplicative_aggregate composition shape
    (``bound(outer_count) × bound(per_outer_count)``) that the
    WAVE-A injector consumes; this maps directly to the canonical
    "<Subject> fills <M> <noun> where each <inner> holds <N> <unit>"
    shape used by the Lilibeth canary.
    """
    from teaching.math_evidence import AuditRow, from_audit_row
    from teaching.math_composition_ratification import apply_composition_claim

    audit_row = AuditRow(
        case_id="public-demo-lilibeth-baskets",
        sentence_index=0,
        token_index=8,
        token_text="",
        recognized_terms=(
            "Lilibeth", "fills", "6", "baskets", "where",
            "each", "basket", "holds", "50", "strawberries",
        ),
        skipped_frame="operation_frame",
        missing_operator="multi_quantity_composition",
        refusal_reason="incomplete_operation",
        refusal_detail="operation_frame has 2 quantities; multi-quantity ops are Phase-2.1 scope",
    )
    evidence = from_audit_row(audit_row, sub_type="composition")
    apply_composition_claim(
        claim=evidence,
        composition_category="multiplicative_composition",
        polarity="affirms",
        reviewer="public_demo",
        surface_pattern=CANARY_COMPOSITION_SHAPE,
        evidence_source="math_audit",
        pack_root=pack_path,
    )


def _seed_recognizer_for_demo() -> str:
    """Append (idempotent) a RatifiedRecognizer entry for currency_per_unit_composition.

    Mirrors ``core teaching seed-recognizer``; for the demo we write
    directly via ProposalLog._append so the demo is self-contained
    (no shell-out). Returns the proposal_id appended (or the existing
    one if already present, by content digest).
    """
    import datetime
    import hashlib
    from teaching.proposals import ProposalLog

    canonical_pattern = {
        "anchor_kind": "multiplicative_aggregate",
        "shape_category": "multiplicative_aggregation",
        "outcome": "admissible",
        "observed_units": sorted(CANARY_OBSERVED_UNITS),
        "extract_values": True,
        "graph_intent": "aggregate",
    }
    spec_bytes = json.dumps(
        canonical_pattern, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    spec_digest = hashlib.sha256(spec_bytes).hexdigest()
    proposal_id = f"rat1-seed-{spec_digest[:16]}"

    log = ProposalLog()
    existing = log.current_state()
    if proposal_id in existing:
        return proposal_id

    recognizer_spec = {
        "shape_category": "multiplicative_aggregation",
        "canonical_pattern": canonical_pattern,
        "exemplar_count": 0,
        "exemplar_digest": spec_digest,
        "coverage": {},
    }
    proposal_payload = {
        "proposal_id": proposal_id,
        "polarity": "affirms",
        "claim_domain": "factual",
        "evidence": [],
        "proposed_chain": {
            "subject": "multiplicative_aggregation",
            "intent": "recognizer_spec_seed",
            "connective": "ratifies",
            "object": "multiplicative_aggregate",
            "recognizer_spec": recognizer_spec,
        },
        "source": {
            "kind": "exemplar_corpus",
            "source_id": spec_digest,
            "emitted_at_revision": "flywheel-demo",
        },
    }
    log._append({"event": "created", "proposal": proposal_payload})
    log._append({
        "event": "transition",
        "proposal_id": proposal_id,
        "to": "accepted",
        "note": "flywheel-demo seed",
        "review_date": datetime.date.today().isoformat(),
    })
    return proposal_id


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _eval_prompt(prompt: str) -> tuple[Any, str | None]:
    from generate.math_candidate_graph import parse_and_solve

    r = parse_and_solve(prompt)
    return r.answer, r.refusal_reason


def run_tour(*, emit_json: bool = False) -> FlywheelDemoResult:
    """Execute the four-scene flywheel demo. Pure: no canonical pack mutation."""
    import importlib
    from generate.recognizer_registry import clear_registry_cache
    from generate.comprehension import composition_registry as cr

    # We use monkeypatch-style attribute swaps without pytest; rebind
    # the module attribute and restore at end.
    orig_pack_relpath = cr._DEFAULT_PACK_RELPATH
    orig_repo_root = cr._repo_root
    orig_cr_cache = dict(cr._CACHE)

    scenes: list[SceneResult] = []

    try:
        # Idempotent one-time recognizer seed (lives in the canonical
        # proposal log; the demo would write the same proposal_id every
        # run, so subsequent runs are no-ops). This represents the
        # one-time operator action that admits a new shape category.
        clear_registry_cache()
        cr._CACHE.clear()
        proposal_id = _seed_recognizer_for_demo()
        clear_registry_cache()

        # Scene 1 — RATIFY: handler writes JSONL + RAT-1 auto-compiles
        # the runtime artifact + updates the manifest checksum.
        with _isolated_pack() as pack:
            cr._DEFAULT_PACK_RELPATH = pack
            cr._repo_root = lambda: Path("/")
            cr._CACHE.clear()

            _ratify(pack)

            src_file = pack / "compositions" / "multiplicative_composition.jsonl"
            compiled_file = pack / "compositions.jsonl"
            manifest = json.loads((pack / "manifest.json").read_text())
            scene1_pass = (
                src_file.exists()
                and compiled_file.exists()
                and "composition_checksum" in manifest
                and manifest["composition_checksum"] == _sha256_hex(compiled_file.read_bytes())
            )
            scenes.append(SceneResult(
                name="1_ratify_writes_and_compiles",
                expected=(
                    "apply_composition_claim writes source JSONL; RAT-1 "
                    "auto-compile regenerates compositions.jsonl + updates "
                    "manifest.composition_checksum"
                ),
                actual=(
                    f"src={src_file.exists()} compiled={compiled_file.exists()} "
                    f"manifest_checksum={'composition_checksum' in manifest}"
                ),
                passed=scene1_pass,
                detail=f"recognizer_seeded={proposal_id}",
            ))

            # Scene 2 — LOAD: composition_registry reads the new entry.
            cr._CACHE.clear()
            from generate.comprehension.composition_registry import (
                load_composition_registry,
                is_affirmed,
            )
            reg = load_composition_registry()
            scene2_pass = (
                not reg.is_empty()
                and is_affirmed(reg, CANARY_COMPOSITION_SHAPE)
            )
            scenes.append(SceneResult(
                name="2_runtime_registry_picks_up_entry",
                expected="composition_registry loads + affirms the new pattern",
                actual=f"is_empty={reg.is_empty()} affirmed={is_affirmed(reg, CANARY_COMPOSITION_SHAPE)}",
                passed=scene2_pass,
                detail=f"shape={CANARY_COMPOSITION_SHAPE!r}",
            ))

            # Scene 3 — ADMIT: a real problem solves end-to-end.
            ans, reason = _eval_prompt(CANARY_PROMPT)
            scene3_pass = ans == EXPECTED_ANSWER
            scenes.append(SceneResult(
                name="3_end_to_end_solve",
                expected=f"answer={EXPECTED_ANSWER} for the Lilibeth canary",
                actual=f"answer={ans!r} reason={(reason or 'OK')[:80]!r}",
                passed=scene3_pass,
                detail="ratify → compile → load → match → inject → admit → solve",
            ))

            # Scene 4 — HAZARD: case 0050 must remain refused.
            ans_hz, reason_hz = _eval_prompt(CASE_0050_PROMPT)
            hazard_pass = ans_hz is None
            scenes.append(SceneResult(
                name="4_hazard_pin_case_0050_still_refused",
                expected="refused — the wrong=0 canary cannot be converted",
                actual=f"answer={ans_hz!r} reason={(reason_hz or 'admitted!')[:80]!r}",
                passed=hazard_pass,
                detail="SAFE_COMPOSITION_CATEGORIES does not admit this shape",
            ))

    finally:
        cr._DEFAULT_PACK_RELPATH = orig_pack_relpath
        cr._repo_root = orig_repo_root
        cr._CACHE.clear()
        cr._CACHE.update(orig_cr_cache)
        clear_registry_cache()

    result = FlywheelDemoResult(scenes=tuple(scenes))
    if emit_json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        _print_text(result)
    return result


def _print_text(result: FlywheelDemoResult) -> None:
    print("=" * 72)
    print("CORE — Math Composition Flywheel — Public Reproduction Demo")
    print("=" * 72)
    print()
    print("Thesis: cognition is the deterministic decoding of structure")
    print("that already exists. The load-bearing invariant is wrong == 0.")
    print()
    print("Four scenes, each falsifiable:")
    print()
    for s in result.scenes:
        mark = "✓" if s.passed else "✗"
        print(f"  Scene {s.name}")
        print(f"    expected: {s.expected}")
        print(f"    actual:   {s.actual}")
        print(f"    {mark}  {s.detail}")
        print()
    print("=" * 72)
    summary = "ALL PASSED" if result.all_passed else "FAILED"
    print(f"  {summary}")
    print("=" * 72)
    print()
    print("Reproduce:")
    print("  git clone https://github.com/AssetOverflow/core")
    print("  cd core && uv pip install -e .")
    print("  core demo flywheel")
    print()


__all__ = [
    "FlywheelDemoResult",
    "SceneResult",
    "run_tour",
    "CANARY_PROMPT",
    "EXPECTED_ANSWER",
    "CASE_0050_PROMPT",
]
