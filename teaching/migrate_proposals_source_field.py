"""One-shot deterministic migration: attach ``source`` to legacy proposals (ADR-0094).

Walks a ``proposals.jsonl`` file and rewrites every ``event: created``
line whose ``proposal`` dict lacks a ``source`` field, attaching a
deterministic operator-authored :class:`ProposalSource` pinned at the
sentinel revision ``"pre-adr-0094-migration"``.

Determinism guarantee: same input file → byte-identical output file.
The sentinel revision (not current HEAD) is used so re-runs across
different commits still produce identical bytes.

Non-``created`` events are passed through unchanged. Lines that
already carry a ``source`` field are not re-migrated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PRE_MIGRATION_SENTINEL: str = "pre-adr-0094-migration"
DEFAULT_OPERATOR_SOURCE_PAYLOAD: dict[str, str] = {
    "kind": "operator",
    "source_id": "",
    "emitted_at_revision": PRE_MIGRATION_SENTINEL,
}


def migrate_file(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Migrate ``path`` in place. Returns a summary of changes.

    ``dry_run`` skips the file write but still reports counts.
    """
    if not path.exists():
        raise FileNotFoundError(f"proposals log not found at {path}")

    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines()

    migrated_lines: list[str] = []
    migrated_count = 0
    skipped_count = 0
    untouched_count = 0

    for raw in lines:
        if not raw.strip():
            migrated_lines.append(raw)
            untouched_count += 1
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            migrated_lines.append(raw)
            untouched_count += 1
            continue

        if event.get("event") != "created":
            migrated_lines.append(raw)
            untouched_count += 1
            continue

        proposal = event.get("proposal")
        if not isinstance(proposal, dict):
            migrated_lines.append(raw)
            untouched_count += 1
            continue

        if "source" in proposal:
            migrated_lines.append(raw)
            skipped_count += 1
            continue

        proposal["source"] = dict(DEFAULT_OPERATOR_SOURCE_PAYLOAD)
        event["proposal"] = proposal
        migrated_lines.append(
            json.dumps(event, sort_keys=True, separators=(",", ":"))
        )
        migrated_count += 1

    new_bytes = ("\n".join(migrated_lines) + "\n").encode("utf-8") if migrated_lines else b""

    if not dry_run and new_bytes != original:
        path.write_bytes(new_bytes)

    return {
        "path": str(path),
        "total_lines": len(lines),
        "migrated_count": migrated_count,
        "already_had_source": skipped_count,
        "untouched_count": untouched_count,
        "bytes_before": len(original),
        "bytes_after": len(new_bytes),
        "changed": new_bytes != original,
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-0094 source-field migration")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(__file__).resolve().parent / "proposals" / "proposals.jsonl",
        help="proposals.jsonl path to migrate (default: in-tree live log)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing",
    )
    args = parser.parse_args(argv)

    summary = migrate_file(args.path, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
