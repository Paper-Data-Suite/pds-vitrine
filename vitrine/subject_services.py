"""Application services for Portfolio Subject identity and Core roster links."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pds_core.class_metadata import (
    ClassMetadata,
    ClassMetadataError,
    class_metadata_path,
    load_class_metadata_for_class,
)
from pds_core.classes import class_folder, list_class_folders, load_class_roster
from pds_core.rosters import RosterError, StudentRecord
from pds_core.workspace import resolve_workspace_root

from vitrine.identity_state import (
    PortfolioSubjectIdentityState,
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
    VitrineRecord,
)
from vitrine.storage import (
    VitrineStorageCommitResult,
    VitrineStorageConflictError,
    VitrineStorageNotFoundError,
    commit_record_batch,
    load_current_records,
    load_current_state,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]

_RESOLUTION_STATUSES = frozenset(
    {
        "resolvable",
        "class_not_found",
        "class_metadata_missing",
        "class_metadata_invalid",
        "class_school_year_mismatch",
        "roster_missing",
        "roster_invalid",
        "student_not_found",
        "historical_reference_only",
        "source_unavailable",
    }
)


class SubjectWorkflowError(ValueError):
    """Expected application error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class IdentityDecisionContext:
    actor: ActorAttribution
    authority_source: str
    basis_type: str
    basis_summary: str
    external_basis_ref: str | None = None


@dataclass(frozen=True, slots=True)
class RosterStudentResolution:
    status: str
    reference: ClassQualifiedStudentRef
    student: StudentRecord | None = None
    class_metadata: ClassMetadata | None = None

    def __post_init__(self) -> None:
        if self.status not in _RESOLUTION_STATUSES:
            raise ValueError(f"unsupported roster resolution status: {self.status}")

    @property
    def resolvable(self) -> bool:
        return self.status == "resolvable" and self.student is not None


@dataclass(frozen=True, slots=True)
class SubjectReferenceResolution:
    reference: ClassQualifiedStudentRef
    status: str
    subject_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"unlinked", "resolved", "conflict"}:
            raise ValueError(f"unsupported Subject reference status: {self.status}")


@dataclass(frozen=True, slots=True)
class SubjectMutationResult:
    subject_ids: tuple[str, ...]
    link_ids: tuple[str, ...]
    affected_portfolio_ids: tuple[str, ...]
    commit: VitrineStorageCommitResult


@dataclass(frozen=True, slots=True)
class SubjectSummary:
    portfolio_subject_id: str
    display_name: str | None
    status: str
    current_link_count: int
    historical_link_count: int
    portfolio_count: int


@dataclass(frozen=True, slots=True)
class SubjectLinkView:
    subject_link_id: str
    reference: ClassQualifiedStudentRef
    status: str
    display_name: str | None
    current_resolution: str


@dataclass(frozen=True, slots=True)
class SubjectDetail:
    summary: SubjectSummary
    current_links: tuple[SubjectLinkView, ...]
    historical_links: tuple[SubjectLinkView, ...]


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _records_and_revision(
    workspace_root: str | Path,
) -> tuple[tuple[VitrineRecord, ...], int | None]:
    try:
        current = load_current_state(workspace_root)
    except VitrineStorageNotFoundError:
        return (), None
    return load_current_records(workspace_root), current.state_revision


def observe_state_revision(workspace_root: str | Path) -> int | None:
    """Return the exact current Vitrine state revision without mutating storage."""
    _, revision = _records_and_revision(workspace_root)
    return revision


def load_subject_identity_state(
    workspace_root: str | Path,
) -> tuple[PortfolioSubjectIdentityState, int | None]:
    records, revision = _records_and_revision(workspace_root)
    state = project_identity_state(records)
    fatal = tuple(
        issue
        for issue in collect_identity_state_issues(state)
        if issue.code != "identity.duplicate_active_association"
    )
    if fatal:
        raise SubjectWorkflowError(
            "identity_state_invalid",
            f"Portfolio Subject identity history contains {len(fatal)} issue(s).",
        )
    return state, revision


def resolve_subject_reference(
    workspace_root: str | Path,
    reference: ClassQualifiedStudentRef,
) -> SubjectReferenceResolution:
    """Resolve one exact roster reference to current Vitrine Subject identity."""
    state, _ = load_subject_identity_state(workspace_root)
    subjects = state.current_subjects_for_reference(reference)
    if not subjects:
        status = "unlinked"
    elif len(subjects) == 1:
        status = "resolved"
    else:
        status = "conflict"
    return SubjectReferenceResolution(reference, status, subjects)


def _require_expected_revision(
    actual: int | None,
    expected: int | None,
) -> None:
    if actual != expected:
        raise SubjectWorkflowError(
            "state_conflict",
            f"Vitrine state changed: expected {expected!r}, found {actual!r}.",
        )


def _commit_records(
    workspace_root: str | Path,
    records: Iterable[VitrineRecord],
    *,
    expected_state_revision: int | None,
) -> VitrineStorageCommitResult:
    try:
        return commit_record_batch(
            workspace_root,
            records,
            expected_state_revision=expected_state_revision,
        )
    except VitrineStorageConflictError as error:
        raise SubjectWorkflowError("state_conflict", str(error)) from error


def resolve_roster_student(
    workspace_root: str | Path,
    reference: ClassQualifiedStudentRef,
) -> RosterStudentResolution:
    """Resolve one exact Core class/year/student reference without fallback."""
    workspace = resolve_workspace_root(workspace_root)
    folder = class_folder(workspace, reference.class_id)
    try:
        if not folder.class_dir.is_dir():
            return RosterStudentResolution("class_not_found", reference)
        metadata_path = class_metadata_path(workspace, reference.class_id)
        if not metadata_path.is_file():
            return RosterStudentResolution("class_metadata_missing", reference)
    except OSError:
        return RosterStudentResolution("source_unavailable", reference)

    try:
        metadata = load_class_metadata_for_class(workspace, reference.class_id)
    except ClassMetadataError:
        return RosterStudentResolution("class_metadata_invalid", reference)
    except OSError:
        return RosterStudentResolution("source_unavailable", reference)
    if metadata.class_id != reference.class_id:
        return RosterStudentResolution("class_metadata_invalid", reference)
    if metadata.school_year != reference.school_year:
        return RosterStudentResolution(
            "class_school_year_mismatch",
            reference,
            class_metadata=metadata,
        )

    try:
        if not folder.roster_path.is_file():
            return RosterStudentResolution(
                "roster_missing", reference, class_metadata=metadata
            )
    except OSError:
        return RosterStudentResolution(
            "source_unavailable", reference, class_metadata=metadata
        )
    try:
        roster = load_class_roster(workspace, reference.class_id)
    except RosterError:
        return RosterStudentResolution(
            "roster_invalid", reference, class_metadata=metadata
        )
    except OSError:
        return RosterStudentResolution(
            "source_unavailable", reference, class_metadata=metadata
        )
    matches = tuple(
        student
        for student in roster.students
        if student.student_id == reference.student_id
    )
    if len(matches) != 1:
        status = "student_not_found" if not matches else "roster_invalid"
        return RosterStudentResolution(status, reference, class_metadata=metadata)
    return RosterStudentResolution(
        "resolvable",
        reference,
        student=matches[0],
        class_metadata=metadata,
    )


def list_linkable_classes(workspace_root: str | Path) -> tuple[tuple[str, str], ...]:
    """Return compact exact class/year choices that have valid Core sources."""
    workspace = resolve_workspace_root(workspace_root)
    result: list[tuple[str, str]] = []
    for folder in list_class_folders(
        workspace,
        require_roster=True,
        require_metadata=True,
        load_metadata=True,
    ):
        if folder.metadata is None:
            continue
        result.append((folder.class_id, folder.metadata.school_year))
    return tuple(sorted(result))


def list_roster_students(
    workspace_root: str | Path,
    *,
    class_id: str,
    school_year: str,
) -> tuple[StudentRecord, ...]:
    """Return one exact class roster after validating its school-year context."""
    workspace = resolve_workspace_root(workspace_root)
    metadata = load_class_metadata_for_class(workspace, class_id)
    if metadata.school_year != school_year:
        raise SubjectWorkflowError(
            "class_school_year_mismatch",
            "Selected class metadata no longer matches the expected school year.",
        )
    return load_class_roster(workspace, class_id).students


def _require_resolved_student(
    workspace_root: str | Path,
    reference: ClassQualifiedStudentRef,
) -> StudentRecord:
    resolution = resolve_roster_student(workspace_root, reference)
    if not resolution.resolvable or resolution.student is None:
        raise SubjectWorkflowError(
            resolution.status,
            "The exact Core roster student reference cannot be confirmed now.",
        )
    return resolution.student


def _confirmation_basis(context: IdentityDecisionContext) -> str:
    if context.basis_type == "migration_from_reviewed_source":
        return "authorized_import"
    if context.basis_type in {
        "authorized_institutional_crosswalk",
        "verified_sis_information",
        "transfer_or_enrollment_record",
    }:
        return "institution_confirmed"
    return "teacher_confirmed"


def _display_name(student: StudentRecord) -> tuple[str | None, str]:
    preferred = student.extra_fields.get("preferred_name", "").strip() or None
    given = preferred or student.first_name
    return preferred, f"{given} {student.last_name}".strip()


def _display_snapshot(
    *,
    link: PortfolioSubjectClassLink,
    student: StudentRecord,
    now: datetime,
    id_factory: IdFactory,
) -> PortfolioSubjectDisplaySnapshot:
    preferred, display = _display_name(student)
    return PortfolioSubjectDisplaySnapshot(
        display_snapshot_id=id_factory("display"),
        subject_link_id=link.subject_link_id,
        student_reference=link.student_reference,
        first_name=student.first_name,
        last_name=student.last_name,
        preferred_name=preferred,
        display_name=display,
        captured_at=now,
    )


def _decision(
    *,
    decision_type: str,
    subject_ids: Iterable[str],
    link_ids: Iterable[str],
    context: IdentityDecisionContext,
    now: datetime,
    id_factory: IdFactory,
) -> PortfolioSubjectIdentityDecision:
    return PortfolioSubjectIdentityDecision(
        identity_decision_id=id_factory("decision"),
        decision_type=decision_type,
        subject_ids=tuple(subject_ids),
        subject_link_ids=tuple(link_ids),
        decided_at=now,
        decided_by=context.actor,
        authority_source=context.authority_source,
        basis_type=context.basis_type,
        basis_summary=context.basis_summary,
        external_basis_ref=context.external_basis_ref,
    )


def _subject_map(state: PortfolioSubjectIdentityState) -> dict[str, PortfolioSubject]:
    return {item.portfolio_subject_id: item for item in state.subjects}


def _link_map(
    state: PortfolioSubjectIdentityState,
) -> dict[str, PortfolioSubjectClassLink]:
    return {item.subject_link_id: item for item in state.links}


def _require_active_subject(
    state: PortfolioSubjectIdentityState,
    subject_id: str,
) -> PortfolioSubject:
    subject = _subject_map(state).get(subject_id)
    if subject is None:
        raise SubjectWorkflowError("subject_not_found", "Portfolio Subject not found.")
    status = state.subject_status(subject_id)
    if status != "active":
        raise SubjectWorkflowError(
            "subject_historical",
            f"Portfolio Subject is historical ({status}).",
        )
    return subject


def _ensure_reference_available(
    state: PortfolioSubjectIdentityState,
    reference: ClassQualifiedStudentRef,
    *,
    allowed_subject_id: str | None = None,
) -> None:
    existing = state.current_subjects_for_reference(reference)
    if not existing:
        return
    if len(existing) > 1:
        raise SubjectWorkflowError(
            "roster_reference_conflict",
            "The exact roster reference has conflicting current Subjects.",
        )
    if allowed_subject_id is not None and existing[0] == allowed_subject_id:
        raise SubjectWorkflowError(
            "roster_reference_already_linked",
            "The exact roster reference is already linked to this Subject.",
        )
    raise SubjectWorkflowError(
        "duplicate_active_association",
        "The exact roster reference is already linked to another current Subject.",
    )


def create_portfolio_subject(
    workspace_root: str | Path,
    reference: ClassQualifiedStudentRef,
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    _ensure_reference_available(state, reference)
    student = _require_resolved_student(workspace_root, reference)
    now = clock()
    subject = PortfolioSubject(
        portfolio_subject_id=id_factory("subject"),
        created_at=now,
        created_by=context.actor,
        display_name_snapshot=_display_name(student)[1],
    )
    link = PortfolioSubjectClassLink(
        subject_link_id=id_factory("link"),
        portfolio_subject_id=subject.portfolio_subject_id,
        student_reference=reference,
        confirmed_at=now,
        confirmed_by=context.actor,
        confirmation_basis=_confirmation_basis(context),
        authority_reference=context.authority_source,
    )
    snapshot = _display_snapshot(
        link=link, student=student, now=now, id_factory=id_factory
    )
    created = _decision(
        decision_type="create_subject",
        subject_ids=(subject.portfolio_subject_id,),
        link_ids=(),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    confirmed = _decision(
        decision_type="confirm_link",
        subject_ids=(subject.portfolio_subject_id,),
        link_ids=(link.subject_link_id,),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    commit = _commit_records(
        workspace_root,
        (subject, link, snapshot, created, confirmed),
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=(subject.portfolio_subject_id,),
        link_ids=(link.subject_link_id,),
        affected_portfolio_ids=(),
        commit=commit,
    )


def link_portfolio_subject(
    workspace_root: str | Path,
    subject_id: str,
    reference: ClassQualifiedStudentRef,
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    _require_active_subject(state, subject_id)
    existing_subjects = state.current_subjects_for_reference(reference)
    if existing_subjects == (subject_id,):
        existing_link = next(
            item
            for item in state.current_links(subject_id)
            if item.student_reference == reference
        )
        current = load_current_state(workspace_root)
        return SubjectMutationResult(
            subject_ids=(subject_id,),
            link_ids=(existing_link.subject_link_id,),
            affected_portfolio_ids=(),
            commit=VitrineStorageCommitResult(
                state_revision=current.state_revision,
                state_sha256=current.state_sha256,
                created_record_revisions=(),
                no_op=True,
            ),
        )
    _ensure_reference_available(
        state, reference, allowed_subject_id=subject_id
    )
    student = _require_resolved_student(workspace_root, reference)
    now = clock()
    link = PortfolioSubjectClassLink(
        subject_link_id=id_factory("link"),
        portfolio_subject_id=subject_id,
        student_reference=reference,
        confirmed_at=now,
        confirmed_by=context.actor,
        confirmation_basis=_confirmation_basis(context),
        authority_reference=context.authority_source,
    )
    snapshot = _display_snapshot(
        link=link, student=student, now=now, id_factory=id_factory
    )
    confirmed = _decision(
        decision_type="confirm_link",
        subject_ids=(subject_id,),
        link_ids=(link.subject_link_id,),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    commit = _commit_records(
        workspace_root,
        (link, snapshot, confirmed),
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=(subject_id,),
        link_ids=(link.subject_link_id,),
        affected_portfolio_ids=(),
        commit=commit,
    )


def correct_subject_link(
    workspace_root: str | Path,
    subject_link_id: str,
    replacement: ClassQualifiedStudentRef,
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    old = _link_map(state).get(subject_link_id)
    if old is None:
        raise SubjectWorkflowError("link_not_found", "Subject link not found.")
    if state.link_status(old.subject_link_id) != "confirmed":
        raise SubjectWorkflowError("link_historical", "Subject link is historical.")
    _require_active_subject(state, old.portfolio_subject_id)
    if old.student_reference == replacement:
        raise SubjectWorkflowError(
            "replacement_reference_unchanged",
            "Replacement must use a different exact roster reference.",
        )
    _ensure_reference_available(state, replacement)
    student = _require_resolved_student(workspace_root, replacement)
    now = clock()
    new_link = PortfolioSubjectClassLink(
        subject_link_id=id_factory("link"),
        portfolio_subject_id=old.portfolio_subject_id,
        student_reference=replacement,
        confirmed_at=now,
        confirmed_by=context.actor,
        confirmation_basis=_confirmation_basis(context),
        authority_reference=context.authority_source,
        predecessor_link_id=old.subject_link_id,
    )
    snapshot = _display_snapshot(
        link=new_link, student=student, now=now, id_factory=id_factory
    )
    superseded = _decision(
        decision_type="supersede_link",
        subject_ids=(old.portfolio_subject_id,),
        link_ids=(old.subject_link_id,),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    confirmed = _decision(
        decision_type="confirm_link",
        subject_ids=(old.portfolio_subject_id,),
        link_ids=(new_link.subject_link_id,),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    commit = _commit_records(
        workspace_root,
        (new_link, snapshot, superseded, confirmed),
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=(old.portfolio_subject_id,),
        link_ids=(new_link.subject_link_id,),
        affected_portfolio_ids=(),
        commit=commit,
    )


def invalidate_subject_link(
    workspace_root: str | Path,
    subject_link_id: str,
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    link = _link_map(state).get(subject_link_id)
    if link is None:
        raise SubjectWorkflowError("link_not_found", "Subject link not found.")
    if state.link_status(subject_link_id) != "confirmed":
        raise SubjectWorkflowError("link_historical", "Subject link is historical.")
    now = clock()
    decision = _decision(
        decision_type="invalidate_link",
        subject_ids=(link.portfolio_subject_id,),
        link_ids=(subject_link_id,),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    commit = _commit_records(
        workspace_root,
        (decision,),
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=(link.portfolio_subject_id,),
        link_ids=(subject_link_id,),
        affected_portfolio_ids=(),
        commit=commit,
    )


def _copy_or_resolve_snapshot(
    workspace_root: str | Path,
    state: PortfolioSubjectIdentityState,
    predecessor: PortfolioSubjectClassLink,
    successor: PortfolioSubjectClassLink,
    *,
    now: datetime,
    id_factory: IdFactory,
) -> PortfolioSubjectDisplaySnapshot | None:
    resolution = resolve_roster_student(workspace_root, predecessor.student_reference)
    if resolution.resolvable and resolution.student is not None:
        return _display_snapshot(
            link=successor,
            student=resolution.student,
            now=now,
            id_factory=id_factory,
        )
    prior = state.latest_display_snapshot(predecessor.subject_link_id)
    if prior is None:
        return None
    return PortfolioSubjectDisplaySnapshot(
        display_snapshot_id=id_factory("display"),
        subject_link_id=successor.subject_link_id,
        student_reference=successor.student_reference,
        first_name=prior.first_name,
        last_name=prior.last_name,
        preferred_name=prior.preferred_name,
        display_name=prior.display_name,
        captured_at=now,
    )


def _affected_portfolios(
    state: PortfolioSubjectIdentityState,
    predecessor_subject_ids: set[str],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            item.portfolio_id
            for item in state.portfolios
            if item.portfolio_subject_id in predecessor_subject_ids
        )
    )


def _subject_display_from_links(
    state: PortfolioSubjectIdentityState,
    links: Sequence[PortfolioSubjectClassLink],
) -> str | None:
    labels = {
        snapshot.display_name
        for link in links
        if (snapshot := state.latest_display_snapshot(link.subject_link_id))
        is not None
    }
    return next(iter(labels)) if len(labels) == 1 else None


def merge_portfolio_subjects(
    workspace_root: str | Path,
    subject_ids: Sequence[str],
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    ordered_subjects = tuple(dict.fromkeys(subject_ids))
    if len(ordered_subjects) < 2:
        raise SubjectWorkflowError(
            "merge_conflict", "Merge requires at least two distinct Subjects."
        )
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    for subject_id in ordered_subjects:
        _require_active_subject(state, subject_id)
    predecessor_links = tuple(
        link
        for subject_id in ordered_subjects
        for link in state.current_links(subject_id)
    )
    if not predecessor_links:
        raise SubjectWorkflowError(
            "merge_conflict", "Selected Subjects have no current roster links."
        )
    now = clock()
    successor_id = id_factory("subject")
    successor = PortfolioSubject(
        portfolio_subject_id=successor_id,
        created_at=now,
        created_by=context.actor,
        display_name_snapshot=_subject_display_from_links(
            state, predecessor_links
        ),
    )
    by_reference: dict[
        ClassQualifiedStudentRef, list[PortfolioSubjectClassLink]
    ] = defaultdict(list)
    for link in predecessor_links:
        by_reference[link.student_reference].append(link)

    new_links: list[PortfolioSubjectClassLink] = []
    snapshots: list[PortfolioSubjectDisplaySnapshot] = []
    allocations: list[SubjectAssociationAllocation] = []
    for reference in sorted(
        by_reference,
        key=lambda item: (item.school_year, item.class_id, item.student_id),
    ):
        predecessors = tuple(
            sorted(by_reference[reference], key=lambda item: item.subject_link_id)
        )
        new_link = PortfolioSubjectClassLink(
            subject_link_id=id_factory("link"),
            portfolio_subject_id=successor_id,
            student_reference=reference,
            confirmed_at=now,
            confirmed_by=context.actor,
            confirmation_basis=_confirmation_basis(context),
            authority_reference=context.authority_source,
        )
        new_links.append(new_link)
        snapshot = _copy_or_resolve_snapshot(
            workspace_root,
            state,
            predecessors[0],
            new_link,
            now=now,
            id_factory=id_factory,
        )
        if snapshot is not None:
            snapshots.append(snapshot)
        allocations.append(
            SubjectAssociationAllocation(
                predecessor_link_ids=tuple(
                    item.subject_link_id for item in predecessors
                ),
                successor_subject_id=successor_id,
                successor_link_id=new_link.subject_link_id,
            )
        )

    supersede_links = _decision(
        decision_type="supersede_link",
        subject_ids=ordered_subjects,
        link_ids=tuple(item.subject_link_id for item in predecessor_links),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    confirm_links = _decision(
        decision_type="confirm_link",
        subject_ids=(successor_id,),
        link_ids=tuple(item.subject_link_id for item in new_links),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    merge_decision = _decision(
        decision_type="merge_subjects",
        subject_ids=(*ordered_subjects, successor_id),
        link_ids=tuple(item.subject_link_id for item in predecessor_links),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    affected = _affected_portfolios(state, set(ordered_subjects))
    transition = PortfolioSubjectIdentityTransition(
        subject_identity_transition_id=id_factory("transition"),
        transition_type="merge",
        identity_decision_id=merge_decision.identity_decision_id,
        predecessor_subject_ids=ordered_subjects,
        successor_subject_ids=(successor_id,),
        association_allocations=tuple(allocations),
        affected_portfolio_ids=affected,
    )
    records: tuple[VitrineRecord, ...] = (
        successor,
        *new_links,
        *snapshots,
        supersede_links,
        confirm_links,
        merge_decision,
        transition,
    )
    commit = _commit_records(
        workspace_root,
        records,
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=(successor_id,),
        link_ids=tuple(item.subject_link_id for item in new_links),
        affected_portfolio_ids=affected,
        commit=commit,
    )


def split_portfolio_subject(
    workspace_root: str | Path,
    subject_id: str,
    groups: Sequence[Sequence[str]],
    *,
    context: IdentityDecisionContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SubjectMutationResult:
    normalized_groups = tuple(tuple(dict.fromkeys(group)) for group in groups)
    if len(normalized_groups) < 2 or any(not group for group in normalized_groups):
        raise SubjectWorkflowError(
            "split_allocation_invalid",
            "Split requires at least two nonempty successor groups.",
        )
    state, actual_revision = load_subject_identity_state(workspace_root)
    _require_expected_revision(actual_revision, expected_state_revision)
    _require_active_subject(state, subject_id)
    current_links = state.current_links(subject_id)
    current_by_id = {item.subject_link_id: item for item in current_links}
    supplied = tuple(link_id for group in normalized_groups for link_id in group)
    if len(supplied) != len(set(supplied)) or set(supplied) != set(current_by_id):
        raise SubjectWorkflowError(
            "split_allocation_invalid",
            "Every current Subject link must be allocated exactly once.",
        )

    now = clock()
    successors: list[PortfolioSubject] = []
    new_links: list[PortfolioSubjectClassLink] = []
    snapshots: list[PortfolioSubjectDisplaySnapshot] = []
    allocations: list[SubjectAssociationAllocation] = []
    for group in normalized_groups:
        predecessor_group = tuple(current_by_id[link_id] for link_id in group)
        successor_id = id_factory("subject")
        successors.append(
            PortfolioSubject(
                portfolio_subject_id=successor_id,
                created_at=now,
                created_by=context.actor,
                display_name_snapshot=_subject_display_from_links(
                    state, predecessor_group
                ),
            )
        )
        for predecessor in predecessor_group:
            new_link = PortfolioSubjectClassLink(
                subject_link_id=id_factory("link"),
                portfolio_subject_id=successor_id,
                student_reference=predecessor.student_reference,
                confirmed_at=now,
                confirmed_by=context.actor,
                confirmation_basis=_confirmation_basis(context),
                authority_reference=context.authority_source,
            )
            new_links.append(new_link)
            snapshot = _copy_or_resolve_snapshot(
                workspace_root,
                state,
                predecessor,
                new_link,
                now=now,
                id_factory=id_factory,
            )
            if snapshot is not None:
                snapshots.append(snapshot)
            allocations.append(
                SubjectAssociationAllocation(
                    predecessor_link_ids=(predecessor.subject_link_id,),
                    successor_subject_id=successor_id,
                    successor_link_id=new_link.subject_link_id,
                )
            )

    supersede_links = _decision(
        decision_type="supersede_link",
        subject_ids=(subject_id,),
        link_ids=tuple(current_by_id),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    confirm_links = _decision(
        decision_type="confirm_link",
        subject_ids=tuple(item.portfolio_subject_id for item in successors),
        link_ids=tuple(item.subject_link_id for item in new_links),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    split_decision = _decision(
        decision_type="split_subject",
        subject_ids=(subject_id, *(item.portfolio_subject_id for item in successors)),
        link_ids=tuple(current_by_id),
        context=context,
        now=now,
        id_factory=id_factory,
    )
    affected = _affected_portfolios(state, {subject_id})
    transition = PortfolioSubjectIdentityTransition(
        subject_identity_transition_id=id_factory("transition"),
        transition_type="split",
        identity_decision_id=split_decision.identity_decision_id,
        predecessor_subject_ids=(subject_id,),
        successor_subject_ids=tuple(
            item.portfolio_subject_id for item in successors
        ),
        association_allocations=tuple(allocations),
        affected_portfolio_ids=affected,
    )
    records: tuple[VitrineRecord, ...] = (
        *successors,
        *new_links,
        *snapshots,
        supersede_links,
        confirm_links,
        split_decision,
        transition,
    )
    commit = _commit_records(
        workspace_root,
        records,
        expected_state_revision=expected_state_revision,
    )
    return SubjectMutationResult(
        subject_ids=tuple(item.portfolio_subject_id for item in successors),
        link_ids=tuple(item.subject_link_id for item in new_links),
        affected_portfolio_ids=affected,
        commit=commit,
    )


def _link_view(
    workspace_root: str | Path,
    state: PortfolioSubjectIdentityState,
    link: PortfolioSubjectClassLink,
) -> SubjectLinkView:
    snapshot = state.latest_display_snapshot(link.subject_link_id)
    resolution = resolve_roster_student(workspace_root, link.student_reference)
    current_resolution = resolution.status
    if state.link_status(link.subject_link_id) != "confirmed" and (
        current_resolution != "resolvable"
    ):
        current_resolution = "historical_reference_only"
    return SubjectLinkView(
        subject_link_id=link.subject_link_id,
        reference=link.student_reference,
        status=state.link_status(link.subject_link_id),
        display_name=snapshot.display_name if snapshot is not None else None,
        current_resolution=current_resolution,
    )


def list_subjects(workspace_root: str | Path) -> tuple[SubjectSummary, ...]:
    state, _ = load_subject_identity_state(workspace_root)
    portfolio_counts: dict[str, int] = defaultdict(int)
    for portfolio in state.portfolios:
        portfolio_counts[portfolio.portfolio_subject_id] += 1
    result: list[SubjectSummary] = []
    for subject in state.subjects:
        current = state.current_links(subject.portfolio_subject_id)
        all_links = tuple(
            item
            for item in state.links
            if item.portfolio_subject_id == subject.portfolio_subject_id
        )
        label = subject.display_name_snapshot
        if current:
            latest = state.latest_display_snapshot(current[0].subject_link_id)
            if latest is not None:
                label = latest.display_name
        result.append(
            SubjectSummary(
                portfolio_subject_id=subject.portfolio_subject_id,
                display_name=label,
                status=state.subject_status(subject.portfolio_subject_id),
                current_link_count=len(current),
                historical_link_count=len(all_links) - len(current),
                portfolio_count=portfolio_counts[subject.portfolio_subject_id],
            )
        )
    return tuple(sorted(result, key=lambda item: item.portfolio_subject_id))


def show_subject(
    workspace_root: str | Path, subject_id: str
) -> SubjectDetail:
    state, _ = load_subject_identity_state(workspace_root)
    subject = _subject_map(state).get(subject_id)
    if subject is None:
        raise SubjectWorkflowError("subject_not_found", "Portfolio Subject not found.")
    summary = next(
        item
        for item in list_subjects(workspace_root)
        if item.portfolio_subject_id == subject_id
    )
    current_ids = {
        item.subject_link_id for item in state.current_links(subject_id)
    }
    all_links = tuple(
        item for item in state.links if item.portfolio_subject_id == subject_id
    )
    current = tuple(
        _link_view(workspace_root, state, item)
        for item in all_links
        if item.subject_link_id in current_ids
    )
    historical = tuple(
        _link_view(workspace_root, state, item)
        for item in all_links
        if item.subject_link_id not in current_ids
    )
    return SubjectDetail(summary, current, historical)


__all__ = [
    "IdentityDecisionContext",
    "RosterStudentResolution",
    "SubjectDetail",
    "SubjectLinkView",
    "SubjectMutationResult",
    "SubjectReferenceResolution",
    "SubjectSummary",
    "SubjectWorkflowError",
    "correct_subject_link",
    "create_portfolio_subject",
    "invalidate_subject_link",
    "link_portfolio_subject",
    "list_linkable_classes",
    "list_roster_students",
    "list_subjects",
    "load_subject_identity_state",
    "merge_portfolio_subjects",
    "observe_state_revision",
    "resolve_roster_student",
    "resolve_subject_reference",
    "show_subject",
    "split_portfolio_subject",
]
