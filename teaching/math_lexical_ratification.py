"""ADR-0167 W2-D — LexicalClaim ratification into math lexicon sources.

This module is the explicit post-review mutation boundary for lexical math
reader evidence.  It edits only per-category source files under
``en_core_math_v1/lexicon``; it does not regenerate the compiled
``lexicon.jsonl`` and therefore does not rewrite the manifest checksum.
"""

from __future__ import annotations

import hashlib
import json
import re
import string
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from teaching.math_evidence import MathReaderRefusalEvidence, from_audit_row


SAFE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "drain_token",
    }
)

_FRAME_OPENER_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "accumulation_verb",
        "capacity_verb",
        "copula_verb",
        "depletion_verb",
        "possession_verb",
        "transfer_verb",
    }
)
_REVIEWER_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_-]+")
_TRIM_PUNCTUATION: Final[str] = string.punctuation


class RatificationError(ValueError):
    """Base class for lexical ratification rejections."""


class WrongClaimSubType(RatificationError):
    """Raised when a non-lexical evidence record reaches this handler."""


class WrongZeroViolationCandidate(RatificationError):
    """Raised when a ratification could open a wrong>0 admission path."""


class AlreadyRatified(RatificationError):
    """Raised when the target surface is already covered by the source file."""


class EvidenceTampering(RatificationError):
    """Raised when the evidence hash no longer matches canonical bytes."""


class UnknownCategory(RatificationError):
    """Raised when the requested category is not a known lexicon source."""


@dataclass(frozen=True, slots=True)
class RatificationReceipt:
    target_file: str
    lemma: str
    category: str
    provenance: str
    file_sha256_before: str
    file_sha256_after: str
    evidence_hash: str
    is_alias: bool
    aliased_to: str | None


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() or (parent / "setup.cfg").exists():
            return parent
    return here.parents[1]


def _default_pack_root() -> Path:
    return _repo_root() / "language_packs" / "data" / "en_core_math_v1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise_surface(surface: str) -> str:
    return surface.lower().strip(_TRIM_PUNCTUATION)


def _reviewer_slug(reviewer: str) -> str:
    slug = _REVIEWER_RE.sub("_", reviewer.lower()).strip("_-")
    if not slug:
        raise RatificationError("reviewer must contain at least one safe character")
    return slug


def _read_entries(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record.get("lemma"), str):
            raise RatificationError(f"{path}: line {line_number} missing string lemma")
        if not isinstance(record.get("category"), str):
            raise RatificationError(f"{path}: line {line_number} missing string category")
        aliases = record.get("aliases", [])
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) for alias in aliases
        ):
            raise RatificationError(f"{path}: line {line_number} has invalid aliases")
        entries.append(record)
    return entries


def _write_entries(path: Path, entries: list[dict[str, object]]) -> None:
    ordered = sorted(entries, key=lambda item: str(item["lemma"]))
    lines = [json.dumps(entry, ensure_ascii=False, sort_keys=False) for entry in ordered]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _all_source_entries(pack_root: Path) -> list[dict[str, object]]:
    source_dir = pack_root / "lexicon"
    entries: list[dict[str, object]] = []
    for path in sorted(source_dir.glob("*.jsonl")):
        entries.extend(_read_entries(path))
    return entries


def _entry_surfaces(entry: dict[str, object]) -> set[str]:
    lemma = str(entry["lemma"]).lower()
    aliases = entry.get("aliases", [])
    return {lemma, *(str(alias).lower() for alias in aliases)}


def _find_frame_opener_conflict(pack_root: Path, lemma: str) -> tuple[str, str] | None:
    for entry in _all_source_entries(pack_root):
        category = str(entry["category"])
        if category not in _FRAME_OPENER_CATEGORIES:
            continue
        if lemma in _entry_surfaces(entry):
            return str(entry["lemma"]), category
    return None


def _stem_alias_parent(
    entries: list[dict[str, object]],
    lemma: str,
) -> dict[str, object] | None:
    for entry in entries:
        parent = str(entry["lemma"]).lower()
        if parent == lemma:
            return entry
        if lemma in _entry_surfaces(entry):
            return entry
        if lemma in {
            f"{parent}s",
            f"{parent}es",
            f"{parent}ed",
            f"{parent}ing",
        }:
            return entry
        if parent.endswith("y") and lemma == f"{parent[:-1]}ies":
            return entry
    return None


def _validate_evidence(claim: MathReaderRefusalEvidence) -> None:
    if claim.sub_type != "lexical":
        raise WrongClaimSubType(
            f"Lexical ratification requires sub_type='lexical'; got {claim.sub_type!r}"
        )
    recomputed = from_audit_row(
        claim.audit_row,
        claim.sub_type,
        claim_signature=claim.claim_signature,
    )
    if recomputed.evidence_hash != claim.evidence_hash:
        raise EvidenceTampering(
            "MathReaderRefusalEvidence hash does not match canonical audit row bytes"
        )


def apply_lexical_claim(
    *,
    claim: MathReaderRefusalEvidence,
    category: str,
    reviewer: str,
    pack_root: Path | None = None,
    ratifier_kind: str = "cli",
) -> RatificationReceipt:
    """Apply a reviewed lexical claim to a math source lexicon file.

    Preconditions:
    - ``claim.sub_type == "lexical"`` or :class:`WrongClaimSubType` is raised.
    - ``category`` is in :data:`SAFE_CATEGORIES`; frame-opener categories raise
      :class:`WrongZeroViolationCandidate`.
    - the target surface is not already a frame-opener lemma or alias.
    - ``claim.evidence_hash`` matches a recomputation from ``claim.audit_row``.

    The write target is ``{pack_root}/lexicon/{category}.jsonl``.  Entries are
    sorted alphabetically by lemma.  If the ratified surface is an inflectional
    match for an existing lemma (for example ``weight`` -> ``weights``), it is
    appended as an alias; otherwise a new lemma entry is written.

    The compiled ``lexicon.jsonl`` and ``manifest.json`` are intentionally not
    regenerated.  The loader verifies the manifest against compiled bytes but
    reads per-category source files for alias-aware entries.
    """
    _validate_evidence(claim)

    root = (pack_root if pack_root is not None else _default_pack_root()).resolve()
    source_dir = root / "lexicon"
    target_file = source_dir / f"{category}.jsonl"

    if category not in SAFE_CATEGORIES:
        if category in _FRAME_OPENER_CATEGORIES:
            raise WrongZeroViolationCandidate(
                f"category {category!r} can open reader frames; LexicalClaim "
                "ratification is restricted to drain-class categories"
            )
        if not target_file.exists():
            raise UnknownCategory(f"unknown math lexicon category: {category!r}")
        raise WrongZeroViolationCandidate(
            f"category {category!r} is outside SAFE_CATEGORIES={sorted(SAFE_CATEGORIES)!r}"
        )
    if not target_file.exists():
        raise UnknownCategory(f"missing source lexicon file for category: {category!r}")

    lemma = _normalise_surface(claim.audit_row.token_text)
    if not lemma:
        raise WrongZeroViolationCandidate("empty lexical surface cannot be ratified")

    conflict = _find_frame_opener_conflict(root, lemma)
    if conflict is not None:
        parent, conflict_category = conflict
        raise WrongZeroViolationCandidate(
            f"surface {lemma!r} already resolves through frame-opener "
            f"{conflict_category!r} lemma {parent!r}"
        )

    provenance = f"phase_2_reader_ratified_{_reviewer_slug(reviewer)}_{date.today().isoformat()}"
    before = _sha256_file(target_file)
    entries = _read_entries(target_file)
    target_relative = str(target_file.relative_to(_repo_root())) if target_file.is_relative_to(_repo_root()) else str(target_file)

    parent = _stem_alias_parent(entries, lemma)
    is_alias = False
    aliased_to: str | None = None

    if parent is not None:
        parent_lemma = str(parent["lemma"])
        aliases = [str(alias) for alias in parent.get("aliases", [])]
        surfaces = {parent_lemma.lower(), *(alias.lower() for alias in aliases)}
        if lemma in surfaces:
            raise AlreadyRatified(
                f"lexical claim {lemma!r} is already ratified in {category!r}"
            )
        aliases.append(lemma)
        parent["aliases"] = sorted(set(aliases))
        parent["ratifier_kind"] = ratifier_kind
        is_alias = True
        aliased_to = parent_lemma
    else:
        entries.append(
            {
                "lemma": lemma,
                "category": category,
                "aliases": [],
                "provenance": provenance,
                "ratifier_kind": ratifier_kind,
            }
        )

    _write_entries(target_file, entries)
    after = _sha256_file(target_file)

    return RatificationReceipt(
        target_file=target_relative,
        lemma=lemma,
        category=category,
        provenance=provenance,
        file_sha256_before=before,
        file_sha256_after=after,
        evidence_hash=claim.evidence_hash,
        is_alias=is_alias,
        aliased_to=aliased_to,
    )


__all__ = [
    "AlreadyRatified",
    "EvidenceTampering",
    "RatificationError",
    "RatificationReceipt",
    "SAFE_CATEGORIES",
    "UnknownCategory",
    "WrongClaimSubType",
    "WrongZeroViolationCandidate",
    "apply_lexical_claim",
]
