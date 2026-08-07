from __future__ import annotations

from pathlib import Path

import pytest

from tests.subject_helpers import (
    DeterministicIds,
    fixed_clock,
    make_subject_workspace,
    teacher_context,
)
from vitrine.models import ClassQualifiedStudentRef, Portfolio, validate_record_graph
from vitrine.storage import (
    commit_record_batch,
    load_current_record_graph,
    load_current_records,
)
from vitrine.subject_services import (
    SubjectWorkflowError,
    correct_subject_link,
    create_portfolio_subject,
    invalidate_subject_link,
    link_portfolio_subject,
    list_subjects,
    merge_portfolio_subjects,
    observe_state_revision,
    resolve_roster_student,
    show_subject,
    split_portfolio_subject,
)


def ref(class_id: str, student_id: str = "00107") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id=student_id,
    )


def test_exact_core_resolution_preserves_leading_zero_student_id(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    resolution = resolve_roster_student(workspace, ref("english10_p2"))
    assert resolution.status == "resolvable"
    assert resolution.student is not None
    assert resolution.student.student_id == "00107"


def test_create_and_explicit_cross_class_link(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    linked = link_portfolio_subject(
        workspace,
        created.subject_ids[0],
        ref("csp_p1"),
        context=teacher_context(),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    detail = show_subject(workspace, created.subject_ids[0])
    assert linked.commit.state_revision == 2
    assert {item.reference.class_id for item in detail.current_links} == {
        "english10_p2",
        "csp_p1",
    }
    assert all(item.reference.student_id == "00107" for item in detail.current_links)


def test_name_and_repeated_local_id_do_not_auto_match(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    same_name = create_portfolio_subject(
        workspace,
        ref("csp_p1", "00999"),
        context=teacher_context(),
        expected_state_revision=first.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    repeated_local_id = create_portfolio_subject(
        workspace,
        ref("math_p3", "00107"),
        context=teacher_context(),
        expected_state_revision=same_name.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    subjects = list_subjects(workspace)
    assert len(subjects) == 3
    assert len({item.portfolio_subject_id for item in subjects}) == 3
    assert repeated_local_id.subject_ids[0] != first.subject_ids[0]


def test_exact_duplicate_reference_is_blocked(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    with pytest.raises(SubjectWorkflowError) as raised:
        create_portfolio_subject(
            workspace,
            ref("english10_p2"),
            context=teacher_context(),
            expected_state_revision=first.commit.state_revision,
            clock=fixed_clock,
            id_factory=ids,
        )
    assert raised.value.code == "duplicate_active_association"


def test_link_correction_preserves_old_link(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    corrected = correct_subject_link(
        workspace,
        created.link_ids[0],
        ref("csp_p1"),
        context=teacher_context("Corrected class reference."),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    detail = show_subject(workspace, created.subject_ids[0])
    assert corrected.commit.state_revision == 2
    assert len(detail.current_links) == 1
    assert detail.current_links[0].reference.class_id == "csp_p1"
    assert len(detail.historical_links) == 1
    assert detail.historical_links[0].subject_link_id == created.link_ids[0]
    assert detail.historical_links[0].status == "superseded"


def test_invalidation_preserves_historical_link(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    invalidate_subject_link(
        workspace,
        created.link_ids[0],
        context=teacher_context("Link was confirmed in error."),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    detail = show_subject(workspace, created.subject_ids[0])
    assert detail.current_links == ()
    assert len(detail.historical_links) == 1
    assert detail.historical_links[0].status == "invalidated"


def test_merge_and_split_are_successor_based(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    first_linked = link_portfolio_subject(
        workspace,
        first.subject_ids[0],
        ref("csp_p1"),
        context=teacher_context(),
        expected_state_revision=first.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    second = create_portfolio_subject(
        workspace,
        ref("math_p3"),
        context=teacher_context(),
        expected_state_revision=first_linked.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    merged = merge_portfolio_subjects(
        workspace,
        (first.subject_ids[0], second.subject_ids[0]),
        context=teacher_context("These Subjects are the same person."),
        expected_state_revision=second.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    statuses = {item.portfolio_subject_id: item.status for item in list_subjects(workspace)}
    assert statuses[first.subject_ids[0]] == "merged"
    assert statuses[second.subject_ids[0]] == "merged"
    assert statuses[merged.subject_ids[0]] == "active"
    merged_detail = show_subject(workspace, merged.subject_ids[0])
    validate_record_graph(load_current_record_graph(workspace).graph)
    groups = (
        (merged_detail.current_links[0].subject_link_id,),
        tuple(item.subject_link_id for item in merged_detail.current_links[1:]),
    )
    split = split_portfolio_subject(
        workspace,
        merged.subject_ids[0],
        groups,
        context=teacher_context("The merged Subject represented two people."),
        expected_state_revision=merged.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    statuses = {item.portfolio_subject_id: item.status for item in list_subjects(workspace)}
    assert statuses[merged.subject_ids[0]] == "split"
    assert all(statuses[item] == "active" for item in split.subject_ids)
    assert len(split.subject_ids) == 2


def test_merge_reports_existing_portfolios_without_rebinding(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    second = create_portfolio_subject(
        workspace,
        ref("math_p3"),
        context=teacher_context(),
        expected_state_revision=first.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    records = load_current_records(workspace)
    subject = next(
        item for item in records if getattr(item, "portfolio_subject_id", None) == first.subject_ids[0]
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_1",
        portfolio_subject_id=first.subject_ids[0],
        created_at=fixed_clock(),
        created_by=subject.created_by,
    )
    committed = commit_record_batch(
        workspace,
        (portfolio,),
        expected_state_revision=second.commit.state_revision,
    )
    merged = merge_portfolio_subjects(
        workspace,
        (first.subject_ids[0], second.subject_ids[0]),
        context=teacher_context(),
        expected_state_revision=committed.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert merged.affected_portfolio_ids == ("portfolio_1",)
    persisted = load_current_records(workspace)
    same_portfolio = next(item for item in persisted if isinstance(item, Portfolio))
    assert same_portfolio.portfolio_subject_id == first.subject_ids[0]


def test_stale_expected_state_conflicts(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    with pytest.raises(SubjectWorkflowError) as raised:
        link_portfolio_subject(
            workspace,
            created.subject_ids[0],
            ref("csp_p1"),
            context=teacher_context(),
            expected_state_revision=0,
            clock=fixed_clock,
            id_factory=ids,
        )
    assert raised.value.code == "state_conflict"


def test_historical_link_survives_roster_disappearance(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    invalidate_subject_link(
        workspace,
        created.link_ids[0],
        context=teacher_context(),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    (workspace / "classes" / "english10_p2" / "roster.csv").unlink()
    detail = show_subject(workspace, created.subject_ids[0])
    assert detail.historical_links[0].current_resolution == "historical_reference_only"
    assert observe_state_revision(workspace) == 2


def test_duplicate_active_reference_can_be_repaired_by_explicit_merge(tmp_path: Path) -> None:
    """A diagnosable duplicate claim must remain loadable so merge can repair it."""
    from vitrine.models import (
        PortfolioSubject,
        PortfolioSubjectClassLink,
        PortfolioSubjectIdentityDecision,
    )

    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    context = teacher_context("Imported duplicate identity claim for review.")
    second_subject = PortfolioSubject(
        portfolio_subject_id="subject_duplicate",
        created_at=fixed_clock(),
        created_by=context.actor,
        display_name_snapshot="Jane Doe",
    )
    second_link = PortfolioSubjectClassLink(
        subject_link_id="link_duplicate",
        portfolio_subject_id=second_subject.portfolio_subject_id,
        student_reference=ref("english10_p2"),
        confirmed_at=fixed_clock(),
        confirmed_by=context.actor,
        confirmation_basis="teacher_confirmed",
        authority_reference=context.authority_source,
    )
    create_decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="decision_duplicate_create",
        decision_type="create_subject",
        subject_ids=(second_subject.portfolio_subject_id,),
        subject_link_ids=(),
        decided_at=fixed_clock(),
        decided_by=context.actor,
        authority_source=context.authority_source,
        basis_type=context.basis_type,
        basis_summary=context.basis_summary,
    )
    confirm_decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="decision_duplicate_confirm",
        decision_type="confirm_link",
        subject_ids=(second_subject.portfolio_subject_id,),
        subject_link_ids=(second_link.subject_link_id,),
        decided_at=fixed_clock(),
        decided_by=context.actor,
        authority_source=context.authority_source,
        basis_type=context.basis_type,
        basis_summary=context.basis_summary,
    )
    conflicted = commit_record_batch(
        workspace,
        (second_subject, second_link, create_decision, confirm_decision),
        expected_state_revision=first.commit.state_revision,
    )

    subjects = list_subjects(workspace)
    assert {item.portfolio_subject_id for item in subjects} == {
        first.subject_ids[0],
        second_subject.portfolio_subject_id,
    }

    merged = merge_portfolio_subjects(
        workspace,
        (first.subject_ids[0], second_subject.portfolio_subject_id),
        context=teacher_context("Teacher resolved duplicate identity claims."),
        expected_state_revision=conflicted.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    successor = show_subject(workspace, merged.subject_ids[0])
    assert len(successor.current_links) == 1
    assert successor.current_links[0].reference == ref("english10_p2")


def test_commit_race_is_translated_to_stable_state_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vitrine.subject_services as services
    from vitrine.storage import VitrineStorageConflictError

    workspace = make_subject_workspace(tmp_path)

    def conflict(*_args: object, **_kwargs: object) -> object:
        raise VitrineStorageConflictError("expected state 1, found 2")

    monkeypatch.setattr(services, "commit_record_batch", conflict)
    with pytest.raises(SubjectWorkflowError) as raised:
        create_portfolio_subject(
            workspace,
            ref("english10_p2"),
            context=teacher_context(),
            expected_state_revision=None,
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )
    assert raised.value.code == "state_conflict"


def test_relinking_same_exact_reference_reports_existing_association(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    replay = link_portfolio_subject(
        workspace,
        created.subject_ids[0],
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    assert replay.link_ids == created.link_ids
    assert replay.commit.no_op is True
    assert replay.commit.state_revision == created.commit.state_revision


def test_exact_reference_lookup_distinguishes_unlinked_and_resolved(tmp_path: Path) -> None:
    from vitrine.subject_services import resolve_subject_reference

    workspace = make_subject_workspace(tmp_path)
    assert resolve_subject_reference(workspace, ref("english10_p2")).status == "unlinked"
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    resolved = resolve_subject_reference(workspace, ref("english10_p2"))
    assert resolved.status == "resolved"
    assert resolved.subject_ids == created.subject_ids


def test_cross_year_link_preserves_independent_school_year_context(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = DeterministicIds()
    created = create_portfolio_subject(
        workspace,
        ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    historical_ref = ClassQualifiedStudentRef(
        school_year="2025-2026",
        class_id="old_english9_p3",
        student_id="00107",
    )
    linked = link_portfolio_subject(
        workspace,
        created.subject_ids[0],
        historical_ref,
        context=teacher_context("Teacher confirms longitudinal continuity."),
        expected_state_revision=created.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    detail = show_subject(workspace, created.subject_ids[0])
    assert linked.commit.state_revision == 2
    assert {(item.reference.school_year, item.reference.class_id) for item in detail.current_links} == {
        ("2025-2026", "old_english9_p3"),
        ("2026-2027", "english10_p2"),
    }
