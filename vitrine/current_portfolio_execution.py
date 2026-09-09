"""Prepared execution through canonical Current Portfolio planning boundaries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeVar

from vitrine.audience_services import AudienceWorkflowError, create_audience_context
from vitrine.curation_services import CurationWorkflowError
from vitrine.current_portfolio_build import (
    CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
    CurrentPortfolioBuildError,
    CurrentPortfolioBuildPreparation,
    prepare_current_portfolio_build,
)
from vitrine.current_portfolio_reflection import (
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
    CurrentPortfolioReflectionRenderer,
)
from vitrine.models import (
    ActorAttribution,
    DigestReference,
    PortfolioProfileRevision,
    PortfolioReflection,
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEdition,
    SnapshotEditionBuildProvenance,
    SnapshotExportPlan,
    SnapshotSeries,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    create_snapshot_directory_export,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityGate,
    SnapshotMaterializationError,
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_services import (
    SnapshotMutationResult,
    SnapshotWorkflowError,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
    load_current_state,
)

CURRENT_PORTFOLIO_EXECUTION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "current_portfolio_build.invalid_preparation",
        "current_portfolio_build.preparation_blocked",
        "current_portfolio_build.prepared_state_changed",
        "current_portfolio_build.execution_state_conflict",
        "current_portfolio_build.audience_context_failed",
        "current_portfolio_build.snapshot_series_failed",
        "current_portfolio_build.build_request_failed",
        "current_portfolio_build.build_plan_failed",
        "current_portfolio_build.canonical_result_invalid",
        "current_portfolio_build.attempt_start_failed",
        "current_portfolio_build.snapshot_authority_denied",
        "current_portfolio_build.snapshot_authority_unresolved",
        "current_portfolio_build.producer_artifact_authorization_denied",
        "current_portfolio_build.producer_artifact_authorization_unresolved",
        "current_portfolio_build.materialization_failed",
        "current_portfolio_build.sealing_failed",
        "current_portfolio_build.edition_verification_failed",
        "current_portfolio_build.export_failed",
        "current_portfolio_build.export_verification_failed",
        "current_portfolio_build.resume_invalid",
    }
)

_REQUEST_IDEMPOTENCY_PREFIX: Final[str] = "current_portfolio_build:"
T = TypeVar("T")


class CurrentPortfolioExecutionError(RuntimeError):
    """Privacy-safe failure from prepared Current Portfolio execution."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        underlying_code: str | None = None,
        underlying_stage: str | None = None,
        completed_stages: tuple[str, ...] = (),
        audience_context_id: str | None = None,
        snapshot_series_id: str | None = None,
        snapshot_build_request_id: str | None = None,
        snapshot_build_plan_id: str | None = None,
        snapshot_build_attempt_id: str | None = None,
        edition_number: int | None = None,
        snapshot_export_artifact_id: str | None = None,
        next_safe_action: str | None = None,
    ) -> None:
        if code not in CURRENT_PORTFOLIO_EXECUTION_ERROR_CODES:
            raise ValueError(f"unsupported Current Portfolio execution code: {code}")
        self.code = code
        self.stage = stage
        self.underlying_code = underlying_code
        self.underlying_stage = underlying_stage
        self.completed_stages = completed_stages
        self.audience_context_id = audience_context_id
        self.snapshot_series_id = snapshot_series_id
        self.snapshot_build_request_id = snapshot_build_request_id
        self.snapshot_build_plan_id = snapshot_build_plan_id
        self.snapshot_build_attempt_id = snapshot_build_attempt_id
        self.edition_number = edition_number
        self.snapshot_export_artifact_id = snapshot_export_artifact_id
        self.next_safe_action = next_safe_action
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CurrentPortfolioPlanExecutionResult:
    """Durable canonical chain through immutable Snapshot Build Plan creation."""

    contract_version: str
    preparation_fingerprint: str
    initial_state_revision: int
    state_revision: int
    audience_context_id: str
    audience_context_disposition: str
    snapshot_series_id: str
    snapshot_series_disposition: str
    snapshot_build_request_id: str
    snapshot_build_request_disposition: str
    snapshot_build_plan_id: str
    snapshot_build_plan_disposition: str
    request_idempotency_key: str

    def __post_init__(self) -> None:
        if self.contract_version != CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION:
            raise ValueError("unexpected Current Portfolio contract version")
        if self.initial_state_revision <= 0 or self.state_revision <= 0:
            raise ValueError("state revisions must be positive")
        if self.state_revision < self.initial_state_revision:
            raise ValueError("final state revision cannot precede initial revision")
        for value in (
            self.audience_context_disposition,
            self.snapshot_series_disposition,
        ):
            if value not in {"created", "reused"}:
                raise ValueError("unsupported create/reuse disposition")
        for value in (
            self.snapshot_build_request_disposition,
            self.snapshot_build_plan_disposition,
        ):
            if value not in {"created", "existing"}:
                raise ValueError("unsupported canonical Snapshot disposition")


@dataclass(frozen=True, slots=True)
class CurrentPortfolioBuildExportResult:
    """Exact durable result chain through verified local directory Export."""

    contract_version: str
    preparation_fingerprint: str
    state_revision: int
    audience_context_id: str
    snapshot_series_id: str
    snapshot_build_request_id: str
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    attempt_number: int
    attempt_terminal_outcome: str
    edition_number: int
    edition_manifest_sha256: str
    edition_logical_inventory_sha256: str
    snapshot_export_artifact_id: str
    export_disposition: str
    export_directory_inventory_sha256: str
    export_path: Path
    current_pointer_advanced: bool = False

    def __post_init__(self) -> None:
        if self.contract_version != CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION:
            raise ValueError("unexpected Current Portfolio contract version")
        if self.state_revision <= 0 or self.attempt_number <= 0:
            raise ValueError("state revision and Attempt number must be positive")
        if self.edition_number <= 0:
            raise ValueError("Edition number must be positive")
        if self.export_disposition not in {"created", "existing"}:
            raise ValueError("unsupported Export disposition")
        if self.current_pointer_advanced:
            raise ValueError("Current Portfolio build/export must not advance pointer")


@dataclass(frozen=True, slots=True)
class CurrentPortfolioExportResumeResult:
    """Verified Export result when resuming one already sealed exact Edition."""

    state_revision: int
    snapshot_series_id: str
    edition_number: int
    snapshot_export_artifact_id: str
    export_disposition: str
    export_directory_inventory_sha256: str
    export_path: Path

    def __post_init__(self) -> None:
        if self.state_revision <= 0 or self.edition_number <= 0:
            raise ValueError("state revision and Edition number must be positive")
        if self.export_disposition not in {"created", "existing"}:
            raise ValueError("unsupported Export disposition")


def _execution_error(
    code: str,
    message: str,
    *,
    stage: str,
    underlying_code: str | None = None,
    underlying_stage: str | None = None,
    completed_stages: tuple[str, ...] = (),
    audience_context_id: str | None = None,
    snapshot_series_id: str | None = None,
    snapshot_build_request_id: str | None = None,
    snapshot_build_plan_id: str | None = None,
    snapshot_build_attempt_id: str | None = None,
    edition_number: int | None = None,
    snapshot_export_artifact_id: str | None = None,
    next_safe_action: str | None = None,
) -> CurrentPortfolioExecutionError:
    return CurrentPortfolioExecutionError(
        code,
        message,
        stage=stage,
        underlying_code=underlying_code,
        underlying_stage=underlying_stage,
        completed_stages=completed_stages,
        audience_context_id=audience_context_id,
        snapshot_series_id=snapshot_series_id,
        snapshot_build_request_id=snapshot_build_request_id,
        snapshot_build_plan_id=snapshot_build_plan_id,
        snapshot_build_attempt_id=snapshot_build_attempt_id,
        edition_number=edition_number,
        snapshot_export_artifact_id=snapshot_export_artifact_id,
        next_safe_action=next_safe_action,
    )


def _revalidation_choice(value: str, selected_id: str | None) -> str | None:
    return selected_id if value == "reuse" else None


def _revalidate_preparation(
    workspace_root: str | Path,
    preparation: CurrentPortfolioBuildPreparation,
    source_providers: SnapshotSourceProviderRegistry,
) -> None:
    if preparation.contract_version != CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION:
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Prepared Current Portfolio contract is unsupported.",
            stage="preparation",
        )
    if not preparation.ready_for_plan_execution:
        raise _execution_error(
            "current_portfolio_build.preparation_blocked",
            "Prepared Current Portfolio still contains blocking conditions.",
            stage="preparation",
        )
    if preparation.current_composition_revision is None:
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Prepared Current Portfolio has no exact current Composition revision.",
            stage="preparation",
        )
    if preparation.audience_context.disposition == "requires_choice":
        raise _execution_error(
            "current_portfolio_build.preparation_blocked",
            "Prepared Current Portfolio requires an exact Audience Context choice.",
            stage="preparation",
        )
    if preparation.snapshot_series.disposition == "requires_choice":
        raise _execution_error(
            "current_portfolio_build.preparation_blocked",
            "Prepared Current Portfolio requires an exact Snapshot Series choice.",
            stage="preparation",
        )
    if not preparation.snapshot_entry_plans:
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Prepared Current Portfolio has no executable Snapshot Entry Plans.",
            stage="preparation",
        )
    if not preparation.directory_export.included_entry_plan_ids:
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Prepared Current Portfolio has no byte-bearing directory Export entries.",
            stage="preparation",
        )

    try:
        current = load_current_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise _execution_error(
            "current_portfolio_build.prepared_state_changed",
            "Prepared Current Portfolio state is no longer available.",
            stage="revalidation",
        ) from error
    if current.state_revision != preparation.observed_state_revision:
        raise _execution_error(
            "current_portfolio_build.prepared_state_changed",
            "Vitrine state changed after Current Portfolio preparation.",
            stage="revalidation",
        )

    audience_context_id = _revalidation_choice(
        preparation.audience_context.disposition,
        preparation.audience_context.selected_audience_context_id,
    )
    snapshot_series_id = _revalidation_choice(
        preparation.snapshot_series.disposition,
        preparation.snapshot_series.selected_snapshot_series_id,
    )
    try:
        observed = prepare_current_portfolio_build(
            workspace_root,
            preparation.portfolio_id,
            audience_rule_id=preparation.selected_audience_rule.audience_rule_id,
            audience_context_id=audience_context_id,
            snapshot_series_id=snapshot_series_id,
            acknowledged_obligation_codes=(
                preparation.acknowledged_obligation_codes
            ),
            source_providers=source_providers,
        )
    except (CurrentPortfolioBuildError, CurationWorkflowError) as error:
        raise _execution_error(
            "current_portfolio_build.prepared_state_changed",
            "Current Portfolio preparation no longer revalidates exactly.",
            stage="revalidation",
            underlying_code=error.code,
        ) from error

    if (
        observed.preparation_fingerprint != preparation.preparation_fingerprint
        or observed.blocking_reasons != preparation.blocking_reasons
        or not observed.ready_for_plan_execution
    ):
        raise _execution_error(
            "current_portfolio_build.prepared_state_changed",
            "Current Portfolio semantics changed after the reviewed preparation.",
            stage="revalidation",
        )


def _result_record(
    result: SnapshotMutationResult, record_type: type[T], stage: str
) -> T:
    matches = tuple(item for item in result.records if isinstance(item, record_type))
    if len(matches) != 1:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Canonical Snapshot service returned an unexpected result shape.",
            stage=stage,
        )
    return matches[0]


def _request_idempotency_key(
    preparation: CurrentPortfolioBuildPreparation,
    *,
    audience_context_id: str,
    snapshot_series_id: str,
    actor: ActorAttribution,
) -> str:
    value = {
        "contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        "snapshot_series_id": snapshot_series_id,
        "portfolio_id": preparation.portfolio_id,
        "portfolio_subject_id": preparation.portfolio_subject_id,
        "profile_binding_id": preparation.profile_binding_id,
        "profile_revision": {
            "portfolio_profile_id": preparation.profile_revision_id,
            "profile_revision": preparation.profile_revision_number,
        },
        "composition_revision": preparation.current_composition_revision,
        "audience_context_id": audience_context_id,
        "snapshot_purpose": preparation.selected_audience_rule.purpose,
        "requested_export_formats": (preparation.directory_export.export_format,),
        "requested_by": {
            "actor_kind": actor.actor_kind,
            "actor_id": actor.actor_id,
            "owning_system": actor.owning_system,
            "display_label_snapshot": actor.display_label_snapshot,
            "role_snapshot": actor.role_snapshot,
        },
        "curation_review_decision_ids": (
            preparation.composition_inventory.applicable_review_decision_ids
        ),
        "predecessor_request_id": None,
    }
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{_REQUEST_IDEMPOTENCY_PREFIX}{digest}"


def _export_plan(
    preparation: CurrentPortfolioBuildPreparation,
) -> SnapshotExportPlan:
    preview = preparation.directory_export
    return SnapshotExportPlan(
        export_plan_id=preview.export_plan_id,
        export_format=preview.export_format,
        export_contract_version=preview.export_contract_version,
        included_entry_plan_ids=preview.included_entry_plan_ids,
        excluded_entry_plan_ids=preview.excluded_entry_plan_ids,
        configuration_digest=DigestReference(value=preview.configuration_sha256),
    )


def _audience_failure(
    error: AudienceWorkflowError,
) -> CurrentPortfolioExecutionError:
    if error.code == "state_conflict":
        return _execution_error(
            "current_portfolio_build.execution_state_conflict",
            "Vitrine state changed during Audience Context creation.",
            stage="audience_context",
            underlying_code=error.code,
        )
    return _execution_error(
        "current_portfolio_build.audience_context_failed",
        "Exact Audience Context creation failed.",
        stage="audience_context",
        underlying_code=error.code,
    )


def _snapshot_failure(
    error: SnapshotWorkflowError,
    *,
    task_code: str,
    task_stage: str,
    completed_stages: tuple[str, ...],
    audience_context_id: str | None,
    snapshot_series_id: str | None = None,
    snapshot_build_request_id: str | None = None,
) -> CurrentPortfolioExecutionError:
    code = (
        "current_portfolio_build.execution_state_conflict"
        if error.code == "snapshot.state_conflict"
        else task_code
    )
    return _execution_error(
        code,
        f"Current Portfolio execution failed during {task_stage.replace('_', ' ')}.",
        stage=task_stage,
        underlying_code=error.code,
        underlying_stage=error.stage,
        completed_stages=completed_stages,
        audience_context_id=audience_context_id,
        snapshot_series_id=snapshot_series_id,
        snapshot_build_request_id=snapshot_build_request_id,
    )


def execute_prepared_current_portfolio_plan(
    workspace_root: str | Path,
    preparation: CurrentPortfolioBuildPreparation,
    *,
    actor: ActorAttribution,
    source_providers: SnapshotSourceProviderRegistry | None = None,
) -> CurrentPortfolioPlanExecutionResult:
    """Revalidate one reviewed preparation and persist canonical Request/Plan state.

    This Slice-4 boundary intentionally stops after immutable Build Plan creation.
    It does not start a Build Attempt, acquire source bytes, render content, seal an
    Edition, create an Export Artifact, or advance the current Edition pointer.
    """

    if not isinstance(preparation, CurrentPortfolioBuildPreparation):
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Current Portfolio execution requires an exact preparation value.",
            stage="preparation",
        )
    if not isinstance(actor, ActorAttribution):
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Current Portfolio execution requires exact actor attribution.",
            stage="preparation",
        )

    providers = source_providers or SnapshotSourceProviderRegistry()
    _revalidate_preparation(workspace_root, preparation, providers)

    initial_revision = preparation.observed_state_revision
    revision = initial_revision
    completed: list[str] = []

    audience_context_id = preparation.audience_context.selected_audience_context_id
    if preparation.audience_context.disposition == "create":
        try:
            audience_result = create_audience_context(
                workspace_root,
                portfolio_id=preparation.portfolio_id,
                audience_rule_id=preparation.selected_audience_rule.audience_rule_id,
                created_by=actor,
                expected_state_revision=revision,
            )
        except AudienceWorkflowError as error:
            raise _audience_failure(error) from error
        audience_context_id = audience_result.context.audience_context_id
        revision = audience_result.state_revision
        audience_disposition = "created"
    else:
        audience_disposition = "reused"
    if audience_context_id is None:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Exact Audience Context identity is unavailable after execution.",
            stage="audience_context",
        )
    completed.append("audience_context")

    snapshot_series_id = preparation.snapshot_series.selected_snapshot_series_id
    if preparation.snapshot_series.disposition == "create":
        try:
            series_result = create_snapshot_series(
                workspace_root,
                portfolio_id=preparation.portfolio_id,
                audience_context_id=audience_context_id,
                snapshot_purpose=preparation.selected_audience_rule.purpose,
                created_by=actor,
                expected_state_revision=revision,
            )
        except SnapshotWorkflowError as error:
            raise _snapshot_failure(
                error,
                task_code="current_portfolio_build.snapshot_series_failed",
                task_stage="snapshot_series",
                completed_stages=tuple(completed),
                audience_context_id=audience_context_id,
            ) from error
        series = _result_record(series_result, SnapshotSeries, "snapshot_series")
        snapshot_series_id = series.snapshot_series_id
        revision = series_result.state_revision
        series_disposition = "created"
    else:
        series_disposition = "reused"
    if snapshot_series_id is None:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Exact Snapshot Series identity is unavailable after execution.",
            stage="snapshot_series",
            completed_stages=tuple(completed),
            audience_context_id=audience_context_id,
        )
    completed.append("snapshot_series")

    idempotency_key = _request_idempotency_key(
        preparation,
        audience_context_id=audience_context_id,
        snapshot_series_id=snapshot_series_id,
        actor=actor,
    )
    assert preparation.current_composition_revision is not None
    try:
        request_result = request_snapshot_build(
            workspace_root,
            snapshot_series_id=snapshot_series_id,
            composition_revision=preparation.current_composition_revision,
            requested_by=actor,
            expected_state_revision=revision,
            idempotency_key=idempotency_key,
            requested_export_formats=(preparation.directory_export.export_format,),
        )
    except SnapshotWorkflowError as error:
        raise _snapshot_failure(
            error,
            task_code="current_portfolio_build.build_request_failed",
            task_stage="build_request",
            completed_stages=tuple(completed),
            audience_context_id=audience_context_id,
            snapshot_series_id=snapshot_series_id,
        ) from error
    request = _result_record(request_result, SnapshotBuildRequest, "build_request")
    revision = request_result.state_revision
    completed.append("build_request")

    export_plan = _export_plan(preparation)
    try:
        plan_result = plan_snapshot_build(
            workspace_root,
            snapshot_build_request_id=request.snapshot_build_request_id,
            entry_plans=preparation.snapshot_entry_plans,
            export_plans=(export_plan,),
            planned_by=actor,
            expected_state_revision=revision,
            acknowledged_obligation_codes=(
                preparation.acknowledged_obligation_codes
            ),
        )
    except SnapshotWorkflowError as error:
        raise _snapshot_failure(
            error,
            task_code="current_portfolio_build.build_plan_failed",
            task_stage="build_plan",
            completed_stages=tuple(completed),
            audience_context_id=audience_context_id,
            snapshot_series_id=snapshot_series_id,
            snapshot_build_request_id=request.snapshot_build_request_id,
        ) from error
    plan = _result_record(plan_result, SnapshotBuildPlan, "build_plan")
    if (
        plan.entry_plans != preparation.snapshot_entry_plans
        or plan.export_plans != (export_plan,)
        or plan.acknowledged_obligation_codes
        != preparation.acknowledged_obligation_codes
    ):
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Immutable Snapshot Build Plan differs from the reviewed preparation.",
            stage="build_plan",
            completed_stages=tuple(completed),
            audience_context_id=audience_context_id,
            snapshot_series_id=snapshot_series_id,
            snapshot_build_request_id=request.snapshot_build_request_id,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
        )
    revision = plan_result.state_revision

    return CurrentPortfolioPlanExecutionResult(
        contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        preparation_fingerprint=preparation.preparation_fingerprint,
        initial_state_revision=initial_revision,
        state_revision=revision,
        audience_context_id=audience_context_id,
        audience_context_disposition=audience_disposition,
        snapshot_series_id=snapshot_series_id,
        snapshot_series_disposition=series_disposition,
        snapshot_build_request_id=request.snapshot_build_request_id,
        snapshot_build_request_disposition=request_result.disposition,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_plan_disposition=plan_result.disposition,
        request_idempotency_key=idempotency_key,
    )


def _verify_copied_entry_provider_commitments(
    workspace_root: str | Path,
    plan: SnapshotBuildPlan,
    source_providers: SnapshotSourceProviderRegistry,
) -> None:
    copied = tuple(
        entry
        for entry in plan.entry_plans
        if entry.materialization_kind == "copied_source"
    )
    if not copied:
        return
    try:
        _current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Exact Profile state is unavailable for provider-plan verification.",
            stage="attempt_preflight",
            snapshot_series_id=plan.snapshot_series_id,
            snapshot_build_request_id=plan.snapshot_build_request_id,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
        ) from error
    profiles = tuple(
        item
        for item in records
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == plan.profile_revision
    )
    if len(profiles) != 1:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Exact Profile Revision does not resolve for provider-plan verification.",
            stage="attempt_preflight",
            snapshot_series_id=plan.snapshot_series_id,
            snapshot_build_request_id=plan.snapshot_build_request_id,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
        )
    section_orders = {item.section_id: item.order for item in profiles[0].sections}
    for entry in copied:
        artifact = entry.source_artifact
        section_order = section_orders.get(entry.section_id)
        placement_id = entry.placement_id
        selection_id = entry.selection_id
        candidate_id = entry.candidate_id
        candidate_evaluation_id = entry.candidate_evaluation_id
        source_publication_id = entry.source_publication_id
        producer_module_id = entry.producer_module_id
        projection_kind = entry.projection_kind
        projection_contract_version = entry.projection_contract_version
        if (
            artifact is None
            or section_order is None
            or placement_id is None
            or selection_id is None
            or candidate_id is None
            or candidate_evaluation_id is None
            or source_publication_id is None
            or producer_module_id is None
            or projection_kind is None
            or projection_contract_version is None
        ):
            raise _execution_error(
                "current_portfolio_build.canonical_result_invalid",
                "Copied Entry Plan is incomplete for provider-plan verification.",
                stage="attempt_preflight",
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
            )
        try:
            provider = source_providers.select(entry)
        except SnapshotMaterializationError as error:
            raise _execution_error(
                "current_portfolio_build.materialization_failed",
                "Exact planned Snapshot source provider is unavailable.",
                stage="attempt_preflight",
                underlying_code=error.code,
                underlying_stage=error.stage,
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
                next_safe_action="review_current_portfolio_preparation",
            ) from error
        semantic = {
            "contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
            "portfolio_id": plan.portfolio_id,
            "portfolio_subject_id": plan.portfolio_subject_id,
            "profile_binding_id": plan.profile_binding_id,
            "profile_revision_id": plan.profile_revision.portfolio_profile_id,
            "profile_revision_number": plan.profile_revision.profile_revision,
            "composition_revision": plan.composition_revision,
            "section_id": entry.section_id,
            "section_order": section_order,
            "position_in_section": entry.ordinal,
            "placement_id": placement_id,
            "selection_id": selection_id,
            "candidate_id": candidate_id,
            "candidate_evaluation_id": candidate_evaluation_id,
            "source_publication_id": source_publication_id,
            "producer_module_id": producer_module_id,
            "projection_kind": projection_kind,
            "projection_contract_version": projection_contract_version,
            "source_artifact": {
                "artifact_id": artifact.artifact_id,
                "artifact_kind": artifact.artifact_kind,
                "representation_kind": artifact.representation_kind,
                "media_type": artifact.media_type,
                "source_locator": artifact.source_locator,
                "native_revision": artifact.native_revision,
                "source_digest": (
                    None
                    if artifact.source_digest is None
                    else {
                        "algorithm": artifact.source_digest.algorithm,
                        "value": artifact.source_digest.value,
                    }
                ),
                "byte_size": artifact.byte_size,
                "language": artifact.language,
                "accessibility_relationship": artifact.accessibility_relationship,
            },
        }
        value = {
            "semantic": semantic,
            "materialization_kind": "copied_source",
            "provider_disposition": "exact_provider",
            "provider_id": provider.descriptor.provider_id,
            "provider_version": provider.descriptor.provider_version,
            "permitted_omission_reason": None,
        }
        encoded = json.dumps(
            {"domain": "vitrine_current_portfolio_entry_plan_v1", "value": value},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        expected_id = f"entry_plan_{hashlib.sha256(encoded).hexdigest()}"
        if expected_id != entry.entry_plan_id:
            raise _execution_error(
                "current_portfolio_build.materialization_failed",
                "Configured Snapshot source provider differs from immutable planning.",
                stage="attempt_preflight",
                underlying_code="snapshot.source_provider_conflict",
                underlying_stage="provider_selection",
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
                next_safe_action="review_current_portfolio_preparation",
            )


def _completion_context(
    workspace_root: str | Path,
    plan_execution: CurrentPortfolioPlanExecutionResult,
) -> tuple[
    SnapshotBuildPlan, SnapshotRendererRegistry, tuple[str, ...]
]:
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Canonical Snapshot Plan state is unavailable for execution.",
            stage="attempt_preflight",
            snapshot_series_id=plan_execution.snapshot_series_id,
            snapshot_build_request_id=plan_execution.snapshot_build_request_id,
            snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
        ) from error
    if current.state_revision != plan_execution.state_revision:
        raise _execution_error(
            "current_portfolio_build.execution_state_conflict",
            "Vitrine state changed after immutable Current Portfolio planning.",
            stage="attempt_preflight",
            snapshot_series_id=plan_execution.snapshot_series_id,
            snapshot_build_request_id=plan_execution.snapshot_build_request_id,
            snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
            next_safe_action="review_current_snapshot_state",
        )
    plans = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == plan_execution.snapshot_build_plan_id
    )
    if len(plans) != 1:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Immutable Snapshot Build Plan does not resolve uniquely.",
            stage="attempt_preflight",
            snapshot_series_id=plan_execution.snapshot_series_id,
            snapshot_build_request_id=plan_execution.snapshot_build_request_id,
            snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
        )
    plan = plans[0]
    if (
        plan.snapshot_series_id != plan_execution.snapshot_series_id
        or plan.snapshot_build_request_id
        != plan_execution.snapshot_build_request_id
    ):
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "Immutable Snapshot Build Plan differs from the task result chain.",
            stage="attempt_preflight",
            snapshot_series_id=plan_execution.snapshot_series_id,
            snapshot_build_request_id=plan_execution.snapshot_build_request_id,
            snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
        )
    existing_attempt_ids = tuple(
        item.snapshot_build_attempt_id
        for item in records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_plan_id == plan.snapshot_build_plan_id
    )

    generated = tuple(
        entry
        for entry in plan.entry_plans
        if entry.materialization_kind == "generated_vitrine"
    )
    if not generated:
        return plan, SnapshotRendererRegistry(), existing_attempt_ids

    reflection_keys: list[tuple[str, int]] = []
    for entry in generated:
        if (
            entry.renderer_id != CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID
            or entry.renderer_version
            != CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION
            or entry.renderer_contract_version
            != CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
            or len(entry.input_references) != 1
        ):
            raise _execution_error(
                "current_portfolio_build.canonical_result_invalid",
                "First-party Build Plan contains unsupported generated content.",
                stage="attempt_preflight",
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
            )
        reference = entry.input_references[0]
        if (
            reference.record_type != "portfolio_reflection"
            or reference.record_revision is None
        ):
            raise _execution_error(
                "current_portfolio_build.canonical_result_invalid",
                "First-party generated content is not an exact Reflection revision.",
                stage="attempt_preflight",
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
            )
        reflection_keys.append((reference.record_id, reference.record_revision))

    reflections: list[PortfolioReflection] = []
    seen_reflections: set[tuple[str, int]] = set()
    for reflection_id, reflection_revision in reflection_keys:
        key = (reflection_id, reflection_revision)
        if key in seen_reflections:
            continue
        seen_reflections.add(key)
        matches = tuple(
            item
            for item in records
            if isinstance(item, PortfolioReflection)
            and item.reflection_id == reflection_id
            and item.reflection_revision == reflection_revision
        )
        if len(matches) != 1:
            raise _execution_error(
                "current_portfolio_build.canonical_result_invalid",
                "Exact frozen Portfolio Reflection revision is unavailable.",
                stage="attempt_preflight",
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_request_id=plan.snapshot_build_request_id,
                snapshot_build_plan_id=plan.snapshot_build_plan_id,
            )
        reflections.append(matches[0])
    renderer = CurrentPortfolioReflectionRenderer(tuple(reflections))
    return plan, SnapshotRendererRegistry((renderer,)), existing_attempt_ids


def _recover_started_attempt_id(
    workspace_root: str | Path,
    snapshot_build_plan_id: str,
    previous_attempt_ids: tuple[str, ...],
) -> str | None:
    try:
        _current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError):
        return None
    previous = set(previous_attempt_ids)
    candidates = tuple(
        item.snapshot_build_attempt_id
        for item in records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_plan_id == snapshot_build_plan_id
        and item.snapshot_build_attempt_id not in previous
    )
    if len(candidates) != 1:
        return None
    return candidates[0]


def _recover_post_seal_edition_number(
    workspace_root: str | Path, snapshot_series_id: str
) -> int | None:
    try:
        _current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError):
        return None
    proven = {
        item.snapshot_edition
        for item in records
        if isinstance(item, SnapshotEditionBuildProvenance)
    }
    candidates = tuple(
        item
        for item in records
        if isinstance(item, SnapshotEdition)
        and item.snapshot_series_id == snapshot_series_id
        and item.reference not in proven
    )
    if len(candidates) != 1:
        return None
    return candidates[0].edition_number


def _completion_snapshot_error(
    error: SnapshotWorkflowError,
    *,
    stage: str,
    plan_execution: CurrentPortfolioPlanExecutionResult,
    attempt_id: str | None,
    edition_number: int | None = None,
) -> CurrentPortfolioExecutionError:
    cause = error.__cause__
    if isinstance(cause, SnapshotMaterializationError):
        underlying_code = cause.code
        underlying_stage = cause.stage
    else:
        underlying_code = error.code
        underlying_stage = error.stage
    producer_denied = (
        underlying_stage is not None
        and underlying_stage.endswith("_artifact_authorization_denied")
    )
    producer_unresolved = (
        underlying_stage is not None
        and underlying_stage.endswith("_artifact_authorization_unresolved")
    )
    if error.code == "snapshot.state_conflict":
        code = "current_portfolio_build.execution_state_conflict"
    elif error.code == "snapshot.authority_denied":
        code = "current_portfolio_build.snapshot_authority_denied"
    elif error.code == "snapshot.authority_unresolved":
        code = "current_portfolio_build.snapshot_authority_unresolved"
    elif producer_denied:
        code = "current_portfolio_build.producer_artifact_authorization_denied"
    elif producer_unresolved:
        code = "current_portfolio_build.producer_artifact_authorization_unresolved"
    elif stage == "attempt_start":
        code = "current_portfolio_build.attempt_start_failed"
    elif stage == "attempt_execution":
        code = "current_portfolio_build.materialization_failed"
    else:
        code = "current_portfolio_build.sealing_failed"

    recovery_codes = {
        "snapshot.attempt_conflict",
        "snapshot.build_lock_conflict",
        "snapshot.build_lock_invalid",
        "snapshot.build_lock_missing",
        "snapshot.durability_uncertain",
        "snapshot.seal_conflict",
        "snapshot.staging_conflict",
        "snapshot.staging_invalid",
    }
    if edition_number is not None or error.code == "snapshot.post_seal_state_conflict":
        next_action = "inspect_post_seal_recovery"
    elif error.code in recovery_codes or (
        error.code == "snapshot.state_conflict" and attempt_id is not None
    ):
        next_action = "inspect_snapshot_recovery"
    elif code in {
        "current_portfolio_build.snapshot_authority_denied",
        "current_portfolio_build.snapshot_authority_unresolved",
    }:
        next_action = "review_snapshot_build_authority"
    elif code in {
        "current_portfolio_build.producer_artifact_authorization_denied",
        "current_portfolio_build.producer_artifact_authorization_unresolved",
    }:
        next_action = "review_producer_artifact_authorization"
    elif stage == "attempt_execution":
        next_action = "review_failed_attempt_and_planned_source"
    else:
        next_action = "review_current_snapshot_state"
    completed = [
        "audience_context",
        "snapshot_series",
        "build_request",
        "build_plan",
    ]
    if attempt_id is not None:
        completed.append("build_attempt")
    if error.code == "snapshot.post_seal_state_conflict":
        completed.append("snapshot_edition_sealed")
    return _execution_error(
        code,
        f"Current Portfolio execution failed during {stage.replace('_', ' ')}.",
        stage=stage,
        underlying_code=underlying_code,
        underlying_stage=underlying_stage,
        completed_stages=tuple(completed),
        audience_context_id=plan_execution.audience_context_id,
        snapshot_series_id=plan_execution.snapshot_series_id,
        snapshot_build_request_id=plan_execution.snapshot_build_request_id,
        snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt_id,
        edition_number=edition_number,
        next_safe_action=next_action,
    )


def _completion_distribution_error(
    error: SnapshotDistributionError,
    *,
    stage: str,
    plan_execution: CurrentPortfolioPlanExecutionResult | None = None,
    snapshot_series_id: str,
    edition_number: int,
    attempt_id: str | None = None,
    export_artifact_id: str | None = None,
) -> CurrentPortfolioExecutionError:
    if error.code == "snapshot_distribution.state_conflict":
        code = "current_portfolio_build.execution_state_conflict"
    elif stage == "edition_verification":
        code = "current_portfolio_build.edition_verification_failed"
    elif stage == "export_verification":
        code = "current_portfolio_build.export_verification_failed"
    else:
        code = "current_portfolio_build.export_failed"
    if plan_execution is None:
        completed = ["snapshot_edition"]
    else:
        completed = [
            "audience_context",
            "snapshot_series",
            "build_request",
            "build_plan",
            "build_attempt",
            "snapshot_edition",
        ]
    if stage in {"export", "export_verification"}:
        completed.append("edition_verification")
    if export_artifact_id is not None:
        completed.append("snapshot_export_artifact")
    if stage in {"edition_verification", "export_verification"}:
        next_action = "inspect_snapshot_custody"
    elif error.code in {
        "snapshot_distribution.durability_uncertain",
        "snapshot_distribution.export_conflict",
        "snapshot_distribution.export_failed",
    }:
        next_action = "inspect_snapshot_custody_then_resume_export"
    else:
        next_action = "resume_export_existing_edition"
    return _execution_error(
        code,
        f"Current Portfolio execution failed during {stage.replace('_', ' ')}.",
        stage=stage,
        underlying_code=error.code,
        underlying_stage=error.stage,
        completed_stages=tuple(completed),
        audience_context_id=(
            None if plan_execution is None else plan_execution.audience_context_id
        ),
        snapshot_series_id=snapshot_series_id,
        snapshot_build_request_id=(
            None
            if plan_execution is None
            else plan_execution.snapshot_build_request_id
        ),
        snapshot_build_plan_id=(
            None
            if plan_execution is None
            else plan_execution.snapshot_build_plan_id
        ),
        snapshot_build_attempt_id=attempt_id,
        edition_number=edition_number,
        snapshot_export_artifact_id=export_artifact_id,
        next_safe_action=next_action,
    )


def execute_current_portfolio_build_export(
    workspace_root: str | Path,
    plan_execution: CurrentPortfolioPlanExecutionResult,
    *,
    actor: ActorAttribution,
    authority_gate: SnapshotBuildAuthorityGate,
    source_providers: SnapshotSourceProviderRegistry | None = None,
) -> CurrentPortfolioBuildExportResult:
    """Build, seal, verify, and export one exact immutable first-party Plan.

    This boundary begins only after Slice-4 prepared execution froze the exact
    Snapshot Build Plan. It never reparses or refreshes Working Composition state,
    never follows successor sources, and never advances the current Edition pointer.
    """

    if not isinstance(plan_execution, CurrentPortfolioPlanExecutionResult):
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Current Portfolio completion requires an exact Plan execution result.",
            stage="attempt_preflight",
        )
    if not isinstance(actor, ActorAttribution):
        raise _execution_error(
            "current_portfolio_build.invalid_preparation",
            "Current Portfolio completion requires exact actor attribution.",
            stage="attempt_preflight",
        )
    providers = source_providers or SnapshotSourceProviderRegistry()
    plan, renderers, existing_attempt_ids = _completion_context(
        workspace_root, plan_execution
    )
    _verify_copied_entry_provider_commitments(workspace_root, plan, providers)

    try:
        started = start_snapshot_build_attempt(
            workspace_root,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
            started_by=actor,
            expected_state_revision=plan_execution.state_revision,
        )
    except SnapshotWorkflowError as error:
        recovered_attempt_id = _recover_started_attempt_id(
            workspace_root,
            plan.snapshot_build_plan_id,
            existing_attempt_ids,
        )
        raise _completion_snapshot_error(
            error,
            stage="attempt_start",
            plan_execution=plan_execution,
            attempt_id=recovered_attempt_id,
        ) from error

    attempt_id = started.attempt.snapshot_build_attempt_id
    try:
        executed = execute_snapshot_build_attempt(
            workspace_root,
            snapshot_build_attempt_id=attempt_id,
            expected_state_revision=started.state_revision,
            authority_gate=authority_gate,
            source_providers=providers,
            renderers=renderers,
        )
    except SnapshotWorkflowError as error:
        raise _completion_snapshot_error(
            error,
            stage="attempt_execution",
            plan_execution=plan_execution,
            attempt_id=attempt_id,
        ) from error

    try:
        sealed = seal_snapshot_build_attempt(
            workspace_root,
            execution=executed,
            expected_state_revision=executed.state_revision,
            sealed_by=actor,
        )
    except SnapshotWorkflowError as error:
        recovered_edition = None
        if error.code == "snapshot.post_seal_state_conflict":
            recovered_edition = _recover_post_seal_edition_number(
                workspace_root, plan.snapshot_series_id
            )
        raise _completion_snapshot_error(
            error,
            stage="sealing",
            plan_execution=plan_execution,
            attempt_id=attempt_id,
            edition_number=recovered_edition,
        ) from error

    edition_number = sealed.edition.edition_number
    try:
        edition_verification = verify_snapshot_edition(
            workspace_root,
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=edition_number,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="edition_verification",
            plan_execution=plan_execution,
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=edition_number,
            attempt_id=attempt_id,
        ) from error

    if len(plan.export_plans) != 1:
        raise _execution_error(
            "current_portfolio_build.canonical_result_invalid",
            "First-party Build Plan must contain one exact directory Export Plan.",
            stage="export",
            audience_context_id=plan_execution.audience_context_id,
            snapshot_series_id=plan.snapshot_series_id,
            snapshot_build_request_id=plan.snapshot_build_request_id,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
            snapshot_build_attempt_id=attempt_id,
            edition_number=edition_number,
            next_safe_action="resume_export_existing_edition",
        )
    export_plan = plan.export_plans[0]
    try:
        export_result = create_snapshot_directory_export(
            workspace_root,
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=edition_number,
            export_plan_id=export_plan.export_plan_id,
            expected_state_revision=sealed.state_revision,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="export",
            plan_execution=plan_execution,
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=edition_number,
            attempt_id=attempt_id,
        ) from error
    export_disposition = (
        "existing"
        if export_result.state_revision == sealed.state_revision
        else "created"
    )
    artifact_id = export_result.export_artifact.snapshot_export_artifact_id
    try:
        export_verification = verify_snapshot_export(
            workspace_root,
            snapshot_export_artifact_id=artifact_id,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="export_verification",
            plan_execution=plan_execution,
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=edition_number,
            attempt_id=attempt_id,
            export_artifact_id=artifact_id,
        ) from error

    return CurrentPortfolioBuildExportResult(
        contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        preparation_fingerprint=plan_execution.preparation_fingerprint,
        state_revision=export_result.state_revision,
        audience_context_id=plan_execution.audience_context_id,
        snapshot_series_id=plan.snapshot_series_id,
        snapshot_build_request_id=plan.snapshot_build_request_id,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt_id,
        attempt_number=started.attempt.attempt_number,
        attempt_terminal_outcome=sealed.attempt_result.terminal_outcome,
        edition_number=edition_number,
        edition_manifest_sha256=edition_verification.manifest_digest.value,
        edition_logical_inventory_sha256=(
            edition_verification.logical_inventory_digest.value
        ),
        snapshot_export_artifact_id=artifact_id,
        export_disposition=export_disposition,
        export_directory_inventory_sha256=(
            export_verification.directory_inventory_digest.value
        ),
        export_path=export_result.export_path,
        current_pointer_advanced=False,
    )


def execute_prepared_current_portfolio_build(
    workspace_root: str | Path,
    preparation: CurrentPortfolioBuildPreparation,
    *,
    actor: ActorAttribution,
    authority_gate: SnapshotBuildAuthorityGate,
    source_providers: SnapshotSourceProviderRegistry | None = None,
) -> CurrentPortfolioBuildExportResult:
    """Execute the exact reviewed Current Portfolio preparation end to end."""

    providers = source_providers or SnapshotSourceProviderRegistry()
    plan_execution = execute_prepared_current_portfolio_plan(
        workspace_root,
        preparation,
        actor=actor,
        source_providers=providers,
    )
    return execute_current_portfolio_build_export(
        workspace_root,
        plan_execution,
        actor=actor,
        authority_gate=authority_gate,
        source_providers=providers,
    )


def resume_current_portfolio_export(
    workspace_root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    export_plan_id: str,
    expected_state_revision: int,
) -> CurrentPortfolioExportResumeResult:
    """Verify and create/reuse the exact Export for one already sealed Edition."""

    if expected_state_revision <= 0 or edition_number <= 0:
        raise _execution_error(
            "current_portfolio_build.resume_invalid",
            "Current Portfolio Export resume requires exact positive revisions.",
            stage="export_resume",
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        )
    try:
        verify_snapshot_edition(
            workspace_root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="edition_verification",
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        ) from error
    try:
        export_result = create_snapshot_directory_export(
            workspace_root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            export_plan_id=export_plan_id,
            expected_state_revision=expected_state_revision,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="export",
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        ) from error
    disposition = (
        "existing"
        if export_result.state_revision == expected_state_revision
        else "created"
    )
    artifact_id = export_result.export_artifact.snapshot_export_artifact_id
    try:
        verification = verify_snapshot_export(
            workspace_root,
            snapshot_export_artifact_id=artifact_id,
        )
    except SnapshotDistributionError as error:
        raise _completion_distribution_error(
            error,
            stage="export_verification",
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            export_artifact_id=artifact_id,
        ) from error
    return CurrentPortfolioExportResumeResult(
        state_revision=export_result.state_revision,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
        snapshot_export_artifact_id=artifact_id,
        export_disposition=disposition,
        export_directory_inventory_sha256=(
            verification.directory_inventory_digest.value
        ),
        export_path=export_result.export_path,
    )


__all__ = [
    "CURRENT_PORTFOLIO_EXECUTION_ERROR_CODES",
    "CurrentPortfolioBuildExportResult",
    "CurrentPortfolioExecutionError",
    "CurrentPortfolioExportResumeResult",
    "CurrentPortfolioPlanExecutionResult",
    "execute_current_portfolio_build_export",
    "execute_prepared_current_portfolio_build",
    "execute_prepared_current_portfolio_plan",
    "resume_current_portfolio_export",
]
