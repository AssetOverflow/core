"""Local deterministic authority substrate for the tool-authority demo.

The proposer contributes a typed request only.  CORE owns validation, envelope
evaluation, and trace generation.  Even an ``authorized`` decision is inert:
the returned ``licensed_action`` is a data artifact, not an execution path.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Final

TOOL_NAME: Final[str] = "core.tool_authority.review"
_HERE: Final[Path] = Path(__file__).resolve().parent
SCHEMA_PATH: Final[Path] = _HERE / "schema.json"

_SUPPORTED_SCHEMA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "enum",
        "pattern",
        "minLength",
        "maxLength",
        "items",
    }
)
_SCALAR_TYPES: Final[dict[str, type]] = {"string": str, "boolean": bool}
_ROOT_AUTHORITY: Final[str] = "demos.claude_tool_authority.authority.validate_payload"
_DECIDE_AUTHORITY: Final[str] = "demos.claude_tool_authority.authority.evaluate_authority"
_ENVELOPE_AUTHORITY: Final[str] = "demo_tool_authority_envelope(local-v1)"
_LICENSE_AUTHORITY: Final[str] = "demos.claude_tool_authority.authority.build_license"

_ALLOWED_NOTE_PREFIX: Final[str] = "workspace/demo_notes/"
_ALLOWED_NOTE_ROOT: Final[PurePosixPath] = PurePosixPath("workspace/demo_notes")
_PROTECTED_PATH_PREFIXES: Final[tuple[str, ...]] = (
    ".git/",
    "chat/",
    "core/",
    "docs/",
    "tests/",
)


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _clip(value: object) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= 80 else rendered[:79] + "…"


def _ensure_supported_schema(spec: dict[str, Any], *, path: str) -> None:
    unsupported = set(spec) - _SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise ValueError(
            f"{path} uses unsupported schema keywords {sorted(unsupported)}; "
            "extend the validator before extending the schema"
        )
    schema_type = spec.get("type")
    if isinstance(schema_type, list):
        return
    if schema_type == "object":
        for name, child in spec.get("properties", {}).items():
            _ensure_supported_schema(child, path=f"{path}.{name}")
    elif schema_type == "array":
        _ensure_supported_schema(spec["items"], path=f"{path}[]")
    elif schema_type not in _SCALAR_TYPES:
        raise ValueError(f"{path} has unsupported schema type {schema_type!r}")


@lru_cache(maxsize=1)
def _input_schema() -> dict[str, Any]:
    schema = load_schema()["inputSchema"]
    _ensure_supported_schema(schema, path="inputSchema")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("inputSchema must be a closed object")
    return schema


def _validate(spec: dict[str, Any], value: Any, *, path: str, errors: list[str]) -> None:
    schema_type = spec["type"]
    if isinstance(schema_type, list):
        allowed = []
        for entry in schema_type:
            if entry == "null" and value is None:
                return
            allowed.append(entry)
        if value is None:
            errors.append(f"{path} must be one of {allowed}")
            return
        non_null = [entry for entry in schema_type if entry != "null"]
        if len(non_null) != 1:
            raise ValueError(f"{path} uses unsupported union type {schema_type!r}")
        schema_type = non_null[0]

    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path} must be object")
            return
        props = spec.get("properties", {})
        if spec.get("additionalProperties") is False:
            for unknown in sorted(set(value) - set(props)):
                errors.append(
                    f"{path} unexpected property {_clip(unknown)} "
                    "(additionalProperties is false)"
                )
        for required in spec.get("required", []):
            if required not in value:
                errors.append(f"{path} missing required property {required!r}")
        for name, child in props.items():
            if name in value:
                _validate(child, value[name], path=f"{path}.{name}", errors=errors)
        return

    if schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path} must be array")
            return
        for index, item in enumerate(value):
            _validate(spec["items"], item, path=f"{path}[{index}]", errors=errors)
        return

    expected = _SCALAR_TYPES[schema_type]
    if type(value) is not expected:
        errors.append(f"{path} must be {schema_type}")
        return
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            errors.append(f"{path} shorter than {spec['minLength']}")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            errors.append(f"{path} longer than {spec['maxLength']}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{path} must be one of {spec['enum']}")
        if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
            errors.append(f"{path} does not match {spec['pattern']!r}")
    elif "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path} must be one of {spec['enum']}")


def validate_payload(payload: Any) -> tuple[str, ...]:
    errors: list[str] = []
    _validate(_input_schema(), payload, path="payload", errors=errors)
    return tuple(errors)


def _safe_request_id(payload: Any) -> str | None:
    request_id = payload.get("request_id") if isinstance(payload, dict) else None
    if not isinstance(request_id, str):
        return None
    pattern = _input_schema()["properties"]["request_id"]["pattern"]
    return request_id if re.fullmatch(pattern, request_id) else None


def _safe_scenario_id(payload: Any) -> str | None:
    scenario_id = payload.get("scenario_id") if isinstance(payload, dict) else None
    if not isinstance(scenario_id, str):
        return None
    pattern = _input_schema()["properties"]["scenario_id"]["pattern"]
    return scenario_id if re.fullmatch(pattern, scenario_id) else None


def _response_hash(response: dict[str, Any]) -> str:
    body = dict(response)
    body.pop("trace_hash", None)
    return _hash_text(_canonical(body))


def _finalize(response: dict[str, Any]) -> dict[str, Any]:
    response["trace_hash"] = _response_hash(response)
    return response


def _invalid_response(payload: Any, errors: tuple[str, ...]) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "invalid",
            "request_id": _safe_request_id(payload),
            "scenario_id": _safe_scenario_id(payload),
            "authority_path": [_ROOT_AUTHORITY],
            "decision_reason": "invalid_payload",
            "trace_summary": {
                "authority_evaluated": False,
                "validation_errors": list(errors),
                "proposer_trace_hash_ignored": bool(
                    isinstance(payload, dict)
                    and isinstance(payload.get("proposer"), dict)
                    and "trace_hash" in payload["proposer"]
                ),
            },
            "invalid_reason": "; ".join(errors),
        }
    )


def _action_fingerprint(payload: dict[str, Any]) -> str:
    action = {
        "action_request": payload["action_request"],
        "proposer": {
            "lane": payload["proposer"]["lane"],
            "model_family": payload["proposer"]["model_family"],
            "proposal_id": payload["proposer"]["proposal_id"],
        },
        "request_id": payload["request_id"],
        "scenario_id": payload["scenario_id"],
    }
    return _hash_text(_canonical(action))


def _protected_target(path: str | None) -> bool:
    if path is None:
        return False
    return any(path.startswith(prefix) for prefix in _PROTECTED_PATH_PREFIXES)


def _normalize_note_target_path(raw_path: Any) -> tuple[str | None, str | None]:
    """Canonicalize demo note paths under deterministic POSIX semantics.

    The input is JSON/demo artifact data, not a host filesystem path.  Be
    conservative: any absolute path, empty path, or ``..`` segment is refused.
    """
    if not isinstance(raw_path, str):
        return None, "malformed_target_path"
    if raw_path == "":
        return None, "empty_target_path"

    normalized = PurePosixPath(raw_path)
    if normalized.is_absolute():
        return None, "absolute_target_path"

    parts = normalized.parts
    if not parts:
        return None, "malformed_target_path"
    if any(part == ".." for part in parts):
        return None, "path_traversal_detected"

    cleaned_parts = tuple(part for part in parts if part not in ("", "."))
    if not cleaned_parts:
        return None, "malformed_target_path"

    cleaned = PurePosixPath(*cleaned_parts)
    cleaned_text = cleaned.as_posix()
    if _protected_target(cleaned_text):
        return None, "protected_path"
    if not cleaned_text.startswith(_ALLOWED_NOTE_PREFIX):
        return None, "outside_authority_envelope"
    if cleaned == _ALLOWED_NOTE_ROOT:
        return None, "malformed_target_path"
    if not cleaned.is_relative_to(_ALLOWED_NOTE_ROOT):
        return None, "outside_authority_envelope"
    return cleaned_text, None


def _normalized_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Copy and canonicalize caller payload before authority evaluation."""
    normalized = copy.deepcopy(payload)
    action_request = normalized["action_request"]
    if action_request["action_type"] != "write_local_note":
        return normalized, None

    target = action_request["target"]
    normalized_path, refusal_reason = _normalize_note_target_path(target.get("path"))
    if refusal_reason is not None:
        return normalized, refusal_reason
    assert normalized_path is not None
    target["path"] = normalized_path
    return normalized, None


def build_license(payload: dict[str, Any]) -> dict[str, Any]:
    target_path = payload["action_request"]["target"]["path"]
    content = payload["action_request"]["payload"]["content"]
    return {
        "action_type": "write_local_note",
        "target_path": target_path,
        "content_sha256": _hash_text(content),
        "authority_scope": "demo.local.low_risk_workspace_note",
        "effect": "inert_license_only",
    }


def evaluate_authority(payload: dict[str, Any]) -> dict[str, Any]:
    action_request = payload["action_request"]
    action_type = action_request["action_type"]
    target = action_request["target"]
    payload_body = action_request["payload"]
    authorities = [_ROOT_AUTHORITY, _DECIDE_AUTHORITY, _ENVELOPE_AUTHORITY]
    trace_summary = {
        "authority_evaluated": True,
        "envelope_version": "local-v1",
        "action_fingerprint": _action_fingerprint(payload),
        "proposer_trace_hash_ignored": "trace_hash" in payload["proposer"],
        "execution_performed": False,
    }

    if action_type == "write_local_note":
        target_path = target.get("path")
        if (
            target.get("kind") == "workspace_path"
            and isinstance(target_path, str)
            and target_path.startswith(_ALLOWED_NOTE_PREFIX)
            and not _protected_target(target_path)
            and "title" in payload_body
            and "content" in payload_body
        ):
            authorities.append(_LICENSE_AUTHORITY)
            return _finalize(
                {
                    "tool": TOOL_NAME,
                    "status": "authorized",
                    "request_id": payload["request_id"],
                    "scenario_id": payload["scenario_id"],
                    "authority_path": authorities,
                    "decision_reason": "inside_low_risk_envelope",
                    "trace_summary": trace_summary,
                    "licensed_action": build_license(payload),
                }
            )

    if action_type == "prepare_email_draft":
        confirmation = action_request.get("confirmation")
        if not (isinstance(confirmation, dict) and confirmation.get("user_confirmed") is True):
            return _finalize(
                {
                    "tool": TOOL_NAME,
                    "status": "ask",
                    "request_id": payload["request_id"],
                    "scenario_id": payload["scenario_id"],
                    "authority_path": authorities,
                    "decision_reason": "missing_explicit_confirmation",
                    "trace_summary": trace_summary,
                    "question": (
                        "CORE requires explicit user confirmation before licensing "
                        "an external email draft. Confirm the recipient and intent."
                    ),
                }
            )

    refusal_reason = "outside_authority_envelope"
    if action_type == "shell_command":
        refusal_reason = "unauthorized_tool"
    elif action_type == "write_local_note" and _protected_target(target.get("path")):
        refusal_reason = "protected_path"
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "refused",
            "request_id": payload["request_id"],
            "scenario_id": payload["scenario_id"],
            "authority_path": authorities,
            "decision_reason": refusal_reason,
            "trace_summary": trace_summary,
            "refusal_reason": refusal_reason,
        }
    )


def run_authority(payload: Any) -> dict[str, Any]:
    errors = validate_payload(payload)
    if errors:
        return _invalid_response(payload, errors)
    assert isinstance(payload, dict)
    normalized_payload, refusal_reason = _normalized_payload(payload)
    if refusal_reason is not None:
        return _finalize(
            {
                "tool": TOOL_NAME,
                "status": "refused",
                "request_id": normalized_payload["request_id"],
                "scenario_id": normalized_payload["scenario_id"],
                "authority_path": [_ROOT_AUTHORITY, _DECIDE_AUTHORITY, _ENVELOPE_AUTHORITY],
                "decision_reason": refusal_reason,
                "trace_summary": {
                    "authority_evaluated": True,
                    "envelope_version": "local-v1",
                    "action_fingerprint": _action_fingerprint(normalized_payload),
                    "proposer_trace_hash_ignored": "trace_hash"
                    in normalized_payload["proposer"],
                    "execution_performed": False,
                    "path_normalized": False,
                },
                "refusal_reason": refusal_reason,
            }
        )
    return evaluate_authority(normalized_payload)


__all__ = [
    "SCHEMA_PATH",
    "TOOL_NAME",
    "build_license",
    "evaluate_authority",
    "load_schema",
    "run_authority",
    "validate_payload",
]
