"""Course YAML template registry.

A template renders a :class:`ValidatedTripleSet` into a canonical course
YAML body (a JSON-shaped dict of strings/lists/dicts — no floats).
Templates are deterministic: same input -> same output bytes.

Lookups are by ``template_id``.  Each template carries its own
``template_version``; bumping the version invalidates downstream
``course_sha256`` values, which is intentional.

Templates in this registry, by ordering-rule layer:

* ``definition`` — Layer 2.  Every relation is a definitional edge.
* ``composed_relation`` — Layer 4.  Chains are the unit of mastery.
* ``procedural`` — Layer 4.  Ordered state transitions.
* ``falsification`` — counter-example-driven; supports any layer.
* ``identity_anchor`` — Layer 1.  Identity axes and refusal probes.

See ``docs/teaching_order.md`` for the layer doctrine.
"""

from __future__ import annotations

from typing import Protocol

from formation.course import SubjectSpec, ValidatedTripleSet


class Template(Protocol):
    """Protocol implemented by every Course template."""

    template_id: str
    template_version: str

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        """Return a JSON-shaped course body (no floats; numerics as strings)."""
        ...


# (module_path, class_name) — kept as strings so we lazy-import.
_REGISTRY: dict[str, tuple[str, str]] = {
    "definition": ("formation.templates.definition", "DefinitionTemplate"),
    "composed_relation": (
        "formation.templates.composed_relation",
        "ComposedRelationTemplate",
    ),
    "procedural": ("formation.templates.procedural", "ProceduralTemplate"),
    "falsification": (
        "formation.templates.falsification",
        "FalsificationTemplate",
    ),
    "identity_anchor": (
        "formation.templates.identity_anchor",
        "IdentityAnchorTemplate",
    ),
}


def get_template(template_id: str) -> Template:
    """Return the template registered under ``template_id``.

    Raises ``KeyError`` if unknown.  The registry is lazily imported so
    template modules do not leak into the public package surface unless
    actually selected.
    """
    try:
        module_path, class_name = _REGISTRY[template_id]
    except KeyError as exc:
        raise KeyError(f"unknown template_id: {template_id!r}") from exc
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()  # type: ignore[no-any-return]


def registered_template_ids() -> tuple[str, ...]:
    """Sorted tuple of known template ids."""
    return tuple(sorted(_REGISTRY))


__all__ = ["Template", "get_template", "registered_template_ids"]
