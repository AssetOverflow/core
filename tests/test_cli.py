from __future__ import annotations

import pytest

from core.cli import build_parser, main


def test_top_level_help_exits_without_runtime_import(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["-h"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "CORE versor engine command suite" in out
    assert "core trace" in out


def test_trace_help_exits_without_runtime_import(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["trace", "-h"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "trace one chat turn" in out
    assert "--pack" in out
    assert "--json" in out


def test_main_without_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "CORE versor engine command suite" in out
    assert "doctor" in out


def test_trace_requires_text_before_runtime_initialization(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["trace"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "trace requires input text" in err


def test_doctor_imports_runtime_support_modules(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "OK   alignment" in out
    assert "OK   morphology" in out
    assert "OK   sensorium" in out


def test_trace_formats_real_runtime_payload(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", "--pack", "en_minimal_v1", "word", "beginning", "truth"]) == 0
    out = capsys.readouterr().out
    assert "input          : word beginning truth" in out
    assert "proposition" in out
    assert "subject" in out
    assert "predicate" in out


def test_trace_json_formats_real_runtime_payload(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", "--pack", "en_minimal_v1", "--json", "word", "beginning", "truth"]) == 0
    out = capsys.readouterr().out
    assert '"input": "word beginning truth"' in out
    assert '"proposition"' in out
    assert '"subject"' in out
    assert '"predicate"' in out
