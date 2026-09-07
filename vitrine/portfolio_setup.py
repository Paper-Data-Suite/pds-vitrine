"""Read-only planning for Create Portfolio for Student guided setup."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from pds_core.rosters import StudentRecord

import vitrine.subject_services as subject_services
from vitrine.identity_state import (
    collect_identity_state_issues,
    project_identity_state,
)
from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    Portfolio,
    PortfolioProfileBinding,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    ProfileRevisionRef,
    VitrineRecord,
)
from vitrine.portfolio_services import list_portfolios
from vitrine.profile_services import (
    ProfileBindingContext,
    ProfileWorkflowError,
    get_portfolio_profile_binding,
    get_profile_requirements,
    get_profile_revision,
    list_bindable_profile_revisions,
    load_profile_state,
    validate_profile_applicability,
)
from vitrine.profile_state import (
    collect_profile_state_issues,
    project_profile_state,
)
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageValidationError,
    commit_record_batch,
    key_for_record,
    load_current_records,
)
from vitrine.subject_services import (
    IdentityDecisionContext,
    list_subjects,
    observe_state_revision,
    resolve_roster_student,
    resolve_subject_reference,
    show_subject,
)

SetupIdFactory = Callable[[str], str]

CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION: Final[str] = (
    "vitrine_create_portfolio_for_student_v1"
)
PORTFOLIO_SETUP_PURPOSES: Final[frozenset[str]] = frozenset({"improvement", "showcase"})
PORTFOLIO_SETUP_SUBJECT_ACTIONS: Final[frozenset[str]] = frozenset(
    {"create_new", "link_existing"}
)


class PortfolioSetupError(ValueError):
    """Expected read-only setup planning failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PortfolioSetupStudentSnapshot:
    reference: ClassQualifiedStudentRef
    first_name: str
    last_name: str
    preferred_name: str | None
    display_name: str
    period: str


@dataclass(frozen=True, slots=True)
class PortfolioSetupLinkPreview:
    subject_link_id: str | None
    reference: ClassQualifiedStudentRef
    display_name: str | None
    source_resolution: str
    disposition: str


@dataclass(frozen=True, slots=True)
class PortfolioSetupExistingPortfolio:
    portfolio_id: str
    title_snapshot: str | None
    profile_binding_id: str | None
    profile_revision: ProfileRevisionRef | None
    purpose_kind: str | None


@dataclass(frozen=True, slots=True)
class PortfolioSetupSubjectResolution:
    reference: ClassQualifiedStudentRef
    roster_status: str
    student: PortfolioSetupStudentSnapshot | None
    subject_status: str
    subject_ids: tuple[str, ...]
    current_links: tuple[PortfolioSetupLinkPreview, ...]
    existing_portfolios: tuple[PortfolioSetupExistingPortfolio, ...]

    @property
    def resolved_subject_id(self) -> str | None:
        if self.subject_status != "resolved" or len(self.subject_ids) != 1:
            return None
        return self.subject_ids[0]


@dataclass(frozen=True, slots=True)
class PortfolioSetupSectionSummary:
    section_id: str
    label: str
    order: int
    obligation: str


@dataclass(frozen=True, slots=True)
class PortfolioSetupProfileChoice:
    reference: ProfileRevisionRef
    label: str
    purpose_kind: str
    profile_family_id: str | None
    sections: tuple[PortfolioSetupSectionSummary, ...]
    requirement_count: int
    audience_classes: tuple[str, ...]
    known_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioSetupProposedIds:
    portfolio_id: str
    profile_binding_id: str
    portfolio_subject_id: str | None = None
    subject_link_id: str | None = None
    display_snapshot_id: str | None = None
    identity_decision_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreatePortfolioForStudentRequest:
    student_reference: ClassQualifiedStudentRef
    purpose_kind: str
    profile_revision: ProfileRevisionRef | None = None
    profile_context: ProfileBindingContext = field(
        default_factory=ProfileBindingContext
    )
    subject_action: str | None = None
    existing_subject_id: str | None = None
    identity_context: IdentityDecisionContext | None = None
    title_snapshot: str | None = None
    description_snapshot: str | None = None


@dataclass(frozen=True, slots=True)
class PortfolioSetupPlan:
    contract_version: str
    observed_state_revision: int | None
    request: CreatePortfolioForStudentRequest
    student: PortfolioSetupStudentSnapshot | None
    subject_resolution: PortfolioSetupSubjectResolution
    subject_action: str | None
    portfolio_subject_id: str | None
    resulting_links: tuple[PortfolioSetupLinkPreview, ...]
    existing_portfolios: tuple[PortfolioSetupExistingPortfolio, ...]
    profile_choices: tuple[PortfolioSetupProfileChoice, ...]
    selected_profile: PortfolioSetupProfileChoice | None
    effective_profile_context: ProfileBindingContext
    proposed_ids: PortfolioSetupProposedIds
    planned_record_kinds: tuple[str, ...]
    blocking_codes: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return (
            not self.blocking_codes
            and self.student is not None
            and self.portfolio_subject_id is not None
            and self.selected_profile is not None
        )


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _student_snapshot(
    reference: ClassQualifiedStudentRef,
    *,
    first_name: str,
    last_name: str,
    period: str,
    preferred_name: str | None,
) -> PortfolioSetupStudentSnapshot:
    display_first = preferred_name or first_name
    return PortfolioSetupStudentSnapshot(
        reference=reference,
        first_name=first_name,
        last_name=last_name,
        preferred_name=preferred_name,
        display_name=f"{display_first} {last_name}".strip(),
        period=period,
    )


def _existing_portfolios(
    workspace_root: str | Path,
    subject_id: str,
) -> tuple[PortfolioSetupExistingPortfolio, ...]:
    result: list[PortfolioSetupExistingPortfolio] = []
    for summary in list_portfolios(workspace_root):
        if summary.portfolio_subject_id != subject_id:
            continue
        binding = get_portfolio_profile_binding(workspace_root, summary.portfolio_id)
        if binding is None:
            result.append(
                PortfolioSetupExistingPortfolio(
                    portfolio_id=summary.portfolio_id,
                    title_snapshot=summary.title_snapshot,
                    profile_binding_id=None,
                    profile_revision=None,
                    purpose_kind=None,
                )
            )
            continue
        revision = get_profile_revision(workspace_root, binding.profile_revision)
        result.append(
            PortfolioSetupExistingPortfolio(
                portfolio_id=summary.portfolio_id,
                title_snapshot=summary.title_snapshot,
                profile_binding_id=binding.profile_binding_id,
                profile_revision=binding.profile_revision,
                purpose_kind=revision.purpose_kind,
            )
        )
    return tuple(sorted(result, key=lambda item: item.portfolio_id))


def _link_previews(
    workspace_root: str | Path,
    subject_id: str,
) -> tuple[PortfolioSetupLinkPreview, ...]:
    detail = show_subject(workspace_root, subject_id)
    return tuple(
        PortfolioSetupLinkPreview(
            subject_link_id=item.subject_link_id,
            reference=item.reference,
            display_name=item.display_name,
            source_resolution=item.current_resolution,
            disposition="existing",
        )
        for item in detail.current_links
    )


def resolve_portfolio_setup_subject(
    workspace_root: str | Path,
    reference: ClassQualifiedStudentRef,
) -> PortfolioSetupSubjectResolution:
    """Resolve one exact roster endpoint without cross-class inference."""
    roster = resolve_roster_student(workspace_root, reference)
    student: PortfolioSetupStudentSnapshot | None = None
    if roster.student is not None and roster.status == "resolvable":
        preferred_name = (
            roster.student.extra_fields.get("preferred_name", "").strip() or None
        )
        student = _student_snapshot(
            reference,
            first_name=roster.student.first_name,
            last_name=roster.student.last_name,
            period=roster.student.period,
            preferred_name=preferred_name,
        )

    reference_resolution = resolve_subject_reference(workspace_root, reference)
    subject_ids = reference_resolution.subject_ids
    links: tuple[PortfolioSetupLinkPreview, ...] = ()
    portfolios: tuple[PortfolioSetupExistingPortfolio, ...] = ()
    if reference_resolution.status == "resolved" and len(subject_ids) == 1:
        links = _link_previews(workspace_root, subject_ids[0])
        portfolios = _existing_portfolios(workspace_root, subject_ids[0])

    return PortfolioSetupSubjectResolution(
        reference=reference,
        roster_status=roster.status,
        student=student,
        subject_status=reference_resolution.status,
        subject_ids=subject_ids,
        current_links=links,
        existing_portfolios=portfolios,
    )


def _profile_choice(
    workspace_root: str | Path,
    reference: ProfileRevisionRef,
) -> PortfolioSetupProfileChoice:
    revision = get_profile_revision(workspace_root, reference)
    requirements = get_profile_requirements(workspace_root, reference)
    return PortfolioSetupProfileChoice(
        reference=reference,
        label=revision.label,
        purpose_kind=revision.purpose_kind,
        profile_family_id=revision.profile_family_id,
        sections=tuple(
            PortfolioSetupSectionSummary(
                section_id=item.section_id,
                label=item.label,
                order=item.order,
                obligation=item.obligation,
            )
            for item in sorted(revision.sections, key=lambda item: item.order)
        ),
        requirement_count=len(requirements),
        audience_classes=tuple(item.audience_class for item in revision.audience_rules),
        known_limitations=revision.known_limitations,
    )


def list_portfolio_setup_profiles(
    workspace_root: str | Path,
    *,
    purpose_kind: str,
) -> tuple[PortfolioSetupProfileChoice, ...]:
    """List exact bindable Profile revisions for one explicit purpose."""
    if purpose_kind not in PORTFOLIO_SETUP_PURPOSES:
        raise PortfolioSetupError(
            "profile_purpose_unsupported",
            "Create Portfolio for Student supports improvement or showcase.",
        )
    revisions = list_bindable_profile_revisions(
        workspace_root,
        purpose_kind=purpose_kind,
    )
    return tuple(_profile_choice(workspace_root, item.reference) for item in revisions)


def _effective_profile_context(
    context: ProfileBindingContext,
    reference: ClassQualifiedStudentRef,
) -> ProfileBindingContext:
    if context.school_year is not None:
        return context
    return replace(context, school_year=reference.school_year)


def _subject_summary_status(
    workspace_root: str | Path,
    subject_id: str,
) -> str | None:
    return next(
        (
            item.status
            for item in list_subjects(workspace_root)
            if item.portfolio_subject_id == subject_id
        ),
        None,
    )


def _proposed_ids(
    action: str | None,
    *,
    existing_subject_id: str | None,
    id_factory: SetupIdFactory,
) -> PortfolioSetupProposedIds:
    subject_id = existing_subject_id
    link_id: str | None = None
    display_id: str | None = None
    decisions: tuple[str, ...] = ()
    if action == "create_new":
        subject_id = id_factory("subject")
        link_id = id_factory("link")
        display_id = id_factory("display")
        decisions = (id_factory("decision"), id_factory("decision"))
    elif action == "link_existing":
        link_id = id_factory("link")
        display_id = id_factory("display")
        decisions = (id_factory("decision"),)
    return PortfolioSetupProposedIds(
        portfolio_id=id_factory("portfolio"),
        profile_binding_id=id_factory("profile_binding"),
        portfolio_subject_id=subject_id,
        subject_link_id=link_id,
        display_snapshot_id=display_id,
        identity_decision_ids=decisions,
    )


def _planned_record_kinds(action: str | None) -> tuple[str, ...]:
    if action == "create_new":
        return (
            "portfolio_subject",
            "portfolio_subject_class_link",
            "portfolio_subject_display_snapshot",
            "portfolio_subject_identity_decision",
            "portfolio_subject_identity_decision",
            "portfolio",
            "portfolio_profile_binding",
        )
    if action == "link_existing":
        return (
            "portfolio_subject_class_link",
            "portfolio_subject_display_snapshot",
            "portfolio_subject_identity_decision",
            "portfolio",
            "portfolio_profile_binding",
        )
    if action == "reuse_existing":
        return ("portfolio", "portfolio_profile_binding")
    return ()


def _proposed_link(
    plan_ids: PortfolioSetupProposedIds,
    student: PortfolioSetupStudentSnapshot,
) -> PortfolioSetupLinkPreview:
    return PortfolioSetupLinkPreview(
        subject_link_id=plan_ids.subject_link_id,
        reference=student.reference,
        display_name=student.display_name,
        source_resolution="resolvable",
        disposition="proposed",
    )


def plan_create_portfolio_for_student(
    workspace_root: str | Path,
    request: CreatePortfolioForStudentRequest,
    *,
    id_factory: SetupIdFactory = _id,
) -> PortfolioSetupPlan:
    """Build a complete transient setup plan without canonical mutation."""
    if request.purpose_kind not in PORTFOLIO_SETUP_PURPOSES:
        raise PortfolioSetupError(
            "profile_purpose_unsupported",
            "Create Portfolio for Student supports improvement or showcase.",
        )
    if (
        request.subject_action is not None
        and request.subject_action not in PORTFOLIO_SETUP_SUBJECT_ACTIONS
    ):
        raise PortfolioSetupError(
            "subject_action_invalid",
            "Subject action must be create_new or link_existing when supplied.",
        )

    observed = observe_state_revision(workspace_root)
    resolution = resolve_portfolio_setup_subject(
        workspace_root,
        request.student_reference,
    )
    blockers: list[str] = []
    if resolution.roster_status != "resolvable" or resolution.student is None:
        blockers.append("student_reference_unavailable")

    action: str | None = None
    subject_id: str | None = None
    links: tuple[PortfolioSetupLinkPreview, ...] = ()
    existing_portfolios: tuple[PortfolioSetupExistingPortfolio, ...] = ()

    if resolution.subject_status == "conflict":
        blockers.append("subject_identity_conflict")
    elif resolution.subject_status == "resolved":
        action = "reuse_existing"
        subject_id = resolution.resolved_subject_id
        links = resolution.current_links
        existing_portfolios = resolution.existing_portfolios
        if (
            request.subject_action is not None
            or request.existing_subject_id is not None
        ):
            blockers.append("subject_already_resolved")
    else:
        if request.subject_action is None:
            blockers.append("subject_choice_required")
        elif request.subject_action == "create_new":
            action = "create_new"
            if request.existing_subject_id is not None:
                blockers.append("subject_choice_invalid")
            if request.identity_context is None:
                blockers.append("identity_basis_required")
        else:
            action = "link_existing"
            if request.existing_subject_id is None:
                blockers.append("subject_choice_required")
            else:
                status = _subject_summary_status(
                    workspace_root,
                    request.existing_subject_id,
                )
                if status is None:
                    blockers.append("subject_not_found")
                elif status != "active":
                    blockers.append("subject_historical")
                else:
                    subject_id = request.existing_subject_id
                    links = _link_previews(workspace_root, subject_id)
                    existing_portfolios = _existing_portfolios(
                        workspace_root,
                        subject_id,
                    )
            if request.identity_context is None:
                blockers.append("identity_basis_required")

    plan_ids = _proposed_ids(
        action,
        existing_subject_id=subject_id,
        id_factory=id_factory,
    )
    if action == "create_new":
        subject_id = plan_ids.portfolio_subject_id

    if (
        action in {"create_new", "link_existing"}
        and resolution.student is not None
        and plan_ids.subject_link_id is not None
    ):
        links = (*links, _proposed_link(plan_ids, resolution.student))

    profile_choices = list_portfolio_setup_profiles(
        workspace_root,
        purpose_kind=request.purpose_kind,
    )
    selected_profile: PortfolioSetupProfileChoice | None = None
    effective_context = _effective_profile_context(
        request.profile_context,
        request.student_reference,
    )
    if request.profile_revision is None:
        blockers.append(
            "profile_choice_required" if profile_choices else "profile_unavailable"
        )
    else:
        try:
            revision = get_profile_revision(
                workspace_root,
                request.profile_revision,
            )
        except ProfileWorkflowError as error:
            if error.code == "profile_revision_not_found":
                blockers.append("profile_revision_not_found")
            else:
                raise
        else:
            if revision.purpose_kind != request.purpose_kind:
                blockers.append("profile_purpose_mismatch")
            else:
                selected_profile = next(
                    (
                        item
                        for item in profile_choices
                        if item.reference == request.profile_revision
                    ),
                    None,
                )
                if selected_profile is None:
                    blockers.append("profile_not_bindable")
                else:
                    try:
                        validate_profile_applicability(
                            revision,
                            effective_context,
                        )
                    except ProfileWorkflowError as error:
                        if error.code == "profile_not_applicable":
                            blockers.append("profile_not_applicable")
                        else:
                            raise

    return PortfolioSetupPlan(
        contract_version=CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION,
        observed_state_revision=observed,
        request=request,
        student=resolution.student,
        subject_resolution=resolution,
        subject_action=action,
        portfolio_subject_id=subject_id,
        resulting_links=links,
        existing_portfolios=existing_portfolios,
        profile_choices=profile_choices,
        selected_profile=selected_profile,
        effective_profile_context=effective_context,
        proposed_ids=replace(
            plan_ids,
            portfolio_subject_id=subject_id,
        ),
        planned_record_kinds=_planned_record_kinds(action),
        blocking_codes=tuple(dict.fromkeys(blockers)),
    )


SetupClock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class PortfolioSetupResult:
    portfolio_subject_id: str
    portfolio_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    state_revision: int
    subject_action: str
    created_record_ids: tuple[str, ...]


def _clock() -> datetime:
    return datetime.now(timezone.utc)


class _PlannedIdentityIdFactory:
    def __init__(
        self,
        *,
        display_snapshot_id: str | None,
        identity_decision_ids: tuple[str, ...],
    ) -> None:
        self._display_snapshot_id = display_snapshot_id
        self._decision_ids = list(identity_decision_ids)

    def __call__(self, prefix: str) -> str:
        if prefix == "display":
            if self._display_snapshot_id is None:
                raise PortfolioSetupError(
                    "setup_plan_invalid",
                    "Setup plan is missing the reviewed display Snapshot ID.",
                )
            value = self._display_snapshot_id
            self._display_snapshot_id = None
            return value
        if prefix == "decision":
            if not self._decision_ids:
                raise PortfolioSetupError(
                    "setup_plan_invalid",
                    "Setup plan is missing a reviewed identity Decision ID.",
                )
            return self._decision_ids.pop(0)
        raise PortfolioSetupError(
            "setup_plan_invalid",
            f"Unexpected setup identity ID prefix: {prefix}.",
        )


def _validate_plan_shape(plan: PortfolioSetupPlan) -> None:
    if plan.contract_version != CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan contract version is not supported.",
        )
    if not plan.ready:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is not ready for canonical creation.",
        )
    if plan.subject_action not in {
        "create_new",
        "link_existing",
        "reuse_existing",
    }:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan does not identify one supported Subject action.",
        )
    if plan.portfolio_subject_id is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing the resulting Portfolio Subject ID.",
        )
    if plan.request.profile_revision is None or plan.selected_profile is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing the reviewed exact Profile Revision.",
        )
    if plan.selected_profile.reference != plan.request.profile_revision:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan Profile detail does not match its exact requested Revision.",
        )
    if plan.proposed_ids.portfolio_subject_id != plan.portfolio_subject_id:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan Subject ID does not match its reviewed proposed IDs.",
        )
    if plan.planned_record_kinds != _planned_record_kinds(plan.subject_action):
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan durable record inventory is inconsistent.",
        )
    if plan.subject_action == "create_new":
        if (
            plan.proposed_ids.subject_link_id is None
            or plan.proposed_ids.display_snapshot_id is None
            or len(plan.proposed_ids.identity_decision_ids) != 2
            or plan.request.identity_context is None
        ):
            raise PortfolioSetupError(
                "setup_plan_invalid",
                "New-Subject setup is missing reviewed identity record identities.",
            )
    elif plan.subject_action == "link_existing":
        if (
            plan.proposed_ids.subject_link_id is None
            or plan.proposed_ids.display_snapshot_id is None
            or len(plan.proposed_ids.identity_decision_ids) != 1
            or plan.request.identity_context is None
        ):
            raise PortfolioSetupError(
                "setup_plan_invalid",
                "Existing-Subject link setup is missing reviewed identity record identities.",
            )
    elif (
        plan.proposed_ids.subject_link_id is not None
        or plan.proposed_ids.display_snapshot_id is not None
        or plan.proposed_ids.identity_decision_ids
    ):
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Resolved-Subject setup unexpectedly proposes identity records.",
        )


def _current_student_for_plan(
    workspace_root: str | Path,
    plan: PortfolioSetupPlan,
) -> StudentRecord:
    resolution = resolve_roster_student(
        workspace_root,
        plan.request.student_reference,
    )
    if not resolution.resolvable or resolution.student is None:
        raise PortfolioSetupError(
            "student_reference_unavailable",
            "The exact reviewed Core roster student is no longer available.",
        )
    student = resolution.student
    preferred_name = student.extra_fields.get("preferred_name", "").strip() or None
    current_snapshot = _student_snapshot(
        plan.request.student_reference,
        first_name=student.first_name,
        last_name=student.last_name,
        period=student.period,
        preferred_name=preferred_name,
    )
    if current_snapshot != plan.student:
        raise PortfolioSetupError(
            "roster_source_changed",
            "The reviewed Core roster student changed; review setup again.",
        )
    return student


def _revalidate_subject_plan(
    workspace_root: str | Path,
    plan: PortfolioSetupPlan,
) -> None:
    subject_id = plan.portfolio_subject_id
    if subject_id is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing its reviewed Portfolio Subject.",
        )
    resolution = resolve_subject_reference(
        workspace_root,
        plan.request.student_reference,
    )
    if plan.subject_action == "reuse_existing":
        if resolution.status != "resolved" or resolution.subject_ids != (subject_id,):
            raise PortfolioSetupError(
                "subject_identity_conflict",
                "The exact roster reference no longer resolves to the reviewed Subject.",
            )
        detail = show_subject(workspace_root, subject_id)
        if detail.summary.status != "active":
            raise PortfolioSetupError(
                "subject_historical",
                "The reviewed Portfolio Subject is no longer active.",
            )
        return

    if resolution.status != "unlinked":
        raise PortfolioSetupError(
            "subject_identity_conflict",
            "The exact roster reference is no longer unlinked.",
        )
    if plan.subject_action == "link_existing":
        detail = show_subject(workspace_root, subject_id)
        if detail.summary.status != "active":
            raise PortfolioSetupError(
                "subject_historical",
                "The reviewed Portfolio Subject is no longer active.",
            )


def _revalidate_profile_plan(
    workspace_root: str | Path,
    plan: PortfolioSetupPlan,
) -> None:
    reference = plan.request.profile_revision
    if reference is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing its exact Profile Revision.",
        )
    try:
        state, _ = load_profile_state(workspace_root)
    except ProfileWorkflowError as error:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Canonical Profile state is invalid.",
        ) from error
    revision = state.revision(reference)
    if revision is None:
        raise PortfolioSetupError(
            "profile_revision_not_found",
            "The reviewed exact Profile Revision no longer exists.",
        )
    if revision.purpose_kind != plan.request.purpose_kind:
        raise PortfolioSetupError(
            "profile_purpose_mismatch",
            "The reviewed exact Profile Revision no longer matches the chosen purpose.",
        )
    if not state.is_bindable(reference):
        raise PortfolioSetupError(
            "profile_not_bindable",
            "The reviewed exact Profile Revision is no longer bindable.",
        )
    expected_context = _effective_profile_context(
        plan.request.profile_context,
        plan.request.student_reference,
    )
    if expected_context != plan.effective_profile_context:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan Profile Binding context is inconsistent.",
        )
    try:
        validate_profile_applicability(
            revision,
            plan.effective_profile_context,
        )
    except ProfileWorkflowError as error:
        if error.code == "profile_not_applicable":
            raise PortfolioSetupError(
                "profile_not_applicable",
                "The reviewed exact Profile Revision is not applicable.",
            ) from error
        raise


def _identity_records_for_plan(
    plan: PortfolioSetupPlan,
    *,
    student: StudentRecord,
    now: datetime,
) -> tuple[VitrineRecord, ...]:
    if plan.subject_action == "reuse_existing":
        return ()
    context = plan.request.identity_context
    subject_id = plan.portfolio_subject_id
    link_id = plan.proposed_ids.subject_link_id
    if context is None or subject_id is None or link_id is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing reviewed Subject identity inputs.",
        )

    records: list[VitrineRecord] = []
    if plan.subject_action == "create_new":
        if plan.student is None:
            raise PortfolioSetupError(
                "setup_plan_invalid",
                "Setup plan is missing its reviewed student Snapshot.",
            )
        records.append(
            PortfolioSubject(
                portfolio_subject_id=subject_id,
                created_at=now,
                created_by=context.actor,
                display_name_snapshot=plan.student.display_name,
            )
        )

    link = PortfolioSubjectClassLink(
        subject_link_id=link_id,
        portfolio_subject_id=subject_id,
        student_reference=plan.request.student_reference,
        confirmed_at=now,
        confirmed_by=context.actor,
        confirmation_basis=subject_services._confirmation_basis(context),
        authority_reference=context.authority_source,
    )
    records.append(link)

    id_factory = _PlannedIdentityIdFactory(
        display_snapshot_id=plan.proposed_ids.display_snapshot_id,
        identity_decision_ids=plan.proposed_ids.identity_decision_ids,
    )
    snapshot = subject_services._display_snapshot(
        link=link,
        student=student,
        now=now,
        id_factory=id_factory,
    )
    records.append(snapshot)

    if plan.subject_action == "create_new":
        records.append(
            subject_services._decision(
                decision_type="create_subject",
                subject_ids=(subject_id,),
                link_ids=(),
                context=context,
                now=now,
                id_factory=id_factory,
            )
        )
    records.append(
        subject_services._decision(
            decision_type="confirm_link",
            subject_ids=(subject_id,),
            link_ids=(link_id,),
            context=context,
            now=now,
            id_factory=id_factory,
        )
    )
    return tuple(records)


def _created_record_ids(plan: PortfolioSetupPlan) -> tuple[str, ...]:
    result: list[str] = []
    if plan.subject_action == "create_new" and plan.portfolio_subject_id is not None:
        result.append(plan.portfolio_subject_id)
    if plan.subject_action in {"create_new", "link_existing"}:
        if plan.proposed_ids.subject_link_id is not None:
            result.append(plan.proposed_ids.subject_link_id)
        if plan.proposed_ids.display_snapshot_id is not None:
            result.append(plan.proposed_ids.display_snapshot_id)
        result.extend(plan.proposed_ids.identity_decision_ids)
    result.extend(
        (
            plan.proposed_ids.portfolio_id,
            plan.proposed_ids.profile_binding_id,
        )
    )
    return tuple(result)


def _validate_prospective_setup_state(
    current_records: tuple[VitrineRecord, ...],
    candidates: tuple[VitrineRecord, ...],
) -> None:
    try:
        current_keys = {key_for_record(item) for item in current_records}
        candidate_keys = tuple(key_for_record(item) for item in candidates)
    except ValueError as error:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan contains an invalid canonical record identity.",
        ) from error
    if len(set(candidate_keys)) != len(candidate_keys):
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan proposes duplicate canonical record identities.",
        )
    if any(item in current_keys for item in candidate_keys):
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan proposes a canonical identity that already exists.",
        )

    combined = (*current_records, *candidates)
    identity_issues = tuple(
        item
        for item in collect_identity_state_issues(project_identity_state(combined))
        if item.code != "identity.duplicate_active_association"
    )
    if identity_issues:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            f"Prospective Subject state is invalid ({identity_issues[0].code}).",
        )
    profile_issues = collect_profile_state_issues(project_profile_state(combined))
    if profile_issues:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            f"Prospective Profile state is invalid ({profile_issues[0].code}).",
        )


def create_portfolio_for_student(
    workspace_root: str | Path,
    plan: PortfolioSetupPlan,
    *,
    actor: ActorAttribution,
    binding_reason: str = "teacher_guided_setup",
    clock: SetupClock = _clock,
) -> PortfolioSetupResult:
    """Revalidate and atomically commit one exact reviewed setup plan."""
    _validate_plan_shape(plan)
    actual_revision = observe_state_revision(workspace_root)
    if actual_revision != plan.observed_state_revision:
        raise PortfolioSetupError(
            "state_conflict",
            f"Vitrine state changed: expected {plan.observed_state_revision!r}, "
            f"found {actual_revision!r}.",
        )

    student = _current_student_for_plan(workspace_root, plan)
    _revalidate_subject_plan(workspace_root, plan)
    _revalidate_profile_plan(workspace_root, plan)

    subject_id = plan.portfolio_subject_id
    profile_reference = plan.request.profile_revision
    if subject_id is None or profile_reference is None:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Setup plan is missing final Subject/Profile identities.",
        )

    now = clock()
    identity_records = _identity_records_for_plan(
        plan,
        student=student,
        now=now,
    )
    portfolio = Portfolio(
        portfolio_id=plan.proposed_ids.portfolio_id,
        portfolio_subject_id=subject_id,
        created_at=now,
        created_by=actor,
        title_snapshot=plan.request.title_snapshot,
        description_snapshot=plan.request.description_snapshot,
    )
    binding = PortfolioProfileBinding(
        profile_binding_id=plan.proposed_ids.profile_binding_id,
        portfolio_id=portfolio.portfolio_id,
        profile_revision=profile_reference,
        bound_at=now,
        bound_by=actor,
        binding_reason=binding_reason,
    )
    candidates: tuple[VitrineRecord, ...] = (
        *identity_records,
        portfolio,
        binding,
    )

    try:
        current_records = load_current_records(workspace_root)
    except VitrineStorageError as error:
        raise PortfolioSetupError(
            "setup_plan_invalid",
            "Canonical Vitrine state could not be loaded for final setup validation.",
        ) from error
    _validate_prospective_setup_state(current_records, candidates)

    try:
        commit = commit_record_batch(
            workspace_root,
            candidates,
            expected_state_revision=plan.observed_state_revision,
        )
    except VitrineStorageConflictError as error:
        raise PortfolioSetupError("state_conflict", str(error)) from error
    except VitrineStorageValidationError as error:
        raise PortfolioSetupError("setup_plan_invalid", str(error)) from error

    return PortfolioSetupResult(
        portfolio_subject_id=subject_id,
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile_reference,
        state_revision=commit.state_revision,
        subject_action=plan.subject_action or "",
        created_record_ids=_created_record_ids(plan),
    )


__all__ = [
    "CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION",
    "PORTFOLIO_SETUP_PURPOSES",
    "PORTFOLIO_SETUP_SUBJECT_ACTIONS",
    "CreatePortfolioForStudentRequest",
    "PortfolioSetupError",
    "PortfolioSetupExistingPortfolio",
    "PortfolioSetupLinkPreview",
    "PortfolioSetupPlan",
    "PortfolioSetupProfileChoice",
    "PortfolioSetupProposedIds",
    "PortfolioSetupResult",
    "PortfolioSetupSectionSummary",
    "PortfolioSetupStudentSnapshot",
    "PortfolioSetupSubjectResolution",
    "create_portfolio_for_student",
    "list_portfolio_setup_profiles",
    "plan_create_portfolio_for_student",
    "resolve_portfolio_setup_subject",
]
