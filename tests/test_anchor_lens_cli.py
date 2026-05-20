"""Anchor-lens CLI — ``core chat --anchor-lens <id>`` flag wiring
(ADR-0073d / L1.4).
"""

from __future__ import annotations

import argparse

import pytest

from core.cli import _runtime_config_from_args
from core.config import DEFAULT_CONFIG


def _namespace(**overrides) -> argparse.Namespace:
    """Build a Namespace shaped like cmd_chat's args."""
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
        anchor_lens=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_runtime_config_default_anchor_lens_is_none():
    cfg = _runtime_config_from_args(_namespace())
    assert cfg.anchor_lens_id is None


def test_runtime_config_threads_anchor_lens_flag():
    cfg = _runtime_config_from_args(_namespace(anchor_lens="grc_logos_v1"))
    assert cfg.anchor_lens_id == "grc_logos_v1"


def test_runtime_config_empty_anchor_lens_treated_as_none():
    cfg = _runtime_config_from_args(_namespace(anchor_lens=""))
    assert cfg.anchor_lens_id is None


def test_runtime_config_anchor_lens_threads_into_runtime():
    from chat.runtime import ChatRuntime

    cfg = _runtime_config_from_args(_namespace(anchor_lens="grc_logos_v1"))
    rt = ChatRuntime(config=cfg)
    assert rt.anchor_lens_id == "grc_logos_v1"
    assert rt.anchor_lens.lens_id == "grc_logos_v1"
    assert not rt.anchor_lens.is_unanchored()


def test_runtime_config_unratified_anchor_lens_id_fails_fast():
    from chat.runtime import ChatRuntime
    from packs.anchor_lens.loader import AnchorLensError

    cfg = _runtime_config_from_args(_namespace(anchor_lens="bogus_v999"))
    with pytest.raises(AnchorLensError):
        ChatRuntime(config=cfg)


def test_chat_parser_accepts_anchor_lens_flag():
    from core.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["chat", "--anchor-lens", "grc_logos_v1"])
    assert ns.anchor_lens == "grc_logos_v1"


def test_chat_parser_anchor_lens_defaults_none():
    from core.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["chat"])
    assert ns.anchor_lens is None


def test_chat_parser_accepts_anchor_lens_and_register_together():
    """Composition of orthogonal axes via the CLI."""
    from core.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args([
        "chat",
        "--register", "convivial_v1",
        "--anchor-lens", "grc_logos_v1",
    ])
    assert ns.register == "convivial_v1"
    assert ns.anchor_lens == "grc_logos_v1"
