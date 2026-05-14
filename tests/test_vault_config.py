from __future__ import annotations

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


def test_runtime_config_controls_vault_reproject_interval_and_store_count() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(vault_reproject_interval=5, output_language="en", frame_pack="en"))

    turns = 3
    for text in ("word beginning truth", "light truth word", "begin thought word"):
        runtime.chat(text)

    assert runtime.session.vault.reproject_interval == 5
    assert runtime.session.vault.store_count == turns * 3
    assert len(runtime.session.vault) == turns * 3
