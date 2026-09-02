"""Authorization-gated Concord Artifact bytes for Vitrine Snapshot sources.

Issue #61 keeps Concord Artifact I/O behind the producer-owned public API.
This module does not inspect Concord native storage, resolve current producer
state, reconstruct native paths, or treat Snapshot build authority as Artifact
authorization.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Final, Protocol, cast

from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
    CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
)
from vitrine.models import DigestReference
from vitrine.models.common import (
    lower_key_tuple,
    require_enum,
    require_identifier,
    require_optional_text,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SnapshotAuthorizedSourceBytesResult,
    SnapshotMaterializationError,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)

CONCORD_ARTIFACT_SOURCE_PROVIDER_ID: Final[str] = (
    "vitrine_concord_returned_artifact_source_provider"
)
CONCORD_ARTIFACT_SOURCE_PROVIDER_VERSION: Final[str] = (
    "vitrine_concord_returned_artifact_source_provider_v1"
)
CONCORD_ARTIFACT_SNAPSHOT_PURPOSE: Final[str] = "build_snapshot"
CONCORD_ARTIFACT_AUTHORIZATION_OPERATION: Final[str] = "read_concord_artifact"
CONCORD_ARTIFACT_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
CONCORD_ARTIFACT_MEDIA_TYPE: Final[str] = "application/pdf"

CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR: Final[
    SnapshotSourceProviderDescriptor
] = SnapshotSourceProviderDescriptor(
    provider_id=CONCORD_ARTIFACT_SOURCE_PROVIDER_ID,
    provider_version=CONCORD_ARTIFACT_SOURCE_PROVIDER_VERSION,
    producer_module_id="concord",
    projection_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
    projection_contract_version=CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
    artifact_kind="collaborative_artifact",
    representation_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
)


def _invalid_request(message: str, *, stage: str) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(
        "snapshot.invalid_request",
        message,
        stage=stage,
    )


def _source_unavailable(message: str, *, stage: str) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(
        "snapshot.source_unavailable",
        message,
        stage=stage,
    )


def _source_integrity(message: str, *, stage: str) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(
        "snapshot.source_integrity_failed",
        message,
        stage=stage,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConcordArtifactAuthorizationRequest:
    """Bounded Vitrine request presented to deployment-owned Artifact policy."""

    operation: str
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    source_publication_id: str
    source_artifact_id: str
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_kind: str
    evidence_record_id: str
    purpose: str

    def __post_init__(self) -> None:
        try:
            if self.operation != CONCORD_ARTIFACT_AUTHORIZATION_OPERATION:
                raise VitrineModelValidationError(
                    "operation must identify Concord Artifact reading."
                )
            for name in (
                "snapshot_build_plan_id",
                "snapshot_build_attempt_id",
                "source_publication_id",
                "source_artifact_id",
                "score_record_id",
                "score_evidence_link_id",
                "evidence_record_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            if (
                isinstance(self.source_snapshot_revision, bool)
                or not isinstance(self.source_snapshot_revision, int)
                or self.source_snapshot_revision < 1
            ):
                raise VitrineModelValidationError(
                    "source_snapshot_revision must be a positive integer."
                )
            object.__setattr__(
                self,
                "evidence_kind",
                require_enum(
                    self.evidence_kind,
                    "evidence_kind",
                    frozenset({"artifact_instance", "artifact_page"}),
                ),
            )
            object.__setattr__(
                self,
                "purpose",
                require_text(self.purpose, "purpose", maximum=256),
            )
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Concord Artifact authorization request is invalid.",
                stage="concord_artifact_authorization_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ConcordArtifactAuthorizationDecision:
    """Deployment-owned decision, independent of Snapshot build authority."""

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
                    CONCORD_ARTIFACT_AUTHORIZATION_OUTCOMES,
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
            raise _invalid_request(
                "Concord Artifact authorization decision is invalid.",
                stage="concord_artifact_authorization",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise _invalid_request(
                "Allowed Concord Artifact authorization requires an authority reference.",
                stage="concord_artifact_authorization",
            )


class ConcordArtifactAuthorizationGate(Protocol):
    def authorize(
        self, request: ConcordArtifactAuthorizationRequest
    ) -> ConcordArtifactAuthorizationDecision: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ConcordArtifactSourceContext:
    """Canonical source context resolved before producer Artifact acquisition.

    The resolver owns Vitrine/Core revalidation. Merely holding this context is
    not Artifact authorization. The workspace root is treated as opaque producer
    context here; this module performs no filesystem probe before Concord's gate.
    """

    workspace_root: Path
    manifest: object
    source_publication_id: str
    score_evidence_link_id: str

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.workspace_root, Path):
                raise VitrineModelValidationError(
                    "workspace_root must be pathlib.Path."
                )
            if not self.workspace_root.is_absolute():
                raise VitrineModelValidationError(
                    "workspace_root must be an absolute path."
                )
            object.__setattr__(
                self,
                "source_publication_id",
                require_identifier(
                    self.source_publication_id, "source_publication_id"
                ),
            )
            object.__setattr__(
                self,
                "score_evidence_link_id",
                require_identifier(
                    self.score_evidence_link_id, "score_evidence_link_id"
                ),
            )
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Concord Artifact source context is invalid.",
                stage="concord_artifact_context",
            ) from error


class ConcordArtifactSourceContextResolver(Protocol):
    """Resolve exact Vitrine/Core provenance, without producer Artifact I/O."""

    def resolve(
        self, request: SnapshotSourceRequest
    ) -> ConcordArtifactSourceContext: ...


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _ManifestProjection(Protocol):
    source_snapshot_revision: int


class _Manifest(Protocol):
    work: object
    record_set: _RecordSet
    projection: _ManifestProjection


class _EvidenceReference(Protocol):
    evidence_kind: str
    owning_system: str
    record_id: str


class _ProducerAuthorizationRequest(Protocol):
    work: object
    record_set_id: str
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _EvidenceReference
    purpose: str


class _ArtifactPage(Protocol):
    artifact_page_id: str


class _ArtifactProjection(Protocol):
    artifact_instance_id: str
    pages: tuple[_ArtifactPage, ...]


class _AuthorizedArtifact(Protocol):
    representation: str
    work: object
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _EvidenceReference
    artifact: _ArtifactProjection
    media_type: str
    sha256: str
    byte_size: int
    content: bytes


@dataclass(frozen=True, slots=True)
class _ConcordArtifactApi:
    decision_factory: Callable[..., object]
    result_type: type[object]
    read: Callable[..., object]
    authorization_error: type[BaseException]
    validation_error: type[BaseException]
    not_found_error: type[BaseException]
    unavailable_error: type[BaseException]
    ambiguity_error: type[BaseException]
    integrity_error: type[BaseException]


def _exception_type(value: object, symbol: str) -> type[BaseException]:
    if (
        not isinstance(value, type)
        or not issubclass(value, BaseException)
    ):
        raise _source_unavailable(
            "Installed Concord Artifact API has an incompatible exception surface.",
            stage="concord_artifact_contract",
        )
    return value


def _load_concord_artifact_api() -> _ConcordArtifactApi:
    try:
        module = import_module("concord.academic_result_artifacts")
    except Exception as error:
        raise _source_unavailable(
            "Installed Concord Artifact API is unavailable.",
            stage="concord_artifact_contract",
        ) from error

    decision_type = getattr(
        module, "AcademicResultArtifactAuthorizationDecision", None
    )
    result_type = getattr(module, "AuthorizedAcademicResultArtifact", None)
    read = getattr(module, "read_authorized_academic_result_artifact", None)
    if not isinstance(decision_type, type) or not isinstance(result_type, type):
        raise _source_unavailable(
            "Installed Concord Artifact API has an incompatible model surface.",
            stage="concord_artifact_contract",
        )
    if not callable(read):
        raise _source_unavailable(
            "Installed Concord Artifact API has no compatible read operation.",
            stage="concord_artifact_contract",
        )

    return _ConcordArtifactApi(
        decision_factory=cast(Callable[..., object], decision_type),
        result_type=result_type,
        read=cast(Callable[..., object], read),
        authorization_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactAuthorizationError",
                None,
            ),
            "ConcordAcademicResultArtifactAuthorizationError",
        ),
        validation_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactValidationError",
                None,
            ),
            "ConcordAcademicResultArtifactValidationError",
        ),
        not_found_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactNotFoundError",
                None,
            ),
            "ConcordAcademicResultArtifactNotFoundError",
        ),
        unavailable_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactUnavailableError",
                None,
            ),
            "ConcordAcademicResultArtifactUnavailableError",
        ),
        ambiguity_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactAmbiguityError",
                None,
            ),
            "ConcordAcademicResultArtifactAmbiguityError",
        ),
        integrity_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactIntegrityError",
                None,
            ),
            "ConcordAcademicResultArtifactIntegrityError",
        ),
    )


class _ConcordAuthorizationBridge:
    """Translate one producer request to deployment-owned Vitrine policy."""

    def __init__(
        self,
        *,
        snapshot_request: SnapshotSourceRequest,
        context: ConcordArtifactSourceContext,
        authorization_gate: ConcordArtifactAuthorizationGate,
        decision_factory: Callable[..., object],
        purpose: str,
    ) -> None:
        self._snapshot_request = snapshot_request
        self._context = context
        self._authorization_gate = authorization_gate
        self._decision_factory = decision_factory
        self._purpose = purpose
        self.last_outcome: str | None = None
        self.gate_failed = False
        self.integrity_mismatch = False
        self.producer_request: _ProducerAuthorizationRequest | None = None

    def _decision(self, status: str) -> object:
        try:
            return self._decision_factory(status=status)
        except Exception as error:
            raise _source_unavailable(
                "Installed Concord Artifact authorization model is incompatible.",
                stage="concord_artifact_contract",
            ) from error

    def authorize(self, value: object) -> object:
        entry = self._snapshot_request.entry_plan
        artifact = entry.source_artifact
        assert artifact is not None
        try:
            producer_request = cast(_ProducerAuthorizationRequest, value)
            evidence = producer_request.evidence_reference
            manifest = cast(_Manifest, self._context.manifest)
            mismatch = (
                producer_request.work != manifest.work
                or producer_request.record_set_id != manifest.record_set.record_set_id
                or producer_request.record_set_revision != manifest.record_set.revision
                or producer_request.source_snapshot_revision
                != manifest.projection.source_snapshot_revision
                or producer_request.source_snapshot_revision != artifact.native_revision
                or producer_request.score_evidence_link_id
                != self._context.score_evidence_link_id
                or evidence.owning_system != "concord"
                or evidence.evidence_kind
                not in {"artifact_instance", "artifact_page"}
                or evidence.record_id != artifact.artifact_id
                or producer_request.purpose != self._purpose
            )
        except Exception:
            mismatch = True
            producer_request = None

        if mismatch or producer_request is None:
            self.integrity_mismatch = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")

        self.producer_request = producer_request
        evidence = producer_request.evidence_reference
        request = ConcordArtifactAuthorizationRequest(
            operation=CONCORD_ARTIFACT_AUTHORIZATION_OPERATION,
            snapshot_build_plan_id=self._snapshot_request.snapshot_build_plan_id,
            snapshot_build_attempt_id=(
                self._snapshot_request.snapshot_build_attempt_id
            ),
            source_publication_id=self._context.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            source_snapshot_revision=producer_request.source_snapshot_revision,
            score_record_id=producer_request.score_record_id,
            score_evidence_link_id=producer_request.score_evidence_link_id,
            evidence_kind=evidence.evidence_kind,
            evidence_record_id=evidence.record_id,
            purpose=self._purpose,
        )
        try:
            decision = self._authorization_gate.authorize(request)
        except Exception:
            self.gate_failed = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        if not isinstance(decision, ConcordArtifactAuthorizationDecision):
            self.gate_failed = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        self.last_outcome = decision.outcome
        return self._decision(decision.outcome)


def _validate_context(
    request: SnapshotSourceRequest,
    context: ConcordArtifactSourceContext,
) -> None:
    entry = request.entry_plan
    artifact = entry.source_artifact
    if artifact is None:
        raise _invalid_request(
            "Concord Artifact source requires an exact planned source Artifact.",
            stage="concord_artifact_context",
        )
    if (
        entry.producer_module_id
        != CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.producer_module_id
        or entry.projection_kind
        != CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.projection_kind
        or entry.projection_contract_version
        != CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.projection_contract_version
        or artifact.artifact_kind
        != CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.artifact_kind
        or artifact.representation_kind
        != CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.representation_kind
        or artifact.media_type != CONCORD_ARTIFACT_MEDIA_TYPE
        or artifact.source_locator is not None
        or artifact.source_digest is not None
        or artifact.byte_size is not None
        or not isinstance(artifact.native_revision, int)
        or artifact.native_revision < 1
    ):
        raise _source_integrity(
            "Planned Concord Artifact source contract is inconsistent.",
            stage="concord_artifact_context",
        )
    if (
        entry.source_publication_id is None
        or context.source_publication_id != entry.source_publication_id
    ):
        raise _source_integrity(
            "Concord Artifact source Publication does not match the immutable Entry Plan.",
            stage="concord_artifact_context",
        )
    manifest = cast(_Manifest, context.manifest)
    try:
        if (
            manifest.record_set.revision < 1
            or manifest.projection.source_snapshot_revision
            != artifact.native_revision
        ):
            raise ValueError
    except Exception as error:
        raise _source_integrity(
            "Concord Artifact source context does not match projected history.",
            stage="concord_artifact_context",
        ) from error


def _verify_authorized_result(
    *,
    result: object,
    api: _ConcordArtifactApi,
    bridge: _ConcordAuthorizationBridge,
    request: SnapshotSourceRequest,
    context: ConcordArtifactSourceContext,
) -> _AuthorizedArtifact:
    if not isinstance(result, api.result_type):
        raise _source_integrity(
            "Concord Artifact API returned an incompatible result.",
            stage="concord_artifact_result",
        )
    producer_request = bridge.producer_request
    if producer_request is None:
        raise _source_integrity(
            "Concord Artifact result has no affirmed producer request.",
            stage="concord_artifact_result",
        )
    authorized = cast(_AuthorizedArtifact, result)
    entry = request.entry_plan
    artifact = entry.source_artifact
    assert artifact is not None
    evidence = authorized.evidence_reference

    try:
        identity_mismatch = (
            authorized.representation != "returned_artifact_pdf"
            or authorized.work != producer_request.work
            or authorized.record_set_revision
            != producer_request.record_set_revision
            or authorized.source_snapshot_revision
            != producer_request.source_snapshot_revision
            or authorized.source_snapshot_revision != artifact.native_revision
            or authorized.score_record_id != producer_request.score_record_id
            or authorized.score_evidence_link_id
            != producer_request.score_evidence_link_id
            or authorized.score_evidence_link_id
            != context.score_evidence_link_id
            or evidence != producer_request.evidence_reference
            or evidence.owning_system != "concord"
            or evidence.evidence_kind
            not in {"artifact_instance", "artifact_page"}
            or evidence.record_id != artifact.artifact_id
            or authorized.media_type != CONCORD_ARTIFACT_MEDIA_TYPE
        )
        if evidence.evidence_kind == "artifact_instance":
            identity_mismatch = (
                identity_mismatch
                or authorized.artifact.artifact_instance_id != artifact.artifact_id
            )
        else:
            page_ids = tuple(
                page.artifact_page_id for page in authorized.artifact.pages
            )
            identity_mismatch = (
                identity_mismatch or artifact.artifact_id not in page_ids
            )
        if type(authorized.content) is not bytes:
            identity_mismatch = True
        if not authorized.content.startswith(b"%PDF"):
            identity_mismatch = True
        if (
            isinstance(authorized.byte_size, bool)
            or not isinstance(authorized.byte_size, int)
            or authorized.byte_size != len(authorized.content)
        ):
            identity_mismatch = True
        expected_sha256 = hashlib.sha256(authorized.content).hexdigest()
        if authorized.sha256 != expected_sha256:
            identity_mismatch = True
    except Exception:
        identity_mismatch = True

    if identity_mismatch:
        raise _source_integrity(
            "Concord Artifact result does not match the exact planned source.",
            stage="concord_artifact_result",
        )
    return authorized


class ConcordReturnedArtifactSourceProvider:
    """Resolve one exact selected Concord Artifact through producer authorization."""

    descriptor: Final[SnapshotSourceProviderDescriptor] = (
        CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR
    )

    def __init__(
        self,
        *,
        context_resolver: ConcordArtifactSourceContextResolver,
        authorization_gate: ConcordArtifactAuthorizationGate,
        purpose: str = CONCORD_ARTIFACT_SNAPSHOT_PURPOSE,
    ) -> None:
        try:
            self._purpose = require_text(purpose, "purpose", maximum=256)
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Concord Artifact Snapshot purpose is invalid.",
                stage="concord_artifact_provider",
            ) from error
        self._context_resolver = context_resolver
        self._authorization_gate = authorization_gate

    def resolve(
        self, request: SnapshotSourceRequest
    ) -> SnapshotAuthorizedSourceBytesResult:
        try:
            context = self._context_resolver.resolve(request)
        except SnapshotMaterializationError:
            raise
        except Exception as error:
            raise _source_unavailable(
                "Concord Artifact source context could not be resolved.",
                stage="concord_artifact_context",
            ) from error
        if not isinstance(context, ConcordArtifactSourceContext):
            raise _source_integrity(
                "Concord Artifact source resolver returned an invalid context.",
                stage="concord_artifact_context",
            )
        _validate_context(request, context)

        # Concord is imported only after Vitrine/Core source context is fixed.
        # The producer API itself invokes its authorization gate before native I/O.
        api = _load_concord_artifact_api()
        bridge = _ConcordAuthorizationBridge(
            snapshot_request=request,
            context=context,
            authorization_gate=self._authorization_gate,
            decision_factory=api.decision_factory,
            purpose=self._purpose,
        )
        try:
            result = api.read(
                context.workspace_root,
                context.manifest,
                context.score_evidence_link_id,
                purpose=self._purpose,
                authorization_gate=bridge,
            )
        except api.authorization_error as error:
            if bridge.integrity_mismatch:
                raise _source_integrity(
                    "Concord Artifact authorization request disagreed with planned provenance.",
                    stage="concord_artifact_authorization",
                ) from error
            if bridge.last_outcome == "denied":
                raise _source_unavailable(
                    "Concord Artifact authorization was denied.",
                    stage="concord_artifact_authorization_denied",
                ) from error
            raise _source_unavailable(
                "Concord Artifact authorization was unresolved.",
                stage="concord_artifact_authorization_unresolved",
            ) from error
        except api.integrity_error as error:
            raise _source_integrity(
                "Concord Artifact historical or byte integrity verification failed.",
                stage="concord_artifact_read",
            ) from error
        except api.validation_error as error:
            raise _source_integrity(
                "Concord Artifact request failed producer validation.",
                stage="concord_artifact_read",
            ) from error
        except (
            api.not_found_error,
            api.unavailable_error,
            api.ambiguity_error,
        ) as error:
            raise _source_unavailable(
                "Concord Artifact source is unavailable.",
                stage="concord_artifact_read",
            ) from error
        except SnapshotMaterializationError:
            raise
        except Exception as error:
            raise _source_unavailable(
                "Concord Artifact source could not be acquired.",
                stage="concord_artifact_read",
            ) from error

        authorized = _verify_authorized_result(
            result=result,
            api=api,
            bridge=bridge,
            request=request,
            context=context,
        )
        entry = request.entry_plan
        artifact = entry.source_artifact
        assert artifact is not None
        return SnapshotAuthorizedSourceBytesResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=context.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            content=authorized.content,
            media_type=authorized.media_type,
            source_digest=DigestReference(value=authorized.sha256),
            byte_size=authorized.byte_size,
            acquisition_contract_version=SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
        )

    def confirm_stability(
        self,
        request: SnapshotSourceRequest,
        result: SnapshotSourceResult,
    ) -> bool:
        raise _invalid_request(
            "Producer-authorized immutable Concord bytes do not use filesystem stability.",
            stage="concord_artifact_stability",
        )


def build_concord_artifact_source_provider(
    *,
    context_resolver: ConcordArtifactSourceContextResolver,
    authorization_gate: ConcordArtifactAuthorizationGate,
    purpose: str = CONCORD_ARTIFACT_SNAPSHOT_PURPOSE,
) -> ConcordReturnedArtifactSourceProvider:
    """Build the Concord provider without importing or discovering Concord."""

    return ConcordReturnedArtifactSourceProvider(
        context_resolver=context_resolver,
        authorization_gate=authorization_gate,
        purpose=purpose,
    )


__all__ = [
    "CONCORD_ARTIFACT_AUTHORIZATION_OPERATION",
    "CONCORD_ARTIFACT_AUTHORIZATION_OUTCOMES",
    "CONCORD_ARTIFACT_MEDIA_TYPE",
    "CONCORD_ARTIFACT_SNAPSHOT_PURPOSE",
    "CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR",
    "CONCORD_ARTIFACT_SOURCE_PROVIDER_ID",
    "CONCORD_ARTIFACT_SOURCE_PROVIDER_VERSION",
    "ConcordArtifactAuthorizationDecision",
    "ConcordArtifactAuthorizationGate",
    "ConcordArtifactAuthorizationRequest",
    "ConcordArtifactSourceContext",
    "ConcordArtifactSourceContextResolver",
    "ConcordReturnedArtifactSourceProvider",
    "build_concord_artifact_source_provider",
]
