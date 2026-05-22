"""Reviewer Registry v1 loader and validator (ADR-0092).

Parses ``docs/reviewers.yaml`` into a typed, immutable :class:`ReviewerRegistry`.
Schema rejection is loud: unknown keys, malformed entries, duplicate ids, and
out-of-scope wildcards all raise :class:`ReviewerRegistryError`.

The registry is consulted by the Domain Pack Contract v1 validator
(ADR-0093) to enforce ADR-0091 predicate #8 (reviewer resolution).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"schema_version", "reviewers", "expert_demo_claims"}
)
ALLOWED_REVIEWER_KEYS: frozenset[str] = frozenset(
    {"reviewer_id", "display_name", "role", "domains", "review_scope", "provenance"}
)
ALLOWED_EXPERT_DEMO_CLAIM_KEYS: frozenset[str] = frozenset(
    {
        "domain_id",
        "evidence_lanes",
        "evidence_revision",
        "signed_by",
        "claim_digest",
    }
)
ALLOWED_ROLES: frozenset[str] = frozenset({"primary", "domain"})
ALLOWED_SCOPES: frozenset[str] = frozenset({"pack", "proposal", "chain", "eval"})
SCHEMA_VERSION: int = 1
WILDCARD_DOMAIN: str = "*"


class ReviewerRegistryError(ValueError):
    """Raised when ``docs/reviewers.yaml`` fails ADR-0092 v1 schema validation."""


@dataclass(frozen=True, slots=True)
class Reviewer:
    reviewer_id: str
    display_name: str
    role: str
    domains: tuple[str, ...]
    review_scope: tuple[str, ...]
    provenance: str


@dataclass(frozen=True, slots=True)
class ExpertDemoClaim:
    """Reviewer-signed expert-demo promotion claim (ADR-0106).

    A row in ``expert_demo_claims`` asserts that ``signed_by`` has
    inspected the evidence at ``evidence_revision`` for ``domain_id``
    across ``evidence_lanes`` and that the canonical evidence-bundle
    SHA-256 equals ``claim_digest``. The reporting layer re-derives the
    digest from the lane results on disk; a mismatch demotes the row
    back to ``reasoning-capable``.
    """

    domain_id: str
    evidence_lanes: tuple[str, ...]
    evidence_revision: str
    signed_by: str
    claim_digest: str


@dataclass(frozen=True, slots=True)
class ReviewerRegistry:
    schema_version: int
    reviewers: tuple[Reviewer, ...]
    expert_demo_claims: tuple[ExpertDemoClaim, ...] = ()

    def expert_demo_claim_for(self, domain_id: str) -> ExpertDemoClaim | None:
        for claim in self.expert_demo_claims:
            if claim.domain_id == domain_id:
                return claim
        return None

    def resolve(self, reviewer_id: str) -> Reviewer | None:
        for reviewer in self.reviewers:
            if reviewer.reviewer_id == reviewer_id:
                return reviewer
        return None

    def can_review(self, reviewer_id: str, *, domain_id: str, scope: str) -> bool:
        """Return True iff this reviewer may ratify ``scope`` artifacts for ``domain_id``.

        Implements ADR-0091 predicate #8 plus ADR-0092 rules 2, 3, and 4:
        - rule 2: unknown ``reviewer_id`` → False
        - rule 3: ``role: domain`` reviewer whose ``domains`` do not include
          ``domain_id`` → False
        - rule 4: reviewer whose ``review_scope`` does not cover ``scope`` → False
        """
        reviewer = self.resolve(reviewer_id)
        if reviewer is None:
            return False
        if scope not in reviewer.review_scope:
            return False
        if reviewer.role == "primary":
            return True
        return domain_id in reviewer.domains


def load_reviewer_registry(path: Path) -> ReviewerRegistry:
    """Parse ``path`` as a Reviewer Registry v1 file.

    Raises :class:`ReviewerRegistryError` on any schema violation. No
    side effects beyond reading ``path``.
    """
    if not path.exists():
        raise ReviewerRegistryError(f"reviewer registry not found at {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReviewerRegistryError(f"reviewer registry YAML parse error: {exc}") from exc

    if not isinstance(raw, Mapping):
        raise ReviewerRegistryError("reviewer registry root must be a mapping")

    unknown_top = set(raw.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if unknown_top:
        raise ReviewerRegistryError(
            f"reviewer registry has unknown top-level keys: {sorted(unknown_top)}"
        )

    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ReviewerRegistryError(
            f"reviewer registry schema_version must be {SCHEMA_VERSION}; got {schema_version!r}"
        )

    reviewers_raw = raw.get("reviewers")
    if reviewers_raw is None:
        raise ReviewerRegistryError("reviewer registry missing 'reviewers' field")
    if not isinstance(reviewers_raw, list):
        raise ReviewerRegistryError("reviewer registry 'reviewers' must be a list")

    parsed: list[Reviewer] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(reviewers_raw):
        reviewer = _parse_reviewer(entry, index=index)
        if reviewer.reviewer_id in seen_ids:
            raise ReviewerRegistryError(
                f"reviewer registry contains duplicate reviewer_id {reviewer.reviewer_id!r}"
            )
        seen_ids.add(reviewer.reviewer_id)
        parsed.append(reviewer)

    claims_raw = raw.get("expert_demo_claims", [])
    if not isinstance(claims_raw, list):
        raise ReviewerRegistryError(
            "reviewer registry 'expert_demo_claims' must be a list when present"
        )
    parsed_claims: list[ExpertDemoClaim] = []
    seen_domains: set[str] = set()
    reviewer_ids = {reviewer.reviewer_id for reviewer in parsed}
    for index, entry in enumerate(claims_raw):
        claim = _parse_expert_demo_claim(entry, index=index, reviewer_ids=reviewer_ids)
        if claim.domain_id in seen_domains:
            raise ReviewerRegistryError(
                f"expert_demo_claims contains duplicate domain_id "
                f"{claim.domain_id!r}"
            )
        seen_domains.add(claim.domain_id)
        parsed_claims.append(claim)

    return ReviewerRegistry(
        schema_version=SCHEMA_VERSION,
        reviewers=tuple(parsed),
        expert_demo_claims=tuple(parsed_claims),
    )


def _parse_expert_demo_claim(
    entry: Any, *, index: int, reviewer_ids: set[str]
) -> ExpertDemoClaim:
    if not isinstance(entry, Mapping):
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} must be a mapping"
        )
    unknown = set(entry.keys()) - ALLOWED_EXPERT_DEMO_CLAIM_KEYS
    if unknown:
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} has unknown fields: "
            f"{sorted(unknown)}"
        )
    missing = ALLOWED_EXPERT_DEMO_CLAIM_KEYS - set(entry.keys())
    if missing:
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} missing required "
            f"fields: {sorted(missing)}"
        )
    domain_id = _require_nonempty_str(
        entry["domain_id"], field="domain_id", index=index
    )
    evidence_revision = _require_nonempty_str(
        entry["evidence_revision"], field="evidence_revision", index=index
    )
    signed_by = _require_nonempty_str(
        entry["signed_by"], field="signed_by", index=index
    )
    claim_digest = _require_nonempty_str(
        entry["claim_digest"], field="claim_digest", index=index
    )
    if signed_by not in reviewer_ids:
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} signed_by "
            f"{signed_by!r} does not resolve to a registered reviewer"
        )
    if len(claim_digest) != 64 or any(
        c not in "0123456789abcdef" for c in claim_digest
    ):
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} claim_digest must be "
            "a lowercase 64-char SHA-256 hex string"
        )
    evidence_lanes = _require_str_list(
        entry["evidence_lanes"], field="evidence_lanes", index=index
    )
    if not evidence_lanes:
        raise ReviewerRegistryError(
            f"expert_demo_claims entry at index {index} has empty "
            "'evidence_lanes' list"
        )
    return ExpertDemoClaim(
        domain_id=domain_id,
        evidence_lanes=evidence_lanes,
        evidence_revision=evidence_revision,
        signed_by=signed_by,
        claim_digest=claim_digest,
    )


def _parse_reviewer(entry: Any, *, index: int) -> Reviewer:
    if not isinstance(entry, Mapping):
        raise ReviewerRegistryError(f"reviewer entry at index {index} must be a mapping")

    unknown = set(entry.keys()) - ALLOWED_REVIEWER_KEYS
    if unknown:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has unknown fields: {sorted(unknown)}"
        )

    missing = ALLOWED_REVIEWER_KEYS - set(entry.keys())
    if missing:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} missing required fields: {sorted(missing)}"
        )

    reviewer_id = _require_nonempty_str(entry["reviewer_id"], field="reviewer_id", index=index)
    display_name = _require_nonempty_str(entry["display_name"], field="display_name", index=index)
    role = _require_nonempty_str(entry["role"], field="role", index=index)
    provenance = _require_nonempty_str(entry["provenance"], field="provenance", index=index)

    if role not in ALLOWED_ROLES:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has invalid role {role!r}; "
            f"must be one of {sorted(ALLOWED_ROLES)}"
        )

    domains = _require_str_list(entry["domains"], field="domains", index=index)
    if not domains:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has empty 'domains' list"
        )
    if role == "domain" and WILDCARD_DOMAIN in domains:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has role='domain' but claims wildcard "
            f"'{WILDCARD_DOMAIN}'; only role='primary' may claim wildcard domains"
        )
    if role == "primary" and domains != (WILDCARD_DOMAIN,):
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has role='primary' but domains "
            f"is not exactly [{WILDCARD_DOMAIN!r}]; primary reviewers must claim wildcard"
        )

    review_scope = _require_str_list(entry["review_scope"], field="review_scope", index=index)
    if not review_scope:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has empty 'review_scope' list"
        )
    unknown_scopes = set(review_scope) - ALLOWED_SCOPES
    if unknown_scopes:
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} has unknown review_scope values: "
            f"{sorted(unknown_scopes)}; allowed: {sorted(ALLOWED_SCOPES)}"
        )

    return Reviewer(
        reviewer_id=reviewer_id,
        display_name=display_name,
        role=role,
        domains=domains,
        review_scope=review_scope,
        provenance=provenance,
    )


def _require_nonempty_str(value: Any, *, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} field {field!r} must be a non-empty string"
        )
    return value


def _require_str_list(value: Any, *, field: str, index: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ReviewerRegistryError(
            f"reviewer entry at index {index} field {field!r} must be a list of strings"
        )
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ReviewerRegistryError(
                f"reviewer entry at index {index} field {field!r} contains a "
                "non-string or empty value"
            )
    return tuple(value)
