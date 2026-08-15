from __future__ import annotations

import io
from pathlib import Path

import pytest

from vitrine import cli
from vitrine.workflow_context import default_workflow_dependencies


def test_workflow_parser_construction_is_side_effect_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    parser = cli.build_parser()
    assert list(tmp_path.iterdir()) == []
    assert parser.parse_args(["portfolio", "list"]).command == "portfolio"
    assert (
        parser.parse_args(["candidate", "list", "portfolio_1"]).command == "candidate"
    )
    assert (
        parser.parse_args(["snapshot", "verify", "series_1", "--edition", "1"]).command
        == "snapshot"
    )


def test_direct_workflow_commands_never_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(AssertionError("unexpected prompt")),
    )
    output = io.StringIO()
    assert (
        cli.main(
            ["portfolio", "list", "--workspace-root", str(tmp_path / "workspace")],
            output=output,
        )
        == 0
    )


def test_default_workflow_dependencies_fail_closed_and_hide_fixtures() -> None:
    dependencies = default_workflow_dependencies()
    assert dependencies.development_fixture_mode is False
    assert dependencies.producer_registry.profiles == ()
    assert dependencies.adapter_registry.adapters == ()
