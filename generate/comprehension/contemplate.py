"""ADR-0174 Phase 4 — in-loop contemplation.

When constraint elimination leaves ``|surviving| >= 2`` open
hypotheses, the reader invokes :func:`contemplate` to deterministically
search vault / packs / audit-history for evidence that disambiguates
the survivors. Returns :class:`Resolution` on unambiguous evidence,
``None`` on ambiguous or absent evidence (caller refuses cleanly —
preserves wrong=0).

Phase 4a scope (this module):

  - :class:`Resolution` dataclass with closed-set ``kind`` and ``source``
  - :func:`contemplate` orchestrator with three adapters consulted in
    precedence order: vault > pack > audit_history
  - Concrete pack adapter: gendered-pronoun resolution via
    ``en_core_names_v1`` (the first load-bearing use case — turns the
    Phase 3a multi-actor defense from refuse-on-ambiguity into admit-
    via-evidence when gendered names disambiguate)
  - Vault and audit-history adapters are stubs returning None in v1;
    Phase 4b will wire them when concrete use cases land

Trust boundary:

  - Read-only over every evidence source (no vault writes, no pack
    mutations, no audit-history modification)
  - Deterministic search; no LLM, no sampling, no normalization
  - Ambiguous evidence → ``None`` → caller refuses (wrong=0 preserved)
  - Adapter precedence is structural (vault > pack > audit_history),
    not score-tuned

Per ADR-0174 §"In-loop contemplation": ambiguity that contemplation
cannot resolve is a refusal, not a guess.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from generate.comprehension.state import (
    ComprehensionStateError,
    Hypothesis,
    ProblemReadingState,
)


# ---------------------------------------------------------------------------
# Closed-set contracts
# ---------------------------------------------------------------------------

VALID_RESOLUTION_KINDS: Final[frozenset[str]] = frozenset(
    {"eliminate", "admit_unknown"}
)
"""Closed set of Resolution.kind values. Adding new kinds requires ADR amendment."""

VALID_RESOLUTION_SOURCES: Final[frozenset[str]] = frozenset(
    {"vault", "pack", "audit_history"}
)
"""Closed set of evidence sources. Adapter precedence is vault > pack > audit_history."""


@dataclass(frozen=True, slots=True)
class Resolution:
    """Outcome of a successful contemplate consult.

    Returned by :func:`contemplate` when evidence unambiguously
    disambiguates the surviving hypothesis set. Serialisable as a
    JSON object in ``reader_trace`` events.

    Fields:
        kind:                 ``"eliminate"`` (remove ``target_hypothesis_id``
                              from survivors) or ``"admit_unknown"``
                              (admit a previously-held unknown bound by
                              the evidence).
        target_hypothesis_id: The ``Hypothesis.confidence_rank`` of the
                              hypothesis to eliminate (for ``"eliminate"``)
                              or the id of the held unknown to admit
                              (for ``"admit_unknown"``).
        sub_question:         The question the contemplate function was
                              asking itself when finding the resolution.
                              Recorded for trace audit; not used for
                              control flow.
        source:               Which adapter produced the resolution —
                              ``"vault"``, ``"pack"``, or
                              ``"audit_history"``.
        evidence:             Source-specific evidence references. For
                              pack source: tuple of ``(pack_id, fact)``
                              entries. For vault source: tuple of
                              ``(vault_recall_key, value)`` entries.
    """

    kind: Literal["eliminate", "admit_unknown"]
    target_hypothesis_id: int
    sub_question: str
    source: Literal["vault", "pack", "audit_history"]
    evidence: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.kind not in VALID_RESOLUTION_KINDS:
            raise ComprehensionStateError(
                f"Resolution.kind must be in {sorted(VALID_RESOLUTION_KINDS)}; "
                f"got {self.kind!r}"
            )
        if (
            not isinstance(self.target_hypothesis_id, int)
            or isinstance(self.target_hypothesis_id, bool)
            or self.target_hypothesis_id < 0
        ):
            raise ComprehensionStateError(
                "Resolution.target_hypothesis_id must be non-negative int; "
                f"got {self.target_hypothesis_id!r}"
            )
        if not isinstance(self.sub_question, str) or not self.sub_question:
            raise ComprehensionStateError(
                "Resolution.sub_question must be non-empty str"
            )
        if self.source not in VALID_RESOLUTION_SOURCES:
            raise ComprehensionStateError(
                f"Resolution.source must be in {sorted(VALID_RESOLUTION_SOURCES)}; "
                f"got {self.source!r}"
            )
        if not isinstance(self.evidence, tuple):
            raise ComprehensionStateError(
                "Resolution.evidence must be tuple"
            )
        for idx, e in enumerate(self.evidence):
            if not (
                isinstance(e, tuple)
                and len(e) == 2
                and isinstance(e[0], str) and e[0]
                and isinstance(e[1], str) and e[1]
            ):
                raise ComprehensionStateError(
                    f"Resolution.evidence[{idx}] must be "
                    f"(source_id:non-empty str, fact:non-empty str); got {e!r}"
                )


# ---------------------------------------------------------------------------
# Gendered-names pack — load + closed-set query
# ---------------------------------------------------------------------------

_PRONOUN_GENDER: Final[dict[str, str]] = {
    "she": "female", "her": "female", "hers": "female",
    "he": "male", "him": "male", "his": "male",
}
"""Closed-set pronoun → gender map. v1 covers English binary-gender
third-person singular pronouns. ``they``/``them`` deliberately excluded
(epicene; ambiguous gender; refusal-preferring discipline)."""


def _names_pack_path() -> Path:
    """Resolve the path to en_core_names_v1/gender.jsonl from repo root."""
    here = Path(__file__).resolve()
    repo_root = here
    for _ in range(10):
        repo_root = repo_root.parent
        if (repo_root / "pyproject.toml").exists():
            break
    return (
        repo_root / "language_packs" / "data" / "en_core_names_v1"
        / "gender.jsonl"
    )


@lru_cache(maxsize=1)
def _load_names_pack() -> dict[str, str]:
    """Load the gendered-names pack into a name → gender map.

    Cached per-process. Returns empty dict if the pack is absent (Phase 4
    consult then returns None on every query, refusal-preferring).
    """
    path = _names_pack_path()
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        name = entry.get("name")
        gender = entry.get("gender")
        if isinstance(name, str) and gender in ("female", "male"):
            out[name.lower()] = gender
    return out


def _pronoun_required_gender(pronoun: str) -> str | None:
    """Return 'female' / 'male' for English gendered pronouns, else None.

    ``they``/``them`` etc. return None — epicene pronouns are ambiguous
    by design and trigger refusal-preferring discipline at the caller.
    """
    return _PRONOUN_GENDER.get(pronoun.lower())


# ---------------------------------------------------------------------------
# Adapters — vault, pack, audit_history
# ---------------------------------------------------------------------------


def _consult_vault(
    state: ProblemReadingState,
    residual: tuple[Hypothesis, ...],
) -> Resolution | None:
    """Vault adapter — exact CGA recall for prior session resolutions.

    Phase 4a: returns None (stub). Phase 4b will wire vault-backed
    resolution when concrete use cases land (e.g. user previously
    corrected a pronoun reference and the resolution was vaulted).
    """
    return None


def _consult_packs(
    state: ProblemReadingState,
    residual: tuple[Hypothesis, ...],
    pronoun_hint: str | None,
    candidate_antecedents: tuple[str, ...],
) -> Resolution | None:
    """Pack adapter — gendered-pronoun resolution via en_core_names_v1.

    Inputs:
      - pronoun_hint: surface pronoun token from the held statement
        (e.g. ``"She"``), if known. None when contemplate is invoked
        for a non-pronoun ambiguity.
      - candidate_antecedents: the proper-noun antecedents the
        multi-actor defense identified as candidates. Each must be
        looked up in the names pack.

    Returns Resolution(kind="eliminate", source="pack", ...) when
    exactly one antecedent's gender matches the pronoun's required
    gender. Returns None when:
      - pronoun_hint is None (no pronoun to disambiguate)
      - pronoun is epicene (they/them) — gender ambiguous by design
      - any antecedent is not in the pack — ambiguous evidence
      - multiple antecedents share the matching gender — ambiguous
      - no antecedent matches the required gender — refuse (would-be
        wrong attribution)

    The Resolution targets the FIRST non-matching antecedent for
    elimination; the caller iterates and eventually leaves one
    survivor.

    Trust boundary: read-only over the pack. The pack itself is a
    closed-set artifact reviewed through the HITL corridor (ADR-0150/
    0152) — unknown-gender names are deliberately excluded.
    """
    if pronoun_hint is None:
        return None
    required_gender = _pronoun_required_gender(pronoun_hint)
    if required_gender is None:
        return None  # epicene pronoun or unknown

    pack = _load_names_pack()
    if not pack:
        return None  # pack absent

    # Each antecedent must be in the pack.
    antecedent_genders: dict[str, str] = {}
    for ant in candidate_antecedents:
        g = pack.get(ant.lower())
        if g is None:
            return None  # unknown name; refusal-preferring
        antecedent_genders[ant] = g

    # Find antecedents matching the required gender.
    matching = [
        ant for ant, g in antecedent_genders.items() if g == required_gender
    ]
    if len(matching) != 1:
        return None  # zero matches OR multiple matches → ambiguous

    chosen = matching[0]
    # We return a Resolution describing what the CALLER must do: bind
    # the pronoun to the chosen antecedent. The target_hypothesis_id
    # and kind are set by the caller in math_candidate_graph based on
    # which hypothesis carries the unresolved pronoun. We use kind=
    # "admit_unknown" with the chosen antecedent encoded in evidence
    # so the caller can route the pronoun resolution.
    return Resolution(
        kind="admit_unknown",
        target_hypothesis_id=0,  # caller substitutes based on context
        sub_question=(
            f"which antecedent matches the {required_gender}-gendered "
            f"pronoun {pronoun_hint!r}?"
        ),
        source="pack",
        evidence=tuple(
            ("en_core_names_v1", f"{ant}={g}")
            for ant, g in sorted(antecedent_genders.items())
        ) + (("en_core_names_v1", f"chosen={chosen}"),),
    )


def _consult_audit_history(
    state: ProblemReadingState,
    residual: tuple[Hypothesis, ...],
) -> Resolution | None:
    """Audit-history adapter — prior reader refusals on the same token.

    Phase 4a: returns None (stub). Phase 4b will wire audit-history
    when refusal-log evidence becomes a concrete consult target.
    """
    return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def contemplate(
    state: ProblemReadingState,
    residual: tuple[Hypothesis, ...],
    *,
    pronoun_hint: str | None = None,
    candidate_antecedents: tuple[str, ...] = (),
) -> Resolution | None:
    """Deterministic search for evidence disambiguating the residual.

    Per ADR-0174 §"In-loop contemplation":
      - Consults adapters in order: vault > pack > audit_history
      - Returns Resolution from the first adapter producing one
      - Returns None when no adapter resolves (caller refuses cleanly)

    Args:
        state: The current ProblemReadingState (for vault recall scope).
        residual: The surviving hypothesis set after constraint elimination.
        pronoun_hint: Optional surface pronoun for pronoun-resolution
            consult (the load-bearing Phase 4a use case).
        candidate_antecedents: Optional candidate antecedents for the
            pronoun, when contemplate is invoked from the multi-actor
            defense site.

    Returns:
        Resolution on unambiguous disambiguation, None otherwise.

    The function is pure: same inputs → same Resolution (or None).
    Determinism is the trace-hash invariant from ADR-0174 §Constraints.
    """
    if not residual or len(residual) < 2:
        # Nothing to disambiguate.
        return None

    # Adapter precedence (ADR-0174 §Open Q#3).
    result = _consult_vault(state, residual)
    if result is not None:
        return result
    result = _consult_packs(
        state, residual,
        pronoun_hint=pronoun_hint,
        candidate_antecedents=candidate_antecedents,
    )
    if result is not None:
        return result
    result = _consult_audit_history(state, residual)
    if result is not None:
        return result
    return None


__all__ = [
    "Resolution",
    "VALID_RESOLUTION_KINDS",
    "VALID_RESOLUTION_SOURCES",
    "contemplate",
]
