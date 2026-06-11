"""Typed validation of the MCP-shaped tool payload — the System 1/System 2 boundary.

The proposer's entire contribution arrives as the ``arguments`` object of an
MCP-shaped tool call.  This module validates it against ``tool_schema.json``
**interpretively**: the constraint set (required keys, types, lengths, enum,
pattern, ``additionalProperties: false``) is read from the committed schema file
itself, so the executable boundary cannot silently drift from the documented one.

Fail-closed and dependency-free: only the narrow JSON-Schema subset the tool
schema actually uses is interpreted, and a schema feature outside that subset
raises loudly at load time rather than being silently ignored.  Validation never
executes any derivation — an invalid payload is rejected before CORE runs.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

_HERE: Final[Path] = Path(__file__).resolve().parent
TOOL_SCHEMA_PATH: Final[Path] = _HERE / "tool_schema.json"

#: The JSON-Schema keywords this interpreter understands, per property spec.
#: ``description``/``default`` are documentation-only.  Anything else in the
#: committed schema is a contract this validator does not enforce -> loud error.
_SUPPORTED_PROPERTY_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"type", "minLength", "maxLength", "enum", "pattern", "description", "default"}
)
_SUPPORTED_TYPES: Final[dict[str, type]] = {"string": str, "boolean": bool}


#: The top-level inputSchema keywords this interpreter understands.  A top-level
#: combinator (``allOf``, ``patternProperties``, ...) would be silently
#: unenforced, so its presence is a loud error, same as an unknown property
#: keyword.
_SUPPORTED_SCHEMA_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"type", "properties", "required", "additionalProperties"}
)


@lru_cache(maxsize=1)
def load_tool_schema() -> dict[str, Any]:
    """The committed MCP-shaped tool definition.  Parsed once and cached: treat
    the returned mapping as read-only (callers only read or compare it)."""
    return json.loads(TOOL_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _input_schema() -> dict[str, Any]:
    schema = load_tool_schema()["inputSchema"]
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError(
            "tool inputSchema must be a closed object "
            "(type: object, additionalProperties: false) — the no-smuggling boundary"
        )
    unsupported_top = set(schema) - _SUPPORTED_SCHEMA_KEYWORDS
    if unsupported_top:
        raise ValueError(
            f"inputSchema uses unsupported top-level keywords {sorted(unsupported_top)}; "
            "extend the validator before extending the schema"
        )
    for name, spec in schema["properties"].items():
        unsupported = set(spec) - _SUPPORTED_PROPERTY_KEYWORDS
        if unsupported:
            raise ValueError(
                f"inputSchema property {name!r} uses unsupported keywords "
                f"{sorted(unsupported)}; extend the validator before extending the schema"
            )
        if spec.get("type") not in _SUPPORTED_TYPES:
            raise ValueError(f"inputSchema property {name!r} has unsupported type")
    return schema


def _clip(name: object) -> str:
    """Bounded repr for echoing an unknown property name — untrusted caller text
    must not round-trip unbounded into surfaces or artifacts."""
    rendered = repr(name)
    return rendered if len(rendered) <= 80 else rendered[:79] + "…"


def validate_payload(arguments: Any) -> tuple[str, ...]:
    """Every way ``arguments`` violates the tool's input schema — empty iff valid.

    Deterministic order (sorted unknown keys first, then schema-declaration
    order), so the same bad payload always yields the same error surface.
    """
    schema = _input_schema()
    if not isinstance(arguments, dict):
        return (f"arguments must be a JSON object, got {type(arguments).__name__}",)

    errors: list[str] = []
    properties: dict[str, Any] = schema["properties"]

    for unknown in sorted(str(key) for key in set(arguments) - set(properties)):
        errors.append(
            f"unexpected property {_clip(unknown)} (additionalProperties is false; "
            "the proposer cannot smuggle answers, derivations, or directives)"
        )

    for required in schema["required"]:
        if required not in arguments:
            errors.append(f"missing required property {required!r}")

    for name, spec in properties.items():
        if name not in arguments:
            continue
        value = arguments[name]
        expected = _SUPPORTED_TYPES[spec["type"]]
        # bool is an int subclass; an exact-type check keeps booleans out of
        # string seats and vice versa.
        if type(value) is not expected:
            errors.append(f"property {name!r} must be {spec['type']}")
            continue
        if isinstance(value, str):
            if "minLength" in spec and len(value) < spec["minLength"]:
                errors.append(f"property {name!r} shorter than {spec['minLength']}")
            if "maxLength" in spec and len(value) > spec["maxLength"]:
                errors.append(f"property {name!r} longer than {spec['maxLength']}")
            if "enum" in spec and value not in spec["enum"]:
                errors.append(f"property {name!r} must be one of {spec['enum']}")
            if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
                errors.append(f"property {name!r} does not match {spec['pattern']!r}")

    return tuple(errors)


__all__ = ["TOOL_SCHEMA_PATH", "load_tool_schema", "validate_payload"]
