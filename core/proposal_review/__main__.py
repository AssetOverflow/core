"""CLI for the read-only proposal review reporter (RPT-c).

    python -m core.proposal_review                    # text report + safety dry-check
    python -m core.proposal_review comprehension-failures
    python -m core.proposal_review --json             # machine-readable
    python -m core.proposal_review --root <path>      # override the sink

Read-only: scans, reports, and dry-checks the comprehension-failure proposal sink. **Mutates
nothing.** Exit 0 iff the safety dry-check passes (every artifact inert + serving unconsumed).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.proposal_review.report import build_report, report_text
from core.proposal_review.safety import dry_check
from core.proposal_review.scan import scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m core.proposal_review",
        description="Read-only comprehension-failure proposal review (observes; never mounts/ratifies).",
    )
    parser.add_argument(
        "target", nargs="?", default="comprehension-failures", choices=["comprehension-failures"]
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--root", default=None, help="override the sink path")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else None
    proposals, malformed = scan(root)
    report = build_report(proposals, malformed)
    verdict = dry_check(proposals, malformed, root=root)

    if args.json:
        print(
            json.dumps(
                {
                    "report": report.to_json_dict(),
                    "safety": {"ok": verdict.ok, "violations": list(verdict.violations)},
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(report_text(report))
        print(f"  safety: {'OK' if verdict.ok else f'VIOLATIONS ({len(verdict.violations)})'}")
        for v in verdict.violations:
            print(f"    ! {v}")
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
