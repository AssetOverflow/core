"""Regression test for ChatRuntime.__init__ config-flag passthrough.

Prior to fix d-2026-05-19, ``ChatRuntime.__init__`` manually reconstructed
``RuntimeConfig`` field-by-field whenever ``pack_id`` or ``frame_pack``
was supplied.  The manual list was incomplete: newer flags
(``identity_pack``, ``ethics_pack``, ``forward_graph_constraint``,
``composed_surface``, ``thread_anaphora``) were silently dropped, so a
caller like

    ChatRuntime(pack_id="x", config=RuntimeConfig(composed_surface=True))

would lose ``composed_surface=True`` without warning.

The fix uses ``dataclasses.replace`` so every field on the dataclass
survives by construction.  This test pins that contract: pass a config
with all current flags set to *non-default* values, instantiate
``ChatRuntime`` with a ``pack_id`` override, and assert every flag
survived on ``runtime.config``.

If a new flag is added to ``RuntimeConfig``, this test should catch any
future drift on the override path provided the default differs from
the test value (the assertion compares post-init value against the
explicitly-set value, not against the default).
"""

from __future__ import annotations

from dataclasses import fields

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


def test_all_runtime_config_flags_survive_pack_id_override() -> None:
    custom = RuntimeConfig(
        input_packs=("en_minimal_v1",),
        output_language="en",
        frame_pack="en",
        max_tokens=17,                  # non-default
        allow_cross_language_recall=False,
        allow_cross_language_generation=True,
        vault_reproject_interval=99,
        use_salience=False,
        salience_top_k=8,
        inhibition_threshold=0.42,
        inner_loop_admissibility=True,
        admissibility_threshold=0.13,
        admissibility_mode="margin",
        admissibility_margin=0.7,
        identity_pack="precision_first_v1",
        ethics_pack="default_general_ethics_v1",
        forward_graph_constraint=True,
        composed_surface=True,
        thread_anaphora=True,
    )

    runtime = ChatRuntime(pack_id="en_minimal_v1", config=custom)

    for field in fields(RuntimeConfig):
        if field.name == "input_packs":
            # The pack_id override deliberately rewrites input_packs;
            # other fields must survive verbatim.
            continue
        expected = getattr(custom, field.name)
        actual = getattr(runtime.config, field.name)
        assert actual == expected, (
            f"RuntimeConfig.{field.name} did not survive pack_id override: "
            f"expected {expected!r}, got {actual!r}"
        )


def test_all_runtime_config_flags_survive_frame_pack_override() -> None:
    custom = RuntimeConfig(
        composed_surface=True,
        thread_anaphora=True,
        forward_graph_constraint=True,
        identity_pack="precision_first_v1",
        ethics_pack="default_general_ethics_v1",
    )

    runtime = ChatRuntime(frame_pack="en", config=custom)

    assert runtime.config.composed_surface is True
    assert runtime.config.thread_anaphora is True
    assert runtime.config.forward_graph_constraint is True
    assert runtime.config.identity_pack == "precision_first_v1"
    assert runtime.config.ethics_pack == "default_general_ethics_v1"


def test_no_override_path_passes_config_through_unchanged() -> None:
    """When neither pack_id nor frame_pack is supplied, the user's
    config is preserved verbatim (it is the same object identity)."""
    custom = RuntimeConfig(composed_surface=True)
    runtime = ChatRuntime(config=custom)
    # Same object: no reconstruction happened.
    assert runtime.config is custom
    assert runtime.config.composed_surface is True


def test_chat_method_exists() -> None:
    """Smoke: the user-facing public methods are present."""
    rt = ChatRuntime()
    assert callable(getattr(rt, "chat", None))
    assert callable(getattr(rt, "respond", None))
    assert callable(getattr(rt, "achat", None))
    assert callable(getattr(rt, "arespond", None))
