from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.current_portfolio_cli import (
    CurrentPortfolioCliError,
    configure_current_portfolio_build_export_parsers,
    run_current_portfolio_build_export_command,
)


def _dependencies() -> SimpleNamespace:
    return SimpleNamespace(
        snapshot_source_providers=object(),
        snapshot_build_authority_gate=object(),
    )


def _namespace(tmp_path: Path, *, command: str) -> argparse.Namespace:
    values: dict[str, object] = {
        "portfolio_build_export_command": command,
        "workspace_root": tmp_path,
        "portfolio_id": "portfolio_1",
        "audience_rule_id": "rule_1",
        "audience_context_id": "context_1",
        "snapshot_series_id": "series_1",
        "acknowledge_obligation": ["obligation_a"],
    }
    if command == "execute":
        values.update(
            {
                "preparation_fingerprint": "a" * 64,
                "expected_state_revision": 17,
                "actor_id": "teacher_1",
                "actor_kind": "authorized_adult",
                "owning_system": "local",
                "role": "teacher",
            }
        )
    return argparse.Namespace(**values)


def _preparation(*, fingerprint: str = "a" * 64) -> SimpleNamespace:
    return SimpleNamespace(
        observed_state_revision=17,
        preparation_fingerprint=fingerprint,
        ready_for_plan_execution=True,
    )


def test_parser_exposes_prepare_and_execute_with_exact_disambiguation() -> None:
    parser = argparse.ArgumentParser()
    roots = parser.add_subparsers(dest="portfolio_command", required=True)
    configure_current_portfolio_build_export_parsers(roots)

    args = parser.parse_args(
        [
            "build-export",
            "execute",
            "portfolio_1",
            "--audience-rule-id",
            "rule_1",
            "--audience-context-id",
            "context_1",
            "--snapshot-series-id",
            "series_1",
            "--acknowledge-obligation",
            "obligation_a",
            "--preparation-fingerprint",
            "f" * 64,
            "--expected-state-revision",
            "9",
            "--actor-id",
            "teacher_1",
        ]
    )

    assert args.portfolio_command == "build-export"
    assert args.portfolio_build_export_command == "execute"
    assert args.audience_context_id == "context_1"
    assert args.snapshot_series_id == "series_1"
    assert args.acknowledge_obligation == ["obligation_a"]
    assert args.expected_state_revision == 9


def test_prepare_is_read_only_and_uses_exact_provider_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = _dependencies()
    captured: dict[str, object] = {}
    preparation = _preparation()

    def fake_prepare(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return preparation

    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.prepare_current_portfolio_build",
        fake_prepare,
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.print_current_portfolio_preparation",
        lambda value, *, output: captured.update(printed=value),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.execute_prepared_current_portfolio_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("write")),
    )

    result = run_current_portfolio_build_export_command(
        _namespace(tmp_path, command="prepare"),
        dependencies=dependencies,
        output=StringIO(),
    )

    assert result == 0
    assert captured["printed"] is preparation
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["audience_rule_id"] == "rule_1"
    assert kwargs["audience_context_id"] == "context_1"
    assert kwargs["snapshot_series_id"] == "series_1"
    assert kwargs["acknowledged_obligation_codes"] == ("obligation_a",)
    assert kwargs["source_providers"] is dependencies.snapshot_source_providers


def test_execute_rejects_changed_fingerprint_before_shared_executor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.prepare_current_portfolio_build",
        lambda *args, **kwargs: _preparation(fingerprint="b" * 64),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.print_current_portfolio_preparation",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.execute_prepared_current_portfolio_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("write")),
    )

    with pytest.raises(CurrentPortfolioCliError) as caught:
        run_current_portfolio_build_export_command(
            _namespace(tmp_path, command="execute"),
            dependencies=_dependencies(),
            output=StringIO(),
        )

    assert caught.value.code == (
        "current_portfolio_build.preparation_fingerprint_mismatch"
    )


def test_execute_uses_exact_reviewed_preparation_and_shared_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = _dependencies()
    preparation = _preparation()
    captured: dict[str, object] = {}
    result = SimpleNamespace(
        preparation_fingerprint="a" * 64,
        state_revision=22,
        audience_context_id="context_1",
        snapshot_series_id="series_1",
        snapshot_build_request_id="request_1",
        snapshot_build_plan_id="plan_1",
        snapshot_build_attempt_id="attempt_1",
        attempt_terminal_outcome="sealed",
        edition_number=2,
        edition_manifest_sha256="c" * 64,
        edition_logical_inventory_sha256="d" * 64,
        snapshot_export_artifact_id="export_1",
        export_disposition="created",
        export_directory_inventory_sha256="e" * 64,
        export_path=tmp_path / "export",
    )

    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.prepare_current_portfolio_build",
        lambda *args, **kwargs: preparation,
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.print_current_portfolio_preparation",
        lambda *args, **kwargs: None,
    )

    def fake_execute(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return result

    monkeypatch.setattr(
        "vitrine.current_portfolio_cli.execute_prepared_current_portfolio_build",
        fake_execute,
    )

    output = StringIO()
    exit_code = run_current_portfolio_build_export_command(
        _namespace(tmp_path, command="execute"),
        dependencies=dependencies,
        output=output,
    )

    assert exit_code == 0
    assert captured["args"] == (tmp_path, preparation)
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["authority_gate"] is dependencies.snapshot_build_authority_gate
    assert kwargs["source_providers"] is dependencies.snapshot_source_providers
    assert kwargs["actor"].actor_id == "teacher_1"
    text = output.getvalue()
    assert "Current Edition pointer advanced: no" in text
    assert "not disclosure permission or delivery" in text
