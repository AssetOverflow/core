"""
Validators for packs/everyday.

Ensures every everyday lemma record satisfies:
  1. Required fields are present and non-null.
  2. Semantic family is from the allowed set for this domain.
  3. Field hooks follow the dot-namespaced format.
  4. readback_priority is 1 or 2.
  5. morph_class is a known class.

Mirrors the structure of packs/en/validators.py.
"""

from typing import Any

ALLOWED_FAMILIES = {
    "artifact", "substance", "phenomenon",
    "organism", "body", "place", "agent", "logos", "relation",
}

ALLOWED_MORPH_CLASSES = {
    "regular", "irregular", "mass", "proper", "copular",
}

REQUIRED_LEMMA_FIELDS = {
    "lemma_id", "language", "script_form",
    "gloss_seed", "pos", "morph_class",
    "semantic_family", "field_hooks", "readback_priority",
}


def validate_lemma(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a single lemma record.
    Returns (is_valid, list_of_error_strings).
    """
    errors: list[str] = []
    lemma_id = record.get("lemma_id", "<unknown>")

    # 1. Required fields
    for field in REQUIRED_LEMMA_FIELDS:
        if field not in record or record[field] is None:
            errors.append(f"{lemma_id}: missing required field '{field}'")

    # 2. Semantic family
    family = record.get("semantic_family", "")
    if family not in ALLOWED_FAMILIES:
        errors.append(f"{lemma_id}: unknown semantic_family '{family}'")

    # 3. Field hooks format
    hooks = record.get("field_hooks", [])
    if not isinstance(hooks, list) or len(hooks) == 0:
        errors.append(f"{lemma_id}: field_hooks must be a non-empty list")
    else:
        for hook in hooks:
            if "." not in hook:
                errors.append(f"{lemma_id}: field_hook '{hook}' must be dot-namespaced")

    # 4. readback_priority
    rp = record.get("readback_priority")
    if rp not in (1, 2):
        errors.append(f"{lemma_id}: readback_priority must be 1 or 2, got {rp!r}")

    # 5. morph_class
    mc = record.get("morph_class", "")
    if mc not in ALLOWED_MORPH_CLASSES:
        errors.append(f"{lemma_id}: unknown morph_class '{mc}'")

    # 6. lemma_id namespace
    if not str(lemma_id).startswith("everyday:"):
        errors.append(f"{lemma_id}: lemma_id must start with 'everyday:'")

    return (len(errors) == 0, errors)


def validate_all(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a list of lemma records. Returns a summary dict."""
    total = len(records)
    passed = 0
    failed = 0
    all_errors: list[str] = []

    for record in records:
        ok, errs = validate_lemma(record)
        if ok:
            passed += 1
        else:
            failed += 1
            all_errors.extend(errs)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": all_errors,
    }
