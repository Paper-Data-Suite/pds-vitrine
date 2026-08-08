from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tests.profile_helpers import (
    ACTOR,
    DeterministicIds,
    fixed_clock,
    improvement_family,
    improvement_requirements,
    improvement_revision,
    make_profile_workspace,
    showcase_family,
    showcase_requirements,
    showcase_revision,
)
from vitrine.models import (
    PortfolioProfileOverlayRevision,
    ProfileOverlayRequirement,
    ProfileOverlayRequirementChange,
    ProfileOverlayRevisionRef,
    ProfileRevisionRef,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    ProfileWorkflowError,
    activate_profile_revision,
    analyze_profile_migration,
    bind_portfolio_profile,
    compare_profile_requirements,
    compose_profile_revision,
    create_profile_family,
    create_profile_overlay,
    create_profile_revision,
    get_portfolio_profile_binding,
    get_profile_migration_history,
    get_profile_requirements,
    list_bindable_profile_revisions,
    migrate_portfolio_profile,
    observe_profile_state_revision,
    transition_profile_lifecycle,
)


def _install_growth_r1(workspace: Path, ids: DeterministicIds) -> None:
    create_profile_family(
        workspace, improvement_family(), expected_state_revision=1
    )
    create_profile_revision(
        workspace,
        improvement_revision(1),
        improvement_requirements(1),
        expected_state_revision=2,
    )
    activate_profile_revision(
        workspace,
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=1),
        actor=ACTOR,
        reason="Approved.",
        authority_reference="local_instructional_policy",
        expected_state_revision=3,
        clock=fixed_clock,
        id_factory=ids,
    )


def test_revision_creation_does_not_activate_or_select_highest(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    create_profile_revision(
        workspace,
        improvement_revision(2, predecessor=1, include_feedback=True),
        improvement_requirements(2, include_feedback=True, title_change=True),
        expected_state_revision=4,
    )
    bindable = list_bindable_profile_revisions(workspace)
    assert [item.reference.profile_revision for item in bindable] == [1]

    activate_profile_revision(
        workspace,
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
        actor=ACTOR,
        reason="Approved successor.",
        authority_reference="local_instructional_policy",
        expected_state_revision=5,
        clock=fixed_clock,
        id_factory=ids,
    )
    transition_profile_lifecycle(
        workspace,
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
        "withdrawn",
        actor=ACTOR,
        reason="Withdraw test successor.",
        authority_reference="local_instructional_policy",
        expected_state_revision=6,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert [item.reference.profile_revision for item in list_bindable_profile_revisions(workspace)] == [1]


def test_material_requirement_change_cannot_reuse_stable_id(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    bad = list(improvement_requirements(2, include_feedback=True))
    bad[0] = replace(
        bad[0],
        obligation="optional",
    )
    with pytest.raises(ProfileWorkflowError) as raised:
        create_profile_revision(
            workspace,
            improvement_revision(2, predecessor=1, include_feedback=True),
            tuple(bad),
            expected_state_revision=4,
        )
    assert raised.value.code == "profile_requirement_identity_conflict"


def test_bind_and_explicit_migration_preserve_predecessor(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    bind_portfolio_profile(
        workspace,
        "portfolio_profile",
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=1),
        actor=ACTOR,
        binding_reason="Initial improvement policy.",
        context=ProfileBindingContext(),
        expected_state_revision=4,
        clock=fixed_clock,
        id_factory=ids,
    )
    create_profile_revision(
        workspace,
        improvement_revision(2, predecessor=1, include_feedback=True),
        improvement_requirements(2, include_feedback=True, title_change=True),
        expected_state_revision=5,
    )
    activate_profile_revision(
        workspace,
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
        actor=ACTOR,
        reason="Approved successor.",
        authority_reference="local_instructional_policy",
        expected_state_revision=6,
        clock=fixed_clock,
        id_factory=ids,
    )
    before = get_portfolio_profile_binding(workspace, "portfolio_profile")
    assert before is not None and before.profile_revision.profile_revision == 1

    analysis = analyze_profile_migration(
        workspace,
        "portfolio_profile",
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
        context=ProfileBindingContext(),
    )
    assert analysis.requirement_impact.added == ("feedback_context_required",)
    assert not analysis.blocked

    _, result = migrate_portfolio_profile(
        workspace,
        "portfolio_profile",
        ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
        actor=ACTOR,
        migration_reason="Adopt successor requirements.",
        authority_reference="local_instructional_policy",
        context=ProfileBindingContext(),
        expected_state_revision=7,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert result.commit is not None
    after = get_portfolio_profile_binding(workspace, "portfolio_profile")
    assert after is not None and after.profile_revision.profile_revision == 2
    assert after.predecessor_binding_id == before.profile_binding_id
    history = get_profile_migration_history(workspace, "portfolio_profile")
    assert len(history) == 1
    assert history[0].predecessor_binding_id == before.profile_binding_id


def test_requirement_comparison_keeps_unresolved_replacement_disjoint() -> None:
    source = improvement_requirements(1)
    target = list(improvement_requirements(2))
    target.append(
        replace(
            target[0],
            requirement_id="replacement_without_source",
            replaces_requirement_id="missing_requirement",
        )
    )
    impact = compare_profile_requirements(source, target)
    assert impact.unresolved_mapping == ("replacement_without_source",)
    assert "replacement_without_source" not in impact.added


def test_requirement_comparison_ignores_title_but_detects_semantics() -> None:
    source = improvement_requirements(1)
    title_only = improvement_requirements(2, title_change=True)
    impact = compare_profile_requirements(source, title_only)
    assert set(impact.unchanged) == {"baseline_required", "current_required", "teacher_review"}
    changed = list(title_only)
    changed[0] = replace(changed[0], statement="Different policy meaning.")
    impact = compare_profile_requirements(source, changed)
    assert impact.materially_changed == ("baseline_required",)


def test_overlay_composition_adds_requirement_and_rejects_weakening(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    base_ref = ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=1)
    overlay = PortfolioProfileOverlayRevision(
        overlay_id="overlay_growth",
        overlay_revision=1,
        predecessor_overlay_revision=None,
        label="Local growth overlay",
        purpose_kind="improvement",
        created_at=fixed_clock(),
        created_by=ACTOR,
        authority_reference="local_instructional_policy",
        component_revisions=(base_ref,),
        requirement_changes=(
            ProfileOverlayRequirementChange(
                action="add",
                requirement=ProfileOverlayRequirement(
                    requirement_id="local_reflection",
                    requirement_kind="reflection",
                    obligation="required",
                    title="Local reflection",
                    statement="Include one local reflection.",
                    scope_kind="portfolio",
                    satisfaction_class="reflection_record",
                    authority_references=("local_instructional_policy",),
                ),
            ),
        ),
    )
    create_profile_overlay(workspace, overlay, expected_state_revision=4)
    effective = replace(
        improvement_revision(1, profile_id="profile_growth_local"),
        profile_family_id="family_improvement",
        label="Local effective growth",
    )
    result = compose_profile_revision(
        workspace,
        effective,
        (base_ref,),
        (ProfileOverlayRevisionRef(overlay_id="overlay_growth", overlay_revision=1),),
        actor=ACTOR,
        authority_reference="local_instructional_policy",
        expected_state_revision=5,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert "local_reflection" in result.requirement_ids
    requirements = get_profile_requirements(workspace, effective.reference)
    assert {item.requirement_id for item in requirements} >= {"baseline_required", "local_reflection"}

    weakening = PortfolioProfileOverlayRevision(
        overlay_id="overlay_weakening",
        overlay_revision=1,
        predecessor_overlay_revision=None,
        label="Bad overlay",
        purpose_kind="improvement",
        created_at=fixed_clock(),
        created_by=ACTOR,
        authority_reference="local_instructional_policy",
        component_revisions=(base_ref,),
        requirement_changes=(
            ProfileOverlayRequirementChange(
                action="replace",
                requirement=ProfileOverlayRequirement(
                    requirement_id="baseline_local_optional",
                    requirement_kind="section",
                    obligation="optional",
                    title="Optional baseline",
                    statement="Baseline is optional.",
                    scope_kind="section",
                    scope_reference="baseline",
                    satisfaction_class="section_cardinality",
                    replaces_requirement_id="baseline_required",
                ),
            ),
        ),
    )
    create_profile_overlay(workspace, weakening, expected_state_revision=6)
    bad_effective = replace(effective, portfolio_profile_id="profile_growth_bad")
    with pytest.raises(ProfileWorkflowError) as raised:
        compose_profile_revision(
            workspace,
            bad_effective,
            (base_ref,),
            (ProfileOverlayRevisionRef(overlay_id="overlay_weakening", overlay_revision=1),),
            actor=ACTOR,
            authority_reference="local_instructional_policy",
            expected_state_revision=7,
            clock=fixed_clock,
            id_factory=ids,
        )
    assert raised.value.code == "profile_composition_conflict"


def test_showcase_profile_is_explicit_policy_not_authorization(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    create_profile_family(workspace, showcase_family(), expected_state_revision=1)
    create_profile_revision(workspace, showcase_revision(), showcase_requirements(), expected_state_revision=2)
    activate_profile_revision(
        workspace,
        ProfileRevisionRef(portfolio_profile_id="profile_showcase_local", profile_revision=1),
        actor=ACTOR,
        reason="Approved local showcase policy.",
        authority_reference="local_showcase_policy",
        expected_state_revision=3,
        clock=fixed_clock,
        id_factory=ids,
    )
    revision = showcase_revision()
    public = next(item for item in revision.audience_rules if item.audience_class == "public")
    assert "privacy_review" in public.required_review_classes
    assert "rights_review" in public.required_review_classes
    assert list_bindable_profile_revisions(workspace, purpose_kind="showcase")[0].bindable


def test_stale_expected_state_conflicts(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    assert observe_profile_state_revision(workspace) == 1
    create_profile_family(workspace, improvement_family(), expected_state_revision=1)
    with pytest.raises(ProfileWorkflowError) as raised:
        create_profile_family(workspace, showcase_family(), expected_state_revision=1)
    assert raised.value.code == "state_conflict"


def test_deprecated_revision_can_receive_later_terminal_event(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    reference = ProfileRevisionRef(
        portfolio_profile_id="profile_growth", profile_revision=1
    )
    transition_profile_lifecycle(
        workspace,
        reference,
        "deprecated",
        actor=ACTOR,
        reason="Discourage new bindings.",
        authority_reference="local_instructional_policy",
        expected_state_revision=4,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert list_bindable_profile_revisions(workspace) == ()
    transition_profile_lifecycle(
        workspace,
        reference,
        "withdrawn",
        actor=ACTOR,
        reason="Withdraw after deprecation.",
        authority_reference="local_instructional_policy",
        expected_state_revision=5,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert list_bindable_profile_revisions(workspace) == ()


def test_overlay_replacement_requires_explicit_matching_authority(tmp_path: Path) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = DeterministicIds()
    _install_growth_r1(workspace, ids)
    base_ref = ProfileRevisionRef(
        portfolio_profile_id="profile_growth", profile_revision=1
    )
    overlay = PortfolioProfileOverlayRevision(
        overlay_id="overlay_wrong_authority",
        overlay_revision=1,
        predecessor_overlay_revision=None,
        label="Wrong authority overlay",
        purpose_kind="improvement",
        created_at=fixed_clock(),
        created_by=ACTOR,
        authority_reference="unrelated_policy",
        component_revisions=(base_ref,),
        requirement_changes=(
            ProfileOverlayRequirementChange(
                action="replace",
                requirement=ProfileOverlayRequirement(
                    requirement_id="baseline_reworded",
                    requirement_kind="section",
                    obligation="required",
                    title="Baseline reworded",
                    statement="Include one baseline item with local context.",
                    scope_kind="section",
                    scope_reference="baseline",
                    satisfaction_class="section_cardinality",
                    replaces_requirement_id="baseline_required",
                ),
            ),
        ),
    )
    create_profile_overlay(workspace, overlay, expected_state_revision=4)
    effective = replace(
        improvement_revision(1, profile_id="profile_growth_wrong_authority"),
        profile_family_id="family_improvement",
        label="Wrong authority effective",
    )
    with pytest.raises(ProfileWorkflowError) as raised:
        compose_profile_revision(
            workspace,
            effective,
            (base_ref,),
            (
                ProfileOverlayRevisionRef(
                    overlay_id=overlay.overlay_id,
                    overlay_revision=overlay.overlay_revision,
                ),
            ),
            actor=ACTOR,
            authority_reference="unrelated_policy",
            expected_state_revision=5,
            clock=fixed_clock,
            id_factory=ids,
        )
    assert raised.value.code == "profile_composition_conflict"
