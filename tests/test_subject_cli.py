from __future__ import annotations

import io
from pathlib import Path

import pytest

from vitrine import cli
from vitrine.storage import VitrineStorageCommitResult
from vitrine.subject_services import (
    SubjectMutationResult,
    SubjectSummary,
    SubjectWorkflowError,
)


def _mutation(*, revision: int = 3) -> SubjectMutationResult:
    return SubjectMutationResult(
        subject_ids=("subject_1",),
        link_ids=("link_1",),
        affected_portfolio_ids=(),
        commit=VitrineStorageCommitResult(
            state_revision=revision,
            state_sha256="a" * 64,
            created_record_revisions=(),
        ),
    )


def _decision_args() -> list[str]:
    return [
        "--actor-id",
        "teacher_1",
        "--authority-source",
        "local_teacher_workflow",
        "--basis-type",
        "direct_teacher_knowledge",
        "--basis-summary",
        "Teacher confirmed identity.",
    ]


def _reference_args() -> list[str]:
    return [
        "--school-year",
        "2026-2027",
        "--class-id",
        "english10_p2",
        "--student-id",
        "00107",
    ]


def test_subject_list_uses_shared_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vitrine.subject_cli.list_subjects",
        lambda _root: (
            SubjectSummary("subject_1", "Jane Doe", "active", 2, 1, 0),
        ),
    )
    output = io.StringIO()
    assert cli.main(["subject", "list"], output=output) == 0
    assert "subject_1\tactive\tJane Doe\tlinks=2\thistorical=1" in output.getvalue()


def test_subject_create_is_noninteractive_and_dispatches_exact_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fail_input(_prompt: str = "") -> str:
        raise AssertionError("direct subject command prompted for input")

    def create(root: object, reference: object, **kwargs: object) -> SubjectMutationResult:
        captured.update(root=root, reference=reference, kwargs=kwargs)
        return _mutation(revision=1)

    monkeypatch.setattr("builtins.input", fail_input)
    monkeypatch.setattr("vitrine.subject_cli.observe_state_revision", lambda _root: None)
    monkeypatch.setattr("vitrine.subject_cli.create_portfolio_subject", create)
    output = io.StringIO()
    args = [
        "subject",
        "create",
        *_reference_args(),
        *_decision_args(),
        "--workspace-root",
        str(tmp_path),
    ]
    assert cli.main(args, output=output) == 0
    reference = captured["reference"]
    assert getattr(reference, "school_year") == "2026-2027"
    assert getattr(reference, "class_id") == "english10_p2"
    assert getattr(reference, "student_id") == "00107"
    assert captured["kwargs"]["expected_state_revision"] is None  # type: ignore[index]
    assert "State revision: 1" in output.getvalue()


def test_explicit_expected_revision_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def link(*args: object, **kwargs: object) -> SubjectMutationResult:
        captured.update(args=args, kwargs=kwargs)
        return _mutation()

    monkeypatch.setattr("vitrine.subject_cli.link_portfolio_subject", link)
    monkeypatch.setattr(
        "vitrine.subject_cli.observe_state_revision",
        lambda _root: (_ for _ in ()).throw(AssertionError("should not observe state")),
    )
    args = [
        "subject",
        "link",
        "subject_1",
        *_reference_args(),
        *_decision_args(),
        "--expected-state-revision",
        "7",
    ]
    assert cli.main(args, output=io.StringIO()) == 0
    assert captured["kwargs"]["expected_state_revision"] == 7  # type: ignore[index]


def test_merge_and_split_parse_explicit_subject_and_link_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr("vitrine.subject_cli.observe_state_revision", lambda _root: 4)

    def merge(_root: object, ids: object, **_kwargs: object) -> SubjectMutationResult:
        calls.append(("merge", ids))
        return _mutation(revision=5)

    def split(
        _root: object, subject_id: object, groups: object, **_kwargs: object
    ) -> SubjectMutationResult:
        calls.append(("split", (subject_id, groups)))
        return _mutation(revision=6)

    monkeypatch.setattr("vitrine.subject_cli.merge_portfolio_subjects", merge)
    monkeypatch.setattr("vitrine.subject_cli.split_portfolio_subject", split)
    assert (
        cli.main(
            ["subject", "merge", "subject_a", "subject_b", *_decision_args()],
            output=io.StringIO(),
        )
        == 0
    )
    assert (
        cli.main(
            [
                "subject",
                "split",
                "subject_a",
                "--group",
                "link_1,link_2",
                "--group",
                "link_3",
                *_decision_args(),
            ],
            output=io.StringIO(),
        )
        == 0
    )
    assert calls == [
        ("merge", ["subject_a", "subject_b"]),
        ("split", ("subject_a", (("link_1", "link_2"), ("link_3",)))),
    ]


def test_subject_workflow_error_uses_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vitrine.subject_cli.list_subjects",
        lambda _root: (_ for _ in ()).throw(
            SubjectWorkflowError("subject_not_found", "Subject was not found.")
        ),
    )
    output = io.StringIO()
    error = io.StringIO()
    assert cli.main(["subject", "list"], output=output, error=error) == 1
    assert output.getvalue() == ""
    assert "Subject error [subject_not_found]" in error.getvalue()
