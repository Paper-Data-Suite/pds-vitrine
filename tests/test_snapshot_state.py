from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    DigestReference,
    Portfolio,
    PortfolioProfileBinding,
    ProfileRevisionRef,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.snapshot_workflow import (
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotSeries,
)
from vitrine.snapshot_state import (
    collect_snapshot_state_issues,
    project_snapshot_state,
    snapshot_plan_fingerprint,
    validate_snapshot_state,
)

NOW = datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="snapshot_fixture_teacher",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_snapshot_fixture",
    profile_revision=1,
)


def _control_plane_records() -> tuple[object, ...]:
    portfolio = Portfolio(
        portfolio_id="portfolio_snapshot_fixture",
        portfolio_subject_id="subject_snapshot_fixture",
        created_at=NOW,
        created_by=ACTOR,
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="profile_binding_snapshot_fixture",
        portfolio_id=portfolio.portfolio_id,
        profile_revision=PROFILE,
        bound_at=NOW,
        bound_by=ACTOR,
    )
    audience = AudienceContext(
        audience_context_id="audience_snapshot_fixture",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=PROFILE,
        audience_rule_id="student_internal",
        audience_class="student",
        purpose="Fixture Snapshot build.",
        subject_scope="single_subject",
        allowed_content_classes=("reflection",),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=(),
        presentation_class="student_portfolio",
        retention_policy_reference=None,
        created_at=NOW,
        created_by=ACTOR,
    )
    composition = WorkingPortfolioCompositionRevision(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=PROFILE,
        composition_revision=1,
        selection_ids=(),
        placement_ids=(),
        arrangement_ids=(),
        created_at=NOW,
        created_by=ACTOR,
    )
    inventory = WorkingPortfolioCompositionInventory(
        portfolio_id=portfolio.portfolio_id,
        composition_revision=composition.composition_revision,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=PROFILE,
        included_rationale_ids=(),
        included_curation_revisions=(),
        applicable_review_decision_ids=(),
        related_profile_requirement_ids=(),
        unresolved_obligation_codes=(),
        coherence_state="coherent",
        created_at=NOW,
        created_by=ACTOR,
    )
    series = SnapshotSeries(
        snapshot_series_id="snapshot_series_1",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        snapshot_purpose="improvement",
        audience_context_id=audience.audience_context_id,
        created_at=NOW,
        created_by=ACTOR,
    )
    request = SnapshotBuildRequest(
        snapshot_build_request_id="snapshot_request_1",
        snapshot_series_id=series.snapshot_series_id,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=PROFILE,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        snapshot_purpose=series.snapshot_purpose,
        requested_export_formats=("directory_package",),
        requested_by=ACTOR,
        requested_at=NOW,
        idempotency_key="snapshot-request-retry-1",
    )
    entry = SnapshotEntryPlan(
        entry_plan_id="entry_plan_reflection",
        plan_position=1,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="01-reflection.md",
        media_type="text/markdown",
        renderer_id="vitrine_reflection_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_reflection_v1",
        renderer_configuration_digest=DigestReference(value="2" * 64),
        input_references=(
            SnapshotInputReference(
                record_type="working_portfolio_composition_revision",
                record_id=portfolio.portfolio_id,
                record_revision=composition.composition_revision,
            ),
        ),
    )
    export = SnapshotExportPlan(
        export_plan_id="directory_export_plan_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="1" * 64),
    )
    provisional_plan = SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_1",
        snapshot_build_request_id=request.snapshot_build_request_id,
        snapshot_series_id=series.snapshot_series_id,
        plan_revision=1,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=PROFILE,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        entry_plans=(entry,),
        export_plans=(export,),
        required_review_references=(),
        acknowledged_obligation_codes=(),
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        builder_contract_id="snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint="0" * 64,
    )
    plan = replace(
        provisional_plan,
        plan_fingerprint=snapshot_plan_fingerprint(provisional_plan),
    )
    attempt = SnapshotBuildAttempt(
        snapshot_build_attempt_id="snapshot_attempt_1",
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        attempt_number=1,
        builder_id="snapshot_builder",
        builder_version="1",
        started_at=NOW,
        staging_reference="snapshot_attempt_1",
        started_by=ACTOR,
    )
    return (
        portfolio,
        binding,
        audience,
        composition,
        inventory,
        series,
        request,
        plan,
        attempt,
    )


def test_valid_control_plane_state_accepts_incomplete_attempt_without_timestamp_inference() -> None:
    state = project_snapshot_state(_control_plane_records())

    assert state.result_for_attempt("snapshot_attempt_1") is None
    assert collect_snapshot_state_issues(state) == ()
    validate_snapshot_state(state)


def test_plan_fingerprint_change_is_detected_without_mutating_historical_plan() -> None:
    records = list(_control_plane_records())
    plan = next(item for item in records if isinstance(item, SnapshotBuildPlan))
    records[records.index(plan)] = replace(plan, plan_fingerprint="f" * 64)

    codes = {issue.code for issue in collect_snapshot_state_issues(project_snapshot_state(records))}
    assert "snapshot.plan_fingerprint_mismatch" in codes


def test_request_context_does_not_follow_a_different_composition_revision() -> None:
    records = list(_control_plane_records())
    request = next(item for item in records if isinstance(item, SnapshotBuildRequest))
    records[records.index(request)] = replace(request, composition_revision=2)

    codes = {issue.code for issue in collect_snapshot_state_issues(project_snapshot_state(records))}
    assert "snapshot.request_composition_mismatch" in codes
    assert "snapshot.request_inventory_mismatch" in codes
    assert "snapshot.plan_request_mismatch" in codes


def test_portable_casefold_path_collision_is_rejected_by_snapshot_state() -> None:
    records = list(_control_plane_records())
    plan = next(item for item in records if isinstance(item, SnapshotBuildPlan))
    first = plan.entry_plans[0]
    second = replace(
        first,
        entry_plan_id="entry_plan_reflection_2",
        plan_position=2,
        ordinal=2,
        target_relative_path="01-REFLECTION.md",
    )
    export = replace(
        plan.export_plans[0],
        included_entry_plan_ids=(first.entry_plan_id, second.entry_plan_id),
    )
    provisional = replace(
        plan,
        entry_plans=(first, second),
        export_plans=(export,),
        plan_fingerprint="0" * 64,
    )
    collided = replace(
        provisional,
        plan_fingerprint=snapshot_plan_fingerprint(provisional),
    )
    records[records.index(plan)] = collided

    codes = {issue.code for issue in collect_snapshot_state_issues(project_snapshot_state(records))}
    assert "snapshot.plan_path_collision" in codes
