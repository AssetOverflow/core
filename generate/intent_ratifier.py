"""Field-grounded intent ratification (ADR-0022 §TBD-1).

The rule-based regex classifier in ``generate/intent.py`` is the
*seed*; this module is the *ratifier*.  Forward semantic control on
top of a non-geometric classifier would recreate the same gap one
level up — the classifier becomes the oracle the field defers to.
ADR-0022 closes that gap by requiring the field to ratify the seed:
the prompt versor must lie within the seeded intent's admissible
region, or the intent demotes to ``IntentTag.UNKNOWN``.

Design decisions:

* **Smallest deterministic step.**  No new classifier model, no
  learned ratifier — the existing regex classifier remains the
  candidate generator; the field is the gate.
* **No sampling.**  Ratification is a CGA-inner-product threshold
  check, exact and replayable.  Same `(intent, prompt_versor)` →
  same verdict byte-for-byte.
* **No new closure invariant.**  The ratifier inspects the prompt
  versor; it does not normalize, repair, or mutate the field
  (CLAUDE.md §Normalization Rules).
* **No new trust surface.**  Pure function over typed in-memory
  state; no IO, no dynamic import.

The ratifier is wired into ``CognitiveTurnPipeline`` after the
seed classification and before the proposition graph is built; a
demotion routes through the existing UNKNOWN-domain surface path,
preserving honest refusal per ADR-0022 §2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

import numpy as np

from algebra.cga import cga_inner
from generate.admissibility import AdmissibilityRegion, region_from_relation_chain
from generate.intent import DialogueIntent, IntentTag


@unique
class RatificationOutcome(Enum):
    RATIFIED = "ratified"
    DEMOTED = "demoted"
    # Generic PASSTHROUGH — emitted by ratify_intent() when no vocab-grounded
    # anchor exists or when the seed is already UNKNOWN.  Preserved for callers
    # that use RatificationOutcome.PASSTHROUGH directly (e.g. existing tests).
    PASSTHROUGH = "passthrough"
    # Specific PASSTHROUGH sub-values — emitted by _ratify_intent() in
    # CognitiveTurnPipeline to distinguish the three cold-start conditions
    # (ADR-0144 / ADR-0142 §Implementation debts, debt 1).  All four PASSTHROUGH
    # variants are normalised to "passthrough" before being folded into
    # trace_hash so pre-ADR-0144 hashes remain byte-identical.
    PASSTHROUGH_NO_FIELD = "passthrough_no_field"
    PASSTHROUGH_NO_VOCAB = "passthrough_no_vocab"
    PASSTHROUGH_NO_VERSOR = "passthrough_no_versor"


@dataclass(frozen=True, slots=True)
class RatifiedIntent:
    """Result of field ratification of a seeded intent.

    ``intent`` is the (possibly demoted) intent the downstream
    pipeline should use.  ``outcome`` records what happened so the
    trace and failure surface can name *why* an intent was rejected.
    ``score`` carries the CGA inner product the verdict was based
    on; ``threshold`` records the gate it was checked against.
    """

    intent: DialogueIntent
    outcome: RatificationOutcome
    score: float
    threshold: float
    seed_tag: IntentTag


def _intent_anchor_versor(vocab, intent: DialogueIntent) -> np.ndarray | None:
    """Return a vocab-grounded anchor versor for ``intent`` or ``None``.

    The anchor is the prompt-side reference the prompt versor is
    compared against.  v1 uses the intent's subject token when the
    vocab carries it; absent that, the predicate anchor for the
    intent tag (e.g. ``is`` for DEFINITION) is the fallback.

    Returns ``None`` when no anchor is grounded — that signals
    PASSTHROUGH (the ratifier has nothing to check against, so the
    seed survives unchanged).  PASSTHROUGH is deliberately distinct
    from RATIFIED so the trace can audit unratified turns.
    """
    if not intent.subject:
        return None
    candidates: tuple[str, ...] = (intent.subject.lower(),)
    if intent.tag is IntentTag.DEFINITION:
        candidates = candidates + ("is",)
    elif intent.tag is IntentTag.CAUSE:
        candidates = candidates + ("causes", "because")
    elif intent.tag is IntentTag.TRANSITIVE_QUERY and intent.relation:
        candidates = candidates + (intent.relation,)
    for token in candidates:
        try:
            return np.asarray(vocab.get_versor(token), dtype=np.float32)
        except (KeyError, AttributeError):
            continue
    return None


#: Default ratification threshold (Finding 3, audit 2026-05-20).
#:
#: Pre-fix the default was ``0.0``, which admitted anything with non-
#: negative projection onto the anchor versor — the field gate was
#: structurally live but semantically transparent (ADR-0022 §TBD-1).
#: Measured against ``core eval cognition`` across all 45 cases (45 =
#: 13 public + 13 dev + 19 holdout), every ratifiable case scored
#: ``cga_inner(prompt, anchor) ≥ 1.10`` after a prime turn primed the
#: field — see ``scripts/calibrate_ratification_threshold.py``.  The
#: 0.5 floor is well below that 1.10 minimum (no regression on any
#: passing case) while clearly non-trivially positive (random Cl(4,1)
#: inner products fluctuate around zero, so 0.5 demands genuine
#: correlation with the anchor).  Off-corpus / adversarial prompts
#: with weakly-aligned anchors will now demote to ``UNKNOWN`` and
#: route through the honest-refusal surface.
_DEFAULT_RATIFICATION_THRESHOLD: float = 0.5


def ratify_intent(
    intent: DialogueIntent,
    prompt_versor: np.ndarray,
    *,
    vocab,
    threshold: float = _DEFAULT_RATIFICATION_THRESHOLD,
) -> RatifiedIntent:
    """Ratify a seeded intent against the prompt versor.

    The seed classifier (``generate.intent.classify_intent``) produced
    ``intent`` syntactically.  This function checks whether the
    prompt versor's geometric position is consistent with that
    classification — concretely, whether ``cga_inner(prompt, anchor)
    ≥ threshold`` where ``anchor`` is the vocab-grounded reference
    for the seeded intent's subject/relation.

    Outcomes:

      * ``RATIFIED`` — the seed survives; the field agrees with the
        regex.
      * ``DEMOTED`` — the field disagrees; the intent is replaced
        with ``IntentTag.UNKNOWN`` so the downstream pipeline routes
        through the unknown-domain surface (ADR-0022 §2).
      * ``PASSTHROUGH`` — no vocab-grounded anchor exists for the
        seed; the seed survives unchanged but the trace records
        that the field did not ratify it.

    The pre-existing ``IntentTag.UNKNOWN`` seed is treated as
    PASSTHROUGH (no demotion of an already-unknown intent).
    """
    if intent.tag is IntentTag.UNKNOWN:
        return RatifiedIntent(
            intent=intent,
            outcome=RatificationOutcome.PASSTHROUGH,
            score=0.0,
            threshold=threshold,
            seed_tag=intent.tag,
        )
    anchor = _intent_anchor_versor(vocab, intent)
    if anchor is None:
        return RatifiedIntent(
            intent=intent,
            outcome=RatificationOutcome.PASSTHROUGH,
            score=0.0,
            threshold=threshold,
            seed_tag=intent.tag,
        )
    prompt = np.asarray(prompt_versor, dtype=np.float32)
    score = float(cga_inner(prompt, anchor))
    if score >= threshold:
        return RatifiedIntent(
            intent=intent,
            outcome=RatificationOutcome.RATIFIED,
            score=score,
            threshold=threshold,
            seed_tag=intent.tag,
        )
    demoted = DialogueIntent(
        tag=IntentTag.UNKNOWN,
        subject=intent.subject,
        secondary_subject=intent.secondary_subject,
        object=intent.object,
        relation=intent.relation,
        negated=intent.negated,
        frame=intent.frame,
    )
    return RatifiedIntent(
        intent=demoted,
        outcome=RatificationOutcome.DEMOTED,
        score=score,
        threshold=threshold,
        seed_tag=intent.tag,
    )


def region_for_intent(
    intent: DialogueIntent,
    *,
    vocab,
    label: str | None = None,
) -> AdmissibilityRegion:
    """Build an ``AdmissibilityRegion`` from a (ratified) intent.

    The region's relation blade is the outer-product chain of
    grounded anchors for the intent's subject, predicate-anchor, and
    (when present) relation token.  Tokens that are not in the
    vocabulary are skipped — they cannot contribute to the blade.

    An intent that grounds *no* tokens yields an unconstrained
    region; this is the same behavior the propose/realize sites
    already accept (region=None) and preserves backwards
    compatibility during the ADR-0022 transition window
    (§TBD-3).
    """
    anchors: list[np.ndarray] = []
    candidates: list[str] = []
    if intent.subject:
        candidates.append(intent.subject.lower())
    if intent.relation:
        candidates.append(intent.relation.lower())
    if intent.tag is IntentTag.DEFINITION:
        candidates.append("is")
    elif intent.tag is IntentTag.CAUSE:
        candidates.append("causes")
    for token in candidates:
        try:
            anchors.append(np.asarray(vocab.get_versor(token), dtype=np.float32))
        except (KeyError, AttributeError):
            continue
    if not anchors:
        return AdmissibilityRegion(label=label or f"intent[{intent.tag.value}]")
    return region_from_relation_chain(
        anchors,
        label=label or f"intent[{intent.tag.value}]",
    )
