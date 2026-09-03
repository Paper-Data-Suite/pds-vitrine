from __future__ import annotations

import io

import pytest

from vitrine import cli


def test_default_adapter_list_contains_completed_live_adapters() -> None:
    output = io.StringIO()
    error = io.StringIO()
    assert cli.main(["adapters", "list"], output=output, error=error) == 0
    text = output.getvalue()
    assert "vitrine_concord_live_adapter" in text
    assert "vitrine_quillan_live_adapter" in text
    assert "vitrine_scoreform_live_adapter" in text
    assert "\tlive\tconcord\t" in text
    assert "\tlive\tquillan\t" in text
    assert "\tlive\tscoreform\t" in text
    assert "fixture" not in text.lower()
    assert error.getvalue() == ""


def test_adapter_list_can_explicitly_include_development_fixtures() -> None:
    output = io.StringIO()
    assert (
        cli.main(
            ["adapters", "list", "--include-development-fixtures"],
            output=output,
        )
        == 0
    )
    text = output.getvalue()
    assert "vitrine_concord_live_adapter" in text
    assert "vitrine_quillan_live_adapter" in text
    assert "vitrine_scoreform_live_adapter" in text
    assert "vitrine_scoreform_fixture_adapter" in text
    assert "vitrine_quillan_fixture_adapter" in text
    assert "vitrine_concord_fixture_adapter" in text
    assert text.count("development_fixture") == 3
    assert text.count("\tlive\t") == 3


def test_live_adapter_show_is_available_without_fixture_opt_in_and_is_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.scoreform_adapter as scoreform_adapter

    def forbidden_import(_name: str) -> object:
        raise AssertionError("adapter diagnostics must not import ScoreForm")

    monkeypatch.setattr(scoreform_adapter, "import_module", forbidden_import)
    output = io.StringIO()
    error = io.StringIO()
    assert (
        cli.main(
            ["adapters", "show", "vitrine_scoreform_live_adapter"],
            output=output,
            error=error,
        )
        == 0
    )
    text = output.getvalue()
    assert "Integration kind: live" in text
    assert "Producer module: scoreform" in text
    assert "scoreform_academic_result_manifest_v1" in text
    assert "vitrine_installed_scoreform_academic_result_reader" in text
    assert "student_" not in text
    assert error.getvalue() == ""


def test_concord_live_adapter_show_is_available_without_importing_concord(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.concord_adapter as concord_adapter

    def forbidden_import(_name: str) -> object:
        raise AssertionError("adapter diagnostics must not import Concord")

    monkeypatch.setattr(concord_adapter, "import_module", forbidden_import)
    output = io.StringIO()
    error = io.StringIO()
    assert (
        cli.main(
            ["adapters", "show", "vitrine_concord_live_adapter"],
            output=output,
            error=error,
        )
        == 0
    )
    text = output.getvalue()
    assert "Integration kind: live" in text
    assert "Producer module: concord" in text
    assert "concord_academic_result_manifest_v1" in text
    assert "vitrine_installed_concord_academic_result_reader" in text
    assert "Required capabilities: criterion_scores" in text
    assert "student_" not in text
    assert error.getvalue() == ""


def test_adapter_show_requires_fixture_opt_in() -> None:
    output = io.StringIO()
    error = io.StringIO()
    assert (
        cli.main(
            ["adapters", "show", "vitrine_scoreform_fixture_adapter"],
            output=output,
            error=error,
        )
        == 1
    )
    assert output.getvalue() == ""
    assert "not found" in error.getvalue().lower()


def test_adapter_show_displays_declaration_but_not_fixture_payload() -> None:
    output = io.StringIO()
    assert (
        cli.main(
            [
                "adapters",
                "show",
                "vitrine_scoreform_fixture_adapter",
                "--include-development-fixtures",
            ],
            output=output,
        )
        == 0
    )
    text = output.getvalue()
    assert "Integration kind: development_fixture" in text
    assert "vitrine_fixture_scoreform_manifest_v1" in text
    assert "PRIVATE_ANSWER_KEY_DO_NOT_PROJECT" not in text
    assert "student_alpha" not in text
