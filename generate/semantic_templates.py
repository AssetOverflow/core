"""Intent-aware semantic templates for the realizer.

Maps (IntentTag, relation_predicate) pairs to deterministic surface
templates that use the seed pack's relation predicates (defines, means,
grounds, supports, contrasts_with, corrects).

Design constraints:
  - No LLM fallback
  - No random template selection
  - Deterministic: same (intent, predicate, subject, object) -> same surface
  - Uses seed pack vocabulary directly
"""

from __future__ import annotations

from generate.intent import IntentTag


_INTENT_TEMPLATES: dict[IntentTag, str] = {
    IntentTag.DEFINITION: "{subject} is defined as {obj}",
    IntentTag.CAUSE: "{subject} is grounded in {obj}",
    IntentTag.PROCEDURE: "first, {obj}; then, {subject} follows",
    IntentTag.COMPARISON: "{subject} and {secondary} are distinguished: {subject} {predicate_h} {secondary}",
    IntentTag.CORRECTION: "correction: {subject} {predicate_h} {obj}",
    IntentTag.RECALL: "recalling {subject}: {obj}",
    IntentTag.VERIFICATION: "{subject} is verified: {obj}",
    IntentTag.UNKNOWN: "{subject} {predicate_h} {obj}",
}

_PREDICATE_HUMANIZE: dict[str, str] = {
    "is_defined_as": "is defined as",
    "is_caused_by": "is caused by",
    "has_steps": "has the following steps",
    "contrasts_with": "contrasts with",
    "corrects": "corrects",
    "recalls": "recalls",
    "is_verified_as": "is verified as",
    "addresses": "addresses",
    "defines": "defines",
    "means": "means",
    "grounds": "grounds",
    "supports": "supports",
    "causes": "causes",
    "reveals": "reveals",
    "precedes": "precedes",
    "follows": "follows",
    "belongs_to": "belongs to",
    "answers": "answers",
    "is_grounded_in": "is grounded in",
    "is_distinguished_from": "is distinguished from",
    "implies": "implies",
    "entails": "entails",
    "requires": "requires",
    "verifies": "verifies",
    "evidences": "evidences",
    "orders": "orders",
}


def humanize_predicate(predicate: str) -> str:
    return _PREDICATE_HUMANIZE.get(predicate, predicate.replace("_", " "))


def render_semantic(
    intent: IntentTag,
    subject: str,
    predicate: str,
    obj: str,
    secondary: str | None = None,
) -> str:
    """Render a semantic surface from intent, subject, predicate, and object."""
    template = _INTENT_TEMPLATES.get(intent, _INTENT_TEMPLATES[IntentTag.UNKNOWN])
    predicate_h = humanize_predicate(predicate)
    obj_display = obj if obj not in ("<pending>", "<prior>") else "..."

    return template.format(
        subject=subject,
        predicate_h=predicate_h,
        obj=obj_display,
        secondary=secondary or obj_display,
    )
