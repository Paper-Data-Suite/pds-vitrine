from __future__ import annotations

import io
from pathlib import Path

import pytest

import vitrine.starter_profiles as starter_profiles
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


def _starter_plan(
    *,
    observed_state_revision: int | None = 3,
    lifecycle_disposition: str = "activate_existing_exact",
) -> starter_profiles.StarterProfileInstallPlan:
    return starter_profiles.StarterProfileInstallPlan(
        starter_profile_id="improvement_portfolio_v1",
        label="Starter Improvement Portfolio",
        purpose_kind="improvement",
        profile_family_id="vitrine_starter_improvement_family",
        portfolio_profile_id="vitrine_starter_improvement",
        profile_revision=1,
        observed_state_revision=observed_state_revision,
        observed_lifecycle_status=(
            "inactive"
            if lifecycle_disposition == "activate_existing_exact"
            else "absent"
        ),
        lifecycle_disposition=lifecycle_disposition,
        components=(
            starter_profiles.StarterProfileInstallComponentDisposition(
                component_kind="family",
                component_id="vitrine_starter_improvement_family",
                disposition="reuse_exact",
            ),
            starter_profiles.StarterProfileInstallComponentDisposition(
                component_kind="revision",
                component_id="vitrine_starter_improvement:1",
                disposition="reuse_exact",
            ),
            starter_profiles.StarterProfileInstallComponentDisposition(
                component_kind="requirement",
                component_id="teacher_review",
                disposition="create",
            ),
        ),
    )


def test_starter_list_uses_packaged_catalog_without_state_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.observe_profile_state_revision",
        lambda _root: (_ for _ in ()).throw(
            AssertionError("starter list must not observe workspace state")
        ),
    )
    output = io.StringIO()
    assert cli.main(["profile", "starter", "list"], output=output) == 0
    text = output.getvalue()
    assert "improvement_portfolio_v1\timprovement\tStarter Improvement Portfolio" in text
    assert "showcase_portfolio_v1\tshowcase\tStarter Showcase Portfolio" in text


def test_starter_show_prints_complete_policy_preview() -> None:
    output = io.StringIO()
    assert (
        cli.main(
            ["profile", "starter", "show", "improvement_portfolio_v1"],
            output=output,
        )
        == 0
    )
    text = output.getvalue()
    assert "Family: vitrine_starter_improvement_family" in text
    assert "Profile: vitrine_starter_improvement@1" in text
    assert "Sections:" in text
    assert "baseline: Baseline Evidence" in text
    assert "Audience rules:" in text
    assert "Requirements:" in text
    assert "Known limitations:" in text
    assert "does not determine whether improvement occurred" in text
    assert "Authority notice:" in text


def test_starter_plan_prints_read_only_install_dispositions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _starter_plan()
    captured: dict[str, object] = {}

    def planner(starter_profile_id: str, **kwargs: object) -> object:
        captured.update(starter_profile_id=starter_profile_id, kwargs=kwargs)
        return plan

    monkeypatch.setattr("vitrine.profile_cli.plan_starter_profile_install", planner)
    output = io.StringIO()
    assert (
        cli.main(
            [
                "profile",
                "starter",
                "plan",
                "improvement_portfolio_v1",
                "--workspace-root",
                str(tmp_path),
            ],
            output=output,
        )
        == 0
    )
    assert captured["starter_profile_id"] == "improvement_portfolio_v1"
    text = output.getvalue()
    assert "Observed state revision: 3" in text
    assert "Lifecycle disposition: activate_existing_exact" in text
    assert "requirement:teacher_review: create" in text
    assert "Activation required: yes" in text
    assert "Bindable after requested install: yes" in text
    assert "Activation notice:" in text


def test_starter_install_requires_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.install_starter_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("install must not run without --confirm")
        ),
    )
    error = io.StringIO()
    args = [
        "profile",
        "starter",
        "install",
        "improvement_portfolio_v1",
        *_actor_args(),
    ]
    assert cli.main(args, output=io.StringIO(), error=error) == 1
    assert "Error [starter_profile_confirmation_required]" in error.getvalue()


def test_starter_install_dispatches_confirmed_guarded_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    plan = _starter_plan(
        observed_state_revision=3,
        lifecycle_disposition="activate_existing_exact",
    )
    result = starter_profiles.StarterProfileInstallResult(
        plan=plan,
        activation_event_id="profile_event_1",
        committed_component_ids=(
            "requirement:teacher_review",
            "lifecycle:profile_event_1",
        ),
        commit=_commit(4),
    )

    def install(starter_profile_id: str, **kwargs: object) -> object:
        captured.update(starter_profile_id=starter_profile_id, kwargs=kwargs)
        return result

    monkeypatch.setattr(
        "vitrine.profile_cli.observe_profile_state_revision", lambda _root: 3
    )
    monkeypatch.setattr("vitrine.profile_cli.install_starter_profile", install)
    output = io.StringIO()
    args = [
        "profile",
        "starter",
        "install",
        "improvement_portfolio_v1",
        *_actor_args(),
        "--confirm",
        "--workspace-root",
        str(tmp_path),
    ]
    assert cli.main(args, output=output) == 0
    assert captured["starter_profile_id"] == "improvement_portfolio_v1"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["expected_state_revision"] == 3
    actor = kwargs["actor"]
    assert getattr(actor, "actor_id") == "teacher_1"
    assert kwargs["reason"] == "Approved local use."
    assert kwargs["authority_reference"] == "local_policy"
    text = output.getvalue()
    assert "State revision: 4" in text
    assert "Profile: vitrine_starter_improvement@1" in text
    assert "Activation event: profile_event_1" in text


def test_starter_error_preserves_stable_machine_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.plan_starter_profile_install",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            starter_profiles.StarterProfileError(
                "starter_profile_install_conflict",
                "Existing immutable content conflicts.",
            )
        ),
    )
    error = io.StringIO()
    assert (
        cli.main(
            ["profile", "starter", "plan", "improvement_portfolio_v1"],
            output=io.StringIO(),
            error=error,
        )
        == 1
    )
    assert "Error [starter_profile_install_conflict]" in error.getvalue()


def test_starter_validate_is_read_only_and_reports_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitrine.profile_cli.observe_profile_state_revision",
        lambda _root: (_ for _ in ()).throw(
            AssertionError("starter validate must not observe workspace state")
        ),
    )
    output = io.StringIO()
    assert (
        cli.main(
            ["profile", "starter", "validate", "improvement_portfolio_v1"],
            output=output,
        )
        == 0
    )
    assert output.getvalue() == (
        "PASS starter Profile: improvement_portfolio_v1\n"
    )
