"""ADR-0169 — CompositionClaim ratification into reviewed math composition mappings.

This module is the explicit post-review mutation boundary for math-domain
composition-pattern evidence.  It edits only per-category source files
under ``language_packs/data/en_core_math_v1/compositions/``; it does not
regenerate the compiled lexicon and therefore does not rewrite the pack
manifest checksum.

Mirrors :mod:`teaching.math_frame_ratification` (F1) but lifts the safe
surface from bounded frame openers to allowlisted composition categories
over already-bound slot patterns (ADR-0169 §"Definition of a CompositionClaim").

Hard rules (ADR-0169 §"Decision"):

- ``SAFE_COMPOSITION_CATEGORIES`` is the only sanctioned surface — no other
  categories may be ratified through this handler.
- case 0050 hazard pin: after any composition ratification, GSM8K
  train-sample case 0050 must still refuse (no speculative pre-frame-filler
  admission).
- evidence pointers MUST carry ``source="math_audit"`` — never ``"corpus"``.
- ``polarity in {"affirms", "falsifies"}``; the falsifies branch records the
  pattern as non-composing and never appends an affirmative composition row.
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


# ---------------------------------------------------------------------------
# Allowlist + constants
# ---------------------------------------------------------------------------

SAFE_COMPOSITION_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "multiplicative_composition",
        "additive_composition",
        "subtractive_composition",
    }
)

_VALID_POLARITIES: Final[frozenset[str]] = frozenset({"affirms", "falsifies"})
_REVIEWER_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_-]+")
_TRIM_PUNCTUATION: Final[str] = string.punctuation


# ---------------------------------------------------------------------------
# Error hierarchy (mirror F1)
# ---------------------------------------------------------------------------


class RatificationError(ValueError):
    """Base class for composition ratification rejections."""


class WrongClaimSubType(RatificationError):
    """Raised when a non-composition evidence record reaches this handler."""


class WrongCompositionCategory(RatificationError):
    """Raised when ``composition_category`` is outside :data:`SAFE_COMPOSITION_CATEGORIES`.

    Per ADR-0169.1 §"Trip-wires" #8, this is the explicit allowlist-enforcement
    exception.  Distinct from :class:`WrongZeroViolationCandidate` to give
    operators a clearer remediation signal (the category is the problem; the
    claim shape itself may be fine).
    """


class WrongZeroViolationCandidate(RatificationError):
    """Raised when a ratification could open a wrong>0 admission path."""


class AlreadyRatified(RatificationError):
    """Raised when the target claim is already covered by the source file."""


class EvidenceTampering(RatificationError):
    """Raised when the evidence hash no longer matches canonical bytes."""


class UnknownCategory(RatificationError):
    """Raised when the requested category is not a known composition source."""


class InvalidPolarity(RatificationError):
    """Raised when polarity is not in :data:`_VALID_POLARITIES`."""


class EvidenceLaundering(RatificationError):
    """Raised when audit evidence is presented as cognition corpus evidence.

    ADR-0169.1 §"Evidence floor": math-audit evidence must never be
    serialised with ``source="corpus"``; that would impersonate ADR-0057's
    cognition corpus evidence floor.
    """


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompositionRatificationReceipt:
    target_file: str
    surface_pattern: str
    composition_category: str
    polarity: str
    provenance: str
    file_sha256_before: str
    file_sha256_after: str
    evidence_hash: str
    is_duplicate_evidence: bool


# ---------------------------------------------------------------------------
# Path / file helpers
# ---------------------------------------------------------------------------


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
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record.get("surface_pattern"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string surface_pattern"
            )
        if not isinstance(record.get("composition_category"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string composition_category"
            )
        if not isinstance(record.get("polarity"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string polarity"
            )
        entries.append(record)
    return entries


def _write_entries(path: Path, entries: list[dict[str, object]]) -> None:
    ordered = sorted(entries, key=lambda item: str(item["surface_pattern"]))
    lines = [
        json.dumps(entry, ensure_ascii=False, sort_keys=False) for entry in ordered
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------


def _validate_evidence(claim: MathReaderRefusalEvidence) -> None:
    """Verify sub_type and tamper-resistance of evidence record."""
    if claim.sub_type != "composition":
        raise WrongClaimSubType(
            f"Composition ratification requires sub_type='composition'; got {claim.sub_type!r}"
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


def _check_no_corpus_laundering(evidence_source: str) -> None:
    """ADR-0169.1 §'Evidence floor' — audit evidence must declare math_audit.

    Fail loudly if a caller hands us an evidence pointer that claims to be
    cognition corpus evidence; that would impersonate the ADR-0057 floor.
    """
    if evidence_source == "corpus":
        raise EvidenceLaundering(
            "audit evidence MUST NOT be laundered as source='corpus'; "
            "use source='math_audit' (ADR-0169.1 §'Evidence floor')"
        )


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def apply_composition_claim(
    *,
    claim: MathReaderRefusalEvidence,
    composition_category: str,
    polarity: str,
    reviewer: str,
    surface_pattern: str | None = None,
    pack_root: Path | None = None,
    evidence_source: str = "math_audit",
) -> CompositionRatificationReceipt:
    """Apply a reviewed composition claim to a math composition source file.

    Preconditions:

    - ``claim.sub_type == "composition"`` (F1 analog of LexicalClaim sub_type pin).
    - ``composition_category`` ∈ :data:`SAFE_COMPOSITION_CATEGORIES`.
    - ``polarity`` ∈ ``{"affirms", "falsifies"}``.
    - ``evidence_source == "math_audit"``; ``"corpus"`` raises
      :class:`EvidenceLaundering` per ADR-0169.1.
    - ``claim.evidence_hash`` matches a recomputation from ``claim.audit_row``.

    The write target is
    ``{pack_root}/compositions/{composition_category}.jsonl``.  Entries are
    sorted alphabetically by ``surface_pattern``.  Each entry records
    ``(surface_pattern, composition_category, polarity, provenance,
    evidence_hashes)`` so the polarity decision is auditable and
    falsification can supersede an earlier affirmation only through an
    explicit reviewed re-apply.

    ``surface_pattern`` defaults to the normalized audit-row token when not
    supplied — useful for tests and minimal first ratifications.  Production
    callers should pass an explicit bound-slot pattern (see ADR-0169
    §"Definition of a CompositionClaim").

    The compiled ``lexicon.jsonl`` and ``manifest.json`` are intentionally
    not regenerated.
    """
    # Trust-boundary checks (ADR-0169.1 §'Evidence floor' before any I/O).
    _check_no_corpus_laundering(evidence_source)
    if evidence_source != "math_audit":
        raise EvidenceLaundering(
            f"evidence_source must be 'math_audit'; got {evidence_source!r}"
        )

    if polarity not in _VALID_POLARITIES:
        raise InvalidPolarity(
            f"polarity must be one of {sorted(_VALID_POLARITIES)!r}; got {polarity!r}"
        )

    _validate_evidence(claim)

    if composition_category not in SAFE_COMPOSITION_CATEGORIES:
        raise WrongCompositionCategory(
            f"composition_category {composition_category!r} is outside SAFE_COMPOSITION_CATEGORIES="
            f"{sorted(SAFE_COMPOSITION_CATEGORIES)!r}; "
            "CompositionClaim ratification is allowlist-only (ADR-0169 §'Initial safe category scope')"
        )

    root = (pack_root if pack_root is not None else _default_pack_root()).resolve()
    source_dir = root / "compositions"
    if not source_dir.exists():
        raise UnknownCategory(
            f"composition source directory does not exist: {source_dir}; "
            "CompositionClaim handler requires a reviewed compositions/ tree"
        )

    target_file = source_dir / f"{composition_category}.jsonl"
    if not target_file.exists():
        # Initialise as empty source file rather than fail — the .gitkeep
        # scaffold guarantees the parent directory; first ratification for a
        # never-seen safe category seeds the file deterministically.
        target_file.write_text("", encoding="utf-8")

    if surface_pattern is None:
        normalized_pattern = _normalise_surface(claim.audit_row.token_text)
    else:
        normalized_pattern = surface_pattern.lower().strip()
    if not normalized_pattern:
        raise WrongZeroViolationCandidate(
            "empty composition surface_pattern cannot be ratified"
        )

    provenance = (
        f"adr_0169_composition_ratified_{_reviewer_slug(reviewer)}_"
        f"{date.today().isoformat()}"
    )
    before = _sha256_file(target_file)
    entries = _read_entries(target_file)
    target_relative = (
        str(target_file.relative_to(_repo_root()))
        if target_file.is_relative_to(_repo_root())
        else str(target_file)
    )

    # Idempotency: identical (surface_pattern, composition_category, polarity,
    # evidence_hash) is a no-op AlreadyRatified.  Evidence-hash-only
    # duplication (same claim ratified for a second time by *different*
    # evidence) appends evidence per ADR-0169.1 §"Idempotency" path #1.
    matching = [
        e
        for e in entries
        if str(e["surface_pattern"]) == normalized_pattern
        and str(e["composition_category"]) == composition_category
        and str(e["polarity"]) == polarity
    ]
    is_duplicate_evidence = False
    if matching:
        existing = matching[0]
        existing_evidence: list[str] = list(existing.get("evidence_hashes", []))  # type: ignore[arg-type]
        if claim.evidence_hash in existing_evidence:
            raise AlreadyRatified(
                f"composition claim ({normalized_pattern!r}, {composition_category!r}, "
                f"{polarity!r}) is already ratified by evidence_hash={claim.evidence_hash}"
            )
        existing_evidence.append(claim.evidence_hash)
        existing["evidence_hashes"] = sorted(set(existing_evidence))
        is_duplicate_evidence = True
    else:
        entries.append(
            {
                "surface_pattern": normalized_pattern,
                "composition_category": composition_category,
                "polarity": polarity,
                "provenance": provenance,
                "evidence_hashes": [claim.evidence_hash],
            }
        )

    _write_entries(target_file, entries)
    after = _sha256_file(target_file)

    # RAT-1 — close the ratify→runtime gap: regenerate the compiled
    # composition artifact and update the pack manifest's
    # composition_checksum so the next runtime turn loads the new entry.
    # Idempotent; identical source → identical compiled bytes.
    from language_packs.compile_pack import compile_pack
    compile_pack(root)

    return CompositionRatificationReceipt(
        target_file=target_relative,
        surface_pattern=normalized_pattern,
        composition_category=composition_category,
        polarity=polarity,
        provenance=provenance,
        file_sha256_before=before,
        file_sha256_after=after,
        evidence_hash=claim.evidence_hash,
        is_duplicate_evidence=is_duplicate_evidence,
    )


__all__ = [
    "AlreadyRatified",
    "CompositionRatificationReceipt",
    "EvidenceLaundering",
    "EvidenceTampering",
    "InvalidPolarity",
    "RatificationError",
    "SAFE_COMPOSITION_CATEGORIES",
    "UnknownCategory",
    "WrongClaimSubType",
    "WrongCompositionCategory",
    "WrongZeroViolationCandidate",
    "apply_composition_claim",
]
