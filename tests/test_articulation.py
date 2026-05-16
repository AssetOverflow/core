from __future__ import annotations

import re

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.articulation import realize

_GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
_HEBREW_RE = re.compile(r"[\u0590-\u05ff]")


def _is_english_surface(text: str) -> bool:
    return not _GREEK_RE.search(text) and not _HEBREW_RE.search(text)


def test_realize_english_surface_is_english_and_compact() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    response = runtime.chat("word beginning truth")
    plan = realize(response.proposition, runtime.session.vocab, "en")
    assert plan.subject
    assert plan.predicate
    assert _is_english_surface(plan.surface)
    assert len(plan.surface.split()) <= 6


def test_realize_greek_surface_uses_greek_script_and_compact() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="grc", frame_pack="grc"))
    response = runtime.chat("logos arche aletheia")
    plan = realize(response.proposition, runtime.session.vocab, "grc")
    assert plan.subject
    assert plan.predicate
    assert _GREEK_RE.search(plan.surface)
    assert not _HEBREW_RE.search(plan.surface)
    assert len(plan.surface.split()) <= 6


def test_realize_hebrew_surface_uses_hebrew_script_and_compact() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="he", frame_pack="he"))
    response = runtime.chat("dabar bereshit emet")
    plan = realize(response.proposition, runtime.session.vocab, "he")
    assert plan.subject
    assert plan.predicate
    assert _HEBREW_RE.search(plan.surface)
    assert not _GREEK_RE.search(plan.surface)
    assert len(plan.surface.split()) <= 6


def test_chat_surface_is_walk_surface() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    runtime.chat("word beginning truth")
    response = runtime.chat("word beginning truth")
    assert response.surface == response.walk_surface


def test_proposition_relation_norm_is_exposed() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    response = runtime.chat("word beginning truth")
    assert response.proposition.relation_norm >= 0.0
