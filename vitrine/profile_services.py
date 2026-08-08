"""Application services for immutable versioned Portfolio Profiles."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path

from vitrine.models import (
    ActorAttribution,
    PortfolioProfileBinding,
    PortfolioProfileComposition,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileMigration,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileAudienceRule,
    ProfileOverlayRequirement,
    ProfileOverlayRevisionRef,
    ProfileRequirementImpact,
    ProfileRevisionRef,
    ProfileSectionDefinition,
    VitrineRecord,
)
from vitrine.profile_state import (
    PortfolioProfileState,
    collect_profile_state_issues,
    project_profile_state,
    requirement_semantic_key,
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


class ProfileWorkflowError(ValueError):
    """Expected Profile application failure with stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ProfileBindingContext:
    as_of: date | None = None
    school_year: str | None = None
    institution_id: str | None = None
    program_id: str | None = None
    content_area: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileMutationResult:
    record_ids: tuple[str, ...]
    commit: VitrineStorageCommitResult | None


@dataclass(frozen=True, slots=True)
class ProfileRevisionSummary:
    reference: ProfileRevisionRef
    label: str
    purpose_kind: str
    lifecycle_status: str
    bindable: bool
    requirement_count: int


@dataclass(frozen=True, slots=True)
class ProfileMigrationAnalysis:
    portfolio_id: str
    predecessor_binding_id: str
    source_profile_revision: ProfileRevisionRef
    target_profile_revision: ProfileRevisionRef
    requirement_impact: ProfileRequirementImpact
    affected_section_ids: tuple[str, ...]
    potentially_affected_selection_count: int
    reapproval_requirement_ids: tuple[str, ...]
    unresolved_requirement_ids: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.unresolved_requirement_ids)


@dataclass(frozen=True, slots=True)
class ProfileCompositionResult:
    effective_revision: ProfileRevisionRef
    requirement_ids: tuple[str, ...]
    composition_id: str
    commit: VitrineStorageCommitResult


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _records_and_revision(workspace_root: str | Path) -> tuple[tuple[VitrineRecord, ...], int | None]:
    try:
        current = load_current_state(workspace_root)
    except VitrineStorageNotFoundError:
        return (), None
    return load_current_records(workspace_root), current.state_revision


def observe_profile_state_revision(workspace_root: str | Path) -> int | None:
    return _records_and_revision(workspace_root)[1]


def load_profile_state(workspace_root: str | Path) -> tuple[PortfolioProfileState, int | None]:
    records, revision = _records_and_revision(workspace_root)
    state = project_profile_state(records)
    issues = collect_profile_state_issues(state)
    if issues:
        raise ProfileWorkflowError("profile_state_invalid", f"Portfolio Profile state contains {len(issues)} issue(s).")
    return state, revision


def _require_expected(actual: int | None, expected: int | None) -> None:
    if actual != expected:
        raise ProfileWorkflowError("state_conflict", f"Vitrine state changed: expected {expected!r}, found {actual!r}.")


def _commit(workspace_root: str | Path, records: Iterable[VitrineRecord], *, expected_state_revision: int | None) -> VitrineStorageCommitResult:
    try:
        return commit_record_batch(workspace_root, records, expected_state_revision=expected_state_revision)
    except VitrineStorageConflictError as error:
        raise ProfileWorkflowError("state_conflict", str(error)) from error


def list_profile_families(workspace_root: str | Path) -> tuple[PortfolioProfileFamily, ...]:
    state, _ = load_profile_state(workspace_root)
    return tuple(sorted(state.families, key=lambda item: (item.purpose_kind, item.label.casefold(), item.profile_family_id)))


def list_profile_revisions(workspace_root: str | Path, *, portfolio_profile_id: str | None = None) -> tuple[ProfileRevisionSummary, ...]:
    state, _ = load_profile_state(workspace_root)
    revisions = state.revisions if portfolio_profile_id is None else tuple(item for item in state.revisions if item.portfolio_profile_id == portfolio_profile_id)
    return tuple(
        ProfileRevisionSummary(
            reference=item.reference,
            label=item.label,
            purpose_kind=item.purpose_kind,
            lifecycle_status=state.lifecycle_status(item.reference),
            bindable=state.is_bindable(item.reference),
            requirement_count=len(state.requirements_for(item.reference)),
        )
        for item in sorted(revisions, key=lambda item: (item.portfolio_profile_id, item.profile_revision))
    )


def get_profile_revision(workspace_root: str | Path, reference: ProfileRevisionRef) -> PortfolioProfileRevision:
    state, _ = load_profile_state(workspace_root)
    revision = state.revision(reference)
    if revision is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Exact Portfolio Profile Revision does not exist.")
    return revision


def get_profile_requirements(workspace_root: str | Path, reference: ProfileRevisionRef) -> tuple[PortfolioProfileRequirement, ...]:
    state, _ = load_profile_state(workspace_root)
    if state.revision(reference) is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Exact Portfolio Profile Revision does not exist.")
    return state.requirements_for(reference)


def list_bindable_profile_revisions(workspace_root: str | Path, *, purpose_kind: str | None = None) -> tuple[ProfileRevisionSummary, ...]:
    return tuple(item for item in list_profile_revisions(workspace_root) if item.bindable and (purpose_kind is None or item.purpose_kind == purpose_kind))


def get_portfolio_profile_binding(workspace_root: str | Path, portfolio_id: str) -> PortfolioProfileBinding | None:
    state, _ = load_profile_state(workspace_root)
    heads = state.active_binding_heads(portfolio_id)
    if len(heads) > 1:
        raise ProfileWorkflowError("profile_binding_conflict", "Portfolio has multiple unresolved Profile Binding heads.")
    return heads[0] if heads else None


def get_profile_migration_history(workspace_root: str | Path, portfolio_id: str) -> tuple[PortfolioProfileMigration, ...]:
    state, _ = load_profile_state(workspace_root)
    return tuple(sorted((item for item in state.migrations if item.portfolio_id == portfolio_id), key=lambda item: (item.migrated_at, item.profile_migration_id)))


def create_profile_family(workspace_root: str | Path, family: PortfolioProfileFamily, *, expected_state_revision: int | None) -> ProfileMutationResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    existing = next((item for item in state.families if item.profile_family_id == family.profile_family_id), None)
    if existing is not None:
        if existing == family:
            return ProfileMutationResult((family.profile_family_id,), None)
        raise ProfileWorkflowError("profile_family_conflict", "Profile Family identity already exists with different content.")
    commit = _commit(workspace_root, (family,), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((family.profile_family_id,), commit)


def create_profile_revision(
    workspace_root: str | Path,
    revision: PortfolioProfileRevision,
    requirements: Sequence[PortfolioProfileRequirement],
    *,
    expected_state_revision: int | None,
) -> ProfileMutationResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    if revision.purpose_kind not in {"improvement", "showcase"}:
        raise ProfileWorkflowError("profile_purpose_unsupported", "#31 operational services support improvement and showcase Profile purposes only.")
    if revision.profile_family_id is not None and not any(item.profile_family_id == revision.profile_family_id for item in state.families):
        raise ProfileWorkflowError("profile_family_not_found", "Profile Family does not exist.")
    if revision.predecessor_revision is not None and state.revision(ProfileRevisionRef(portfolio_profile_id=revision.portfolio_profile_id, profile_revision=revision.predecessor_revision)) is None:
        raise ProfileWorkflowError("profile_predecessor_invalid", "Exact predecessor Profile Revision does not exist.")
    if not requirements:
        raise ProfileWorkflowError("profile_incomplete", "Operational Profile Revision requires at least one explicit requirement.")
    normalized = tuple(requirements)
    for requirement in normalized:
        if requirement.profile_reference != revision.reference:
            raise ProfileWorkflowError("profile_requirement_revision_mismatch", "Every requirement must identify the exact Profile Revision being created.")
    if len({item.requirement_id for item in normalized}) != len(normalized):
        raise ProfileWorkflowError("duplicate_requirement_id", "Requirement IDs must be unique within the Profile Revision.")
    candidate_state = project_profile_state((*_records_and_revision(workspace_root)[0], revision, *normalized))
    issues = collect_profile_state_issues(candidate_state)
    if issues:
        first = issues[0]
        raise ProfileWorkflowError(first.code.replace(".", "_"), first.message)
    commit = _commit(workspace_root, (revision, *normalized), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((f"{revision.portfolio_profile_id}:{revision.profile_revision}", *(item.requirement_id for item in normalized)), commit)


def _lifecycle_head(state: PortfolioProfileState, reference: ProfileRevisionRef) -> PortfolioProfileLifecycleEvent | None:
    heads = state.lifecycle_heads(reference)
    if len(heads) > 1:
        raise ProfileWorkflowError("profile_lifecycle_conflict", "Profile Revision has multiple unresolved lifecycle heads.")
    return heads[0] if heads else None


def activate_profile_revision(
    workspace_root: str | Path,
    reference: ProfileRevisionRef,
    *,
    actor: ActorAttribution,
    reason: str,
    authority_reference: str | None,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> ProfileMutationResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    revision = state.revision(reference)
    if revision is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Exact Portfolio Profile Revision does not exist.")
    if revision.purpose_kind not in {"improvement", "showcase"}:
        raise ProfileWorkflowError("profile_purpose_unsupported", "#31 may activate improvement and showcase Profile purposes only.")
    if not state.requirements_for(reference):
        raise ProfileWorkflowError("profile_incomplete", "Profile Revision has no explicit operational requirements.")
    head = _lifecycle_head(state, reference)
    if head is not None:
        if head.event_kind == "activated":
            return ProfileMutationResult((head.profile_lifecycle_event_id,), None)
        raise ProfileWorkflowError(f"profile_{head.event_kind}", f"Profile Revision lifecycle head is {head.event_kind}; activation is not implicit.")
    now = clock()
    event = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id=id_factory("profile_event"),
        profile_revision=reference,
        event_kind="activated",
        event_at=now,
        effective_at=now,
        actor=actor,
        reason=reason,
        authority_reference=authority_reference,
    )
    commit = _commit(workspace_root, (event,), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((event.profile_lifecycle_event_id,), commit)


def transition_profile_lifecycle(
    workspace_root: str | Path,
    reference: ProfileRevisionRef,
    event_kind: str,
    *,
    actor: ActorAttribution,
    reason: str,
    authority_reference: str | None,
    successor_revision: ProfileRevisionRef | None = None,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> ProfileMutationResult:
    if event_kind not in {"deprecated", "superseded", "withdrawn", "retired"}:
        raise ProfileWorkflowError("profile_lifecycle_invalid", "Unsupported lifecycle transition.")
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    if state.revision(reference) is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Exact Portfolio Profile Revision does not exist.")
    head = _lifecycle_head(state, reference)
    if head is None:
        raise ProfileWorkflowError(
            "profile_inactive",
            "Profile Revision must be activated before a lifecycle transition.",
        )
    if head.event_kind == "deprecated" and event_kind == "deprecated":
        return ProfileMutationResult((head.profile_lifecycle_event_id,), None)
    if head.event_kind not in {"activated", "deprecated"}:
        raise ProfileWorkflowError(
            f"profile_{head.event_kind}",
            "Profile Revision already has a terminal lifecycle head.",
        )
    if event_kind == "superseded":
        if successor_revision is None or state.revision(successor_revision) is None:
            raise ProfileWorkflowError("profile_revision_not_found", "Supersession requires an existing exact successor Revision.")
    elif successor_revision is not None:
        raise ProfileWorkflowError("profile_lifecycle_invalid", "Only supersession accepts successor_revision.")
    now = clock()
    event = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id=id_factory("profile_event"),
        profile_revision=reference,
        event_kind=event_kind,
        event_at=now,
        effective_at=now,
        actor=actor,
        reason=reason,
        predecessor_event_id=head.profile_lifecycle_event_id,
        successor_revision=successor_revision,
        authority_reference=authority_reference,
    )
    commit = _commit(workspace_root, (event,), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((event.profile_lifecycle_event_id,), commit)


def _check_applicability(revision: PortfolioProfileRevision, context: ProfileBindingContext) -> None:
    applicability = revision.applicability
    if applicability.school_years and context.school_year not in applicability.school_years:
        raise ProfileWorkflowError("profile_not_applicable", "Binding context school year does not match Profile applicability.")
    if applicability.institution_id is not None and context.institution_id != applicability.institution_id:
        raise ProfileWorkflowError("profile_not_applicable", "Binding context institution does not match Profile applicability.")
    if applicability.program_id is not None and context.program_id != applicability.program_id:
        raise ProfileWorkflowError("profile_not_applicable", "Binding context program does not match Profile applicability.")
    if applicability.content_areas and context.content_area not in applicability.content_areas:
        raise ProfileWorkflowError("profile_not_applicable", "Binding context content area does not match Profile applicability.")
    if applicability.effective_from is not None:
        if context.as_of is None or context.as_of < applicability.effective_from:
            raise ProfileWorkflowError("profile_not_applicable", "Binding context is before Profile effective date or lacks an as-of date.")
    if applicability.effective_through is not None:
        if context.as_of is None or context.as_of > applicability.effective_through:
            raise ProfileWorkflowError("profile_not_applicable", "Binding context is after Profile effective date or lacks an as-of date.")


def bind_portfolio_profile(
    workspace_root: str | Path,
    portfolio_id: str,
    reference: ProfileRevisionRef,
    *,
    actor: ActorAttribution,
    binding_reason: str,
    context: ProfileBindingContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> ProfileMutationResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    if not any(item.portfolio_id == portfolio_id for item in state.portfolios):
        raise ProfileWorkflowError("portfolio_not_found", "Portfolio does not exist.")
    revision = state.revision(reference)
    if revision is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Exact Portfolio Profile Revision does not exist.")
    if not state.is_bindable(reference):
        status = state.lifecycle_status(reference)
        raise ProfileWorkflowError(f"profile_{status}", f"Profile Revision is not bindable: lifecycle status is {status}.")
    _check_applicability(revision, context)
    heads = state.active_binding_heads(portfolio_id)
    if heads:
        if len(heads) > 1:
            raise ProfileWorkflowError("profile_binding_conflict", "Portfolio has multiple unresolved Profile Binding heads.")
        if heads[0].profile_revision == reference:
            return ProfileMutationResult((heads[0].profile_binding_id,), None)
        raise ProfileWorkflowError("profile_already_bound", "Portfolio already has an active Profile Binding; migrate explicitly.")
    binding = PortfolioProfileBinding(
        profile_binding_id=id_factory("profile_binding"),
        portfolio_id=portfolio_id,
        profile_revision=reference,
        bound_at=clock(),
        bound_by=actor,
        binding_reason=binding_reason,
    )
    commit = _commit(workspace_root, (binding,), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((binding.profile_binding_id,), commit)


def compare_profile_requirements(source: Sequence[PortfolioProfileRequirement], target: Sequence[PortfolioProfileRequirement]) -> ProfileRequirementImpact:
    old = {item.requirement_id: item for item in source}
    new = {item.requirement_id: item for item in target}
    unchanged: list[str] = []
    materially_changed: list[str] = []
    for requirement_id in sorted(set(old) & set(new)):
        if requirement_semantic_key(old[requirement_id]) == requirement_semantic_key(new[requirement_id]):
            unchanged.append(requirement_id)
        else:
            materially_changed.append(requirement_id)
    replacement_candidates = {
        item.requirement_id
        for item in target
        if item.replaces_requirement_id is not None and item.requirement_id not in old
    }
    replaced = sorted(
        item.requirement_id
        for item in target
        if item.requirement_id in replacement_candidates
        and item.replaces_requirement_id in old
    )
    replaced_old = {
        item.replaces_requirement_id
        for item in target
        if item.requirement_id in replaced and item.replaces_requirement_id is not None
    }
    unresolved = sorted(replacement_candidates - set(replaced))
    added = sorted(set(new) - set(old) - replacement_candidates)
    removed = sorted(set(old) - set(new) - replaced_old)
    return ProfileRequirementImpact(
        unchanged=tuple(unchanged),
        added=tuple(added),
        removed=tuple(removed),
        replaced=tuple(replaced),
        materially_changed=tuple(materially_changed),
        unresolved_mapping=tuple(unresolved),
    )


def analyze_profile_migration(workspace_root: str | Path, portfolio_id: str, target: ProfileRevisionRef, *, context: ProfileBindingContext) -> ProfileMigrationAnalysis:
    records, _ = _records_and_revision(workspace_root)
    state = project_profile_state(records)
    issues = collect_profile_state_issues(state)
    if issues:
        raise ProfileWorkflowError("profile_state_invalid", "Portfolio Profile state is invalid.")
    heads = state.active_binding_heads(portfolio_id)
    if len(heads) != 1:
        code = "profile_binding_not_found" if not heads else "profile_binding_conflict"
        raise ProfileWorkflowError(code, "Portfolio must have exactly one active Profile Binding before migration.")
    current = heads[0]
    target_revision = state.revision(target)
    if target_revision is None:
        raise ProfileWorkflowError("profile_revision_not_found", "Target Profile Revision does not exist.")
    if not state.is_bindable(target):
        raise ProfileWorkflowError("profile_inactive", "Target Profile Revision is not explicitly bindable.")
    _check_applicability(target_revision, context)
    source_requirements = state.requirements_for(current.profile_revision)
    target_requirements = state.requirements_for(target)
    impact = compare_profile_requirements(source_requirements, target_requirements)
    unresolved = tuple(sorted((*impact.materially_changed, *impact.unresolved_mapping)))
    changed_ids = set((*impact.added, *impact.removed, *impact.replaced, *impact.materially_changed, *impact.unresolved_mapping))
    affected_sections = tuple(sorted({item.scope_reference for item in (*source_requirements, *target_requirements) if item.requirement_id in changed_ids and item.scope_kind == "section" and item.scope_reference is not None}))
    reapproval = tuple(sorted(item.requirement_id for item in target_requirements if item.requirement_kind == "approval" and item.requirement_id in changed_ids))
    selection_count = sum(1 for item in records if getattr(item, "record_type", None) == "portfolio_selection" and getattr(item, "portfolio_id", None) == portfolio_id and getattr(item, "profile_binding_id", None) == current.profile_binding_id)
    return ProfileMigrationAnalysis(
        portfolio_id=portfolio_id,
        predecessor_binding_id=current.profile_binding_id,
        source_profile_revision=current.profile_revision,
        target_profile_revision=target,
        requirement_impact=impact,
        affected_section_ids=affected_sections,
        potentially_affected_selection_count=selection_count,
        reapproval_requirement_ids=reapproval,
        unresolved_requirement_ids=unresolved,
    )


def migrate_portfolio_profile(
    workspace_root: str | Path,
    portfolio_id: str,
    target: ProfileRevisionRef,
    *,
    actor: ActorAttribution,
    migration_reason: str,
    authority_reference: str,
    context: ProfileBindingContext,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> tuple[ProfileMigrationAnalysis, ProfileMutationResult]:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    analysis = analyze_profile_migration(workspace_root, portfolio_id, target, context=context)
    if analysis.blocked:
        raise ProfileWorkflowError("profile_migration_blocked", "Migration contains materially changed or unresolved requirement mappings.")
    predecessor = next(
        item
        for item in state.bindings
        if item.profile_binding_id == analysis.predecessor_binding_id
    )
    if predecessor.profile_revision == target:
        return analysis, ProfileMutationResult((predecessor.profile_binding_id,), None)
    now = clock()
    successor = PortfolioProfileBinding(
        profile_binding_id=id_factory("profile_binding"),
        portfolio_id=portfolio_id,
        profile_revision=target,
        bound_at=now,
        bound_by=actor,
        binding_reason=migration_reason,
        predecessor_binding_id=predecessor.profile_binding_id,
    )
    migration = PortfolioProfileMigration(
        profile_migration_id=id_factory("profile_migration"),
        portfolio_id=portfolio_id,
        predecessor_binding_id=predecessor.profile_binding_id,
        successor_binding_id=successor.profile_binding_id,
        source_profile_revision=predecessor.profile_revision,
        target_profile_revision=target,
        requirement_impact=analysis.requirement_impact,
        unresolved_requirement_ids=analysis.unresolved_requirement_ids,
        reapproval_requirement_ids=analysis.reapproval_requirement_ids,
        migrated_at=now,
        migrated_by=actor,
        migration_reason=migration_reason,
        authority_reference=authority_reference,
    )
    commit = _commit(workspace_root, (successor, migration), expected_state_revision=expected_state_revision)
    return analysis, ProfileMutationResult((successor.profile_binding_id, migration.profile_migration_id), commit)


def create_profile_overlay(workspace_root: str | Path, overlay: PortfolioProfileOverlayRevision, *, expected_state_revision: int | None) -> ProfileMutationResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    for component in overlay.component_revisions:
        component_revision = state.revision(component)
        if component_revision is None:
            raise ProfileWorkflowError("profile_revision_not_found", "Overlay component Profile Revision does not exist.")
        if component_revision.purpose_kind != overlay.purpose_kind:
            raise ProfileWorkflowError("profile_composition_conflict", "Overlay purpose must match every exact component Revision.")
    if overlay.predecessor_overlay_revision is not None and not any(item.overlay_id == overlay.overlay_id and item.overlay_revision == overlay.predecessor_overlay_revision for item in state.overlays):
        raise ProfileWorkflowError("overlay_predecessor_invalid", "Overlay predecessor Revision does not exist.")
    commit = _commit(workspace_root, (overlay,), expected_state_revision=expected_state_revision)
    return ProfileMutationResult((f"{overlay.overlay_id}:{overlay.overlay_revision}",), commit)


def _overlay_to_requirement(item: ProfileOverlayRequirement, reference: ProfileRevisionRef) -> PortfolioProfileRequirement:
    return PortfolioProfileRequirement(
        portfolio_profile_id=reference.portfolio_profile_id,
        profile_revision=reference.profile_revision,
        requirement_id=item.requirement_id,
        requirement_kind=item.requirement_kind,
        obligation=item.obligation,
        title=item.title,
        statement=item.statement,
        scope_kind=item.scope_kind,
        satisfaction_class=item.satisfaction_class,
        authority_references=item.authority_references,
        scope_reference=item.scope_reference,
        replaces_requirement_id=item.replaces_requirement_id,
    )


def _weakened(old: PortfolioProfileRequirement, new: ProfileOverlayRequirement) -> bool:
    if old.obligation == "required" and new.obligation != "required":
        return True
    if old.obligation == "prohibited" and new.obligation != "prohibited":
        return True
    return False


def compose_profile_revision(
    workspace_root: str | Path,
    effective_revision: PortfolioProfileRevision,
    component_revisions: Sequence[ProfileRevisionRef],
    overlay_revisions: Sequence[ProfileOverlayRevisionRef],
    *,
    actor: ActorAttribution,
    authority_reference: str,
    expected_state_revision: int | None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> ProfileCompositionResult:
    state, actual = load_profile_state(workspace_root)
    _require_expected(actual, expected_state_revision)
    if not component_revisions:
        raise ProfileWorkflowError("profile_composition_conflict", "Composition requires at least one exact component Revision.")
    merged_requirements: dict[str, PortfolioProfileRequirement] = {}
    sections: dict[str, ProfileSectionDefinition] = {}
    audiences: dict[str, ProfileAudienceRule] = {}
    for component_reference in component_revisions:
        revision = state.revision(component_reference)
        if revision is None:
            raise ProfileWorkflowError("profile_revision_not_found", "Composition component Profile Revision does not exist.")
        if state.lifecycle_status(component_reference) not in {"activated", "deprecated"}:
            raise ProfileWorkflowError("profile_inactive", "Composition component must be explicitly activated or deprecated.")
        if revision.purpose_kind != effective_revision.purpose_kind:
            raise ProfileWorkflowError("profile_composition_conflict", "Composition components must agree with effective purpose_kind.")
        for requirement in state.requirements_for(component_reference):
            existing_requirement = merged_requirements.get(requirement.requirement_id)
            if existing_requirement is not None and requirement_semantic_key(existing_requirement) != requirement_semantic_key(requirement):
                raise ProfileWorkflowError("profile_composition_conflict", f"Component requirement conflict: {requirement.requirement_id}.")
            merged_requirements[requirement.requirement_id] = requirement
        for section in revision.sections:
            existing_section = sections.get(section.section_id)
            if existing_section is not None and existing_section != section:
                raise ProfileWorkflowError("profile_composition_conflict", f"Component section conflict: {section.section_id}.")
            sections[section.section_id] = section
        for audience in revision.audience_rules:
            existing_audience = audiences.get(audience.audience_rule_id)
            if existing_audience is not None and existing_audience != audience:
                raise ProfileWorkflowError("profile_composition_conflict", f"Component audience conflict: {audience.audience_rule_id}.")
            audiences[audience.audience_rule_id] = audience
    for overlay_reference in overlay_revisions:
        overlay = next((item for item in state.overlays if item.overlay_id == overlay_reference.overlay_id and item.overlay_revision == overlay_reference.overlay_revision), None)
        if overlay is None:
            raise ProfileWorkflowError("overlay_not_found", "Exact Overlay Revision does not exist.")
        if overlay.purpose_kind != effective_revision.purpose_kind:
            raise ProfileWorkflowError("profile_composition_conflict", "Overlay purpose does not match the effective Profile purpose.")
        if not set(overlay.component_revisions).issubset(set(component_revisions)):
            raise ProfileWorkflowError("profile_composition_conflict", "Overlay was authored against component Revisions not present in this composition.")
        for change in overlay.requirement_changes:
            item = change.requirement
            if change.action == "add":
                if item.requirement_id in merged_requirements:
                    raise ProfileWorkflowError("profile_composition_conflict", f"Overlay addition collides with requirement: {item.requirement_id}.")
                merged_requirements[item.requirement_id] = _overlay_to_requirement(item, effective_revision.reference)
            else:
                target_id = item.replaces_requirement_id
                if target_id is None or target_id not in merged_requirements:
                    raise ProfileWorkflowError("profile_composition_conflict", f"Overlay replacement target is missing for {item.requirement_id}.")
                old = merged_requirements[target_id]
                if overlay.authority_reference not in old.authority_references:
                    raise ProfileWorkflowError("profile_composition_conflict", f"Overlay authority is not explicitly permitted to replace requirement: {target_id}.")
                if _weakened(old, item):
                    raise ProfileWorkflowError("profile_composition_conflict", f"Overlay replacement weakens controlling requirement: {target_id}.")
                if item.requirement_id != target_id and item.requirement_id in merged_requirements:
                    raise ProfileWorkflowError("profile_composition_conflict", f"Overlay replacement collides with requirement: {item.requirement_id}.")
                del merged_requirements[target_id]
                merged_requirements[item.requirement_id] = _overlay_to_requirement(item, effective_revision.reference)
        for section in overlay.section_additions:
            if section.section_id in sections:
                raise ProfileWorkflowError("profile_composition_conflict", f"Overlay section addition collides with section: {section.section_id}.")
            sections[section.section_id] = section
        for audience in overlay.audience_rule_additions:
            if audience.audience_rule_id in audiences:
                raise ProfileWorkflowError("profile_composition_conflict", f"Overlay audience addition collides with audience: {audience.audience_rule_id}.")
            audiences[audience.audience_rule_id] = audience
    expected_sections = tuple(sorted(sections.values(), key=lambda item: item.order))
    expected_audiences = tuple(
        sorted(audiences.values(), key=lambda item: item.audience_rule_id)
    )
    if effective_revision.sections != expected_sections or effective_revision.audience_rules != expected_audiences:
        raise ProfileWorkflowError("profile_composition_conflict", "Effective Revision must contain the fully flattened component and overlay sections/audience rules.")
    effective_requirements = tuple(
        replace(item, portfolio_profile_id=effective_revision.portfolio_profile_id, profile_revision=effective_revision.profile_revision)
        for item in sorted(merged_requirements.values(), key=lambda item: item.requirement_id)
    )
    composition = PortfolioProfileComposition(
        profile_composition_id=id_factory("profile_composition"),
        effective_profile_revision=effective_revision.reference,
        component_profile_revisions=tuple(component_revisions),
        overlay_revisions=tuple(overlay_revisions),
        composed_at=clock(),
        composed_by=actor,
        authority_reference=authority_reference,
    )
    candidate_records: tuple[VitrineRecord, ...] = (
        effective_revision,
        *effective_requirements,
        composition,
    )
    candidate_state = project_profile_state((*_records_and_revision(workspace_root)[0], *candidate_records))
    issues = collect_profile_state_issues(candidate_state)
    if issues:
        first = issues[0]
        raise ProfileWorkflowError(first.code.replace(".", "_"), first.message)
    commit = _commit(workspace_root, candidate_records, expected_state_revision=expected_state_revision)
    return ProfileCompositionResult(effective_revision.reference, tuple(item.requirement_id for item in effective_requirements), composition.profile_composition_id, commit)


__all__ = [
    "ProfileBindingContext",
    "ProfileCompositionResult",
    "ProfileMigrationAnalysis",
    "ProfileMutationResult",
    "ProfileRevisionSummary",
    "ProfileWorkflowError",
    "activate_profile_revision",
    "analyze_profile_migration",
    "bind_portfolio_profile",
    "compare_profile_requirements",
    "compose_profile_revision",
    "create_profile_family",
    "create_profile_overlay",
    "create_profile_revision",
    "get_portfolio_profile_binding",
    "get_profile_migration_history",
    "get_profile_requirements",
    "get_profile_revision",
    "list_bindable_profile_revisions",
    "list_profile_families",
    "list_profile_revisions",
    "load_profile_state",
    "migrate_portfolio_profile",
    "observe_profile_state_revision",
    "transition_profile_lifecycle",
]
