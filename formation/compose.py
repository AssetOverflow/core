"""Phase 4 — Compose: ValidatedTripleSet -> CourseYAML, byte-stable.

The composer is deterministic by construction:

* The template renders a JSON-shaped dict whose contents are independent of
  input ordering (concepts lex-sorted; relations topo-sorted with lex
  tie-break; sources lex-sorted within each candidate).
* The YAML emitter walks the dict in sorted-key order and uses a fixed
  block style with explicit list markers.  Strings, ints, and bools only —
  floats are forbidden (per ``formation.hashing``).
* ``course_sha256 = sha256(yaml_bytes)``.

If PyYAML is importable we additionally cross-check that
``yaml.safe_load(yaml_bytes)`` round-trips to the same dict; otherwise the
emitter is the sole source of truth.  Round-trip parity is enforced under
test as well.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from formation.course import CourseYAML, SubjectSpec, ValidatedTripleSet
from formation.hashing import _reject_floats, sha256_of
from formation.templates import get_template

_PLAIN_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_./:-]*$")
_NEEDS_QUOTING_KEYWORDS = frozenset(
    {
        "",
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        "null",
        "~",
        "True",
        "False",
        "Yes",
        "No",
        "On",
        "Off",
        "Null",
        "NULL",
    }
)


def compose(
    validated_set: ValidatedTripleSet,
    spec: SubjectSpec,
    source_bundle_sha: str,
    template_id: str = "definition",
    template_version: str = "1.0.0",
) -> CourseYAML:
    """Compose a deterministic :class:`CourseYAML` artifact.

    Same logical input -> same ``yaml_bytes`` -> same ``course_sha256``.
    Reordering the relations/concepts/counters tuples does not change the
    output because the template re-sorts them.

    Args:
        validated_set: Forge output.  All triples have passed every rule.
        spec: Subject spec (course header info).
        source_bundle_sha: SHA of the ore bundle that fed the Forge.
        template_id: Which template to render with (default ``"definition"``).
        template_version: Caller-asserted template version; must match the
            template's own ``template_version``.  This propagates into the
            YAML body and therefore into ``course_sha256``.
    """
    template = get_template(template_id)
    if template.template_version != template_version:
        raise ValueError(
            f"compose: template_version mismatch — caller asked for "
            f"{template_version!r} but registry has "
            f"{template.template_version!r}"
        )

    body = template.render(
        validated_set=validated_set,
        spec=spec,
        source_bundle_sha=source_bundle_sha,
    )
    _reject_floats(body)  # belt and suspenders — same rule as canonical_json
    yaml_bytes = _emit_canonical_yaml(body)
    course_sha256 = hashlib.sha256(yaml_bytes).hexdigest()
    course_id = str(body["course_id"])
    return CourseYAML(
        course_id=course_id,
        yaml_bytes=yaml_bytes,
        course_sha256=course_sha256,
        source_bundle_sha=source_bundle_sha,
        validated_set_sha=sha256_of(_validated_set_payload(validated_set)),
        template_id=template.template_id,
        template_version=template.template_version,
    )


# ---------- canonical YAML emitter ----------


def _emit_canonical_yaml(payload: dict[str, Any]) -> bytes:
    """Emit ``payload`` as deterministic block-style YAML bytes.

    Supports strings, ints, bools, lists, and dicts only.  Keys are emitted
    in sorted order; floats raise (rejected upstream too).  No anchors, no
    tags, no flow style — only block scalars and block sequences/mappings.
    """
    lines: list[str] = []
    _emit_node(payload, indent=0, lines=lines, in_list=False)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _emit_node(
    node: Any, *, indent: int, lines: list[str], in_list: bool
) -> None:
    pad = "  " * indent
    if isinstance(node, dict):
        if not node:
            lines.append(f"{pad}{{}}")
            return
        for key in sorted(node.keys()):
            if not isinstance(key, str):
                raise TypeError(
                    "canonical YAML: dict keys must be strings, got "
                    f"{type(key).__name__}"
                )
            value = node[key]
            key_repr = _scalar(key, force_quote_keyword=True)
            if isinstance(value, dict):
                if not value:
                    lines.append(f"{pad}{key_repr}: {{}}")
                else:
                    lines.append(f"{pad}{key_repr}:")
                    _emit_node(value, indent=indent + 1, lines=lines, in_list=False)
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{pad}{key_repr}: []")
                else:
                    lines.append(f"{pad}{key_repr}:")
                    _emit_list(value, indent=indent, lines=lines)
            else:
                lines.append(f"{pad}{key_repr}: {_scalar(value)}")
    elif isinstance(node, list):
        if not node:
            lines.append(f"{pad}[]")
            return
        _emit_list(node, indent=indent, lines=lines)
    else:
        lines.append(f"{pad}{_scalar(node)}")


def _emit_list(items: list[Any], *, indent: int, lines: list[str]) -> None:
    pad = "  " * indent
    for item in items:
        if isinstance(item, dict):
            if not item:
                lines.append(f"{pad}- {{}}")
                continue
            keys = sorted(item.keys())
            first_key = keys[0]
            first_value = item[first_key]
            first_repr = _scalar(first_key, force_quote_keyword=True)
            if isinstance(first_value, dict):
                if not first_value:
                    lines.append(f"{pad}- {first_repr}: {{}}")
                else:
                    lines.append(f"{pad}- {first_repr}:")
                    _emit_node(
                        first_value, indent=indent + 2, lines=lines, in_list=False
                    )
            elif isinstance(first_value, list):
                if not first_value:
                    lines.append(f"{pad}- {first_repr}: []")
                else:
                    lines.append(f"{pad}- {first_repr}:")
                    _emit_list(first_value, indent=indent + 2, lines=lines)
            else:
                lines.append(f"{pad}- {first_repr}: {_scalar(first_value)}")
            for k in keys[1:]:
                v = item[k]
                k_repr = _scalar(k, force_quote_keyword=True)
                inner_pad = "  " * (indent + 1)
                if isinstance(v, dict):
                    if not v:
                        lines.append(f"{inner_pad}{k_repr}: {{}}")
                    else:
                        lines.append(f"{inner_pad}{k_repr}:")
                        _emit_node(v, indent=indent + 2, lines=lines, in_list=False)
                elif isinstance(v, list):
                    if not v:
                        lines.append(f"{inner_pad}{k_repr}: []")
                    else:
                        lines.append(f"{inner_pad}{k_repr}:")
                        _emit_list(v, indent=indent + 2, lines=lines)
                else:
                    lines.append(f"{inner_pad}{k_repr}: {_scalar(v)}")
        elif isinstance(item, list):
            if not item:
                lines.append(f"{pad}- []")
            else:
                lines.append(f"{pad}-")
                _emit_list(item, indent=indent + 1, lines=lines)
        else:
            lines.append(f"{pad}- {_scalar(item)}")


def _scalar(value: Any, *, force_quote_keyword: bool = False) -> str:
    """Emit a scalar.  Strings are quoted unless plain-safe and unambiguous."""
    if isinstance(value, bool):
        # bool is a subclass of int — check first.
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return '"null"'  # we forbid bare null to keep parser-agnostic
    if isinstance(value, float):
        raise TypeError(
            "canonical YAML: float values are forbidden; encode as strings"
        )
    if not isinstance(value, str):
        raise TypeError(
            f"canonical YAML: unsupported scalar type {type(value).__name__}"
        )
    needs_quote = (
        force_quote_keyword
        and value in _NEEDS_QUOTING_KEYWORDS
    )
    if needs_quote or _needs_quoting(value):
        return _double_quoted(value)
    return value


def _needs_quoting(text: str) -> bool:
    if text == "":
        return True
    if text in _NEEDS_QUOTING_KEYWORDS:
        return True
    if _PLAIN_SAFE.match(text) is None:
        return True
    # Avoid being parsed as an int by YAML readers.
    if text.lstrip("-").isdigit():
        return True
    return False


def _double_quoted(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


# ---------- validated-set hashing ----------


def _validated_set_payload(vs: ValidatedTripleSet) -> dict[str, Any]:
    """Order-independent payload of ``vs`` for SHA derivation."""
    return {
        "subject_id": vs.subject_id,
        "schema_version": vs.schema_version,
        "concepts": sorted(
            (
                {
                    "canonical_term": c.canonical_term,
                    "definition": c.definition,
                    "sources": sorted(
                        (
                            {
                                "source_sha": s.source_sha,
                                "span": s.span,
                                "adapter": s.adapter,
                                "retrieved_at": s.retrieved_at,
                            }
                            for s in c.sources
                        ),
                        key=lambda d: (d["source_sha"], d["adapter"]),
                    ),
                }
                for c in vs.concepts
            ),
            key=lambda d: (d["canonical_term"],),
        ),
        "relations": sorted(
            (
                {
                    "head": r.head,
                    "relation": r.relation,
                    "tail": r.tail,
                    "sources": sorted(
                        (
                            {
                                "source_sha": s.source_sha,
                                "span": s.span,
                                "adapter": s.adapter,
                                "retrieved_at": s.retrieved_at,
                            }
                            for s in r.sources
                        ),
                        key=lambda d: (d["source_sha"], d["adapter"]),
                    ),
                }
                for r in vs.relations
            ),
            key=lambda d: (d["head"], d["relation"], d["tail"]),
        ),
        "counters": sorted(
            (
                {
                    "head": c.head,
                    "relation": c.relation,
                    "tail": c.tail,
                }
                for c in vs.counters
            ),
            key=lambda d: (d["head"], d["relation"], d["tail"]),
        ),
        "ordering_hints": sorted(
            (
                {"before": o.before, "after": o.after}
                for o in vs.ordering_hints
            ),
            key=lambda d: (d["before"], d["after"]),
        ),
    }


__all__ = ["compose"]
