"""CLI tests for the ADR-0024 chain demo subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import cli


class TestADR0024SuiteAliases:
    """Layer 1: pin the new suite aliases so they don't drift."""

    @pytest.mark.parametrize(
        "suite,must_contain",
        [
            ("refusal", "tests/test_refusal_contract.py"),
            ("margin", "tests/test_margin_admissibility.py"),
            ("rotor", "tests/test_rotor_admissibility.py"),
            ("inner-loop", "tests/test_inner_loop_admissibility.py"),
            ("phase5", "tests/test_phase5_corpus.py"),
            ("phase6", "tests/test_phase6_demo.py"),
        ],
    )
    def test_suite_alias_resolves(
        self, monkeypatch, suite: str, must_contain: str
    ) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_run(*args: str, check: bool = False, cwd=None) -> int:
            calls.append(args)
            return 0

        monkeypatch.setattr(cli, "_run", fake_run)
        rc = cli.main(["test", "--suite", suite, "-q"])
        assert rc == 0
        assert calls, f"no _run invocation for suite {suite!r}"
        assert must_contain in calls[0]

    def test_adr_0024_alias_runs_full_chain(self, monkeypatch) -> None:
        calls: list[tuple[str, ...]] = []
        monkeypatch.setattr(
            cli, "_run", lambda *a, **kw: (calls.append(a) or 0)
        )
        rc = cli.main(["test", "--suite", "adr-0024", "-q"])
        assert rc == 0
        command = calls[0]
        # All six Phase 2-6 contract files must be present.
        for path in (
            "tests/test_refusal_contract.py",
            "tests/test_margin_admissibility.py",
            "tests/test_rotor_admissibility.py",
            "tests/test_phase5_corpus.py",
            "tests/test_phase6_demo.py",
        ):
            assert path in command, f"missing {path} in adr-0024 expansion"

    def test_list_suites_includes_new_aliases(self, capsys) -> None:
        rc = cli.main(["test", "--list-suites"])
        captured = capsys.readouterr()
        assert rc == 0
        out = captured.out.splitlines()
        for alias in (
            "adr-0024",
            "refusal",
            "margin",
            "rotor",
            "inner-loop",
            "phase5",
            "phase6",
        ):
            assert alias in out, f"alias {alias!r} missing from --list-suites"


class TestDemoSubcommand:
    """Layer 2: pin the `core demo` subcommand surface."""

    def test_demo_help_lists_targets(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            cli.main(["demo", "--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        for target in ("phase5", "phase6", "all", "list-results"):
            assert target in captured.out

    def test_demo_phase6_runs_and_writes_report(self, capsys) -> None:
        rc = cli.main(["demo", "phase6"])
        assert rc == 0
        captured = capsys.readouterr()
        # Headline text on stdout.
        assert "ALL THREE CONDITIONS" in captured.out
        assert "PASS" in captured.out
        # Report file present and well-formed.
        report = Path("evals/forward_semantic_control/results/phase6_demo_report.json")
        assert report.exists()
        data = json.loads(report.read_text())
        assert data["metrics"]["all_three_conditions_pass"] is True

    def test_demo_phase6_json_emits_machine_readable(self, capsys) -> None:
        rc = cli.main(["demo", "phase6", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        # First non-blank chunk of stdout must be a parseable JSON
        # object containing the headline keys.
        payload = json.loads(captured.out.split("\n\n")[0])
        assert "metrics" in payload
        assert "all_three_conditions_pass" in payload["metrics"]

    def test_demo_list_results_indexes_reports(self, capsys) -> None:
        rc = cli.main(["demo", "list-results"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "results directory" in captured.out
        assert "phase6_demo_report.json" in captured.out

    def test_demo_list_results_json_well_formed(self, capsys) -> None:
        rc = cli.main(["demo", "list-results", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "results_dir" in data
        assert isinstance(data["reports"], list)
        names = [e["file"] for e in data["reports"]]
        assert "phase6_demo_report.json" in names

    def test_demo_index_file_refreshed_after_run(self) -> None:
        cli.main(["demo", "phase6"])
        index_path = Path("evals/forward_semantic_control/results/index.json")
        assert index_path.exists()
        data = json.loads(index_path.read_text())
        names = [e["file"] for e in data["reports"]]
        assert "phase6_demo_report.json" in names


class TestDemoPreambles:
    """Pin the preamble explanations so they don't drift silently."""

    def test_phase6_preamble_explains_three_conditions(self, capsys) -> None:
        cli.main(["demo", "phase6"])
        out = capsys.readouterr().out
        assert "WHAT THIS DEMO TESTS" in out
        assert "C1 Replay determinism" in out
        assert "C2 Traced rejection" in out
        assert "C3 Coherent refusal" in out
        assert "WHAT TO EXPECT" in out
        assert "WHEN TO TWEAK" in out

    def test_phase6_preamble_states_in_system_baseline(self, capsys) -> None:
        cli.main(["demo", "phase6"])
        out = capsys.readouterr().out
        # The "why not a transformer LLM" explanation must be present.
        assert "ADR-0023 ablation" in out
        assert "non-deterministic" in out or "Non-deterministic" in out

    def test_phase5_preamble_explains_five_families(self, capsys) -> None:
        cli.main(["demo", "phase5"])
        out = capsys.readouterr().out
        assert "WHAT THIS DEMO TESTS" in out
        for family in (
            "near_forbidden_correct_endpoint",
            "near_equal_admissible",
            "no_admissible_path",
            "multi_step_admissibility",
            "heterogeneous_relation",
        ):
            assert family in out
        assert "WHAT TO LOOK FOR" in out

    def test_phase5_preamble_states_delta_falsifiable(self, capsys) -> None:
        cli.main(["demo", "phase5"])
        out = capsys.readouterr().out
        assert "FALSIFIABLE" in out or "falsifiable" in out

    def test_preamble_suppressed_under_json(self, capsys) -> None:
        cli.main(["demo", "phase6", "--json"])
        out = capsys.readouterr().out
        # No preamble text should leak into --json mode.
        assert "WHAT THIS DEMO TESTS" not in out
        # Output must be parseable JSON from the first character.
        payload = json.loads(out.split("\n\n")[0])
        assert "metrics" in payload

    def test_all_preamble_explains_combined_run(self, capsys) -> None:
        cli.main(["demo", "all"])
        out = capsys.readouterr().out
        assert "Combined Demo" in out
        # Both phase preambles fire for `demo all`.
        assert "Phase 5 Demo" in out
        assert "Phase 6 Demo" in out
        # Combined summary at the end.
        assert "Combined demo summary" in out
        assert "load-bearing claim of the ADR-0024 chain" in out


class TestResultsReadme:
    """The results/ directory ships with an explanatory README so cold readers
    can interpret each report without spelunking the runner source."""

    def test_results_readme_exists(self) -> None:
        readme = Path("evals/forward_semantic_control/results/README.md")
        assert readme.exists()
        text = readme.read_text()
        # The README must explicitly call out each phase's report file.
        for fname in (
            "phase5_report.json",
            "phase6_demo_report.json",
            "phase5_benign_inner_loop_report.json",
            "phase4_characterization",
            "phase3_v2_report.json",
            "phase2_inner_loop_report.json",
        ):
            assert fname in text, f"{fname} missing from results/README.md"

    def test_corpus_readmes_exist(self) -> None:
        for path in (
            "evals/forward_semantic_control/public/v2_phase5/README.md",
            "evals/forward_semantic_control/public/v2_phase6_demo/README.md",
            "evals/forward_semantic_control/public/inner_loop_benign/README.md",
        ):
            assert Path(path).exists(), f"{path} missing"
