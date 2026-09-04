"""Privacy-safe diagnostics for producer-authorized Snapshot Artifact failures.

Issue #62 Slice 5 explains existing Quillan/Concord Snapshot source failures
without changing producer Artifact authorization, source-provider behavior, or
Snapshot materialization contracts. ScoreForm remains explicitly not applicable.
"""

from __future__ import annotations

from typing import Final

from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
    CompatibilityDiagnosticError,
    CrossProducerCompatibilityDiagnostic,
)
from vitrine.models.common import require_identifier
from vitrine.models.errors import VitrineModelValidationError
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    ReleasedProducerContractAudit,
)
from vitrine.snapshot_materialization import SnapshotMaterializationError

_ARTIFACT_STAGE_PREFIX: Final[dict[str, str]] = {
    "quillan": "quillan_artifact_",
    "concord": "concord_artifact_",
}


def _optional_identifier(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return require_identifier(value, field_name)
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error


def _audit(producer_module_id: str) -> ReleasedProducerContractAudit:
    if not isinstance(producer_module_id, str):
        raise CompatibilityDiagnosticError("producer_module_id must be a string.")
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE.get(producer_module_id)
    if audit is None:
        raise CompatibilityDiagnosticError(
            "Artifact diagnostics require one #57-audited live producer identity."
        )
    return audit


def _safe_fields(
    producer_module_id: str,
    *,
    source_artifact_id: str | None,
) -> tuple[tuple[str, str], ...]:
    audit = _audit(producer_module_id)
    values: list[tuple[str, str]] = [
        ("artifact_access_mode", audit.artifact_access_mode),
        (
            "artifact_reader_module",
            audit.artifact_reader_module or "<not_applicable>",
        ),
        (
            "artifact_request_kinds",
            ",".join(audit.artifact_request_kinds) or "<not_applicable>",
        ),
    ]
    normalized_artifact_id = _optional_identifier(
        source_artifact_id,
        "source_artifact_id",
    )
    if normalized_artifact_id is not None:
        values.append(("source_artifact_id", normalized_artifact_id))
    return tuple(values)


def _diagnostic(
    *,
    producer_module_id: str,
    publication_id: str | None,
    source_artifact_id: str | None,
    outcome: str,
    code: str,
    stage: str,
    reason_code: str,
    summary: str,
    next_action: str,
    extra_safe_fields: tuple[tuple[str, str], ...] = (),
) -> CrossProducerCompatibilityDiagnostic:
    normalized_publication = _optional_identifier(publication_id, "publication_id")
    return CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=(
            CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
        ),
        scope="artifact",
        outcome=outcome,
        code=code,
        stage=stage,
        producer_module_id=producer_module_id,
        publication_id=normalized_publication,
        adapter_id=None,
        reason_codes=(reason_code,),
        safe_fields=(
            *_safe_fields(
                producer_module_id,
                source_artifact_id=source_artifact_id,
            ),
            *extra_safe_fields,
        ),
        summary=summary,
        next_action=next_action,
    )


def diagnose_artifact_applicability(
    producer_module_id: str,
    *,
    publication_id: str | None = None,
    source_artifact_id: str | None = None,
) -> CrossProducerCompatibilityDiagnostic:
    """Describe audited Artifact applicability without reading producer state."""

    audit = _audit(producer_module_id)
    if audit.artifact_access_mode == "none":
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="not_applicable",
            code="compatibility.artifact_api_not_applicable",
            stage="artifact_api",
            reason_code="compatibility.artifact_api_not_applicable",
            summary=(
                "This audited producer does not expose a consumer-neutral Artifact "
                "API for Vitrine Snapshot acquisition."
            ),
            next_action=(
                "No Artifact provider is expected for this producer. Treat projected "
                "evidence according to its supported Vitrine representations."
            ),
        )
    return _diagnostic(
        producer_module_id=producer_module_id,
        publication_id=publication_id,
        source_artifact_id=source_artifact_id,
        outcome="supported",
        code="compatibility.artifact_api_ready",
        stage="artifact_api",
        reason_code="compatibility.artifact_api_ready",
        summary=(
            "This audited producer contract supports separately authorized Artifact "
            "acquisition through its public API."
        ),
        next_action=(
            "Artifact authorization, source availability, and returned-result "
            "integrity remain separate checks for the specific source."
        ),
    )


def _require_matching_stage(
    producer_module_id: str, error: SnapshotMaterializationError
) -> None:
    if (
        error.code == "snapshot.source_provider_missing"
        and error.stage == "provider_selection"
    ):
        return
    prefix = _ARTIFACT_STAGE_PREFIX.get(producer_module_id)
    if prefix is None or not error.stage.startswith(prefix):
        raise CompatibilityDiagnosticError(
            "Snapshot Artifact failure stage does not match the requested producer."
        )


def explain_artifact_failure(
    producer_module_id: str,
    error: SnapshotMaterializationError,
    *,
    publication_id: str | None = None,
    source_artifact_id: str | None = None,
) -> CrossProducerCompatibilityDiagnostic:
    """Map one existing Snapshot/provider Artifact failure to a safe explanation.

    The originating ``SnapshotMaterializationError.code`` and ``stage`` are
    preserved verbatim. The original exception message is intentionally ignored.
    """

    audit = _audit(producer_module_id)
    if audit.artifact_access_mode == "none":
        return diagnose_artifact_applicability(
            producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
        )
    if not isinstance(error, SnapshotMaterializationError):
        raise CompatibilityDiagnosticError(
            "error must be SnapshotMaterializationError."
        )
    _require_matching_stage(producer_module_id, error)

    producer_label = "Quillan" if producer_module_id == "quillan" else "Concord"

    if error.code == "snapshot.source_provider_missing":
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="unavailable",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_provider_missing",
            summary=(
                "Vitrine has no exact Snapshot source provider registered for this "
                f"planned {producer_label} Artifact contract."
            ),
            next_action=(
                "Reconcile the Vitrine source-provider registration. Do not bypass "
                "the producer Artifact API or reconstruct producer-native paths."
            ),
        )

    if error.stage.endswith("_artifact_contract"):
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="unavailable",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_api_unavailable",
            summary=(
                f"The installed {producer_label} public Artifact API is unavailable "
                "or incompatible with the audited integration surface."
            ),
            next_action=(
                f"Repair the installed {producer_label} public Artifact API. Do not "
                "use package-version equality as the semantic compatibility rule."
            ),
        )

    if error.stage.endswith("_artifact_authorization_denied"):
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="denied",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_authorization_denied",
            summary=(
                "The deployment Artifact authorization policy denied this "
                f"{producer_label} "
                "source acquisition."
            ),
            next_action=(
                "Review the deployment/application authorization policy. Do not bypass "
                "the producer authorization gate."
            ),
            extra_safe_fields=(("artifact_bytes_acquired", "no"),),
        )

    if error.stage.endswith("_artifact_authorization_unresolved"):
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="unresolved",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_authorization_unresolved",
            summary=(
                f"{producer_label} Artifact authorization could not be established "
                "for this source acquisition."
            ),
            next_action=(
                "Resolve the deployment/application authorization decision. Do not "
                "treat an exception or invalid decision as allowed."
            ),
            extra_safe_fields=(("artifact_bytes_acquired", "no"),),
        )

    if error.code == "snapshot.source_unavailable":
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="unavailable",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_source_unavailable",
            summary=(
                f"The {producer_label} public Artifact path could not resolve the "
                "requested historical source."
            ),
            next_action=(
                "Reconcile or republish through the owning producer/Core workflow. "
                "Do not inspect producer-native storage or infer a replacement path."
            ),
        )

    if error.code in {
        "snapshot.source_integrity_failed",
        "snapshot.source_digest_mismatch",
        "snapshot.source_changed_during_acquisition",
    }:
        return _diagnostic(
            producer_module_id=producer_module_id,
            publication_id=publication_id,
            source_artifact_id=source_artifact_id,
            outcome="integrity_failed",
            code=error.code,
            stage=error.stage,
            reason_code="compatibility.artifact_integrity_failed",
            summary=(
                f"The {producer_label} Artifact source or returned result failed an "
                "integrity/provenance check."
            ),
            next_action=(
                "Reconcile the producer/Core historical source and retry through the "
                "public Artifact API. Do not repair bytes or provenance inside Vitrine."
            ),
        )

    return _diagnostic(
        producer_module_id=producer_module_id,
        publication_id=publication_id,
        source_artifact_id=source_artifact_id,
        outcome="failed",
        code=error.code,
        stage=error.stage,
        reason_code="compatibility.artifact_failure",
        summary=(
            f"The {producer_label} Artifact acquisition failed at a recognized "
            "producer/Vitrine boundary."
        ),
        next_action=(
            "Use the preserved technical code and stage to inspect the owning "
            "boundary. "
            "Do not expose raw producer exceptions or bypass authorization."
        ),
    )


__all__ = [
    "diagnose_artifact_applicability",
    "explain_artifact_failure",
]
