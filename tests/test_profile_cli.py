from __future__ import annotations

import io
from pathlib import Path

import pytest

from vitrine import cli
from vitrine.models import ProfileRevisionRef
from vitrine.profile_services import (
    ProfileMigrationAnalysis,
    ProfileMutationResult,
    ProfileRevisionSummary,
    ProfileWorkflowError,
)
from vitrine.storage import VitrineStorageCommitResult


def _commit(revision: int = 3) -> VitrineStorageCommitResult:
    return VitrineStorageCommitResult(
        state_revision=revision,
        state_sha256="a" * 64,
        created_record_revisions=(),
    )


def _mutation(revision: int = 3) -> ProfileMutationResult:
    return ProfileMutationResult(("record_1",), _commit(revision))


def _actor_args() -> list[str]:
    return [
        "--actor-id",
        "teacher_1",
        "--authority-reference",
        "local_policy",
        "--reason",
        "Approved local use.",
    ]


def test_profile_list_uses_shared_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.list_profile_revisions",
        lambda _root, portfolio_profile_id=None: (
            ProfileRevisionSummary(
                ProfileRevisionRef(
                    portfolio_profile_id="profile_growth", profile_revision=1
                ),
                "Growth",
                "improvement",
                "activated",
                True,
                3,
            ),
        ),
    )
    output = io.StringIO()
    assert cli.main(["profile", "list"], output=output) == 0
    assert "profile_growth@1\tactivated\timprovement\tGrowth\trequirements=3" in output.getvalue()


def test_activate_is_noninteractive_and_dispatches_exact_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fail_input(_prompt: str = "") -> str:
        raise AssertionError("direct Profile command prompted for input")

    def activate(root: object, reference: object, **kwargs: object) -> ProfileMutationResult:
        captured.update(root=root, reference=reference, kwargs=kwargs)
        return _mutation(4)

    monkeypatch.setattr("builtins.input", fail_input)
    monkeypatch.setattr("vitrine.profile_cli.observe_profile_state_revision", lambda _root: 3)
    monkeypatch.setattr("vitrine.profile_cli.activate_profile_revision", activate)
    output = io.StringIO()
    args = [
        "profile",
        "activate",
        "profile_growth",
        "--revision",
        "1",
        *_actor_args(),
        "--workspace-root",
        str(tmp_path),
    ]
    assert cli.main(args, output=output) == 0
    reference = captured["reference"]
    assert getattr(reference, "portfolio_profile_id") == "profile_growth"
    assert getattr(reference, "profile_revision") == 1
    assert captured["kwargs"]["expected_state_revision"] == 3  # type: ignore[index]
    assert "State revision: 4" in output.getvalue()


def test_explicit_expected_revision_avoids_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def activate(*args: object, **kwargs: object) -> ProfileMutationResult:
        captured.update(args=args, kwargs=kwargs)
        return _mutation(8)

    monkeypatch.setattr("vitrine.profile_cli.activate_profile_revision", activate)
    monkeypatch.setattr(
        "vitrine.profile_cli.observe_profile_state_revision",
        lambda _root: (_ for _ in ()).throw(AssertionError("should not observe state")),
    )
    assert (
        cli.main(
            [
                "profile",
                "activate",
                "profile_growth",
                "--revision",
                "2",
                *_actor_args(),
                "--expected-state-revision",
                "7",
            ],
            output=io.StringIO(),
        )
        == 0
    )
    assert captured["kwargs"]["expected_state_revision"] == 7  # type: ignore[index]


def test_migration_analyze_prints_deterministic_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vitrine.models import ProfileRequirementImpact

    analysis = ProfileMigrationAnalysis(
        portfolio_id="portfolio_1",
        predecessor_binding_id="binding_1",
        source_profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_growth", profile_revision=1
        ),
        target_profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_growth", profile_revision=2
        ),
        requirement_impact=ProfileRequirementImpact(
            unchanged=("baseline_required",),
            added=("feedback_context_required",),
        ),
        affected_section_ids=("feedback_context",),
        potentially_affected_selection_count=2,
        reapproval_requirement_ids=("teacher_review",),
        unresolved_requirement_ids=(),
    )
    monkeypatch.setattr(
        "vitrine.profile_cli.analyze_profile_migration",
        lambda *_args, **_kwargs: analysis,
    )
    output = io.StringIO()
    assert (
        cli.main(
            [
                "profile",
                "migration",
                "analyze",
                "portfolio_1",
                "profile_growth",
                "--revision",
                "2",
            ],
            output=output,
        )
        == 0
    )
    text = output.getvalue()
    assert "added: feedback_context_required" in text
    assert "Potentially affected selections: 2" in text
    assert "Blocked: no" in text


def test_profile_error_uses_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.list_profile_revisions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ProfileWorkflowError("profile_revision_not_found", "Profile missing.")
        ),
    )
    output = io.StringIO()
    error = io.StringIO()
    assert cli.main(["profile", "list"], output=output, error=error) == 1
    assert output.getvalue() == ""
    assert "Error [profile_revision_not_found]: Profile missing." in error.getvalue()
