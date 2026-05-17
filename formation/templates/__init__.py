"""Course YAML template registry.

A template renders a :class:`ValidatedTripleSet` into the canonical
five-phase course YAML body (a JSON-shaped dict of strings/lists/dicts —
no floats).  Templates are deterministic: same input -> same output bytes.

Lookups are by ``template_id``.  Each template carries its own
``template_version``; bumping the version invalidates downstream
``course_sha256`` values, which is intentional.
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


def get_template(template_id: str) -> Template:
    """Return the template registered under ``template_id``.

    Raises ``KeyError`` if unknown.  The registry is lazily imported to keep
    template modules from leaking into the public package surface.
    """
    if template_id == "definition":
        from formation.templates.definition import DefinitionTemplate

        return DefinitionTemplate()
    raise KeyError(f"unknown template_id: {template_id!r}")


__all__ = ["Template", "get_template"]
