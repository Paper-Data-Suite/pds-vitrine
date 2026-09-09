from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vitrine.current_portfolio_build import (
    CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
    CurrentPortfolioBuildError,
    prepare_current_portfolio_build,
)
from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    ProfileRevisionRef,
    SnapshotSeries,
)
from vitrine.working_composition import (
    WorkingCompositionAudienceSummary,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
    WorkingCompositionRequirementSummary,
    WorkingCompositionReviewSummary,
)

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_showcase",
    profile_revision=2,
)
RULE = WorkingCompositionAudienceSummary(
    audience_rule_id="external_review",
    audience_class="external_reviewer",
    purpose="Bounded external review",
    allowed_content_classes=("reflection", "student_work"),
    prohibited_content_classes=("private_teacher_note",),
    required_review_classes=("privacy_review", "rights_review"),
    presentation_class="showcase",
    retention_policy_reference="policy_7",
)


def _requirement(
    requirement_id: str, review_class: str
) -> WorkingCompositionRequirementSummary:
    return WorkingCompositionRequirementSummary(
        requirement_id=requirement_id,
        title=requirement_id,
        statement=requirement_id,
        requirement_kind="audience",
        obligation="required",
        scope_kind="audience",
        scope_reference="external_review",
        satisfaction_class=review_class,
        status="audience_stage",
        related_to_frozen_inventory=True,
        associated_unresolved_obligation_codes=(),
    )


def _review(
    review_id: str,
    requirement_id: str,
    *,
    decision: str = "approved",
    requires_attention: bool = False,
) -> WorkingCompositionReviewSummary:
    return WorkingCompositionReviewSummary(
        curation_review_decision_id=review_id,
        decision=decision,
        approval_requirement_id=requirement_id,
        target_scope="composition",
        target_references=(),
        required_follow_up_codes=(),
        requires_attention=requires_attention,
    )


def _working(
    *,
    disposition: str = "reuse_exact_current",
    unplaced_selection_ids: tuple[str, ...] = (),
    unresolved_obligation_codes: tuple[str, ...] = (),
    reviews: tuple[WorkingCompositionReviewSummary, ...] | None = None,
) -> WorkingCompositionPreparation:
    if reviews is None:
        reviews = (
            _review("review_privacy", "privacy_requirement"),
            _review("review_rights", "rights_requirement"),
        )
    payload = WorkingCompositionPayloadPreview(
        selection_ids=("selection_1",),
        placement_ids=("placement_1",),
        arrangement_ids=("arrangement_1",),
        included_rationale_ids=(),
        included_curation_revisions=(),
        applicable_review_decision_ids=tuple(
            item.curation_review_decision_id for item in reviews
        ),
        related_profile_requirement_ids=(
            "privacy_requirement",
            "rights_requirement",
        ),
        unresolved_obligation_codes=unresolved_obligation_codes,
        coherence_state=(
            "coherent_with_unresolved_obligations"
            if unresolved_obligation_codes
            else "coherent"
        ),
    )
    return WorkingCompositionPreparation(
        contract_version="vitrine_guided_working_composition_v1",
        observed_state_revision=11,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision_id="profile_showcase",
        profile_revision_number=2,
        observed_composition_pointer_revision=4,
        current_composition_revision=3,
        predicted_composition_revision=3,
        predecessor_composition_revision=2,
        predicted_composition_pointer_revision=4,
        disposition=disposition,
        payload=payload,
        sections=(),
        selections=(),
        unplaced_selection_ids=unplaced_selection_ids,
        requirements=(
            _requirement("privacy_requirement", "privacy_review"),
            _requirement("rights_requirement", "rights_review"),
        ),
        source_observations=(),
        reviews=reviews,
        audience_rules=(RULE,),
        requested_composition_note=None,
        composition_note_will_persist=False,
        preparation_fingerprint="a" * 64,
    )


def _context(context_id: str) -> AudienceContext:
    return AudienceContext(
        audience_context_id=context_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        audience_rule_id=RULE.audience_rule_id,
        audience_class=RULE.audience_class,
        purpose=RULE.purpose,
        subject_scope="portfolio_subject",
        allowed_content_classes=RULE.allowed_content_classes,
        prohibited_content_classes=RULE.prohibited_content_classes,
        required_review_classes=RULE.required_review_classes,
        presentation_class=RULE.presentation_class,
        retention_policy_reference=RULE.retention_policy_reference,
        created_at=NOW,
        created_by=ACTOR,
    )


def _series(series_id: str, context_id: str) -> SnapshotSeries:
    return SnapshotSeries(
        snapshot_series_id=series_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        snapshot_purpose=RULE.purpose,
        audience_context_id=context_id,
        created_at=NOW,
        created_by=ACTOR,
    )


def _patch_state(monkeypatch: pytest.MonkeyPatch, working, records=()) -> None:
    import vitrine.current_portfolio_build as module

    monkeypatch.setattr(
        module,
        "prepare_working_composition",
        lambda *_args, **_kwargs: working,
    )
    current = type("Current", (), {"state_revision": working.observed_state_revision})()
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (current, tuple(records)),
    )


def test_exact_current_context_and_series_are_reused_without_writes(
    monkeypatch,
) -> None:
    working = _working()
    context = _context("audience_1")
    series = _series("series_1", context.audience_context_id)
    _patch_state(monkeypatch, working, (context, series))

    prepared = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )

    assert prepared.contract_version == CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION
    assert prepared.working_composition_disposition == "reuse_exact_current"
    assert prepared.audience_context.disposition == "reuse"
    assert prepared.audience_context.selected_audience_context_id == "audience_1"
    assert prepared.snapshot_series.disposition == "reuse"
    assert prepared.snapshot_series.selected_snapshot_series_id == "series_1"
    assert prepared.missing_required_review_classes == ()
    assert prepared.blocking_reasons == ()
    assert prepared.ready_for_plan_execution is True
    assert len(prepared.preparation_fingerprint) == 64


def test_stale_working_composition_and_unplaced_selection_block(monkeypatch) -> None:
    working = _working(
        disposition="create_successor",
        unplaced_selection_ids=("selection_1",),
    )
    _patch_state(monkeypatch, working)

    prepared = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )

    assert prepared.audience_context.disposition == "create"
    assert prepared.snapshot_series.disposition == "create"
    assert "working_composition_requires_freeze" in prepared.blocking_reasons
    assert "unplaced_selections" in prepared.blocking_reasons
    assert prepared.ready_for_plan_execution is False


def test_duplicate_exact_audience_contexts_require_explicit_choice(monkeypatch) -> None:
    working = _working()
    context_a = _context("audience_a")
    context_b = _context("audience_b")
    _patch_state(monkeypatch, working, (context_b, context_a))

    prepared = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )

    assert prepared.audience_context.disposition == "requires_choice"
    assert prepared.audience_context.selected_audience_context_id is None
    assert prepared.audience_context.matching_audience_context_ids == (
        "audience_a",
        "audience_b",
    )
    assert prepared.snapshot_series.resolution_deferred_for_audience_context is True
    assert "audience_context_choice_required" in prepared.blocking_reasons
    assert "snapshot_series_choice_required" not in prepared.blocking_reasons


def test_explicit_context_and_series_choices_resolve_ambiguity(monkeypatch) -> None:
    working = _working()
    context_a = _context("audience_a")
    context_b = _context("audience_b")
    series_a = _series("series_a", "audience_b")
    series_b = _series("series_b", "audience_b")
    _patch_state(monkeypatch, working, (context_a, context_b, series_a, series_b))

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="external_review",
        audience_context_id="audience_b",
        snapshot_series_id="series_b",
    )

    assert prepared.audience_context.disposition == "reuse"
    assert prepared.audience_context.selected_audience_context_id == "audience_b"
    assert prepared.snapshot_series.disposition == "reuse"
    assert prepared.snapshot_series.selected_snapshot_series_id == "series_b"
    assert prepared.blocking_reasons == ()


def test_duplicate_exact_series_require_explicit_choice(monkeypatch) -> None:
    working = _working()
    context = _context("audience_1")
    _patch_state(
        monkeypatch,
        working,
        (context, _series("series_b", "audience_1"), _series("series_a", "audience_1")),
    )

    prepared = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )

    assert prepared.snapshot_series.disposition == "requires_choice"
    assert prepared.snapshot_series.selected_snapshot_series_id is None
    assert prepared.snapshot_series.matching_snapshot_series_ids == (
        "series_a",
        "series_b",
    )
    assert "snapshot_series_choice_required" in prepared.blocking_reasons


def test_missing_exact_required_review_class_blocks(monkeypatch) -> None:
    working = _working(
        reviews=(
            _review("review_privacy", "privacy_requirement"),
            _review(
                "review_rights",
                "rights_requirement",
                decision="changes_requested",
                requires_attention=True,
            ),
        )
    )
    _patch_state(monkeypatch, working)

    prepared = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )

    assert prepared.missing_required_review_classes == ("rights_review",)
    assert "missing_required_reviews" in prepared.blocking_reasons
    rights = next(
        item
        for item in prepared.required_reviews
        if item.review_class == "rights_review"
    )
    assert rights.profile_requirement_ids == ("rights_requirement",)
    assert rights.satisfying_review_decision_ids == ()


def test_unresolved_obligations_require_exact_separate_acknowledgement(
    monkeypatch,
) -> None:
    working = _working(
        unresolved_obligation_codes=("reflection_required", "approval_required")
    )
    _patch_state(monkeypatch, working)

    first = prepare_current_portfolio_build(
        ".", "portfolio_1", audience_rule_id="external_review"
    )
    assert first.acknowledged_obligation_codes == ()
    assert first.obligation_acknowledgement_complete is False
    assert "unresolved_obligations_acknowledgement_required" in first.blocking_reasons

    second = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="external_review",
        acknowledged_obligation_codes=("approval_required", "reflection_required"),
    )
    assert second.acknowledged_obligation_codes == (
        "reflection_required",
        "approval_required",
    )
    assert second.obligation_acknowledgement_complete is True
    assert (
        "unresolved_obligations_acknowledgement_required"
        not in second.blocking_reasons
    )
    assert second.preparation_fingerprint != first.preparation_fingerprint


def test_acknowledgement_cannot_claim_noncurrent_obligation(monkeypatch) -> None:
    working = _working(unresolved_obligation_codes=("reflection_required",))
    _patch_state(monkeypatch, working)

    with pytest.raises(CurrentPortfolioBuildError) as caught:
        prepare_current_portfolio_build(
            ".",
            "portfolio_1",
            audience_rule_id="external_review",
            acknowledged_obligation_codes=("approval_required",),
        )

    assert caught.value.code == "current_portfolio_build.invalid_request"


def test_state_change_after_working_composition_preparation_fails_closed(
    monkeypatch,
) -> None:
    import vitrine.current_portfolio_build as module

    working = _working()
    monkeypatch.setattr(
        module,
        "prepare_working_composition",
        lambda *_args, **_kwargs: working,
    )
    current = type(
        "Current",
        (),
        {"state_revision": working.observed_state_revision + 1},
    )()
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (current, ()),
    )

    with pytest.raises(CurrentPortfolioBuildError) as caught:
        prepare_current_portfolio_build(
            ".", "portfolio_1", audience_rule_id="external_review"
        )

    assert caught.value.code == "current_portfolio_build.state_changed"
