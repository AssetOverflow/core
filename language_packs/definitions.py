"""ADR-0084 — definitional-layer substrate.

Owns the schema and load path for the extended ``glosses.jsonl`` entries
introduced by ADR-0084.  This module is the *substrate* layer only — no
composer here consumes the new fields, and no surface is generated from
them.  ADR-0085 adds the consumer; ADR-0086 adds predicate licensing at
ratification.

Design notes
------------

- ADR-0084 attaches the definitional block to the per-lemma gloss entry,
  NOT to ``lexicon.jsonl``.  The lexicon checksum stays the immutable
  seal; ``glosses.jsonl`` remains the additive overlay that already exists
  for the 9 core packs.
- Pack-level opt-in via ``LanguagePackManifest.definitional_layer``.  A
  pack without the flag parses today exactly as before — the older
  ``(pos, gloss)`` two-tuple shape is preserved in
  :mod:`chat.pack_resolver`.
- Strict-mode parsing (``definitional_layer: true``) enforces:
    * every required field present and well-typed
    * unknown keys inside the gloss entry rejected
    * ``predicates_invited`` may be an empty list (migration aid)
    * ``definition_version`` is a positive int
- Closure-rule enforcement lives in :func:`verify_definitional_closure`;
  it is invoked by the ratification gate (and by the standalone
  ``scripts/verify_definitional_closure.py`` dev tool authored alongside
  the content PR).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable


_PACK_ROOT = Path(__file__).parent / "data"


# Required keys inside a strict (definitional_layer=True) gloss entry.
_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "lemma",
        "gloss",
        "definitional_atoms",
        "predicates_invited",
        "definition_version",
        "provenance_ids",
    }
)

# All allowed keys inside a strict gloss entry.  Any key outside this
# set is rejected — ADR-0084 §Schema validation, "unrecognised key
# inside ``definition`` rejected (strict gate)".
_ALLOWED_KEYS: frozenset[str] = _REQUIRED_KEYS | frozenset({"pos"})


@dataclass(frozen=True, slots=True)
class GlossEntry:
    """One parsed ``glosses.jsonl`` entry.

    Fields beyond ``(lemma, gloss, pos)`` are populated only for entries
    coming from a pack with ``definitional_layer: true``.  Legacy
    two-field entries map to default values for the ADR-0084 fields.
    """

    lemma: str
    gloss: str
    pos: str = ""
    definitional_atoms: tuple[str, ...] = field(default_factory=tuple)
    predicates_invited: tuple[str, ...] = field(default_factory=tuple)
    definition_version: int = 0
    provenance_ids: tuple[str, ...] = field(default_factory=tuple)


class DefinitionalSchemaError(ValueError):
    """Raised when a strict-mode gloss entry violates the ADR-0084 schema."""


def _require_nonempty_str(payload: dict, key: str, *, lemma_hint: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DefinitionalSchemaError(
            f"gloss entry for lemma={lemma_hint!r} requires non-empty string field {key!r}"
        )
    return value.strip()


def _require_str_tuple(
    payload: dict, key: str, *, lemma_hint: str, allow_empty: bool
) -> tuple[str, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list) or any(not isinstance(x, str) or not x for x in raw):
        raise DefinitionalSchemaError(
            f"gloss entry for lemma={lemma_hint!r} requires {key!r} to be a list of non-empty strings"
        )
    if not raw and not allow_empty:
        raise DefinitionalSchemaError(
            f"gloss entry for lemma={lemma_hint!r} requires non-empty {key!r}"
        )
    return tuple(raw)


def parse_gloss_entry(payload: dict, *, strict: bool) -> GlossEntry:
    """Parse a single ``glosses.jsonl`` row.

    ``strict=True`` applies the ADR-0084 schema gate: required fields,
    typed lists, no unknown keys, positive ``definition_version``.

    ``strict=False`` preserves the back-compat two-field shape — any
    extra ADR-0084 fields present are read opportunistically but never
    required.
    """
    if not isinstance(payload, dict):
        raise DefinitionalSchemaError(f"gloss entry must be a JSON object, got {type(payload).__name__}")

    _maybe_lemma = payload.get("lemma")
    lemma_hint: str = _maybe_lemma if isinstance(_maybe_lemma, str) and _maybe_lemma else "<unknown>"

    if strict:
        unknown = set(payload.keys()) - _ALLOWED_KEYS
        if unknown:
            raise DefinitionalSchemaError(
                f"gloss entry for lemma={lemma_hint!r} carries unrecognised key(s): {sorted(unknown)}"
            )
        missing = _REQUIRED_KEYS - set(payload.keys())
        if missing:
            raise DefinitionalSchemaError(
                f"gloss entry for lemma={lemma_hint!r} missing required key(s): {sorted(missing)}"
            )

        lemma = _require_nonempty_str(payload, "lemma", lemma_hint=lemma_hint)
        gloss = _require_nonempty_str(payload, "gloss", lemma_hint=lemma)
        definitional_atoms = _require_str_tuple(
            payload, "definitional_atoms", lemma_hint=lemma, allow_empty=False
        )
        predicates_invited = _require_str_tuple(
            payload, "predicates_invited", lemma_hint=lemma, allow_empty=True
        )
        definition_version_raw = payload.get("definition_version")
        if not isinstance(definition_version_raw, int) or isinstance(definition_version_raw, bool) or definition_version_raw < 1:
            raise DefinitionalSchemaError(
                f"gloss entry for lemma={lemma!r} requires positive int definition_version"
            )
        provenance_ids = _require_str_tuple(
            payload, "provenance_ids", lemma_hint=lemma, allow_empty=False
        )
        pos_raw = payload.get("pos", "")
        if not isinstance(pos_raw, str):
            raise DefinitionalSchemaError(
                f"gloss entry for lemma={lemma!r} requires pos to be a string when present"
            )
        return GlossEntry(
            lemma=lemma,
            gloss=gloss,
            pos=pos_raw,
            definitional_atoms=definitional_atoms,
            predicates_invited=predicates_invited,
            definition_version=definition_version_raw,
            provenance_ids=provenance_ids,
        )

    # Lax / back-compat path: accept the original (lemma, gloss[, pos])
    # shape; surface ADR-0084 fields only if they happen to be present
    # and well-typed.  Silently drop malformed extras — never fabricate.
    lemma_raw = payload.get("lemma")
    gloss_raw = payload.get("gloss")
    if not isinstance(lemma_raw, str) or not lemma_raw.strip():
        raise DefinitionalSchemaError("gloss entry missing lemma")
    if not isinstance(gloss_raw, str) or not gloss_raw.strip():
        raise DefinitionalSchemaError(f"gloss entry for lemma={lemma_raw!r} missing gloss")

    pos_raw = payload.get("pos", "")
    pos = pos_raw if isinstance(pos_raw, str) else ""

    def _safe_str_tuple(key: str) -> tuple[str, ...]:
        raw = payload.get(key)
        if isinstance(raw, list) and all(isinstance(x, str) and x for x in raw):
            return tuple(raw)
        return ()

    dv = payload.get("definition_version")
    definition_version = dv if isinstance(dv, int) and not isinstance(dv, bool) and dv > 0 else 0

    return GlossEntry(
        lemma=lemma_raw.strip(),
        gloss=gloss_raw.strip(),
        pos=pos,
        definitional_atoms=_safe_str_tuple("definitional_atoms"),
        predicates_invited=_safe_str_tuple("predicates_invited"),
        definition_version=definition_version,
        provenance_ids=_safe_str_tuple("provenance_ids"),
    )


@lru_cache(maxsize=64)
def _load_pack_glosses_cached(pack_id: str, strict: bool) -> tuple[GlossEntry, ...]:
    path = _PACK_ROOT / pack_id / "glosses.jsonl"
    if not path.exists():
        return ()
    out: list[GlossEntry] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            if strict:
                raise DefinitionalSchemaError(
                    f"{pack_id}/glosses.jsonl:{line_no}: malformed JSON ({exc})"
                ) from exc
            continue
        try:
            out.append(parse_gloss_entry(payload, strict=strict))
        except DefinitionalSchemaError:
            if strict:
                raise
            continue
    return tuple(out)


def load_pack_glosses(pack_id: str, *, strict: bool) -> tuple[GlossEntry, ...]:
    """Return all parsed gloss entries for *pack_id*.

    ``strict=True`` enforces the ADR-0084 schema gate row-by-row; a
    single violation aborts the load with :class:`DefinitionalSchemaError`.
    Strict callers should pass ``manifest.definitional_layer`` so opt-in
    is driven from the manifest, not from the call site.
    """
    return _load_pack_glosses_cached(pack_id, strict)


def clear_definitions_cache() -> None:
    """Drop the gloss-entry cache.

    Test-only escape hatch — ratified packs are immutable in production
    and this cache is never invalidated outside tests.
    """
    _load_pack_glosses_cached.cache_clear()


# --------------------------------------------------------------------------- #
# Closure-rule verifier
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ClosureViolation:
    """One unresolved ``definitional_atoms`` reference."""

    pack_id: str
    lemma: str
    unresolved_token: str


def verify_definitional_closure(
    pack_id: str,
    *,
    mounted_pack_lemmas: Iterable[str],
    primitive_lemmas: Iterable[str],
    strict: bool = True,
) -> tuple[ClosureViolation, ...]:
    """Return every unresolved ``definitional_atoms`` reference in *pack_id*.

    A token resolves if it is (a) another lemma in the same pack's gloss
    set, (b) a lemma in any of *mounted_pack_lemmas* (which the caller
    builds from currently-mounted packs), or (c) a primitive in
    *primitive_lemmas*.  Per ADR-0084 §Definitional closure rule,
    cycles are permitted — co-reference between two pack lemmas is
    valid.

    The empty tuple is a pass.  Anything non-empty fails ratification.
    """
    entries = load_pack_glosses(pack_id, strict=strict)
    if not entries:
        return ()

    same_pack = {e.lemma.strip().lower() for e in entries}
    mounted = {lem.strip().lower() for lem in mounted_pack_lemmas if lem}
    primitives = {lem.strip().lower() for lem in primitive_lemmas if lem}

    violations: list[ClosureViolation] = []
    for entry in entries:
        for token in entry.definitional_atoms:
            key = token.strip().lower()
            if not key:
                continue
            if key in same_pack or key in mounted or key in primitives:
                continue
            violations.append(
                ClosureViolation(
                    pack_id=pack_id,
                    lemma=entry.lemma,
                    unresolved_token=token,
                )
            )
    return tuple(violations)
