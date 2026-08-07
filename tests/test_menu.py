from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from vitrine.menu import run_menu


def scripted_input(values: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


def test_immediate_quit_creates_no_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    output = io.StringIO()
    clears: list[None] = []
    result = run_menu(
        input_fn=scripted_input(["Q"]),
        output=output,
        clear_fn=lambda: clears.append(None),
    )
    assert result == 0
    assert not (tmp_path / "workspace").exists()
    assert "B. Back" not in output.getvalue()
    assert "M. Main Menu" not in output.getvalue()
    assert clears


def test_help_returns_to_main_menu() -> None:
    output = io.StringIO()
    result = run_menu(
        input_fn=scripted_input(["h", "", "q"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert result == 0
    assert "Vitrine Help" in output.getvalue()


def test_workspace_submenu_back_and_main_navigation() -> None:
    output = io.StringIO()
    result = run_menu(
        input_fn=scripted_input(["2", "b", "2", "m", "q"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert result == 0
    assert output.getvalue().count("Vitrine\n") >= 3


def test_eof_and_keyboard_interrupt_exit_cleanly() -> None:
    for exception in (EOFError(), KeyboardInterrupt()):

        def raising(_prompt: str, exc: BaseException = exception) -> str:
            raise exc

        assert (
            run_menu(input_fn=raising, output=io.StringIO(), clear_fn=lambda: None)
            == 0
        )


def test_cancelled_workspace_set_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    workspace = tmp_path / "workspace"
    output = io.StringIO()
    result = run_menu(
        input_fn=scripted_input(["2", "2", str(workspace), "", "b", "q"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert result == 0
    assert not workspace.exists()
    assert not (tmp_path / "config").exists()


def test_confirmed_validate_creates_workspace_without_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    config = tmp_path / "config"
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    output = io.StringIO()
    result = run_menu(
        input_fn=scripted_input(["2", "3", "CREATE", "", "b", "q"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert result == 0
    assert (workspace / ".pds" / "workspace.json").is_file()
    assert not (config / "paper-data-suite" / "config.json").exists()
