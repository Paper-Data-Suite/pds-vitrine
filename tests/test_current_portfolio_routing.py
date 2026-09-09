from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import portfolio_menu, workflow_cli


def test_workflow_cli_registers_portfolio_build_export_task() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    workflow_cli.configure_workflow_parsers(subparsers)

    args = parser.parse_args(
        [
            "portfolio",
            "build-export",
            "prepare",
            "portfolio_1",
            "--audience-rule-id",
            "rule_1",
        ]
    )

    assert args.command == "portfolio"
    assert args.portfolio_command == "build-export"
    assert args.portfolio_build_export_command == "prepare"


def test_workflow_cli_routes_build_export_to_shared_task_handler(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = object()
    captured: dict[str, object] = {}

    def fake_handler(
        args: argparse.Namespace,
        *,
        dependencies: object,
        output: StringIO,
    ) -> int:
        captured["args"] = args
        captured["dependencies"] = dependencies
        captured["output"] = output
        return 7

    monkeypatch.setattr(
        workflow_cli,
        "run_current_portfolio_build_export_command",
        fake_handler,
    )
    args = argparse.Namespace(
        command="portfolio",
        portfolio_command="build-export",
        workspace_root=tmp_path,
    )
    output = StringIO()

    result = workflow_cli.run_workflow_command(
        args,
        dependencies=dependencies,  # type: ignore[arg-type]
        output=output,
    )

    assert result == 7
    assert captured["args"] is args
    assert captured["dependencies"] is dependencies
    assert captured["output"] is output


def test_portfolio_option_six_routes_to_current_portfolio_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = object()
    captured: dict[str, object] = {}
    responses = iter(("6", "", "B"))

    monkeypatch.setattr(
        portfolio_menu,
        "show_portfolio",
        lambda *args, **kwargs: SimpleNamespace(
            summary=SimpleNamespace(
                title_snapshot="Portfolio One",
                subject_display_label=None,
            )
        ),
    )

    def fake_task(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        portfolio_menu,
        "run_current_portfolio_build_export_menu",
        fake_task,
    )

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=lambda prompt: next(responses),
        output=StringIO(),
        clear_fn=lambda: None,
        dependencies=dependencies,  # type: ignore[arg-type]
        actor=None,
    )

    assert captured["root"] == tmp_path
    assert captured["portfolio_id"] == "portfolio_1"
    assert captured["dependencies"] is dependencies
    assert captured["actor"] is None
