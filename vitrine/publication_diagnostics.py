"""Read-only canonical Publication and authorized read diagnostics for Vitrine.

Issue #62 reuses Core canonical Publication, registration, series, producer Profile,
and compatibility authority. Metadata preflight performs no manifest I/O. The
explicit Slice 4 read probe crosses that boundary only after deployment-owned
authorization, then verifies exact Core bytes, invokes the audited producer public
reader, and runs the selected pure live projection. Neither path persists Candidate
state, builds Snapshots, accesses producer Artifacts, or repairs source state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pds_core.academic_work_registration_storage import (
    AcademicWorkRegistrationIntegrityError,
    AcademicWorkRegistrationNotFoundError,
    AcademicWorkRegistrationReadError,
    load_academic_work_registration_revision,
)
from pds_core.academic_work_registrations import AcademicWorkRegistration
from pds_core.publication_compatibility import (
    PublicationProducerProfileError,
    PublicationProducerRegistry,
    build_publication_producer_registry,
    evaluate_publication_compatibility,
)
from pds_core.publication_records import PublicationRecord
from pds_core.publication_storage import (
    PublicationIntegrityError,
    PublicationReadError,
    list_publication_record_set,
)
from pds_core.registry_services import (
    RegistryServiceIntegrityError,
    RegistryServiceNotFoundError,
    RegistryServiceValidationError,
    RegistryServiceWriteError,
    get_canonical_publication_record,
    get_canonical_publication_withdrawal,
)

from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
    DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS,
    CompatibilityDiagnosticError,
    CrossProducerCompatibilityDiagnostic,
    diagnose_audited_reader_readiness,
    explain_live_adapter_support,
)
from vitrine.models.common import require_identifier, require_lower_identifier
from vitrine.models.errors import VitrineModelValidationError
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterRegistry,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProducerReaderError,
    build_adapter_registry,
)
from vitrine.producer_reader_services import (
    ProducerReaderServiceError,
    SourceReadAuthorizationGate,
    SourceReadAuthorizationRequest,
    authorize_source_read,
    build_audited_installed_producer_reader,
    read_verified_publication_manifest_bytes,
)
from vitrine.released_producer_contracts import RELEASED_PRODUCER_CONTRACT_BY_MODULE

COMPATIBILITY_SOURCE_READ_OPERATION: Final[str] = "compatibility_source_read"


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationCompatibilityDiagnostics:
    """Transient metadata-only preflight for one explicit canonical Publication."""

    publication_id: str
    producer_module_id: str | None
    overall: CrossProducerCompatibilityDiagnostic
    checks: tuple[CrossProducerCompatibilityDiagnostic, ...]

    def __post_init__(self) -> None:
        try:
            publication_id = require_identifier(self.publication_id, "publication_id")
            producer_module_id = (
                None
                if self.producer_module_id is None
                else require_lower_identifier(
                    self.producer_module_id, "producer_module_id"
                )
            )
        except VitrineModelValidationError as error:
            raise CompatibilityDiagnosticError(str(error)) from error
        checks = tuple(self.checks)
        if not isinstance(self.overall, CrossProducerCompatibilityDiagnostic):
            raise CompatibilityDiagnosticError(
                "overall must be CrossProducerCompatibilityDiagnostic."
            )
        if any(
            not isinstance(item, CrossProducerCompatibilityDiagnostic)
            for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "checks must contain compatibility diagnostics."
            )
        if self.overall.publication_id != publication_id or any(
            item.publication_id != publication_id for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "Publication diagnostics must name the requested Publication."
            )
        if producer_module_id is not None and any(
            item.producer_module_id not in {None, producer_module_id}
            for item in (self.overall, *checks)
        ):
            raise CompatibilityDiagnosticError(
                "Publication diagnostics must belong to one producer."
            )
        object.__setattr__(self, "publication_id", publication_id)
        object.__setattr__(self, "producer_module_id", producer_module_id)
        object.__setattr__(self, "checks", checks)

    @property
    def ready(self) -> bool:
        return self.overall.outcome == "ready"


def _diagnostic(
    *,
    publication_id: str,
    producer_module_id: str | None,
    outcome: str,
    code: str,
    stage: str,
    reason_codes: tuple[str, ...],
    summary: str,
    next_action: str,
    safe_fields: tuple[tuple[str, str], ...] = (),
    scope: str = "publication_compatibility",
    adapter_id: str | None = None,
) -> CrossProducerCompatibilityDiagnostic:
    return CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=(
            CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
        ),
        scope=scope,
        outcome=outcome,
        code=code,
        stage=stage,
        producer_module_id=producer_module_id,
        publication_id=publication_id,
        adapter_id=adapter_id,
        reason_codes=reason_codes,
        safe_fields=safe_fields,
        summary=summary,
        next_action=next_action,
    )


def _report(
    publication_id: str,
    producer_module_id: str | None,
    checks: list[CrossProducerCompatibilityDiagnostic],
    *,
    ready: bool = False,
) -> PublicationCompatibilityDiagnostics:
    if ready:
        overall = _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer_module_id,
            outcome="ready",
            code="compatibility.publication_ready",
            stage="publication_compatibility",
            reason_codes=("compatibility.publication_ready",),
            summary=(
                "The canonical Publication metadata path is ready for an explicit "
                "authorized source-read probe."
            ),
            next_action=(
                "No metadata compatibility action is required. Authorization and "
                "manifest-byte verification remain separate later checks."
            ),
        )
    else:
        blocked = next(
            (
                item
                for item in checks
                if item.outcome
                not in {"ready", "supported", "not_applicable", "not_checked"}
            ),
            checks[-1],
        )
        overall = _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer_module_id,
            outcome=blocked.outcome,
            code=blocked.code,
            stage="publication_compatibility",
            reason_codes=blocked.reason_codes,
            safe_fields=(("blocked_stage", blocked.stage),),
            summary=(
                "The canonical Publication metadata path is not ready for deeper "
                "source reading."
            ),
            next_action=(
                "Resolve the blocking metadata diagnostic. Vitrine does not cross "
                "the failed boundary or substitute another Publication automatically."
            ),
        )
    return PublicationCompatibilityDiagnostics(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        overall=overall,
        checks=tuple(checks),
    )


def _canonical_publication(
    workspace_root: str | Path,
    publication_id: str,
) -> tuple[PublicationRecord | None, CrossProducerCompatibilityDiagnostic]:
    try:
        publication = get_canonical_publication_record(workspace_root, publication_id)
    except RegistryServiceValidationError as error:
        raise CompatibilityDiagnosticError(
            "publication_id is not a valid Core Publication identifier."
        ) from error
    except RegistryServiceNotFoundError:
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=None,
            outcome="unavailable",
            code="candidate.canonical_publication_missing",
            stage="canonical_publication",
            reason_codes=("compatibility.canonical_publication_missing",),
            summary="The requested canonical Core Publication does not exist.",
            next_action=(
                "Review Core Publication history. Vitrine does not substitute a "
                "different Publication automatically."
            ),
        )
    except (RegistryServiceIntegrityError, RegistryServiceWriteError):
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=None,
            outcome="integrity_failed",
            code="candidate.canonical_publication_invalid",
            stage="canonical_publication",
            reason_codes=("compatibility.canonical_publication_invalid",),
            summary="The requested canonical Core Publication could not be validated.",
            next_action="Reconcile canonical Core Publication state before continuing.",
        )
    return publication, _diagnostic(
        publication_id=publication_id,
        producer_module_id=publication.work.module_id,
        outcome="ready",
        code="compatibility.canonical_publication_loaded",
        stage="canonical_publication",
        reason_codes=("compatibility.canonical_publication_loaded",),
        safe_fields=(
            ("core_publication_schema_version", publication.schema_version),
            ("manifest_contract_version", publication.manifest_contract_version),
            ("publication_kind", publication.publication_kind),
            ("record_set_id", publication.record_set_id),
            ("record_set_revision", str(publication.record_set_revision)),
        ),
        summary="The requested canonical Core Publication loaded successfully.",
        next_action="Continue with its exact referenced Registration revision.",
    )


def _registration(
    workspace_root: str | Path,
    publication: PublicationRecord,
) -> tuple[AcademicWorkRegistration | None, CrossProducerCompatibilityDiagnostic]:
    publication_id = publication.publication_id
    producer = publication.work.module_id
    if publication.publication_kind != "academic_result_set":
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="not_applicable",
            code="compatibility.registration_not_applicable",
            stage="registration",
            reason_codes=("compatibility.registration_not_applicable",),
            summary="This Publication kind does not use an Academic Work Registration.",
            next_action="Continue with canonical Publication series state.",
        )
    revision = publication.academic_work_registration_revision
    if revision is None:
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="unavailable",
            code="candidate.registration_missing",
            stage="registration",
            reason_codes=("compatibility.registration_missing",),
            summary="The academic Publication has no referenced Registration revision.",
            next_action=(
                "Reconcile the producer/Core Publication. Vitrine does not invent a "
                "Registration revision."
            ),
        )
    try:
        value = load_academic_work_registration_revision(
            workspace_root, publication.work, revision
        )
    except AcademicWorkRegistrationNotFoundError:
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="unavailable",
            code="candidate.registration_missing",
            stage="registration",
            reason_codes=("compatibility.registration_missing",),
            safe_fields=(("registration_revision", str(revision)),),
            summary="The referenced Academic Work Registration revision does not exist.",
            next_action=(
                "Reconcile canonical Registration history. Vitrine does not replace "
                "the missing revision with a current one."
            ),
        )
    except (AcademicWorkRegistrationIntegrityError, AcademicWorkRegistrationReadError):
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="integrity_failed",
            code="candidate.registration_mismatch",
            stage="registration",
            reason_codes=("compatibility.registration_mismatch",),
            safe_fields=(("registration_revision", str(revision)),),
            summary="The referenced Academic Work Registration could not be validated.",
            next_action="Reconcile canonical Registration history before continuing.",
        )
    if value.work != publication.work or value.registration_revision != revision:
        return None, _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="integrity_failed",
            code="candidate.registration_mismatch",
            stage="registration",
            reason_codes=("compatibility.registration_mismatch",),
            summary="The referenced Registration disagrees with Publication identity.",
            next_action="Reconcile canonical Registration history before continuing.",
        )
    return value, _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer,
        outcome="ready",
        code="compatibility.registration_loaded",
        stage="registration",
        reason_codes=("compatibility.registration_loaded",),
        safe_fields=(
            ("producer_contract_version", value.producer_contract_version),
            ("registration_revision", str(value.registration_revision)),
        ),
        summary="The exact referenced Academic Work Registration loaded successfully.",
        next_action="Continue with canonical Publication series state.",
    )


def _series_state(
    workspace_root: str | Path,
    publication: PublicationRecord,
) -> CrossProducerCompatibilityDiagnostic:
    publication_id = publication.publication_id
    producer = publication.work.module_id
    try:
        series = list_publication_record_set(
            workspace_root,
            publication.work,
            publication.publication_kind,
            publication.record_set_id,
        )
    except (PublicationIntegrityError, PublicationReadError):
        return _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="integrity_failed",
            code="candidate.series_conflict",
            stage="series_state",
            reason_codes=("compatibility.publication_series_conflict",),
            summary="The canonical Publication series could not be validated.",
            next_action="Reconcile Core Publication series state before continuing.",
        )
    successor_ids = {
        item.supersedes_publication_id
        for item in series
        if item.supersedes_publication_id is not None
    }
    heads = tuple(item for item in series if item.publication_id not in successor_ids)
    if len(heads) != 1:
        return _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="failed",
            code="candidate.series_conflict",
            stage="series_state",
            reason_codes=("compatibility.publication_series_conflict",),
            safe_fields=(("head_count", str(len(heads))),),
            summary="The canonical Publication series has no unique explicit head.",
            next_action="Reconcile Core Publication history; do not select by ordering.",
        )
    try:
        withdrawal = get_canonical_publication_withdrawal(
            workspace_root, publication_id
        )
    except (
        RegistryServiceNotFoundError,
        RegistryServiceIntegrityError,
        RegistryServiceWriteError,
    ):
        return _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="integrity_failed",
            code="candidate.series_conflict",
            stage="series_state",
            reason_codes=("compatibility.publication_series_conflict",),
            summary="Canonical Publication withdrawal state could not be validated.",
            next_action="Reconcile Core Publication withdrawal state before continuing.",
        )
    head = heads[0]
    is_head = head.publication_id == publication_id
    is_withdrawn = withdrawal is not None
    if is_head and not is_withdrawn:
        return _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.publication_current_selectable",
            stage="series_state",
            reason_codes=("compatibility.publication_current_selectable",),
            safe_fields=(
                ("current_series_head_publication_id", head.publication_id),
                ("observed_series_state", "current_selectable"),
                ("observed_withdrawal_state", "not_withdrawn"),
            ),
            summary="The requested Publication is the current selectable series head.",
            next_action="Continue with producer Profile compatibility.",
        )
    state = "withdrawn_head" if is_head else (
        "withdrawn_historical" if is_withdrawn else "historical"
    )
    reason = (
        "compatibility.publication_withdrawn"
        if is_withdrawn
        else "compatibility.publication_historical"
    )
    return _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer,
        outcome="not_selectable",
        code="candidate.publication_not_selectable",
        stage="series_state",
        reason_codes=(reason,),
        safe_fields=(
            ("current_series_head_publication_id", head.publication_id),
            ("observed_series_state", state),
            ("observed_withdrawal_state", "withdrawn" if is_withdrawn else "not_withdrawn"),
        ),
        summary=(
            "The requested Publication is withdrawn and is not selectable."
            if is_withdrawn
            else "The requested Publication is historical and is not the current selectable head."
        ),
        next_action=(
            "Review Core Publication history and explicitly choose the intended "
            "workflow. Vitrine does not substitute the current head automatically."
        ),
    )


def _support_request(
    publication: PublicationRecord,
    registration: AcademicWorkRegistration | None,
) -> ProducerAdapterSupportRequest:
    source = publication.source_record
    return ProducerAdapterSupportRequest(
        producer_module_id=publication.work.module_id,
        core_publication_schema_version=publication.schema_version,
        publication_kind=publication.publication_kind,
        manifest_contract_version=publication.manifest_contract_version,
        producer_contract_version=(
            registration.producer_contract_version if registration is not None else None
        ),
        source_record_kind=source.record_kind if source is not None else None,
        source_record_contract_version=(
            source.contract_version if source is not None else None
        ),
        capabilities=tuple(publication.capabilities),
    )


def _copy_for_publication(
    value: CrossProducerCompatibilityDiagnostic,
    publication_id: str,
    *,
    stage: str | None = None,
) -> CrossProducerCompatibilityDiagnostic:
    return CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=value.diagnostic_contract_version,
        scope=value.scope,
        outcome=value.outcome,
        code=value.code,
        stage=value.stage if stage is None else stage,
        producer_module_id=value.producer_module_id,
        publication_id=publication_id,
        adapter_id=value.adapter_id,
        reason_codes=value.reason_codes,
        safe_fields=value.safe_fields,
        summary=value.summary,
        next_action=value.next_action,
    )


def diagnose_publication_compatibility(
    workspace_root: str | Path,
    publication_id: str,
    *,
    producer_registry: PublicationProducerRegistry | None = None,
    adapter_registry: ProducerProjectionAdapterRegistry | None = None,
) -> PublicationCompatibilityDiagnostics:
    """Diagnose canonical Publication metadata without manifest or Artifact I/O."""

    try:
        requested_id = require_identifier(publication_id, "publication_id")
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error
    adapters = build_adapter_registry() if adapter_registry is None else adapter_registry
    if not isinstance(adapters, ProducerProjectionAdapterRegistry):
        raise CompatibilityDiagnosticError(
            "adapter_registry must be ProducerProjectionAdapterRegistry."
        )

    checks: list[CrossProducerCompatibilityDiagnostic] = []
    publication, canonical = _canonical_publication(workspace_root, requested_id)
    checks.append(canonical)
    if publication is None:
        return _report(requested_id, None, checks)
    producer = publication.work.module_id

    registration, registration_check = _registration(workspace_root, publication)
    checks.append(registration_check)
    if registration_check.outcome not in {"ready", "not_applicable"}:
        return _report(requested_id, producer, checks)

    series_check = _series_state(workspace_root, publication)
    checks.append(series_check)
    if series_check.outcome != "ready":
        return _report(requested_id, producer, checks)

    request = _support_request(publication, registration)
    if producer in DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS:
        fixture = _copy_for_publication(
            explain_live_adapter_support(request, registry=adapters),
            requested_id,
            stage="fixture_boundary",
        )
        checks.append(fixture)
        return _report(requested_id, producer, checks)

    profiles = producer_registry
    if profiles is None:
        try:
            profiles = build_publication_producer_registry(
                explicit_profiles=(), discover_installed=True
            )
        except Exception:
            checks.append(
                _diagnostic(
                    publication_id=requested_id,
                    producer_module_id=producer,
                    outcome="failed",
                    code="compatibility.core_profile_discovery_failed",
                    stage="core_profile",
                    reason_codes=("compatibility.core_profile_discovery_failed",),
                    summary="Core producer Profile discovery could not be completed safely.",
                    next_action="Repair installed producer Profile discovery before continuing.",
                )
            )
            return _report(requested_id, producer, checks)
    elif not isinstance(profiles, PublicationProducerRegistry):
        raise CompatibilityDiagnosticError(
            "producer_registry must be PublicationProducerRegistry."
        )
    assert profiles is not None

    profile = profiles.get(producer)
    if profile is None:
        checks.append(
            _diagnostic(
                publication_id=requested_id,
                producer_module_id=producer,
                outcome="unavailable",
                code="candidate.producer_profile_missing",
                stage="core_profile",
                reason_codes=("compatibility.core_profile_missing",),
                summary="Core did not provide a producer Profile for this Publication.",
                next_action=(
                    "Install or repair the producer Profile integration. Do not infer "
                    "compatibility from package name or version."
                ),
            )
        )
        return _report(requested_id, producer, checks)
    checks.append(
        _diagnostic(
            publication_id=requested_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.core_profile_discovered",
            stage="core_profile",
            reason_codes=("compatibility.core_profile_discovered",),
            safe_fields=(("producer_display_name", profile.display_name),),
            summary="Core resolved the producer's validated Publication Profile.",
            next_action="Evaluate Core-owned semantic compatibility.",
        )
    )

    try:
        core = evaluate_publication_compatibility(publication, profile, registration)
    except PublicationProducerProfileError:
        checks.append(
            _diagnostic(
                publication_id=requested_id,
                producer_module_id=producer,
                outcome="failed",
                code="candidate.producer_incompatible",
                stage="core_compatibility",
                reason_codes=("compatibility.core_contract_incompatible",),
                summary="Core producer compatibility evaluation could not be completed safely.",
                next_action=(
                    "Reconcile producer Profile and canonical Publication metadata. "
                    "Vitrine does not replace Core compatibility policy."
                ),
            )
        )
        return _report(requested_id, producer, checks)
    if not core.compatible:
        checks.append(
            _diagnostic(
                publication_id=requested_id,
                producer_module_id=producer,
                outcome="unsupported",
                code=core.codes[0],
                stage="core_compatibility",
                reason_codes=core.codes,
                safe_fields=(("core_compatibility_codes", ",".join(core.codes)),),
                summary="Core reports this producer semantic contract as incompatible.",
                next_action=(
                    "Reconcile or republish through the owning producer/Core workflow. "
                    "Do not make Vitrine accept an incompatible Core contract."
                ),
            )
        )
        return _report(requested_id, producer, checks)
    checks.append(
        _diagnostic(
            publication_id=requested_id,
            producer_module_id=producer,
            outcome="supported",
            code="compatibility.core_contract_supported",
            stage="core_compatibility",
            reason_codes=("compatibility.core_contract_supported",),
            summary="Core reports this Publication contract as producer-compatible.",
            next_action="Continue with exact Vitrine live adapter support.",
        )
    )

    adapter = _copy_for_publication(
        explain_live_adapter_support(request, registry=adapters),
        requested_id,
        stage="adapter_support",
    )
    checks.append(adapter)
    if adapter.outcome != "supported":
        return _report(requested_id, producer, checks)

    if producer not in RELEASED_PRODUCER_CONTRACT_BY_MODULE:
        checks.append(
            _diagnostic(
                publication_id=requested_id,
                producer_module_id=producer,
                outcome="not_checked",
                code="compatibility.publication_not_ready",
                stage="reader_distribution",
                reason_codes=("compatibility.reader_binding_not_audited",),
                summary="No #57-audited installed reader binding exists for this producer.",
                next_action="Add an explicit audited reader contract before producer reading.",
            )
        )
        return _report(requested_id, producer, checks)

    distribution, reader = diagnose_audited_reader_readiness(producer)
    distribution = _copy_for_publication(distribution, requested_id)
    reader = _copy_for_publication(reader, requested_id)
    checks.extend((distribution, reader))
    if distribution.outcome != "ready" or reader.outcome != "ready":
        return _report(requested_id, producer, checks)
    return _report(requested_id, producer, checks, ready=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationReadProbeDiagnostics:
    """Transient authorized read/projection probe for one explicit Publication."""

    publication_id: str
    producer_module_id: str | None
    overall: CrossProducerCompatibilityDiagnostic
    checks: tuple[CrossProducerCompatibilityDiagnostic, ...]
    projected_source_count: int | None = None

    def __post_init__(self) -> None:
        try:
            publication_id = require_identifier(self.publication_id, "publication_id")
            producer_module_id = (
                None
                if self.producer_module_id is None
                else require_lower_identifier(
                    self.producer_module_id, "producer_module_id"
                )
            )
        except VitrineModelValidationError as error:
            raise CompatibilityDiagnosticError(str(error)) from error
        checks = tuple(self.checks)
        if not isinstance(self.overall, CrossProducerCompatibilityDiagnostic):
            raise CompatibilityDiagnosticError(
                "overall must be CrossProducerCompatibilityDiagnostic."
            )
        if any(
            not isinstance(item, CrossProducerCompatibilityDiagnostic)
            for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "checks must contain compatibility diagnostics."
            )
        if self.overall.publication_id != publication_id or any(
            item.publication_id != publication_id for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "Read-probe diagnostics must name the requested Publication."
            )
        if producer_module_id is not None and any(
            item.producer_module_id not in {None, producer_module_id}
            for item in (self.overall, *checks)
        ):
            raise CompatibilityDiagnosticError(
                "Read-probe diagnostics must belong to one producer."
            )
        count = self.projected_source_count
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            raise CompatibilityDiagnosticError(
                "projected_source_count must be a nonnegative integer or null."
            )
        object.__setattr__(self, "publication_id", publication_id)
        object.__setattr__(self, "producer_module_id", producer_module_id)
        object.__setattr__(self, "checks", checks)

    @property
    def ready(self) -> bool:
        return self.overall.outcome == "ready"


def _probe_report(
    publication_id: str,
    producer_module_id: str | None,
    checks: list[CrossProducerCompatibilityDiagnostic],
    *,
    projected_source_count: int | None = None,
    ready: bool = False,
) -> PublicationReadProbeDiagnostics:
    if ready:
        overall = _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer_module_id,
            outcome="ready",
            code="compatibility.read_probe_ready",
            stage="read_probe",
            scope="source_read",
            reason_codes=("compatibility.read_probe_ready",),
            safe_fields=(
                ("projected_source_count", str(projected_source_count or 0)),
            ),
            summary=(
                "The explicit authorized producer read and pure live projection "
                "probe completed successfully."
            ),
            next_action=(
                "No read-path compatibility action is required. Candidate and "
                "portfolio policy remain separate workflows."
            ),
        )
    else:
        blocked = next(
            (
                item
                for item in reversed(checks)
                if item.outcome
                not in {"ready", "supported", "not_applicable", "not_checked"}
            ),
            checks[-1],
        )
        overall = _diagnostic(
            publication_id=publication_id,
            producer_module_id=producer_module_id,
            outcome=blocked.outcome,
            code=blocked.code,
            stage="read_probe",
            scope=blocked.scope,
            reason_codes=blocked.reason_codes
            or ("compatibility.read_probe_not_ready",),
            safe_fields=(("blocked_stage", blocked.stage),),
            summary=(
                "The explicit producer read/projection probe stopped at a "
                "fail-closed boundary."
            ),
            next_action=(
                "Resolve the blocking diagnostic. Vitrine does not cross the "
                "failed boundary or persist Candidate state from this probe."
            ),
        )
    return PublicationReadProbeDiagnostics(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        overall=overall,
        checks=tuple(checks),
        projected_source_count=projected_source_count,
    )


def _copy_probe_stage(
    value: CrossProducerCompatibilityDiagnostic,
    *,
    publication_id: str,
    stage: str,
) -> CrossProducerCompatibilityDiagnostic:
    return CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=value.diagnostic_contract_version,
        scope=value.scope,
        outcome=value.outcome,
        code=value.code,
        stage=stage,
        producer_module_id=value.producer_module_id,
        publication_id=publication_id,
        adapter_id=value.adapter_id,
        reason_codes=value.reason_codes,
        safe_fields=value.safe_fields,
        summary=value.summary,
        next_action=value.next_action,
    )


def _authorization_failure_diagnostic(
    *,
    publication_id: str,
    producer_module_id: str,
    error: ProducerReaderServiceError,
) -> CrossProducerCompatibilityDiagnostic:
    if error.code == "source_read.authorization_denied":
        outcome = "denied"
        reason = "compatibility.source_read_denied"
        summary = "The deployment authorization policy denied this source read."
    else:
        outcome = "unresolved"
        reason = "compatibility.source_read_unresolved"
        summary = "Source-read authorization could not be established."
    return _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        outcome=outcome,
        code=error.code,
        stage=error.stage,
        scope="source_read",
        reason_codes=(reason,),
        safe_fields=(("protected_source_inspected", "no"),),
        summary=summary,
        next_action=(
            "Review the deployment authorization policy. Vitrine did not inspect "
            "the protected manifest."
        ),
    )


def _manifest_failure_diagnostic(
    *,
    publication_id: str,
    producer_module_id: str,
    error: ProducerReaderServiceError,
) -> CrossProducerCompatibilityDiagnostic:
    if error.code == "source_read.manifest_missing":
        outcome = "unavailable"
        reason = "compatibility.manifest_missing"
        summary = "The authorized canonical Publication manifest is unavailable."
        action = (
            "Reconcile or republish through the owning producer/Core workflow."
        )
    else:
        outcome = "integrity_failed"
        reason = "compatibility.manifest_integrity_failed"
        summary = (
            "The authorized canonical Publication manifest failed Core integrity "
            "verification."
        )
        action = (
            "Reconcile producer/Core Publication integrity before reading again."
        )
    return _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        outcome=outcome,
        code=error.code,
        stage=error.stage,
        scope="source_read",
        reason_codes=(reason,),
        summary=summary,
        next_action=action,
    )


def _reader_failure_diagnostic(
    *,
    publication_id: str,
    producer_module_id: str,
    error: ProducerReaderError,
) -> CrossProducerCompatibilityDiagnostic:
    if error.code == "reader.unavailable":
        outcome = "unavailable"
        summary = "The audited producer public reader became unavailable."
    elif error.code == "reader.incompatible":
        outcome = "unsupported"
        summary = "The audited producer public reader API is incompatible."
    else:
        outcome = "failed"
        summary = (
            "The producer public reader rejected the authorized Core-verified "
            "manifest bytes."
        )
    return _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        outcome=outcome,
        code=error.code,
        stage=error.stage,
        scope="reader",
        reason_codes=("compatibility.reader_invocation_failed",),
        summary=summary,
        next_action=(
            "Repair the producer public reader/integration boundary. Vitrine does "
            "not expose the producer exception body."
        ),
        adapter_id=error.adapter_id,
    )


def _projection_failure_diagnostic(
    *,
    publication_id: str,
    producer_module_id: str,
    error: ProducerProjectionError,
) -> CrossProducerCompatibilityDiagnostic:
    return _diagnostic(
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        outcome="failed",
        code=error.code,
        stage=error.stage,
        scope="projection",
        reason_codes=("compatibility.projection_failed",),
        summary=(
            "The selected live Vitrine adapter could not project the validated "
            "producer public model."
        ),
        next_action=(
            "Repair the live projection integration. Do not infer student, Grade, "
            "mastery, or portfolio quality from this integration failure."
        ),
        adapter_id=error.adapter_id,
    )


def diagnose_publication_read_probe(
    workspace_root: str | Path,
    publication_id: str,
    *,
    portfolio_id: str,
    portfolio_subject_id: str,
    purpose: str,
    authorization_gate: SourceReadAuthorizationGate,
    producer_registry: PublicationProducerRegistry | None = None,
    adapter_registry: ProducerProjectionAdapterRegistry | None = None,
) -> PublicationReadProbeDiagnostics:
    """Authorize, verify, read, and purely project one explicit Publication.

    Metadata compatibility is completed first. A denied or unresolved source-read
    decision stops before manifest existence, digest, bytes, producer-reader, or
    projection inspection. The probe persists no Vitrine records.
    """

    metadata = diagnose_publication_compatibility(
        workspace_root,
        publication_id,
        producer_registry=producer_registry,
        adapter_registry=adapter_registry,
    )
    checks = list(metadata.checks)
    if not metadata.ready:
        return _probe_report(
            metadata.publication_id,
            metadata.producer_module_id,
            checks,
        )
    producer = metadata.producer_module_id
    if producer is None:
        raise CompatibilityDiagnosticError(
            "Ready Publication metadata must identify one producer module."
        )
    adapters = build_adapter_registry() if adapter_registry is None else adapter_registry
    if not isinstance(adapters, ProducerProjectionAdapterRegistry):
        raise CompatibilityDiagnosticError(
            "adapter_registry must be ProducerProjectionAdapterRegistry."
        )

    publication, canonical = _canonical_publication(
        workspace_root, metadata.publication_id
    )
    canonical = _copy_probe_stage(
        canonical,
        publication_id=metadata.publication_id,
        stage="canonical_revalidation",
    )
    checks.append(canonical)
    if publication is None:
        return _probe_report(metadata.publication_id, producer, checks)

    registration, registration_check = _registration(workspace_root, publication)
    registration_check = _copy_probe_stage(
        registration_check,
        publication_id=metadata.publication_id,
        stage="registration_revalidation",
    )
    checks.append(registration_check)
    if registration_check.outcome not in {"ready", "not_applicable"}:
        return _probe_report(metadata.publication_id, producer, checks)

    series_check = _copy_probe_stage(
        _series_state(workspace_root, publication),
        publication_id=metadata.publication_id,
        stage="series_revalidation",
    )
    checks.append(series_check)
    if series_check.outcome != "ready":
        return _probe_report(metadata.publication_id, producer, checks)

    request = _support_request(publication, registration)
    try:
        adapter = adapters.select_adapter(request)
    except ProducerAdapterError as error:
        checks.append(
            _diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                outcome="unsupported",
                code=error.code,
                stage=error.stage,
                scope="contract_support",
                reason_codes=("compatibility.no_exact_live_contract",),
                summary=(
                    "Exact Vitrine live adapter support changed before the read probe."
                ),
                next_action=(
                    "Re-run metadata diagnostics and reconcile the exact adapter "
                    "registry. No fallback adapter is selected."
                ),
                adapter_id=error.adapter_id,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)

    try:
        authorization_request = SourceReadAuthorizationRequest(
            portfolio_id=portfolio_id,
            portfolio_subject_id=portfolio_subject_id,
            publication_id=metadata.publication_id,
            operation=COMPATIBILITY_SOURCE_READ_OPERATION,
            purpose=purpose,
        )
    except ProducerReaderServiceError as error:
        raise CompatibilityDiagnosticError(
            "Compatibility read-probe authorization context is invalid."
        ) from error

    try:
        decision = authorize_source_read(authorization_gate, authorization_request)
    except ProducerReaderServiceError as error:
        checks.append(
            _authorization_failure_diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                error=error,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)
    authorization_fields: tuple[tuple[str, str], ...] = ()
    if decision.reason_codes:
        authorization_fields = (
            ("authorization_reason_codes", ",".join(decision.reason_codes)),
        )
    checks.append(
        _diagnostic(
            publication_id=metadata.publication_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.source_read_allowed",
            stage="source_authorization",
            scope="source_read",
            reason_codes=("compatibility.source_read_allowed",),
            safe_fields=authorization_fields,
            summary="The deployment authorization policy allowed this source read.",
            next_action="Verify the exact canonical manifest before producer reading.",
        )
    )

    try:
        manifest_bytes = read_verified_publication_manifest_bytes(
            workspace_root, publication
        )
    except ProducerReaderServiceError as error:
        checks.append(
            _manifest_failure_diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                error=error,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)
    checks.append(
        _diagnostic(
            publication_id=metadata.publication_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.manifest_verified",
            stage="manifest_integrity",
            scope="source_read",
            reason_codes=("compatibility.manifest_verified",),
            summary=(
                "Core verified the canonical manifest containment and digest and "
                "returned immutable bytes."
            ),
            next_action="Invoke the #57-audited producer public reader.",
        )
    )

    try:
        reader = build_audited_installed_producer_reader(producer)
        public_model = reader.read(manifest_bytes)
    except ProducerReaderError as error:
        checks.append(
            _reader_failure_diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                error=error,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)
    checks.append(
        _diagnostic(
            publication_id=metadata.publication_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.reader_invocation_succeeded",
            stage="producer_reader",
            scope="reader",
            reason_codes=("compatibility.reader_invocation_succeeded",),
            safe_fields=(
                ("public_reader_id", reader.descriptor.public_reader_id),
                ("reader_contract_version", reader.descriptor.reader_contract_version),
            ),
            summary="The audited producer public reader accepted the verified bytes.",
            next_action="Invoke the exact selected pure Vitrine live projection.",
            adapter_id=adapter.declaration.adapter_id,
        )
    )

    try:
        batch = adapter.project(public_model)
        if not isinstance(batch, ProducerProjectionBatch):
            raise ProducerProjectionError(
                "projection.failed",
                "projection",
                "Selected adapter returned an invalid projection batch.",
                adapter_id=adapter.declaration.adapter_id,
                producer_module_id=producer,
            )
    except ProducerProjectionError as error:
        checks.append(
            _projection_failure_diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                error=error,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)
    except Exception:
        projection_error = ProducerProjectionError(
            "projection.failed",
            "projection",
            "Selected adapter projection failed unexpectedly.",
            adapter_id=adapter.declaration.adapter_id,
            producer_module_id=producer,
        )
        checks.append(
            _projection_failure_diagnostic(
                publication_id=metadata.publication_id,
                producer_module_id=producer,
                error=projection_error,
            )
        )
        return _probe_report(metadata.publication_id, producer, checks)

    checks.append(
        _diagnostic(
            publication_id=metadata.publication_id,
            producer_module_id=producer,
            outcome="ready",
            code="compatibility.projection_succeeded",
            stage="projection",
            scope="projection",
            reason_codes=("compatibility.projection_succeeded",),
            safe_fields=(
                ("candidate_projection_contract_version", batch.candidate_projection_contract_version),
                ("projected_source_count", str(len(batch.projected_sources))),
            ),
            summary=(
                "The exact selected live Vitrine adapter projected the validated "
                "producer public model successfully."
            ),
            next_action=(
                "The read/projection path is healthy. Candidate evaluation and "
                "persistence remain separate."
            ),
            adapter_id=batch.adapter_id,
        )
    )
    return _probe_report(
        metadata.publication_id,
        producer,
        checks,
        projected_source_count=len(batch.projected_sources),
        ready=True,
    )


__all__ = [
    "COMPATIBILITY_SOURCE_READ_OPERATION",
    "PublicationCompatibilityDiagnostics",
    "PublicationReadProbeDiagnostics",
    "diagnose_publication_compatibility",
    "diagnose_publication_read_probe",
]
