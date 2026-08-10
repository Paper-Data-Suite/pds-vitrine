"""Pure producer-reader and projection-adapter contracts for Vitrine.

Issue #32 defines integration configuration and transient projection values only.
This module performs no workspace discovery, authorization, persistence, network
access, or producer-package discovery.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from pds_core.publication_records import PUBLICATION_CAPABILITIES, PUBLICATION_KINDS

from vitrine.models.common import (
    require_controlled_key,
    require_identifier,
    require_lower_identifier,
    require_optional_text,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.models.sources import (
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)

INTEGRATION_KINDS = frozenset({"development_fixture", "live"})
ADAPTER_FAILURE_CODES = frozenset(
    {
        "adapter.invalid_support_request",
        "adapter.invalid_declaration",
        "adapter.duplicate_identity",
        "adapter.unsupported_contract",
        "adapter.conflict",
        "adapter.fixture_not_enabled",
        "reader.unavailable",
        "reader.incompatible",
        "reader.decode_failed",
        "reader.validation_failed",
        "projection.invalid_input",
        "projection.failed",
    }
)
_DIAGNOSTIC_CODE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")

ProjectionScalar: TypeAlias = str | int | float | bool | None
ProjectionValue: TypeAlias = ProjectionScalar | tuple[ProjectionScalar, ...]


class ProducerAdapterError(RuntimeError):
    """Stable privacy-safe adapter, reader, registry, or projection failure."""

    def __init__(
        self,
        code: str,
        stage: str,
        message: str,
        *,
        adapter_id: str | None = None,
        producer_module_id: str | None = None,
        publication_kind: str | None = None,
        manifest_contract_version: str | None = None,
        diagnostic_fields: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if code not in ADAPTER_FAILURE_CODES:
            raise ValueError(f"Unsupported producer-adapter failure code: {code}")
        if not isinstance(stage, str) or not stage:
            raise ValueError("stage must be nonempty.")
        self.code = code
        self.stage = stage
        self.adapter_id = adapter_id
        self.producer_module_id = producer_module_id
        self.publication_kind = publication_kind
        self.manifest_contract_version = manifest_contract_version
        self.diagnostic_fields = tuple(sorted(diagnostic_fields))
        super().__init__(message)


class ProducerAdapterUnsupportedError(ProducerAdapterError):
    """No exact adapter declaration matches a support request."""


class ProducerAdapterConflictError(ProducerAdapterError):
    """More than one adapter declaration matches a support request."""


class ProducerReaderError(ProducerAdapterError):
    """A producer reader could not produce one validated public model."""


class ProducerProjectionError(ProducerAdapterError):
    """A selected adapter could not produce its transient projection."""


def _validation_failure(code: str, stage: str, message: str) -> ProducerAdapterError:
    return ProducerAdapterError(code, stage, message)


def _identifier(value: object, field_name: str, *, code: str, stage: str) -> str:
    try:
        return require_identifier(value, field_name)
    except VitrineModelValidationError as error:
        raise _validation_failure(code, stage, str(error)) from error


def _lower_identifier(
    value: object, field_name: str, *, code: str, stage: str
) -> str:
    try:
        return require_lower_identifier(value, field_name)
    except VitrineModelValidationError as error:
        raise _validation_failure(code, stage, str(error)) from error


def _optional_identifier(
    value: object, field_name: str, *, code: str, stage: str
) -> str | None:
    if value is None:
        return None
    return _identifier(value, field_name, code=code, stage=stage)


def _integration_kind(value: object, *, code: str, stage: str) -> str:
    if not isinstance(value, str) or value not in INTEGRATION_KINDS:
        raise _validation_failure(
            code,
            stage,
            "integration_kind must be 'development_fixture' or 'live'.",
        )
    return value


def _capabilities(
    values: Iterable[str], field_name: str, *, code: str, stage: str
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise _validation_failure(code, stage, f"{field_name} must be an iterable.")
    try:
        raw = tuple(values)
    except TypeError as error:
        raise _validation_failure(code, stage, f"{field_name} must be iterable.") from error
    normalized: list[str] = []
    for value in raw:
        if not isinstance(value, str) or value not in PUBLICATION_CAPABILITIES:
            raise _validation_failure(
                code,
                stage,
                f"{field_name} contains an unsupported Core publication capability.",
            )
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise _validation_failure(code, stage, f"{field_name} must not contain duplicates.")
    return tuple(sorted(normalized))


def _controlled_tuple(
    values: Iterable[str], field_name: str, *, code: str, stage: str
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise _validation_failure(code, stage, f"{field_name} must be an iterable.")
    try:
        raw = tuple(values)
    except TypeError as error:
        raise _validation_failure(code, stage, f"{field_name} must be iterable.") from error
    normalized: list[str] = []
    for value in raw:
        try:
            normalized.append(require_controlled_key(value, field_name))
        except VitrineModelValidationError as error:
            raise _validation_failure(code, stage, str(error)) from error
    if len(set(normalized)) != len(normalized):
        raise _validation_failure(code, stage, f"{field_name} must not contain duplicates.")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerAdapterSupportRequest:
    producer_module_id: str
    core_publication_schema_version: str
    publication_kind: str
    manifest_contract_version: str
    producer_contract_version: str | None
    source_record_kind: str | None
    source_record_contract_version: str | None
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        code = "adapter.invalid_support_request"
        stage = "support_request"
        object.__setattr__(
            self,
            "producer_module_id",
            _lower_identifier(
                self.producer_module_id,
                "producer_module_id",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "core_publication_schema_version",
            _identifier(
                self.core_publication_schema_version,
                "core_publication_schema_version",
                code=code,
                stage=stage,
            ),
        )
        if self.publication_kind not in PUBLICATION_KINDS:
            raise _validation_failure(
                code, stage, "publication_kind is not a Core publication kind."
            )
        object.__setattr__(
            self,
            "manifest_contract_version",
            _identifier(
                self.manifest_contract_version,
                "manifest_contract_version",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "producer_contract_version",
            _optional_identifier(
                self.producer_contract_version,
                "producer_contract_version",
                code=code,
                stage=stage,
            ),
        )
        if self.source_record_kind is None:
            if self.source_record_contract_version is not None:
                raise _validation_failure(
                    code,
                    stage,
                    "source_record_contract_version requires source_record_kind.",
                )
        else:
            object.__setattr__(
                self,
                "source_record_kind",
                _lower_identifier(
                    self.source_record_kind,
                    "source_record_kind",
                    code=code,
                    stage=stage,
                ),
            )
        object.__setattr__(
            self,
            "source_record_contract_version",
            _optional_identifier(
                self.source_record_contract_version,
                "source_record_contract_version",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "capabilities",
            _capabilities(self.capabilities, "capabilities", code=code, stage=stage),
        )

    @property
    def safe_diagnostic_fields(self) -> tuple[tuple[str, str], ...]:
        return (
            ("capabilities", ",".join(self.capabilities)),
            ("core_publication_schema_version", self.core_publication_schema_version),
            ("manifest_contract_version", self.manifest_contract_version),
            ("producer_contract_version", self.producer_contract_version or "<absent>"),
            ("producer_module_id", self.producer_module_id),
            ("publication_kind", self.publication_kind),
            ("source_record_contract_version", self.source_record_contract_version or "<absent>"),
            ("source_record_kind", self.source_record_kind or "<absent>"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerAdapterSupportKey:
    producer_module_id: str
    core_publication_schema_version: str
    publication_kind: str
    manifest_contract_version: str
    producer_contract_version: str | None
    source_record_kind: str | None
    source_record_contract_version: str | None
    required_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        code = "adapter.invalid_declaration"
        stage = "support_key"
        object.__setattr__(
            self,
            "producer_module_id",
            _lower_identifier(
                self.producer_module_id,
                "producer_module_id",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "core_publication_schema_version",
            _identifier(
                self.core_publication_schema_version,
                "core_publication_schema_version",
                code=code,
                stage=stage,
            ),
        )
        if self.publication_kind not in PUBLICATION_KINDS:
            raise _validation_failure(
                code, stage, "publication_kind is not a Core publication kind."
            )
        object.__setattr__(
            self,
            "manifest_contract_version",
            _identifier(
                self.manifest_contract_version,
                "manifest_contract_version",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "producer_contract_version",
            _optional_identifier(
                self.producer_contract_version,
                "producer_contract_version",
                code=code,
                stage=stage,
            ),
        )
        if self.source_record_kind is None:
            if self.source_record_contract_version is not None:
                raise _validation_failure(
                    code,
                    stage,
                    "source_record_contract_version requires source_record_kind.",
                )
        else:
            object.__setattr__(
                self,
                "source_record_kind",
                _lower_identifier(
                    self.source_record_kind,
                    "source_record_kind",
                    code=code,
                    stage=stage,
                ),
            )
        object.__setattr__(
            self,
            "source_record_contract_version",
            _optional_identifier(
                self.source_record_contract_version,
                "source_record_contract_version",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _capabilities(
                self.required_capabilities,
                "required_capabilities",
                code=code,
                stage=stage,
            ),
        )

    def matches(self, request: ProducerAdapterSupportRequest) -> bool:
        return (
            self.producer_module_id == request.producer_module_id
            and self.core_publication_schema_version
            == request.core_publication_schema_version
            and self.publication_kind == request.publication_kind
            and self.manifest_contract_version == request.manifest_contract_version
            and self.producer_contract_version == request.producer_contract_version
            and self.source_record_kind == request.source_record_kind
            and self.source_record_contract_version
            == request.source_record_contract_version
            and set(self.required_capabilities).issubset(request.capabilities)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerReaderDescriptor:
    public_reader_id: str
    reader_contract_version: str
    package_identity: str
    integration_kind: str

    def __post_init__(self) -> None:
        code = "adapter.invalid_declaration"
        stage = "reader_descriptor"
        object.__setattr__(
            self,
            "public_reader_id",
            _identifier(
                self.public_reader_id, "public_reader_id", code=code, stage=stage
            ),
        )
        object.__setattr__(
            self,
            "reader_contract_version",
            _identifier(
                self.reader_contract_version,
                "reader_contract_version",
                code=code,
                stage=stage,
            ),
        )
        try:
            package_identity = require_text(
                self.package_identity, "package_identity", maximum=256
            )
        except VitrineModelValidationError as error:
            raise _validation_failure(code, stage, str(error)) from error
        object.__setattr__(self, "package_identity", package_identity)
        object.__setattr__(
            self,
            "integration_kind",
            _integration_kind(self.integration_kind, code=code, stage=stage),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerProjectionAdapterDeclaration:
    adapter_id: str
    adapter_contract_version: str
    candidate_projection_contract_version: str
    support_key: ProducerAdapterSupportKey
    public_reader_id: str
    reader_contract_version: str
    reader_package_identity: str
    supported_source_families: tuple[str, ...]
    supported_representation_families: tuple[str, ...]
    diagnostic_contract_version: str
    integration_kind: str

    def __post_init__(self) -> None:
        code = "adapter.invalid_declaration"
        stage = "declaration"
        object.__setattr__(
            self,
            "adapter_id",
            _identifier(self.adapter_id, "adapter_id", code=code, stage=stage),
        )
        for field_name in (
            "adapter_contract_version",
            "candidate_projection_contract_version",
            "public_reader_id",
            "reader_contract_version",
            "diagnostic_contract_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(
                    getattr(self, field_name), field_name, code=code, stage=stage
                ),
            )
        if not isinstance(self.support_key, ProducerAdapterSupportKey):
            raise _validation_failure(
                code, stage, "support_key must be ProducerAdapterSupportKey."
            )
        try:
            reader_package_identity = require_text(
                self.reader_package_identity,
                "reader_package_identity",
                maximum=256,
            )
        except VitrineModelValidationError as error:
            raise _validation_failure(code, stage, str(error)) from error
        object.__setattr__(self, "reader_package_identity", reader_package_identity)
        object.__setattr__(
            self,
            "supported_source_families",
            _controlled_tuple(
                self.supported_source_families,
                "supported_source_families",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "supported_representation_families",
            _controlled_tuple(
                self.supported_representation_families,
                "supported_representation_families",
                code=code,
                stage=stage,
            ),
        )
        object.__setattr__(
            self,
            "integration_kind",
            _integration_kind(self.integration_kind, code=code, stage=stage),
        )

    @property
    def identity(self) -> tuple[str, str]:
        return (self.adapter_id, self.adapter_contract_version)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectionField:
    key: str
    value: ProjectionValue

    def __post_init__(self) -> None:
        try:
            key = require_controlled_key(self.key, "key")
        except VitrineModelValidationError as error:
            raise ProducerProjectionError(
                "projection.invalid_input", "projection", str(error)
            ) from error
        object.__setattr__(self, "key", key)
        value = self.value
        values = value if isinstance(value, tuple) else (value,)
        for item in values:
            if item is not None and not isinstance(item, (str, bool, int, float)):
                raise ProducerProjectionError(
                    "projection.invalid_input",
                    "projection",
                    "ProjectionField values must be JSON scalar values or tuples of scalars.",
                )
            if isinstance(item, float) and not math.isfinite(item):
                raise ProducerProjectionError(
                    "projection.invalid_input",
                    "projection",
                    "ProjectionField numeric values must be finite.",
                )
            if isinstance(item, str):
                try:
                    require_text(item, "ProjectionField string", maximum=1000)
                except VitrineModelValidationError as error:
                    raise ProducerProjectionError(
                        "projection.invalid_input", "projection", str(error)
                    ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectionDisplaySnapshot:
    title: str
    summary: str | None = None
    fields: tuple[ProjectionField, ...] = ()

    def __post_init__(self) -> None:
        try:
            title = require_text(self.title, "title", maximum=300)
            summary = require_optional_text(self.summary, "summary", maximum=1000)
        except VitrineModelValidationError as error:
            raise ProducerProjectionError(
                "projection.invalid_input", "projection", str(error)
            ) from error
        fields = tuple(self.fields)
        if any(not isinstance(item, ProjectionField) for item in fields):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "fields must contain ProjectionField values.",
            )
        if len({item.key for item in fields}) != len(fields):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "display fields must have unique keys.",
            )
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "fields", tuple(sorted(fields, key=lambda item: item.key)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectedProducerRelationship:
    source_subject_kind: str
    source_subject_id: str
    relationship_kind: str
    relationship_authority: str
    supporting_source_reference: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "source_subject_kind",
                require_controlled_key(self.source_subject_kind, "source_subject_kind"),
            )
            object.__setattr__(
                self,
                "source_subject_id",
                require_identifier(self.source_subject_id, "source_subject_id"),
            )
            object.__setattr__(
                self,
                "relationship_kind",
                require_controlled_key(self.relationship_kind, "relationship_kind"),
            )
            object.__setattr__(
                self,
                "relationship_authority",
                require_controlled_key(
                    self.relationship_authority, "relationship_authority"
                ),
            )
            object.__setattr__(
                self,
                "supporting_source_reference",
                require_optional_text(
                    self.supporting_source_reference,
                    "supporting_source_reference",
                    maximum=256,
                ),
            )
        except VitrineModelValidationError as error:
            raise ProducerProjectionError(
                "projection.invalid_input", "projection", str(error)
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectedProducerSource:
    projection_kind: str
    producer_source: ProducerSourceReference
    source_artifact: SourceArtifactReference
    source_relationships: tuple[ProjectedProducerRelationship, ...]
    source_privacy: SourcePrivacyMetadata
    display_snapshot: ProjectionDisplaySnapshot

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "projection_kind",
                require_controlled_key(self.projection_kind, "projection_kind"),
            )
        except VitrineModelValidationError as error:
            raise ProducerProjectionError(
                "projection.invalid_input", "projection", str(error)
            ) from error
        if not isinstance(self.producer_source, ProducerSourceReference):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "producer_source must be ProducerSourceReference.",
            )
        if not isinstance(self.source_artifact, SourceArtifactReference):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "source_artifact must be SourceArtifactReference.",
            )
        relationships = tuple(self.source_relationships)
        if any(not isinstance(item, ProjectedProducerRelationship) for item in relationships):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "source_relationships contains an invalid relationship.",
            )
        if not isinstance(self.source_privacy, SourcePrivacyMetadata):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "source_privacy must be SourcePrivacyMetadata.",
            )
        if not isinstance(self.display_snapshot, ProjectionDisplaySnapshot):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "display_snapshot must be ProjectionDisplaySnapshot.",
            )
        object.__setattr__(
            self,
            "source_relationships",
            tuple(
                sorted(
                    relationships,
                    key=lambda item: (
                        item.relationship_kind,
                        item.source_subject_kind,
                        item.source_subject_id,
                        item.relationship_authority,
                        item.supporting_source_reference or "",
                    ),
                )
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerProjectionBatch:
    adapter_id: str
    adapter_contract_version: str
    reader_id: str
    reader_contract_version: str
    candidate_projection_contract_version: str
    support_key: ProducerAdapterSupportKey
    projected_sources: tuple[ProjectedProducerSource, ...]
    diagnostic_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "adapter_id",
            "adapter_contract_version",
            "reader_id",
            "reader_contract_version",
            "candidate_projection_contract_version",
        ):
            try:
                object.__setattr__(
                    self,
                    field_name,
                    require_identifier(getattr(self, field_name), field_name),
                )
            except VitrineModelValidationError as error:
                raise ProducerProjectionError(
                    "projection.invalid_input", "projection", str(error)
                ) from error
        if not isinstance(self.support_key, ProducerAdapterSupportKey):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "support_key must be ProducerAdapterSupportKey.",
            )
        sources = tuple(self.projected_sources)
        if any(not isinstance(item, ProjectedProducerSource) for item in sources):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "projected_sources contains an invalid source.",
            )
        identities = [
            (
                item.projection_kind,
                item.producer_source.source_record_kind,
                item.producer_source.source_record_id,
                item.producer_source.native_revision,
            )
            for item in sources
        ]
        if len(set(identities)) != len(identities):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "projected source identities must be unique within a batch.",
            )
        codes = tuple(self.diagnostic_codes)
        if any(
            not isinstance(code, str) or _DIAGNOSTIC_CODE.fullmatch(code) is None
            for code in codes
        ):
            raise ProducerProjectionError(
                "projection.invalid_input",
                "projection",
                "diagnostic_codes must be stable dotted identifiers.",
            )
        object.__setattr__(
            self,
            "projected_sources",
            tuple(
                sorted(
                    sources,
                    key=lambda item: (
                        item.projection_kind,
                        item.producer_source.source_record_kind,
                        item.producer_source.source_record_id,
                        str(item.producer_source.native_revision or ""),
                    ),
                )
            ),
        )
        object.__setattr__(self, "diagnostic_codes", tuple(sorted(set(codes))))


class ProducerManifestReader(Protocol):
    @property
    def descriptor(self) -> ProducerReaderDescriptor: ...

    def read(self, value: bytes) -> object: ...


class ProducerProjectionAdapter(Protocol):
    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration: ...

    @property
    def reader(self) -> ProducerManifestReader: ...

    def project(self, public_model: object) -> ProducerProjectionBatch: ...


def _validate_adapter_binding(adapter: ProducerProjectionAdapter) -> None:
    declaration = adapter.declaration
    if not isinstance(declaration, ProducerProjectionAdapterDeclaration):
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter declaration has the wrong type.",
        )
    reader = adapter.reader.descriptor
    if not isinstance(reader, ProducerReaderDescriptor):
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter reader descriptor has the wrong type.",
            adapter_id=declaration.adapter_id,
        )
    if declaration.public_reader_id != reader.public_reader_id:
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter declaration public_reader_id does not match its reader.",
            adapter_id=declaration.adapter_id,
        )
    if declaration.reader_contract_version != reader.reader_contract_version:
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter declaration reader_contract_version does not match its reader.",
            adapter_id=declaration.adapter_id,
        )
    if declaration.reader_package_identity != reader.package_identity:
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter declaration reader package identity does not match its reader.",
            adapter_id=declaration.adapter_id,
        )
    if declaration.integration_kind != reader.integration_kind:
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "Adapter and reader integration kinds must agree.",
            adapter_id=declaration.adapter_id,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerProjectionAdapterRegistry:
    adapters: tuple[ProducerProjectionAdapter, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.adapters, (str, bytes, Mapping)):
            raise ProducerAdapterError(
                "adapter.invalid_declaration",
                "registry",
                "adapters must be an iterable of adapter values.",
            )
        try:
            raw = tuple(self.adapters)
        except TypeError as error:
            raise ProducerAdapterError(
                "adapter.invalid_declaration",
                "registry",
                "adapters must be iterable.",
            ) from error
        seen: set[tuple[str, str]] = set()
        for adapter in raw:
            try:
                declaration = adapter.declaration
                _validate_adapter_binding(adapter)
            except AttributeError as error:
                raise ProducerAdapterError(
                    "adapter.invalid_declaration",
                    "registry",
                    "Registry contains a value that does not implement the adapter contract.",
                ) from error
            if declaration.identity in seen:
                raise ProducerAdapterError(
                    "adapter.duplicate_identity",
                    "registry",
                    "Registry contains a duplicate adapter identity.",
                    adapter_id=declaration.adapter_id,
                )
            seen.add(declaration.identity)
        object.__setattr__(
            self,
            "adapters",
            tuple(sorted(raw, key=lambda item: item.declaration.identity)),
        )

    def select_adapter(
        self, request: ProducerAdapterSupportRequest
    ) -> ProducerProjectionAdapter:
        if not isinstance(request, ProducerAdapterSupportRequest):
            raise ProducerAdapterError(
                "adapter.invalid_support_request",
                "selection",
                "request must be ProducerAdapterSupportRequest.",
            )
        matches = tuple(
            adapter
            for adapter in self.adapters
            if adapter.declaration.support_key.matches(request)
        )
        if not matches:
            raise ProducerAdapterUnsupportedError(
                "adapter.unsupported_contract",
                "selection",
                "No exact Vitrine producer adapter supports this contract.",
                producer_module_id=request.producer_module_id,
                publication_kind=request.publication_kind,
                manifest_contract_version=request.manifest_contract_version,
                diagnostic_fields=request.safe_diagnostic_fields,
            )
        if len(matches) > 1:
            identities = tuple(
                f"{adapter.declaration.adapter_id}@{adapter.declaration.adapter_contract_version}"
                for adapter in matches
            )
            raise ProducerAdapterConflictError(
                "adapter.conflict",
                "selection",
                "Multiple Vitrine producer adapters match this exact contract.",
                producer_module_id=request.producer_module_id,
                publication_kind=request.publication_kind,
                manifest_contract_version=request.manifest_contract_version,
                diagnostic_fields=(
                    *request.safe_diagnostic_fields,
                    ("matching_adapters", ",".join(identities)),
                ),
            )
        return matches[0]


def build_adapter_registry(
    *, adapters: Iterable[ProducerProjectionAdapter] = ()
) -> ProducerProjectionAdapterRegistry:
    """Build the ordinary runtime registry without installed-package discovery.

    Explicit development-fixture adapters are rejected here. Tests and developer
    tools must opt into ``build_development_fixture_adapter_registry`` instead.
    """

    try:
        raw = tuple(adapters)
    except TypeError as error:
        raise ProducerAdapterError(
            "adapter.invalid_declaration",
            "registry",
            "adapters must be iterable.",
        ) from error
    registry = ProducerProjectionAdapterRegistry(adapters=raw)
    fixture = next(
        (
            adapter
            for adapter in registry.adapters
            if adapter.declaration.integration_kind == "development_fixture"
        ),
        None,
    )
    if fixture is not None:
        raise ProducerAdapterError(
            "adapter.fixture_not_enabled",
            "registry",
            "Development fixture adapters require the explicit fixture registry.",
            adapter_id=fixture.declaration.adapter_id,
        )
    return registry


__all__ = [
    "ADAPTER_FAILURE_CODES",
    "INTEGRATION_KINDS",
    "ProducerAdapterConflictError",
    "ProducerAdapterError",
    "ProducerAdapterSupportKey",
    "ProducerAdapterSupportRequest",
    "ProducerAdapterUnsupportedError",
    "ProducerManifestReader",
    "ProducerProjectionAdapter",
    "ProducerProjectionAdapterDeclaration",
    "ProducerProjectionAdapterRegistry",
    "ProducerProjectionBatch",
    "ProducerProjectionError",
    "ProducerReaderDescriptor",
    "ProducerReaderError",
    "ProjectedProducerRelationship",
    "ProjectedProducerSource",
    "ProjectionDisplaySnapshot",
    "ProjectionField",
    "build_adapter_registry",
]
