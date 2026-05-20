"""Primitives-pack loader (ADR-0084).

Loads ``packs/primitives/<pack_id>/{manifest.json,primitives.jsonl}``
with byte-checksum verification and strict schema parsing.

Why a separate loader (not :mod:`language_packs.compiler`)
----------------------------------------------------------

Primitives are not lexicon entries — they have no surface, no morphology,
no semantic-domain assignment, no manifold coordinate.  They are a flat
set of terminal symbols consulted by
:func:`language_packs.definitions.verify_definitional_closure` as the
``floor`` argument.  Treating them as a degenerate ``LexicalEntry`` would
import irrelevant machinery and blur the substrate boundary the ADR is
deliberately drawing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


class PrimitivesPackError(RuntimeError):
    """Raised when a primitives pack is missing, malformed, or unverified.

    Inherits from :class:`RuntimeError` (not :class:`ValueError`) on the
    same principle as :class:`packs.safety.SafetyPackError` — a missing
    primitives pack is a fail-closed runtime condition for any system
    that opts into the definitional layer, not a recoverable
    input-validation error.
    """


DEFAULT_PRIMITIVES_PACK: str = "en_semantic_primitives_v1"
_PACK_ROOT: Path = Path(__file__).resolve().parent

_REQUIRED_MANIFEST_KEYS: frozenset[str] = frozenset(
    {
        "pack_id",
        "language",
        "kind",
        "definitional_layer",
        "version",
        "issued_at",
        "checksum",
        "primitive_count",
        "never_auto_mutable",
        "provenance",
    }
)
_ALLOWED_PRIMITIVE_KEYS: frozenset[str] = frozenset(
    {"lemma", "category", "pos", "primitive_version", "provenance_ids"}
)
_REQUIRED_PRIMITIVE_KEYS: frozenset[str] = frozenset(
    {"lemma", "category", "primitive_version", "provenance_ids"}
)


@dataclass(frozen=True, slots=True)
class Primitive:
    """One ratified primitive entry."""

    lemma: str
    category: str
    pos: str
    primitive_version: int
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PrimitivesPack:
    """Loaded primitives pack — immutable terminal-symbol floor."""

    pack_id: str
    language: str
    version: int
    issued_at: str
    primitives: tuple[Primitive, ...]
    checksum: str

    @property
    def lemmas(self) -> frozenset[str]:
        """Return the lower-cased frozen set of primitive lemmas."""
        return frozenset(p.lemma.lower() for p in self.primitives)


def _validate_pack_id(pack_id: object) -> str:
    if not isinstance(pack_id, str) or not pack_id:
        raise PrimitivesPackError(f"primitives pack_id must be a non-empty string, got {pack_id!r}")
    if ".." in pack_id or "/" in pack_id or "\\" in pack_id or pack_id.startswith("."):
        raise PrimitivesPackError(f"primitives pack_id contains forbidden path token(s): {pack_id!r}")
    for ch in pack_id:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-"})):
            raise PrimitivesPackError(
                f"primitives pack_id must be alphanumeric/_/-, got {pack_id!r}"
            )
    return pack_id


def _parse_primitive(payload: object, *, line_no: int, pack_id: str) -> Primitive:
    if not isinstance(payload, dict):
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: entry must be a JSON object"
        )
    unknown = set(payload.keys()) - _ALLOWED_PRIMITIVE_KEYS
    if unknown:
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: unrecognised key(s): {sorted(unknown)}"
        )
    missing = _REQUIRED_PRIMITIVE_KEYS - set(payload.keys())
    if missing:
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: missing required key(s): {sorted(missing)}"
        )

    lemma = payload["lemma"]
    category = payload["category"]
    primitive_version = payload["primitive_version"]
    provenance_ids = payload["provenance_ids"]
    pos = payload.get("pos", "")

    if not isinstance(lemma, str) or not lemma.strip():
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: lemma must be a non-empty string"
        )
    if not isinstance(category, str) or not category.strip():
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: category must be a non-empty string"
        )
    if not isinstance(primitive_version, int) or isinstance(primitive_version, bool) or primitive_version < 1:
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: primitive_version must be a positive int"
        )
    if not isinstance(provenance_ids, list) or not provenance_ids or any(
        not isinstance(x, str) or not x for x in provenance_ids
    ):
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: provenance_ids must be a non-empty list of strings"
        )
    if not isinstance(pos, str):
        raise PrimitivesPackError(
            f"{pack_id}/primitives.jsonl:{line_no}: pos must be a string when present"
        )

    return Primitive(
        lemma=lemma.strip(),
        category=category.strip(),
        pos=pos,
        primitive_version=primitive_version,
        provenance_ids=tuple(provenance_ids),
    )


@lru_cache(maxsize=8)
def _load_primitives_pack_cached(pack_id: str) -> PrimitivesPack:
    pack_dir = _PACK_ROOT / pack_id
    manifest_path = pack_dir / "manifest.json"
    primitives_path = pack_dir / "primitives.jsonl"

    if not manifest_path.exists():
        raise PrimitivesPackError(f"primitives pack manifest missing at {manifest_path}")
    if not primitives_path.exists():
        raise PrimitivesPackError(f"primitives pack jsonl missing at {primitives_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrimitivesPackError(f"primitives pack manifest malformed: {exc}") from exc

    if not isinstance(manifest, dict):
        raise PrimitivesPackError("primitives pack manifest must be a JSON object")
    missing = _REQUIRED_MANIFEST_KEYS - set(manifest.keys())
    if missing:
        raise PrimitivesPackError(
            f"primitives pack manifest missing required key(s): {sorted(missing)}"
        )
    if manifest["kind"] != "primitives":
        raise PrimitivesPackError(
            f"primitives pack manifest kind must be 'primitives', got {manifest['kind']!r}"
        )
    if manifest["definitional_layer"] is not True:
        raise PrimitivesPackError(
            "primitives pack manifest must have definitional_layer: true"
        )
    if manifest["never_auto_mutable"] is not True:
        raise PrimitivesPackError(
            "primitives pack manifest must have never_auto_mutable: true"
        )
    if manifest["pack_id"] != pack_id:
        raise PrimitivesPackError(
            f"primitives pack manifest pack_id {manifest['pack_id']!r} != directory {pack_id!r}"
        )

    primitives_bytes = primitives_path.read_bytes()
    actual_checksum = hashlib.sha256(primitives_bytes).hexdigest()
    expected_checksum = manifest["checksum"]
    if not isinstance(expected_checksum, str) or actual_checksum != expected_checksum:
        raise PrimitivesPackError(
            f"primitives pack checksum mismatch for {pack_id}: "
            f"{actual_checksum} != {expected_checksum}"
        )

    primitives: list[Primitive] = []
    for line_no, raw_line in enumerate(primitives_bytes.decode("utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PrimitivesPackError(
                f"{pack_id}/primitives.jsonl:{line_no}: malformed JSON ({exc})"
            ) from exc
        primitives.append(_parse_primitive(payload, line_no=line_no, pack_id=pack_id))

    declared_count = manifest["primitive_count"]
    if not isinstance(declared_count, int) or declared_count != len(primitives):
        raise PrimitivesPackError(
            f"primitives pack manifest declares primitive_count={declared_count} "
            f"but {len(primitives)} entries parsed from primitives.jsonl"
        )

    # Lemma-uniqueness gate — a primitive must be the floor, so the
    # same lemma must not be ratified twice within one pack.
    seen: set[str] = set()
    for primitive in primitives:
        key = primitive.lemma.lower()
        if key in seen:
            raise PrimitivesPackError(
                f"primitives pack {pack_id} ratifies lemma {primitive.lemma!r} more than once"
            )
        seen.add(key)

    version_raw = manifest["version"]
    if not isinstance(version_raw, int):
        raise PrimitivesPackError(
            f"primitives pack manifest version must be an int, got {version_raw!r}"
        )
    issued_at_raw = manifest["issued_at"]
    if not isinstance(issued_at_raw, str) or not issued_at_raw:
        raise PrimitivesPackError("primitives pack manifest issued_at must be a non-empty string")
    language_raw = manifest["language"]
    if not isinstance(language_raw, str) or not language_raw:
        raise PrimitivesPackError("primitives pack manifest language must be a non-empty string")

    return PrimitivesPack(
        pack_id=pack_id,
        language=language_raw,
        version=version_raw,
        issued_at=issued_at_raw,
        primitives=tuple(primitives),
        checksum=actual_checksum,
    )


def load_primitives_pack(pack_id: str = DEFAULT_PRIMITIVES_PACK) -> PrimitivesPack:
    """Load and verify a primitives pack from disk.

    Fails closed on any error (missing files, checksum mismatch, schema
    violation).  Result is cached — subsequent calls return the same
    immutable instance.
    """
    return _load_primitives_pack_cached(_validate_pack_id(pack_id))


def clear_primitives_cache() -> None:
    """Drop the primitives-pack cache.

    Test-only escape hatch — ratified primitives packs are immutable in
    production and this cache is never invalidated outside tests.
    """
    _load_primitives_pack_cached.cache_clear()


def union_primitive_lemmas(pack_ids: Iterable[str]) -> frozenset[str]:
    """Return the lower-cased union of every primitive lemma across *pack_ids*."""
    out: set[str] = set()
    for pack_id in pack_ids:
        out.update(load_primitives_pack(pack_id).lemmas)
    return frozenset(out)
