"""Sealed :class:`ProposalSource` provenance type (ADR-0094/ADR-0104/ADR-0080).

Widens :class:`teaching.proposals.TeachingChainProposal` and
:class:`teaching.store.PackMutationProposal` with a typed source field.
Operator and miner provenance landed in ADR-0094/ADR-0095; curriculum
source activation is governed by ADR-0104. ADR-0080 activates the
reserved contemplation source kind for read-only, SPECULATIVE findings.

The kind field is a sealed :data:`ProposalKind` literal. Adding a new
kind requires a new ADR adding a branch to every consumer.

Consumers must branch on :attr:`ProposalSource.kind` using exhaustive
``match`` statements ended by
:func:`typing.assert_never`. The pattern is::

    match proposal.source.kind:
        case "operator":
            ...
        case "miner":
            ...
        case "curriculum":
            ...
        case "contemplation":
            ...
        case "exemplar_corpus":
            ...
        case _:  # pragma: no cover - exhaustiveness
            assert_never(proposal.source.kind)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, get_args


ProposalKind = Literal[
    "operator", "miner", "curriculum", "contemplation", "exemplar_corpus"
]
ALLOWED_KINDS: frozenset[str] = frozenset(get_args(ProposalKind))


class ProposalSourceError(ValueError):
    """Raised when a proposal source value violates ADR-0094 v1 schema."""


@dataclass(frozen=True, slots=True)
class ProposalSource:
    """Typed provenance for one proposal.

    :param kind:
        One of ``"operator"``, ``"miner"``, ``"curriculum"``, or
        ``"contemplation"``. The set is sealed; adding a new kind
        requires a new ADR.
    :param source_id:
        Empty for ``kind="operator"``. For other kinds, the originating
        miner id or curriculum course id.
    :param emitted_at_revision:
        Git SHA at emission time. Pinned per proposal so replays can
        anchor against the substrate state the proposal was derived
        from.
    """

    kind: ProposalKind
    source_id: str
    emitted_at_revision: str

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_KINDS:
            raise ProposalSourceError(
                f"ProposalSource.kind must be one of {sorted(ALLOWED_KINDS)}; "
                f"got {self.kind!r}"
            )
        if self.kind == "operator" and self.source_id:
            raise ProposalSourceError(
                "ProposalSource.kind='operator' requires empty source_id; "
                f"got {self.source_id!r}"
            )
        if self.kind != "operator" and not self.source_id:
            raise ProposalSourceError(
                f"ProposalSource.kind={self.kind!r} requires non-empty source_id"
            )
        if not self.emitted_at_revision:
            raise ProposalSourceError(
                "ProposalSource.emitted_at_revision must be non-empty"
            )

    def serialize(self) -> str:
        """Compact human-readable form for logs and telemetry.

        - ``ProposalSource("operator", "", "<sha>")`` -> ``"operator"``
        - ``ProposalSource("miner", "articulation_quality", "<sha>")``
          -> ``"miner:articulation_quality"``
        - ``ProposalSource("curriculum", "math_logic_v1", "<sha>")``
          -> ``"curriculum:math_logic_v1"``
        - ``ProposalSource("contemplation", "frontier_compare", "<sha>")``
          -> ``"contemplation:frontier_compare"``
        """
        if not self.source_id:
            return self.kind
        return f"{self.kind}:{self.source_id}"

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "source_id": self.source_id,
            "emitted_at_revision": self.emitted_at_revision,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "ProposalSource":
        """Parse a serialized source. Raises on missing or unknown fields.

        Accepts ``Any`` because callers typically pass dicts loaded from
        untrusted JSONL where static typing cannot guarantee shape.
        """
        if not isinstance(payload, Mapping):
            raise ProposalSourceError(
                f"ProposalSource payload must be a mapping; got {type(payload).__name__}"
            )
        allowed = {"kind", "source_id", "emitted_at_revision"}
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ProposalSourceError(
                f"ProposalSource payload has unknown fields: {sorted(unknown)}"
            )
        missing = allowed - set(payload.keys())
        if missing:
            raise ProposalSourceError(
                f"ProposalSource payload missing required fields: {sorted(missing)}"
            )
        return cls(
            kind=payload["kind"],
            source_id=payload["source_id"],
            emitted_at_revision=payload["emitted_at_revision"],
        )

    @classmethod
    def operator(cls, *, emitted_at_revision: str) -> "ProposalSource":
        """Convenience constructor for the default operator-authored case."""
        return cls(kind="operator", source_id="", emitted_at_revision=emitted_at_revision)
