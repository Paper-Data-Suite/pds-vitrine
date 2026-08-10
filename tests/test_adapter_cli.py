from __future__ import annotations

import io

from vitrine import cli


def test_default_adapter_list_does_not_present_fixtures_as_live() -> None:
    output = io.StringIO()
    error = io.StringIO()
    assert cli.main(["adapters", "list"], output=output, error=error) == 0
    assert output.getvalue().strip() == "No live producer adapters are registered."
    assert "fixture" not in output.getvalue().lower()
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
    assert "vitrine_scoreform_fixture_adapter" in text
    assert "vitrine_quillan_fixture_adapter" in text
    assert "vitrine_concord_fixture_adapter" in text
    assert text.count("development_fixture") == 3


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
