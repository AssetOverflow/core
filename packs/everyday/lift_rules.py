"""
Lift rules for packs/everyday.

Each rule maps a resolved sense (field_target) to a field vector slot.
The lift operation is deterministic: same input always yields same vector.
Rules are applied in priority order; first match wins per lemma.

Mirrors the structure of packs/en/lift_rules.py.
"""

from typing import Any


# Semantic family → top-level field namespace mapping.
# Used to validate that field_hooks are coherent with semantic_family.
FAMILY_NAMESPACE_MAP: dict[str, list[str]] = {
    "artifact":    ["artifact"],
    "substance":   ["substance"],
    "phenomenon":  ["phenomenon", "time", "perception"],
    "organism":    ["organism", "existence"],
    "body":        ["body"],
    "place":       ["place"],
    "agent":       ["agent", "logos", "existence"],
    "logos":       ["logos", "agent"],
    "relation":    ["relation"],
}


def apply_lift(record: dict[str, Any]) -> dict[str, Any]:
    """
    Lift an everyday lemma record into a semantic field vector.

    Returns a dict with:
      - status: "success" | "warning" | "error"
      - vector: list of activated field hooks (validated)
      - warnings: list of warning strings (may be empty)
    """
    warnings: list[str] = []
    hooks: list[str] = record.get("field_hooks", [])
    family: str = record.get("semantic_family", "")
    lemma_id: str = record.get("lemma_id", "?")

    if not hooks:
        return {"status": "error", "vector": [], "warnings": [f"{lemma_id}: no field_hooks defined"]}

    allowed_namespaces = FAMILY_NAMESPACE_MAP.get(family, [])
    validated: list[str] = []

    for hook in hooks:
        top_ns = hook.split(".")[0]
        if allowed_namespaces and top_ns not in allowed_namespaces:
            warnings.append(
                f"{lemma_id}: hook '{hook}' namespace '{top_ns}' not in allowed namespaces "
                f"for family '{family}': {allowed_namespaces}"
            )
        validated.append(hook)

    status = "warning" if warnings else "success"
    return {"status": status, "vector": validated, "warnings": warnings}


def validate_family_hook_coherence(record: dict[str, Any]) -> bool:
    """Quick boolean check: are all hooks coherent with the semantic family?"""
    result = apply_lift(record)
    return result["status"] != "error" and not result["warnings"]
