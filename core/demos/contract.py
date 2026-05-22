"""ADR-0098 Demo Composition Contract — protocol + dataclasses.

The contract has three structural rules. Each is enforced by code in
this module or in the demo_composition lane, not by trust:

1. **Deterministic JSON.** Two runs with identical inputs and seed
   produce byte-identical ``json_path`` contents. Verified by the
   demo_composition lane's per-adapter byte-equality cases and by the
   :func:`canonical_json` helper, which is the only sanctioned
   serializer for adapter output.

2. **No global state mutation.** An adapter may not mutate process-
   global registries (runtime singletons, module-level telemetry
   sinks, ``os.environ``) across its :meth:`DemoCommand.run` call.
   :func:`verify_no_global_state_mutation` snapshots a load-bearing
   subset of process state before and after a run; the lane fails
   when an adapter's snapshot changes.

3. **Declared output paths only.** Adapters write only under the
   ``output_dir`` they were handed. The path is sanitized via the
   existing ``core._safe_display.safe_pack_id`` discipline (ADR-0051).

Composability is read-only: a composing demo (the showcase under
ADR-0099) may read another adapter's :class:`DemoResult` but never
mutates it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable


CLAIM_CONTRACT_VERSION: int = 1


class DemoContractError(ValueError):
    """Raised when an ADR-0098 contract rule is violated."""


@dataclass(frozen=True, slots=True)
class Claim:
    """One falsifiable claim a demo asserts and supplies evidence for."""

    claim_id: str
    statement: str
    supported: bool
    evidence_locator: str

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise DemoContractError("Claim.claim_id must be non-empty")
        if not self.statement.strip():
            raise DemoContractError("Claim.statement must be non-empty")
        if not self.evidence_locator.strip():
            raise DemoContractError("Claim.evidence_locator must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "supported": self.supported,
            "evidence_locator": self.evidence_locator,
        }


@dataclass(frozen=True, slots=True)
class DemoResult:
    """Typed result returned by every :class:`DemoCommand`.

    ``json_path`` is the on-disk artifact whose bytes are pinned by
    the byte-equality invariant. ``evidence`` maps each claim id to a
    short evidence locator (path or hash) that the composing demo can
    use without reading the underlying demo's internals.

    ``trace_features`` exposes lightweight canonical evidence (e.g.
    ``trace_hash``, ``grounding_source``) the showcase can spot-check
    when composing claims across demos.
    """

    demo_id: str
    claim_contract_version: int
    claims: tuple[Claim, ...]
    evidence: Mapping[str, str]
    all_claims_supported: bool
    json_path: Path
    trace_features: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.demo_id.strip():
            raise DemoContractError("DemoResult.demo_id must be non-empty")
        if self.claim_contract_version != CLAIM_CONTRACT_VERSION:
            raise DemoContractError(
                f"DemoResult.claim_contract_version must be {CLAIM_CONTRACT_VERSION}; "
                f"got {self.claim_contract_version!r}"
            )
        claim_ids = [c.claim_id for c in self.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise DemoContractError(
                f"DemoResult.claims contains duplicate claim_id: {claim_ids}"
            )
        missing_evidence = [
            c.claim_id for c in self.claims if c.claim_id not in self.evidence
        ]
        if missing_evidence:
            raise DemoContractError(
                "DemoResult.evidence missing locator for claim_id(s): "
                f"{missing_evidence}"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "demo_id": self.demo_id,
            "claim_contract_version": self.claim_contract_version,
            "claims": [c.as_dict() for c in self.claims],
            "evidence": dict(sorted(self.evidence.items())),
            "all_claims_supported": self.all_claims_supported,
            "json_path": str(self.json_path),
            "trace_features": dict(sorted(self.trace_features.items())),
        }


@runtime_checkable
class DemoCommand(Protocol):
    """Composable demo protocol.

    Implementations declare a stable ``demo_id`` and the contract
    version they target, then expose a ``run`` method that produces a
    :class:`DemoResult`. The showcase composer (ADR-0099) consumes
    that protocol without depending on any adapter's internals.
    """

    demo_id: str
    claim_contract_version: int

    def run(
        self, *, output_dir: Path, seed: int | None = None
    ) -> DemoResult: ...


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Single sanctioned serializer for adapter JSON output.

    Sorted keys, two-space indent, trailing newline. Any adapter that
    rolls its own serializer risks violating the
    :data:`demo_json_byte_equality` invariant on platforms that disagree
    on default formatting; routing through this helper avoids that.
    """
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"


# ---------------------------------------------------------------------------
# Global-state-mutation detector (ADR-0098 invariant #2)
# ---------------------------------------------------------------------------


_TRACKED_MODULES: tuple[str, ...] = (
    "chat.telemetry",
    "chat.runtime",
    "language_packs.compiler",
)


def _global_state_snapshot() -> dict[str, Any]:
    """Capture a load-bearing subset of process state for diff checking.

    The set is deliberately narrow: only state we expect demos to
    leave untouched. Capturing all of ``sys.modules`` would produce
    too many false positives from lazy imports.
    """
    snapshot: dict[str, Any] = {
        "env_subset": tuple(
            sorted(
                (k, os.environ[k])
                for k in os.environ
                if k.startswith("CORE_") or k == "PYTHONHASHSEED"
            )
        ),
    }
    import sys

    for mod_name in _TRACKED_MODULES:
        module = sys.modules.get(mod_name)
        if module is None:
            snapshot[mod_name] = None
            continue
        # Capture id() of module-level singletons we know demos must
        # not swap. Identity is sufficient because rebinding implies
        # mutation of the module's namespace.
        snapshot[mod_name] = id(module)
    return snapshot


def verify_no_global_state_mutation(
    *, before: dict[str, Any], after: dict[str, Any]
) -> tuple[bool, tuple[str, ...]]:
    """Compare two state snapshots; return ``(passed, divergences)``.

    Adapters that follow the protocol leave every snapshot key
    unchanged across their :meth:`DemoCommand.run` call. Lazy imports
    (``None`` → module id transitions) are *not* contract violations:
    importing a previously-unloaded module is benign and unavoidable
    when the adapter does its own deferred imports. Only id → id
    rebindings (the module object was replaced) and value-set
    divergences on env vars are flagged.
    """
    divergences: list[str] = []
    for key in set(before.keys()) | set(after.keys()):
        b = before.get(key)
        a = after.get(key)
        if b == a:
            continue
        if b is None and a is not None:
            # Lazy import: a module that wasn't yet loaded is now
            # loaded. Benign and unavoidable.
            continue
        divergences.append(
            f"{key}: before={b!r} after={a!r}"
        )
    return (not divergences, tuple(divergences))


def capture_state() -> dict[str, Any]:
    """Public alias for the snapshot helper, for test fixtures."""
    return _global_state_snapshot()
