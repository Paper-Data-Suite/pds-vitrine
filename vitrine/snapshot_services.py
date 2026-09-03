"""Guarded services for immutable Snapshot planning, execution, and sealing."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, TypeVar

from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    CandidateEvaluation,
    DigestReference,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileBinding,
    PortfolioProfileRevision,
    PortfolioSelection,
    SectionArrangementRevision,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildFinding,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEdition,
    SnapshotEditionBuildProvenance,
    SnapshotEditionRef,
    SnapshotEntry,
    SnapshotEntryOutcome,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotManifest,
    SnapshotMaterializationProvenance,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
    SnapshotSeries,
    VitrineRecord,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.common import (
    lower_key_tuple,
    require_aware_datetime,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_text,
)
from vitrine.models.conversion import JsonValue
from vitrine.models.errors import VitrineModelValidationError
from vitrine.snapshot_custody import (
    SNAPSHOT_DIGEST_POLICY_ID,
    SNAPSHOT_PATH_POLICY_ID,
    SnapshotCustodyError,
    SnapshotStagingArea,
    acquire_snapshot_series_lock,
    create_snapshot_staging,
    inspect_snapshot_series_lock,
    load_snapshot_staging,
    publish_snapshot_staging_as_edition,
    read_staging_content_bytes,
    read_staging_internal_bytes,
    release_snapshot_series_lock,
    require_empty_snapshot_staging,
    staging_content_inventory,
    validate_snapshot_path_inventory,
    write_staging_internal_bytes_exclusive,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_BUILD_OPERATION,
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityGate,
    SnapshotBuildAuthorityRequest,
    SnapshotCopiedBytesResult,
    SnapshotGeneratedBytesResult,
    SnapshotMaterializationError,
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
    copy_planned_source_to_staging,
    render_planned_entry_to_staging,
)
from vitrine.snapshot_sealing import (
    SNAPSHOT_INTERNAL_MANIFEST_CONTRACT_VERSION,
    SNAPSHOT_LOGICAL_INVENTORY_CONTRACT_VERSION,
    canonical_snapshot_json_bytes,
    snapshot_digest,
    snapshot_logical_inventory_digest,
    snapshot_manifest_digest,
)
from vitrine.snapshot_state import (
    collect_snapshot_state_issues,
    project_snapshot_state,
    snapshot_plan_fingerprint,
)
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageNotFoundError,
    VitrineStoragePartialSuccessError,
    _commit_prevalidated_snapshot_batch,
    load_current_records_with_state,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]
T = TypeVar("T")

SNAPSHOT_BUILDER_CONTRACT_ID: Final[str] = "vitrine_snapshot_builder"
SNAPSHOT_BUILDER_CONTRACT_VERSION: Final[str] = "1"

SNAPSHOT_SERVICE_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot.invalid_request",
        "snapshot.context_not_found",
        "snapshot.state_conflict",
        "snapshot.state_invalid",
        "snapshot.durability_uncertain",
        "snapshot.series_not_found",
        "snapshot.series_context_mismatch",
        "snapshot.request_not_found",
        "snapshot.request_conflict",
        "snapshot.composition_mismatch",
        "snapshot.audience_context_mismatch",
        "snapshot.plan_conflict",
        "snapshot.plan_source_mismatch",
        "snapshot.plan_order_invalid",
        "snapshot.plan_inventory_incomplete",
        "snapshot.plan_review_mismatch",
        "snapshot.plan_audience_prohibited",
        "snapshot.attempt_conflict",
        "snapshot.attempt_not_found",
        "snapshot.build_lock_conflict",
        "snapshot.build_lock_invalid",
        "snapshot.build_lock_missing",
        "snapshot.build_lock_write_failed",
        "snapshot.authority_denied",
        "snapshot.authority_unresolved",
        "snapshot.materialization_failed",
        "snapshot.final_verification_failed",
        "snapshot.seal_conflict",
        "snapshot.post_seal_state_conflict",
        "snapshot.staging_conflict",
        "snapshot.staging_invalid",
    }
)

_SOURCE_CONTENT_CLASS_BY_ARTIFACT_KIND: Final[dict[str, str]] = {
    "assessment_summary": "assessment_summary",
    "collaborative_artifact": "student_work",
    "original_student_work": "student_work",
    "rendered_feedback": "feedback",
}


class SnapshotWorkflowError(RuntimeError):
    """Expected Snapshot orchestration failure with a stable privacy-safe code."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in SNAPSHOT_SERVICE_CODES:
            raise ValueError(f"unsupported Snapshot workflow code: {code}")
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotMutationResult:
    state_revision: int
    records: tuple[VitrineRecord, ...]
    disposition: str

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        object.__setattr__(self, "records", tuple(self.records))
        if self.disposition not in {"created", "existing"}:
            raise ValueError("unsupported Snapshot mutation disposition.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotAttemptStartResult:
    state_revision: int
    attempt: SnapshotBuildAttempt
    staging_root: Path

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.attempt, SnapshotBuildAttempt):
            raise ValueError("attempt must be SnapshotBuildAttempt.")
        if not isinstance(self.staging_root, Path):
            raise ValueError("staging_root must be pathlib.Path.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotPreparedEntry:
    """One pre-seal Entry disposition produced by successful Attempt execution."""

    entry_plan_id: str
    disposition: str
    copied_bytes: SnapshotCopiedBytesResult | None = None
    generated_bytes: SnapshotGeneratedBytesResult | None = None
    pending_omission_reason: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.entry_plan_id, "entry_plan_id")
        if self.disposition not in {
            "prepared_bytes",
            "reference_only",
            "omission_pending",
        }:
            raise ValueError("unsupported prepared Snapshot Entry disposition.")
        byte_results = int(self.copied_bytes is not None) + int(
            self.generated_bytes is not None
        )
        if self.disposition == "prepared_bytes":
            if byte_results != 1 or self.pending_omission_reason is not None:
                raise ValueError(
                    "prepared_bytes requires exactly one byte result and no omission."
                )
        elif self.disposition == "omission_pending":
            if byte_results != 0 or self.pending_omission_reason is None:
                raise ValueError(
                    "omission_pending requires one planned omission reason and no bytes."
                )
        elif byte_results != 0 or self.pending_omission_reason is not None:
            raise ValueError(
                "reference_only must not carry bytes or an omission reason."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotAttemptExecutionResult:
    """Noncanonical prepared state consumed by the later sealing boundary."""

    state_revision: int
    attempt: SnapshotBuildAttempt
    plan: SnapshotBuildPlan
    staging_root: Path
    authority_reference: str
    entries: tuple[SnapshotPreparedEntry, ...]

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.attempt, SnapshotBuildAttempt):
            raise ValueError("attempt must be SnapshotBuildAttempt.")
        if not isinstance(self.plan, SnapshotBuildPlan):
            raise ValueError("plan must be SnapshotBuildPlan.")
        if self.attempt.snapshot_build_plan_id != self.plan.snapshot_build_plan_id:
            raise ValueError("attempt and plan must match.")
        if not isinstance(self.staging_root, Path):
            raise ValueError("staging_root must be pathlib.Path.")
        require_text(self.authority_reference, "authority_reference", maximum=500)
        object.__setattr__(self, "entries", tuple(self.entries))
        expected = tuple(item.entry_plan_id for item in self.plan.entry_plans)
        actual = tuple(item.entry_plan_id for item in self.entries)
        if actual != expected:
            raise ValueError(
                "prepared Snapshot Entry results must preserve exact Plan order."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSealResult:
    state_revision: int
    edition: SnapshotEdition
    manifest: SnapshotManifest
    seal: SnapshotSeal
    attempt_result: SnapshotBuildAttemptResult
    edition_path: Path | None

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.edition, SnapshotEdition):
            raise ValueError("edition must be SnapshotEdition.")
        if not isinstance(self.manifest, SnapshotManifest):
            raise ValueError("manifest must be SnapshotManifest.")
        if not isinstance(self.seal, SnapshotSeal):
            raise ValueError("seal must be SnapshotSeal.")
        if not isinstance(self.attempt_result, SnapshotBuildAttemptResult):
            raise ValueError("attempt_result must be SnapshotBuildAttemptResult.")
        if self.edition.reference != self.seal.snapshot_edition:
            raise ValueError("seal and Edition identity must match.")
        if self.edition.reference != self.manifest.snapshot_edition:
            raise ValueError("manifest and Edition identity must match.")
        if self.edition_path is not None and not isinstance(self.edition_path, Path):
            raise ValueError("edition_path must be pathlib.Path or null.")


class _ApprovedAuthorityGate:
    """Internal gate that reuses one already-approved external build decision."""

    def __init__(self, decision: SnapshotBuildAuthorityDecision) -> None:
        self._decision = decision

    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        return self._decision


_PERMITTED_OMISSION_BY_FAILURE: Final[dict[str, str]] = {
    "snapshot.source_unavailable": "source_unavailable",
    "snapshot.source_provider_missing": "representation_unavailable",
    "snapshot.renderer_missing": "representation_unavailable",
    "snapshot.render_failed": "representation_unavailable",
}


@dataclass(frozen=True, slots=True)
class _LoadedState:
    records: tuple[VitrineRecord, ...]
    state_revision: int


@dataclass(frozen=True, slots=True)
class _BuildContext:
    series: SnapshotSeries
    request: SnapshotBuildRequest
    portfolio: Portfolio
    binding: PortfolioProfileBinding
    profile: PortfolioProfileRevision
    composition: WorkingPortfolioCompositionRevision
    inventory: WorkingPortfolioCompositionInventory
    audience: AudienceContext


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now(clock: Clock) -> datetime:
    try:
        return require_aware_datetime(clock(), "clock").astimezone(timezone.utc)
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot clock must return an aware datetime.",
            stage="clock",
        ) from error


def _load_state(
    workspace_root: str | Path, expected_state_revision: int
) -> _LoadedState:
    try:
        expected = require_positive_int(
            expected_state_revision, "expected_state_revision"
        )
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot expected state revision is invalid.",
            stage="request",
        ) from error
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise SnapshotWorkflowError(
            "snapshot.context_not_found",
            "Vitrine canonical state is unavailable.",
            stage="load",
        ) from error
    if current.state_revision != expected:
        raise SnapshotWorkflowError(
            "snapshot.state_conflict",
            "Vitrine canonical state changed before the Snapshot operation.",
            stage="concurrency",
        )
    return _LoadedState(records=records, state_revision=current.state_revision)


def _commit(
    workspace_root: str | Path,
    records: tuple[VitrineRecord, ...],
    expected_state_revision: int,
    *,
    current_records: tuple[VitrineRecord, ...],
) -> int:
    """Validate one complete Snapshot transition, then use canonical storage."""

    combined = (*current_records, *records)
    issues = collect_snapshot_state_issues(project_snapshot_state(combined))
    if issues:
        raise SnapshotWorkflowError(
            "snapshot.state_invalid",
            f"Snapshot transition is invalid ({issues[0].code}).",
            stage="validation",
        )
    try:
        result = _commit_prevalidated_snapshot_batch(
            workspace_root,
            records,
            expected_state_revision=expected_state_revision,
        )
    except VitrineStoragePartialSuccessError as error:
        raise SnapshotWorkflowError(
            "snapshot.durability_uncertain",
            "Snapshot canonical persistence has uncertain durability and requires explicit recovery.",
            stage="durability",
        ) from error
    except VitrineStorageConflictError as error:
        raise SnapshotWorkflowError(
            "snapshot.state_conflict",
            "Vitrine canonical state changed before the Snapshot mutation committed.",
            stage="concurrency",
        ) from error
    except VitrineStorageError as error:
        raise SnapshotWorkflowError(
            "snapshot.context_not_found",
            "Snapshot canonical persistence failed.",
            stage="persistence",
        ) from error
    return result.state_revision


def _one(values: tuple[T, ...], *, code: str, message: str, stage: str) -> T:
    if len(values) != 1:
        raise SnapshotWorkflowError(code, message, stage=stage)
    return values[0]


def _series(records: tuple[VitrineRecord, ...], series_id: str) -> SnapshotSeries:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotSeries) and item.snapshot_series_id == series_id
    )
    return _one(
        values,
        code="snapshot.series_not_found",
        message="Snapshot Series does not resolve uniquely.",
        stage="series",
    )


def _request(records: tuple[VitrineRecord, ...], request_id: str) -> SnapshotBuildRequest:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildRequest)
        and item.snapshot_build_request_id == request_id
    )
    return _one(
        values,
        code="snapshot.request_not_found",
        message="Snapshot Build Request does not resolve uniquely.",
        stage="request",
    )


def _plan(records: tuple[VitrineRecord, ...], plan_id: str) -> SnapshotBuildPlan:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildPlan) and item.snapshot_build_plan_id == plan_id
    )
    return _one(
        values,
        code="snapshot.plan_conflict",
        message="Snapshot Build Plan does not resolve uniquely.",
        stage="plan",
    )


def _build_context(
    records: tuple[VitrineRecord, ...], request: SnapshotBuildRequest
) -> _BuildContext:
    series = _series(records, request.snapshot_series_id)
    portfolio_values = tuple(
        item
        for item in records
        if isinstance(item, Portfolio) and item.portfolio_id == request.portfolio_id
    )
    portfolio = _one(
        portfolio_values,
        code="snapshot.context_not_found",
        message="Snapshot Portfolio does not resolve uniquely.",
        stage="context",
    )
    assert isinstance(portfolio, Portfolio)
    binding_values = tuple(
        item
        for item in records
        if isinstance(item, PortfolioProfileBinding)
        and item.profile_binding_id == request.profile_binding_id
    )
    binding = _one(
        binding_values,
        code="snapshot.context_not_found",
        message="Snapshot Profile Binding does not resolve uniquely.",
        stage="context",
    )
    assert isinstance(binding, PortfolioProfileBinding)
    profile_values = tuple(
        item
        for item in records
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == request.profile_revision
    )
    profile = _one(
        profile_values,
        code="snapshot.context_not_found",
        message="Snapshot Profile Revision does not resolve uniquely.",
        stage="context",
    )
    assert isinstance(profile, PortfolioProfileRevision)
    composition_values = tuple(
        item
        for item in records
        if isinstance(item, WorkingPortfolioCompositionRevision)
        and item.portfolio_id == request.portfolio_id
        and item.composition_revision == request.composition_revision
    )
    composition = _one(
        composition_values,
        code="snapshot.composition_mismatch",
        message="Exact Snapshot Composition Revision does not resolve uniquely.",
        stage="composition",
    )
    assert isinstance(composition, WorkingPortfolioCompositionRevision)
    inventory_values = tuple(
        item
        for item in records
        if isinstance(item, WorkingPortfolioCompositionInventory)
        and item.portfolio_id == request.portfolio_id
        and item.composition_revision == request.composition_revision
    )
    inventory = _one(
        inventory_values,
        code="snapshot.composition_mismatch",
        message="Exact Snapshot Composition Inventory does not resolve uniquely.",
        stage="composition",
    )
    assert isinstance(inventory, WorkingPortfolioCompositionInventory)
    audience_values = tuple(
        item
        for item in records
        if isinstance(item, AudienceContext)
        and item.audience_context_id == request.audience_context_id
    )
    audience = _one(
        audience_values,
        code="snapshot.audience_context_mismatch",
        message="Snapshot Audience Context does not resolve uniquely.",
        stage="audience",
    )
    assert isinstance(audience, AudienceContext)
    expected_context = (
        request.portfolio_id,
        request.portfolio_subject_id,
        request.profile_binding_id,
        request.profile_revision,
    )
    if (
        series.portfolio_id,
        series.portfolio_subject_id,
        request.profile_binding_id,
        request.profile_revision,
    ) != expected_context or series.audience_context_id != request.audience_context_id:
        raise SnapshotWorkflowError(
            "snapshot.series_context_mismatch",
            "Snapshot Series context does not match the Build Request.",
            stage="series",
        )
    if (portfolio.portfolio_id, portfolio.portfolio_subject_id) != (
        request.portfolio_id,
        request.portfolio_subject_id,
    ):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Portfolio context does not match the Build Request.",
            stage="context",
        )
    if binding.portfolio_id != request.portfolio_id or binding.profile_revision != request.profile_revision:
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Profile Binding does not match the Build Request.",
            stage="context",
        )
    if (
        composition.portfolio_subject_id,
        composition.profile_binding_id,
        composition.profile_revision,
    ) != (
        request.portfolio_subject_id,
        request.profile_binding_id,
        request.profile_revision,
    ):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition context does not match the Build Request.",
            stage="composition",
        )
    if (inventory.profile_binding_id, inventory.profile_revision) != (
        request.profile_binding_id,
        request.profile_revision,
    ):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition Inventory context does not match the Build Request.",
            stage="composition",
        )
    if (
        audience.portfolio_id,
        audience.portfolio_subject_id,
        audience.profile_binding_id,
        audience.profile_revision,
    ) != expected_context:
        raise SnapshotWorkflowError(
            "snapshot.audience_context_mismatch",
            "Snapshot Audience Context does not match the exact Composition context.",
            stage="audience",
        )
    if profile.reference != request.profile_revision:
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Profile Revision does not match the Build Request.",
            stage="context",
        )
    return _BuildContext(
        series=series,
        request=request,
        portfolio=portfolio,
        binding=binding,
        profile=profile,
        composition=composition,
        inventory=inventory,
        audience=audience,
    )


def create_snapshot_series(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    audience_context_id: str,
    snapshot_purpose: str,
    created_by: ActorAttribution,
    expected_state_revision: int,
    predecessor_series_id: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotMutationResult:
    """Create one explicit Snapshot Series; no matching/reuse is inferred."""

    try:
        portfolio_id = require_identifier(portfolio_id, "portfolio_id")
        audience_context_id = require_identifier(audience_context_id, "audience_context_id")
        snapshot_purpose = require_text(snapshot_purpose, "snapshot_purpose", maximum=500)
        predecessor_series_id = require_optional_text(
            predecessor_series_id, "predecessor_series_id", maximum=256
        )
        if not isinstance(created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot Series request is invalid.",
            stage="series",
        ) from error
    loaded = _load_state(workspace_root, expected_state_revision)
    portfolio_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
    )
    portfolio = _one(
        portfolio_values,
        code="snapshot.context_not_found",
        message="Snapshot Series Portfolio does not resolve uniquely.",
        stage="series",
    )
    assert isinstance(portfolio, Portfolio)
    audience_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, AudienceContext)
        and item.audience_context_id == audience_context_id
    )
    audience = _one(
        audience_values,
        code="snapshot.audience_context_mismatch",
        message="Snapshot Series Audience Context does not resolve uniquely.",
        stage="series",
    )
    assert isinstance(audience, AudienceContext)
    if (audience.portfolio_id, audience.portfolio_subject_id) != (
        portfolio.portfolio_id,
        portfolio.portfolio_subject_id,
    ):
        raise SnapshotWorkflowError(
            "snapshot.audience_context_mismatch",
            "Snapshot Series Audience Context belongs to another Portfolio.",
            stage="series",
        )
    if predecessor_series_id is not None:
        predecessor = _series(loaded.records, predecessor_series_id)
        if predecessor.snapshot_series_id == predecessor_series_id and predecessor.portfolio_id != portfolio_id:
            raise SnapshotWorkflowError(
                "snapshot.series_context_mismatch",
                "Snapshot predecessor Series belongs to another Portfolio.",
                stage="series",
            )
    series = SnapshotSeries(
        snapshot_series_id=id_factory("snapshot_series"),
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        snapshot_purpose=snapshot_purpose,
        audience_context_id=audience_context_id,
        created_at=_now(clock),
        created_by=created_by,
        predecessor_series_id=predecessor_series_id,
    )
    revision = _commit(
        workspace_root,
        (series,),
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )
    return SnapshotMutationResult(
        state_revision=revision, records=(series,), disposition="created"
    )


def _request_intent(request: SnapshotBuildRequest) -> tuple[object, ...]:
    return (
        request.snapshot_series_id,
        request.portfolio_id,
        request.portfolio_subject_id,
        request.profile_binding_id,
        request.profile_revision,
        request.composition_revision,
        request.audience_context_id,
        request.snapshot_purpose,
        request.requested_export_formats,
        request.requested_by,
        request.curation_review_decision_ids,
        request.predecessor_request_id,
    )


def request_snapshot_build(
    workspace_root: str | Path,
    *,
    snapshot_series_id: str,
    composition_revision: int,
    requested_by: ActorAttribution,
    expected_state_revision: int,
    idempotency_key: str | None = None,
    predecessor_request_id: str | None = None,
    requested_export_formats: tuple[str, ...] = ("directory_package",),
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotMutationResult:
    """Persist intent to build one exact Composition Revision for a Series."""

    try:
        snapshot_series_id = require_identifier(snapshot_series_id, "snapshot_series_id")
        composition_revision = require_positive_int(
            composition_revision, "composition_revision"
        )
        idempotency_key = require_optional_text(
            idempotency_key, "idempotency_key", maximum=256
        )
        predecessor_request_id = require_optional_text(
            predecessor_request_id, "predecessor_request_id", maximum=256
        )
        if not isinstance(requested_by, ActorAttribution):
            raise VitrineModelValidationError("requested_by must be ActorAttribution.")
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot Build Request is invalid.",
            stage="request",
        ) from error
    loaded = _load_state(workspace_root, expected_state_revision)
    series = _series(loaded.records, snapshot_series_id)
    composition_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
        and item.portfolio_id == series.portfolio_id
        and item.composition_revision == composition_revision
    )
    composition = _one(
        composition_values,
        code="snapshot.composition_mismatch",
        message="Exact Snapshot Composition Revision does not resolve uniquely.",
        stage="request",
    )
    assert isinstance(composition, WorkingPortfolioCompositionRevision)
    inventory_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
        and item.portfolio_id == series.portfolio_id
        and item.composition_revision == composition_revision
    )
    inventory = _one(
        inventory_values,
        code="snapshot.composition_mismatch",
        message="Exact Snapshot Composition Inventory does not resolve uniquely.",
        stage="request",
    )
    assert isinstance(inventory, WorkingPortfolioCompositionInventory)
    audience_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, AudienceContext)
        and item.audience_context_id == series.audience_context_id
    )
    audience = _one(
        audience_values,
        code="snapshot.audience_context_mismatch",
        message="Snapshot Series Audience Context does not resolve uniquely.",
        stage="request",
    )
    assert isinstance(audience, AudienceContext)
    if composition.portfolio_subject_id != series.portfolio_subject_id:
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition belongs to another Portfolio Subject.",
            stage="request",
        )
    if (inventory.profile_binding_id, inventory.profile_revision) != (
        composition.profile_binding_id,
        composition.profile_revision,
    ):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition Inventory does not match the Composition.",
            stage="request",
        )
    if (
        audience.portfolio_id,
        audience.portfolio_subject_id,
        audience.profile_binding_id,
        audience.profile_revision,
    ) != (
        composition.portfolio_id,
        composition.portfolio_subject_id,
        composition.profile_binding_id,
        composition.profile_revision,
    ):
        raise SnapshotWorkflowError(
            "snapshot.audience_context_mismatch",
            "Snapshot Audience Context does not match the exact Composition.",
            stage="request",
        )
    if predecessor_request_id is not None:
        predecessor = _request(loaded.records, predecessor_request_id)
        if predecessor.snapshot_series_id != snapshot_series_id:
            raise SnapshotWorkflowError(
                "snapshot.request_conflict",
                "Snapshot predecessor Request belongs to another Series.",
                stage="request",
            )
    provisional = SnapshotBuildRequest(
        snapshot_build_request_id="snapshot_request_provisional",
        snapshot_series_id=series.snapshot_series_id,
        portfolio_id=composition.portfolio_id,
        portfolio_subject_id=composition.portfolio_subject_id,
        profile_binding_id=composition.profile_binding_id,
        profile_revision=composition.profile_revision,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        snapshot_purpose=series.snapshot_purpose,
        requested_export_formats=requested_export_formats,
        requested_by=requested_by,
        requested_at=_now(clock),
        curation_review_decision_ids=inventory.applicable_review_decision_ids,
        idempotency_key=idempotency_key,
        predecessor_request_id=predecessor_request_id,
    )
    if idempotency_key is not None:
        matches = tuple(
            item
            for item in loaded.records
            if isinstance(item, SnapshotBuildRequest)
            and item.snapshot_series_id == snapshot_series_id
            and item.idempotency_key == idempotency_key
        )
        if len(matches) > 1:
            raise SnapshotWorkflowError(
                "snapshot.request_conflict",
                "Snapshot idempotency key has multiple canonical Requests.",
                stage="request",
            )
        if matches:
            existing = matches[0]
            if _request_intent(existing) != _request_intent(provisional):
                raise SnapshotWorkflowError(
                    "snapshot.request_conflict",
                    "Snapshot idempotency key was reused for different build intent.",
                    stage="request",
                )
            return SnapshotMutationResult(
                state_revision=loaded.state_revision,
                records=(existing,),
                disposition="existing",
            )
    request = replace(
        provisional,
        snapshot_build_request_id=id_factory("snapshot_request"),
    )
    revision = _commit(
        workspace_root,
        (request,),
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )
    return SnapshotMutationResult(
        state_revision=revision, records=(request,), disposition="created"
    )


def _placement_rank(
    context: _BuildContext, records: tuple[VitrineRecord, ...]
) -> dict[str, tuple[int, int]]:
    arrangements = {
        item.arrangement_id: item
        for item in records
        if isinstance(item, SectionArrangementRevision)
        and item.arrangement_id in context.composition.arrangement_ids
    }
    if set(arrangements) != set(context.composition.arrangement_ids):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition Arrangement inventory is incomplete.",
            stage="plan",
        )
    section_order = {item.section_id: item.order for item in context.profile.sections}
    ranks: dict[str, tuple[int, int]] = {}
    for arrangement in arrangements.values():
        if arrangement.section_id not in section_order:
            raise SnapshotWorkflowError(
                "snapshot.composition_mismatch",
                "Snapshot Composition Arrangement references an unknown Profile section.",
                stage="plan",
            )
        for position, placement_id in enumerate(arrangement.placement_ids, start=1):
            if placement_id in ranks:
                raise SnapshotWorkflowError(
                    "snapshot.composition_mismatch",
                    "Snapshot Composition Placement occurs in multiple current Arrangements.",
                    stage="plan",
                )
            ranks[placement_id] = (section_order[arrangement.section_id], position)
    if set(ranks) != set(context.composition.placement_ids):
        raise SnapshotWorkflowError(
            "snapshot.composition_mismatch",
            "Snapshot Composition Arrangement order does not cover its exact Placement inventory.",
            stage="plan",
        )
    return ranks


def _source_context(
    context: _BuildContext,
    records: tuple[VitrineRecord, ...],
    entry: SnapshotEntryPlan,
) -> tuple[PortfolioPlacement, PortfolioSelection, PortfolioCandidate, CandidateEvaluation]:
    if entry.placement_id is None:
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Producer-backed Snapshot Entry Plan requires an exact Composition Placement.",
            stage="plan",
        )
    placements = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPlacement)
        and item.placement_id == entry.placement_id
    )
    placement = _one(
        placements,
        code="snapshot.plan_source_mismatch",
        message="Snapshot Entry Placement does not resolve uniquely.",
        stage="plan",
    )
    assert isinstance(placement, PortfolioPlacement)
    selections = tuple(
        item
        for item in records
        if isinstance(item, PortfolioSelection)
        and item.selection_id == placement.selection_id
    )
    selection = _one(
        selections,
        code="snapshot.plan_source_mismatch",
        message="Snapshot Entry Selection does not resolve uniquely.",
        stage="plan",
    )
    assert isinstance(selection, PortfolioSelection)
    candidates = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == selection.candidate_id
    )
    candidate = _one(
        candidates,
        code="snapshot.plan_source_mismatch",
        message="Snapshot Entry Candidate does not resolve uniquely.",
        stage="plan",
    )
    assert isinstance(candidate, PortfolioCandidate)
    evaluations = tuple(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == selection.candidate_evaluation_id
    )
    evaluation = _one(
        evaluations,
        code="snapshot.plan_source_mismatch",
        message="Snapshot Entry Candidate Evaluation does not resolve uniquely.",
        stage="plan",
    )
    assert isinstance(evaluation, CandidateEvaluation)
    if (
        placement.placement_id not in context.composition.placement_ids
        or selection.selection_id not in context.composition.selection_ids
        or placement.selection_id != selection.selection_id
        or selection.candidate_id != candidate.candidate_id
        or selection.candidate_evaluation_id != candidate.candidate_evaluation_id
        or candidate.candidate_evaluation_id != evaluation.candidate_evaluation_id
    ):
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Snapshot Entry source chain is not the exact Composition-selected source.",
            stage="plan",
        )
    return placement, selection, candidate, evaluation


def _validate_source_entry(
    context: _BuildContext,
    records: tuple[VitrineRecord, ...],
    entry: SnapshotEntryPlan,
) -> str:
    placement, selection, candidate, evaluation = _source_context(context, records, entry)
    endpoint = candidate.source_endpoint
    artifact = endpoint.source_artifact
    if artifact is None:
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Producer-backed Snapshot Entry Plan requires the exact Candidate source Artifact.",
            stage="plan",
        )
    expected = (
        placement.section_id,
        selection.selection_id,
        candidate.candidate_id,
        evaluation.candidate_evaluation_id,
        endpoint.core_publication.publication_id,
        endpoint.producer_source.producer_module_id,
        artifact.representation_kind,
        endpoint.producer_source.projection_contract_version,
        artifact,
        artifact.source_digest,
    )
    actual = (
        entry.section_id,
        entry.selection_id,
        entry.candidate_id,
        entry.candidate_evaluation_id,
        entry.source_publication_id,
        entry.producer_module_id,
        entry.projection_kind,
        entry.projection_contract_version,
        entry.source_artifact,
        entry.producer_source_digest_claim,
    )
    if actual != expected:
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Snapshot Entry Plan does not preserve the exact Candidate source endpoint.",
            stage="plan",
        )
    if entry.materialization_kind == "copied_source" and entry.media_type != artifact.media_type:
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Copied Snapshot Entry media type differs from the exact source Artifact.",
            stage="plan",
        )
    expected_class = _SOURCE_CONTENT_CLASS_BY_ARTIFACT_KIND.get(artifact.artifact_kind)
    if expected_class is not None and entry.content_class != expected_class:
        raise SnapshotWorkflowError(
            "snapshot.plan_source_mismatch",
            "Snapshot Entry content class does not match the selected source Artifact kind.",
            stage="plan",
        )
    return placement.placement_id


def _validate_generated_inputs(
    context: _BuildContext,
    records: tuple[VitrineRecord, ...],
    entry: SnapshotEntryPlan,
) -> tuple[str, ...]:
    allowed_curation = {
        (
            "curation_annotation" if item.record_kind == "annotation" else "portfolio_reflection",
            item.record_id,
            item.revision,
        )
        for item in context.inventory.included_curation_revisions
    }
    selections = {
        item.selection_id: item
        for item in records
        if isinstance(item, PortfolioSelection)
        and item.selection_id in context.composition.selection_ids
    }
    placements = {
        item.placement_id: item
        for item in records
        if isinstance(item, PortfolioPlacement)
        and item.placement_id in context.composition.placement_ids
    }
    selected_candidates = {item.candidate_id for item in selections.values()}
    selected_evaluations = {item.candidate_evaluation_id for item in selections.values()}
    placement_refs: list[str] = []
    for reference in entry.input_references:
        key = (reference.record_type, reference.record_id, reference.record_revision)
        if reference.record_type in {"curation_annotation", "portfolio_reflection"}:
            if key not in allowed_curation:
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references curation not frozen by the Composition Inventory.",
                    stage="plan",
                )
        elif reference.record_type == "portfolio_selection":
            if reference.record_revision is not None or reference.record_id not in selections:
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references a Selection outside the exact Composition.",
                    stage="plan",
                )
        elif reference.record_type == "portfolio_placement":
            if reference.record_revision is not None or reference.record_id not in placements:
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references a Placement outside the exact Composition.",
                    stage="plan",
                )
            placement_refs.append(reference.record_id)
        elif reference.record_type == "portfolio_candidate":
            if reference.record_revision is not None or reference.record_id not in selected_candidates:
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references a Candidate outside the exact Composition.",
                    stage="plan",
                )
        elif reference.record_type == "candidate_evaluation":
            if reference.record_revision is not None or reference.record_id not in selected_evaluations:
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references an Evaluation outside the exact Composition.",
                    stage="plan",
                )
        elif reference.record_type == "working_portfolio_composition_revision":
            if (
                reference.record_id != context.composition.portfolio_id
                or reference.record_revision != context.composition.composition_revision
            ):
                raise SnapshotWorkflowError(
                    "snapshot.plan_source_mismatch",
                    "Generated Snapshot Entry references another Composition Revision.",
                    stage="plan",
                )
        else:
            raise SnapshotWorkflowError(
                "snapshot.plan_source_mismatch",
                "Generated Snapshot Entry uses an unsupported exact input reference.",
                stage="plan",
            )
    return tuple(placement_refs)


def _validate_plan_entries(
    context: _BuildContext,
    records: tuple[VitrineRecord, ...],
    entries: tuple[SnapshotEntryPlan, ...],
    exports: tuple[SnapshotExportPlan, ...],
) -> None:
    if not entries:
        raise SnapshotWorkflowError(
            "snapshot.plan_inventory_incomplete",
            "Snapshot Build Plan must contain at least one Entry Plan.",
            stage="plan",
        )
    try:
        byte_paths = tuple(
            item.target_relative_path
            for item in entries
            if item.target_relative_path is not None
        )
        validate_snapshot_path_inventory(byte_paths)
    except SnapshotCustodyError as error:
        raise SnapshotWorkflowError(
            "snapshot.plan_conflict",
            "Snapshot Build Plan contains an unsafe or colliding output path.",
            stage="plan",
        ) from error
    ranks = _placement_rank(context, records)
    plan_rank_items: list[tuple[int, tuple[int, int]]] = []
    covered_placements: set[str] = set()
    for entry in entries:
        if not set(entry.required_review_ids).issubset(
            set(context.request.curation_review_decision_ids)
        ):
            raise SnapshotWorkflowError(
                "snapshot.plan_review_mismatch",
                "Snapshot Entry Plan references a Review outside the exact Build Request.",
                stage="plan",
            )
        prohibited = entry.content_class in context.audience.prohibited_content_classes
        allowed = (
            not context.audience.allowed_content_classes
            or entry.content_class in context.audience.allowed_content_classes
        )
        if prohibited or not allowed:
            if not (
                entry.materialization_kind == "reference_only"
                and entry.permitted_omission_reason == "audience_prohibited"
            ):
                raise SnapshotWorkflowError(
                    "snapshot.plan_audience_prohibited",
                    "Snapshot Entry content class is not permitted for the exact Audience Context.",
                    stage="plan",
                )
        placement_refs: tuple[str, ...]
        if entry.materialization_kind in {"copied_source", "reference_only"}:
            placement_refs = (_validate_source_entry(context, records, entry),)
        else:
            placement_refs = _validate_generated_inputs(context, records, entry)
        for placement_id in placement_refs:
            covered_placements.add(placement_id)
            plan_rank_items.append((entry.plan_position, ranks[placement_id]))
    ordered_ranks = [rank for _, rank in sorted(plan_rank_items)]
    if ordered_ranks != sorted(ordered_ranks):
        raise SnapshotWorkflowError(
            "snapshot.plan_order_invalid",
            "Placement-bound Snapshot Entries do not preserve Profile/Arrangement order.",
            stage="plan",
        )
    if covered_placements != set(context.composition.placement_ids):
        raise SnapshotWorkflowError(
            "snapshot.plan_inventory_incomplete",
            "Snapshot Build Plan does not explicitly account for every Composition Placement.",
            stage="plan",
        )
    entry_ids = {item.entry_plan_id for item in entries}
    if not exports:
        raise SnapshotWorkflowError(
            "snapshot.plan_inventory_incomplete",
            "Snapshot Build Plan requires an explicit directory Export Plan.",
            stage="plan",
        )
    for export in exports:
        if set(export.included_entry_plan_ids) | set(export.excluded_entry_plan_ids) != entry_ids:
            raise SnapshotWorkflowError(
                "snapshot.plan_inventory_incomplete",
                "Snapshot Export Plan must partition the exact Entry Plan inventory.",
                stage="plan",
            )
        reference_only_ids = {
            item.entry_plan_id
            for item in entries
            if item.materialization_kind == "reference_only"
        }
        if reference_only_ids & set(export.included_entry_plan_ids):
            raise SnapshotWorkflowError(
                "snapshot.plan_inventory_incomplete",
                "Reference-only Snapshot items cannot be included as byte-bearing export files.",
                stage="plan",
            )


def _plan_intent(plan: SnapshotBuildPlan) -> tuple[object, ...]:
    return (
        plan.snapshot_build_request_id,
        plan.snapshot_series_id,
        plan.portfolio_id,
        plan.portfolio_subject_id,
        plan.profile_binding_id,
        plan.profile_revision,
        plan.composition_revision,
        plan.audience_context_id,
        plan.entry_plans,
        plan.export_plans,
        plan.required_review_references,
        plan.acknowledged_obligation_codes,
        plan.path_policy_id,
        plan.digest_policy_id,
        plan.builder_contract_id,
        plan.builder_contract_version,
        plan.planned_by,
        plan.predecessor_plan_id,
    )


def plan_snapshot_build(
    workspace_root: str | Path,
    *,
    snapshot_build_request_id: str,
    entry_plans: tuple[SnapshotEntryPlan, ...],
    export_plans: tuple[SnapshotExportPlan, ...],
    planned_by: ActorAttribution,
    expected_state_revision: int,
    acknowledged_obligation_codes: tuple[str, ...] = (),
    predecessor_plan_id: str | None = None,
    builder_contract_id: str = SNAPSHOT_BUILDER_CONTRACT_ID,
    builder_contract_version: str = SNAPSHOT_BUILDER_CONTRACT_VERSION,
    path_policy_id: str = SNAPSHOT_PATH_POLICY_ID,
    digest_policy_id: str = SNAPSHOT_DIGEST_POLICY_ID,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotMutationResult:
    """Freeze exact Composition/source/rendering decisions into an immutable Plan."""

    try:
        snapshot_build_request_id = require_identifier(
            snapshot_build_request_id, "snapshot_build_request_id"
        )
        predecessor_plan_id = require_optional_text(
            predecessor_plan_id, "predecessor_plan_id", maximum=256
        )
        builder_contract_id = require_identifier(builder_contract_id, "builder_contract_id")
        builder_contract_version = require_identifier(
            builder_contract_version, "builder_contract_version"
        )
        path_policy_id = require_identifier(path_policy_id, "path_policy_id")
        digest_policy_id = require_identifier(digest_policy_id, "digest_policy_id")
        acknowledged = lower_key_tuple(
            acknowledged_obligation_codes, "acknowledged_obligation_codes"
        )
        if not isinstance(planned_by, ActorAttribution):
            raise VitrineModelValidationError("planned_by must be ActorAttribution.")
        entries = tuple(entry_plans)
        exports = tuple(export_plans)
    except (TypeError, VitrineModelValidationError) as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot Build Plan request is invalid.",
            stage="plan",
        ) from error
    loaded = _load_state(workspace_root, expected_state_revision)
    request = _request(loaded.records, snapshot_build_request_id)
    context = _build_context(loaded.records, request)
    _validate_plan_entries(context, loaded.records, entries, exports)
    if not set(acknowledged).issubset(
        set(context.inventory.unresolved_obligation_codes)
    ):
        raise SnapshotWorkflowError(
            "snapshot.plan_conflict",
            "Snapshot Plan acknowledges an obligation not frozen by the Composition Inventory.",
            stage="plan",
        )
    existing_plans = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_request_id == snapshot_build_request_id
    )
    predecessor: SnapshotBuildPlan | None = None
    if predecessor_plan_id is not None:
        predecessor = _plan(loaded.records, predecessor_plan_id)
        if predecessor.snapshot_build_request_id != snapshot_build_request_id:
            raise SnapshotWorkflowError(
                "snapshot.plan_conflict",
                "Snapshot predecessor Plan belongs to another Build Request.",
                stage="plan",
            )
        plan_revision = predecessor.plan_revision + 1
    else:
        if existing_plans:
            plan_revision = 1
        else:
            plan_revision = 1
    provisional = SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_provisional",
        snapshot_build_request_id=request.snapshot_build_request_id,
        snapshot_series_id=request.snapshot_series_id,
        plan_revision=plan_revision,
        portfolio_id=request.portfolio_id,
        portfolio_subject_id=request.portfolio_subject_id,
        profile_binding_id=request.profile_binding_id,
        profile_revision=request.profile_revision,
        composition_revision=request.composition_revision,
        audience_context_id=request.audience_context_id,
        entry_plans=entries,
        export_plans=exports,
        required_review_references=request.curation_review_decision_ids,
        acknowledged_obligation_codes=acknowledged,
        path_policy_id=path_policy_id,
        digest_policy_id=digest_policy_id,
        builder_contract_id=builder_contract_id,
        builder_contract_version=builder_contract_version,
        planned_at=_now(clock),
        planned_by=planned_by,
        plan_fingerprint="0" * 64,
        predecessor_plan_id=predecessor_plan_id,
    )
    for existing in existing_plans:
        if _plan_intent(existing) == _plan_intent(provisional):
            return SnapshotMutationResult(
                state_revision=loaded.state_revision,
                records=(existing,),
                disposition="existing",
            )
    if existing_plans and predecessor is None:
        raise SnapshotWorkflowError(
            "snapshot.plan_conflict",
            "A different Snapshot Plan already exists; successor planning requires an explicit predecessor.",
            stage="plan",
        )
    plan = replace(
        provisional,
        snapshot_build_plan_id=id_factory("snapshot_plan"),
    )
    plan = replace(plan, plan_fingerprint=snapshot_plan_fingerprint(plan))
    revision = _commit(
        workspace_root,
        (plan,),
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )
    return SnapshotMutationResult(
        state_revision=revision, records=(plan,), disposition="created"
    )


def start_snapshot_build_attempt(
    workspace_root: str | Path,
    *,
    snapshot_build_plan_id: str,
    started_by: ActorAttribution,
    expected_state_revision: int,
    builder_id: str = SNAPSHOT_BUILDER_CONTRACT_ID,
    builder_version: str = SNAPSHOT_BUILDER_CONTRACT_VERSION,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotAttemptStartResult:
    """Persist an immutable Attempt start, then create its noncanonical staging tree."""

    try:
        snapshot_build_plan_id = require_identifier(
            snapshot_build_plan_id, "snapshot_build_plan_id"
        )
        builder_id = require_identifier(builder_id, "builder_id")
        builder_version = require_identifier(builder_version, "builder_version")
        if not isinstance(started_by, ActorAttribution):
            raise VitrineModelValidationError("started_by must be ActorAttribution.")
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot Build Attempt request is invalid.",
            stage="attempt",
        ) from error
    loaded = _load_state(workspace_root, expected_state_revision)
    plan = _plan(loaded.records, snapshot_build_plan_id)
    attempts = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_plan_id == snapshot_build_plan_id
    )
    plans_by_id = {
        item.snapshot_build_plan_id: item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
    }
    series_attempts = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttempt)
        and plans_by_id.get(item.snapshot_build_plan_id) is not None
        and plans_by_id[item.snapshot_build_plan_id].snapshot_series_id
        == plan.snapshot_series_id
    )
    result_attempt_ids = {
        item.snapshot_build_attempt_id
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttemptResult)
    }
    incomplete = tuple(
        item
        for item in series_attempts
        if item.snapshot_build_attempt_id not in result_attempt_ids
    )
    if incomplete:
        raise SnapshotWorkflowError(
            "snapshot.attempt_conflict",
            "Snapshot Series already has an incomplete Build Attempt.",
            stage="attempt",
        )
    attempt_number = max((item.attempt_number for item in attempts), default=0) + 1
    attempt_id = id_factory("snapshot_attempt")
    attempt = SnapshotBuildAttempt(
        snapshot_build_attempt_id=attempt_id,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        attempt_number=attempt_number,
        builder_id=builder_id,
        builder_version=builder_version,
        started_at=_now(clock),
        staging_reference=attempt_id,
        started_by=started_by,
    )
    revision = _commit(
        workspace_root,
        (attempt,),
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )
    try:
        series_lock = acquire_snapshot_series_lock(
            workspace_root,
            snapshot_series_id=plan.snapshot_series_id,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
            acquired_at=attempt.started_at,
        )
    except SnapshotCustodyError as error:
        finding = SnapshotBuildFinding(
            code=error.code,
            severity="error",
            blocking=True,
            summary="Snapshot Series build lock could not be acquired exclusively.",
        )
        terminal = SnapshotBuildAttemptResult(
            snapshot_build_attempt_result_id=id_factory("snapshot_attempt_result"),
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            completed_at=_now(clock),
            terminal_outcome="failed",
            entry_outcomes=tuple(
                SnapshotEntryOutcome(
                    entry_plan_id=entry.entry_plan_id,
                    disposition="failed_blocking",
                    finding_codes=(error.code,),
                )
                for entry in plan.entry_plans
            ),
            findings=(finding,),
        )
        _commit(
            workspace_root,
            (terminal,),
            expected_state_revision=revision,
            current_records=(*loaded.records, attempt),
        )
        raise SnapshotWorkflowError(
            error.code,
            "Snapshot Attempt failed because its Series build lock could not be acquired.",
            stage="build_lock",
        ) from error
    try:
        staging = create_snapshot_staging(workspace_root, attempt.snapshot_build_attempt_id)
    except SnapshotCustodyError as error:
        finding = SnapshotBuildFinding(
            code=error.code,
            severity="error",
            blocking=True,
            summary="Snapshot staging could not be created safely.",
        )
        outcomes = tuple(
            SnapshotEntryOutcome(
                entry_plan_id=entry.entry_plan_id,
                disposition="failed_blocking",
                finding_codes=(error.code,),
            )
            for entry in plan.entry_plans
        )
        cleanup_findings: tuple[SnapshotBuildFinding, ...] = ()
        try:
            release_snapshot_series_lock(
                workspace_root,
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
                expected_sha256=series_lock.sha256,
            )
        except SnapshotCustodyError as cleanup_error:
            cleanup_findings = (
                SnapshotBuildFinding(
                    code=cleanup_error.code,
                    severity="warning",
                    blocking=False,
                    summary="Snapshot Series build lock remains for explicit recovery.",
                ),
            )
        terminal = SnapshotBuildAttemptResult(
            snapshot_build_attempt_result_id=id_factory("snapshot_attempt_result"),
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            completed_at=_now(clock),
            terminal_outcome="failed",
            entry_outcomes=outcomes,
            findings=(finding,),
            cleanup_findings=cleanup_findings,
        )
        _commit(
            workspace_root,
            (terminal,),
            expected_state_revision=revision,
            current_records=(*loaded.records, attempt),
        )
        raise SnapshotWorkflowError(
            "snapshot.staging_conflict",
            "Snapshot Attempt failed because its staging tree could not be created safely.",
            stage="staging",
        ) from error
    return SnapshotAttemptStartResult(
        state_revision=revision,
        attempt=attempt,
        staging_root=staging.root,
    )


def _attempt(
    records: tuple[VitrineRecord, ...], attempt_id: str
) -> SnapshotBuildAttempt:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_attempt_id == attempt_id
    )
    return _one(
        values,
        code="snapshot.attempt_not_found",
        message="Snapshot Build Attempt does not resolve uniquely.",
        stage="attempt",
    )



def _require_attempt_series_lock(
    workspace_root: str | Path,
    *,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
) -> object:
    try:
        inspection = inspect_snapshot_series_lock(
            workspace_root, snapshot_series_id=plan.snapshot_series_id
        )
    except SnapshotCustodyError as error:
        raise SnapshotWorkflowError(
            error.code,
            "Snapshot Attempt does not hold a valid Series build lock.",
            stage="build_lock",
        ) from error
    if (
        inspection.snapshot_build_attempt_id != attempt.snapshot_build_attempt_id
        or inspection.snapshot_build_plan_id != plan.snapshot_build_plan_id
    ):
        raise SnapshotWorkflowError(
            "snapshot.build_lock_conflict",
            "Snapshot Series build lock belongs to another Attempt or Plan.",
            stage="build_lock",
        )
    return inspection


def _release_attempt_series_lock_best_effort(
    workspace_root: str | Path,
    *,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
) -> SnapshotBuildFinding | None:
    try:
        inspection = inspect_snapshot_series_lock(
            workspace_root, snapshot_series_id=plan.snapshot_series_id
        )
        if (
            inspection.snapshot_build_attempt_id != attempt.snapshot_build_attempt_id
            or inspection.snapshot_build_plan_id != plan.snapshot_build_plan_id
        ):
            return SnapshotBuildFinding(
                code="snapshot.build_lock_conflict",
                severity="warning",
                blocking=False,
                summary="Snapshot Series build lock belongs to another execution and was preserved.",
            )
        release_snapshot_series_lock(
            workspace_root,
            snapshot_series_id=plan.snapshot_series_id,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_sha256=inspection.sha256,
        )
    except SnapshotCustodyError as error:
        return SnapshotBuildFinding(
            code=error.code,
            severity="warning",
            blocking=False,
            summary="Snapshot Series build lock remains for explicit recovery.",
        )
    return None

def _external_build_authority(
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    gate: SnapshotBuildAuthorityGate,
) -> SnapshotBuildAuthorityDecision:
    request = SnapshotBuildAuthorityRequest(
        operation=SNAPSHOT_BUILD_OPERATION,
        snapshot_series_id=plan.snapshot_series_id,
        snapshot_build_request_id=plan.snapshot_build_request_id,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        portfolio_id=plan.portfolio_id,
        portfolio_subject_id=plan.portfolio_subject_id,
        profile_binding_id=plan.profile_binding_id,
        actor=attempt.started_by,
    )
    try:
        decision = gate.authorize(request)
    except SnapshotMaterializationError:
        raise
    except Exception as error:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot build-authority gate failed.",
            stage="authority",
        ) from error
    if not isinstance(decision, SnapshotBuildAuthorityDecision):
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot build-authority gate returned an invalid decision.",
            stage="authority",
        )
    return decision


def _failed_attempt_result(
    *,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    code: str,
    summary: str,
    completed_at: datetime,
    id_factory: IdFactory,
) -> SnapshotBuildAttemptResult:
    outcomes = tuple(
        SnapshotEntryOutcome(
            entry_plan_id=entry.entry_plan_id,
            disposition=(
                "reference_only"
                if entry.materialization_kind == "reference_only"
                and entry.permitted_omission_reason is None
                else "failed_blocking"
            ),
            finding_codes=(
                ()
                if entry.materialization_kind == "reference_only"
                and entry.permitted_omission_reason is None
                else (code,)
            ),
        )
        for entry in plan.entry_plans
    )
    return SnapshotBuildAttemptResult(
        snapshot_build_attempt_result_id=id_factory("snapshot_attempt_result"),
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        completed_at=completed_at,
        terminal_outcome="failed",
        entry_outcomes=outcomes,
        findings=(
            SnapshotBuildFinding(
                code=code,
                severity="error",
                blocking=True,
                summary=summary,
            ),
        ),
    )


def _persist_execution_failure(
    workspace_root: str | Path,
    *,
    loaded: _LoadedState,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    code: str,
    summary: str,
    clock: Clock,
    id_factory: IdFactory,
) -> int:
    cleanup = _release_attempt_series_lock_best_effort(
        workspace_root, plan=plan, attempt=attempt
    )
    terminal = _failed_attempt_result(
        plan=plan,
        attempt=attempt,
        code=code,
        summary=summary,
        completed_at=_now(clock),
        id_factory=id_factory,
    )
    if cleanup is not None:
        terminal = replace(terminal, cleanup_findings=(cleanup,))
    return _commit(
        workspace_root,
        (terminal,),
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )


def execute_snapshot_build_attempt(
    workspace_root: str | Path,
    *,
    snapshot_build_attempt_id: str,
    expected_state_revision: int,
    authority_gate: SnapshotBuildAuthorityGate,
    source_providers: SnapshotSourceProviderRegistry,
    renderers: SnapshotRendererRegistry,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotAttemptExecutionResult:
    """Execute one open Attempt into staging without fabricating an Edition.

    Successful byte materialization and permitted omissions remain noncanonical until
    the later sealing boundary can assign the real immutable Edition identity.
    Blocking execution failures are terminal and persisted immediately.
    """

    try:
        snapshot_build_attempt_id = require_identifier(
            snapshot_build_attempt_id, "snapshot_build_attempt_id"
        )
    except VitrineModelValidationError as error:
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot Build Attempt identity is invalid.",
            stage="attempt_execution",
        ) from error
    if not isinstance(source_providers, SnapshotSourceProviderRegistry):
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot source-provider registry is invalid.",
            stage="attempt_execution",
        )
    if not isinstance(renderers, SnapshotRendererRegistry):
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot renderer registry is invalid.",
            stage="attempt_execution",
        )

    loaded = _load_state(workspace_root, expected_state_revision)
    attempt = _attempt(loaded.records, snapshot_build_attempt_id)
    plan = _plan(loaded.records, attempt.snapshot_build_plan_id)
    if any(
        isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
        for item in loaded.records
    ):
        raise SnapshotWorkflowError(
            "snapshot.attempt_conflict",
            "Snapshot Build Attempt already has a terminal Result.",
            stage="attempt_execution",
        )
    try:
        _require_attempt_series_lock(
            workspace_root, plan=plan, attempt=attempt
        )
    except SnapshotWorkflowError as error:
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=error.code,
            summary="Snapshot Attempt lost or conflicted with its Series build lock.",
            clock=clock,
            id_factory=id_factory,
        )
        raise

    try:
        staging = load_snapshot_staging(
            workspace_root, attempt.snapshot_build_attempt_id
        )
        require_empty_snapshot_staging(staging)
    except SnapshotCustodyError as error:
        if error.code == "snapshot.staging_conflict":
            # Existing residue may be interrupted execution evidence. Do not
            # silently classify or overwrite it; explicit recovery owns that case.
            raise SnapshotWorkflowError(
                "snapshot.staging_conflict",
                "Snapshot Attempt staging contains unresolved prior execution state.",
                stage="attempt_execution",
            ) from error
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=error.code,
            summary="Snapshot Attempt staging is unavailable or invalid.",
            clock=clock,
            id_factory=id_factory,
        )
        raise SnapshotWorkflowError(
            "snapshot.staging_invalid",
            "Snapshot Attempt failed because staging is unavailable or invalid.",
            stage="attempt_execution",
        ) from error

    try:
        decision = _external_build_authority(plan, attempt, authority_gate)
    except SnapshotMaterializationError as error:
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=error.code,
            summary="Snapshot build authority could not be established.",
            clock=clock,
            id_factory=id_factory,
        )
        raise SnapshotWorkflowError(
            "snapshot.materialization_failed",
            "Snapshot Attempt failed before materialization.",
            stage="authority",
        ) from error

    if decision.outcome != "allowed":
        code = (
            "snapshot.authority_denied"
            if decision.outcome == "denied"
            else "snapshot.authority_unresolved"
        )
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=code,
            summary="Snapshot build authority was not granted.",
            clock=clock,
            id_factory=id_factory,
        )
        raise SnapshotWorkflowError(
            code,
            "Snapshot Attempt stopped before source access because build authority was not granted.",
            stage="authority",
        )
    assert decision.authority_reference is not None
    internal_gate = _ApprovedAuthorityGate(decision)

    prepared: list[SnapshotPreparedEntry] = []
    for entry in plan.entry_plans:
        if entry.materialization_kind == "reference_only":
            if entry.permitted_omission_reason is not None:
                prepared.append(
                    SnapshotPreparedEntry(
                        entry_plan_id=entry.entry_plan_id,
                        disposition="omission_pending",
                        pending_omission_reason=entry.permitted_omission_reason,
                    )
                )
            else:
                prepared.append(
                    SnapshotPreparedEntry(
                        entry_plan_id=entry.entry_plan_id,
                        disposition="reference_only",
                    )
                )
            continue

        try:
            if entry.materialization_kind == "copied_source":
                copied = copy_planned_source_to_staging(
                    plan=plan,
                    attempt=attempt,
                    entry_plan_id=entry.entry_plan_id,
                    staging=staging,
                    authority_gate=internal_gate,
                    source_providers=source_providers,
                )
                prepared.append(
                    SnapshotPreparedEntry(
                        entry_plan_id=entry.entry_plan_id,
                        disposition="prepared_bytes",
                        copied_bytes=copied,
                    )
                )
            else:
                generated = render_planned_entry_to_staging(
                    plan=plan,
                    attempt=attempt,
                    entry_plan_id=entry.entry_plan_id,
                    staging=staging,
                    authority_gate=internal_gate,
                    renderers=renderers,
                )
                prepared.append(
                    SnapshotPreparedEntry(
                        entry_plan_id=entry.entry_plan_id,
                        disposition="prepared_bytes",
                        generated_bytes=generated,
                    )
                )
        except SnapshotMaterializationError as error:
            omission_reason = _PERMITTED_OMISSION_BY_FAILURE.get(error.code)
            if (
                omission_reason is not None
                and entry.permitted_omission_reason == omission_reason
            ):
                prepared.append(
                    SnapshotPreparedEntry(
                        entry_plan_id=entry.entry_plan_id,
                        disposition="omission_pending",
                        pending_omission_reason=omission_reason,
                    )
                )
                continue
            _persist_execution_failure(
                workspace_root,
                loaded=loaded,
                plan=plan,
                attempt=attempt,
                code=error.code,
                summary="Snapshot Attempt encountered a blocking materialization failure.",
                clock=clock,
                id_factory=id_factory,
            )
            raise SnapshotWorkflowError(
                "snapshot.materialization_failed",
                "Snapshot Attempt failed during exact Entry materialization.",
                stage=error.stage,
            ) from error

    return SnapshotAttemptExecutionResult(
        state_revision=loaded.state_revision,
        attempt=attempt,
        plan=plan,
        staging_root=staging.root,
        authority_reference=decision.authority_reference,
        entries=tuple(prepared),
    )


def _strings_json(values: tuple[str, ...]) -> JsonValue:
    result: list[JsonValue] = []
    result.extend(values)
    return result


def _digest_json(value: DigestReference | None) -> JsonValue:
    if value is None:
        return None
    return {"algorithm": value.algorithm, "value": value.value}


def _source_artifact_json(entry: SnapshotEntryPlan) -> JsonValue:
    artifact = entry.source_artifact
    if artifact is None:
        return None
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_kind": artifact.artifact_kind,
        "representation_kind": artifact.representation_kind,
        "media_type": artifact.media_type,
        "source_locator": artifact.source_locator,
        "native_revision": artifact.native_revision,
        "source_digest": _digest_json(artifact.source_digest),
        "byte_size": artifact.byte_size,
        "language": artifact.language,
        "accessibility_relationship": artifact.accessibility_relationship,
    }


def _input_references_json(entry: SnapshotEntryPlan) -> JsonValue:
    result: list[JsonValue] = []
    for item in entry.input_references:
        value: dict[str, JsonValue] = {
            "record_type": item.record_type,
            "record_id": item.record_id,
            "record_revision": item.record_revision,
        }
        result.append(value)
    return result


def _sealed_disposition(prepared: SnapshotPreparedEntry) -> str:
    return {
        "prepared_bytes": "included",
        "omission_pending": "omitted_permitted",
        "reference_only": "reference_only",
    }[prepared.disposition]


def _materialized_entry_media_type(
    entry: SnapshotEntryPlan, prepared: SnapshotPreparedEntry
) -> str | None:
    if prepared.copied_bytes is not None:
        return prepared.copied_bytes.media_type
    return entry.media_type


def _manifest_entry_json(
    entry: SnapshotEntryPlan,
    prepared: SnapshotPreparedEntry,
    *,
    materialization_id: str | None,
    snapshot_entry_id: str | None,
    snapshot_omission_id: str | None,
) -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = {
        "entry_plan_id": entry.entry_plan_id,
        "plan_position": entry.plan_position,
        "section_id": entry.section_id,
        "ordinal": entry.ordinal,
        "semantic_role": entry.semantic_role,
        "materialization_kind": entry.materialization_kind,
        "content_class": entry.content_class,
        "disposition": _sealed_disposition(prepared),
        "materialization_id": materialization_id,
        "snapshot_entry_id": snapshot_entry_id,
        "snapshot_omission_id": snapshot_omission_id,
        "selection_id": entry.selection_id,
        "placement_id": entry.placement_id,
        "candidate_id": entry.candidate_id,
        "candidate_evaluation_id": entry.candidate_evaluation_id,
        "source_publication_id": entry.source_publication_id,
        "producer_module_id": entry.producer_module_id,
        "projection_kind": entry.projection_kind,
        "projection_contract_version": entry.projection_contract_version,
        "source_artifact": _source_artifact_json(entry),
        "producer_source_digest_claim": _digest_json(
            entry.producer_source_digest_claim
        ),
        "target_relative_path": entry.target_relative_path,
        "media_type": _materialized_entry_media_type(entry, prepared),
        "required_review_ids": _strings_json(entry.required_review_ids),
        "permitted_omission_reason": entry.permitted_omission_reason,
        "input_references": _input_references_json(entry),
    }
    if prepared.copied_bytes is not None:
        copied = prepared.copied_bytes
        value["materialization"] = {
            "source_provider_id": copied.source_provider_id,
            "source_provider_version": copied.source_provider_version,
            "acquired_source_digest": _digest_json(copied.acquired_source_digest),
            "output_digest": _digest_json(copied.copied_output_digest),
            "byte_size": copied.byte_size,
            "source_stability_result": copied.source_stability_result,
        }
    elif prepared.generated_bytes is not None:
        generated = prepared.generated_bytes
        value["materialization"] = {
            "renderer_id": generated.renderer_id,
            "renderer_version": generated.renderer_version,
            "renderer_contract_version": generated.renderer_contract_version,
            "configuration_digest": _digest_json(generated.configuration_digest),
            "template_digest": _digest_json(generated.template_digest),
            "output_digest": _digest_json(generated.output_digest),
            "byte_size": generated.byte_size,
        }
    else:
        value["materialization"] = None
    value["omission_reason"] = prepared.pending_omission_reason
    return value


def _logical_entry_json(
    entry: SnapshotEntryPlan, prepared: SnapshotPreparedEntry
) -> dict[str, JsonValue]:
    output_digest: JsonValue = None
    byte_size: JsonValue = None
    if prepared.copied_bytes is not None:
        output_digest = _digest_json(prepared.copied_bytes.copied_output_digest)
        byte_size = prepared.copied_bytes.byte_size
    elif prepared.generated_bytes is not None:
        output_digest = _digest_json(prepared.generated_bytes.output_digest)
        byte_size = prepared.generated_bytes.byte_size
    return {
        "entry_plan_id": entry.entry_plan_id,
        "disposition": _sealed_disposition(prepared),
        "section_id": entry.section_id,
        "ordinal": entry.ordinal,
        "semantic_role": entry.semantic_role,
        "content_class": entry.content_class,
        "selection_id": entry.selection_id,
        "placement_id": entry.placement_id,
        "candidate_id": entry.candidate_id,
        "candidate_evaluation_id": entry.candidate_evaluation_id,
        "source_publication_id": entry.source_publication_id,
        "producer_module_id": entry.producer_module_id,
        "projection_kind": entry.projection_kind,
        "projection_contract_version": entry.projection_contract_version,
        "source_artifact_id": (
            None if entry.source_artifact is None else entry.source_artifact.artifact_id
        ),
        "producer_source_digest_claim": _digest_json(
            entry.producer_source_digest_claim
        ),
        "relative_path": entry.target_relative_path,
        "media_type": _materialized_entry_media_type(entry, prepared),
        "renderer_id": entry.renderer_id,
        "renderer_version": entry.renderer_version,
        "renderer_contract_version": entry.renderer_contract_version,
        "renderer_configuration_digest": _digest_json(
            entry.renderer_configuration_digest
        ),
        "renderer_template_digest": _digest_json(entry.renderer_template_digest),
        "input_references": _input_references_json(entry),
        "output_digest": output_digest,
        "byte_size": byte_size,
        "omission_reason": prepared.pending_omission_reason,
    }


def _verify_prepared_snapshot_bytes(
    staging: SnapshotStagingArea,
    plan: SnapshotBuildPlan,
    prepared_entries: tuple[SnapshotPreparedEntry, ...],
) -> None:
    # SnapshotStagingArea is validated by the custody helpers; keeping this helper
    # typed through their public API avoids duplicating custody rules here.
    expected_paths: list[str] = []
    for entry, prepared in zip(plan.entry_plans, prepared_entries, strict=True):
        if prepared.disposition != "prepared_bytes":
            continue
        if entry.target_relative_path is None:
            raise SnapshotWorkflowError(
                "snapshot.final_verification_failed",
                "Prepared Snapshot Entry has no planned output path.",
                stage="seal_verification",
            )
        expected_paths.append(entry.target_relative_path)
    try:
        actual_inventory = staging_content_inventory(staging)
    except SnapshotCustodyError as error:
        raise SnapshotWorkflowError(
            "snapshot.final_verification_failed",
            "Snapshot staging inventory failed final verification.",
            stage="seal_verification",
        ) from error
    if actual_inventory != tuple(sorted(expected_paths)):
        raise SnapshotWorkflowError(
            "snapshot.final_verification_failed",
            "Snapshot staging inventory differs from the exact prepared Entry inventory.",
            stage="seal_verification",
        )
    for entry, prepared in zip(plan.entry_plans, prepared_entries, strict=True):
        if prepared.disposition != "prepared_bytes":
            continue
        assert entry.target_relative_path is not None
        try:
            payload = read_staging_content_bytes(staging, entry.target_relative_path)
        except SnapshotCustodyError as error:
            raise SnapshotWorkflowError(
                "snapshot.final_verification_failed",
                "Prepared Snapshot bytes could not be re-read for final verification.",
                stage="seal_verification",
            ) from error
        actual_digest = snapshot_digest(payload)
        if prepared.copied_bytes is not None:
            expected_digest = prepared.copied_bytes.copied_output_digest
            expected_size = prepared.copied_bytes.byte_size
            if prepared.copied_bytes.target_relative_path != entry.target_relative_path:
                raise SnapshotWorkflowError(
                    "snapshot.final_verification_failed",
                    "Copied byte result no longer matches the frozen Entry Plan path.",
                    stage="seal_verification",
                )
        elif prepared.generated_bytes is not None:
            expected_digest = prepared.generated_bytes.output_digest
            expected_size = prepared.generated_bytes.byte_size
            if prepared.generated_bytes.target_relative_path != entry.target_relative_path:
                raise SnapshotWorkflowError(
                    "snapshot.final_verification_failed",
                    "Generated byte result no longer matches the frozen Entry Plan path.",
                    stage="seal_verification",
                )
        else:
            raise SnapshotWorkflowError(
                "snapshot.final_verification_failed",
                "Prepared Snapshot Entry is missing its byte custody result.",
                stage="seal_verification",
            )
        if actual_digest != expected_digest or len(payload) != expected_size:
            raise SnapshotWorkflowError(
                "snapshot.final_verification_failed",
                "Prepared Snapshot bytes changed before sealing.",
                stage="seal_verification",
            )


def _next_edition_identity(
    records: tuple[VitrineRecord, ...], snapshot_series_id: str
) -> tuple[int, int | None]:
    numbers = tuple(
        item.edition_number
        for item in records
        if isinstance(item, SnapshotEdition)
        and item.snapshot_series_id == snapshot_series_id
    )
    predecessor = max(numbers) if numbers else None
    return (1 if predecessor is None else predecessor + 1, predecessor)


def _build_sealed_records(
    *,
    execution: SnapshotAttemptExecutionResult,
    edition_ref: SnapshotEditionRef,
    predecessor_edition: int | None,
    sealed_at: datetime,
    sealed_by: ActorAttribution,
    id_factory: IdFactory,
) -> tuple[
    tuple[VitrineRecord, ...],
    SnapshotManifest,
    SnapshotSeal,
    SnapshotEdition,
    tuple[SnapshotEntryOutcome, ...],
    bytes,
]:
    materializations: list[SnapshotMaterializationRecord] = []
    entries: list[SnapshotEntry] = []
    omissions: list[SnapshotOmission] = []
    provenance: list[SnapshotMaterializationProvenance] = []
    outcomes: list[SnapshotEntryOutcome] = []
    materialization_ids_by_plan: dict[str, str] = {}
    entry_ids_by_plan: dict[str, str] = {}
    omission_ids_by_plan: dict[str, str] = {}

    for plan_entry, prepared in zip(
        execution.plan.entry_plans, execution.entries, strict=True
    ):
        if prepared.disposition == "prepared_bytes":
            materialization_id = id_factory("snapshot_materialization")
            snapshot_entry_id = id_factory("snapshot_entry")
            if prepared.copied_bytes is not None:
                copied = prepared.copied_bytes
                materialization = SnapshotMaterializationRecord(
                    materialization_id=materialization_id,
                    snapshot_edition=edition_ref,
                    materialization_kind="copied_source",
                    candidate_id=plan_entry.candidate_id,
                    selection_id=plan_entry.selection_id,
                    placement_id=plan_entry.placement_id,
                    source_artifact=plan_entry.source_artifact,
                    source_digest=copied.acquired_source_digest,
                    output_digest=copied.copied_output_digest,
                    byte_size=copied.byte_size,
                    materialized_at=sealed_at,
                    materialized_by=sealed_by,
                )
                provenance_record = SnapshotMaterializationProvenance(
                    snapshot_materialization_provenance_id=id_factory(
                        "snapshot_materialization_provenance"
                    ),
                    materialization_id=materialization_id,
                    snapshot_edition=edition_ref,
                    entry_plan_id=plan_entry.entry_plan_id,
                    source_provider_id=copied.source_provider_id,
                    source_provider_version=copied.source_provider_version,
                    renderer_id=None,
                    renderer_version=None,
                    renderer_contract_version=None,
                    input_references=(),
                    producer_source_digest_claim=plan_entry.producer_source_digest_claim,
                    source_stability_result=copied.source_stability_result,
                    configuration_digest=None,
                    template_digest=None,
                    verification_result="verified",
                    recorded_at=sealed_at,
                    recorded_by=sealed_by,
                )
            elif prepared.generated_bytes is not None:
                generated = prepared.generated_bytes
                materialization = SnapshotMaterializationRecord(
                    materialization_id=materialization_id,
                    snapshot_edition=edition_ref,
                    materialization_kind="generated_vitrine",
                    candidate_id=None,
                    selection_id=None,
                    placement_id=None,
                    source_artifact=None,
                    source_digest=None,
                    output_digest=generated.output_digest,
                    byte_size=generated.byte_size,
                    materialized_at=sealed_at,
                    materialized_by=sealed_by,
                )
                provenance_record = SnapshotMaterializationProvenance(
                    snapshot_materialization_provenance_id=id_factory(
                        "snapshot_materialization_provenance"
                    ),
                    materialization_id=materialization_id,
                    snapshot_edition=edition_ref,
                    entry_plan_id=plan_entry.entry_plan_id,
                    source_provider_id=None,
                    source_provider_version=None,
                    renderer_id=generated.renderer_id,
                    renderer_version=generated.renderer_version,
                    renderer_contract_version=generated.renderer_contract_version,
                    input_references=plan_entry.input_references,
                    producer_source_digest_claim=None,
                    source_stability_result="not_applicable",
                    configuration_digest=generated.configuration_digest,
                    template_digest=generated.template_digest,
                    verification_result="verified",
                    recorded_at=sealed_at,
                    recorded_by=sealed_by,
                )
            else:
                raise SnapshotWorkflowError(
                    "snapshot.final_verification_failed",
                    "Prepared Entry has no copied or generated byte result.",
                    stage="seal_records",
                )
            assert plan_entry.target_relative_path is not None
            materialized_media_type = _materialized_entry_media_type(plan_entry, prepared)
            if materialized_media_type is None:
                raise SnapshotWorkflowError(
                    "snapshot.final_verification_failed",
                    "Prepared Entry has no materialized media type.",
                    stage="seal_records",
                )
            entry_record = SnapshotEntry(
                snapshot_entry_id=snapshot_entry_id,
                snapshot_edition=edition_ref,
                materialization_id=materialization_id,
                section_id=plan_entry.section_id,
                ordinal=plan_entry.ordinal,
                relative_path=plan_entry.target_relative_path,
                media_type=materialized_media_type,
                content_class=plan_entry.content_class,
                display_title=None,
                source_placement_id=plan_entry.placement_id,
            )
            materializations.append(materialization)
            entries.append(entry_record)
            provenance.append(provenance_record)
            materialization_ids_by_plan[plan_entry.entry_plan_id] = materialization_id
            entry_ids_by_plan[plan_entry.entry_plan_id] = snapshot_entry_id
            outcomes.append(
                SnapshotEntryOutcome(
                    entry_plan_id=plan_entry.entry_plan_id,
                    disposition="included",
                    materialization_id=materialization_id,
                )
            )
        elif prepared.disposition == "omission_pending":
            if (
                plan_entry.candidate_id is None
                and plan_entry.selection_id is None
                and plan_entry.placement_id is None
            ):
                raise SnapshotWorkflowError(
                    "snapshot.final_verification_failed",
                    "Pending omission cannot satisfy the frozen source-backed Omission contract.",
                    stage="seal_records",
                )
            assert prepared.pending_omission_reason is not None
            omission_id = id_factory("snapshot_omission")
            omission = SnapshotOmission(
                snapshot_omission_id=omission_id,
                snapshot_edition=edition_ref,
                candidate_id=plan_entry.candidate_id,
                selection_id=plan_entry.selection_id,
                placement_id=plan_entry.placement_id,
                reason_code=prepared.pending_omission_reason,
                audience_context_id=execution.plan.audience_context_id,
                recorded_at=sealed_at,
                recorded_by=sealed_by,
                note=f"Permitted by Entry Plan {plan_entry.entry_plan_id}.",
            )
            omissions.append(omission)
            omission_ids_by_plan[plan_entry.entry_plan_id] = omission_id
            outcomes.append(
                SnapshotEntryOutcome(
                    entry_plan_id=plan_entry.entry_plan_id,
                    disposition="omitted_permitted",
                    omission_id=omission_id,
                )
            )
        else:
            materialization_id = id_factory("snapshot_materialization")
            materialization = SnapshotMaterializationRecord(
                materialization_id=materialization_id,
                snapshot_edition=edition_ref,
                materialization_kind="reference_only",
                candidate_id=plan_entry.candidate_id,
                selection_id=plan_entry.selection_id,
                placement_id=plan_entry.placement_id,
                source_artifact=plan_entry.source_artifact,
                source_digest=None,
                output_digest=None,
                byte_size=None,
                materialized_at=sealed_at,
                materialized_by=sealed_by,
            )
            provenance_record = SnapshotMaterializationProvenance(
                snapshot_materialization_provenance_id=id_factory(
                    "snapshot_materialization_provenance"
                ),
                materialization_id=materialization_id,
                snapshot_edition=edition_ref,
                entry_plan_id=plan_entry.entry_plan_id,
                source_provider_id=None,
                source_provider_version=None,
                renderer_id=None,
                renderer_version=None,
                renderer_contract_version=None,
                input_references=(),
                producer_source_digest_claim=plan_entry.producer_source_digest_claim,
                source_stability_result="not_applicable",
                configuration_digest=None,
                template_digest=None,
                verification_result="verified",
                recorded_at=sealed_at,
                recorded_by=sealed_by,
            )
            materializations.append(materialization)
            provenance.append(provenance_record)
            materialization_ids_by_plan[plan_entry.entry_plan_id] = materialization_id
            outcomes.append(
                SnapshotEntryOutcome(
                    entry_plan_id=plan_entry.entry_plan_id,
                    disposition="reference_only",
                )
            )

    manifest_id = id_factory("snapshot_manifest")
    seal_id = id_factory("snapshot_seal")
    manifest = SnapshotManifest(
        manifest_id=manifest_id,
        manifest_contract_version=SNAPSHOT_INTERNAL_MANIFEST_CONTRACT_VERSION,
        snapshot_edition=edition_ref,
        portfolio_id=execution.plan.portfolio_id,
        portfolio_subject_id=execution.plan.portfolio_subject_id,
        profile_binding_id=execution.plan.profile_binding_id,
        profile_revision=execution.plan.profile_revision,
        composition_revision=execution.plan.composition_revision,
        audience_context_id=execution.plan.audience_context_id,
        entry_ids=tuple(sorted(item.snapshot_entry_id for item in entries)),
        omission_ids=tuple(sorted(item.snapshot_omission_id for item in omissions)),
        created_at=sealed_at,
        created_by=sealed_by,
    )

    manifest_entries: list[JsonValue] = [
        _manifest_entry_json(
            plan_entry,
            prepared,
            materialization_id=materialization_ids_by_plan.get(
                plan_entry.entry_plan_id
            ),
            snapshot_entry_id=entry_ids_by_plan.get(plan_entry.entry_plan_id),
            snapshot_omission_id=omission_ids_by_plan.get(plan_entry.entry_plan_id),
        )
        for plan_entry, prepared in zip(
            execution.plan.entry_plans, execution.entries, strict=True
        )
    ]
    export_plans_json: list[JsonValue] = []
    for item in execution.plan.export_plans:
        export_value: dict[str, JsonValue] = {
            "export_plan_id": item.export_plan_id,
            "export_format": item.export_format,
            "export_contract_version": item.export_contract_version,
            "included_entry_plan_ids": _strings_json(item.included_entry_plan_ids),
            "excluded_entry_plan_ids": _strings_json(item.excluded_entry_plan_ids),
            "configuration_digest": _digest_json(item.configuration_digest),
        }
        export_plans_json.append(export_value)
    logical_entries: list[JsonValue] = [
        _logical_entry_json(plan_entry, prepared)
        for plan_entry, prepared in zip(
            execution.plan.entry_plans, execution.entries, strict=True
        )
    ]
    logical_value: dict[str, JsonValue] = {
        "contract_version": SNAPSHOT_LOGICAL_INVENTORY_CONTRACT_VERSION,
        "entries": logical_entries,
    }
    manifest_value: dict[str, JsonValue] = {
        "contract_version": SNAPSHOT_INTERNAL_MANIFEST_CONTRACT_VERSION,
        "snapshot_edition": {
            "snapshot_series_id": edition_ref.snapshot_series_id,
            "edition_number": edition_ref.edition_number,
        },
        "portfolio_id": execution.plan.portfolio_id,
        "portfolio_subject_id": execution.plan.portfolio_subject_id,
        "profile_binding_id": execution.plan.profile_binding_id,
        "profile_revision": {
            "portfolio_profile_id": execution.plan.profile_revision.portfolio_profile_id,
            "profile_revision": execution.plan.profile_revision.profile_revision,
        },
        "composition_revision": execution.plan.composition_revision,
        "audience_context_id": execution.plan.audience_context_id,
        "snapshot_build_request_id": execution.plan.snapshot_build_request_id,
        "snapshot_build_plan_id": execution.plan.snapshot_build_plan_id,
        "snapshot_build_attempt_id": execution.attempt.snapshot_build_attempt_id,
        "plan_fingerprint": execution.plan.plan_fingerprint,
        "snapshot_manifest_id": manifest_id,
        "snapshot_seal_id": seal_id,
        "entry_ids": _strings_json(
            tuple(sorted(item.snapshot_entry_id for item in entries))
        ),
        "omission_ids": _strings_json(
            tuple(sorted(item.snapshot_omission_id for item in omissions))
        ),
        "materialization_ids": _strings_json(
            tuple(sorted(item.materialization_id for item in materializations))
        ),
        "materialization_provenance_ids": _strings_json(
            tuple(
                sorted(
                    item.snapshot_materialization_provenance_id
                    for item in provenance
                )
            )
        ),
        "path_policy_id": execution.plan.path_policy_id,
        "digest_policy_id": execution.plan.digest_policy_id,
        "entries": manifest_entries,
        "export_plans": export_plans_json,
        "logical_inventory": logical_value,
    }
    manifest_bytes = canonical_snapshot_json_bytes(manifest_value)
    manifest_digest = snapshot_manifest_digest(manifest_value)
    if snapshot_digest(manifest_bytes) != manifest_digest:
        raise AssertionError("canonical manifest digest implementation disagrees")
    logical_digest = snapshot_logical_inventory_digest(logical_value)
    seal = SnapshotSeal(
        seal_id=seal_id,
        snapshot_edition=edition_ref,
        manifest_id=manifest_id,
        manifest_digest=manifest_digest,
        logical_inventory_digest=logical_digest,
        sealed_at=sealed_at,
        sealed_by=sealed_by,
    )
    edition = SnapshotEdition(
        snapshot_series_id=edition_ref.snapshot_series_id,
        edition_number=edition_ref.edition_number,
        portfolio_id=execution.plan.portfolio_id,
        portfolio_subject_id=execution.plan.portfolio_subject_id,
        profile_binding_id=execution.plan.profile_binding_id,
        profile_revision=execution.plan.profile_revision,
        composition_revision=execution.plan.composition_revision,
        audience_context_id=execution.plan.audience_context_id,
        manifest_id=manifest_id,
        seal_id=seal_id,
        created_at=sealed_at,
        created_by=sealed_by,
        predecessor_edition=predecessor_edition,
    )
    records: tuple[VitrineRecord, ...] = (
        *materializations,
        *entries,
        *omissions,
        manifest,
        seal,
        edition,
        *provenance,
    )
    return records, manifest, seal, edition, tuple(outcomes), manifest_bytes


def seal_snapshot_build_attempt(
    workspace_root: str | Path,
    *,
    execution: SnapshotAttemptExecutionResult,
    expected_state_revision: int,
    sealed_by: ActorAttribution,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> SnapshotSealResult:
    """Verify, seal, publish, and terminalize one successfully executed Attempt."""

    if not isinstance(execution, SnapshotAttemptExecutionResult):
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot sealing requires a successful Attempt execution result.",
            stage="seal_request",
        )
    if not isinstance(sealed_by, ActorAttribution):
        raise SnapshotWorkflowError(
            "snapshot.invalid_request",
            "Snapshot sealing actor attribution is invalid.",
            stage="seal_request",
        )
    loaded = _load_state(workspace_root, expected_state_revision)
    if execution.state_revision != loaded.state_revision:
        raise SnapshotWorkflowError(
            "snapshot.state_conflict",
            "Snapshot state changed after Attempt execution and before sealing.",
            stage="seal_concurrency",
        )
    attempt = _attempt(loaded.records, execution.attempt.snapshot_build_attempt_id)
    plan = _plan(loaded.records, attempt.snapshot_build_plan_id)
    if attempt != execution.attempt or plan != execution.plan:
        raise SnapshotWorkflowError(
            "snapshot.seal_conflict",
            "Snapshot execution result no longer matches its canonical Attempt and Plan.",
            stage="seal_request",
        )
    if any(
        isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
        for item in loaded.records
    ):
        raise SnapshotWorkflowError(
            "snapshot.attempt_conflict",
            "Snapshot Build Attempt already has a terminal Result.",
            stage="seal_request",
        )
    _require_attempt_series_lock(
        workspace_root, plan=plan, attempt=attempt
    )
    try:
        staging = load_snapshot_staging(
            workspace_root, attempt.snapshot_build_attempt_id
        )
    except SnapshotCustodyError as error:
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=error.code,
            summary="Snapshot Attempt staging is unavailable at the sealing boundary.",
            clock=clock,
            id_factory=id_factory,
        )
        raise SnapshotWorkflowError(
            "snapshot.staging_invalid",
            "Snapshot Attempt failed because its staging tree is unavailable or invalid.",
            stage="seal_request",
        ) from error
    try:
        if next(staging.internal_root.iterdir(), None) is not None:
            raise SnapshotWorkflowError(
                "snapshot.seal_conflict",
                "Snapshot staging contains unresolved prior sealing metadata.",
                stage="seal_request",
            )
    except OSError as error:
        raise SnapshotWorkflowError(
            "snapshot.staging_invalid",
            "Snapshot internal staging could not be inspected before sealing.",
            stage="seal_request",
        ) from error

    try:
        _verify_prepared_snapshot_bytes(staging, plan, execution.entries)
    except SnapshotWorkflowError as error:
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code="snapshot.final_verification_failed",
            summary="Snapshot Attempt failed final pre-seal byte verification.",
            clock=clock,
            id_factory=id_factory,
        )
        raise error

    edition_number, predecessor_edition = _next_edition_identity(
        loaded.records, plan.snapshot_series_id
    )
    edition_ref = SnapshotEditionRef(
        snapshot_series_id=plan.snapshot_series_id,
        edition_number=edition_number,
    )
    sealed_at = _now(clock)
    (
        sealed_records,
        manifest,
        seal,
        edition,
        entry_outcomes,
        manifest_bytes,
    ) = _build_sealed_records(
        execution=execution,
        edition_ref=edition_ref,
        predecessor_edition=predecessor_edition,
        sealed_at=sealed_at,
        sealed_by=sealed_by,
        id_factory=id_factory,
    )

    try:
        write_staging_internal_bytes_exclusive(staging, "manifest.json", manifest_bytes)
        if read_staging_internal_bytes(staging, "manifest.json") != manifest_bytes:
            raise SnapshotCustodyError(
                "snapshot.staging_invalid",
                "Snapshot internal manifest failed exact byte re-read verification.",
            )
    except SnapshotCustodyError as error:
        _persist_execution_failure(
            workspace_root,
            loaded=loaded,
            plan=plan,
            attempt=attempt,
            code=error.code,
            summary="Snapshot Attempt failed while writing its canonical internal manifest.",
            clock=clock,
            id_factory=id_factory,
        )
        raise SnapshotWorkflowError(
            "snapshot.final_verification_failed",
            "Snapshot Attempt failed before its Edition could be sealed.",
            stage="seal_manifest",
        ) from error

    sealed_state_revision = _commit(
        workspace_root,
        sealed_records,
        expected_state_revision=loaded.state_revision,
        current_records=loaded.records,
    )

    publication_finding: SnapshotBuildFinding | None = None
    edition_path: Path | None = None
    try:
        edition_path = publish_snapshot_staging_as_edition(
            staging,
            snapshot_series_id=edition.snapshot_series_id,
            edition_number=edition.edition_number,
        )
    except SnapshotCustodyError as error:
        publication_finding = SnapshotBuildFinding(
            code=error.code,
            severity="error",
            blocking=False,
            summary=(
                "Snapshot Edition was sealed canonically, but verified staging "
                "could not be published to final Edition custody."
            ),
        )

    lock_cleanup_finding = _release_attempt_series_lock_best_effort(
        workspace_root, plan=plan, attempt=attempt
    )
    cleanup_findings = (
        () if lock_cleanup_finding is None else (lock_cleanup_finding,)
    )
    attempt_result_id = id_factory("snapshot_attempt_result")
    terminal_outcome = (
        "sealed"
        if publication_finding is None and lock_cleanup_finding is None
        else "partial_success_after_seal"
    )
    attempt_result = SnapshotBuildAttemptResult(
        snapshot_build_attempt_result_id=attempt_result_id,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        completed_at=_now(clock),
        terminal_outcome=terminal_outcome,
        entry_outcomes=entry_outcomes,
        findings=(() if publication_finding is None else (publication_finding,)),
        cleanup_findings=cleanup_findings,
        sealed_snapshot_edition=edition.reference,
    )
    build_provenance = SnapshotEditionBuildProvenance(
        snapshot_edition_build_provenance_id=id_factory(
            "snapshot_edition_build_provenance"
        ),
        snapshot_edition=edition.reference,
        snapshot_build_request_id=plan.snapshot_build_request_id,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        snapshot_build_attempt_result_id=attempt_result_id,
        portfolio_id=plan.portfolio_id,
        profile_binding_id=plan.profile_binding_id,
        profile_revision=plan.profile_revision,
        composition_revision=plan.composition_revision,
        audience_context_id=plan.audience_context_id,
        builder_contract_id=plan.builder_contract_id,
        builder_contract_version=plan.builder_contract_version,
        path_policy_id=plan.path_policy_id,
        digest_policy_id=plan.digest_policy_id,
        recorded_at=attempt_result.completed_at,
        recorded_by=sealed_by,
    )
    try:
        final_state_revision = _commit(
            workspace_root,
            (attempt_result, build_provenance),
            expected_state_revision=sealed_state_revision,
            current_records=(*loaded.records, *sealed_records),
        )
    except SnapshotWorkflowError as error:
        if error.code == "snapshot.state_conflict":
            raise SnapshotWorkflowError(
                "snapshot.post_seal_state_conflict",
                "Snapshot Edition is sealed, but Attempt terminalization encountered a concurrent state change.",
                stage="post_seal_concurrency",
            ) from error
        raise

    return SnapshotSealResult(
        state_revision=final_state_revision,
        edition=edition,
        manifest=manifest,
        seal=seal,
        attempt_result=attempt_result,
        edition_path=edition_path,
    )


__all__ = [
    "SNAPSHOT_BUILDER_CONTRACT_ID",
    "SNAPSHOT_BUILDER_CONTRACT_VERSION",
    "SNAPSHOT_SERVICE_CODES",
    "SnapshotAttemptExecutionResult",
    "SnapshotAttemptStartResult",
    "SnapshotPreparedEntry",
    "SnapshotSealResult",
    "SnapshotMutationResult",
    "SnapshotWorkflowError",
    "create_snapshot_series",
    "execute_snapshot_build_attempt",
    "plan_snapshot_build",
    "request_snapshot_build",
    "seal_snapshot_build_attempt",
    "start_snapshot_build_attempt",
]
