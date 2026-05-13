from __future__ import annotations

import builtins

from probe import repl


def test_repl_exits_cleanly_on_stdin_eof(monkeypatch, capsys):
    inputs = iter(["light"])

    def fake_input(prompt: str) -> str:
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr(builtins, "input", fake_input)

    repl.main()

    out = capsys.readouterr().out
    assert "[field walk:" in out
    assert "light" in out
