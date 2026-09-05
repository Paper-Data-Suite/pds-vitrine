from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.workspace import ensure_workspace_root

import vitrine.starter_profiles as starter_profiles
from tests.profile_helpers import (
    ACTOR,
    DeterministicIds,
    fixed_clock,
    make_profile_workspace,
)
from vitrine.candidate_services import CANDIDATE_KIND_BY_ARTIFACT_KIND
from vitrine.models import PortfolioProfileLifecycleEvent
from vitrine.profile_services import (
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    transition_profile_lifecycle,
)
from vitrine.starter_profiles import (
    STARTER_PROFILE_CANDIDATE_KINDS_V1,
    STARTER_PROFILE_IDS,
    StarterProfileError,
    StarterProfileInstallComponentDisposition,
    StarterProfileInstallPlan,
    get_starter_profile_pack,
    install_starter_profile,
    list_starter_profile_packs,
    plan_starter_profile_install,
    validate_starter_profile_pack,
)
from vitrine.storage import (
    list_state_revisions,
    load_current_records,
    load_current_state,
)


def test_starter_catalog_contains_exactly_two_frozen_profiles() -> None:
    summaries = list_starter_profile_packs()
    assert tuple(item.starter_profile_id for item in summaries) == STARTER_PROFILE_IDS
    assert tuple(item.purpose_kind for item in summaries) == ("improvement", "showcase")
    assert tuple(item.profile_revision for item in summaries) == (1, 1)
    assert tuple(item.profile_family_id for item in summaries) == (
        "vitrine_starter_improvement_family",
        "vitrine_starter_showcase_family",
    )
    assert tuple(item.portfolio_profile_id for item in summaries) == (
        "vitrine_starter_improvement",
        "vitrine_starter_showcase",
    )


def test_package_resource_loading_does_not_depend_on_current_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert tuple(item.starter_profile_id for item in list_starter_profile_packs()) == (
        "improvement_portfolio_v1",
        "showcase_portfolio_v1",
    )


def test_packaged_authorship_is_deterministic_vitrine_provenance() -> None:
    for starter_id in STARTER_PROFILE_IDS:
        pack = get_starter_profile_pack(starter_id)
        assert pack.family.created_by.actor_kind == "system"
        assert pack.family.created_by.actor_id == "vitrine_starter_profile_catalog"
        assert pack.family.created_by.owning_system == "vitrine"
        assert pack.family.created_by.role_snapshot == "starter_profile_author"
        assert pack.revision.created_by == pack.family.created_by
        assert pack.revision.created_at == pack.family.created_at
        assert pack.revision.source_authority_references == (
            "vitrine_starter_profile_catalog_v1",
        )
        assert pack.revision.known_limitations


def test_improvement_starter_is_explicit_comparison_policy() -> None:
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    sections = {item.section_id: item for item in pack.revision.sections}
    assert tuple(sections) == (
        "baseline",
        "later_evidence",
        "supporting_feedback",
        "reflection",
    )
    assert sections["baseline"].minimum_placements == 1
    assert sections["baseline"].maximum_placements == 1
    assert sections["later_evidence"].minimum_placements == 1
    assert sections["later_evidence"].maximum_placements == 3
    assert sections["supporting_feedback"].obligation == "optional"
    assert sections["reflection"].reflection_requirement == "required"
    assert sections["reflection"].maximum_placements == 0
    assert not any(item.required_relationship_kinds for item in sections.values())

    requirements = {item.requirement_id: item for item in pack.requirements}
    assert set(requirements) == {
        "baseline_cardinality",
        "later_evidence_cardinality",
        "comparison_reflection",
        "teacher_review",
    }
    assert requirements["comparison_reflection"].requirement_kind == "reflection"
    assert requirements["teacher_review"].requirement_kind == "approval"

    policy_text = " ".join(
        [
            *(item.purpose for item in pack.revision.sections),
            *pack.revision.known_limitations,
        ]
    ).casefold()
    assert "does not determine whether improvement occurred" in policy_text
    assert "does not calculate or assert improvement" in policy_text
    assert "automatic latest, highest, or best selection" in policy_text


def test_showcase_starter_preserves_review_and_disclosure_boundaries() -> None:
    pack = get_starter_profile_pack("showcase_portfolio_v1")
    sections = {item.section_id: item for item in pack.revision.sections}
    assert tuple(sections) == ("featured_work", "supporting_evidence", "reflection")
    assert sections["featured_work"].allowed_candidate_kinds == ("student_work",)
    assert sections["supporting_evidence"].obligation == "optional"
    assert sections["reflection"].reflection_requirement == "required"
    assert not any(item.required_relationship_kinds for item in sections.values())

    assert len(pack.revision.audience_rules) == 1
    audience = pack.revision.audience_rules[0]
    assert audience.audience_class == "external_reviewer"
    assert audience.presentation_class == "showcase"
    assert set(audience.required_review_classes) == {
        "accessibility_review",
        "privacy_review",
        "rights_review",
    }
    assert "private_teacher_note" in audience.prohibited_content_classes
    assert "disclosure authorization" in audience.purpose.casefold()

    requirements = {item.requirement_id: item for item in pack.requirements}
    assert set(requirements) == {
        "featured_work_cardinality",
        "showcase_reflection",
        "privacy_review",
        "rights_review",
        "accessibility_treatment",
        "collaborative_work_treatment",
        "final_curator_approval",
    }
    assert requirements["collaborative_work_treatment"].obligation == "conditional"
    assert requirements["final_curator_approval"].requirement_kind == "approval"
    assert any(
        "does not grant permission to disclose" in item.casefold()
        for item in pack.revision.known_limitations
    )


def test_starter_candidate_vocabulary_matches_current_candidate_evaluator() -> None:
    evaluator_kinds = frozenset(CANDIDATE_KIND_BY_ARTIFACT_KIND.values())
    assert STARTER_PROFILE_CANDIDATE_KINDS_V1 == evaluator_kinds
    for starter_id in STARTER_PROFILE_IDS:
        pack = get_starter_profile_pack(starter_id)
        assert all(
            set(section.allowed_candidate_kinds) <= evaluator_kinds
            for section in pack.revision.sections
        )


def test_starter_validation_uses_profile_aggregate_rules() -> None:
    for starter_id in STARTER_PROFILE_IDS:
        result = validate_starter_profile_pack(starter_id)
        assert result.starter_profile_id == starter_id
        assert result.valid
        assert result.issue_codes == ()


def test_unknown_starter_id_is_stable_not_found_error() -> None:
    with pytest.raises(StarterProfileError) as raised:
        get_starter_profile_pack("missing_starter")
    assert raised.value.code == "starter_profile_not_found"


def test_starter_runtime_module_has_no_sibling_producer_imports() -> None:
    source = inspect.getsource(starter_profiles)
    forbidden_imports = (
        "import scoreform",
        "from scoreform",
        "import quillan",
        "from quillan",
        "import pds_concord",
        "from pds_concord",
    )
    assert not any(value in source for value in forbidden_imports)


def _component_map(
    plan: StarterProfileInstallPlan,
) -> dict[tuple[str, str], StarterProfileInstallComponentDisposition]:
    return {
        (item.component_kind, item.component_id): item for item in plan.components
    }


def _create_exact_starter_revision(
    workspace: Path,
    starter_profile_id: str,
    *,
    activate: bool,
) -> DeterministicIds:
    pack = get_starter_profile_pack(starter_profile_id)
    ids = DeterministicIds()
    create_profile_family(
        workspace,
        pack.family,
        expected_state_revision=load_current_state(workspace).state_revision,
    )
    create_profile_revision(
        workspace,
        pack.revision,
        pack.requirements,
        expected_state_revision=load_current_state(workspace).state_revision,
    )
    if activate:
        activate_profile_revision(
            workspace,
            pack.revision.reference,
            actor=ACTOR,
            reason="Activate exact starter for planning test.",
            authority_reference="test_authority",
            expected_state_revision=load_current_state(workspace).state_revision,
            clock=fixed_clock,
            id_factory=ids,
        )
    return ids


def test_install_plan_for_missing_workspace_is_all_create_and_read_only(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "missing-workspace"
    plan = plan_starter_profile_install(
        "improvement_portfolio_v1", workspace_root=workspace
    )
    assert plan.observed_state_revision is None
    assert plan.observed_lifecycle_status == "absent"
    assert plan.lifecycle_disposition == "activate_new"
    assert plan.created_record_count == 6
    assert plan.reused_record_count == 0
    assert plan.conflict_record_count == 0
    assert plan.activation_required
    assert plan.would_change
    assert not workspace.exists()


def test_install_plan_reports_partial_exact_family_without_writing(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    create_profile_family(workspace, pack.family, expected_state_revision=1)
    before_records = load_current_records(workspace)
    before_revision = load_current_state(workspace).state_revision

    plan = plan_starter_profile_install(
        pack.starter_profile_id, workspace_root=workspace
    )

    components = _component_map(plan)
    assert components[("family", pack.family.profile_family_id)].disposition == (
        "reuse_exact"
    )
    assert components[("revision", "vitrine_starter_improvement:1")].disposition == (
        "create"
    )
    assert plan.lifecycle_disposition == "activate_new"
    assert plan.observed_state_revision == before_revision
    assert load_current_records(workspace) == before_records
    assert load_current_state(workspace).state_revision == before_revision


def test_install_plan_for_exact_inactive_revision_proposes_activation_only(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    _create_exact_starter_revision(
        workspace, "improvement_portfolio_v1", activate=False
    )
    before_records = load_current_records(workspace)
    before_revision = load_current_state(workspace).state_revision

    plan = plan_starter_profile_install(
        "improvement_portfolio_v1", workspace_root=workspace
    )

    assert {item.disposition for item in plan.components} == {"reuse_exact"}
    assert plan.observed_lifecycle_status == "inactive"
    assert plan.lifecycle_disposition == "activate_existing_exact"
    assert plan.created_record_count == 0
    assert plan.activation_required
    assert plan.would_change
    assert load_current_records(workspace) == before_records
    assert load_current_state(workspace).state_revision == before_revision


def test_install_plan_for_exact_active_revision_is_no_change(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    _create_exact_starter_revision(
        workspace, "showcase_portfolio_v1", activate=True
    )
    before_records = load_current_records(workspace)
    before_revision = load_current_state(workspace).state_revision

    plan = plan_starter_profile_install(
        "showcase_portfolio_v1", workspace_root=workspace
    )

    assert {item.disposition for item in plan.components} == {"reuse_exact"}
    assert plan.observed_lifecycle_status == "activated"
    assert plan.lifecycle_disposition == "already_active"
    assert not plan.activation_required
    assert not plan.would_change
    assert not plan.has_conflicts
    assert load_current_records(workspace) == before_records
    assert load_current_state(workspace).state_revision == before_revision


def test_install_plan_surfaces_immutable_family_conflict(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    create_profile_family(
        workspace,
        replace(pack.family, description="Different immutable family content."),
        expected_state_revision=1,
    )

    plan = plan_starter_profile_install(
        pack.starter_profile_id, workspace_root=workspace
    )

    family = _component_map(plan)[("family", pack.family.profile_family_id)]
    assert family.disposition == "conflict"
    assert family.detail_code == "immutable_content_conflict"
    assert plan.has_conflicts
    assert plan.lifecycle_disposition == "lifecycle_conflict"
    assert not plan.would_change


def test_install_plan_surfaces_requirement_and_extra_requirement_conflicts(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    create_profile_family(workspace, pack.family, expected_state_revision=1)
    changed = replace(
        pack.requirements[0], statement="Different immutable requirement meaning."
    )
    extra = replace(
        pack.requirements[-1],
        requirement_id="teacher_local_extra_requirement",
        title="Teacher-local extra requirement",
        statement="Extra immutable policy attached to the exact starter revision.",
    )
    create_profile_revision(
        workspace,
        pack.revision,
        (changed, *pack.requirements[1:], extra),
        expected_state_revision=2,
    )

    plan = plan_starter_profile_install(
        pack.starter_profile_id, workspace_root=workspace
    )
    components = _component_map(plan)

    changed_component = components[("requirement", changed.requirement_id)]
    assert changed_component.disposition == "conflict"
    assert changed_component.detail_code == "immutable_content_conflict"
    extra_component = components[("requirement", extra.requirement_id)]
    assert extra_component.disposition == "conflict"
    assert extra_component.detail_code == "unexpected_existing_requirement"
    assert plan.conflict_record_count == 2
    assert plan.lifecycle_disposition == "lifecycle_conflict"


def test_install_plan_rejects_existing_starter_series_without_exact_revision(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    create_profile_family(workspace, pack.family, expected_state_revision=1)
    unrelated_revision = replace(
        pack.revision,
        profile_revision=2,
        label="Existing different root revision",
    )
    unrelated_requirements = tuple(
        replace(item, profile_revision=2) for item in pack.requirements
    )
    create_profile_revision(
        workspace,
        unrelated_revision,
        unrelated_requirements,
        expected_state_revision=2,
    )

    plan = plan_starter_profile_install(
        pack.starter_profile_id, workspace_root=workspace
    )
    revision_component = _component_map(plan)[
        ("revision", "vitrine_starter_improvement:1")
    ]
    assert revision_component.disposition == "conflict"
    assert revision_component.detail_code == "profile_series_identity_conflict"
    assert plan.lifecycle_disposition == "lifecycle_conflict"


def test_install_plan_never_reactivates_terminal_starter_lifecycle(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = _create_exact_starter_revision(
        workspace, "improvement_portfolio_v1", activate=True
    )
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    transition_profile_lifecycle(
        workspace,
        pack.revision.reference,
        "withdrawn",
        actor=ACTOR,
        reason="Withdraw exact starter for planning test.",
        authority_reference="test_authority",
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    before_records = load_current_records(workspace)
    before_revision = load_current_state(workspace).state_revision

    plan = plan_starter_profile_install(
        pack.starter_profile_id, workspace_root=workspace
    )

    assert plan.observed_lifecycle_status == "withdrawn"
    assert plan.lifecycle_disposition == "lifecycle_conflict"
    assert plan.has_conflicts
    assert not plan.activation_required
    assert not plan.would_change
    assert load_current_records(workspace) == before_records
    assert load_current_state(workspace).state_revision == before_revision


def _lifecycle_events(workspace: Path) -> tuple[PortfolioProfileLifecycleEvent, ...]:
    return tuple(
        item
        for item in load_current_records(workspace)
        if isinstance(item, PortfolioProfileLifecycleEvent)
    )


def test_install_starter_profile_initializes_existing_core_workspace_atomically(
    tmp_path: Path,
) -> None:
    workspace = ensure_workspace_root(tmp_path / "workspace", create=True)
    ids = DeterministicIds()

    result = install_starter_profile(
        "improvement_portfolio_v1",
        workspace_root=workspace,
        actor=ACTOR,
        reason="Install the packaged improvement starter.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )

    assert not result.no_op
    assert result.plan.observed_state_revision is None
    assert result.resulting_state_revision == 1
    assert result.activation_event_id == "profile_event_1"
    assert len(result.committed_component_ids) == 7
    assert list_state_revisions(workspace) == (1,)

    pack = get_starter_profile_pack("improvement_portfolio_v1")
    records = load_current_records(workspace)
    assert pack.family in records
    assert pack.revision in records
    assert all(item in records for item in pack.requirements)
    events = _lifecycle_events(workspace)
    assert len(events) == 1
    event = events[0]
    assert event.profile_lifecycle_event_id == "profile_event_1"
    assert event.profile_revision == pack.revision.reference
    assert event.event_kind == "activated"
    assert event.actor == ACTOR
    assert event.event_at == fixed_clock()
    assert event.effective_at == fixed_clock()
    assert event.authority_reference == "teacher_confirmed_starter_install"
    assert event.actor != pack.family.created_by


def test_install_starter_profile_uses_one_state_revision_for_full_batch(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    before_records = load_current_records(workspace)
    assert list_state_revisions(workspace) == (1,)

    result = install_starter_profile(
        "showcase_portfolio_v1",
        workspace_root=workspace,
        actor=ACTOR,
        reason="Install the packaged showcase starter.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=1,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.resulting_state_revision == 2
    assert list_state_revisions(workspace) == (1, 2)
    after_records = load_current_records(workspace)
    assert set(before_records).issubset(after_records)
    assert len(after_records) - len(before_records) == 10


def test_install_starter_profile_reuses_partial_exact_state_in_same_commit(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    create_profile_family(workspace, pack.family, expected_state_revision=1)
    assert load_current_state(workspace).state_revision == 2

    result = install_starter_profile(
        pack.starter_profile_id,
        workspace_root=workspace,
        actor=ACTOR,
        reason="Complete explicit starter installation.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=2,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.resulting_state_revision == 3
    assert list_state_revisions(workspace) == (1, 2, 3)
    assert (
        "family:vitrine_starter_improvement_family"
        not in result.committed_component_ids
    )
    assert "revision:vitrine_starter_improvement:1" in result.committed_component_ids
    assert "lifecycle:profile_event_1" in result.committed_component_ids


def test_install_starter_profile_activates_exact_inactive_revision_only(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    _create_exact_starter_revision(
        workspace, "improvement_portfolio_v1", activate=False
    )
    before_records = load_current_records(workspace)
    before_revision = load_current_state(workspace).state_revision

    result = install_starter_profile(
        "improvement_portfolio_v1",
        workspace_root=workspace,
        actor=ACTOR,
        reason="Activate the exact installed starter.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=before_revision,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.resulting_state_revision == before_revision + 1
    assert result.committed_component_ids == ("lifecycle:profile_event_1",)
    after_records = load_current_records(workspace)
    assert len(after_records) == len(before_records) + 1
    assert _lifecycle_events(workspace)[0].actor == ACTOR


def test_install_starter_profile_is_idempotent_when_exact_revision_is_active(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    first_ids = DeterministicIds()
    first = install_starter_profile(
        "showcase_portfolio_v1",
        workspace_root=workspace,
        actor=ACTOR,
        reason="Install the showcase starter.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=1,
        clock=fixed_clock,
        id_factory=first_ids,
    )
    before_records = load_current_records(workspace)
    before_revisions = list_state_revisions(workspace)

    second_ids = DeterministicIds()
    second = install_starter_profile(
        "showcase_portfolio_v1",
        workspace_root=workspace,
        actor=ACTOR,
        reason="Repeat the same explicit install.",
        authority_reference="teacher_confirmed_starter_install",
        expected_state_revision=first.resulting_state_revision,
        clock=fixed_clock,
        id_factory=second_ids,
    )

    assert second.no_op
    assert second.activation_event_id is None
    assert second.committed_component_ids == ()
    assert second.resulting_state_revision == first.resulting_state_revision
    assert load_current_records(workspace) == before_records
    assert list_state_revisions(workspace) == before_revisions
    assert second_ids.counters == {}


def test_install_starter_profile_rejects_stale_expected_state_without_writing(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    before_records = load_current_records(workspace)
    before_revisions = list_state_revisions(workspace)

    with pytest.raises(StarterProfileError) as raised:
        install_starter_profile(
            "improvement_portfolio_v1",
            workspace_root=workspace,
            actor=ACTOR,
            reason="Stale guarded install.",
            authority_reference="teacher_confirmed_starter_install",
            expected_state_revision=None,
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )

    assert raised.value.code == "state_conflict"
    assert load_current_records(workspace) == before_records
    assert list_state_revisions(workspace) == before_revisions


def test_install_starter_profile_refuses_terminal_lifecycle_without_writing(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    ids = _create_exact_starter_revision(
        workspace, "improvement_portfolio_v1", activate=True
    )
    pack = get_starter_profile_pack("improvement_portfolio_v1")
    transition_profile_lifecycle(
        workspace,
        pack.revision.reference,
        "retired",
        actor=ACTOR,
        reason="Retire exact starter before reinstall attempt.",
        authority_reference="test_authority",
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    before_records = load_current_records(workspace)
    before_revisions = list_state_revisions(workspace)
    expected = load_current_state(workspace).state_revision

    with pytest.raises(StarterProfileError) as raised:
        install_starter_profile(
            pack.starter_profile_id,
            workspace_root=workspace,
            actor=ACTOR,
            reason="Do not revive a retired starter.",
            authority_reference="teacher_confirmed_starter_install",
            expected_state_revision=expected,
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )

    assert raised.value.code == "starter_profile_lifecycle_conflict"
    assert load_current_records(workspace) == before_records
    assert list_state_revisions(workspace) == before_revisions


def test_install_starter_profile_refuses_immutable_component_conflict(
    tmp_path: Path,
) -> None:
    workspace = make_profile_workspace(tmp_path)
    pack = get_starter_profile_pack("showcase_portfolio_v1")
    create_profile_family(
        workspace,
        replace(pack.family, description="Conflicting immutable content."),
        expected_state_revision=1,
    )
    before_records = load_current_records(workspace)
    before_revisions = list_state_revisions(workspace)
    expected = load_current_state(workspace).state_revision

    with pytest.raises(StarterProfileError) as raised:
        install_starter_profile(
            pack.starter_profile_id,
            workspace_root=workspace,
            actor=ACTOR,
            reason="Conflicting starter install.",
            authority_reference="teacher_confirmed_starter_install",
            expected_state_revision=expected,
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )

    assert raised.value.code == "starter_profile_install_conflict"
    assert load_current_records(workspace) == before_records
    assert list_state_revisions(workspace) == before_revisions

