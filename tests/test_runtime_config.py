from __future__ import annotations

import re

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig

_GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
_HEBREW_RE = re.compile(r"[\u0590-\u05ff]")


def _is_english_surface(text: str) -> bool:
    return not _GREEK_RE.search(text) and not _HEBREW_RE.search(text)


def test_default_runtime_emits_english_surface() -> None:
    runtime = ChatRuntime()
    response = runtime.chat("word beginning truth")
    assert response.output_language == "en"
    assert response.frame_pack == "en"
    assert _is_english_surface(response.surface)


def test_trilanguage_mounted_runtime_still_emits_english_surface_by_default() -> None:
    runtime = ChatRuntime(
        config=RuntimeConfig(
            input_packs=("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1"),
            output_language="en",
            frame_pack="en",
        )
    )
    response = runtime.chat("word beginning truth")
    assert _is_english_surface(response.surface)
    assert response.proposition.frame_id.startswith("en:")


def test_greek_output_language_emits_greek_surface() -> None:
    runtime = ChatRuntime(
        config=RuntimeConfig(
            input_packs=("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1"),
            output_language="grc",
            frame_pack="grc",
        )
    )
    response = runtime.chat("logos arche aletheia")
    assert response.output_language == "grc"
    assert response.frame_pack == "grc"
    assert _GREEK_RE.search(response.surface)
    assert response.proposition.frame_id.startswith(("grc:", "el:"))


def test_chat_response_surface_uses_articulation_plan() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    response = runtime.chat("word beginning truth")
    assert response.surface == response.articulation.surface
