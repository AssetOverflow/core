#!/usr/bin/env python3
"""Seal eval holdout JSONL files with age recipients.

This script intentionally performs recipient-only encryption. Identity/private
key material is never read by this command.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pyrage import encrypt
from pyrage import x25519

DEFAULT_EVALS_ROOT = Path("evals")
PLAINTEXT_NAMES = ("cases_plaintext.jsonl", "cases.jsonl")


@dataclass(frozen=True, slots=True)
class SealPlan:
    source: Path
    target: Path


def _recipient(value: str) -> x25519.Recipient:
    value = value.strip()
    if not value:
        raise ValueError("recipient must not be empty")
    return x25519.Recipient.from_str(value)


def _iter_holdout_dirs(evals_root: Path, lane: str | None) -> Iterable[Path]:
    if lane is not None:
        candidate = evals_root / lane / "holdouts"
        if candidate.is_dir():
            yield candidate
        return

    if not evals_root.is_dir():
        return
    for child in sorted(evals_root.iterdir()):
        holdouts = child / "holdouts"
        if holdouts.is_dir():
            yield holdouts


def _plans_for_dir(holdouts_dir: Path, version: str | None) -> list[SealPlan]:
    roots = [holdouts_dir]
    if version is not None:
        roots = [holdouts_dir / version]

    plans: list[SealPlan] = []
    for root in roots:
        if not root.is_dir():
            continue
        for name in PLAINTEXT_NAMES:
            source = root / name
            if source.exists():
                plans.append(SealPlan(source=source, target=root / "cases.jsonl.age"))
                break
    return plans


def discover_plans(evals_root: Path, lane: str | None, version: str | None) -> list[SealPlan]:
    plans: list[SealPlan] = []
    for holdouts_dir in _iter_holdout_dirs(evals_root, lane):
        plans.extend(_plans_for_dir(holdouts_dir, version))
    return plans


def seal(plan: SealPlan, recipient: x25519.Recipient, *, overwrite: bool) -> None:
    if plan.target.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing sealed holdout: {plan.target}. "
            "Pass --overwrite to replace it."
        )
    ciphertext = encrypt(plan.source.read_bytes(), [recipient])
    plan.target.write_bytes(ciphertext)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipient", required=True, help="age x25519 recipient")
    parser.add_argument("--evals-root", type=Path, default=DEFAULT_EVALS_ROOT)
    parser.add_argument("--lane", help="seal only evals/<lane>/holdouts")
    parser.add_argument("--version", help="seal only holdouts/<version>")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    recipient = _recipient(args.recipient)
    plans = discover_plans(args.evals_root, args.lane, args.version)

    if not plans:
        print("No plaintext holdouts discovered.")
        return 0

    for plan in plans:
        action = "would seal" if args.dry_run else "sealed"
        print(f"{action}: {plan.source} -> {plan.target}")
        if not args.dry_run:
            seal(plan, recipient, overwrite=args.overwrite)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
