"""The Forge — the single trust boundary between untrusted text and the manifold.

The Forge accepts ``RelationCandidate`` / ``ConceptCandidate`` /
``CounterCandidate`` objects (typically emitted by the Smelter) and runs each
through every validation rule in order.  Candidates that pass every rule are
emitted as part of a ``ValidatedTripleSet`` and acquire
``EpistemicStatus.SPECULATIVE`` when handed to the teaching layer.

Validation rules, in order:

    R1. Triple is well-typed.   Must parse via
        ``teaching.relation_parse.parse_triple`` so the head/relation/tail
        align with the cognition pack's relation predicates.

    R2. Identity-axis collision screen.  No triple may name an identity-axis
        term in its head or tail.  Identity is not editable via mining.

    R3. Source allow-list.  Every cited source SHA must appear in the
        ``SourceAllowlist``.  Quarantined otherwise.

    R4. Pack collision check.  The triple must not already exist in the
        language pack or ``TeachingStore`` — duplicate triples are dropped
        (not quarantined; they are simply redundant).

    R5. Cross-reference rule.  A candidate graduates iff:
            - it has at least one ``"primary"`` source, OR
            - it has ≥2 independent ``"secondary"`` source SHAs.
        LLM-sourced candidates carry tier ``"llm"`` and never satisfy R5 on
        their own; they require ≥2 non-LLM corroborators (i.e. R5 evaluates
        only the non-LLM citations).

Cache: a ``ValidatedTripleCache`` keyed by ``(head, relation, tail)`` stores
previously-validated triples and short-circuits re-validation.  The cache is
append-only and content-addressed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Protocol

from formation.allowlist import SourceAllowlist
from formation.candidate import (
    CandidateState,
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.course import ValidatedTripleSet
from formation.hashing import canonical_json, sha256_of
from teaching.relation_parse import parse_triple


# Default identity-axis terms.  These match the typical CORE identity-manifold
# vocabulary (truth, identity, self, etc.) and can be extended per-deployment.
# Curated, not learned — per CLAUDE.md "compact, curated packs" doctrine.
DEFAULT_IDENTITY_AXIS_TERMS: Final[frozenset[str]] = frozenset({
    "identity",
    "self",
    "truth",
    "truthfulness",
    "coherence",
    "honesty",
    "core",
    "manifold",
    "operator",
    "claude",
    "anthropic",
})


class _TripleHaystack(Protocol):
    """Minimal protocol for pack/teaching-store collision lookup."""

    def triples(self) -> tuple[tuple[str, str, str], ...]: ...


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    """A candidate that failed a Forge rule.

    ``reason`` is one of:
        "malformed", "identity_axis_collision",
        "invalid_source", "duplicate", "insufficient_corroboration".
    """

    head: str
    relation: str
    tail: str
    reason: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ForgeResult:
    validated: tuple[RelationCandidate, ...]
    quarantined: tuple[RelationCandidate, ...]
    duplicates: tuple[RelationCandidate, ...]
    rejections: tuple[RejectedCandidate, ...]


class ValidatedTripleCache:
    """Append-only file-backed cache of validated triples.

    Keyed by ``(head, relation, tail)``.  A cache hit means the triple has
    been validated previously for *some* subject and may be reused without
    re-running Forge rules R3–R5 (R1 and R2 are properties of the triple
    itself and are re-checked cheaply).
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path).resolve() if path is not None else None
        self._entries: dict[tuple[str, str, str], dict[str, object]] = {}
        if self._path is not None and self._path.exists():
            self._load()

    def _load(self) -> None:
        import json
        assert self._path is not None
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            key = (entry["head"], entry["relation"], entry["tail"])
            self._entries[key] = entry

    def contains(self, head: str, relation: str, tail: str) -> bool:
        return (head, relation, tail) in self._entries

    def remember(
        self, candidate: RelationCandidate, validated_set_sha: str
    ) -> None:
        key = (candidate.head, candidate.relation, candidate.tail)
        if key in self._entries:
            return
        entry = {
            "head": candidate.head,
            "relation": candidate.relation,
            "tail": candidate.tail,
            "validated_set_sha": validated_set_sha,
            "source_shas": sorted({s.source_sha for s in candidate.sources}),
        }
        self._entries[key] = entry
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                # canonical JSON per line; JSON-lines is fine for append-only.
                fh.write(canonical_json(entry).decode("utf-8") + "\n")

    def __len__(self) -> int:
        return len(self._entries)


class Forge:
    """The trust boundary.  Stateless validator over candidate inputs.

    Construct once with the allow-list, identity-axis terms, and any pack /
    teaching-store haystacks; invoke ``validate(...)`` per Smelter output.
    """

    def __init__(
        self,
        allowlist: SourceAllowlist,
        identity_axis_terms: Iterable[str] = DEFAULT_IDENTITY_AXIS_TERMS,
        pack_haystack: _TripleHaystack | None = None,
        teaching_store: _TripleHaystack | None = None,
        cache: ValidatedTripleCache | None = None,
    ) -> None:
        self._allowlist = allowlist
        self._identity_terms = frozenset(t.strip().lower() for t in identity_axis_terms)
        self._pack = pack_haystack
        self._teach = teaching_store
        self._cache = cache if cache is not None else ValidatedTripleCache()

    @property
    def cache(self) -> ValidatedTripleCache:
        return self._cache

    # ------------------------- public surface -------------------------

    def validate(
        self,
        subject_id: str,
        concepts: Iterable[ConceptCandidate] = (),
        relations: Iterable[RelationCandidate] = (),
        counters: Iterable[CounterCandidate] = (),
        ordering_hints: Iterable[OrderingHint] = (),
    ) -> ValidatedTripleSet:
        """Run every rule over the candidate inputs and emit a ``ValidatedTripleSet``."""
        validated_relations: list[RelationCandidate] = []
        quarantined_relations: list[RelationCandidate] = []

        existing = self._existing_triples()

        for cand in relations:
            outcome = self._evaluate_relation(cand, existing)
            if outcome is None:
                # duplicate; silently drop.
                continue
            if outcome.state is CandidateState.VALIDATED:
                validated_relations.append(outcome)
            else:
                quarantined_relations.append(outcome)

        validated_concepts = self._validate_concepts(concepts)
        validated_counters = self._validate_counters(counters)

        vts = ValidatedTripleSet(
            subject_id=subject_id,
            concepts=tuple(validated_concepts),
            relations=tuple(validated_relations),
            counters=tuple(validated_counters),
            ordering_hints=tuple(ordering_hints),
            quarantined=tuple(quarantined_relations),
        )
        vts_sha = sha256_of(_vts_for_hashing(vts))
        for v in validated_relations:
            self._cache.remember(v, vts_sha)
        return vts

    # ------------------------- relation rules -------------------------

    def _evaluate_relation(
        self,
        cand: RelationCandidate,
        existing: frozenset[tuple[str, str, str]],
    ) -> RelationCandidate | None:
        """Run rules R1–R5 against a single relation candidate.

        Returns the candidate with updated ``state`` and ``rejection_reason``,
        or ``None`` if the candidate is a duplicate of an existing pack/store
        triple (silently dropped).
        """
        triple = (cand.head, cand.relation, cand.tail)

        # R1: well-typed.
        if not self._is_well_typed(cand):
            return _quarantined(cand, "malformed")

        # R2: identity-axis collision.
        if self._collides_with_identity_axis(cand):
            return _quarantined(cand, "identity_axis_collision")

        # R3: source allow-list.
        bad_source = self._first_bad_source(cand)
        if bad_source is not None:
            return _quarantined(
                cand, "invalid_source", detail=bad_source
            )

        # R4: pack/teaching-store duplicate.
        if triple in existing:
            return None  # silent drop

        # R4b: cache hit short-circuits R5 — already validated previously.
        if self._cache.contains(*triple):
            return _validated(cand)

        # R5: cross-reference rule.
        if not self._satisfies_cross_reference(cand):
            return _quarantined(cand, "insufficient_corroboration")

        return _validated(cand)

    def _is_well_typed(self, cand: RelationCandidate) -> bool:
        if not cand.head or not cand.relation or not cand.tail:
            return False
        # Reconstruct a "head relation tail" sentence and round-trip it
        # through the project's relation parser so a well-typed candidate is
        # one the rest of the system can actually parse.
        sentence = f"{cand.head} {cand.relation.replace('_', ' ')} {cand.tail}"
        parsed = parse_triple(sentence)
        if parsed is None:
            return False
        head, relation, tail = parsed
        return (
            head == cand.head.lower()
            and relation == cand.relation
            and tail == cand.tail.lower()
        )

    def _collides_with_identity_axis(self, cand: RelationCandidate) -> bool:
        for side in (cand.head, cand.tail):
            for term in _tokens(side):
                if term in self._identity_terms:
                    return True
        return False

    def _first_bad_source(self, cand: RelationCandidate) -> str | None:
        if not cand.sources:
            return "no_sources"
        for src in cand.sources:
            if not _is_clean_sha(src.source_sha):
                return f"path_traversal:{src.source_sha!r}"
            if not self._allowlist.contains(src.source_sha):
                return f"not_in_allowlist:{src.source_sha}"
        return None

    def _satisfies_cross_reference(self, cand: RelationCandidate) -> bool:
        tiers = [self._allowlist.tier_of(s.source_sha) for s in cand.sources]
        # LLM citations never count toward R5 on their own.
        non_llm_distinct = {
            (s.source_sha, t)
            for s, t in zip(cand.sources, tiers)
            if t in ("primary", "secondary")
        }
        if any(t == "primary" for _sha, t in non_llm_distinct):
            return True
        secondary_shas = {sha for sha, t in non_llm_distinct if t == "secondary"}
        return len(secondary_shas) >= 2

    # ------------------------- helpers -------------------------

    def _existing_triples(self) -> frozenset[tuple[str, str, str]]:
        triples: set[tuple[str, str, str]] = set()
        if self._pack is not None:
            triples.update(self._pack.triples())
        if self._teach is not None:
            triples.update(self._teach.triples())
        return frozenset(triples)

    def _validate_concepts(
        self, concepts: Iterable[ConceptCandidate]
    ) -> list[ConceptCandidate]:
        # Concepts are admissible whenever they have ≥1 allow-listed source
        # whose SHA is clean.  Identity-axis terms are forbidden in the
        # canonical term.
        out: list[ConceptCandidate] = []
        for cc in concepts:
            if not cc.sources:
                continue
            if any(t in self._identity_terms for t in _tokens(cc.canonical_term)):
                continue
            if not all(_is_clean_sha(s.source_sha) for s in cc.sources):
                continue
            if not all(self._allowlist.contains(s.source_sha) for s in cc.sources):
                continue
            out.append(
                ConceptCandidate(
                    canonical_term=cc.canonical_term,
                    definition=cc.definition,
                    sources=cc.sources,
                    state=CandidateState.VALIDATED,
                )
            )
        return out

    def _validate_counters(
        self, counters: Iterable[CounterCandidate]
    ) -> list[CounterCandidate]:
        # Counters are explicitly false-but-plausible; they are stored for
        # Phase 4 boundary hardening.  We still require allow-listed sources
        # and identity-axis cleanliness.
        out: list[CounterCandidate] = []
        for cc in counters:
            if not cc.sources:
                continue
            if any(
                t in self._identity_terms
                for side in (cc.head, cc.tail)
                for t in _tokens(side)
            ):
                continue
            if not all(_is_clean_sha(s.source_sha) for s in cc.sources):
                continue
            if not all(self._allowlist.contains(s.source_sha) for s in cc.sources):
                continue
            out.append(
                CounterCandidate(
                    head=cc.head,
                    relation=cc.relation,
                    tail=cc.tail,
                    sources=cc.sources,
                    state=CandidateState.VALIDATED,
                )
            )
        return out


# ---------- module-private helpers ----------


def _quarantined(
    cand: RelationCandidate, reason: str, detail: str = ""
) -> RelationCandidate:
    return RelationCandidate(
        head=cand.head,
        relation=cand.relation,
        tail=cand.tail,
        sources=cand.sources,
        state=CandidateState.QUARANTINED,
        rejection_reason=reason if not detail else f"{reason}:{detail}",
    )


def _validated(cand: RelationCandidate) -> RelationCandidate:
    return RelationCandidate(
        head=cand.head,
        relation=cand.relation,
        tail=cand.tail,
        sources=cand.sources,
        state=CandidateState.VALIDATED,
        rejection_reason="",
    )


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(t.strip().lower() for t in text.replace("_", " ").split() if t.strip())


def _is_clean_sha(sha: str) -> bool:
    import re
    return bool(re.fullmatch(r"[0-9a-f]{64}", sha))


def _vts_for_hashing(vts: ValidatedTripleSet) -> dict[str, object]:
    """Project a ``ValidatedTripleSet`` to a canonical-JSON-safe dict."""
    return {
        "subject_id": vts.subject_id,
        "schema_version": vts.schema_version,
        "concepts": sorted(
            [
                {
                    "canonical_term": c.canonical_term,
                    "definition": c.definition,
                    "source_shas": sorted({s.source_sha for s in c.sources}),
                }
                for c in vts.concepts
            ],
            key=lambda d: d["canonical_term"],
        ),
        "relations": sorted(
            [
                {
                    "head": r.head,
                    "relation": r.relation,
                    "tail": r.tail,
                    "source_shas": sorted({s.source_sha for s in r.sources}),
                }
                for r in vts.relations
            ],
            key=lambda d: (d["head"], d["relation"], d["tail"]),
        ),
        "counters": sorted(
            [
                {"head": c.head, "relation": c.relation, "tail": c.tail}
                for c in vts.counters
            ],
            key=lambda d: (d["head"], d["relation"], d["tail"]),
        ),
        "ordering_hints": sorted(
            [{"before": h.before, "after": h.after} for h in vts.ordering_hints],
            key=lambda d: (d["before"], d["after"]),
        ),
    }
