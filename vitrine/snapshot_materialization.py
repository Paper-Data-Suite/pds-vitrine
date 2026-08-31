"""Authority, provider, renderer, and exact-byte Snapshot materialization primitives."""

from __future__ import annotations

import hashlib
import hmac
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotEntryPlan,
)
from vitrine.models.common import (
    lower_key_tuple,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_lower_identifier,
    require_nonnegative_int,
    require_optional_text,
    require_relative_path,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    SnapshotStagingArea,
    normalize_snapshot_relative_path,
    write_staging_bytes_exclusive,
)

SNAPSHOT_BUILD_AUTHORITY_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
SNAPSHOT_BUILD_OPERATION: Final[str] = "build_snapshot"
SNAPSHOT_SOURCE_STABILITY_CONTRACT: Final[str] = "filesystem_reread_v1"
SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT: Final[str] = "authorized_source_bytes_v1"

SNAPSHOT_MATERIALIZATION_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot.invalid_request",
        "snapshot.authority_denied",
        "snapshot.authority_unresolved",
        "snapshot.source_provider_missing",
        "snapshot.source_provider_conflict",
        "snapshot.source_unavailable",
        "snapshot.source_path_unsafe",
        "snapshot.source_integrity_failed",
        "snapshot.source_digest_mismatch",
        "snapshot.source_changed_during_acquisition",
        "snapshot.renderer_missing",
        "snapshot.renderer_conflict",
        "snapshot.render_failed",
        "snapshot.entry_digest_mismatch",
        "snapshot.staging_conflict",
        "snapshot.staging_invalid",
    }
)


class SnapshotMaterializationError(RuntimeError):
    """Expected byte-materialization failure with stable privacy-safe metadata."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in SNAPSHOT_MATERIALIZATION_CODES:
            raise ValueError(f"unsupported Snapshot materialization code: {code}")
        self.code = code
        self.stage = stage
        super().__init__(message)


def _wrap_custody(error: SnapshotCustodyError, *, stage: str) -> SnapshotMaterializationError:
    code = error.code
    if code not in SNAPSHOT_MATERIALIZATION_CODES:
        code = "snapshot.staging_invalid"
    return SnapshotMaterializationError(code, str(error), stage=stage)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildAuthorityRequest:
    operation: str
    snapshot_series_id: str
    snapshot_build_request_id: str
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    actor: ActorAttribution

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "operation",
                require_enum(
                    self.operation,
                    "operation",
                    frozenset({SNAPSHOT_BUILD_OPERATION}),
                ),
            )
            for name in (
                "snapshot_series_id",
                "snapshot_build_request_id",
                "snapshot_build_plan_id",
                "snapshot_build_attempt_id",
                "portfolio_id",
                "portfolio_subject_id",
                "profile_binding_id",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            if not isinstance(self.actor, ActorAttribution):
                raise VitrineModelValidationError("actor must be ActorAttribution.")
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot build-authority request is invalid.",
                stage="authority_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildAuthorityDecision:
    outcome: str
    authority_reference: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "outcome",
                require_enum(
                    self.outcome,
                    "outcome",
                    SNAPSHOT_BUILD_AUTHORITY_OUTCOMES,
                ),
            )
            object.__setattr__(
                self,
                "authority_reference",
                require_optional_text(
                    self.authority_reference,
                    "authority_reference",
                    maximum=500,
                ),
            )
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot build-authority decision is invalid.",
                stage="authority",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Allowed Snapshot build authority requires authority_reference.",
                stage="authority",
            )


class SnapshotBuildAuthorityGate(Protocol):
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSourceProviderDescriptor:
    provider_id: str
    provider_version: str
    producer_module_id: str
    projection_kind: str
    projection_contract_version: str
    artifact_kind: str
    representation_kind: str

    def __post_init__(self) -> None:
        try:
            for name in ("provider_id", "provider_version", "projection_contract_version"):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            object.__setattr__(
                self,
                "producer_module_id",
                require_lower_identifier(self.producer_module_id, "producer_module_id"),
            )
            for name in ("projection_kind", "artifact_kind", "representation_kind"):
                object.__setattr__(
                    self,
                    name,
                    require_controlled_key(getattr(self, name), name),
                )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot source-provider descriptor is invalid.",
                stage="provider_registry",
            ) from error

    @property
    def support_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.producer_module_id,
            self.projection_kind,
            self.projection_contract_version,
            self.artifact_kind,
            self.representation_kind,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSourceRequest:
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    entry_plan: SnapshotEntryPlan

    def __post_init__(self) -> None:
        try:
            for name in ("snapshot_build_plan_id", "snapshot_build_attempt_id"):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot source request is invalid.",
                stage="source_request",
            ) from error
        if not isinstance(self.entry_plan, SnapshotEntryPlan):
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot source request requires SnapshotEntryPlan.",
                stage="source_request",
            )
        if self.entry_plan.materialization_kind != "copied_source":
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot source request requires copied_source Entry Plan.",
                stage="source_request",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSourceResult:
    provider_id: str
    provider_version: str
    source_publication_id: str
    source_artifact_id: str
    source_root: Path
    source_relative_path: str
    stability_contract: str = SNAPSHOT_SOURCE_STABILITY_CONTRACT

    def __post_init__(self) -> None:
        try:
            for name in (
                "provider_id",
                "provider_version",
                "source_publication_id",
                "source_artifact_id",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            if not isinstance(self.source_root, Path):
                raise VitrineModelValidationError("source_root must be pathlib.Path.")
            object.__setattr__(
                self,
                "source_relative_path",
                require_relative_path(
                    self.source_relative_path, "source_relative_path"
                ),
            )
            object.__setattr__(
                self,
                "stability_contract",
                require_identifier(self.stability_contract, "stability_contract"),
            )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot source result is invalid.",
                stage="source_resolution",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotAuthorizedSourceBytesResult:
    """Producer-authorized immutable bytes for one exact planned Artifact."""

    provider_id: str
    provider_version: str
    source_publication_id: str
    source_artifact_id: str
    content: bytes
    media_type: str
    source_digest: DigestReference | None = None
    byte_size: int | None = None
    acquisition_contract_version: str = SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT

    def __post_init__(self) -> None:
        try:
            for name in (
                "provider_id",
                "provider_version",
                "source_publication_id",
                "source_artifact_id",
                "acquisition_contract_version",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            if not isinstance(self.content, bytes):
                raise VitrineModelValidationError("content must be immutable bytes.")
            object.__setattr__(
                self,
                "media_type",
                require_text(self.media_type, "media_type", maximum=200),
            )
            if self.source_digest is not None and not isinstance(
                self.source_digest, DigestReference
            ):
                raise VitrineModelValidationError(
                    "source_digest must be DigestReference or null."
                )
            if self.byte_size is not None:
                object.__setattr__(
                    self,
                    "byte_size",
                    require_nonnegative_int(self.byte_size, "byte_size"),
                )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Authorized Snapshot source-byte result is invalid.",
                stage="source_resolution",
            ) from error


class SnapshotSourceProvider(Protocol):
    @property
    def descriptor(self) -> SnapshotSourceProviderDescriptor: ...

    def resolve(
        self, request: SnapshotSourceRequest
    ) -> SnapshotSourceResult | SnapshotAuthorizedSourceBytesResult: ...

    def confirm_stability(
        self, request: SnapshotSourceRequest, result: SnapshotSourceResult
    ) -> bool: ...


class SnapshotSourceProviderRegistry:
    def __init__(self, providers: tuple[SnapshotSourceProvider, ...] = ()) -> None:
        self._providers = tuple(providers)
        ids = [item.descriptor.provider_id for item in self._providers]
        if len(set(ids)) != len(ids):
            raise SnapshotMaterializationError(
                "snapshot.source_provider_conflict",
                "Snapshot source-provider identities must be unique.",
                stage="provider_registry",
            )

    def select(self, entry_plan: SnapshotEntryPlan) -> SnapshotSourceProvider:
        artifact = entry_plan.source_artifact
        if (
            entry_plan.materialization_kind != "copied_source"
            or artifact is None
            or entry_plan.producer_module_id is None
            or entry_plan.projection_kind is None
            or entry_plan.projection_contract_version is None
        ):
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Copied Snapshot Entry Plan has incomplete provider support metadata.",
                stage="provider_selection",
            )
        key = (
            entry_plan.producer_module_id,
            entry_plan.projection_kind,
            entry_plan.projection_contract_version,
            artifact.artifact_kind,
            artifact.representation_kind,
        )
        matches = tuple(
            provider
            for provider in self._providers
            if provider.descriptor.support_key == key
        )
        if not matches:
            raise SnapshotMaterializationError(
                "snapshot.source_provider_missing",
                "No exact Snapshot source provider supports the planned source contract.",
                stage="provider_selection",
            )
        if len(matches) > 1:
            raise SnapshotMaterializationError(
                "snapshot.source_provider_conflict",
                "Multiple Snapshot source providers match the exact planned source contract.",
                stage="provider_selection",
            )
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotRendererDescriptor:
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str

    def __post_init__(self) -> None:
        try:
            for name in (
                "renderer_id",
                "renderer_version",
                "renderer_contract_version",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot renderer descriptor is invalid.",
                stage="renderer_registry",
            ) from error

    @property
    def support_key(self) -> tuple[str, str, str]:
        return (self.renderer_id, self.renderer_version, self.renderer_contract_version)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotRenderRequest:
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    entry_plan: SnapshotEntryPlan

    def __post_init__(self) -> None:
        try:
            for name in ("snapshot_build_plan_id", "snapshot_build_attempt_id"):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot render request is invalid.",
                stage="render_request",
            ) from error
        if not isinstance(self.entry_plan, SnapshotEntryPlan):
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot render request requires SnapshotEntryPlan.",
                stage="render_request",
            )
        if self.entry_plan.materialization_kind != "generated_vitrine":
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Snapshot render request requires generated_vitrine Entry Plan.",
                stage="render_request",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotRenderResult:
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    content: bytes
    media_type: str
    configuration_digest: DigestReference
    template_digest: DigestReference | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        try:
            for name in (
                "renderer_id",
                "renderer_version",
                "renderer_contract_version",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            if not isinstance(self.content, bytes):
                raise VitrineModelValidationError("content must be bytes.")
            object.__setattr__(
                self, "media_type", require_text(self.media_type, "media_type", maximum=200)
            )
            if not isinstance(self.configuration_digest, DigestReference):
                raise VitrineModelValidationError(
                    "configuration_digest must be DigestReference."
                )
            if self.template_digest is not None and not isinstance(
                self.template_digest, DigestReference
            ):
                raise VitrineModelValidationError(
                    "template_digest must be DigestReference or null."
                )
            object.__setattr__(
                self,
                "language",
                require_optional_text(self.language, "language", maximum=64),
            )
        except VitrineModelValidationError as error:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Snapshot renderer returned an invalid result.",
                stage="render",
            ) from error


class SnapshotRenderer(Protocol):
    @property
    def descriptor(self) -> SnapshotRendererDescriptor: ...

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult: ...


class SnapshotRendererRegistry:
    def __init__(self, renderers: tuple[SnapshotRenderer, ...] = ()) -> None:
        self._renderers = tuple(renderers)
        ids = [item.descriptor.support_key for item in self._renderers]
        if len(set(ids)) != len(ids):
            raise SnapshotMaterializationError(
                "snapshot.renderer_conflict",
                "Snapshot renderer support keys must be unique.",
                stage="renderer_registry",
            )

    def select(self, entry_plan: SnapshotEntryPlan) -> SnapshotRenderer:
        if (
            entry_plan.materialization_kind != "generated_vitrine"
            or entry_plan.renderer_id is None
            or entry_plan.renderer_version is None
            or entry_plan.renderer_contract_version is None
        ):
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Generated Snapshot Entry Plan has incomplete renderer metadata.",
                stage="renderer_selection",
            )
        key = (
            entry_plan.renderer_id,
            entry_plan.renderer_version,
            entry_plan.renderer_contract_version,
        )
        matches = tuple(
            renderer
            for renderer in self._renderers
            if renderer.descriptor.support_key == key
        )
        if not matches:
            raise SnapshotMaterializationError(
                "snapshot.renderer_missing",
                "No exact Snapshot renderer supports the planned renderer contract.",
                stage="renderer_selection",
            )
        if len(matches) > 1:
            raise SnapshotMaterializationError(
                "snapshot.renderer_conflict",
                "Multiple Snapshot renderers match the planned renderer contract.",
                stage="renderer_selection",
            )
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotCopiedBytesResult:
    entry_plan_id: str
    target_relative_path: str
    source_provider_id: str
    source_provider_version: str
    acquired_source_digest: DigestReference
    copied_output_digest: DigestReference
    byte_size: int
    source_stability_result: str = "verified"


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotGeneratedBytesResult:
    entry_plan_id: str
    target_relative_path: str
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    output_digest: DigestReference
    byte_size: int
    configuration_digest: DigestReference
    template_digest: DigestReference | None


def _sha256(payload: bytes) -> DigestReference:
    return DigestReference(value=hashlib.sha256(payload).hexdigest())


def _entry_for_plan(plan: SnapshotBuildPlan, entry_plan_id: str) -> SnapshotEntryPlan:
    try:
        entry_plan_id = require_identifier(entry_plan_id, "entry_plan_id")
    except VitrineModelValidationError as error:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request", "Snapshot Entry Plan identity is invalid.", stage="request"
        ) from error
    entry = next(
        (item for item in plan.entry_plans if item.entry_plan_id == entry_plan_id),
        None,
    )
    if entry is None:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot Entry Plan does not belong to the Build Plan.",
            stage="request",
        )
    return entry


def _authorize(
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    gate: SnapshotBuildAuthorityGate,
) -> SnapshotBuildAuthorityDecision:
    if attempt.snapshot_build_plan_id != plan.snapshot_build_plan_id:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot Attempt does not belong to the Build Plan.",
            stage="authority_request",
        )
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
    decision = gate.authorize(request)
    if not isinstance(decision, SnapshotBuildAuthorityDecision):
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot build-authority gate returned an invalid decision.",
            stage="authority",
        )
    if decision.outcome == "denied":
        raise SnapshotMaterializationError(
            "snapshot.authority_denied",
            "Snapshot build authority was denied.",
            stage="authority",
        )
    if decision.outcome == "unresolved":
        raise SnapshotMaterializationError(
            "snapshot.authority_unresolved",
            "Snapshot build authority is unresolved.",
            stage="authority",
        )
    return decision


def _is_link_or_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        raw_attrs = getattr(path.lstat(), "st_file_attributes", 0)
        attrs = raw_attrs if isinstance(raw_attrs, int) else 0
    except OSError as error:
        raise SnapshotMaterializationError(
            "snapshot.source_unavailable",
            "Planned Snapshot source could not be inspected.",
            stage="source_read",
        ) from error
    raw_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    flag = raw_flag if isinstance(raw_flag, int) else 0
    return bool(flag and attrs & flag)


def _source_file(result: SnapshotSourceResult) -> Path:
    root = result.source_root
    if not root.is_absolute():
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Snapshot source provider root must be absolute.",
            stage="source_resolution",
        )
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise SnapshotMaterializationError(
            "snapshot.source_unavailable",
            "Snapshot source provider root is unavailable.",
            stage="source_resolution",
        ) from error
    if resolved_root != root:
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Snapshot source provider root must be an exact canonical path.",
            stage="source_resolution",
        )
    if not root.is_dir() or _is_link_or_reparse(root):
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Snapshot source provider root must be an ordinary directory.",
            stage="source_resolution",
        )
    try:
        relative = normalize_snapshot_relative_path(result.source_relative_path)
    except SnapshotCustodyError as error:
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Snapshot source provider returned an unsafe relative path.",
            stage="source_resolution",
        ) from error
    current = root
    parts = relative.split("/")
    for part in parts:
        current = current / part
        if not current.exists():
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Planned Snapshot source is unavailable.",
                stage="source_read",
            )
        if _is_link_or_reparse(current):
            raise SnapshotMaterializationError(
                "snapshot.source_path_unsafe",
                "Planned Snapshot source traverses a link or reparse point.",
                stage="source_read",
            )
    if not current.is_file():
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Planned Snapshot source must be a regular file.",
            stage="source_read",
        )
    try:
        current.relative_to(root)
    except ValueError as error:
        raise SnapshotMaterializationError(
            "snapshot.source_path_unsafe",
            "Planned Snapshot source escaped its approved root.",
            stage="source_read",
        ) from error
    return current


def copy_planned_source_to_staging(
    *,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    entry_plan_id: str,
    staging: SnapshotStagingArea,
    authority_gate: SnapshotBuildAuthorityGate,
    source_providers: SnapshotSourceProviderRegistry,
) -> SnapshotCopiedBytesResult:
    """Acquire exact planned source bytes and verify an exclusive staged copy."""

    entry = _entry_for_plan(plan, entry_plan_id)
    if entry.materialization_kind != "copied_source":
        raise SnapshotMaterializationError(
            "snapshot.invalid_request", "Entry Plan is not copied_source.", stage="request"
        )
    if staging.snapshot_build_attempt_id != attempt.snapshot_build_attempt_id:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot staging area belongs to a different Attempt.",
            stage="request",
        )
    _authorize(plan, attempt, authority_gate)
    provider = source_providers.select(entry)
    request = SnapshotSourceRequest(
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        entry_plan=entry,
    )
    try:
        resolved = provider.resolve(request)
    except SnapshotMaterializationError:
        raise
    except Exception as error:
        raise SnapshotMaterializationError(
            "snapshot.source_unavailable",
            "Snapshot source provider could not resolve the planned source.",
            stage="source_resolution",
        ) from error
    if not isinstance(
        resolved, (SnapshotSourceResult, SnapshotAuthorizedSourceBytesResult)
    ):
        raise SnapshotMaterializationError(
            "snapshot.source_integrity_failed",
            "Snapshot source provider returned an unsupported result type.",
            stage="source_resolution",
        )

    descriptor = provider.descriptor
    artifact = entry.source_artifact
    assert artifact is not None
    if (
        resolved.provider_id != descriptor.provider_id
        or resolved.provider_version != descriptor.provider_version
        or resolved.source_publication_id != entry.source_publication_id
        or resolved.source_artifact_id != artifact.artifact_id
    ):
        raise SnapshotMaterializationError(
            "snapshot.source_integrity_failed",
            "Snapshot source provider resolution does not match the immutable Entry Plan.",
            stage="source_resolution",
        )

    filesystem_result: SnapshotSourceResult | None = None
    if isinstance(resolved, SnapshotAuthorizedSourceBytesResult):
        if (
            resolved.acquisition_contract_version
            != SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
            or resolved.media_type != entry.media_type
            or resolved.media_type != artifact.media_type
        ):
            raise SnapshotMaterializationError(
                "snapshot.source_integrity_failed",
                "Authorized source-byte metadata does not match the immutable Entry Plan.",
                stage="source_resolution",
            )
        acquired = resolved.content
        acquired_digest = _sha256(acquired)
        if resolved.source_digest is not None and not hmac.compare_digest(
            resolved.source_digest.value, acquired_digest.value
        ):
            raise SnapshotMaterializationError(
                "snapshot.source_digest_mismatch",
                "Authorized source-byte digest does not match the returned bytes.",
                stage="source_verify",
            )
        if resolved.byte_size is not None and resolved.byte_size != len(acquired):
            raise SnapshotMaterializationError(
                "snapshot.source_integrity_failed",
                "Authorized source-byte size does not match the returned bytes.",
                stage="source_verify",
            )
        source_stability_result = "not_applicable"
    else:
        filesystem_result = resolved
        if (
            artifact.source_locator is None
            or resolved.source_relative_path != artifact.source_locator
            or resolved.stability_contract != SNAPSHOT_SOURCE_STABILITY_CONTRACT
        ):
            raise SnapshotMaterializationError(
                "snapshot.source_integrity_failed",
                "Filesystem source resolution does not match the immutable Entry Plan.",
                stage="source_resolution",
            )
        source_path = _source_file(resolved)
        try:
            acquired = source_path.read_bytes()
        except OSError as error:
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Planned Snapshot source could not be read.",
                stage="source_read",
            ) from error
        acquired_digest = _sha256(acquired)
        source_stability_result = "verified"

    claims = tuple(
        claim
        for claim in (entry.producer_source_digest_claim, artifact.source_digest)
        if claim is not None
    )
    for claim in claims:
        if not hmac.compare_digest(claim.value, acquired_digest.value):
            raise SnapshotMaterializationError(
                "snapshot.source_digest_mismatch",
                "Planned Snapshot source digest does not match the acquired bytes.",
                stage="source_verify",
            )
    if artifact.byte_size is not None and artifact.byte_size != len(acquired):
        raise SnapshotMaterializationError(
            "snapshot.source_integrity_failed",
            "Planned Snapshot source size does not match the acquired bytes.",
            stage="source_verify",
        )
    assert entry.target_relative_path is not None
    try:
        target = write_staging_bytes_exclusive(
            staging, entry.target_relative_path, acquired
        )
    except SnapshotCustodyError as error:
        raise _wrap_custody(error, stage="staging_write") from error
    try:
        staged = target.read_bytes()
    except OSError as error:
        raise SnapshotMaterializationError(
            "snapshot.staging_invalid",
            "Staged Snapshot bytes could not be reloaded.",
            stage="staging_verify",
        ) from error
    output_digest = _sha256(staged)
    if len(staged) != len(acquired) or not hmac.compare_digest(
        output_digest.value, acquired_digest.value
    ):
        raise SnapshotMaterializationError(
            "snapshot.entry_digest_mismatch",
            "Staged Snapshot bytes do not match the acquired source bytes.",
            stage="staging_verify",
        )

    if filesystem_result is not None:
        source_path = _source_file(filesystem_result)
        try:
            provider_stable = provider.confirm_stability(request, filesystem_result)
        except Exception as error:
            raise SnapshotMaterializationError(
                "snapshot.source_changed_during_acquisition",
                "Snapshot source stability could not be confirmed.",
                stage="source_stability",
            ) from error
        try:
            reread = source_path.read_bytes()
        except OSError as error:
            raise SnapshotMaterializationError(
                "snapshot.source_changed_during_acquisition",
                "Snapshot source became unavailable during acquisition.",
                stage="source_stability",
            ) from error
        reread_digest = _sha256(reread)
        if (
            not provider_stable
            or len(reread) != len(acquired)
            or not hmac.compare_digest(reread_digest.value, acquired_digest.value)
        ):
            try:
                target.unlink()
            except OSError:
                pass
            raise SnapshotMaterializationError(
                "snapshot.source_changed_during_acquisition",
                "Snapshot source changed during acquisition.",
                stage="source_stability",
            )

    return SnapshotCopiedBytesResult(
        entry_plan_id=entry.entry_plan_id,
        target_relative_path=entry.target_relative_path,
        source_provider_id=descriptor.provider_id,
        source_provider_version=descriptor.provider_version,
        acquired_source_digest=acquired_digest,
        copied_output_digest=output_digest,
        byte_size=len(staged),
        source_stability_result=source_stability_result,
    )


def render_planned_entry_to_staging(
    *,
    plan: SnapshotBuildPlan,
    attempt: SnapshotBuildAttempt,
    entry_plan_id: str,
    staging: SnapshotStagingArea,
    authority_gate: SnapshotBuildAuthorityGate,
    renderers: SnapshotRendererRegistry,
) -> SnapshotGeneratedBytesResult:
    """Render one exact planned Vitrine-generated Entry into guarded staging."""

    entry = _entry_for_plan(plan, entry_plan_id)
    if entry.materialization_kind != "generated_vitrine":
        raise SnapshotMaterializationError(
            "snapshot.invalid_request", "Entry Plan is not generated_vitrine.", stage="request"
        )
    if staging.snapshot_build_attempt_id != attempt.snapshot_build_attempt_id:
        raise SnapshotMaterializationError(
            "snapshot.invalid_request",
            "Snapshot staging area belongs to a different Attempt.",
            stage="request",
        )
    _authorize(plan, attempt, authority_gate)
    renderer = renderers.select(entry)
    request = SnapshotRenderRequest(
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        entry_plan=entry,
    )
    try:
        result = renderer.render(request)
    except SnapshotMaterializationError:
        raise
    except Exception as error:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Snapshot renderer failed.",
            stage="render",
        ) from error
    descriptor = renderer.descriptor
    if (
        result.renderer_id != descriptor.renderer_id
        or result.renderer_version != descriptor.renderer_version
        or result.renderer_contract_version != descriptor.renderer_contract_version
    ):
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Snapshot renderer result identity does not match the immutable Entry Plan.",
            stage="render_verify",
        )
    if result.media_type != entry.media_type:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Snapshot renderer media type does not match the immutable Entry Plan.",
            stage="render_verify",
        )
    if (
        entry.renderer_configuration_digest is None
        or result.configuration_digest != entry.renderer_configuration_digest
    ):
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Snapshot renderer configuration digest does not match the immutable Entry Plan.",
            stage="render_verify",
        )
    if result.template_digest != entry.renderer_template_digest:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Snapshot renderer template digest does not match the immutable Entry Plan.",
            stage="render_verify",
        )
    assert entry.target_relative_path is not None
    try:
        target = write_staging_bytes_exclusive(
            staging, entry.target_relative_path, result.content
        )
    except SnapshotCustodyError as error:
        raise _wrap_custody(error, stage="staging_write") from error
    try:
        staged = target.read_bytes()
    except OSError as error:
        raise SnapshotMaterializationError(
            "snapshot.staging_invalid",
            "Generated Snapshot bytes could not be reloaded.",
            stage="staging_verify",
        ) from error
    output_digest = _sha256(staged)
    if staged != result.content:
        raise SnapshotMaterializationError(
            "snapshot.entry_digest_mismatch",
            "Generated Snapshot staging bytes changed after rendering.",
            stage="staging_verify",
        )
    return SnapshotGeneratedBytesResult(
        entry_plan_id=entry.entry_plan_id,
        target_relative_path=entry.target_relative_path,
        renderer_id=descriptor.renderer_id,
        renderer_version=descriptor.renderer_version,
        renderer_contract_version=descriptor.renderer_contract_version,
        output_digest=output_digest,
        byte_size=len(staged),
        configuration_digest=result.configuration_digest,
        template_digest=result.template_digest,
    )


__all__ = [
    "SNAPSHOT_BUILD_AUTHORITY_OUTCOMES",
    "SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT",
    "SNAPSHOT_BUILD_OPERATION",
    "SNAPSHOT_SOURCE_STABILITY_CONTRACT",
    "SnapshotBuildAuthorityDecision",
    "SnapshotBuildAuthorityGate",
    "SnapshotAuthorizedSourceBytesResult",
    "SnapshotBuildAuthorityRequest",
    "SnapshotCopiedBytesResult",
    "SnapshotGeneratedBytesResult",
    "SnapshotMaterializationError",
    "SnapshotRenderRequest",
    "SnapshotRenderResult",
    "SnapshotRenderer",
    "SnapshotRendererDescriptor",
    "SnapshotRendererRegistry",
    "SnapshotSourceProvider",
    "SnapshotSourceProviderDescriptor",
    "SnapshotSourceProviderRegistry",
    "SnapshotSourceRequest",
    "SnapshotSourceResult",
    "copy_planned_source_to_staging",
    "render_planned_entry_to_staging",
]
