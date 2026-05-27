"""ME-1 — case 0050 hazard pin for the currency-per-unit composition extension.

Mandatory: feeding case 0050's actual sentence shapes through the
extended matcher MUST NOT emit a ``composition_shape`` anchor.
Case 0050's text does not carry the buy-verb + count + $amount + each
shape, so the regex narrowness in
``_try_extract_currency_per_unit_composition_anchor`` refuses it.

See [[feedback-wrong-zero-hazard-case-0050]] — this is the canary that
prevents the matcher extension from drifting into ``wrong > 0``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from generate.recognizer_match import _match_rate_with_currency


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "currency_per_unit_composition",
    "observed_currency_symbols": ["$"],
    "observed_per_units": ["each", "apiece"],
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    while here.parent != here and not (here / "pyproject.toml").exists():
        here = here.parent
    return here


def _case_0050_text() -> str | None:
    cases_path = (
        _repo_root() / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"
    )
    if not cases_path.exists():
        return None
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("case_id", "").endswith("-0050"):
            return rec.get("question") or rec.get("text") or ""
    return None


def test_case_0050_does_not_emit_composition_shape():
    text = _case_0050_text()
    if text is None:
        # Test corpus missing in this repo state; the parametrized
        # hazard pin in test_consumption_case_0050_hazard_pin.py still
        # guards the canonical pack's allowlist enforcement.
        import pytest

        pytest.skip("train_sample case_0050 not present")
        return
    assert text, "case 0050 text must be non-empty"
    # Run the matcher against each sentence; assert none publishes
    # composition_shape.
    for sentence in text.split("."):
        if not sentence.strip():
            continue
        result = _match_rate_with_currency(sentence.strip() + ".", _SPEC)
        if result is None:
            continue
        anchors, _intent = result
        for anchor in anchors:
            assert "composition_shape" not in anchor, (
                f"Case 0050 sentence produced composition_shape anchor: {anchor!r}"
            )


def test_case_0050_recognizer_match_module_imports_no_solver_mutation():
    """Defense in depth: the matcher module does not import solver internals."""
    import ast

    here = _repo_root() / "generate" / "recognizer_match.py"
    tree = ast.parse(here.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "algebra.",
        "field.",
        "chat.",
    )
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    taints = {i for i in imports if any(i.startswith(p) for p in forbidden_prefixes)}
    assert taints == set(), f"recognizer_match imports forbidden modules: {taints}"
