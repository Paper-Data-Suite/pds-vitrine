from __future__ import annotations

import io
from pathlib import Path

import pytest

from vitrine import cli


def test_parser_construction_is_side_effect_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.build_parser()
    assert list(tmp_path.iterdir()) == []


def test_help_is_noninteractive(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fail_menu(**_: object) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli.menu_module, "run_menu", fail_menu)
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])
    assert raised.value.code == 0
    assert called is False


def test_bare_command_launches_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.menu_module, "run_menu", lambda **_: 7)
    assert cli.main([]) == 7


def test_explicit_menu_launches_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.menu_module, "run_menu", lambda **_: 8)
    assert cli.main(["menu"]) == 8


def test_workspace_show_is_read_only(tmp_path: Path) -> None:
    output = io.StringIO()
    assert (
        cli.main(
            ["workspace", "show", "--workspace-root", str(tmp_path / "pds")],
            output=output,
        )
        == 0
    )
    assert "Exists: no" in output.getvalue()
    assert not (tmp_path / "pds").exists()


def test_workspace_validate_creates_core_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "pds"
    output = io.StringIO()
    assert (
        cli.main(
            ["workspace", "validate", "--workspace-root", str(workspace)],
            output=output,
        )
        == 0
    )
    assert (workspace / ".pds" / "workspace.json").is_file()
    assert "Created workspace" in output.getvalue()


def test_workspace_error_uses_stderr(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("x", encoding="utf-8")
    output = io.StringIO()
    error = io.StringIO()
    result = cli.main(
        ["workspace", "validate", "--workspace-root", str(file_path)],
        output=output,
        error=error,
    )
    assert result == 1
    assert output.getvalue() == ""
    assert "Workspace error:" in error.getvalue()


def test_workspace_set_and_reset_use_core_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    workspace = tmp_path / "workspace"
    output = io.StringIO()
    assert cli.main(["workspace", "set", str(workspace)], output=output) == 0
    assert (workspace / ".pds" / "workspace.json").is_file()
    assert cli.main(["workspace", "reset"], output=output) == 0
    assert workspace.is_dir()


def test_direct_workspace_command_never_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_input(_prompt: str = "") -> str:
        raise AssertionError("direct command prompted for input")

    monkeypatch.setattr("builtins.input", fail_input)
    output = io.StringIO()
    assert (
        cli.main(
            ["workspace", "show", "--workspace-root", str(tmp_path / "workspace")],
            output=output,
        )
        == 0
    )


def test_invalid_usage_has_argparse_status_two() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["workspace"])
    assert raised.value.code == 2
