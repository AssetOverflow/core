"""ADR-0168 — FrameClaim ratification into reviewed math frame mappings.

This module is the explicit post-review mutation boundary for math-domain
frame-opener evidence.  It edits only per-category source files under
``language_packs/data/en_core_math_v1/frames/``; it does not regenerate the
compiled lexicon and therefore does not rewrite the pack manifest checksum.

Mirrors :mod:`teaching.math_lexical_ratification` (W2-D) but lifts the safe
surface from drain-class lexical entries to allowlisted frame categories.

Hard rules (ADR-0168 §"Decision"):

- ``SAFE_FRAME_CATEGORIES`` is the only sanctioned surface — no other
  categories may be ratified through this handler.
- case 0050 hazard pin: after any frame ratification, GSM8K train-sample
  case 0050 must still refuse (no speculative pre-frame-filler admission).
- evidence pointers MUST carry ``source="math_audit"`` — never ``"corpus"``.
- ``polarity in {"affirms", "falsifies"}``; the falsifies branch records the
  surface as a non-opener and never appends an opener lemma.
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

SAFE_FRAME_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "increment_frame",
        "decrement_frame",
        "transfer_frame",
        "remainder_frame",
    }
)

_VALID_POLARITIES: Final[frozenset[str]] = frozenset({"affirms", "falsifies"})
_REVIEWER_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_-]+")
_TRIM_PUNCTUATION: Final[str] = string.punctuation


# ---------------------------------------------------------------------------
# Error hierarchy (mirror W2-D)
# ---------------------------------------------------------------------------


class RatificationError(ValueError):
    """Base class for frame ratification rejections."""


class WrongClaimSubType(RatificationError):
    """Raised when a non-frame evidence record reaches this handler."""


class WrongZeroViolationCandidate(RatificationError):
    """Raised when a ratification could open a wrong>0 admission path."""


class AlreadyRatified(RatificationError):
    """Raised when the target surface is already covered by the source file."""


class EvidenceTampering(RatificationError):
    """Raised when the evidence hash no longer matches canonical bytes."""


class UnknownCategory(RatificationError):
    """Raised when the requested category is not a known frame source."""


class InvalidPolarity(RatificationError):
    """Raised when polarity is not in :data:`_VALID_POLARITIES`."""


class EvidenceLaundering(RatificationError):
    """Raised when audit evidence is presented as cognition corpus evidence.

    ADR-0168.1 §"Evidence floor": math-audit evidence must never be
    serialised with ``source="corpus"``; that would impersonate ADR-0057's
    cognition corpus evidence floor.
    """


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrameRatificationReceipt:
    target_file: str
    surface_form: str
    frame_category: str
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
        if not isinstance(record.get("surface_form"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string surface_form"
            )
        if not isinstance(record.get("frame_category"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string frame_category"
            )
        if not isinstance(record.get("polarity"), str):
            raise RatificationError(
                f"{path}: line {line_number} missing string polarity"
            )
        entries.append(record)
    return entries


def _write_entries(path: Path, entries: list[dict[str, object]]) -> None:
    ordered = sorted(entries, key=lambda item: str(item["surface_form"]))
    lines = [
        json.dumps(entry, ensure_ascii=False, sort_keys=False) for entry in ordered
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------


def _validate_evidence(claim: MathReaderRefusalEvidence) -> None:
    """Verify sub_type and tamper-resistance of evidence record."""
    if claim.sub_type != "frame":
        raise WrongClaimSubType(
            f"Frame ratification requires sub_type='frame'; got {claim.sub_type!r}"
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
    """ADR-0168.1 §'Evidence floor' — audit evidence must declare math_audit.

    Fail loudly if a caller hands us an evidence pointer that claims to be
    cognition corpus evidence; that would impersonate the ADR-0057 floor.
    """
    if evidence_source == "corpus":
        raise EvidenceLaundering(
            "audit evidence MUST NOT be laundered as source='corpus'; "
            "use source='math_audit' (ADR-0168.1 §'Evidence floor')"
        )


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def apply_frame_claim(
    *,
    claim: MathReaderRefusalEvidence,
    frame_category: str,
    polarity: str,
    reviewer: str,
    pack_root: Path | None = None,
    evidence_source: str = "math_audit",
) -> FrameRatificationReceipt:
    """Apply a reviewed frame claim to a math frame source file.

    Preconditions:

    - ``claim.sub_type == "frame"`` (W2-D analog of LexicalClaim sub_type pin).
    - ``frame_category`` ∈ :data:`SAFE_FRAME_CATEGORIES`.
    - ``polarity`` ∈ ``{"affirms", "falsifies"}``.
    - ``evidence_source == "math_audit"``; ``"corpus"`` raises
      :class:`EvidenceLaundering` per ADR-0168.1.
    - ``claim.evidence_hash`` matches a recomputation from ``claim.audit_row``.

    The write target is ``{pack_root}/frames/{frame_category}.jsonl``.
    Entries are sorted alphabetically by ``surface_form``.  Each entry
    records ``(surface_form, frame_category, polarity, provenance,
    evidence_hash)`` so the polarity decision is auditable and
    falsification can supersede an earlier affirmation only through an
    explicit reviewed re-apply.

    The compiled ``lexicon.jsonl`` and ``manifest.json`` are intentionally
    not regenerated.
    """
    # Trust-boundary checks (ADR-0168.1 §'Evidence floor' before any I/O).
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

    if frame_category not in SAFE_FRAME_CATEGORIES:
        raise WrongZeroViolationCandidate(
            f"frame_category {frame_category!r} is outside SAFE_FRAME_CATEGORIES="
            f"{sorted(SAFE_FRAME_CATEGORIES)!r}; FrameClaim ratification is allowlist-only"
        )

    root = (pack_root if pack_root is not None else _default_pack_root()).resolve()
    source_dir = root / "frames"
    if not source_dir.exists():
        raise UnknownCategory(
            f"frame source directory does not exist: {source_dir}; "
            "FrameClaim handler requires a reviewed frames/ tree"
        )

    target_file = source_dir / f"{frame_category}.jsonl"
    if not target_file.exists():
        # Initialise as empty source file rather than fail — the .gitkeep
        # scaffold guarantees the parent directory; first ratification for a
        # never-seen safe category seeds the file deterministically.
        target_file.write_text("", encoding="utf-8")

    surface_form = _normalise_surface(claim.audit_row.token_text)
    if not surface_form:
        raise WrongZeroViolationCandidate(
            "empty frame surface cannot be ratified"
        )

    provenance = (
        f"adr_0168_frame_ratified_{_reviewer_slug(reviewer)}_"
        f"{date.today().isoformat()}"
    )
    before = _sha256_file(target_file)
    entries = _read_entries(target_file)
    target_relative = (
        str(target_file.relative_to(_repo_root()))
        if target_file.is_relative_to(_repo_root())
        else str(target_file)
    )

    # Idempotency: identical (surface_form, frame_category, polarity,
    # evidence_hash) is a no-op AlreadyRatified.  Evidence-hash-only
    # duplication (same surface ratified for a second time by *different*
    # evidence) appends evidence per ADR-0168.1 §"Idempotency" path #1.
    matching = [
        e
        for e in entries
        if str(e["surface_form"]) == surface_form
        and str(e["frame_category"]) == frame_category
        and str(e["polarity"]) == polarity
    ]
    is_duplicate_evidence = False
    if matching:
        existing = matching[0]
        existing_evidence: list[str] = list(existing.get("evidence_hashes", []))  # type: ignore[arg-type]
        if claim.evidence_hash in existing_evidence:
            raise AlreadyRatified(
                f"frame claim ({surface_form!r}, {frame_category!r}, {polarity!r}) "
                f"is already ratified by evidence_hash={claim.evidence_hash}"
            )
        existing_evidence.append(claim.evidence_hash)
        existing["evidence_hashes"] = sorted(set(existing_evidence))
        is_duplicate_evidence = True
    else:
        entries.append(
            {
                "surface_form": surface_form,
                "frame_category": frame_category,
                "polarity": polarity,
                "provenance": provenance,
                "evidence_hashes": [claim.evidence_hash],
            }
        )

    _write_entries(target_file, entries)
    after = _sha256_file(target_file)

    return FrameRatificationReceipt(
        target_file=target_relative,
        surface_form=surface_form,
        frame_category=frame_category,
        polarity=polarity,
        provenance=provenance,
        file_sha256_before=before,
        file_sha256_after=after,
        evidence_hash=claim.evidence_hash,
        is_duplicate_evidence=is_duplicate_evidence,
    )


__all__ = [
    "AlreadyRatified",
    "EvidenceLaundering",
    "EvidenceTampering",
    "FrameRatificationReceipt",
    "InvalidPolarity",
    "RatificationError",
    "SAFE_FRAME_CATEGORIES",
    "UnknownCategory",
    "WrongClaimSubType",
    "WrongZeroViolationCandidate",
    "apply_frame_claim",
]
