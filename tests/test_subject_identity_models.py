from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vitrine.identity_state import (
    collect_identity_state_issues,
    project_identity_state,
)
from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    PortfolioSubjectIdentityTransition,
    SubjectAssociationAllocation,
    record_from_json_bytes,
    record_to_canonical_json_bytes,
)

NOW = datetime(2026, 8, 7, 15, 0, tzinfo=timezone.utc)


def actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="teacher_1",
        owning_system="local",
        role_snapshot="teacher",
    )


def reference(class_id: str = "english10_p2") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id="00107",
    )


def test_identity_history_records_round_trip_strictly() -> None:
    subject = PortfolioSubject(
        portfolio_subject_id="subject_1",
        created_at=NOW,
        created_by=actor(),
    )
    link = PortfolioSubjectClassLink(
        subject_link_id="link_1",
        portfolio_subject_id=subject.portfolio_subject_id,
        student_reference=reference(),
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    snapshot = PortfolioSubjectDisplaySnapshot(
        display_snapshot_id="display_1",
        subject_link_id=link.subject_link_id,
        student_reference=link.student_reference,
        first_name="Jane",
        last_name="Doe",
        preferred_name="Jay",
        display_name="Jay Doe",
        captured_at=NOW,
    )
    decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="decision_1",
        decision_type="confirm_link",
        subject_ids=(subject.portfolio_subject_id,),
        subject_link_ids=(link.subject_link_id,),
        decided_at=NOW,
        decided_by=actor(),
        authority_source="local_teacher_workflow",
        basis_type="direct_teacher_knowledge",
        basis_summary="Teacher confirms the exact roster context.",
    )
    for record in (snapshot, decision):
        data = record_to_canonical_json_bytes(record)
        assert record_from_json_bytes(data) == record
        assert record_to_canonical_json_bytes(record_from_json_bytes(data)) == data


def test_merge_and_split_cardinality_is_enforced() -> None:
    with pytest.raises(ValueError):
        PortfolioSubjectIdentityTransition(
            subject_identity_transition_id="transition_1",
            transition_type="merge",
            identity_decision_id="decision_1",
            predecessor_subject_ids=("subject_1",),
            successor_subject_ids=("subject_2",),
            association_allocations=(),
            affected_portfolio_ids=(),
        )


def test_duplicate_active_reference_is_a_stable_diagnostic() -> None:
    subjects = tuple(
        PortfolioSubject(
            portfolio_subject_id=f"subject_{index}",
            created_at=NOW,
            created_by=actor(),
        )
        for index in (1, 2)
    )
    links = tuple(
        PortfolioSubjectClassLink(
            subject_link_id=f"link_{index}",
            portfolio_subject_id=subject.portfolio_subject_id,
            student_reference=reference(),
            confirmed_at=NOW,
            confirmed_by=actor(),
            confirmation_basis="teacher_confirmed",
        )
        for index, subject in enumerate(subjects, start=1)
    )
    state = project_identity_state((*subjects, *links))
    codes = {item.code for item in collect_identity_state_issues(state)}
    assert "identity.duplicate_active_association" in codes


def test_allocation_must_preserve_exact_roster_reference() -> None:
    predecessor = PortfolioSubject(
        portfolio_subject_id="subject_1", created_at=NOW, created_by=actor()
    )
    successor = PortfolioSubject(
        portfolio_subject_id="subject_2", created_at=NOW, created_by=actor()
    )
    old_link = PortfolioSubjectClassLink(
        subject_link_id="link_1",
        portfolio_subject_id=predecessor.portfolio_subject_id,
        student_reference=reference("english10_p2"),
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    new_link = PortfolioSubjectClassLink(
        subject_link_id="link_2",
        portfolio_subject_id=successor.portfolio_subject_id,
        student_reference=reference("csp_p1"),
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="decision_1",
        decision_type="merge_subjects",
        subject_ids=("subject_1", "subject_2"),
        subject_link_ids=(),
        decided_at=NOW,
        decided_by=actor(),
        authority_source="local_teacher_workflow",
        basis_type="direct_teacher_knowledge",
        basis_summary="Synthetic merge.",
    )
    transition = PortfolioSubjectIdentityTransition(
        subject_identity_transition_id="transition_1",
        transition_type="supersede",
        identity_decision_id=decision.identity_decision_id,
        predecessor_subject_ids=(predecessor.portfolio_subject_id,),
        successor_subject_ids=(successor.portfolio_subject_id,),
        association_allocations=(
            SubjectAssociationAllocation(
                predecessor_link_ids=(old_link.subject_link_id,),
                successor_subject_id=successor.portfolio_subject_id,
                successor_link_id=new_link.subject_link_id,
            ),
        ),
        affected_portfolio_ids=(),
    )
    state = project_identity_state(
        (predecessor, successor, old_link, new_link, decision, transition)
    )
    codes = {item.code for item in collect_identity_state_issues(state)}
    assert "identity.allocation_reference_mismatch" in codes


def test_merge_allocation_must_cover_decision_predecessor_links() -> None:
    first = PortfolioSubject(
        portfolio_subject_id="subject_1", created_at=NOW, created_by=actor()
    )
    second = PortfolioSubject(
        portfolio_subject_id="subject_2", created_at=NOW, created_by=actor()
    )
    successor = PortfolioSubject(
        portfolio_subject_id="subject_3", created_at=NOW, created_by=actor()
    )
    old_a = PortfolioSubjectClassLink(
        subject_link_id="link_1",
        portfolio_subject_id=first.portfolio_subject_id,
        student_reference=reference("english10_p2"),
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    old_b = PortfolioSubjectClassLink(
        subject_link_id="link_2",
        portfolio_subject_id=second.portfolio_subject_id,
        student_reference=reference("csp_p1"),
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    new_a = PortfolioSubjectClassLink(
        subject_link_id="link_3",
        portfolio_subject_id=successor.portfolio_subject_id,
        student_reference=old_a.student_reference,
        confirmed_at=NOW,
        confirmed_by=actor(),
        confirmation_basis="teacher_confirmed",
    )
    decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="decision_1",
        decision_type="merge_subjects",
        subject_ids=("subject_1", "subject_2", "subject_3"),
        subject_link_ids=("link_1", "link_2"),
        decided_at=NOW,
        decided_by=actor(),
        authority_source="local_teacher_workflow",
        basis_type="direct_teacher_knowledge",
        basis_summary="Synthetic merge.",
    )
    transition = PortfolioSubjectIdentityTransition(
        subject_identity_transition_id="transition_1",
        transition_type="merge",
        identity_decision_id=decision.identity_decision_id,
        predecessor_subject_ids=("subject_1", "subject_2"),
        successor_subject_ids=("subject_3",),
        association_allocations=(
            SubjectAssociationAllocation(
                predecessor_link_ids=("link_1",),
                successor_subject_id="subject_3",
                successor_link_id="link_3",
            ),
        ),
        affected_portfolio_ids=(),
    )
    state = project_identity_state(
        (first, second, successor, old_a, old_b, new_a, decision, transition)
    )
    codes = {item.code for item in collect_identity_state_issues(state)}
    assert "identity.allocation_inventory_mismatch" in codes


def test_display_snapshot_name_is_deterministic() -> None:
    with pytest.raises(ValueError):
        PortfolioSubjectDisplaySnapshot(
            display_snapshot_id="display_bad",
            subject_link_id="link_1",
            student_reference=reference(),
            first_name="Jane",
            last_name="Doe",
            preferred_name="Jay",
            display_name="Jane Doe",
            captured_at=NOW,
        )
