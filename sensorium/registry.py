"""
sensorium/registry.py — ModalityPack registry.

The registry is the single mount point for all modality packs.
Registering a pack runs the mount-time unitarity check if a projection
head is present and checksum_verified is False.

Adding a modality never touches any existing layer.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from sensorium.protocol import (
    CL41_DIM,
    AuthorityToken,
    EfferentGate,
    EfferentRefusal,
    EfferentVerdict,
    ModalityPack,
)


class ModalityRegistry:
    """
    Registry for ModalityPack instances.

    Usage
    -----
    registry = ModalityRegistry()
    registry.mount(text_pack)
    pack = registry.get("en")
    mv   = registry.project("en", "beginning")
    """

    def __init__(self, *, efferent_gate: EfferentGate | None = None) -> None:
        self._packs: dict[str, ModalityPack] = {}
        self._efferent_gate = efferent_gate

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def mount(self, pack: ModalityPack, sample: Any = None) -> None:
        """
        Register a ModalityPack.

        If the pack has a projection head and checksum_verified is False,
        a unitarity check is run using `sample`. If sample is None and
        the pack has a vocabulary, the first vocabulary entry is used.

        Raises ValueError if the unitarity check fails.
        """
        if pack.projection is not None and not pack.checksum_verified:
            probe = sample
            if probe is None and len(pack.vocabulary) > 0:
                # Use the first registered token as the probe
                probe = next(iter(pack.vocabulary._token_to_rotor))
            if probe is not None:
                if not pack.projection.verify_unitarity(probe):
                    raise ValueError(
                        f"Unitarity check failed for pack '{pack.pack_id}'. "
                        "ProjectionHead.verify_unitarity() returned False. "
                        "The projection does not preserve the versor condition."
                    )
        self._packs[pack.pack_id] = pack

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, pack_id: str) -> ModalityPack:
        """Return the pack for pack_id. Raises KeyError if not mounted."""
        if pack_id not in self._packs:
            raise KeyError(
                f"No pack mounted for '{pack_id}'. "
                f"Mounted packs: {list(self._packs.keys())}"
            )
        return self._packs[pack_id]

    def project(self, pack_id: str, signal: Any) -> np.ndarray:
        """
        Project a surface signal through the named pack's ProjectionHead.

        Returns a (32,) float32 Cl(4,1) multivector.
        Raises RuntimeError if the pack's gate is not engaged or has no
        projection head.
        """
        pack = self.get(pack_id)
        if not pack.gate_engaged:
            raise RuntimeError(
                f"Pack '{pack_id}' gate is not engaged. "
                "Complete the Supervised Seeding Epoch before using this pack."
            )
        if pack.projection is None:
            raise RuntimeError(
                f"Pack '{pack_id}' has no ProjectionHead. "
                "Assign a projection before calling project()."
            )
        mv = pack.projection.project(signal)
        if mv.shape != (CL41_DIM,):
            raise ValueError(
                f"ProjectionHead for '{pack_id}' returned shape {mv.shape}, "
                f"expected ({CL41_DIM},)."
            )
        return mv.astype(np.float32)

    def project_batch(self, pack_id: str, signals: list) -> np.ndarray:
        """Batch projection. Returns (N, 32) float32."""
        pack = self.get(pack_id)
        if not pack.gate_engaged:
            raise RuntimeError(f"Pack '{pack_id}' gate is not engaged.")
        if pack.projection is None:
            raise RuntimeError(f"Pack '{pack_id}' has no ProjectionHead.")
        mvs = pack.projection.project_batch(signals)
        if mvs.ndim != 2 or mvs.shape[1] != CL41_DIM:
            raise ValueError(
                f"Batch projection for '{pack_id}' returned shape {mvs.shape}, "
                f"expected (N, {CL41_DIM})."
            )
        return mvs.astype(np.float32)

    def decode(self, pack_id: str, mv: np.ndarray, *, authority: AuthorityToken) -> Any:
        """Decode a manifold vector through a governed SurfaceDecoder.

        Efferent emission fails closed: a runtime gate must admit the vector
        before the decoder sees it.
        """
        pack = self.get(pack_id)
        if not pack.gate_engaged:
            raise RuntimeError(f"Pack '{pack_id}' gate is not engaged.")
        if pack.decoder is None:
            raise RuntimeError(f"Pack '{pack_id}' has no SurfaceDecoder.")
        vec = np.asarray(mv, dtype=np.float32)
        if vec.shape != (CL41_DIM,):
            raise ValueError(
                f"decode for '{pack_id}' received shape {vec.shape}, expected ({CL41_DIM},)."
            )
        if self._efferent_gate is None:
            verdict = EfferentVerdict(
                admitted=False,
                reason="no efferent gate configured",
                authority_sha256=authority.authority_sha256,
                policy_sha256="deny-by-default",
            )
            raise EfferentRefusal(pack_id, verdict)
        verdict = self._efferent_gate.admit(pack_id, vec, authority)
        if not verdict.admitted:
            raise EfferentRefusal(pack_id, verdict)
        return pack.decoder.decode(vec)

    def decode_batch(
        self,
        pack_id: str,
        mvs: np.ndarray,
        *,
        authority: AuthorityToken,
    ) -> list[Any]:
        """Batch decode after every vector is admitted by the efferent gate."""
        pack = self.get(pack_id)
        if not pack.gate_engaged:
            raise RuntimeError(f"Pack '{pack_id}' gate is not engaged.")
        if pack.decoder is None:
            raise RuntimeError(f"Pack '{pack_id}' has no SurfaceDecoder.")
        arr = np.asarray(mvs, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] != CL41_DIM:
            raise ValueError(
                f"decode_batch for '{pack_id}' received shape {arr.shape}, "
                f"expected (N, {CL41_DIM})."
            )
        if self._efferent_gate is None:
            verdict = EfferentVerdict(
                admitted=False,
                reason="no efferent gate configured",
                authority_sha256=authority.authority_sha256,
                policy_sha256="deny-by-default",
            )
            raise EfferentRefusal(pack_id, verdict)
        for vec in arr:
            verdict = self._efferent_gate.admit(pack_id, vec, authority)
            if not verdict.admitted:
                raise EfferentRefusal(pack_id, verdict)
        return pack.decoder.decode_batch(arr)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def mounted_packs(self) -> list[str]:
        """Return list of mounted pack IDs."""
        return list(self._packs.keys())

    def __len__(self) -> int:
        return len(self._packs)

    def __contains__(self, pack_id: str) -> bool:
        return pack_id in self._packs
