from __future__ import annotations

from pathlib import Path

import pytest

from vitrine.workspace import (
    reset_workspace,
    set_workspace,
    show_workspace,
    validate_workspace,
)


def test_validate_creates_without_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    workspace = tmp_path / "workspace"
    result = validate_workspace(workspace)
    assert result.created is True
    assert result.saved is False
    assert (workspace / ".pds" / "workspace.json").is_file()
    assert not (config_home / "paper-data-suite" / "config.json").exists()


def test_set_and_reset_use_core_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    workspace = tmp_path / "workspace"
    result = set_workspace(workspace)
    assert result.saved is True
    assert show_workspace().source == "saved_config"
    assert reset_workspace() is True
    assert reset_workspace() is False
    assert workspace.exists()


def test_explicit_root_precedes_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = tmp_path / "environment"
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(environment))
    status = show_workspace(explicit)
    assert status.root == explicit.resolve()
    assert status.source == "explicit"


def test_environment_root_is_used_when_no_explicit_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = tmp_path / "environment"
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(environment))
    status = show_workspace()
    assert status.root == environment.resolve()
    assert status.source == "environment"
