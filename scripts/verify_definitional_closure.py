#!/usr/bin/env python3
"""Verify ADR-0084 definitional closure across mounted definitional packs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "language_packs" / "data"
PRIMITIVES_PATH = REPO_ROOT / "packs" / "primitives" / "en_semantic_primitives_v1" / "primitives.jsonl"
TOKEN_RE = re.compile(r"[A-Za-z_]+")
STOPWORDS = {"is", "of", "to", "by", "the", "a", "an", "that", "which"}
PREPOSITIONS = {
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "into",
    "between",
    "before",
    "after",
    "during",
    "while",
    "until",
    "since",
    "through",
    "within",
    "without",
    "as",
    "under",
    "over",
    "about",
    "against",
    "toward",
    "towards",
    "across",
    "than",
}
SKIP_TOKENS = STOPWORDS | PREPOSITIONS


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_resolution_set() -> set[str]:
    lemmas: set[str] = set()
    for lex_path in DATA_ROOT.glob("*/lexicon.jsonl"):
        for row in _load_jsonl(lex_path):
            lemma = row.get("lemma")
            if isinstance(lemma, str):
                lemmas.add(lemma)
    for gloss_path in DATA_ROOT.glob("*/glosses.jsonl"):
        for row in _load_jsonl(gloss_path):
            lemma = row.get("lemma")
            if isinstance(lemma, str):
                lemmas.add(lemma)
    for row in _load_jsonl(PRIMITIVES_PATH):
        lemma = row.get("lemma")
        if isinstance(lemma, str):
            lemmas.add(lemma)
    return lemmas


def _definitional_pack_manifests() -> list[Path]:
    manifests: list[Path] = []
    for manifest_path in DATA_ROOT.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if manifest.get("definitional_layer") is True:
            manifests.append(manifest_path)
    return sorted(manifests)


def _content_tokens(gloss: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(gloss)]
    ordered: list[str] = []
    for token in tokens:
        if token in SKIP_TOKENS:
            continue
        if token not in ordered:
            ordered.append(token)
    return ordered


def verify() -> dict:
    resolution_set = _load_resolution_set()
    total_entries = 0
    total_atoms = 0
    unresolved_by_pack: dict[str, list[str]] = defaultdict(list)
    mismatched_atoms_by_pack: dict[str, list[str]] = defaultdict(list)

    for manifest_path in _definitional_pack_manifests():
        pack_dir = manifest_path.parent
        gloss_path = pack_dir / "glosses.jsonl"
        pack_id = pack_dir.name
        for row in _load_jsonl(gloss_path):
            total_entries += 1
            atoms = row.get("definitional_atoms", [])
            if not isinstance(atoms, list):
                unresolved_by_pack[pack_id].append(f"{row.get('lemma','<unknown>')}:<non-list-atoms>")
                continue
            gloss = row.get("gloss")
            if not isinstance(gloss, str):
                mismatched_atoms_by_pack[pack_id].append(f"{row.get('lemma','<unknown>')}:<missing-gloss>")
                continue
            expected_atoms = _content_tokens(gloss)
            if atoms != expected_atoms:
                mismatched_atoms_by_pack[pack_id].append(
                    f"{row.get('lemma','<unknown>')}:expected={expected_atoms}:actual={atoms}"
                )
            for atom in atoms:
                total_atoms += 1
                if not isinstance(atom, str) or atom not in resolution_set:
                    unresolved_by_pack[pack_id].append(f"{row.get('lemma','<unknown>')}:{atom}")

    unresolved_by_pack = {pack: items for pack, items in unresolved_by_pack.items() if items}
    mismatched_atoms_by_pack = {pack: items for pack, items in mismatched_atoms_by_pack.items() if items}
    return {
        "total_entries_checked": total_entries,
        "total_definitional_atoms_checked": total_atoms,
        "unresolved_by_pack": unresolved_by_pack,
        "mismatched_atoms_by_pack": mismatched_atoms_by_pack,
        "definitional_pack_count": len(_definitional_pack_manifests()),
        "primitive_pack_path": str(PRIMITIVES_PATH.relative_to(REPO_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    report = verify()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"total entries checked: {report['total_entries_checked']}")
        print(f"total definitional_atoms checked: {report['total_definitional_atoms_checked']}")
        if report["unresolved_by_pack"]:
            print("unresolved tokens grouped by pack:")
            for pack, items in sorted(report["unresolved_by_pack"].items()):
                print(f"- {pack}: {', '.join(items)}")
        else:
            print("unresolved tokens grouped by pack: none")
        if report["mismatched_atoms_by_pack"]:
            print("gloss/atom mismatches grouped by pack:")
            for pack, items in sorted(report["mismatched_atoms_by_pack"].items()):
                print(f"- {pack}: {', '.join(items)}")
        else:
            print("gloss/atom mismatches grouped by pack: none")
    return 0 if not report["unresolved_by_pack"] and not report["mismatched_atoms_by_pack"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
