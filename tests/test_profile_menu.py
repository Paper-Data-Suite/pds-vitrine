from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pds_core.menu_navigation import QuitPDS, ReturnToMainMenu

from tests.profile_helpers import (
    improvement_family,
    improvement_requirements,
    improvement_revision,
    make_profile_workspace,
)
from vitrine.models import ProfileRevisionRef
from vitrine.profile_menu import run_profile_menu
from vitrine.profile_services import (
    ProfileWorkflowError,
    create_profile_family,
    create_profile_revision,
    list_bindable_profile_revisions,
)


def scripted_input(values: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


class ScreenRecorder:
    def __init__(self) -> None:
        self.output = io.StringIO()
        self.offsets: list[int] = []

    def clear(self) -> None:
        self.offsets.append(self.output.tell())

    def screens(self) -> tuple[str, ...]:
        text = self.output.getvalue()
        if not self.offsets:
            return (text,)
        return tuple(
            text[start : self.offsets[index + 1] if index + 1 < len(self.offsets) else len(text)]
            for index, start in enumerate(self.offsets)
        )


def test_profile_menu_help_back_main_and_quit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_profile_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    output = io.StringIO()
    run_profile_menu(
        input_fn=scripted_input(["h", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    text = output.getvalue()
    assert "Portfolio Profile Help" in text
    assert "B. Back" in text
    assert "M. Main Menu" in text
    assert "Q. Quit" in text

    with pytest.raises(ReturnToMainMenu):
        run_profile_menu(
            input_fn=scripted_input(["m"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )
    with pytest.raises(QuitPDS):
        run_profile_menu(
            input_fn=scripted_input(["q"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )


def test_profile_menu_dispatches_all_workflows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_profile_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    called: list[str] = []
    names = (
        "_view_profiles",
        "_create_family",
        "_create_revision",
        "_activate",
        "_bind",
        "_migrate",
        "_overlay",
        "_compose",
    )
    for name in names:
        monkeypatch.setattr(
            f"vitrine.profile_menu.{name}",
            lambda *args, _name=name, **kwargs: called.append(_name),
        )
    for index, name in enumerate(names, start=1):
        run_profile_menu(
            input_fn=scripted_input([str(index), "b"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )
        assert called[-1] == name


def test_activation_flow_clears_revision_list_before_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_profile_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    create_profile_family(workspace, improvement_family(), expected_state_revision=1)
    create_profile_revision(
        workspace,
        improvement_revision(1),
        improvement_requirements(1),
        expected_state_revision=2,
    )
    recorder = ScreenRecorder()
    run_profile_menu(
        input_fn=scripted_input(
            [
                "4",  # activate
                "1",  # exact revision
                "teacher_profile",
                "local_instructional_policy",
                "Approved local use.",
                "ACTIVATE",
                "",  # success pause
                "b",
            ]
        ),
        output=recorder.output,
        clear_fn=recorder.clear,
    )
    bindable = list_bindable_profile_revisions(workspace)
    assert bindable == (
        bindable[0],
    )
    assert bindable[0].reference == ProfileRevisionRef(
        portfolio_profile_id="profile_growth", profile_revision=1
    )
    confirmation = next(
        screen
        for screen in recorder.screens()
        if screen.startswith("Activate Profile Revision\n")
        and "Requirements:" in screen
    )
    assert "profile_growth@1" in confirmation
    assert "Select Profile Revision" not in confirmation
    assert "1. Growth Profile" not in confirmation


def test_view_profile_is_compact_after_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_profile_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    create_profile_family(workspace, improvement_family(), expected_state_revision=1)
    create_profile_revision(
        workspace,
        improvement_revision(1),
        improvement_requirements(1),
        expected_state_revision=2,
    )
    recorder = ScreenRecorder()
    run_profile_menu(
        input_fn=scripted_input(["1", "1", "", "b"]),
        output=recorder.output,
        clear_fn=recorder.clear,
    )
    detail = next(
        screen for screen in recorder.screens() if screen.startswith("Growth Profile r1\n")
    )
    assert "Profile: profile_growth@1" in detail
    assert "Requirements: 3" in detail
    assert "Select Profile Revision" not in detail


def test_expected_profile_error_is_concise_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_profile_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))

    def fail(*_args: object, **_kwargs: object) -> None:
        raise ProfileWorkflowError("state_conflict", "Vitrine state changed.")

    monkeypatch.setattr("vitrine.profile_menu._view_profiles", fail)
    output = io.StringIO()
    run_profile_menu(
        input_fn=scripted_input(["1", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    text = output.getvalue()
    assert "Profile problem [state_conflict]: Vitrine state changed." in text
    assert "Traceback" not in text
