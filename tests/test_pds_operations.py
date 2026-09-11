from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    ModuleOperationsRequest,
    ModuleOwnerActionRef,
    validate_module_attention_report,
    validate_module_operations_profile,
    validate_module_readiness_report,
)

from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionNotice,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
)
from vitrine.constants import VITRINE_MODULE_ID
from vitrine.operations_provider import (
    VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED,
    VITRINE_ATTENTION_WORKSPACE_REQUIRED,
    VITRINE_READINESS_STORAGE_BLOCKED,
    VITRINE_READINESS_WORKSPACE_REQUIRED,
    evaluate_vitrine_attention_for_core,
    evaluate_vitrine_readiness,
    project_vitrine_attention_to_core,
)
from vitrine.pds_operations import get_module_operations_profile


def test_operations_profile_is_core_v1_with_both_capabilities() -> None:
    profile = get_module_operations_profile()

    assert validate_module_operations_profile(profile) is profile
    assert profile.module_id == VITRINE_MODULE_ID
    assert profile.supported_core_operations_contract_versions == frozenset(
        {MODULE_OPERATIONS_CONTRACT_VERSION}
    )
    assert profile.readiness_provider is not None
    assert profile.attention_provider is not None


def test_readiness_requires_explicit_workspace() -> None:
    report = evaluate_vitrine_readiness(ModuleOperationsRequest())

    assert validate_module_readiness_report(
        report, expected_module_id=VITRINE_MODULE_ID
    ) is report
    assert report.evaluation == "unavailable"
    assert report.ready is None
    assert tuple(item.code for item in report.notices) == (
        VITRINE_READINESS_WORKSPACE_REQUIRED,
    )


def test_existing_empty_workspace_is_ready_without_creating_vitrine_state(
    tmp_path: Path,
) -> None:
    before = tuple(tmp_path.iterdir())

    report = evaluate_vitrine_readiness(
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            active_school_year="2026-2027",
            class_id="english-10",
        )
    )

    assert report.evaluation == "evaluated"
    assert report.ready is True
    assert report.notices == ()
    assert tuple(tmp_path.iterdir()) == before
    assert not (tmp_path / "vitrine").exists()


def test_existing_incomplete_vitrine_namespace_is_diagnosed_not_unavailable(
    tmp_path: Path,
) -> None:
    (tmp_path / "vitrine").mkdir()
    before = tuple(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    report = evaluate_vitrine_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path)
    )

    after = tuple(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert tuple(item.code for item in report.notices) == (
        VITRINE_READINESS_STORAGE_BLOCKED,
    )
    assert after == before


def test_attention_requires_explicit_workspace() -> None:
    report = evaluate_vitrine_attention_for_core(ModuleOperationsRequest())

    assert report.evaluation == "unavailable"
    assert report.summaries == ()
    assert tuple(item.code for item in report.notices) == (
        VITRINE_ATTENTION_WORKSPACE_REQUIRED,
    )


def test_class_scoped_attention_is_explicitly_unavailable_without_native_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_native_call(*args: object, **kwargs: object) -> object:
        raise AssertionError("native attention must not run for class scope")

    monkeypatch.setattr(
        "vitrine.operations_provider.evaluate_vitrine_attention",
        unexpected_native_call,
    )

    report = evaluate_vitrine_attention_for_core(
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            active_school_year="2026-2027",
            class_id="english-10",
        )
    )

    assert report.evaluation == "unavailable"
    assert report.summaries == ()
    assert tuple(item.code for item in report.notices) == (
        VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED,
    )


def test_native_attention_maps_only_core_supported_fields() -> None:
    native = VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=7,
        summaries=(
            VitrineAttentionSummary(
                code="vitrine_selection_decision_pending",
                label="Selection decision pending",
                count=2,
                count_unit="selection_proposals",
                attention_class="workflow",
                portfolio_id="portfolio-cross-class",
                reason_codes=("proposal_undecided",),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_review",
                    portfolio_id="portfolio-cross-class",
                ),
            ),
        ),
        notices=(
            VitrineAttentionNotice(
                code="vitrine_attention_partial",
                summary=(
                    "Some Vitrine attention sources could not be evaluated safely; "
                    "available summaries are still shown."
                ),
            ),
        ),
    )

    report = project_vitrine_attention_to_core(native)

    assert validate_module_attention_report(
        report, expected_module_id=VITRINE_MODULE_ID
    ) is report
    assert report.evaluation == "evaluated"
    assert len(report.summaries) == 1
    summary = report.summaries[0]
    assert summary.code == "vitrine_selection_decision_pending"
    assert summary.label == "Selection decision pending"
    assert summary.count == 2
    assert summary.class_id is None
    assert summary.work_ref is None
    assert summary.action == ModuleOwnerActionRef(
        module_id="vitrine",
        action_id="open_candidate_review",
    )
    assert "portfolio-cross-class" not in summary.action.action_id
    assert tuple(item.code for item in report.notices) == (
        "vitrine_attention_partial",
    )


def test_native_unavailable_remains_unavailable_not_empty_success() -> None:
    native = VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="unavailable",
        observed_state_revision=None,
        summaries=(),
        notices=(
            VitrineAttentionNotice(
                code="vitrine_attention_unavailable",
                summary="Vitrine attention could not be evaluated safely.",
            ),
        ),
    )

    report = project_vitrine_attention_to_core(native)

    assert report.evaluation == "unavailable"
    assert report.summaries == ()
    assert tuple(item.code for item in report.notices) == (
        "vitrine_attention_unavailable",
    )
