from __future__ import annotations

from tests.profile_helpers import (
    ACTOR,
    NOW,
    improvement_family,
    improvement_requirements,
    improvement_revision,
)
from vitrine.models import (
    PortfolioProfileComposition,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileMigration,
    PortfolioProfileOverlayRevision,
    ProfileOverlayRequirement,
    ProfileOverlayRequirementChange,
    ProfileRequirementImpact,
    ProfileRevisionRef,
    record_from_dict,
    record_to_dict,
)
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.record_registry import identity_segments_for_record


def test_new_profile_records_round_trip_exactly() -> None:
    requirement = improvement_requirements(1)[0]
    assert record_from_dict(record_to_dict(requirement)) == requirement

    event = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id="profile_event_1",
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_growth", profile_revision=1
        ),
        event_kind="activated",
        event_at=NOW,
        effective_at=NOW,
        actor=ACTOR,
        reason="Approved for local use.",
    )
    assert record_from_dict(record_to_dict(event)) == event

    overlay = PortfolioProfileOverlayRevision(
        overlay_id="overlay_growth",
        overlay_revision=1,
        predecessor_overlay_revision=None,
        label="Local overlay",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=ACTOR,
        authority_reference="local_instructional_policy",
        component_revisions=(event.profile_revision,),
        requirement_changes=(
            ProfileOverlayRequirementChange(
                action="add",
                requirement=ProfileOverlayRequirement(
                    requirement_id="local_reflection",
                    requirement_kind="reflection",
                    obligation="required",
                    title="Local reflection",
                    statement="Include a local reflection.",
                    scope_kind="portfolio",
                    satisfaction_class="reflection_record",
                ),
            ),
        ),
    )
    assert record_from_dict(record_to_dict(overlay)) == overlay

    composition = PortfolioProfileComposition(
        profile_composition_id="profile_composition_1",
        effective_profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_growth_local", profile_revision=1
        ),
        component_profile_revisions=(event.profile_revision,),
        overlay_revisions=(overlay.reference,),
        composed_at=NOW,
        composed_by=ACTOR,
        authority_reference="local_instructional_policy",
    )
    assert record_from_dict(record_to_dict(composition)) == composition
    assert identity_segments_for_record(requirement) == (
        "profile_growth",
        "1",
        "baseline_required",
    )


def test_profile_migration_impact_categories_are_disjoint() -> None:
    migration = PortfolioProfileMigration(
        profile_migration_id="profile_migration_1",
        portfolio_id="portfolio_profile",
        predecessor_binding_id="binding_1",
        successor_binding_id="binding_2",
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
        unresolved_requirement_ids=(),
        reapproval_requirement_ids=("teacher_review",),
        migrated_at=NOW,
        migrated_by=ACTOR,
        migration_reason="Adopt revised local policy.",
        authority_reference="local_instructional_policy",
    )
    assert record_from_dict(record_to_dict(migration)) == migration


def test_profile_lifecycle_cycle_is_invalid_history() -> None:
    reference = ProfileRevisionRef(
        portfolio_profile_id="profile_growth", profile_revision=1
    )
    event_a = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id="profile_event_a",
        profile_revision=reference,
        event_kind="activated",
        event_at=NOW,
        effective_at=NOW,
        actor=ACTOR,
        reason="Cycle fixture A.",
        predecessor_event_id="profile_event_b",
    )
    event_b = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id="profile_event_b",
        profile_revision=reference,
        event_kind="withdrawn",
        event_at=NOW,
        effective_at=NOW,
        actor=ACTOR,
        reason="Cycle fixture B.",
        predecessor_event_id="profile_event_a",
    )
    state = project_profile_state(
        (improvement_family(), improvement_revision(1), event_a, event_b)
    )
    codes = {item.code for item in collect_profile_state_issues(state)}
    assert "profile.lifecycle_cycle" in codes
