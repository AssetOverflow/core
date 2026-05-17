"""
InnerLoopExhaustion — evidence-carrying honest refusal at the walk site.

ADR-0024 Phase 2.  When the inner-loop admissibility check leaves no
admissible destination for the next step, the walk must refuse rather
than silently relax the constraint.  Phase 1 raised a plain
``ValueError`` with a message string; Phase 2 promotes that to a
typed exception that carries the refusal evidence (region label,
step index, rejected attempts, machine-readable reason) so downstream
layers can materialise the refusal into trace evidence without
re-parsing the message.

This is *not* normalization or repair (CLAUDE.md §Normalization Rules).
The walk still refuses at the same site, with the same algebra, with
the same effect on caller control flow.  The exception subclasses
``ValueError`` so every existing ``except ValueError`` handler in the
runtime/eval code paths continues to work byte-for-byte — the carrying
of structured evidence is additive.

Reason codes are minimal in Phase 2.  A single
``INNER_LOOP_EXHAUSTION`` reason covers both raise sites in
``generate/stream.py``:

  1. Pre-walk: the region's allowed-index intersection with the
     candidate set is empty before any step ran.  ``step_index = -1``
     and ``rejected_attempts = ()`` distinguish this site — no
     inner-loop rejections were issued; the region was already empty.

  2. In-walk: at some step, every candidate in the admissible set was
     rejected by ``check_transition`` at the configured threshold.
     ``step_index >= 0`` and ``rejected_attempts`` records the tried
     (index, word, score) triples in attempt order.

Splitting these into separate reasons can wait for Phase 4, when
rotor-frame refusal introduces a third structurally distinct mode
(ADR-0025).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class RefusalReason(Enum):
    """Machine-readable refusal taxonomy.

    The string value is what flows into ``trace_hash`` payloads when
    refusal materialisation is wired through a future ADR.  Stable
    string values are part of the replay contract.
    """

    INNER_LOOP_EXHAUSTION = "inner_loop_exhaustion"


class InnerLoopExhaustion(ValueError):
    """Honest refusal raised by the generation walk.

    Subclasses ``ValueError`` so pre-Phase-2 ``except ValueError``
    handlers in ``chat/runtime.py``, ``evals/...``, and tests still
    catch it without modification.

    Attributes
    ----------
    reason : RefusalReason
        Machine-readable taxonomy code.  Phase 2 uses a single value;
        Phase 4 (rotor frame admissibility) is expected to add more.
    region_label : str
        The ``AdmissibilityRegion.label`` that produced the refusal —
        the operator-visible identifier of which constraint blocked
        propagation.
    step_index : int
        Index of the step at which the inner loop exhausted.  ``-1``
        marks the pre-walk site (region intersection empty before any
        step ran); non-negative values identify the in-walk site.
    rejected_attempts : tuple[tuple[int, str, float], ...]
        Ordered record of ``(candidate_index, word, score)`` triples
        that the inner-loop check rejected at the step that failed.
        Empty tuple for the pre-walk site.

    ``str(exc)`` returns the human-readable message — preserving the
    Phase 1 exception message contract for callers that only inspected
    ``str(e)``.  Instances are logically immutable: attributes are set
    once in ``__init__`` and should not be reassigned.
    """

    __slots__ = ("reason", "region_label", "step_index", "rejected_attempts")

    def __init__(
        self,
        *,
        reason: RefusalReason,
        region_label: str,
        step_index: int,
        rejected_attempts: tuple[tuple[int, str, float], ...] = (),
        message: str | None = None,
    ) -> None:
        self.reason = reason
        self.region_label = region_label
        self.step_index = step_index
        self.rejected_attempts = tuple(rejected_attempts)
        super().__init__(message if message is not None else self._default_message())

    def _default_message(self) -> str:
        if self.step_index < 0:
            return (
                f"AdmissibilityRegion[{self.region_label}] left no walk candidates."
            )
        return (
            f"AdmissibilityRegion[{self.region_label}] inner-loop "
            f"rejected all candidates at step {self.step_index}."
        )
