"""Process frame schema layer — declarative candidate process schemas.

Tranche 1 — broad base-layer foundations.

Exposes candidate process schemas without executing arithmetic.
Each frame declares trigger surfaces, required/optional roles,
candidate relation type, hazards, and what is NOT licensed.

A process frame MAY say "this looks like a transfer candidate."
It MAY NOT calculate "therefore the answer is X."
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping


# ---------------------------------------------------------------------------
# Frame role — typed role within a process frame.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FrameRole:
    """A typed role within a :class:`ProcessFrame`.

    ``semantic_type`` classifies the role's function in the frame
    (e.g., ``'agent'``, ``'patient'``, ``'quantity'``).
    """
    name: str
    description: str
    semantic_type: str  # "agent" | "patient" | "quantity" | "unit" | "rate" | "container" | "target" | "object" | "scale"


# ---------------------------------------------------------------------------
# Process frame — declarative candidate schema.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ProcessFrame:
    """A declarative process schema — no arithmetic.

    ``trigger_surfaces`` lists the surface tokens that suggest this frame.
    ``required_roles`` must all be filled for the frame to be fully grounded.
    ``optional_roles`` may enhance the frame but are not mandatory.
    ``candidate_relation`` names the relation type this frame emits.
    ``hazards`` lists hazard categories this frame may trigger.
    ``not_licensed`` explicitly states what this frame does NOT permit.
    """
    name: str
    trigger_surfaces: tuple[str, ...]
    required_roles: tuple[FrameRole, ...]
    optional_roles: tuple[FrameRole, ...]
    candidate_relation: str
    hazards: tuple[str, ...]
    not_licensed: tuple[str, ...]


# ---------------------------------------------------------------------------
# Frame definitions — the 8 required process frames.
# ---------------------------------------------------------------------------
def _build_frames() -> tuple[ProcessFrame, ...]:
    """Build the complete set of process frames for Tranche 1."""

    transfer = ProcessFrame(
        name="transfer",
        trigger_surfaces=(
            "give", "gave", "gives", "giving",
            "receive", "received", "receives",
            "donate", "donated", "donates",
            "lend", "lent", "lends",
            "borrow", "borrowed", "borrows",
            "hand", "handed", "pass", "passed",
        ),
        required_roles=(
            FrameRole("agent", "The entity performing the transfer", "agent"),
            FrameRole("patient", "The entity receiving the transfer", "patient"),
            FrameRole("quantity", "The amount being transferred", "quantity"),
        ),
        optional_roles=(
            FrameRole("object", "What is being transferred", "object"),
            FrameRole("unit", "Unit of the transferred quantity", "unit"),
        ),
        candidate_relation="transfer",
        hazards=(
            "unbound_base_quantity",
            "comparative_direction_ambiguity",
        ),
        not_licensed=(
            "Computing the final answer from the transfer",
            "Determining net gain/loss without explicit problem context",
            "Inferring the direction of transfer without surface evidence",
        ),
    )

    consumption = ProcessFrame(
        name="consumption",
        trigger_surfaces=(
            "use", "used", "uses", "using",
            "spend", "spent", "spends", "spending",
            "eat", "ate", "eats", "eating",
            "lose", "lost", "loses", "losing",
            "gain", "gained", "gains", "gaining",
            "waste", "wasted", "wastes",
            "consume", "consumed", "consumes",
        ),
        required_roles=(
            FrameRole("agent", "The entity consuming/using", "agent"),
            FrameRole("quantity", "The amount consumed/used", "quantity"),
        ),
        optional_roles=(
            FrameRole("object", "What is being consumed", "object"),
            FrameRole("unit", "Unit of the consumed quantity", "unit"),
            FrameRole("rate", "Rate of consumption if applicable", "rate"),
        ),
        candidate_relation="consumption",
        hazards=(
            "unbound_base_quantity",
            "remainder_context_required",
        ),
        not_licensed=(
            "Computing the remaining quantity after consumption",
            "Inferring consumption rate from total and time without explicit cue",
            "Deciding whether gain or loss applies without surface evidence",
        ),
    )

    transaction = ProcessFrame(
        name="transaction",
        trigger_surfaces=(
            "buy", "bought", "buys", "buying",
            "sell", "sold", "sells", "selling",
            "cost", "costs", "costing",
            "purchase", "purchased", "purchases",
            "pay", "paid", "pays", "paying",
            "charge", "charged", "charges",
        ),
        required_roles=(
            FrameRole("buyer", "The entity purchasing", "agent"),
            FrameRole("quantity", "The number of items purchased", "quantity"),
            FrameRole("price", "The cost per item or total cost", "quantity"),
        ),
        optional_roles=(
            FrameRole("seller", "The entity selling", "patient"),
            FrameRole("object", "What is being bought/sold", "object"),
            FrameRole("unit", "Unit of the purchased quantity", "unit"),
            FrameRole("total_cost", "Total cost if specified", "quantity"),
        ),
        candidate_relation="transaction",
        hazards=(
            "currency_context",
            "unbound_base_quantity",
        ),
        not_licensed=(
            "Computing total cost from unit price and quantity",
            "Inferring unit price from total cost without explicit cue",
            "Determining change or remaining money",
        ),
    )

    labor_rate = ProcessFrame(
        name="labor_rate",
        trigger_surfaces=(
            "earn", "earned", "earns", "earning",
            "work", "worked", "works", "working",
            "make", "made", "makes", "making",
            "paid", "pay", "pays",
            "salary", "wage", "wages",
            "hourly", "per hour", "an hour",
        ),
        required_roles=(
            FrameRole("worker", "The entity earning/working", "agent"),
            FrameRole("rate", "The earning rate (e.g., $/hour)", "rate"),
            FrameRole("duration", "The time period worked", "quantity"),
        ),
        optional_roles=(
            FrameRole("unit", "Unit of the rate", "unit"),
            FrameRole("total_earnings", "Total earnings if specified", "quantity"),
        ),
        candidate_relation="labor_rate",
        hazards=(
            "currency_context",
            "temporal_context",
            "multiplicative_vs_occurrence_times",
        ),
        not_licensed=(
            "Computing total earnings from rate and duration",
            "Determining overtime rates without explicit cue",
            "Inferring work schedule from partial information",
        ),
    )

    travel = ProcessFrame(
        name="travel",
        trigger_surfaces=(
            "drive", "drove", "drives", "driving",
            "walk", "walked", "walks", "walking",
            "run", "ran", "runs", "running",
            "travel", "traveled", "travelled", "travels",
            "trip", "journey", "route",
            "round-trip", "round trip",
            "miles per hour", "mph", "km/h",
        ),
        required_roles=(
            FrameRole("traveler", "The entity traveling", "agent"),
            FrameRole("distance", "The distance traveled", "quantity"),
        ),
        optional_roles=(
            FrameRole("speed", "The speed of travel", "rate"),
            FrameRole("duration", "The time spent traveling", "quantity"),
            FrameRole("segments", "Individual segments of the journey", "object"),
        ),
        candidate_relation="travel",
        hazards=(
            "temporal_context",
            "unbound_base_quantity",
        ),
        not_licensed=(
            "Computing travel time from distance and speed",
            "Summing segments without explicit round-trip cue",
            "Inferring return trip distance without surface evidence",
        ),
    )

    container_packing = ProcessFrame(
        name="container_packing",
        trigger_surfaces=(
            "box", "boxes",
            "pack", "packs", "packed",
            "fill", "filled", "fills",
            "contain", "contains", "contained",
            "bag", "bags",
            "crate", "crates",
            "carton", "cartons",
            "dozen", "dozens",
            "bundle", "bundles",
        ),
        required_roles=(
            FrameRole("container", "The container type", "container"),
            FrameRole("content", "What the container holds", "object"),
            FrameRole("count_per", "Items per container", "quantity"),
        ),
        optional_roles=(
            FrameRole("num_containers", "Number of containers", "quantity"),
            FrameRole("total_items", "Total items across containers", "quantity"),
            FrameRole("unit", "Unit of the items", "unit"),
        ),
        candidate_relation="container_packing",
        hazards=(
            "unbound_base_quantity",
        ),
        not_licensed=(
            "Computing total items from containers × items-per-container",
            "Inferring container size without explicit pack data",
            "Determining leftover items without remainder cue",
        ),
    )

    partition = ProcessFrame(
        name="partition",
        trigger_surfaces=(
            "split", "splits",
            "divide", "divided", "divides",
            "share", "shared", "shares", "sharing",
            "part", "parts",
            "whole", "rest",
            "remaining", "remainder", "left", "left over",
            "half", "third", "quarter",
            "portion", "portions",
            "fraction",
        ),
        required_roles=(
            FrameRole("whole", "The total quantity being partitioned", "quantity"),
            FrameRole("parts", "The number of parts or partition ratio", "quantity"),
        ),
        optional_roles=(
            FrameRole("remainder", "The remaining portion after partition", "quantity"),
            FrameRole("agent", "The entity performing the partition", "agent"),
            FrameRole("recipients", "Who receives the parts", "patient"),
        ),
        candidate_relation="partition",
        hazards=(
            "unbound_base_quantity",
            "remainder_context_required",
        ),
        not_licensed=(
            "Computing the remainder from whole and parts",
            "Determining the partition ratio without explicit cue",
            "Chaining nested partitions without explicit surface evidence",
        ),
    )

    comparison = ProcessFrame(
        name="comparison",
        trigger_surfaces=(
            "more than", "more",
            "less than", "less", "fewer", "fewer than",
            "times as many", "times as much",
            "twice", "twice as", "twice as many",
            "double", "triple",
            "as many as", "as much as",
            "greater", "greater than",
            "smaller", "smaller than",
        ),
        required_roles=(
            FrameRole("reference", "The reference quantity being compared to", "quantity"),
            FrameRole("target", "The quantity being described", "quantity"),
            FrameRole("scale_factor", "The comparison ratio or difference", "scale"),
        ),
        optional_roles=(
            FrameRole("direction", "Whether comparison is additive or multiplicative", "object"),
            FrameRole("unit", "Unit of the compared quantities", "unit"),
        ),
        candidate_relation="comparison",
        hazards=(
            "comparative_direction_ambiguity",
            "unbound_base_quantity",
            "multiplicative_vs_occurrence_times",
        ),
        not_licensed=(
            "Computing the target from reference and scale factor",
            "Inferring comparison direction without surface evidence",
            "Resolving 'more' as additive vs. multiplicative without context",
        ),
    )

    return (
        transfer,
        consumption,
        transaction,
        labor_rate,
        travel,
        container_packing,
        partition,
        comparison,
    )


# ---------------------------------------------------------------------------
# Index — built once, cached for process lifetime.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _FrameIndex:
    """Internal index for fast lookup by surface and name."""
    by_name: Mapping[str, ProcessFrame]
    by_surface: Mapping[str, tuple[ProcessFrame, ...]]
    all_frames: tuple[ProcessFrame, ...]


@lru_cache(maxsize=1)
def _index() -> _FrameIndex:
    frames = _build_frames()
    by_name: dict[str, ProcessFrame] = {}
    by_surface: dict[str, list[ProcessFrame]] = {}

    for frame in frames:
        by_name[frame.name] = frame
        for surface in frame.trigger_surfaces:
            by_surface.setdefault(surface.lower(), []).append(frame)

    # Deterministic ordering within each surface bucket.
    frozen_by_surface = {
        k: tuple(sorted(v, key=lambda f: f.name))
        for k, v in by_surface.items()
    }

    return _FrameIndex(
        by_name=by_name,
        by_surface=frozen_by_surface,
        all_frames=frames,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def lookup_frame(surface: str) -> tuple[ProcessFrame, ...]:
    """Return all process frames triggered by the given surface.

    Returns an empty tuple if no frame matches the surface.
    Case-insensitive matching.
    """
    return _index().by_surface.get(surface.lower(), ())


def all_frames() -> tuple[ProcessFrame, ...]:
    """Return all registered process frames in definition order."""
    return _index().all_frames


def frame_by_name(name: str) -> ProcessFrame | None:
    """Return the frame with the given name, or None if not found."""
    return _index().by_name.get(name)
