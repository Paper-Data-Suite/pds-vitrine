from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import vitrine.attention as attention
from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VITRINE_ATTENTION_V2_CONTRACT_VERSION,
    VitrineAttentionQuery,
    evaluate_vitrine_attention_v2,
)
from vitrine.candidate_inbox import CandidateInboxItem
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioSeries,
)
from vitrine.models import ProfileRevisionRef
from vitrine.portfolio_completion import PortfolioCompletionOperationalStatus
from vitrine.working_composition import (
    WORKING_COMPOSITION_CONTRACT_VERSION,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
    WorkingCompositionRequirementSummary,
)

_NOW = datetime(2026, 10, 11, tzinfo=UTC)
_PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile",
    profile_revision=1,
)


def _preparation(
    *,
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
        current_composition_revision=2,
        predicted_composition_revision=2,
        predecessor_composition_revision=1,
        predicted_composition_pointer_revision=2,
        disposition="reuse_exact_current",
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
        composition_note_will_persist=False,
        preparation_fingerprint="a" * 64,
        requirement_contents=(),
    )


def _item(
    *,
    outcome: str | None = "eligible",
    selected_state: str = "unselected",
    stale_state: str | None = None,
    eligible_sections: tuple[str, ...] = ("later",),
) -> CandidateInboxItem:
    return CandidateInboxItem(
        contract_version="vitrine_candidate_inbox_v1",
        entry_id="candidate:candidate",
        candidate_id="candidate",
        current_evaluation_id="evaluation",
        current_resolution="current",
        portfolio_id="portfolio",
        portfolio_label="Portfolio",
        portfolio_subject_id="subject",
        subject_label="Student",
        profile_binding_id="binding",
        portfolio_profile_id="profile",
        profile_revision=1,
        profile_label="Profile",
        profile_purpose="improvement",
        source_display_label="Evidence",
        producer_module_id="scoreform",
        evaluation_outcome=outcome,
        candidate_condition="clear",
        stale_state=stale_state,
        stale_reason_codes=(
            ("publication_changed",)
            if stale_state == "stale"
            else ()
        ),
        attention_needed=stale_state in {"stale", "unresolved"},
        attention_reason_codes=(
            ("candidate_evaluation_unresolved",)
            if stale_state == "unresolved"
            else ()
        ),
        selected_state=selected_state,
        active_selection_ids=(
            ("selection",)
            if selected_state == "selected"
            else ()
        ),
        historical_selection_ids=(),
        evaluated_at=_NOW,
        eligible_section_ids=eligible_sections,
    )


def _history() -> CompletedPortfolioHistory:
    export = CompletedPortfolioExport(
        snapshot_export_artifact_id="export",
        export_format="directory_package",
        export_contract_version="snapshot_directory_export_v1",
        relative_path="exports/export",
        generated_at=_NOW,
        predecessor_export_artifact_id=None,
    )
    edition = CompletedPortfolioEdition(
        snapshot_series_id="series",
        edition_number=1,
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        profile_binding_id="binding",
        profile_revision=_PROFILE,
        composition_revision=2,
        audience_context_id="audience",
        created_at=_NOW,
        predecessor_edition=None,
        is_current=False,
        exports=(export,),
        presentations=(),
    )
    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="portfolio",
        portfolio_subject_id="subject",
        series=(
            CompletedPortfolioSeries(
                snapshot_series_id="series",
                portfolio_id="portfolio",
                portfolio_subject_id="subject",
                snapshot_purpose="student portfolio",
                audience_context_id="audience",
                audience_class="student",
                audience_purpose="student review",
                presentation_class="student_portfolio",
                created_at=_NOW,
                predecessor_series_id=None,
                current_edition_number=None,
                editions=(edition,),
            ),
        ),
    )


def _requirement(
    *,
    kind: str,
    scope_reference: str,
) -> WorkingCompositionRequirementSummary:
    return WorkingCompositionRequirementSummary(
        requirement_id=f"{kind}_requirement",
        title="Requirement",
        statement="Required.",
        requirement_kind=kind,
        obligation="required",
        scope_kind="section",
        scope_reference=scope_reference,
        satisfaction_class=(
            "placement_cardinality"
            if kind == "section"
            else "reflection_presence"
        ),
        status="unresolved_missing",
        related_to_frozen_inventory=True,
        associated_unresolved_obligation_codes=(),
    )


def _codes(
    facts: tuple[attention._AttentionV2Fact, ...],
) -> tuple[str, ...]:
    return tuple(item.code for item in facts)


def test_v1_contract_remains_frozen_while_v2_is_distinct() -> None:
    assert (
        VITRINE_ATTENTION_CONTRACT_VERSION
        == "vitrine_attention_next_actions_v1"
    )
    assert (
        VITRINE_ATTENTION_V2_CONTRACT_VERSION
        == "vitrine_attention_next_actions_v2"
    )


def test_unused_eligible_candidate_is_optional_when_requirements_are_satisfied() -> None:
    facts = attention._v2_candidate_facts(
        (_item(),),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(),
    )

    assert _codes(facts) == ("vitrine_candidate_optional_evidence",)
    assert facts[0].requirement_level == "opportunity"


def test_candidate_is_required_when_it_can_fill_missing_section() -> None:
    facts = attention._v2_candidate_facts(
        (_item(eligible_sections=("later",)),),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(
            requirements=(
                _requirement(
                    kind="section",
                    scope_reference="later",
                ),
            )
        ),
    )

    assert _codes(facts) == ("vitrine_candidate_review_pending",)
    assert facts[0].requirement_level == "required"


def test_missing_reflection_does_not_make_extra_evidence_required() -> None:
    facts = attention._v2_candidate_facts(
        (_item(),),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(
            requirements=(
                _requirement(
                    kind="reflection",
                    scope_reference="reflection",
                ),
            )
        ),
    )

    assert _codes(facts) == ("vitrine_candidate_optional_evidence",)


def test_unused_stale_candidate_is_optional() -> None:
    facts = attention._v2_candidate_facts(
        (_item(stale_state="stale"),),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(),
    )

    assert "vitrine_candidate_optional_stale" in _codes(facts)
    assert "vitrine_candidate_evaluation_stale" not in _codes(facts)


def test_selected_stale_candidate_remains_required() -> None:
    facts = attention._v2_candidate_facts(
        (
            _item(
                selected_state="selected",
                stale_state="stale",
            ),
        ),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(),
    )

    assert "vitrine_candidate_evaluation_stale" in _codes(facts)
    assert "vitrine_candidate_optional_stale" not in _codes(facts)


def test_unused_unresolved_candidate_is_optional() -> None:
    facts = attention._v2_candidate_facts(
        (
            _item(
                outcome="unresolved",
                stale_state="unresolved",
            ),
        ),
        SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
        (),
        _preparation(),
    )

    assert _codes(facts) == ("vitrine_candidate_optional_unresolved",)


def test_v2_evaluator_reports_complete_and_optional_extra_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inbox = SimpleNamespace(
        observed_state_revision=7,
        truncated=False,
        items=(_item(),),
    )
    preparation = _preparation()
    history = _history()

    monkeypatch.setattr(
        attention,
        "load_current_records_with_state",
        lambda root: (
            SimpleNamespace(state_revision=7),
            (),
        ),
    )
    monkeypatch.setattr(
        attention,
        "_portfolio_ids",
        lambda records, request: ("portfolio",),
    )
    monkeypatch.setattr(
        attention,
        "project_curation_state",
        lambda records: SimpleNamespace(
            selections=(),
            proposals=(),
            decisions=(),
        ),
    )
    monkeypatch.setattr(
        attention,
        "list_candidate_inbox",
        lambda root, query: inbox,
    )
    monkeypatch.setattr(
        attention,
        "prepare_working_composition",
        lambda root, portfolio_id: preparation,
    )
    monkeypatch.setattr(
        attention,
        "project_completed_portfolio_history",
        lambda records, *, portfolio_id: history,
    )
    monkeypatch.setattr(
        attention,
        "project_portfolio_completion_operational_status",
        lambda records, *, portfolio_id: (
            PortfolioCompletionOperationalStatus()
        ),
    )
    monkeypatch.setattr(
        attention,
        "_snapshot_facts",
        lambda *args, **kwargs: ((), False),
    )
    monkeypatch.setattr(
        attention,
        "project_snapshot_state",
        lambda records: SimpleNamespace(),
    )
    monkeypatch.setattr(
        attention,
        "load_current_state",
        lambda root: SimpleNamespace(state_revision=7),
    )

    report = evaluate_vitrine_attention_v2(
        tmp_path,
        VitrineAttentionQuery(portfolio_id="portfolio"),
    )
    by_code = {
        item.code: item
        for item in report.summaries
    }

    assert (
        report.contract_version
        == VITRINE_ATTENTION_V2_CONTRACT_VERSION
    )
    assert "vitrine_candidate_review_pending" not in by_code
    assert (
        by_code[
            "vitrine_candidate_optional_evidence"
        ].requirement_level
        == "opportunity"
    )
    assert (
        by_code["vitrine_portfolio_complete"].requirement_level
        == "status"
    )
    assert (
        by_code[
            "vitrine_student_presentation_missing"
        ].requirement_level
        == "opportunity"
    )


# Issue #104 Slice 5: completion and Attention transitions.
def _issue104_attention_with_read_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    preparation: WorkingCompositionPreparation,
    history: CompletedPortfolioHistory,
    operational: PortfolioCompletionOperationalStatus,
) -> attention.VitrineAttentionReportV2:
    """Compose actual completion/Attention projections from supplied read models.

    Only the persistence, inbox, and snapshot-fact read boundaries are stubbed.
    This is a projection matrix, not a substitute for custody verification.
    """
    monkeypatch.setattr(
        attention,
        "load_current_records_with_state",
        lambda _root: (SimpleNamespace(state_revision=7), ()),
    )
    monkeypatch.setattr(
        attention,
        "load_current_state",
        lambda _root: SimpleNamespace(state_revision=7),
    )
    monkeypatch.setattr(attention, "_portfolio_ids", lambda _records, _query: ("portfolio",))
    monkeypatch.setattr(
        attention,
        "project_curation_state",
        lambda _records: SimpleNamespace(selections=(), proposals=(), decisions=()),
    )
    monkeypatch.setattr(
        attention,
        "list_candidate_inbox",
        lambda _root, _query: SimpleNamespace(
            observed_state_revision=7,
            truncated=False,
            items=(_item(),),
        ),
    )
    monkeypatch.setattr(
        attention,
        "prepare_working_composition",
        lambda _root, _portfolio_id: preparation,
    )
    monkeypatch.setattr(
        attention,
        "project_completed_portfolio_history",
        lambda _records, *, portfolio_id: history,
    )
    monkeypatch.setattr(
        attention,
        "project_portfolio_completion_operational_status",
        lambda _records, *, portfolio_id: operational,
    )
    monkeypatch.setattr(
        attention,
        "project_snapshot_state",
        lambda _records: SimpleNamespace(),
    )
    monkeypatch.setattr(attention, "_snapshot_facts", lambda *args, **kwargs: ((), False))
    return evaluate_vitrine_attention_v2(
        tmp_path,
        VitrineAttentionQuery(portfolio_id="portfolio"),
    )


@pytest.mark.parametrize(
    ("scenario", "expected_status", "expected_action", "expected_reason"),
    (
        ("complete", "complete", "open_completed_portfolio_editions", None),
        ("historical_new_frozen", "update_ready", "open_build_export_current_portfolio", None),
        ("historical_unfrozen", "required_work", None, "working_composition_create_successor"),
        ("missing_export", "recovery_or_integrity_blocked", None, "snapshot_export_missing"),
        ("incomplete_attempt", "recovery_or_integrity_blocked", None, "snapshot_attempt_incomplete"),
        ("integrity_conflict", "recovery_or_integrity_blocked", None, "snapshot_attempt_result_conflict"),
    ),
)
def test_issue104_attention_preserves_completion_and_teacher_next_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scenario: str,
    expected_status: str,
    expected_action: str | None,
    expected_reason: str | None,
) -> None:
    """Optional evidence must never erase completion, update, or blocked status."""
    from dataclasses import replace

    preparation = _preparation()
    history = _history()
    operational = PortfolioCompletionOperationalStatus()

    if scenario in {"historical_new_frozen", "historical_unfrozen"}:
        series = history.series[0]
        prior_edition = replace(series.editions[0], composition_revision=1)
        history = replace(
            history,
            series=(replace(series, editions=(prior_edition,)),),
        )
    if scenario == "historical_unfrozen":
        preparation = replace(
            preparation,
            current_composition_revision=1,
            predicted_composition_revision=2,
            disposition="create_successor",
            composition_note_will_persist=True,
        )
    elif scenario == "missing_export":
        series = history.series[0]
        exportless = replace(series.editions[0], exports=())
        history = replace(history, series=(replace(series, editions=(exportless,)),))
        operational = PortfolioCompletionOperationalStatus(
            recovery_reason_codes=("snapshot_export_missing",),
        )
    elif scenario == "incomplete_attempt":
        operational = PortfolioCompletionOperationalStatus(
            recovery_reason_codes=("snapshot_attempt_incomplete",),
        )
    elif scenario == "integrity_conflict":
        operational = PortfolioCompletionOperationalStatus(
            integrity_reason_codes=("snapshot_attempt_result_conflict",),
        )

    report = _issue104_attention_with_read_models(
        monkeypatch,
        tmp_path,
        preparation=preparation,
        history=history,
        operational=operational,
    )
    assert report.evaluation == "evaluated"
    assert report.observed_state_revision == 7
    assert report.notices == ()

    by_code = {summary.code: summary for summary in report.summaries}
    status_code = f"vitrine_portfolio_{expected_status}"
    assert status_code in by_code
    status = by_code[status_code]
    assert status.requirement_level == "status"
    assert status.portfolio_id == "portfolio"
    assert status.count == 1
    assert (status.next_action.action_id if status.next_action else None) == expected_action
    assert (expected_reason is None or expected_reason in status.reason_codes)
    assert sum(code.startswith("vitrine_portfolio_") for code in by_code) == 1

    assert "vitrine_candidate_review_pending" not in by_code
    assert by_code["vitrine_candidate_optional_evidence"].requirement_level == "opportunity"
    # A verified technical Export can still need a student Presentation, even
    # while an independent recovery or integrity condition blocks the workflow.
    if scenario in {"complete", "incomplete_attempt", "integrity_conflict"}:
        assert by_code["vitrine_student_presentation_missing"].requirement_level == "opportunity"
    else:
        assert "vitrine_student_presentation_missing" not in by_code
