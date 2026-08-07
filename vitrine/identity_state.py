"""Pure Portfolio Subject identity-history projection and validation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from vitrine.models import (
    ClassQualifiedStudentRef,
    Portfolio,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    PortfolioSubjectIdentityTransition,
    ValidationIssue,
    VitrineIdentityStateError,
    VitrineRecord,
)

_TERMINAL_LINK_DECISIONS = frozenset({"invalidate_link", "supersede_link"})
_SUBJECT_STATUS_BY_TRANSITION = {
    "merge": "merged",
    "split": "split",
    "invalidate": "invalidated",
    "supersede": "superseded",
}


def _issue(
    code: str,
    message: str,
    *,
    record_type: str | None = None,
    record_id: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        record_type=record_type,
        record_id=record_id,
    )


def _index_by_id(values: Iterable[object], field_name: str) -> dict[str, object]:
    return {str(getattr(item, field_name)): item for item in values}


@dataclass(frozen=True, slots=True)
class PortfolioSubjectIdentityState:
    """Derived current/historical view over immutable identity records."""

    portfolios: tuple[Portfolio, ...]
    subjects: tuple[PortfolioSubject, ...]
    links: tuple[PortfolioSubjectClassLink, ...]
    display_snapshots: tuple[PortfolioSubjectDisplaySnapshot, ...]
    decisions: tuple[PortfolioSubjectIdentityDecision, ...]
    transitions: tuple[PortfolioSubjectIdentityTransition, ...]

    def _current_decision_ids(self) -> frozenset[str]:
        superseded = {
            item.supersedes_decision_id
            for item in self.decisions
            if item.supersedes_decision_id is not None
        }
        return frozenset(
            item.identity_decision_id
            for item in self.decisions
            if item.identity_decision_id not in superseded
        )

    def _current_transition_ids(self) -> frozenset[str]:
        superseded = {
            item.supersedes_transition_id
            for item in self.transitions
            if item.supersedes_transition_id is not None
        }
        return frozenset(
            item.subject_identity_transition_id
            for item in self.transitions
            if item.subject_identity_transition_id not in superseded
        )

    def link_status(self, subject_link_id: str) -> str:
        current_decisions = self._current_decision_ids()
        terminal = [
            item.decision_type
            for item in self.decisions
            if item.identity_decision_id in current_decisions
            and subject_link_id in item.subject_link_ids
            and item.decision_type in _TERMINAL_LINK_DECISIONS
        ]
        if "supersede_link" in terminal:
            return "superseded"
        if "invalidate_link" in terminal:
            return "invalidated"
        return "confirmed"

    def subject_status(self, portfolio_subject_id: str) -> str:
        current_transitions = self._current_transition_ids()
        statuses = [
            _SUBJECT_STATUS_BY_TRANSITION[item.transition_type]
            for item in self.transitions
            if item.subject_identity_transition_id in current_transitions
            and portfolio_subject_id in item.predecessor_subject_ids
        ]
        return statuses[0] if statuses else "active"

    def current_links(
        self, portfolio_subject_id: str
    ) -> tuple[PortfolioSubjectClassLink, ...]:
        if self.subject_status(portfolio_subject_id) != "active":
            return ()
        return tuple(
            sorted(
                (
                    link
                    for link in self.links
                    if link.portfolio_subject_id == portfolio_subject_id
                    and self.link_status(link.subject_link_id) == "confirmed"
                ),
                key=lambda item: (
                    item.student_reference.school_year,
                    item.student_reference.class_id,
                    item.student_reference.student_id,
                    item.subject_link_id,
                ),
            )
        )

    def current_subjects_for_reference(
        self, reference: ClassQualifiedStudentRef
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    link.portfolio_subject_id
                    for link in self.links
                    if link.student_reference == reference
                    and self.link_status(link.subject_link_id) == "confirmed"
                    and self.subject_status(link.portfolio_subject_id) == "active"
                }
            )
        )

    def current_subject_for_reference(
        self, reference: ClassQualifiedStudentRef
    ) -> str | None:
        matches = self.current_subjects_for_reference(reference)
        return matches[0] if len(matches) == 1 else None

    def latest_display_snapshot(
        self, subject_link_id: str
    ) -> PortfolioSubjectDisplaySnapshot | None:
        matches = [
            item
            for item in self.display_snapshots
            if item.subject_link_id == subject_link_id
        ]
        if not matches:
            return None
        return max(
            matches,
            key=lambda item: (item.captured_at, item.display_snapshot_id),
        )


def project_identity_state(
    records: Iterable[VitrineRecord],
) -> PortfolioSubjectIdentityState:
    """Project identity records without deciding whether conflicts are recoverable."""
    values = tuple(records)
    return PortfolioSubjectIdentityState(
        portfolios=tuple(item for item in values if isinstance(item, Portfolio)),
        subjects=tuple(
            item for item in values if isinstance(item, PortfolioSubject)
        ),
        links=tuple(
            item
            for item in values
            if isinstance(item, PortfolioSubjectClassLink)
        ),
        display_snapshots=tuple(
            item
            for item in values
            if isinstance(item, PortfolioSubjectDisplaySnapshot)
        ),
        decisions=tuple(
            item
            for item in values
            if isinstance(item, PortfolioSubjectIdentityDecision)
        ),
        transitions=tuple(
            item
            for item in values
            if isinstance(item, PortfolioSubjectIdentityTransition)
        ),
    )


def build_identity_state(
    records: Iterable[VitrineRecord],
) -> PortfolioSubjectIdentityState:
    state = project_identity_state(records)
    validate_identity_state(state)
    return state


def collect_identity_state_issues(
    state: PortfolioSubjectIdentityState,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    subjects = _index_by_id(state.subjects, "portfolio_subject_id")
    links = _index_by_id(state.links, "subject_link_id")
    decisions = _index_by_id(state.decisions, "identity_decision_id")
    transitions = _index_by_id(
        state.transitions, "subject_identity_transition_id"
    )
    portfolios = _index_by_id(state.portfolios, "portfolio_id")

    for snapshot in state.display_snapshots:
        link = links.get(snapshot.subject_link_id)
        if link is None:
            issues.append(
                _issue(
                    "identity.display_snapshot_link_missing",
                    "Display Snapshot references a missing Subject link.",
                    record_type=snapshot.record_type,
                    record_id=snapshot.display_snapshot_id,
                )
            )
        elif isinstance(link, PortfolioSubjectClassLink) and (
            snapshot.student_reference != link.student_reference
        ):
            issues.append(
                _issue(
                    "identity.display_snapshot_reference_mismatch",
                    "Display Snapshot roster reference differs from its Subject link.",
                    record_type=snapshot.record_type,
                    record_id=snapshot.display_snapshot_id,
                )
            )

    for decision in state.decisions:
        for subject_id in decision.subject_ids:
            if subject_id not in subjects:
                issues.append(
                    _issue(
                        "identity.decision_subject_missing",
                        "Identity Decision references a missing Subject.",
                        record_type=decision.record_type,
                        record_id=decision.identity_decision_id,
                    )
                )
        for link_id in decision.subject_link_ids:
            if link_id not in links:
                issues.append(
                    _issue(
                        "identity.decision_link_missing",
                        "Identity Decision references a missing Subject link.",
                        record_type=decision.record_type,
                        record_id=decision.identity_decision_id,
                    )
                )
        if (
            decision.supersedes_decision_id is not None
            and decision.supersedes_decision_id not in decisions
        ):
            issues.append(
                _issue(
                    "identity.decision_predecessor_missing",
                    "Identity Decision supersedes a missing decision.",
                    record_type=decision.record_type,
                    record_id=decision.identity_decision_id,
                )
            )

    decision_successors: dict[str, list[str]] = {}
    for decision in state.decisions:
        if decision.supersedes_decision_id is not None:
            decision_successors.setdefault(
                decision.supersedes_decision_id, []
            ).append(decision.identity_decision_id)
    for predecessor, successors in decision_successors.items():
        if len(successors) > 1:
            issues.append(
                _issue(
                    "identity.decision_supersession_branch",
                    "One Identity Decision has multiple direct corrections.",
                    record_type="portfolio_subject_identity_decision",
                    record_id=predecessor,
                )
            )
    for decision in state.decisions:
        seen: set[str] = set()
        current: PortfolioSubjectIdentityDecision | None = decision
        while current is not None and current.supersedes_decision_id is not None:
            if current.identity_decision_id in seen:
                issues.append(
                    _issue(
                        "identity.decision_supersession_cycle",
                        "Identity Decision correction chain contains a cycle.",
                        record_type=decision.record_type,
                        record_id=decision.identity_decision_id,
                    )
                )
                break
            seen.add(current.identity_decision_id)
            predecessor_decision = decisions.get(current.supersedes_decision_id)
            current = (
                predecessor_decision
                if isinstance(predecessor_decision, PortfolioSubjectIdentityDecision)
                else None
            )

    current_decisions = state._current_decision_ids()
    terminal_by_link: dict[str, list[str]] = {}
    for decision in state.decisions:
        if (
            decision.identity_decision_id in current_decisions
            and decision.decision_type in _TERMINAL_LINK_DECISIONS
        ):
            for link_id in decision.subject_link_ids:
                terminal_by_link.setdefault(link_id, []).append(
                    decision.identity_decision_id
                )
    for link_id, terminal_decisions in terminal_by_link.items():
        if len(terminal_decisions) > 1:
            issues.append(
                _issue(
                    "identity.link_terminal_conflict",
                    "Subject link has conflicting current terminal decisions.",
                    record_type="portfolio_subject_class_link",
                    record_id=link_id,
                )
            )

    for transition in state.transitions:
        transition_decision = decisions.get(transition.identity_decision_id)
        expected_decision_type = {
            "merge": "merge_subjects",
            "split": "split_subject",
            "invalidate": "invalidate_subject",
            "supersede": "supersede_subject",
        }[transition.transition_type]
        if not isinstance(transition_decision, PortfolioSubjectIdentityDecision):
            issues.append(
                _issue(
                    "identity.transition_decision_missing",
                    "Subject transition references a missing Identity Decision.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )
        elif transition_decision.decision_type != expected_decision_type:
            issues.append(
                _issue(
                    "identity.transition_decision_type_mismatch",
                    "Transition and Identity Decision types disagree.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )
        elif transition.transition_type in {"merge", "split"}:
            expected_subject_ids = set(transition.predecessor_subject_ids) | set(
                transition.successor_subject_ids
            )
            if set(transition_decision.subject_ids) != expected_subject_ids:
                issues.append(
                    _issue(
                        "identity.transition_decision_subject_mismatch",
                        "Transition decision must identify every predecessor and successor Subject.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
        for subject_id in (
            *transition.predecessor_subject_ids,
            *transition.successor_subject_ids,
        ):
            if subject_id not in subjects:
                issues.append(
                    _issue(
                        "identity.transition_subject_missing",
                        "Subject transition references a missing Subject.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
        if (
            transition.supersedes_transition_id is not None
            and transition.supersedes_transition_id not in transitions
        ):
            issues.append(
                _issue(
                    "identity.transition_predecessor_missing",
                    "Subject transition supersedes a missing transition.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )
        expected_portfolios = tuple(
            sorted(
                portfolio.portfolio_id
                for portfolio in state.portfolios
                if portfolio.portfolio_subject_id
                in transition.predecessor_subject_ids
            )
        )
        if tuple(sorted(transition.affected_portfolio_ids)) != expected_portfolios:
            issues.append(
                _issue(
                    "identity.transition_affected_portfolios_mismatch",
                    "Transition affected Portfolio inventory is incomplete or excessive.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )
        for portfolio_id in transition.affected_portfolio_ids:
            if portfolio_id not in portfolios:
                issues.append(
                    _issue(
                        "identity.transition_portfolio_missing",
                        "Transition references a missing affected Portfolio.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )

        allocated_predecessors: list[str] = []
        for allocation in transition.association_allocations:
            allocated_predecessors.extend(allocation.predecessor_link_ids)
            if allocation.successor_subject_id not in transition.successor_subject_ids:
                issues.append(
                    _issue(
                        "identity.allocation_successor_subject_mismatch",
                        "Allocation successor Subject is not a transition successor.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
            successor_link = links.get(allocation.successor_link_id)
            if not isinstance(successor_link, PortfolioSubjectClassLink):
                issues.append(
                    _issue(
                        "identity.allocation_successor_link_missing",
                        "Allocation references a missing successor link.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
                continue
            if successor_link.portfolio_subject_id != allocation.successor_subject_id:
                issues.append(
                    _issue(
                        "identity.allocation_successor_link_mismatch",
                        "Allocation successor link belongs to another Subject.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
            predecessor_refs: set[ClassQualifiedStudentRef] = set()
            for predecessor_link_id in allocation.predecessor_link_ids:
                predecessor_link = links.get(predecessor_link_id)
                if not isinstance(predecessor_link, PortfolioSubjectClassLink):
                    issues.append(
                        _issue(
                            "identity.allocation_predecessor_link_missing",
                            "Allocation references a missing predecessor link.",
                            record_type=transition.record_type,
                            record_id=transition.subject_identity_transition_id,
                        )
                    )
                    continue
                if (
                    predecessor_link.portfolio_subject_id
                    not in transition.predecessor_subject_ids
                ):
                    issues.append(
                        _issue(
                            "identity.allocation_predecessor_subject_mismatch",
                            "Allocation predecessor link belongs to another Subject.",
                            record_type=transition.record_type,
                            record_id=transition.subject_identity_transition_id,
                        )
                    )
                predecessor_refs.add(predecessor_link.student_reference)
            if predecessor_refs and (
                predecessor_refs != {successor_link.student_reference}
            ):
                issues.append(
                    _issue(
                        "identity.allocation_reference_mismatch",
                        "Allocation must preserve one exact roster reference.",
                        record_type=transition.record_type,
                        record_id=transition.subject_identity_transition_id,
                    )
                )
        if len(allocated_predecessors) != len(set(allocated_predecessors)):
            issues.append(
                _issue(
                    "identity.allocation_duplicate_predecessor_link",
                    "A predecessor link is allocated more than once.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )
        if (
            transition.transition_type in {"merge", "split"}
            and isinstance(transition_decision, PortfolioSubjectIdentityDecision)
            and set(allocated_predecessors) != set(transition_decision.subject_link_ids)
        ):
            issues.append(
                _issue(
                    "identity.allocation_inventory_mismatch",
                    "Transition allocation must cover every predecessor link in its decision exactly once.",
                    record_type=transition.record_type,
                    record_id=transition.subject_identity_transition_id,
                )
            )

    current_transitions = state._current_transition_ids()
    terminal_by_subject: dict[str, list[str]] = {}
    for transition in state.transitions:
        if transition.subject_identity_transition_id not in current_transitions:
            continue
        for subject_id in transition.predecessor_subject_ids:
            terminal_by_subject.setdefault(subject_id, []).append(
                transition.subject_identity_transition_id
            )
    for subject_id, subject_transitions in terminal_by_subject.items():
        if len(subject_transitions) > 1:
            issues.append(
                _issue(
                    "identity.subject_terminal_transition_conflict",
                    "Subject has multiple current terminal transitions.",
                    record_type="portfolio_subject",
                    record_id=subject_id,
                )
            )

    adjacency: dict[str, set[str]] = {}
    for transition in state.transitions:
        if transition.subject_identity_transition_id not in current_transitions:
            continue
        for predecessor in transition.predecessor_subject_ids:
            adjacency.setdefault(predecessor, set()).update(
                transition.successor_subject_ids
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(subject_id: str) -> bool:
        if subject_id in visiting:
            return True
        if subject_id in visited:
            return False
        visiting.add(subject_id)
        for successor_id in adjacency.get(subject_id, ()):
            if visit(successor_id):
                return True
        visiting.remove(subject_id)
        visited.add(subject_id)
        return False

    for subject_id in sorted(subjects):
        if subject_id not in visited and visit(subject_id):
            issues.append(
                _issue(
                    "identity.transition_cycle",
                    "Subject transition graph contains a cycle.",
                    record_type="portfolio_subject",
                    record_id=subject_id,
                )
            )
            break

    active_refs: dict[ClassQualifiedStudentRef, str] = {}
    for link in state.links:
        if state.link_status(link.subject_link_id) != "confirmed":
            continue
        if state.subject_status(link.portfolio_subject_id) != "active":
            continue
        prior = active_refs.get(link.student_reference)
        if prior is not None and prior != link.portfolio_subject_id:
            issues.append(
                _issue(
                    "identity.duplicate_active_association",
                    "One exact roster reference has multiple current Subjects.",
                    record_type=link.record_type,
                    record_id=link.subject_link_id,
                )
            )
        else:
            active_refs[link.student_reference] = link.portfolio_subject_id

    return tuple(
        sorted(
            issues,
            key=lambda item: (
                item.code,
                item.record_type or "",
                item.record_id or "",
                item.message,
            ),
        )
    )


def validate_identity_state(state: PortfolioSubjectIdentityState) -> None:
    issues = collect_identity_state_issues(state)
    if issues:
        raise VitrineIdentityStateError(issues)


__all__ = [
    "PortfolioSubjectIdentityState",
    "build_identity_state",
    "project_identity_state",
    "collect_identity_state_issues",
    "validate_identity_state",
]
