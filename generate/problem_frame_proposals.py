"""ProblemFrame proposal helpers — Phase 2 of the ADR-0236 builder split.

Owns all construction-proposal detection logic that fires before contract
assessment. Imports propose_construction and ConstructionProposal from
construction_affordances. Must not import ContractAssessment, assess_contracts,
problem_frame_contracts, or ProblemFrameBuilder.
"""

from __future__ import annotations

import re

from generate.construction_affordances import ConstructionProposal, propose_construction
from generate.kernel_facts import GroundedScalar, SourceSpan
from generate.problem_frame_extractors import surface_in_text
from generate.process_frames import ProcessFrame

_DECREASE_TO_FRACTION_RE = re.compile(
    r"(?P<transition>decrease\s+to)\s+(?P<fraction>\d+\s*/\s*\d+)\s+of",
    re.IGNORECASE,
)
_PERCENT_OF_PROPOSAL_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\s+of\b",
    re.IGNORECASE,
)

_QUANTITY_ENTITY_PRONOUNS: frozenset[str] = frozenset(
    {
        "he",
        "her",
        "hers",
        "him",
        "his",
        "it",
        "its",
        "one",
        "ones",
        "she",
        "their",
        "theirs",
        "them",
        "these",
        "they",
        "this",
        "those",
    }
)

_QUANTITY_ENTITY_CONFUSER_SURFACES: tuple[str, ...] = (
    "each",
    "fewer than",
    "greater than",
    "less than",
    "more than",
    "per",
    "percent",
    "percentage",
    "ratio",
)

# Duplicated intentionally to preserve phase-local ownership.
# Do not import another phase's internals just to share this regex.
_ENTITY_AFTER_QUANTITY_RE = re.compile(
    r"(?P<quantity>\d+(?:\.\d+)?\s*%?)\s+(?:of\s+(?:the\s+)?)?"
    r"(?P<entity>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)


def _has_list_or_enumeration_suffix(text: str, end: int) -> bool:
    sentence_ends = tuple(
        index for marker in ".!?" if (index := text.find(marker, end)) != -1
    )
    sentence_end = min(sentence_ends, default=len(text))
    tail = text[end:sentence_end].lstrip().lower()
    return tail.startswith((",", ";", "and ", "or "))


def _contains_quantity_entity_confuser(text: str) -> bool:
    return any(
        surface_in_text(surface, text) for surface in _QUANTITY_ENTITY_CONFUSER_SURFACES
    )


def _proportional_decrease_proposals(text: str) -> tuple[ConstructionProposal, ...]:
    """Propose the one authorized proposal-first construction from its chunk."""
    matches = tuple(_DECREASE_TO_FRACTION_RE.finditer(text))
    if len(matches) != 1:
        return ()
    match = matches[0]
    evidence = SourceSpan(
        text[match.start() : match.end()],
        match.start(),
        match.end(),
    )
    return (
        propose_construction(
            "proportional_change.decrease_to_fraction",
            (evidence,),
        ),
    )


def _percent_partition_proposals(
    text: str,
    frames: tuple[ProcessFrame, ...],
) -> tuple[ConstructionProposal, ...]:
    """Propose percent partition from a process cue plus explicit percent-of."""
    frame_names = {frame.name for frame in frames}
    if not frame_names & {"partition", "consumption"}:
        return ()

    evidence_spans = tuple(
        SourceSpan(text[match.start() : match.end()], match.start(), match.end())
        for match in _PERCENT_OF_PROPOSAL_RE.finditer(text)
    )
    if not evidence_spans:
        return ()

    return (
        propose_construction(
            "partition.percent_partition",
            evidence_spans,
        ),
    )


def _quantity_entity_proposals(
    text: str,
    quantities: tuple[GroundedScalar, ...],
    frames: tuple[ProcessFrame, ...],
) -> tuple[ConstructionProposal, ...]:
    """Propose one narrow local quantity/entity cue from existing extraction.

    The family is intentionally unavailable when another process frame or a
    rate/comparison/percent surface is active.  Such text needs a different
    family to interpret it; this seam never selects the nearest noun.
    """
    if len(quantities) != 1 or frames:
        return ()
    if _contains_quantity_entity_confuser(text):
        return ()

    matches = tuple(_ENTITY_AFTER_QUANTITY_RE.finditer(text))
    if len(matches) != 1:
        return ()
    match = matches[0]
    if "%" in match.group("quantity"):
        return ()
    if match.group("entity").lower() in _QUANTITY_ENTITY_PRONOUNS:
        return ()
    if _has_list_or_enumeration_suffix(text, match.end("entity")):
        return ()

    quantity_span = quantities[0].provenance.source_spans[0]
    if quantity_span.start != match.start("quantity") or quantity_span.end != match.end(
        "quantity"
    ):
        return ()

    evidence = SourceSpan(
        text[match.start() : match.end()],
        match.start(),
        match.end(),
    )
    return (propose_construction("binding.quantity_entity", (evidence,)),)


def _unary_delta_proposals(
    text: str,
) -> tuple[ConstructionProposal, ...]:
    """Propose the narrow gained/lost unary-delta slice from exact local cues."""
    matches = list(re.finditer(r"\b(gained|lost)\b", text))
    if len(matches) != 1:
        return ()
    match = matches[0]

    clean_text = re.sub(r"\d+\.\d+", "", text)
    trimmed = clean_text.strip()
    if trimmed and trimmed[-1] in ".!?":
        trimmed = trimmed[:-1]
    if any(marker in trimmed for marker in ".!?"):
        return ()

    confusers = {
        "percent",
        "percentage",
        "%",
        "per",
        "each",
        "ratio",
        "than",
        "more than",
        "less than",
        "fewer than",
        "greater than",
        "times as",
    }
    for c in confusers:
        pattern = rf"\b{re.escape(c)}\b" if c[0].isalnum() and c[-1].isalnum() else re.escape(c)
        if re.search(pattern, text, re.IGNORECASE):
            return ()

    transfer_verbs = {
        "gave",
        "give",
        "gives",
        "handed",
        "passed",
        "sent",
        "send",
        "sends",
        "received",
        "receives",
        "bought",
        "buys",
        "sold",
        "sells",
        "spent",
        "spends",
        "ate",
        "eats",
    }
    if any(re.search(rf"\b{verb}\b", text.lower()) for verb in transfer_verbs):
        return ()

    containment_verbs = {
        "put",
        "took",
        "moved",
        "filled",
    }
    if any(re.search(rf"\b{verb}\b", text.lower()) for verb in containment_verbs):
        return ()

    before_after = {"had", "was", "became", "originally", "now has"}
    if any(re.search(rf"\b{word}\b", text.lower()) for word in before_after):
        return ()

    for coord in {"and", "or"}:
        if re.search(rf"\b{coord}\b", text, re.IGNORECASE):
            return ()
    if "," in text:
        return ()

    evidence = SourceSpan(
        text[match.start() : match.end()],
        match.start(),
        match.end(),
    )
    return (propose_construction("state_change.unary_del