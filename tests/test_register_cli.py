"""Register CLI — ``core chat --register <id>`` flag wiring
(ADR-0072 / Plan Phase R5).
"""

from __future__ import annotations

import argparse

import pytest

from core.cli import _runtime_config_from_args
from core.config import DEFAULT_CONFIG


def _namespace(**overrides) -> argparse.Namespace:
    """Build a Namespace shaped like ``cmd_chat``'s args, allowing
    targeted overrides for register / identity."""
    defaults = dict(
        output_language=DEFAULT_CONFIG.output_language,
        frame_pack=None,
        pack=None,
        max_tokens=DEFAULT_CONFIG.max_tokens,
        no_cross_language_recall=False,
        allow_cross_language_generation=False,
        vault_reproject_interval=DEFAULT_CONFIG.vault_reproject_interval,
        no_salience=False,
        salience_top_k=DEFAULT_CONFIG.salience_top_k,
        inhibition_threshold=DEFAULT_CONFIG.inhibition_threshold,
        inner_loop_admissibility=False,
        admissibility_threshold=0.0,
        identity="",
        register=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_runtime_config_default_register_is_none():
    """No --register on CLI ⇒ register_pack_id is None ⇒ unregistered."""
    cfg = _runtime_config_from_args(_namespace())
    assert cfg.register_pack_id is None


def test_runtime_config_threads_register_flag():
    """--register convivial_v1 ⇒ RuntimeConfig.register_pack_id set."""
    cfg = _runtime_config_from_args(_namespace(register="convivial_v1"))
    assert cfg.register_pack_id == "convivial_v1"


def test_runtime_config_empty_register_treated_as_none():
    """Empty-string --register (treated as unset) ⇒ None."""
    cfg = _runtime_config_from_args(_namespace(register=""))
    assert cfg.register_pack_id is None


def test_runtime_config_register_pack_id_threads_into_runtime():
    """Loading the runtime with a ratified register id wires
    ChatRuntime.register_pack to a non-unregistered pack."""
    from chat.runtime import ChatRuntime

    cfg = _runtime_config_from_args(_namespace(register="convivial_v1"))
    rt = ChatRuntime(config=cfg)
    assert rt.register_pack_id == "convivial_v1"
    assert rt.register_pack.register_id == "convivial_v1"
    assert not rt.register_pack.is_unregistered()


def test_runtime_config_unratified_register_id_fails_fast():
    """An unratified / non-existent register id ⇒ RegisterPackError at
    ChatRuntime init, not at first turn."""
    from chat.runtime import ChatRuntime
    from packs.register.loader import RegisterPackError

    cfg = _runtime_config_from_args(_namespace(register="bogus_v999"))
    with pytest.raises(RegisterPackError):
        ChatRuntime(config=cfg)


def test_chat_parser_accepts_register_flag():
    """``core chat --register convivial_v1`` parses cleanly."""
    from core.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["chat", "--register", "convivial_v1"])
    assert ns.register == "convivial_v1"


def test_chat_parser_register_defaults_none():
    from core.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["chat"])
    assert ns.register is None
