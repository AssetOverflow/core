"""FrameVerdict — the frame-general closed-world verdict type (ADR-0222 §3, B4).

A SEALED, off-serving type. DISTINCT from ``generate/determine/Determined``: no
``answer: bool`` field, a five-way ``verdict`` enum instead, a distinct name, a distinct
evaluator (``generate.frame_verdict.evaluate``), and a firewall (INV-31). INV-30's
call-name scan keys on the literal name ``Determined`` and the ``answer`` argument —
``FrameVerdict`` matches neither, so a closed-world verdict can never be confused with an
open-world answer.

Shapes follow the B4 operator master brief (a consistent refinement of ADR-0222 §3's
illustrative block): ``PositiveRefutationKind`` is an enum; ``ClosedFrame`` carries an
explicit ``closure_declared`` flag + ``source``/``provenance``; the verdict carries
``provenance``. The ADR invariants are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique


@unique
class FrameKind(str, Enum):
    TEXT = "text"              # a declared-complete CWA fact set (ProofWriter-CWA, FOLIO)
    PERCEPTION = "perception"  # an ADR-0211 changed-slot falsification (PR-3)
    AUDIO = "audio"            # reserved
    VISION = "vision"          # reserved
    TOOL = "tool"              # reserved
    UNKNOWN = "unknown"        # unclassified frame — always SCOPE_BOUNDARY


@unique
class WorldAssumption(str, Enum):
    OPEN = "open"                      # absence => undetermined; entailed_false is ILLEGAL here
    CLOSED = "closed"                  # frame declared complete
    BOUNDED_CLOSED = "bounded_closed"  # complete only within a declared scope


@unique
class FrameVerdictKind(str, Enum):
    ENTAILED_TRUE = "entailed_true"    # the frame proves query
    ENTAILED_FALSE = "entailed_false"  # the frame proves ¬query (positive refutation)
    UNDETERMINED = "undetermined"      # neither query nor ¬query proven — within-frame refusal
    CONTRADICTION = "contradiction"    # the frame's own premises are inconsistent — NOT a False
    SCOPE_BOUNDARY = "scope_boundary"  # out of decidable regime / frame not licensed complete


@unique
class PositiveRefutationKind(str, Enum):
    """How an ``entailed_false`` was POSITIVELY proven. Required on every
    ``entailed_false``; ``None`` for every other verdict. A generic FALSIFIED (absence /
    over-observation) has NO positive refutation kind and therefore cannot prove false."""

    ROBDD_REFUTATION = "robdd_refutation"            # text: (⋀prem) → ¬query is an ROBDD tautology
    PERCEPTION_CHANGED_SLOT = "perception_changed_slot"  # perception: a declared-expected slot observed contradicting


@dataclass(frozen=True, slots=True)
class ClosedWorldProof:
    """Modality-blind, content-addressed proof envelope. Text and (PR-3) perception carry
    the SAME shape; only ``producer``, ``outcome``, and the keys differ."""

    producer: str                # "proof_chain.entail" | "sensorium.falsification" | "frame_verdict.guard"
    outcome: str                 # the producer's own literal: ENTAILED/REFUTED/UNKNOWN/REFUSED | FALSIFIED/SUPPORTED
    proof_sha256: str            # sha256_json over the canonical proof payload (non-empty)
    proof_keys: tuple[str, ...]  # content-addressed keys: entail (conjunction/query/refutation) | perception (run trace_hash)
    positive_refutation_kind: PositiveRefutationKind | None = None
    trace_hash: str = ""         # the underlying producer's deterministic evidence digest


@dataclass(frozen=True, slots=True)
class ClosedFrame:
    """The EXPLICIT closed-world context that licenses asserting a negation. The evaluator
    takes THIS, never a ``SessionContext`` — so it structurally cannot read open-world
    session memory where absence != false. Constructed explicitly by a lane / scenario."""

    frame_id: str
    frame_kind: FrameKind
    world_assumption: WorldAssumption     # OPEN => refuse; CLOSED/BOUNDED_CLOSED license a negation
    propositions: tuple[str, ...]         # text: the COMPLETE enumerated propositional-formula set
    closure_declared: bool                # the explicit completeness license; False => SCOPE_BOUNDARY
    source: str                           # who built the frame (a lane id) — provenance, not a license
    provenance: tuple[str, ...] = ()      # content-addressed refs the frame was assembled from


@dataclass(frozen=True, slots=True)
class FrameVerdict:
    """A closed-world verdict. DISTINCT from ``Determined``: no ``answer`` field, a five-way
    ``verdict`` enum, a distinct name, a distinct evaluator. INV-31 firewalls it out of the
    open-world runtime."""

    frame_id: str
    frame_kind: FrameKind
    world_assumption: WorldAssumption
    query: str                     # the proposition under test (canonical key)
    verdict: FrameVerdictKind      # the two-sided result — NOT a bool, NOT named ``answer``
    proof: ClosedWorldProof        # the replayable refutation/entailment evidence
    basis: str                     # epistemic_basis(grounds): "as_told" | "verified" (never hardcoded)
    trace_hash: str                # sha256_json deterministic replay digest of the whole verdict
    provenance: tuple[str, ...] = ()  # content-addressed refs (premise keys) — never raw payloads

    def __post_init__(self) -> None:
        # Admissibility invariants (ADR-0222 §3 / §12 obligation 2). A mismatched
        # (verdict, proof, world) triple fails LOUDLY at construction, so a mutation test can
        # trip it. NOTE: these run at CONSTRUCTION only (frozen+slots) — a post-construction
        # ``object.__setattr__`` bypass is out of scope; any future deserialization / codec
        # path MUST re-construct through ``_construct.build_frame_verdict`` (which re-runs this),
        # never reassign fields.

        # (0) Frame-general negation law: ``entailed_false`` is ILLEGAL in an OPEN world
        # (``WorldAssumption.OPEN`` — absence is never false). No producer (text, perception, or
        # any future modality) may emit an OPEN-world negation. The text evaluator and the
        # perception adapter both gate OPEN -> SCOPE_BOUNDARY upstream; this is the STRUCTURAL
        # backstop that fires if any producer forgets the gate.
        if (
            self.verdict is FrameVerdictKind.ENTAILED_FALSE
            and self.world_assumption is WorldAssumption.OPEN
        ):
            raise ValueError(
                "entailed_false is illegal in an OPEN world (WorldAssumption.OPEN) — absence is "
                "never false; an OPEN frame must refuse (scope_boundary), never assert a negation"
            )

        # (1) ``entailed_false`` may exist ONLY with a positive-refutation proof that NAMES which
        # positive refutation it is. A generic FALSIFIED (which ADR-0211 also emits for missing /
        # unexpected / whole-frame-missing — i.e. absence) cannot satisfy this; only an ROBDD
        # refutation or a perceptual changed-slot contradiction can.
        if self.verdict is FrameVerdictKind.ENTAILED_FALSE:
            p = self.proof
            ok = (
                (p.producer == "proof_chain.entail"
                    and p.outcome == "REFUTED"
                    and p.positive_refutation_kind is PositiveRefutationKind.ROBDD_REFUTATION)
                or (p.producer == "sensorium.falsification"
                    and p.outcome == "FALSIFIED"
                    and p.positive_refutation_kind is PositiveRefutationKind.PERCEPTION_CHANGED_SLOT)
            )
            if not ok or not p.proof_sha256:
                raise ValueError(
                    "entailed_false requires a positive-refutation proof: an ROBDD refutation "
                    "(ROBDD_REFUTATION) or a perceptual changed-slot contradiction "
                    "(PERCEPTION_CHANGED_SLOT) — never a generic FALSIFIED"
                )

        # (2) SYMMETRIC guard: ``entailed_true`` is admissible ONLY with a matching positive
        # entailment/support proof and NO refutation kind. Without this, a committed "Yes." would
        # lean ENTIRELY on the INV-31-A2 construction allowlist; with it, a bogus positive proof
        # fails loudly at construction too — a mutation test can trip a forged ENTAILED_TRUE.
        if self.verdict is FrameVerdictKind.ENTAILED_TRUE:
            p = self.proof
            ok = (
                (p.producer == "proof_chain.entail" and p.outcome == "ENTAILED")
                or (p.producer == "sensorium.falsification" and p.outcome == "SUPPORTED")
            )
            if not ok or not p.proof_sha256 or p.positive_refutation_kind is not None:
                raise ValueError(
                    "entailed_true requires a positive entailment/support proof "
                    "(proof_chain.entail/ENTAILED or sensorium.falsification/SUPPORTED) with a "
                    "non-empty proof_sha256 and NO positive_refutation_kind"
                )
