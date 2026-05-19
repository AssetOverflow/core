"""RuntimeConfig.register_pack_id — field shape and runtime-init behaviour
(ADR-0069 Phase R2).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import DEFAULT_REGISTER_PACK, RuntimeConfig
from packs.register.loader import RegisterPack, RegisterPackError


def test_default_is_none():
    config = RuntimeConfig()
    assert config.register_pack_id is None


def test_default_register_pack_constant():
    assert DEFAULT_REGISTER_PACK == "default_neutral_v1"


def test_config_is_frozen():
    config = RuntimeConfig()
    with pytest.raises(Exception):
        config.register_pack_id = "default_neutral_v1"  # type: ignore[misc]


def test_runtime_with_none_uses_unregistered_sentinel():
    runtime = ChatRuntime(config=RuntimeConfig(register_pack_id=None))
    assert isinstance(runtime.register_pack, RegisterPack)
    assert runtime.register_pack.is_unregistered()
    assert runtime.register_pack.is_null_register()
    assert runtime.register_pack_id is None


def test_runtime_with_default_neutral_loads_pack():
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="default_neutral_v1"),
    )
    assert runtime.register_pack.register_id == "default_neutral_v1"
    assert runtime.register_pack.is_null_register()
    assert not runtime.register_pack.is_unregistered()
    assert runtime.register_pack_id == "default_neutral_v1"


def test_runtime_init_rejects_invalid_register_id():
    """Invalid register_pack_id fails fast at __init__, not at first turn."""
    with pytest.raises(RegisterPackError):
        ChatRuntime(
            config=RuntimeConfig(register_pack_id="no_such_pack_v999"),
        )


def test_runtime_init_rejects_path_traversal():
    with pytest.raises(RegisterPackError):
        ChatRuntime(
            config=RuntimeConfig(register_pack_id="../etc/passwd"),
        )


def test_runtime_init_rejects_empty_string():
    """Empty string is explicitly invalid (no auto-resolution to default)."""
    with pytest.raises(RegisterPackError):
        ChatRuntime(config=RuntimeConfig(register_pack_id=""))
