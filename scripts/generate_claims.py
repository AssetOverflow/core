"""Generate CLAIMS.md from the capability ledger and pinned lane SHAs.

CLAIMS.md is a single-page, auditable list of every CI-pinned
capability claim CORE currently makes. It is **mechanically derived**
from two ground-truth sources:

- ``core.capability.ledger_report()`` — domain ratification rows
  (Tier 1: "this domain is reasoning-capable").
- ``scripts.verify_lane_shas.PINNED_SHAS`` + ``LANE_SPECS`` —
  per-lane pinned report SHA-256 (Tier 2: "this lane's report bytes
  hash to X under deterministic replay").

The generator is **deterministic**: same inputs → byte-identical
output. ``tests/test_claims_md_is_current.py`` regenerates the file
into a temp path and asserts byte equality with the on-disk copy.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAIMS_PATH = REPO_ROOT / "CLAIMS.md"

# Import via path so this script remains runnable without installing the
# package.
sys.path.insert(0, str(REPO_ROOT))

from core.capability import ledger_report  # noqa: E402
from scripts.verify_lane_shas import LANE_SPECS, PINNED_SHAS  # noqa: E402  # type: ignore[import-not-found]


# ADR → human-readable lane purpose. Keep this in lockstep with the
# ADR docs themselves; the generator fails fast if any lane lacks a
# mapping here, which surfaces drift before CI does.
_LANE_ADR: dict[str, tuple[str, str]] = {
    "reviewer_registry": (
        "ADR-0092",
        "Reviewer registry schema validates + bootstrap entry self-seals",
    ),
    "miner_loop_closure": (
        "ADR-0095",
        "Miner-sourced proposals route through single reviewed teaching path",
    ),
    "curriculum_loop_closure": (
        "ADR-0104",
        "Curriculum-sourced proposals route through single reviewed teaching path",
    ),
    "domain_contract_validation": (
        "ADR-0093",
        "All ratified packs satisfy the 9 ADR-0091 contract predicates",
    ),
    "fabrication_control_summary": (
        "ADR-0096",
        "Phantom endpoints / cross-pack non-bridges / sibling collapses refuse",
    ),
    "demo_composition": (
        "ADR-0098",
        "Demos compose from shipped modules; no parallel mechanism",
    ),
    "public_demo": (
        "ADR-0099",
        "Public showcase runs deterministically under 30s; all claims supported",
    ),
    "math_teaching_corpus_v1": (
        "ADR-0131",
        "Math teaching corpus replays deterministically; all chains pass exit criterion (correct_rate=1.0, wrong=0)",
    ),
}


# Domain → ratifying ADR. The ledger row already carries provenance
# inside each contract (e.g. "adr-0101:reviewed:2026-05-21"), but we
# pin the canonical ADR id here so the table reads cleanly even if a
# pack later carries a different provenance prefix.
_DOMAIN_ADR: dict[str, str] = {
    "systems_software": "ADR-0101",
    "mathematics_logic": "ADR-0097",
    "physics": "ADR-0100",
    "hebrew_greek_textual_reasoning": "ADR-0102",
    "philosophy_theology": "ADR-0085",
}


@dataclass(frozen=True, slots=True)
class DomainRow:
    domain: str
    status: str
    adr: str
    pack_count: int
    open_gaps_count: int


@dataclass(frozen=True, slots=True)
class LaneRow:
    lane_id: str
    adr: str
    purpose: str
    report_path: str
    pinned_sha: str


def _collect_domain_rows() -> list[DomainRow]:
    report = ledger_report()
    rows: list[DomainRow] = []
    for entry in report["domains"]:
        domain = entry["domain"]
        if domain not in _DOMAIN_ADR:
            raise RuntimeError(
                f"domain {domain!r} missing from _DOMAIN_ADR mapping in "
                f"scripts/generate_claims.py — add its ratifying ADR id."
            )
        rows.append(
            DomainRow(
                domain=domain,
                status=entry["status"],
                adr=_DOMAIN_ADR[domain],
                pack_count=len(entry["packs"]),
                open_gaps_count=len(entry["open_gaps"]),
            )
        )
    # Deterministic ordering: by ADR id (lexicographic), then domain.
    return sorted(rows, key=lambda r: (r.adr, r.domain))


def _collect_lane_rows() -> list[LaneRow]:
    rows: list[LaneRow] = []
    for spec in LANE_SPECS:
        if spec.lane_id not in _LANE_ADR:
            raise RuntimeError(
                f"lane {spec.lane_id!r} missing from _LANE_ADR mapping in "
                f"scripts/generate_claims.py — add its ADR id and purpose."
            )
        adr, purpose = _LANE_ADR[spec.lane_id]
        pinned = PINNED_SHAS.get(spec.lane_id)
        if not pinned:
            raise RuntimeError(
                f"lane {spec.lane_id!r} has no entry in PINNED_SHAS — "
                f"run scripts/verify_lane_shas.py --update first."
            )
        rows.append(
            LaneRow(
                lane_id=spec.lane_id,
                adr=adr,
                purpose=purpose,
                report_path=spec.report_relative,
                pinned_sha=pinned,
            )
        )
    return sorted(rows, key=lambda r: r.adr)


def _render(
    *, domain_rows: list[DomainRow], lane_rows: list[LaneRow]
) -> str:
    """Render CLAIMS.md as a deterministic markdown string.

    Two tables. No timestamps, no git revs, no wall-clock — anything
    volatile would break the "regenerate and compare bytes" test.
    """
    lines: list[str] = [
        "# CLAIMS",
        "",
        "<!--",
        "AUTO-GENERATED by scripts/generate_claims.py.",
        "Do not hand-edit. Run `python3 scripts/generate_claims.py` to",
        "regenerate after any change to the capability ledger or pinned",
        "lane SHAs (scripts/verify_lane_shas.py).",
        "-->",
        "",
        "Every row below is mechanically derived from in-tree state and",
        "verified by CI. Tier 1 rows come from `core.capability.ledger_report`;",
        "Tier 2 rows come from `scripts/verify_lane_shas.py`'s pinned SHAs.",
        "",
        "## Tier 1 — Ratified domains",
        "",
        "Each row asserts: the domain's packs pass all nine ADR-0091 contract",
        "predicates, declared operator chains meet the ≥8 / ≥3-intent floor,",
        "the reviewer registry resolves the primary reviewer, and the ledger",
        "status predicate evaluates to `reasoning-capable` with no open gaps.",
        "",
        "| Domain | Status | ADR | Packs | Open gaps |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in domain_rows:
        lines.append(
            f"| `{row.domain}` | {row.status} | {row.adr} | {row.pack_count} | "
            f"{row.open_gaps_count} |"
        )
    lines.extend(
        [
            "",
            "## Tier 2 — Pinned lane reports",
            "",
            "Each row asserts: running the lane's runner produces a JSON",
            "report whose SHA-256 matches the pinned value below. Mismatch",
            "is a CI failure (`.github/workflows/lane-shas.yml`).",
            "",
            "| ADR | Lane | Purpose | Report path | Pinned SHA-256 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in lane_rows:
        lines.append(
            f"| {row.adr} | `{row.lane_id}` | {row.purpose} | "
            f"`{row.report_path}` | `{row.pinned_sha}` |"
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```bash",
            "python3 scripts/verify_lane_shas.py    # verify all Tier 2 SHAs",
            "core test --suite full -q              # exercises Tier 1 invariants",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_claims() -> bytes:
    domain_rows = _collect_domain_rows()
    lane_rows = _collect_lane_rows()
    text = _render(domain_rows=domain_rows, lane_rows=lane_rows)
    return text.encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate CLAIMS.md")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if CLAIMS.md differs from regenerated bytes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CLAIMS_PATH,
        help="write to this path (default: repo-root CLAIMS.md)",
    )
    args = parser.parse_args(argv)

    payload = render_claims()
    sha = hashlib.sha256(payload).hexdigest()

    if args.check:
        if not CLAIMS_PATH.exists():
            print(f"FAIL: {CLAIMS_PATH} does not exist; run without --check")
            return 1
        on_disk = CLAIMS_PATH.read_bytes()
        if on_disk != payload:
            print("FAIL: CLAIMS.md is stale — regenerate with:")
            print("  python3 scripts/generate_claims.py")
            print(f"  on-disk sha256: {hashlib.sha256(on_disk).hexdigest()}")
            print(f"  computed sha256: {sha}")
            return 1
        print(f"OK: CLAIMS.md is current (sha256: {sha})")
        return 0

    args.output.write_bytes(payload)
    print(f"wrote {args.output} (sha256: {sha})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
