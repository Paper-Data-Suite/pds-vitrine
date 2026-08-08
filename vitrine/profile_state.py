"""Pure projection and validation for canonical Portfolio Profile policy history."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from vitrine.models import (
    Portfolio,
    PortfolioProfileBinding,
    PortfolioProfileComposition,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileMigration,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileRevisionRef,
    ValidationIssue,
    VitrineProfileStateError,
    VitrineRecord,
)


def _issue(code: str, message: str, record_type: str | None = None, record_id: str | None = None) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, record_type=record_type, record_id=record_id)


def _revision_key(value: PortfolioProfileRevision | ProfileRevisionRef) -> tuple[str, int]:
    return (value.portfolio_profile_id, value.profile_revision)


def requirement_semantic_key(value: PortfolioProfileRequirement) -> tuple[object, ...]:
    """Return policy-bearing fields used for stable requirement continuity."""
    return (
        value.requirement_kind,
        value.obligation,
        value.statement,
        value.scope_kind,
        value.scope_reference,
        value.satisfaction_class,
        value.authority_references,
    )


def _cycle_representatives(
    predecessors: dict[str, str | None],
) -> tuple[str, ...]:
    """Return one deterministic representative for each predecessor cycle."""
    representatives: set[str] = set()
    for start in sorted(predecessors):
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start
        while current is not None and current in predecessors:
            if current in positions:
                cycle = path[positions[current] :]
                representatives.add(min(cycle))
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessors[current]
    return tuple(sorted(representatives))


@dataclass(frozen=True, slots=True)
class PortfolioProfileState:
    portfolios: tuple[Portfolio, ...]
    families: tuple[PortfolioProfileFamily, ...]
    revisions: tuple[PortfolioProfileRevision, ...]
    bindings: tuple[PortfolioProfileBinding, ...]
    requirements: tuple[PortfolioProfileRequirement, ...]
    lifecycle_events: tuple[PortfolioProfileLifecycleEvent, ...]
    overlays: tuple[PortfolioProfileOverlayRevision, ...]
    compositions: tuple[PortfolioProfileComposition, ...]
    migrations: tuple[PortfolioProfileMigration, ...]

    def revision(self, reference: ProfileRevisionRef) -> PortfolioProfileRevision | None:
        key = _revision_key(reference)
        return next((item for item in self.revisions if _revision_key(item) == key), None)

    def requirements_for(self, reference: ProfileRevisionRef) -> tuple[PortfolioProfileRequirement, ...]:
        key = _revision_key(reference)
        return tuple(sorted((item for item in self.requirements if (item.portfolio_profile_id, item.profile_revision) == key), key=lambda item: item.requirement_id))

    def lifecycle_heads(self, reference: ProfileRevisionRef) -> tuple[PortfolioProfileLifecycleEvent, ...]:
        events = tuple(item for item in self.lifecycle_events if item.profile_revision == reference)
        predecessor_ids = {item.predecessor_event_id for item in events if item.predecessor_event_id is not None}
        return tuple(sorted((item for item in events if item.profile_lifecycle_event_id not in predecessor_ids), key=lambda item: item.profile_lifecycle_event_id))

    def lifecycle_status(self, reference: ProfileRevisionRef) -> str:
        heads = self.lifecycle_heads(reference)
        if not heads:
            return "inactive"
        if len(heads) != 1:
            return "conflict"
        return heads[0].event_kind

    def is_bindable(self, reference: ProfileRevisionRef) -> bool:
        return self.revision(reference) is not None and self.lifecycle_status(reference) == "activated"

    def active_binding_heads(self, portfolio_id: str) -> tuple[PortfolioProfileBinding, ...]:
        items = tuple(item for item in self.bindings if item.portfolio_id == portfolio_id)
        predecessor_ids = {item.predecessor_binding_id for item in items if item.predecessor_binding_id is not None}
        return tuple(sorted((item for item in items if item.profile_binding_id not in predecessor_ids), key=lambda item: item.profile_binding_id))

    def active_binding(self, portfolio_id: str) -> PortfolioProfileBinding | None:
        heads = self.active_binding_heads(portfolio_id)
        return heads[0] if len(heads) == 1 else None


def project_profile_state(records: Iterable[VitrineRecord]) -> PortfolioProfileState:
    values = tuple(records)
    return PortfolioProfileState(
        portfolios=tuple(item for item in values if isinstance(item, Portfolio)),
        families=tuple(item for item in values if isinstance(item, PortfolioProfileFamily)),
        revisions=tuple(item for item in values if isinstance(item, PortfolioProfileRevision)),
        bindings=tuple(item for item in values if isinstance(item, PortfolioProfileBinding)),
        requirements=tuple(item for item in values if isinstance(item, PortfolioProfileRequirement)),
        lifecycle_events=tuple(item for item in values if isinstance(item, PortfolioProfileLifecycleEvent)),
        overlays=tuple(item for item in values if isinstance(item, PortfolioProfileOverlayRevision)),
        compositions=tuple(item for item in values if isinstance(item, PortfolioProfileComposition)),
        migrations=tuple(item for item in values if isinstance(item, PortfolioProfileMigration)),
    )


def collect_profile_state_issues(state: PortfolioProfileState) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    families = {item.profile_family_id: item for item in state.families}
    revisions = {_revision_key(item): item for item in state.revisions}
    portfolios = {item.portfolio_id: item for item in state.portfolios}
    bindings = {item.profile_binding_id: item for item in state.bindings}
    overlays = {(item.overlay_id, item.overlay_revision): item for item in state.overlays}

    # Revision/family/predecessor integrity and no ambiguous branch.
    revision_successors: dict[tuple[str, int], list[tuple[str, int]]] = defaultdict(list)
    for revision in state.revisions:
        key = _revision_key(revision)
        if revision.profile_family_id is not None:
            family = families.get(revision.profile_family_id)
            if family is None:
                issues.append(_issue("profile.family_missing", "Profile Family does not exist.", revision.record_type, f"{key[0]}:{key[1]}"))
            elif family.purpose_kind != revision.purpose_kind:
                issues.append(_issue("profile.family_purpose_mismatch", "Profile Family purpose does not match Profile Revision purpose.", revision.record_type, f"{key[0]}:{key[1]}"))
        if revision.predecessor_revision is not None:
            predecessor_key = (revision.portfolio_profile_id, revision.predecessor_revision)
            predecessor_revision = revisions.get(predecessor_key)
            if predecessor_revision is None:
                issues.append(_issue("profile.predecessor_missing", "Profile predecessor Revision does not exist.", revision.record_type, f"{key[0]}:{key[1]}"))
            else:
                if (
                    predecessor_revision.profile_family_id != revision.profile_family_id
                    or predecessor_revision.purpose_kind != revision.purpose_kind
                ):
                    issues.append(_issue("profile.predecessor_series_mismatch", "Profile successor changed Family or purpose within one series.", revision.record_type, f"{key[0]}:{key[1]}"))
                revision_successors[predecessor_key].append(key)
    for revision_predecessor_key, revision_successor_keys in revision_successors.items():
        if len(revision_successor_keys) > 1:
            issues.append(_issue("profile.revision_branch", "One Profile Revision has more than one direct successor.", "portfolio_profile_revision", f"{revision_predecessor_key[0]}:{revision_predecessor_key[1]}"))

    # Requirements reference exact revisions and exact scope identities.
    req_by_revision: dict[tuple[str, int], dict[str, PortfolioProfileRequirement]] = defaultdict(dict)
    for requirement in state.requirements:
        key = (requirement.portfolio_profile_id, requirement.profile_revision)
        requirement_revision = revisions.get(key)
        if requirement_revision is None:
            issues.append(_issue("profile.requirement_revision_missing", "Requirement Profile Revision does not exist.", requirement.record_type, requirement.requirement_id))
            continue
        req_by_revision[key][requirement.requirement_id] = requirement
        if requirement.scope_kind == "section" and requirement.scope_reference is not None:
            if requirement.scope_reference not in {item.section_id for item in requirement_revision.sections}:
                issues.append(_issue("profile.requirement_scope_invalid", "Requirement section scope does not resolve in the exact Revision.", requirement.record_type, requirement.requirement_id))
        if requirement.scope_kind == "audience" and requirement.scope_reference is not None:
            if requirement.scope_reference not in {item.audience_rule_id for item in requirement_revision.audience_rules}:
                issues.append(_issue("profile.requirement_scope_invalid", "Requirement audience scope does not resolve in the exact Revision.", requirement.record_type, requirement.requirement_id))

    # Stable identity and explicit replacement across direct predecessors.
    for revision in state.revisions:
        if revision.predecessor_revision is None:
            continue
        current_key = _revision_key(revision)
        previous_key = (revision.portfolio_profile_id, revision.predecessor_revision)
        current = req_by_revision.get(current_key, {})
        previous = req_by_revision.get(previous_key, {})
        for requirement_id in sorted(set(current) & set(previous)):
            if requirement_semantic_key(current[requirement_id]) != requirement_semantic_key(previous[requirement_id]):
                issues.append(_issue("profile.requirement_identity_conflict", "Materially changed requirement reused a stable requirement_id.", current[requirement_id].record_type, requirement_id))
        for item in current.values():
            if item.replaces_requirement_id is None:
                continue
            target = item.replaces_requirement_id
            if target not in previous:
                issues.append(_issue("profile.requirement_replacement_invalid", "Replacement target does not exist in the direct predecessor Revision.", item.record_type, item.requirement_id))
            elif target in current:
                issues.append(_issue("profile.requirement_replacement_invalid", "Replacement target remains present in the successor Revision.", item.record_type, item.requirement_id))

    # Lifecycle history is explicit and single-headed per exact Revision.
    events = {item.profile_lifecycle_event_id: item for item in state.lifecycle_events}
    event_successors: dict[str, list[str]] = defaultdict(list)
    for event in state.lifecycle_events:
        if _revision_key(event.profile_revision) not in revisions:
            issues.append(_issue("profile.lifecycle_revision_missing", "Lifecycle event Profile Revision does not exist.", event.record_type, event.profile_lifecycle_event_id))
        if event.predecessor_event_id is not None:
            lifecycle_predecessor = events.get(event.predecessor_event_id)
            if lifecycle_predecessor is None:
                issues.append(_issue("profile.lifecycle_predecessor_missing", "Lifecycle predecessor event does not exist.", event.record_type, event.profile_lifecycle_event_id))
            elif lifecycle_predecessor.profile_revision != event.profile_revision:
                issues.append(_issue("profile.lifecycle_predecessor_mismatch", "Lifecycle predecessor belongs to another Profile Revision.", event.record_type, event.profile_lifecycle_event_id))
            event_successors[event.predecessor_event_id].append(event.profile_lifecycle_event_id)
        if event.event_kind == "superseded":
            if event.successor_revision is None or _revision_key(event.successor_revision) not in revisions:
                issues.append(_issue("profile.lifecycle_successor_missing", "Superseded lifecycle event requires an existing exact successor Revision.", event.record_type, event.profile_lifecycle_event_id))
        elif event.successor_revision is not None:
            issues.append(_issue("profile.lifecycle_successor_unexpected", "Only a superseded event may identify successor_revision.", event.record_type, event.profile_lifecycle_event_id))
    for lifecycle_predecessor_id, lifecycle_successor_ids in event_successors.items():
        if len(lifecycle_successor_ids) > 1:
            issues.append(_issue("profile.lifecycle_branch", "Lifecycle event has more than one successor.", "portfolio_profile_lifecycle_event", lifecycle_predecessor_id))
    event_predecessors = {
        item.profile_lifecycle_event_id: item.predecessor_event_id
        for item in state.lifecycle_events
    }
    for representative in _cycle_representatives(event_predecessors):
        issues.append(
            _issue(
                "profile.lifecycle_cycle",
                "Lifecycle predecessor chain contains a cycle.",
                "portfolio_profile_lifecycle_event",
                representative,
            )
        )
    for revision in state.revisions:
        lifecycle_heads = state.lifecycle_heads(revision.reference)
        if len(lifecycle_heads) > 1:
            issues.append(_issue("profile.lifecycle_conflict", "Profile Revision has multiple unresolved lifecycle heads.", revision.record_type, f"{revision.portfolio_profile_id}:{revision.profile_revision}"))

    # Binding history has one explicit head per Portfolio; endpoints resolve exactly.
    binding_successors: dict[str, list[str]] = defaultdict(list)
    for binding in state.bindings:
        if binding.portfolio_id not in portfolios:
            issues.append(_issue("profile_binding.portfolio_missing", "Bound Portfolio does not exist.", binding.record_type, binding.profile_binding_id))
        if _revision_key(binding.profile_revision) not in revisions:
            issues.append(_issue("profile_binding.revision_missing", "Bound Profile Revision does not exist.", binding.record_type, binding.profile_binding_id))
        if binding.predecessor_binding_id is not None:
            binding_predecessor = bindings.get(binding.predecessor_binding_id)
            if binding_predecessor is None:
                issues.append(_issue("profile_binding.predecessor_missing", "Profile Binding predecessor does not exist.", binding.record_type, binding.profile_binding_id))
            elif binding_predecessor.portfolio_id != binding.portfolio_id:
                issues.append(_issue("profile_binding.predecessor_mismatch", "Profile Binding predecessor belongs to another Portfolio.", binding.record_type, binding.profile_binding_id))
            binding_successors[binding.predecessor_binding_id].append(binding.profile_binding_id)
    for binding_predecessor_id, binding_successor_ids in binding_successors.items():
        if len(binding_successor_ids) > 1:
            issues.append(_issue("profile_binding.branch", "Profile Binding has more than one successor.", "portfolio_profile_binding", binding_predecessor_id))
    binding_predecessors = {
        item.profile_binding_id: item.predecessor_binding_id for item in state.bindings
    }
    for representative in _cycle_representatives(binding_predecessors):
        issues.append(
            _issue(
                "profile_binding.cycle",
                "Profile Binding predecessor chain contains a cycle.",
                "portfolio_profile_binding",
                representative,
            )
        )
    for portfolio_id in portfolios:
        binding_heads = state.active_binding_heads(portfolio_id)
        if len(binding_heads) > 1:
            issues.append(_issue("profile_binding.conflict", "Portfolio has multiple unresolved Profile Binding heads.", "portfolio", portfolio_id))

    # Overlay/component provenance.
    overlay_successors: dict[tuple[str, int], list[tuple[str, int]]] = defaultdict(list)
    for overlay in state.overlays:
        for component in overlay.component_revisions:
            component_revision = revisions.get(_revision_key(component))
            if component_revision is None:
                issues.append(_issue("profile.overlay_component_missing", "Overlay component Profile Revision does not exist.", overlay.record_type, f"{overlay.overlay_id}:{overlay.overlay_revision}"))
            elif component_revision.purpose_kind != overlay.purpose_kind:
                issues.append(_issue("profile.overlay_purpose_mismatch", "Overlay purpose does not match its exact component Revision.", overlay.record_type, f"{overlay.overlay_id}:{overlay.overlay_revision}"))
        if overlay.predecessor_overlay_revision is not None:
            overlay_predecessor_key = (overlay.overlay_id, overlay.predecessor_overlay_revision)
            if overlay_predecessor_key not in overlays:
                issues.append(_issue("profile.overlay_predecessor_missing", "Overlay predecessor Revision does not exist.", overlay.record_type, f"{overlay.overlay_id}:{overlay.overlay_revision}"))
            overlay_successors[overlay_predecessor_key].append((overlay.overlay_id, overlay.overlay_revision))
    for overlay_predecessor_key, overlay_successor_keys in overlay_successors.items():
        if len(overlay_successor_keys) > 1:
            issues.append(_issue("profile.overlay_branch", "Overlay Revision has more than one successor.", "portfolio_profile_overlay_revision", f"{overlay_predecessor_key[0]}:{overlay_predecessor_key[1]}"))

    compositions = {item.profile_composition_id: item for item in state.compositions}
    compositions_by_effective: dict[tuple[str, int], list[str]] = defaultdict(list)
    for composition in compositions.values():
        compositions_by_effective[_revision_key(composition.effective_profile_revision)].append(
            composition.profile_composition_id
        )
        if _revision_key(composition.effective_profile_revision) not in revisions:
            issues.append(_issue("profile.composition_effective_missing", "Effective composed Profile Revision does not exist.", composition.record_type, composition.profile_composition_id))
        for component in composition.component_profile_revisions:
            if _revision_key(component) not in revisions:
                issues.append(_issue("profile.composition_component_missing", "Composition component Profile Revision does not exist.", composition.record_type, composition.profile_composition_id))
        for overlay_ref in composition.overlay_revisions:
            if (overlay_ref.overlay_id, overlay_ref.overlay_revision) not in overlays:
                issues.append(_issue("profile.composition_overlay_missing", "Composition Overlay Revision does not exist.", composition.record_type, composition.profile_composition_id))
    for effective_key, composition_ids in compositions_by_effective.items():
        if len(composition_ids) > 1:
            issues.append(
                _issue(
                    "profile.composition_conflict",
                    "Effective Profile Revision has more than one composition provenance record.",
                    "portfolio_profile_revision",
                    f"{effective_key[0]}:{effective_key[1]}",
                )
            )

    # Migration records tie exact predecessor/successor Binding history together.
    for migration in state.migrations:
        migration_predecessor_binding = bindings.get(migration.predecessor_binding_id)
        migration_successor_binding = bindings.get(migration.successor_binding_id)
        if migration_predecessor_binding is None or migration_successor_binding is None:
            issues.append(_issue("profile.migration_binding_missing", "Migration references a missing Profile Binding.", migration.record_type, migration.profile_migration_id))
            continue
        if migration_predecessor_binding.portfolio_id != migration.portfolio_id or migration_successor_binding.portfolio_id != migration.portfolio_id:
            issues.append(_issue("profile.migration_portfolio_mismatch", "Migration Binding does not belong to the declared Portfolio.", migration.record_type, migration.profile_migration_id))
        if migration_successor_binding.predecessor_binding_id != migration_predecessor_binding.profile_binding_id:
            issues.append(_issue("profile.migration_chain_mismatch", "Migration successor Binding does not directly supersede predecessor Binding.", migration.record_type, migration.profile_migration_id))
        if migration_predecessor_binding.profile_revision != migration.source_profile_revision or migration_successor_binding.profile_revision != migration.target_profile_revision:
            issues.append(_issue("profile.migration_revision_mismatch", "Migration Profile Revision references disagree with Binding endpoints.", migration.record_type, migration.profile_migration_id))

    return tuple(sorted(issues, key=lambda item: (item.code, item.record_type or "", item.record_id or "", item.message)))


def validate_profile_state(state: PortfolioProfileState) -> None:
    issues = collect_profile_state_issues(state)
    if issues:
        raise VitrineProfileStateError(issues)


def build_profile_state(records: Iterable[VitrineRecord]) -> PortfolioProfileState:
    state = project_profile_state(records)
    validate_profile_state(state)
    return state


__all__ = [
    "PortfolioProfileState",
    "build_profile_state",
    "collect_profile_state_issues",
    "project_profile_state",
    "requirement_semantic_key",
    "validate_profile_state",
]
