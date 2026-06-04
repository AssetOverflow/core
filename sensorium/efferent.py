"""Concrete efferent gate policy and trace-safe decision records."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.audio.checksum import sha256_json
from sensorium.protocol import CL41_DIM, AuthorityToken, EfferentVerdict


@dataclass(frozen=True, slots=True)
class EfferentEmissionTrace:
    """Trace-safe record of an efferent admission or refusal."""

    pack_id: str
    admitted: bool
    reason: str
    authority_sha256: str
    policy_sha256: str
    capability: str
    trace_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "admitted": self.admitted,
            "reason": self.reason,
            "authority_sha256": self.authority_sha256,
            "policy_sha256": self.policy_sha256,
            "capability": self.capability,
            "trace_sha256": self.trace_sha256,
        }


@dataclass(frozen=True, slots=True)
class DefaultEfferentGate:
    """Capability-scoped efferent gate.

    Admission requires a valid ``(32,)`` vector and one of:
    ``decode:<pack_id>``, ``decode:*``, or ``*`` in the authority token.
    """

    policy_id: str = "default-efferent-v1"

    @property
    def policy_sha256(self) -> str:
        return sha256_json({
            "policy_id": self.policy_id,
            "required_capability": "decode:<pack_id>",
            "wildcards": ["decode:*", "*"],
            "shape": [CL41_DIM],
        })

    def admit(
        self,
        pack_id: str,
        mv: np.ndarray,
        authority: AuthorityToken,
    ) -> EfferentVerdict:
        vec = np.asarray(mv, dtype=np.float32)
        if vec.shape != (CL41_DIM,):
            return EfferentVerdict(
                admitted=False,
                reason=f"invalid efferent vector shape: {vec.shape}",
                authority_sha256=authority.authority_sha256,
                policy_sha256=self.policy_sha256,
            )
        required = f"decode:{pack_id}"
        caps = set(authority.capabilities)
        admitted = required in caps or "decode:*" in caps or "*" in caps
        return EfferentVerdict(
            admitted=admitted,
            reason="admitted" if admitted else f"missing capability: {required}",
            authority_sha256=authority.authority_sha256,
            policy_sha256=self.policy_sha256,
        )

    def trace(
        self,
        pack_id: str,
        authority: AuthorityToken,
        verdict: EfferentVerdict,
    ) -> EfferentEmissionTrace:
        capability = f"decode:{pack_id}"
        payload = {
            "kind": "EfferentEmissionTrace",
            "pack_id": pack_id,
            "admitted": verdict.admitted,
            "reason": verdict.reason,
            "authority_sha256": authority.authority_sha256,
            "policy_sha256": verdict.policy_sha256,
            "capability": capability,
        }
        return EfferentEmissionTrace(
            pack_id=pack_id,
            admitted=verdict.admitted,
            reason=verdict.reason,
            authority_sha256=authority.authority_sha256,
            policy_sha256=verdict.policy_sha256,
            capability=capability,
            trace_sha256=sha256_json(payload),
        )
