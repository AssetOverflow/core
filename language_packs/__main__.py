"""
python -m language_packs <command> [pack_id]

Commands
--------
compile <pack_id>   Compile pack, verify checksum, print manifold stats.
verify  <pack_id>   Verify on-disk checksum against manifest only.
list                List all packs in language_packs/data/ with metadata.

Checksum contract
-----------------
The checksum is always computed from the raw bytes on disk:
    hashlib.sha256(Path(lexicon_path).read_bytes()).hexdigest()
This is the AGENTS.md rule: hash what disk holds, not what Python strings hold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _available_packs() -> list[str]:
    if not _DATA_DIR.exists():
        return []
    return sorted(p.name for p in _DATA_DIR.iterdir() if p.is_dir())


def cmd_list(_args) -> int:
    packs = _available_packs()
    if not packs:
        print("No packs found in language_packs/data/")
        return 0
    print(f"{'pack_id':<30} {'role':<20} {'entries':>7} {'checksum_ok'}")
    print("-" * 70)
    for pack_id in packs:
        pack_dir = _DATA_DIR / pack_id
        manifest_path = pack_dir / "manifest.json"
        lexicon_path = pack_dir / "lexicon.jsonl"
        if not manifest_path.exists() or not lexicon_path.exists():
            print(f"{pack_id:<30} {'<missing files>':<20}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual = _checksum(lexicon_path)
        ok = "\u2713" if actual == manifest.get("checksum", "") else "\u2717 MISMATCH"
        entries = sum(1 for line in lexicon_path.read_text(encoding="utf-8").splitlines() if line.strip())
        role = manifest.get("role", "?")
        print(f"{pack_id:<30} {role:<20} {entries:>7}   {ok}")
    return 0


def cmd_verify(args) -> int:
    pack_id = args.pack_id
    pack_dir = _DATA_DIR / pack_id
    manifest_path = pack_dir / "manifest.json"
    lexicon_path = pack_dir / "lexicon.jsonl"

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if not lexicon_path.exists():
        print(f"ERROR: lexicon not found: {lexicon_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = _checksum(lexicon_path)
    expected = manifest.get("checksum", "")

    if actual == expected:
        print(f"{pack_id}: checksum OK ({actual[:16]}...)")
        return 0
    else:
        print(f"ERROR: checksum MISMATCH for {pack_id}", file=sys.stderr)
        print(f"  expected: {expected}", file=sys.stderr)
        print(f"  actual:   {actual}", file=sys.stderr)
        print(f"  Fix: update manifest.json checksum to: {actual}", file=sys.stderr)
        return 1


def cmd_compile(args) -> int:
    # Verify first
    rc = cmd_verify(args)
    if rc != 0:
        return rc

    pack_id = args.pack_id
    from language_packs.compiler import load_pack, load_pack_entries

    try:
        manifest, manifold = load_pack(pack_id)
        entries = load_pack_entries(pack_id)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    n_entries = len(entries)
    n_points = len(manifold)
    print(f"{pack_id}: compiled {n_entries} entries -> {n_points} manifold points")
    print(f"  language:         {manifest.language}")
    print(f"  role:             {manifest.role.value}")
    print(f"  determinism:      {manifest.determinism_class}")
    print(f"  oov_policy:       {manifest.oov_policy.value}")
    print(f"  gate_engaged:     {manifest.gate_engaged}")
    print(f"  version:          {manifest.version}")

    # Spot-check: first and last surface should round-trip through manifold
    first = entries[0].surface
    last = entries[-1].surface
    try:
        manifold.get_versor(first)
        manifold.get_versor(last)
        print(f"  spot-check:       '{first}' and '{last}' resolve OK")
    except KeyError as exc:
        print(f"  WARNING: spot-check failed: {exc}", file=sys.stderr)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m language_packs",
        description="CORE language-pack compiler and verifier.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all available packs.")

    p_verify = sub.add_parser("verify", help="Verify pack checksum.")
    p_verify.add_argument("pack_id", help="Pack ID (directory name under language_packs/data/).")

    p_compile = sub.add_parser("compile", help="Compile pack and print manifold stats.")
    p_compile.add_argument("pack_id", help="Pack ID (directory name under language_packs/data/).")

    args = parser.parse_args()

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command == "compile":
        return cmd_compile(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
