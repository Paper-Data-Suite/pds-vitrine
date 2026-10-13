from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import vitrine.portfolio_completion as completion_module
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
)
from vitrine.models import ProfileRevisionRef
from vitrine.portfolio_completion import (
    PORTFOLIO_COMPLETION_CONTRACT_VERSION,
    PortfolioCompletionOperationalStatus,
    project_portfolio_completion,
    project_portfolio_completion_operational_status,
)
from vitrine.working_composition import (
    WORKING_COMPOSITION_CONTRACT_VERSION,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
    WorkingCompositionRequirementSummary,
)

_NOW = datetime(2026, 10, 8, tzinfo=UTC)
_PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile",
    profile_revision=1,
)


def _working(
    *,
    current_revision: int | None = 2,
    predicted_revision: int = 2,
    disposition: str = "reuse_exact_current",
    requirements: tuple[WorkingCompositionRequirementSummary, ...] = (),
) -> WorkingCompositionPreparation:
    return WorkingCompositionPreparation(
        contract_version=WORKING_COMPOSITION_CONTRACT_VERSION,
        observed_state_revision=7,
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        profile_binding_id="binding",
        profile_revision_id="profile",
        profile_revision_number=1,
        observed_composition_pointer_revision=2,
        current_composition_revision=current_revision,
        predicted_composition_revision=predicted_revision,
        predecessor_composition_revision=1,
        predicted_composition_pointer_revision=2,
        disposition=disposition,
        payload=WorkingCompositionPayloadPreview(
            selection_ids=(),
            placement_ids=(),
            arrangement_ids=(),
            included_rationale_ids=(),
            included_curation_revisions=(),
            applicable_review_decision_ids=(),
            related_profile_requirement_ids=(),
            unresolved_obligation_codes=(),
            coherence_state="coherent",
        ),
        sections=(),
        selections=(),
        unplaced_selection_ids=(),
        requirements=requirements,
        source_observations=(),
        reviews=(),
        audience_rules=(),
        requested_composition_note=None,
        composition_note_will_persist=disposition != "reuse_exact_current",
        preparation_fingerprint="a" * 64,
        requirement_contents=(),
    )


def _export() -> CompletedPortfolioExport:
    return CompletedPortfolioExport(
        snapshot_export_artifact_id="export",
        export_format="directory_package",
        export_contract_version="snapshot_directory_export_v1",
        relative_path="exports/export",
        generated_at=_NOW,
        predecessor_export_artifact_id=None,
    )


def _presentation() -> CompletedPortfolioPresentation:
    return CompletedPortfolioPresentation(
        presentation_artifact_id="presentation",
        snapshot_export_artifact_id="export",
        presentation_class="student_portfolio",
        presentation_contract_version="student_portfolio_presentation_v1",
        renderer_id="renderer",
        renderer_version="1",
        renderer_contract_version="renderer_v1",
        relative_path="presentations/presentation",
        html_relative_path="presentations/presentation/portfolio.html",
        printable_pdf_relative_path="presentations/presentation/portfolio.pdf",
        generated_at=_NOW,
        predecessor_presentation_artifact_id=None,
    )


def _history(
    *,
    composition_revision: int | None = None,
    with_export: bool = True,
    with_presentation: bool = False,
    is_current: bool = False,
    presentation_class: str = "student_portfolio",
) -> CompletedPortfolioHistory:
    if composition_revision is None:
        return CompletedPortfolioHistory(
            contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
            portfolio_id="portfolio",
            portfolio_subject_id="subject",
            series=(),
        )

    edition = CompletedPortfolioEdition(
        snapshot_series_id="series",
        edition_number=1,
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        profile_binding_id="binding",
        profile_revision=_PROFILE,
        composition_revision=composition_revision,
        audience_context_id="audience",
        created_at=_NOW,
        predecessor_edition=None,
        is_current=is_current,
        exports=(_export(),) if with_export else (),
        presentations=(_presentation(),) if with_presentation else (),
    )
    series = CompletedPortfolioSeries(
        snapshot_series_id="series",
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        snapshot_purpose="student portfolio",
        audience_context_id="audience",
        audience_class="student",
        audience_purpose="student review",
        presentation_class=presentation_class,
        created_at=_NOW,
        predecessor_series_id=None,
        current_edition_number=1 if is_current else None,
        editions=(edition,),
    )
    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        series=(series,),
    )


def test_ready_to_build_without_completed_history() -> None:
    projection = project_portfolio_completion(_working(), _history())

    assert projection.contract_version == PORTFOLIO_COMPLETION_CONTRACT_VERSION
    assert projection.state == "ready_to_build"
    assert projection.can_build_current
    assert not projection.has_required_work
    assert not projection.is_complete
    assert projection.historical_completed_edition_count == 0


def test_exact_completed_edition_does_not_require_current_pointer() -> None:
    projection = project_portfolio_completion(
        _working(current_revision=2),
        _history(composition_revision=2, is_current=False),
    )

    assert projection.state == "complete"
    assert projection.is_complete
    assert len(projection.exact_current_editions) == 1
    assert projection.exact_current_editions[0].is_current is False
    assert projection.historical_completed_edition_count == 1


def test_historical_completion_with_newer_frozen_composition_is_update_ready() -> None:
    projection = project_portfolio_completion(
        _working(current_revision=2),
        _history(composition_revision=1),
    )

    assert projection.state == "update_ready"
    assert projection.can_build_current
    assert projection.exact_current_editions == ()
    assert projection.historical_completed_edition_count == 1


def test_unfrozen_changed_composition_remains_required_work() -> None:
    projection = project_portfolio_completion(
        _working(
            current_revision=1,
            predicted_revision=2,
            disposition="create_successor",
        ),
        _history(composition_revision=1),
    )

    assert projection.state == "required_work"
    assert projection.has_required_work
    assert "working_composition_create_successor" in projection.required_reason_codes


def test_required_requirement_blocks_historical_completion() -> None:
    requirement = WorkingCompositionRequirementSummary(
        requirement_id="reflection",
        title="Reflection",
        statement="Student reflection is required.",
        requirement_kind="reflection",
        obligation="required",
        scope_kind="section",
        scope_reference="reflection",
        satisfaction_class="reflection_presence",
        status="unresolved_missing",
        related_to_frozen_inventory=True,
        associated_unresolved_obligation_codes=(),
    )

    projection = project_portfolio_completion(
        _working(requirements=(requirement,)),
        _history(composition_revision=2),
    )

    assert projection.state == "required_work"
    assert "requirement_unresolved_missing" in projection.required_reason_codes


def test_operational_blocker_precedes_otherwise_complete_state() -> None:
    projection = project_portfolio_completion(
        _working(),
        _history(composition_revision=2),
        operational_status=PortfolioCompletionOperationalStatus(
            recovery_reason_codes=("snapshot_attempt_incomplete",),
        ),
    )

    assert projection.state == "recovery_or_integrity_blocked"
    assert projection.recovery_reason_codes == ("snapshot_attempt_incomplete",)


def test_missing_student_presentation_is_separate_from_technical_completion() -> None:
    missing = project_portfolio_completion(
        _working(),
        _history(composition_revision=2, with_presentation=False),
    )
    present = project_portfolio_completion(
        _working(),
        _history(composition_revision=2, with_presentation=True),
    )

    assert missing.state == "complete"
    assert missing.student_presentation_missing is True
    assert missing.exact_current_editions[0].student_presentation_available is False

    assert present.state == "complete"
    assert present.student_presentation_missing is False
    assert present.exact_current_editions[0].student_presentation_available is True


def test_sealed_edition_without_export_is_not_technical_completion() -> None:
    projection = project_portfolio_completion(
        _working(),
        _history(composition_revision=2, with_export=False),
        operational_status=PortfolioCompletionOperationalStatus(
            recovery_reason_codes=("snapshot_export_missing",),
        ),
    )

    assert projection.state == "recovery_or_integrity_blocked"
    assert projection.historical_completed_edition_count == 0
    assert projection.exact_current_editions == ()


def test_empty_canonical_snapshot_state_has_no_operational_blocker() -> None:
    status = project_portfolio_completion_operational_status(
        (),
        portfolio_id="portfolio",
    )

    assert status.recovery_reason_codes == ()
    assert status.integrity_reason_codes == ()
    assert status.blocked is False


def test_prepare_completion_composes_existing_read_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working = _working()
    history = _history(composition_revision=2)
    operational = PortfolioCompletionOperationalStatus()

    monkeypatch.setattr(
        completion_module,
        "prepare_working_composition",
        lambda workspace_root, portfolio_id: working,
    )
    monkeypatch.setattr(
        completion_module,
        "load_current_records_with_state",
        lambda workspace_root: (SimpleNamespace(state_revision=7), ()),
    )
    monkeypatch.setattr(
        completion_module,
        "project_completed_portfolio_history",
        lambda records, *, portfolio_id: history,
    )
    monkeypatch.setattr(
        completion_module,
        "project_portfolio_completion_operational_status",
        lambda records, *, portfolio_id: operational,
    )

    projection = completion_module.prepare_portfolio_completion(
        tmp_path,
        "portfolio",
    )

    assert projection.state == "complete"
    assert projection.observed_state_revision == 7


def test_projection_rejects_mismatched_history_identity() -> None:
    bad_history = CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="other_portfolio",
        portfolio_subject_id="subject",
        series=(),
    )

    with pytest.raises(
        completion_module.PortfolioCompletionError,
        match="exact Working Portfolio",
    ):
        project_portfolio_completion(_working(), bad_history)


# Issue #104 Slice 5: completion and Attention transitions.
def test_issue104_combined_recovery_and_integrity_keep_completed_history_visible() -> None:
    """An operational blocker must not erase a verified historical Export."""
    status = PortfolioCompletionOperationalStatus(
        recovery_reason_codes=("snapshot_attempt_incomplete",),
        integrity_reason_codes=("snapshot_attempt_result_conflict",),
    )
    projection = project_portfolio_completion(
        _working(),
        _history(composition_revision=2, with_export=True, with_presentation=False),
        operational_status=status,
    )

    assert projection.state == "recovery_or_integrity_blocked"
    assert not projection.can_build_current
    assert projection.historical_completed_edition_count == 1
    assert len(projection.exact_current_editions) == 1
    assert projection.exact_current_editions[0].export_count == 1
    assert not projection.exact_current_editions[0].is_current
    assert projection.student_presentation_missing is True
    assert projection.recovery_reason_codes == ("snapshot_attempt_incomplete",)
    assert projection.integrity_reason_codes == ("snapshot_attempt_result_conflict",)


@pytest.mark.parametrize(
    ("reason_kind", "reason_code"),
    (
        ("recovery", "snapshot_export_missing"),
        ("recovery", "snapshot_attempt_incomplete"),
        ("integrity", "snapshot_attempt_result_conflict"),
        ("integrity", "snapshot_durability_uncertain"),
    ),
)
def test_issue104_operational_blockers_override_update_ready(
    reason_kind: str, reason_code: str
) -> None:
    """An older Edition stays historical, even when updates are blocked."""
    operational = PortfolioCompletionOperationalStatus(
        recovery_reason_codes=(reason_code,) if reason_kind == "recovery" else (),
        integrity_reason_codes=(reason_code,) if reason_kind == "integrity" else (),
    )
    projection = project_portfolio_completion(
        _working(current_revision=2),
        _history(composition_revision=1),
        operational_status=operational,
    )

    assert projection.state == "recovery_or_integrity_blocked"
    assert not projection.can_build_current
    assert projection.historical_completed_edition_count == 1
    assert projection.exact_current_editions == ()
    assert reason_code in (
        *projection.recovery_reason_codes,
        *projection.integrity_reason_codes,
    )
