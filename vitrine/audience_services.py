"""Application services for freezing exact Profile audience rules."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    Portfolio,
    VitrineRecord,
)
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageNotFoundError,
    commit_record_batch,
    load_current_records,
    load_current_state,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


class AudienceWorkflowError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class AudienceMutationResult:
    context: AudienceContext
    state_revision: int


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _load(root: str | Path) -> tuple[tuple[VitrineRecord, ...], int | None]:
    try:
        current = load_current_state(root)
    except VitrineStorageNotFoundError:
        return (), None
    return load_current_records(root), current.state_revision


def list_audience_contexts(
    workspace_root: str | Path, *, portfolio_id: str | None = None
) -> tuple[AudienceContext, ...]:
    records, _ = _load(workspace_root)
    return tuple(
        sorted(
            (
                item
                for item in records
                if isinstance(item, AudienceContext)
                and (portfolio_id is None or item.portfolio_id == portfolio_id)
            ),
            key=lambda item: item.audience_context_id,
        )
    )


def show_audience_context(
    workspace_root: str | Path, audience_context_id: str
) -> AudienceContext:
    matches = tuple(
        x
        for x in list_audience_contexts(workspace_root)
        if x.audience_context_id == audience_context_id
    )
    if len(matches) != 1:
        raise AudienceWorkflowError(
            "audience_context_not_found", "Audience Context not found."
        )
    return matches[0]


def create_audience_context(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    audience_rule_id: str,
    created_by: ActorAttribution,
    expected_state_revision: int,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> AudienceMutationResult:
    records, actual = _load(workspace_root)
    if actual != expected_state_revision:
        raise AudienceWorkflowError(
            "state_conflict", "Vitrine state changed since observation."
        )
    portfolio = next(
        (
            x
            for x in records
            if isinstance(x, Portfolio) and x.portfolio_id == portfolio_id
        ),
        None,
    )
    if portfolio is None:
        raise AudienceWorkflowError("portfolio_not_found", "Portfolio not found.")
    state = project_profile_state(records)
    if collect_profile_state_issues(state):
        raise AudienceWorkflowError(
            "profile_state_invalid", "Portfolio Profile state is invalid."
        )
    binding = state.active_binding(portfolio_id)
    if binding is None:
        raise AudienceWorkflowError(
            "profile_binding_missing", "Portfolio has no active Profile Binding."
        )
    revision = state.revision(binding.profile_revision)
    if revision is None:
        raise AudienceWorkflowError(
            "profile_revision_missing", "Bound Profile Revision is missing."
        )
    rule = next(
        (x for x in revision.audience_rules if x.audience_rule_id == audience_rule_id),
        None,
    )
    if rule is None:
        raise AudienceWorkflowError(
            "audience_rule_not_found",
            "Audience rule is not in the exact bound Profile Revision.",
        )
    context = AudienceContext(
        audience_context_id=id_factory("audience"),
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=binding.profile_revision,
        audience_rule_id=rule.audience_rule_id,
        audience_class=rule.audience_class,
        purpose=rule.purpose,
        subject_scope="portfolio_subject",
        allowed_content_classes=rule.allowed_content_classes,
        prohibited_content_classes=rule.prohibited_content_classes,
        required_review_classes=rule.required_review_classes,
        presentation_class=rule.presentation_class,
        retention_policy_reference=rule.retention_policy_reference,
        created_at=clock(),
        created_by=created_by,
    )
    try:
        commit = commit_record_batch(
            workspace_root, (context,), expected_state_revision=expected_state_revision
        )
    except VitrineStorageConflictError as error:
        raise AudienceWorkflowError("state_conflict", str(error)) from error
    return AudienceMutationResult(context, commit.state_revision)


__all__ = [
    "AudienceMutationResult",
    "AudienceWorkflowError",
    "create_audience_context",
    "list_audience_contexts",
    "show_audience_context",
]
