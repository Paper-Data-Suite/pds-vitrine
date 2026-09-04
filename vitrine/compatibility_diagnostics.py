"""Pure cross-producer compatibility diagnostics for Vitrine.

Issue #62 provides a transient, privacy-safe explanation layer over existing
Core/Vitrine compatibility authority. Contract-only explanation remains pure and
producer-package lazy. The explicit installed-readiness operation may discover
Core producer Profiles and import audited public producer modules, but it performs
no workspace I/O, authorization, manifest reading, or persistence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module, metadata
from typing import Final

from pds_core.publication_compatibility import (
    PublicationProducerRegistry,
    build_publication_producer_registry,
)

from vitrine.models.common import (
    require_controlled_key,
    require_identifier,
    require_lower_identifier,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.producer_adapters import (
    ProducerAdapterConflictError,
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    ProducerAdapterUnsupportedError,
    ProducerProjectionAdapter,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)
from vitrine.producer_reader_services import build_audited_installed_producer_reader
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACTS,
    ReleasedProducerContractAudit,
)

CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION: Final[str] = (
    "vitrine_cross_producer_compatibility_diagnostic_v1"
)

COMPATIBILITY_DIAGNOSTIC_SCOPES: Final[frozenset[str]] = frozenset(
    {
        "producer_readiness",
        "contract_support",
        "publication_compatibility",
        "source_read",
        "reader",
        "projection",
        "artifact",
        "fixture_boundary",
    }
)
COMPATIBILITY_DIAGNOSTIC_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "ready",
        "supported",
        "not_applicable",
        "unsupported",
        "not_selectable",
        "unavailable",
        "denied",
        "unresolved",
        "integrity_failed",
        "failed",
        "not_checked",
    }
)

COMPATIBILITY_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "compatibility.contract_supported",
        "compatibility.producer_not_registered",
        "compatibility.multiple_live_contracts_match",
        "compatibility.no_exact_live_contract",
        "compatibility.core_publication_schema_mismatch",
        "compatibility.publication_kind_mismatch",
        "compatibility.manifest_contract_mismatch",
        "compatibility.producer_contract_mismatch",
        "compatibility.source_record_presence_mismatch",
        "compatibility.source_record_kind_mismatch",
        "compatibility.source_record_contract_mismatch",
        "compatibility.required_capability_missing",
        "compatibility.fixture_identity",
        "compatibility.producer_ready",
        "compatibility.producer_not_ready",
        "compatibility.live_adapter_registered",
        "compatibility.live_adapter_missing",
        "compatibility.live_adapter_conflict",
        "compatibility.core_profile_discovered",
        "compatibility.core_profile_missing",
        "compatibility.core_profile_discovery_failed",
        "compatibility.reader_distribution_available",
        "compatibility.reader_distribution_unavailable",
        "compatibility.reader_api_ready",
        "compatibility.reader_api_incompatible",
        "compatibility.reader_api_not_checked",
        "compatibility.artifact_api_not_applicable",
        "compatibility.artifact_api_ready",
        "compatibility.artifact_api_unavailable",
        "compatibility.artifact_api_not_checked",
        "compatibility.artifact_authorization_denied",
        "compatibility.artifact_authorization_unresolved",
        "compatibility.artifact_source_unavailable",
        "compatibility.artifact_integrity_failed",
        "compatibility.artifact_provider_missing",
        "compatibility.artifact_failure",
        "compatibility.canonical_publication_loaded",
        "compatibility.canonical_publication_missing",
        "compatibility.canonical_publication_invalid",
        "compatibility.registration_loaded",
        "compatibility.registration_not_applicable",
        "compatibility.registration_missing",
        "compatibility.registration_mismatch",
        "compatibility.publication_current_selectable",
        "compatibility.publication_historical",
        "compatibility.publication_withdrawn",
        "compatibility.publication_series_conflict",
        "compatibility.core_contract_supported",
        "compatibility.core_contract_incompatible",
        "compatibility.publication_ready",
        "compatibility.publication_not_ready",
        "compatibility.fixture_publication_identity",
        "compatibility.reader_binding_not_audited",
        "compatibility.source_read_allowed",
        "compatibility.source_read_denied",
        "compatibility.source_read_unresolved",
        "compatibility.manifest_verified",
        "compatibility.manifest_missing",
        "compatibility.manifest_integrity_failed",
        "compatibility.reader_invocation_succeeded",
        "compatibility.reader_invocation_failed",
        "compatibility.projection_succeeded",
        "compatibility.projection_failed",
        "compatibility.read_probe_ready",
        "compatibility.read_probe_not_ready",
    }
)

DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "vitrine_concord_fixture",
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
    }
)
_FIXTURE_ADAPTER_ID_BY_PRODUCER: Final[dict[str, str]] = {
    "vitrine_concord_fixture": "vitrine_concord_fixture_adapter",
    "vitrine_quillan_fixture": "vitrine_quillan_fixture_adapter",
    "vitrine_scoreform_fixture": "vitrine_scoreform_fixture_adapter",
}

_DOTTED_CODE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_CORE_COMPATIBILITY_CODE = re.compile(r"^contracts\.[a-z][a-z0-9_]*$")
_ABSENT = "<absent>"


class CompatibilityDiagnosticError(ValueError):
    """Invalid request or transient compatibility diagnostic value."""


def _diagnostic_code(value: object, field_name: str) -> str:
    try:
        text = require_text(value, field_name, maximum=128)
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error
    if _DOTTED_CODE.fullmatch(text) is None:
        raise CompatibilityDiagnosticError(
            f"{field_name} must be a lowercase dotted diagnostic identifier."
        )
    return text


def _optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return require_identifier(value, field_name)
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error


def _optional_lower_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return require_lower_identifier(value, field_name)
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error


def _normalized_codes(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise CompatibilityDiagnosticError(f"{field_name} must be an iterable.")
    try:
        result = tuple(_diagnostic_code(value, field_name) for value in values)
    except TypeError as error:
        raise CompatibilityDiagnosticError(
            f"{field_name} must be an iterable."
        ) from error
    return tuple(sorted(set(result)))


def _safe_fields(
    values: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    if isinstance(values, (str, bytes)):
        raise CompatibilityDiagnosticError("safe_fields must be an iterable.")
    normalized: list[tuple[str, str]] = []
    try:
        rows = tuple(values)
    except TypeError as error:
        raise CompatibilityDiagnosticError("safe_fields must be an iterable.") from error
    for row in rows:
        if not isinstance(row, tuple) or len(row) != 2:
            raise CompatibilityDiagnosticError(
                "safe_fields must contain key/value string pairs."
            )
        key, value = row
        try:
            safe_key = require_controlled_key(key, "safe_fields key")
            safe_value = require_text(value, "safe_fields value", maximum=500)
        except VitrineModelValidationError as error:
            raise CompatibilityDiagnosticError(str(error)) from error
        normalized.append((safe_key, safe_value))
    if len({key for key, _ in normalized}) != len(normalized):
        raise CompatibilityDiagnosticError("safe_fields keys must be unique.")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True, kw_only=True)
class CrossProducerCompatibilityDiagnostic:
    """One transient, privacy-safe compatibility explanation."""

    diagnostic_contract_version: str
    scope: str
    outcome: str
    code: str
    stage: str
    producer_module_id: str | None
    publication_id: str | None
    adapter_id: str | None
    reason_codes: tuple[str, ...]
    safe_fields: tuple[tuple[str, str], ...]
    summary: str
    next_action: str

    def __post_init__(self) -> None:
        if (
            self.diagnostic_contract_version
            != CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
        ):
            raise CompatibilityDiagnosticError(
                "diagnostic_contract_version is not the supported diagnostic contract."
            )
        if self.scope not in COMPATIBILITY_DIAGNOSTIC_SCOPES:
            raise CompatibilityDiagnosticError("scope is not supported.")
        if self.outcome not in COMPATIBILITY_DIAGNOSTIC_OUTCOMES:
            raise CompatibilityDiagnosticError("outcome is not supported.")
        object.__setattr__(self, "code", _diagnostic_code(self.code, "code"))
        try:
            object.__setattr__(
                self,
                "stage",
                require_controlled_key(self.stage, "stage"),
            )
            object.__setattr__(
                self,
                "summary",
                require_text(self.summary, "summary", maximum=1000),
            )
            object.__setattr__(
                self,
                "next_action",
                require_text(self.next_action, "next_action", maximum=1000),
            )
        except VitrineModelValidationError as error:
            raise CompatibilityDiagnosticError(str(error)) from error
        object.__setattr__(
            self,
            "producer_module_id",
            _optional_lower_identifier(
                self.producer_module_id,
                "producer_module_id",
            ),
        )
        object.__setattr__(
            self,
            "publication_id",
            _optional_identifier(self.publication_id, "publication_id"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _optional_identifier(self.adapter_id, "adapter_id"),
        )
        reason_codes = _normalized_codes(self.reason_codes, "reason_codes")
        unknown = {
            code
            for code in reason_codes
            if code not in COMPATIBILITY_REASON_CODES
            and _CORE_COMPATIBILITY_CODE.fullmatch(code) is None
        }
        if unknown:
            raise CompatibilityDiagnosticError(
                "reason_codes contains an unsupported compatibility reason."
            )
        object.__setattr__(self, "reason_codes", reason_codes)
        object.__setattr__(self, "safe_fields", _safe_fields(self.safe_fields))



def _result(
    *,
    scope: str,
    outcome: str,
    code: str,
    stage: str,
    producer_module_id: str | None,
    publication_id: str | None = None,
    adapter_id: str | None = None,
    reason_codes: tuple[str, ...],
    safe_fields: tuple[tuple[str, str], ...],
    summary: str,
    next_action: str,
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


def _display(value: str | None) -> str:
    return value if value is not None else _ABSENT


def _capabilities(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else _ABSENT


def _supported_fields(
    request: ProducerAdapterSupportRequest,
    key: ProducerAdapterSupportKey,
) -> tuple[tuple[str, str], ...]:
    return (
        ("available_capabilities", _capabilities(request.capabilities)),
        ("core_publication_schema_version", request.core_publication_schema_version),
        ("manifest_contract_version", request.manifest_contract_version),
        ("producer_contract_version", _display(request.producer_contract_version)),
        ("publication_kind", request.publication_kind),
        ("required_capabilities", _capabilities(key.required_capabilities)),
        ("source_record_contract_version", _display(request.source_record_contract_version)),
        ("source_record_kind", _display(request.source_record_kind)),
    )


def _mismatch(
    reason: str,
    name: str,
    actual: str | None,
    expected: str | None,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    return (
        reason,
        (
            (f"actual_{name}", _display(actual)),
            (f"expected_{name}", _display(expected)),
        ),
    )


def _mismatches(
    request: ProducerAdapterSupportRequest,
    key: ProducerAdapterSupportKey,
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    rows: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    scalar_specs = (
        (
            "compatibility.core_publication_schema_mismatch",
            "core_publication_schema_version",
            request.core_publication_schema_version,
            key.core_publication_schema_version,
        ),
        (
            "compatibility.publication_kind_mismatch",
            "publication_kind",
            request.publication_kind,
            key.publication_kind,
        ),
        (
            "compatibility.manifest_contract_mismatch",
            "manifest_contract_version",
            request.manifest_contract_version,
            key.manifest_contract_version,
        ),
        (
            "compatibility.producer_contract_mismatch",
            "producer_contract_version",
            request.producer_contract_version,
            key.producer_contract_version,
        ),
    )
    for reason, name, actual, expected in scalar_specs:
        if actual != expected:
            rows.append(_mismatch(reason, name, actual, expected))

    actual_present = request.source_record_kind is not None
    expected_present = key.source_record_kind is not None
    if actual_present != expected_present:
        rows.append(
            (
                "compatibility.source_record_presence_mismatch",
                (
                    ("actual_source_record_kind", _display(request.source_record_kind)),
                    (
                        "actual_source_record_contract_version",
                        _display(request.source_record_contract_version),
                    ),
                    ("expected_source_record_kind", _display(key.source_record_kind)),
                    (
                        "expected_source_record_contract_version",
                        _display(key.source_record_contract_version),
                    ),
                ),
            )
        )
    elif actual_present:
        if request.source_record_kind != key.source_record_kind:
            rows.append(
                _mismatch(
                    "compatibility.source_record_kind_mismatch",
                    "source_record_kind",
                    request.source_record_kind,
                    key.source_record_kind,
                )
            )
        if (
            request.source_record_contract_version
            != key.source_record_contract_version
        ):
            rows.append(
                _mismatch(
                    "compatibility.source_record_contract_mismatch",
                    "source_record_contract_version",
                    request.source_record_contract_version,
                    key.source_record_contract_version,
                )
            )

    missing = tuple(
        sorted(set(key.required_capabilities) - set(request.capabilities))
    )
    if missing:
        rows.append(
            (
                "compatibility.required_capability_missing",
                (
                    ("missing_required_capabilities", ",".join(missing)),
                    (
                        "available_capabilities",
                        _capabilities(request.capabilities),
                    ),
                    (
                        "expected_required_capabilities",
                        _capabilities(key.required_capabilities),
                    ),
                ),
            )
        )
    return tuple(rows)


def _unsupported_summary(
    request: ProducerAdapterSupportRequest,
    reasons: tuple[str, ...],
) -> tuple[str, str]:
    if (
        request.producer_module_id == "quillan"
        and "compatibility.source_record_presence_mismatch" in reasons
        and request.source_record_kind == "assignment"
        and request.source_record_contract_version == "2"
    ):
        return (
            "The live Quillan Publication contract requires source_record to be "
            "absent. Quillan assignment contract 2 belongs to the Academic Work "
            "Registration and does not expand the live Publication support key.",
            "Reconcile or republish the producer/Core Publication; do not broaden "
            "QUILLAN_LIVE_SUPPORT_KEY with assignment contract 2.",
        )
    if (
        request.producer_module_id == "concord"
        and "compatibility.source_record_presence_mismatch" in reasons
    ):
        return (
            "The live Concord contract requires its exact versioned Activity "
            "Publication source record.",
            "Reconcile or republish the Concord/Core Publication with the exact "
            "supported Activity source contract.",
        )
    return (
        "The producer identity is known, but this exact semantic Publication "
        "contract does not match the registered Vitrine live support key.",
        "Use a Publication matching an explicitly supported semantic contract, "
        "or add a future explicit compatibility implementation. Do not select a "
        "nearest adapter or fall back to a development fixture.",
    )


def _same_producer_live_adapters(
    registry: ProducerProjectionAdapterRegistry,
    producer_module_id: str,
) -> tuple[ProducerProjectionAdapter, ...]:
    return tuple(
        adapter
        for adapter in registry.adapters
        if adapter.declaration.integration_kind == "live"
        and adapter.declaration.support_key.producer_module_id == producer_module_id
    )


def explain_live_adapter_support(
    request: ProducerAdapterSupportRequest,
    *,
    registry: ProducerProjectionAdapterRegistry | None = None,
) -> CrossProducerCompatibilityDiagnostic:
    """Explain one exact live support request without weakening adapter selection.

    Exact selection remains owned by ``ProducerProjectionAdapterRegistry``.  This
    function only classifies a successful selection or explains why the registry
    rejected the exact request.  It performs no producer-package or workspace I/O.
    """

    if not isinstance(request, ProducerAdapterSupportRequest):
        raise CompatibilityDiagnosticError(
            "request must be ProducerAdapterSupportRequest."
        )
    effective_registry = build_adapter_registry() if registry is None else registry
    if not isinstance(effective_registry, ProducerProjectionAdapterRegistry):
        raise CompatibilityDiagnosticError(
            "registry must be ProducerProjectionAdapterRegistry."
        )

    producer_module_id = request.producer_module_id
    if producer_module_id in DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS:
        return _result(
            scope="fixture_boundary",
            outcome="unsupported",
            code="adapter.fixture_not_enabled",
            stage="fixture_boundary",
            producer_module_id=producer_module_id,
            adapter_id=_FIXTURE_ADAPTER_ID_BY_PRODUCER[producer_module_id],
            reason_codes=("compatibility.fixture_identity",),
            safe_fields=(("integration_kind", "development_fixture"),),
            summary=(
                "This producer identity belongs to a Vitrine development fixture, "
                "not to an installed live producer integration."
            ),
            next_action=(
                "Use the explicit development-fixture registry only for fixture "
                "workflows. Do not remap this identity to a live producer."
            ),
        )

    try:
        selected = effective_registry.select_adapter(request)
    except ProducerAdapterConflictError as error:
        candidates = _same_producer_live_adapters(
            effective_registry, producer_module_id
        )
        adapter_ids = tuple(
            adapter.declaration.adapter_id for adapter in candidates
        )
        return _result(
            scope="contract_support",
            outcome="failed",
            code=error.code,
            stage=error.stage,
            producer_module_id=producer_module_id,
            reason_codes=("compatibility.multiple_live_contracts_match",),
            safe_fields=(("matching_adapter_ids", ",".join(adapter_ids)),),
            summary=(
                "Multiple live Vitrine adapters match this exact semantic contract."
            ),
            next_action=(
                "Reconcile the live adapter registry. Do not select by insertion "
                "order or package version."
            ),
        )
    except ProducerAdapterUnsupportedError as error:
        candidates = _same_producer_live_adapters(
            effective_registry, producer_module_id
        )
        if not candidates:
            live_producers = tuple(
                sorted(
                    {
                        adapter.declaration.support_key.producer_module_id
                        for adapter in effective_registry.adapters
                        if adapter.declaration.integration_kind == "live"
                    }
                )
            )
            return _result(
                scope="contract_support",
                outcome="unsupported",
                code=error.code,
                stage=error.stage,
                producer_module_id=producer_module_id,
                reason_codes=("compatibility.producer_not_registered",),
                safe_fields=(
                    ("registered_live_producers", _capabilities(live_producers)),
                ),
                summary=(
                    "No live Vitrine adapter is registered for this producer "
                    "identity."
                ),
                next_action=(
                    "Add a future explicit live integration if this producer is "
                    "supported. Do not substitute a development fixture."
                ),
            )
        if len(candidates) != 1:
            adapter_ids = tuple(
                adapter.declaration.adapter_id for adapter in candidates
            )
            return _result(
                scope="contract_support",
                outcome="unsupported",
                code=error.code,
                stage=error.stage,
                producer_module_id=producer_module_id,
                reason_codes=("compatibility.no_exact_live_contract",),
                safe_fields=(("registered_adapter_ids", ",".join(adapter_ids)),),
                summary=(
                    "The producer is known, but no registered live declaration "
                    "matches this exact semantic contract."
                ),
                next_action=(
                    "Review the explicitly supported contracts. Do not choose the "
                    "nearest declaration or use insertion order as fallback."
                ),
            )

        candidate = candidates[0]
        mismatches = _mismatches(request, candidate.declaration.support_key)
        reason_codes = tuple(reason for reason, _ in mismatches)
        fields: list[tuple[str, str]] = []
        for _, mismatch_fields in mismatches:
            for field in mismatch_fields:
                if field[0] not in {key for key, _ in fields}:
                    fields.append(field)
        if not reason_codes:
            reason_codes = ("compatibility.no_exact_live_contract",)
        summary, next_action = _unsupported_summary(request, reason_codes)
        return _result(
            scope="contract_support",
            outcome="unsupported",
            code=error.code,
            stage=error.stage,
            producer_module_id=producer_module_id,
            adapter_id=candidate.declaration.adapter_id,
            reason_codes=reason_codes,
            safe_fields=tuple(fields),
            summary=summary,
            next_action=next_action,
        )

    declaration = selected.declaration
    return _result(
        scope="contract_support",
        outcome="supported",
        code="compatibility.contract_supported",
        stage="selection",
        producer_module_id=producer_module_id,
        adapter_id=declaration.adapter_id,
        reason_codes=("compatibility.contract_supported",),
        safe_fields=_supported_fields(request, declaration.support_key),
        summary=(
            "This exact semantic Publication contract is supported by the selected "
            "Vitrine live adapter."
        ),
        next_action=(
            "No compatibility action is required. Authorization and source reading "
            "remain separate later checks."
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerIntegrationReadiness:
    """One audited producer's transient readiness report."""

    producer_module_id: str
    overall: CrossProducerCompatibilityDiagnostic
    checks: tuple[CrossProducerCompatibilityDiagnostic, ...]

    def __post_init__(self) -> None:
        try:
            producer_module_id = require_lower_identifier(
                self.producer_module_id,
                "producer_module_id",
            )
        except VitrineModelValidationError as error:
            raise CompatibilityDiagnosticError(str(error)) from error
        checks = tuple(self.checks)
        if not checks:
            raise CompatibilityDiagnosticError("checks must not be empty.")
        if not isinstance(self.overall, CrossProducerCompatibilityDiagnostic):
            raise CompatibilityDiagnosticError(
                "overall must be CrossProducerCompatibilityDiagnostic."
            )
        if any(
            not isinstance(item, CrossProducerCompatibilityDiagnostic)
            for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "checks must contain CrossProducerCompatibilityDiagnostic values."
            )
        if self.overall.producer_module_id != producer_module_id or any(
            item.producer_module_id != producer_module_id for item in checks
        ):
            raise CompatibilityDiagnosticError(
                "readiness diagnostics must belong to the same producer."
            )
        stages = tuple(item.stage for item in checks)
        if len(set(stages)) != len(stages):
            raise CompatibilityDiagnosticError(
                "readiness checks must have unique stages."
            )
        object.__setattr__(self, "producer_module_id", producer_module_id)
        object.__setattr__(self, "checks", checks)

    @property
    def ready(self) -> bool:
        return self.overall.outcome == "ready"


def _readiness_result(
    *,
    producer_module_id: str,
    outcome: str,
    code: str,
    stage: str,
    reason_code: str,
    safe_fields: tuple[tuple[str, str], ...],
    summary: str,
    next_action: str,
) -> CrossProducerCompatibilityDiagnostic:
    return _result(
        scope="producer_readiness",
        outcome=outcome,
        code=code,
        stage=stage,
        producer_module_id=producer_module_id,
        reason_codes=(reason_code,),
        safe_fields=safe_fields,
        summary=summary,
        next_action=next_action,
    )


def _live_adapter_readiness(
    audit: ReleasedProducerContractAudit,
    registry: ProducerProjectionAdapterRegistry,
) -> CrossProducerCompatibilityDiagnostic:
    matches = tuple(
        adapter
        for adapter in registry.adapters
        if adapter.declaration.integration_kind == "live"
        and adapter.declaration.support_key.producer_module_id
        == audit.producer_module_id
    )
    if len(matches) == 1:
        declaration = matches[0].declaration
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="ready",
            code="compatibility.live_adapter_registered",
            stage="adapter_registry",
            reason_code="compatibility.live_adapter_registered",
            safe_fields=(("adapter_id", declaration.adapter_id),),
            summary="The audited producer has exactly one registered live Vitrine adapter.",
            next_action="No adapter-registry action is required.",
        )
    if not matches:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="unavailable",
            code="compatibility.live_adapter_missing",
            stage="adapter_registry",
            reason_code="compatibility.live_adapter_missing",
            safe_fields=(),
            summary="The audited producer has no registered live Vitrine adapter.",
            next_action=(
                "Reconcile the Vitrine live adapter registry. Do not substitute a "
                "development fixture."
            ),
        )
    return _readiness_result(
        producer_module_id=audit.producer_module_id,
        outcome="failed",
        code="adapter.conflict",
        stage="adapter_registry",
        reason_code="compatibility.live_adapter_conflict",
        safe_fields=(("matching_adapter_ids", ",".join(
            item.declaration.adapter_id for item in matches
        )),),
        summary="More than one live Vitrine adapter is registered for this producer.",
        next_action=(
            "Reconcile the live adapter registry. Do not select by insertion order "
            "or distribution version."
        ),
    )


def _profile_readiness(
    audit: ReleasedProducerContractAudit,
    producer_registry: PublicationProducerRegistry | None,
    *,
    discovery_failed: bool,
) -> CrossProducerCompatibilityDiagnostic:
    if discovery_failed:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="failed",
            code="compatibility.core_profile_discovery_failed",
            stage="core_profile",
            reason_code="compatibility.core_profile_discovery_failed",
            safe_fields=(),
            summary="Core producer Profile discovery could not be completed safely.",
            next_action=(
                "Repair the installed producer Profile discovery surface. Raw "
                "entry-point errors are intentionally not exposed."
            ),
        )
    assert producer_registry is not None
    profile = producer_registry.get(audit.producer_module_id)
    if profile is None:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="unavailable",
            code="compatibility.core_profile_missing",
            stage="core_profile",
            reason_code="compatibility.core_profile_missing",
            safe_fields=(),
            summary="Core did not discover this audited producer's Publication Profile.",
            next_action=(
                "Install or repair the producer integration that exposes its Core "
                "Publication Profile."
            ),
        )
    return _readiness_result(
        producer_module_id=audit.producer_module_id,
        outcome="ready",
        code="compatibility.core_profile_discovered",
        stage="core_profile",
        reason_code="compatibility.core_profile_discovered",
        safe_fields=(("producer_display_name", profile.display_name),),
        summary="Core discovered the producer's validated Publication Profile.",
        next_action="No producer-Profile discovery action is required.",
    )


def _distribution_readiness(
    audit: ReleasedProducerContractAudit,
) -> tuple[CrossProducerCompatibilityDiagnostic, str | None]:
    try:
        installed_version = metadata.version(audit.distribution_name)
    except metadata.PackageNotFoundError:
        installed_version = None
    except Exception:
        installed_version = None
    if installed_version is None:
        return (
            _readiness_result(
                producer_module_id=audit.producer_module_id,
                outcome="unavailable",
                code="reader.unavailable",
                stage="reader_distribution",
                reason_code="compatibility.reader_distribution_unavailable",
                safe_fields=(("distribution_name", audit.distribution_name),),
                summary="The audited producer reader distribution is not available.",
                next_action=(
                    "Install or repair the producer integration. Distribution version "
                    "is informational and is not Vitrine's semantic compatibility key."
                ),
            ),
            None,
        )
    return (
        _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="ready",
            code="compatibility.reader_distribution_available",
            stage="reader_distribution",
            reason_code="compatibility.reader_distribution_available",
            safe_fields=(
                ("distribution_name", audit.distribution_name),
                ("installed_distribution_version", installed_version),
            ),
            summary="The audited producer reader distribution is installed.",
            next_action=(
                "No distribution-readiness action is required. The installed version "
                "is informational, not a semantic adapter-selection key."
            ),
        ),
        installed_version,
    )


def _reader_api_readiness(
    audit: ReleasedProducerContractAudit,
    installed_version: str | None,
) -> CrossProducerCompatibilityDiagnostic:
    reader = build_audited_installed_producer_reader(audit.producer_module_id)
    descriptor = reader.descriptor
    base_fields = (
        ("distribution_name", audit.distribution_name),
        ("public_reader_id", descriptor.public_reader_id),
        ("reader_contract_version", descriptor.reader_contract_version),
    )
    if installed_version is None:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="not_checked",
            code="reader.unavailable",
            stage="reader_api",
            reason_code="compatibility.reader_api_not_checked",
            safe_fields=base_fields,
            summary="The public reader API was not inspected because its distribution is unavailable.",
            next_action="Restore the producer distribution before checking its public reader API.",
        )
    try:
        module = import_module(audit.public_reader_module)
        symbol = getattr(module, audit.public_reader_symbol)
    except Exception:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="unavailable",
            code="reader.incompatible",
            stage="reader_api",
            reason_code="compatibility.reader_api_incompatible",
            safe_fields=base_fields,
            summary="The installed producer public reader module or symbol is incompatible.",
            next_action=(
                "Repair or update the producer package so the audited public reader "
                "API is available. Do not expose the underlying import exception."
            ),
        )
    if not callable(symbol):
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="unavailable",
            code="reader.incompatible",
            stage="reader_api",
            reason_code="compatibility.reader_api_incompatible",
            safe_fields=base_fields,
            summary="The installed producer public reader symbol is not callable.",
            next_action=(
                "Repair or update the producer package so the audited public reader "
                "API is callable."
            ),
        )
    return _readiness_result(
        producer_module_id=audit.producer_module_id,
        outcome="ready",
        code="compatibility.reader_api_ready",
        stage="reader_api",
        reason_code="compatibility.reader_api_ready",
        safe_fields=base_fields,
        summary="The audited producer public reader module and callable symbol are available.",
        next_action="No public-reader API readiness action is required.",
    )


def _artifact_api_readiness(
    audit: ReleasedProducerContractAudit,
    installed_version: str | None,
) -> CrossProducerCompatibilityDiagnostic:
    if audit.artifact_access_mode == "none":
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="not_applicable",
            code="compatibility.artifact_api_not_applicable",
            stage="artifact_api",
            reason_code="compatibility.artifact_api_not_applicable",
            safe_fields=(("artifact_access_mode", "none"),),
            summary="This audited producer has no consumer-neutral Artifact API requirement.",
            next_action="No Artifact API action is applicable for this producer.",
        )
    module_name = audit.artifact_reader_module
    assert module_name is not None
    base_fields = (
        ("artifact_access_mode", audit.artifact_access_mode),
        ("artifact_reader_module", module_name),
    )
    if installed_version is None:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="not_checked",
            code="compatibility.artifact_api_unavailable",
            stage="artifact_api",
            reason_code="compatibility.artifact_api_not_checked",
            safe_fields=base_fields,
            summary="The producer Artifact API was not inspected because its distribution is unavailable.",
            next_action="Restore the producer distribution before checking its Artifact API.",
        )
    try:
        import_module(module_name)
    except Exception:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="unavailable",
            code="compatibility.artifact_api_unavailable",
            stage="artifact_api",
            reason_code="compatibility.artifact_api_unavailable",
            safe_fields=base_fields,
            summary="The audited producer Artifact API module is unavailable.",
            next_action=(
                "Repair the producer public Artifact API. Detailed authorization and "
                "Artifact-result diagnostics remain separate later checks."
            ),
        )
    return _readiness_result(
        producer_module_id=audit.producer_module_id,
        outcome="ready",
        code="compatibility.artifact_api_ready",
        stage="artifact_api",
        reason_code="compatibility.artifact_api_ready",
        safe_fields=base_fields,
        summary="The audited producer Artifact API module is available.",
        next_action=(
            "No Artifact module-readiness action is required. Authorization, source "
            "availability, and result integrity remain separate later checks."
        ),
    )


def _overall_readiness(
    audit: ReleasedProducerContractAudit,
    checks: tuple[CrossProducerCompatibilityDiagnostic, ...],
) -> CrossProducerCompatibilityDiagnostic:
    by_stage = {item.stage: item for item in checks}
    required_ready = (
        by_stage["adapter_registry"].outcome == "ready"
        and by_stage["core_profile"].outcome == "ready"
        and by_stage["reader_distribution"].outcome == "ready"
        and by_stage["reader_api"].outcome == "ready"
        and by_stage["artifact_api"].outcome in {"ready", "not_applicable"}
    )
    if required_ready:
        return _readiness_result(
            producer_module_id=audit.producer_module_id,
            outcome="ready",
            code="compatibility.producer_ready",
            stage="producer_readiness",
            reason_code="compatibility.producer_ready",
            safe_fields=(("artifact_access_mode", audit.artifact_access_mode),),
            summary="The audited producer integration is ready for supported Vitrine consumption.",
            next_action=(
                "No installed-integration readiness action is required. Source "
                "authorization and specific Publication compatibility remain separate."
            ),
        )
    return _readiness_result(
        producer_module_id=audit.producer_module_id,
        outcome="unavailable",
        code="compatibility.producer_not_ready",
        stage="producer_readiness",
        reason_code="compatibility.producer_not_ready",
        safe_fields=(("blocked_stages", ",".join(
            item.stage
            for item in checks
            if item.outcome not in {"ready", "not_applicable"}
        )),),
        summary="The audited producer integration is not fully ready for live consumption.",
        next_action=(
            "Review the blocked readiness checks. Do not auto-install packages, "
            "broaden semantic support, or enable development fixtures."
        ),
    )


def diagnose_installed_producer_readiness(
    *,
    adapter_registry: ProducerProjectionAdapterRegistry | None = None,
    producer_registry: PublicationProducerRegistry | None = None,
) -> tuple[ProducerIntegrationReadiness, ...]:
    """Inspect the three audited live integration surfaces without workspace I/O.

    This is an explicit readiness operation, so it may discover installed Core
    producer Profiles and import audited producer public modules. Ordinary Vitrine
    imports, adapter construction, and contract-only diagnostics remain lazy.
    """

    effective_adapter_registry = (
        build_adapter_registry() if adapter_registry is None else adapter_registry
    )
    if not isinstance(
        effective_adapter_registry,
        ProducerProjectionAdapterRegistry,
    ):
        raise CompatibilityDiagnosticError(
            "adapter_registry must be ProducerProjectionAdapterRegistry."
        )

    discovery_failed = False
    effective_producer_registry = producer_registry
    if effective_producer_registry is None:
        try:
            effective_producer_registry = build_publication_producer_registry(
                explicit_profiles=(),
                discover_installed=True,
            )
        except Exception:
            discovery_failed = True
            effective_producer_registry = None
    elif not isinstance(effective_producer_registry, PublicationProducerRegistry):
        raise CompatibilityDiagnosticError(
            "producer_registry must be PublicationProducerRegistry."
        )

    reports: list[ProducerIntegrationReadiness] = []
    for audit in RELEASED_PRODUCER_CONTRACTS:
        adapter_check = _live_adapter_readiness(audit, effective_adapter_registry)
        profile_check = _profile_readiness(
            audit,
            effective_producer_registry,
            discovery_failed=discovery_failed,
        )
        distribution_check, installed_version = _distribution_readiness(audit)
        reader_check = _reader_api_readiness(audit, installed_version)
        artifact_check = _artifact_api_readiness(audit, installed_version)
        checks = (
            adapter_check,
            profile_check,
            distribution_check,
            reader_check,
            artifact_check,
        )
        reports.append(
            ProducerIntegrationReadiness(
                producer_module_id=audit.producer_module_id,
                overall=_overall_readiness(audit, checks),
                checks=checks,
            )
        )
    return tuple(reports)


def diagnose_audited_reader_readiness(
    producer_module_id: str,
) -> tuple[
    CrossProducerCompatibilityDiagnostic,
    CrossProducerCompatibilityDiagnostic,
]:
    """Inspect one #57-audited installed reader without workspace or manifest I/O."""

    try:
        producer = require_lower_identifier(producer_module_id, "producer_module_id")
    except VitrineModelValidationError as error:
        raise CompatibilityDiagnosticError(str(error)) from error
    audit = next(
        (
            item
            for item in RELEASED_PRODUCER_CONTRACTS
            if item.producer_module_id == producer
        ),
        None,
    )
    if audit is None:
        raise CompatibilityDiagnosticError(
            "producer_module_id has no #57-audited installed reader binding."
        )
    distribution, installed_version = _distribution_readiness(audit)
    reader = _reader_api_readiness(audit, installed_version)
    return distribution, reader


__all__ = [
    "COMPATIBILITY_DIAGNOSTIC_OUTCOMES",
    "COMPATIBILITY_DIAGNOSTIC_SCOPES",
    "COMPATIBILITY_REASON_CODES",
    "CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION",
    "DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS",
    "CompatibilityDiagnosticError",
    "CrossProducerCompatibilityDiagnostic",
    "ProducerIntegrationReadiness",
    "diagnose_audited_reader_readiness",
    "diagnose_installed_producer_readiness",
    "explain_live_adapter_support",
]
