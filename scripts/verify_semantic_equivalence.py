"""Verify the ADR-0184 S4b semantic replay-equivalence pin.

Regenerates the canonical candidate trace for every problem in the
GSM8K/derivation corpus and compares it — per problem, per dimension — against
the committed reference artifact
(``evals/gsm8k_math/equivalence/v1/expected_traces.jsonl``).  The artifact pins
the behavior that the #684/#685 cross-tree differentials proved byte-equal to
the pre-semantic-ledger legacy path, so a mismatch here means the semantic
candidate source drifted from proven behavior.

Update the pin with ``--update`` ONLY when a derivation-lane change is
intentional and reviewed.  The artifact diff is the audit trail — never update
it to silence a failure you cannot explain.

Usage:

    python scripts/verify_semantic_equivalence.py            # verify; exit non-zero on drift
    python scripts/verify_semantic_equivalence.py --update   # rewrite the reference artifact
    python scripts/verify_semantic_equivalence.py --json     # machine-readable report
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evals.gsm8k_math.equivalence import trace as eq  # noqa: E402


def _current_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def _update(live: list[dict[str, object]]) -> int:
    eq.EXPECTED_TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with eq.EXPECTED_TRACES_PATH.open("w") as handle:
        for trace in live:
            handle.write(eq.trace_line(trace))
            handle.write("\n")
    manifest = {
        "version": "v1",
        "problem_count": len(live),
        "corpus_sha": eq.traces_sha(live),
        "pinned_at_commit": _current_commit(),
        "provenance": (
            "Pins derivation-lane candidate behavior proven byte-equal to the "
            "pre-semantic-ledger legacy path by the PR #684 and #685 cross-tree "
            "differentials (937 problems, 0 differences each). ADR-0184 S4b."
        ),
        "regenerate": "python scripts/verify_semantic_equivalence.py --update",
    }
    eq.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"pinned {len(live)} problem traces -> {eq.EXPECTED_TRACES_PATH}")
    print(f"corpus sha {manifest['corpus_sha']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="rewrite the reference artifact")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args()

    live = eq.corpus_traces()
    if args.update:
        return _update(live)

    if not eq.EXPECTED_TRACES_PATH.exists():
        print("no reference artifact; run with --update to pin one", file=sys.stderr)
        return 2

    expected = eq.load_expected_traces()
    manifest = eq.load_manifest()
    differences = list(eq.compare_traces(expected, live))
    expected_sha = eq.traces_sha(expected)
    if manifest.get("corpus_sha") != expected_sha:
        differences.insert(
            0,
            "manifest corpus_sha does not match the committed artifact "
            "(artifact edited without --update?)",
        )
    authority = [
        f"{trace['problem_sha'][:16]}: {violation}"  # type: ignore[index]
        for trace in live
        for violation in eq.authority_violations(trace)
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "problems": len(live),
                    "live_sha": eq.traces_sha(live),
                    "expected_sha": expected_sha,
                    "differences": differences,
                    "authority_violations": authority,
                },
                indent=2,
            )
        )
    else:
        for line in differences + authority:
            print(f"  ✗ {line}")
        status = "EQUIVALENT" if not (differences or authority) else "DRIFT DETECTED"
        print(f"{len(live)} problems; {len(differences)} differences, "
              f"{len(authority)} authority violations -> {status}")

    return 0 if not (differences or authority) else 1


if __name__ == "__main__":
    raise SystemExit(main())
