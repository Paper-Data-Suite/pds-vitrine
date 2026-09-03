"""Authorization-gated Quillan Artifact bytes for Vitrine Snapshot sources.

Issue #60 Slice 3 keeps every Quillan Artifact read behind the released public
``quillan.academic_result_artifacts`` API. Vitrine validates immutable source-plan
and publication context, bridges deployment-owned authorization to the producer
request, verifies the returned public result, and returns immutable Snapshot
source bytes without reopening producer paths.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Final, Protocol, cast

from vitrine.models import DigestReference
from vitrine.models.common import (
    lower_key_tuple,
    require_enum,
    require_identifier,
    require_optional_text,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.quillan_contract import (
    QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID,
    QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION,
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
    QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT,
    SnapshotAuthorizedSourceBytesResult,
    SnapshotMaterializationError,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)

QUILLAN_ARTIFACT_SNAPSHOT_PURPOSE: Final[str] = "build_snapshot"
QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION: Final[str] = "read_quillan_artifact"
QUILLAN_ARTIFACT_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
QUILLAN_ARTIFACT_REQUEST_KINDS: Final[frozenset[str]] = frozenset(
    {"student_work", "feedback_pdf", "feedback_markdown"}
)

QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_ID: Final[str] = (
    f"{QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID}_student_work"
)
QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_ID: Final[str] = (
    f"{QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID}_feedback_pdf"
)
QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_ID: Final[str] = (
    f"{QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID}_feedback_markdown"
)

QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR: Final[
    SnapshotSourceProviderDescriptor
] = SnapshotSourceProviderDescriptor(
    provider_id=QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_ID,
    provider_version=QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION,
    producer_module_id="quillan",
    projection_kind=QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    artifact_kind=QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
    representation_kind=QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    concrete_media_types=QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
)
QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR: Final[
    SnapshotSourceProviderDescriptor
] = SnapshotSourceProviderDescriptor(
    provider_id=QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_ID,
    provider_version=QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION,
    producer_module_id="quillan",
    projection_kind=QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    artifact_kind=QUILLAN_FEEDBACK_ARTIFACT_KIND,
    representation_kind=QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
)
QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR: Final[
    SnapshotSourceProviderDescriptor
] = SnapshotSourceProviderDescriptor(
    provider_id=QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_ID,
    provider_version=QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION,
    producer_module_id="quillan",
    projection_kind=QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    artifact_kind=QUILLAN_FEEDBACK_ARTIFACT_KIND,
    representation_kind=QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
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
class QuillanArtifactAuthorizationRequest:
    """Exact deployment-owned decision input for one planned Quillan source."""

    operation: str
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    source_publication_id: str
    source_artifact_id: str
    student_id: str
    artifact_kind: str
    evidence_id: str | None
    purpose: str

    def __post_init__(self) -> None:
        try:
            if self.operation != QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION:
                raise VitrineModelValidationError(
                    "operation must identify Quillan Artifact reading."
                )
            for name in (
                "snapshot_build_plan_id",
                "snapshot_build_attempt_id",
                "source_publication_id",
                "source_artifact_id",
                "student_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            object.__setattr__(
                self,
                "artifact_kind",
                require_enum(
                    self.artifact_kind,
                    "artifact_kind",
                    QUILLAN_ARTIFACT_REQUEST_KINDS,
                ),
            )
            if self.evidence_id is not None:
                object.__setattr__(
                    self,
                    "evidence_id",
                    require_text(self.evidence_id, "evidence_id", maximum=500),
                )
            object.__setattr__(
                self,
                "purpose",
                require_text(self.purpose, "purpose", maximum=256),
            )
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Quillan Artifact authorization request is invalid.",
                stage="quillan_artifact_authorization_request",
            ) from error
        if (self.artifact_kind == "student_work") != (self.evidence_id is not None):
            raise _invalid_request(
                "Quillan student-work authorization requires exactly one evidence identity.",
                stage="quillan_artifact_authorization_request",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class QuillanArtifactAuthorizationDecision:
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
                    QUILLAN_ARTIFACT_AUTHORIZATION_OUTCOMES,
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
                "Quillan Artifact authorization decision is invalid.",
                stage="quillan_artifact_authorization",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise _invalid_request(
                "Allowed Quillan Artifact authorization requires an authority reference.",
                stage="quillan_artifact_authorization",
            )


class QuillanArtifactAuthorizationGate(Protocol):
    def authorize(
        self, request: QuillanArtifactAuthorizationRequest
    ) -> QuillanArtifactAuthorizationDecision: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class QuillanArtifactSourceContext:
    """Revalidated Vitrine/Core context for one exact Quillan Artifact capability.

    ``workspace_root`` remains opaque to Vitrine. This module never probes it.
    Quillan receives it only after the immutable Entry Plan has been checked; the
    producer API performs its own authorization before native workspace I/O.
    """

    workspace_root: Path
    manifest: object
    source_publication_id: str
    student_id: str
    artifact_request_kind: str
    evidence_id: str | None = None

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
                "student_id",
                require_identifier(self.student_id, "student_id"),
            )
            object.__setattr__(
                self,
                "artifact_request_kind",
                require_enum(
                    self.artifact_request_kind,
                    "artifact_request_kind",
                    QUILLAN_ARTIFACT_REQUEST_KINDS,
                ),
            )
            if self.evidence_id is not None:
                object.__setattr__(
                    self,
                    "evidence_id",
                    require_text(self.evidence_id, "evidence_id", maximum=500),
                )
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Quillan Artifact source context is invalid.",
                stage="quillan_artifact_context",
            ) from error
        if (self.artifact_request_kind == "student_work") != (
            self.evidence_id is not None
        ):
            raise _invalid_request(
                "Quillan student-work context requires exactly one evidence identity.",
                stage="quillan_artifact_context",
            )


class QuillanArtifactSourceContextResolver(Protocol):
    """Resolve exact Vitrine/Core provenance without producer Artifact I/O."""

    def resolve(self, request: SnapshotSourceRequest) -> QuillanArtifactSourceContext: ...


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _Work(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _EvidenceReference(Protocol):
    evidence_id: str
    routed_evidence_sha256: str


class _DigitalProvenance(Protocol):
    evidence_references: tuple[_EvidenceReference, ...]


class _Submission(Protocol):
    entry_method: str
    digital_provenance: _DigitalProvenance | None


class _StudentResult(Protocol):
    student_id: str
    submission: _Submission


class _Manifest(Protocol):
    record_set: _RecordSet
    work: _Work
    students: tuple[_StudentResult, ...]


class _ProducerAuthorizationRequest(Protocol):
    work: object
    record_set_id: str
    record_set_revision: int
    student_id: str
    artifact_kind: str
    purpose: str


class _AuthorizedArtifact(Protocol):
    artifact_kind: str
    work: object
    record_set_revision: int
    student_id: str
    relative_path: str
    media_type: str
    sha256: str
    byte_size: int
    data: bytes
    evidence_reference: _EvidenceReference | None


@dataclass(frozen=True, slots=True)
class _QuillanArtifactApi:
    decision_factory: Callable[..., object]
    result_type: type[object]
    read: Callable[..., object]
    authorization_error: type[BaseException]
    validation_error: type[BaseException]
    unavailable_error: type[BaseException]
    integrity_error: type[BaseException]
    read_error: type[BaseException]


def _exception_type(value: object) -> type[BaseException]:
    if not isinstance(value, type) or not issubclass(value, BaseException):
        raise _source_unavailable(
            "Installed Quillan Artifact API has an incompatible exception surface.",
            stage="quillan_artifact_contract",
        )
    return value


def _load_quillan_artifact_api() -> _QuillanArtifactApi:
    try:
        module = import_module("quillan.academic_result_artifacts")
    except Exception as error:
        raise _source_unavailable(
            "Installed Quillan Artifact API is unavailable.",
            stage="quillan_artifact_contract",
        ) from error

    decision_type = getattr(
        module, "AcademicResultArtifactAuthorizationDecision", None
    )
    result_type = getattr(module, "AuthorizedAcademicResultArtifact", None)
    read = getattr(module, "read_authorized_academic_result_artifacts", None)
    if not isinstance(decision_type, type) or not isinstance(result_type, type):
        raise _source_unavailable(
            "Installed Quillan Artifact API has an incompatible model surface.",
            stage="quillan_artifact_contract",
        )
    if not callable(read):
        raise _source_unavailable(
            "Installed Quillan Artifact API has no compatible read operation.",
            stage="quillan_artifact_contract",
        )

    return _QuillanArtifactApi(
        decision_factory=cast(Callable[..., object], decision_type),
        result_type=result_type,
        read=cast(Callable[..., object], read),
        authorization_error=_exception_type(
            getattr(
                module,
                "QuillanAcademicResultArtifactAuthorizationError",
                None,
            )
        ),
        validation_error=_exception_type(
            getattr(
                module,
                "QuillanAcademicResultArtifactValidationError",
                None,
            )
        ),
        unavailable_error=_exception_type(
            getattr(
                module,
                "QuillanAcademicResultArtifactUnavailableError",
                None,
            )
        ),
        integrity_error=_exception_type(
            getattr(
                module,
                "QuillanAcademicResultArtifactIntegrityError",
                None,
            )
        ),
        read_error=_exception_type(
            getattr(
                module,
                "QuillanAcademicResultArtifactReadError",
                None,
            )
        ),
    )


def _student(manifest: _Manifest, student_id: str) -> _StudentResult:
    matches = tuple(item for item in manifest.students if item.student_id == student_id)
    if len(matches) != 1:
        raise _source_integrity(
            "Quillan Artifact context does not resolve one represented student.",
            stage="quillan_artifact_context",
        )
    return matches[0]


def _selected_reference(
    manifest: _Manifest, *, student_id: str, evidence_id: str
) -> _EvidenceReference:
    student = _student(manifest, student_id)
    provenance = student.submission.digital_provenance
    if student.submission.entry_method != "pds2_response_pages" or provenance is None:
        raise _source_integrity(
            "Planned Quillan student work is not represented digital evidence.",
            stage="quillan_artifact_context",
        )
    matches = tuple(
        item for item in provenance.evidence_references if item.evidence_id == evidence_id
    )
    if len(matches) != 1:
        raise _source_integrity(
            "Planned Quillan student work does not resolve one selected evidence reference.",
            stage="quillan_artifact_context",
        )
    return matches[0]


def _request_spec(
    artifact_request_kind: str,
) -> tuple[SnapshotSourceProviderDescriptor, str, str, str]:
    if artifact_request_kind == "student_work":
        return (
            QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
            QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
            QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
            QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
        )
    if artifact_request_kind == "feedback_pdf":
        return (
            QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
            QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
            QUILLAN_FEEDBACK_ARTIFACT_KIND,
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
        )
    if artifact_request_kind == "feedback_markdown":
        return (
            QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
            QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
            QUILLAN_FEEDBACK_ARTIFACT_KIND,
            QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
        )
    raise _invalid_request(
        "Quillan Artifact request kind is unsupported.",
        stage="quillan_artifact_provider",
    )


def _validate_context(
    request: SnapshotSourceRequest,
    context: QuillanArtifactSourceContext,
    descriptor: SnapshotSourceProviderDescriptor,
) -> _EvidenceReference | None:
    entry = request.entry_plan
    artifact = entry.source_artifact
    if artifact is None:
        raise _invalid_request(
            "Quillan Artifact source requires an exact planned source Artifact.",
            stage="quillan_artifact_context",
        )
    expected_descriptor, representation_kind, artifact_kind, media_type = _request_spec(
        context.artifact_request_kind
    )
    if descriptor != expected_descriptor:
        raise _source_integrity(
            "Quillan provider descriptor disagrees with the source context.",
            stage="quillan_artifact_context",
        )
    if (
        entry.producer_module_id != "quillan"
        or entry.projection_kind != representation_kind
        or entry.projection_contract_version
        != QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION
        or artifact.artifact_kind != artifact_kind
        or artifact.representation_kind != representation_kind
        or artifact.media_type != media_type
        or artifact.source_locator is not None
        or artifact.source_digest is not None
        or artifact.byte_size is not None
        or not isinstance(artifact.native_revision, int)
        or artifact.native_revision < 1
    ):
        raise _source_integrity(
            "Planned Quillan Artifact source contract is inconsistent.",
            stage="quillan_artifact_context",
        )
    if (
        entry.source_publication_id is None
        or context.source_publication_id != entry.source_publication_id
    ):
        raise _source_integrity(
            "Quillan Artifact source Publication does not match the immutable Entry Plan.",
            stage="quillan_artifact_context",
        )

    manifest = cast(_Manifest, context.manifest)
    try:
        if (
            manifest.work.module_id != "quillan"
            or manifest.record_set.revision != artifact.native_revision
            or manifest.record_set.revision < 1
        ):
            raise ValueError
    except Exception as error:
        raise _source_integrity(
            "Quillan Artifact source context does not match published history.",
            stage="quillan_artifact_context",
        ) from error

    _student(manifest, context.student_id)
    if context.artifact_request_kind == "student_work":
        assert context.evidence_id is not None
        expected_artifact_id = quillan_evidence_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=context.student_id,
            evidence_id=context.evidence_id,
        )
        if artifact.artifact_id != expected_artifact_id:
            raise _source_integrity(
                "Quillan selected-evidence identity does not match the immutable Entry Plan.",
                stage="quillan_artifact_context",
            )
        return _selected_reference(
            manifest,
            student_id=context.student_id,
            evidence_id=context.evidence_id,
        )

    expected_artifact_id = quillan_feedback_source_id(
        class_id=manifest.work.class_id,
        work_id=manifest.work.work_id,
        student_id=context.student_id,
        artifact_request_kind=context.artifact_request_kind,
    )
    if artifact.artifact_id != expected_artifact_id:
        raise _source_integrity(
            "Quillan feedback identity does not match the immutable Entry Plan.",
            stage="quillan_artifact_context",
        )
    return None


class _QuillanAuthorizationBridge:
    """Translate Quillan's producer request to deployment-owned Vitrine policy."""

    def __init__(
        self,
        *,
        snapshot_request: SnapshotSourceRequest,
        context: QuillanArtifactSourceContext,
        authorization_gate: QuillanArtifactAuthorizationGate,
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
                "Installed Quillan Artifact authorization model is incompatible.",
                stage="quillan_artifact_contract",
            ) from error

    def authorize(self, value: object) -> object:
        artifact = self._snapshot_request.entry_plan.source_artifact
        assert artifact is not None
        manifest = cast(_Manifest, self._context.manifest)
        try:
            producer_request = cast(_ProducerAuthorizationRequest, value)
            mismatch = (
                producer_request.work != manifest.work
                or producer_request.record_set_id != manifest.record_set.record_set_id
                or producer_request.record_set_revision != manifest.record_set.revision
                or producer_request.record_set_revision != artifact.native_revision
                or producer_request.student_id != self._context.student_id
                or producer_request.artifact_kind != self._context.artifact_request_kind
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
        request = QuillanArtifactAuthorizationRequest(
            operation=QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION,
            snapshot_build_plan_id=self._snapshot_request.snapshot_build_plan_id,
            snapshot_build_attempt_id=(
                self._snapshot_request.snapshot_build_attempt_id
            ),
            source_publication_id=self._context.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            student_id=self._context.student_id,
            artifact_kind=self._context.artifact_request_kind,
            evidence_id=self._context.evidence_id,
            purpose=self._purpose,
        )
        try:
            decision = self._authorization_gate.authorize(request)
        except Exception:
            self.gate_failed = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        if not isinstance(decision, QuillanArtifactAuthorizationDecision):
            self.gate_failed = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        self.last_outcome = decision.outcome
        return self._decision(decision.outcome)


def _verified_result(
    *,
    raw_results: object,
    api: _QuillanArtifactApi,
    bridge: _QuillanAuthorizationBridge,
    request: SnapshotSourceRequest,
    context: QuillanArtifactSourceContext,
    expected_evidence: _EvidenceReference | None,
) -> _AuthorizedArtifact:
    if bridge.last_outcome != "allowed" or bridge.producer_request is None:
        raise _source_integrity(
            "Quillan Artifact bytes returned without affirmed authorization.",
            stage="quillan_artifact_result",
        )
    if not isinstance(raw_results, tuple) or not raw_results:
        raise _source_integrity(
            "Quillan Artifact API returned an incompatible result set.",
            stage="quillan_artifact_result",
        )
    if any(not isinstance(item, api.result_type) for item in raw_results):
        raise _source_integrity(
            "Quillan Artifact API returned an incompatible result.",
            stage="quillan_artifact_result",
        )

    manifest = cast(_Manifest, context.manifest)
    producer_request = bridge.producer_request
    valid: list[_AuthorizedArtifact] = []
    for raw in raw_results:
        authorized = cast(_AuthorizedArtifact, raw)
        try:
            mismatch = (
                authorized.artifact_kind != context.artifact_request_kind
                or authorized.work != producer_request.work
                or authorized.work != manifest.work
                or authorized.record_set_revision != producer_request.record_set_revision
                or authorized.record_set_revision != manifest.record_set.revision
                or authorized.student_id != context.student_id
                or type(authorized.data) is not bytes
                or isinstance(authorized.byte_size, bool)
                or not isinstance(authorized.byte_size, int)
                or authorized.byte_size != len(authorized.data)
                or hashlib.sha256(authorized.data).hexdigest() != authorized.sha256
            )
        except Exception:
            mismatch = True
        if mismatch:
            raise _source_integrity(
                "Quillan Artifact result does not match the exact planned source.",
                stage="quillan_artifact_result",
            )
        valid.append(authorized)

    if context.artifact_request_kind == "student_work":
        assert expected_evidence is not None
        student = _student(manifest, context.student_id)
        provenance = student.submission.digital_provenance
        if student.submission.entry_method != "pds2_response_pages" or provenance is None:
            raise _source_integrity(
                "Quillan student-work result has no represented digital provenance.",
                stage="quillan_artifact_result",
            )
        expected_results = provenance.evidence_references
        if len(valid) != len(expected_results):
            raise _source_integrity(
                "Quillan student-work result cardinality disagrees with public provenance.",
                stage="quillan_artifact_result",
            )
        for item, reference in zip(valid, expected_results, strict=True):
            if (
                item.evidence_reference != reference
                or item.sha256 != reference.routed_evidence_sha256
                or item.media_type not in QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES
            ):
                raise _source_integrity(
                    "Quillan student-work bytes disagree with public manifest provenance.",
                    stage="quillan_artifact_result",
                )
        matches = tuple(
            item
            for item in valid
            if item.evidence_reference is not None
            and item.evidence_reference.evidence_id == expected_evidence.evidence_id
        )
        if len(matches) != 1:
            raise _source_integrity(
                "Quillan student-work results do not resolve the exact selected evidence.",
                stage="quillan_artifact_result",
            )
        return matches[0]

    if len(valid) != 1:
        raise _source_integrity(
            "Quillan feedback result is not the exact requested representation.",
            stage="quillan_artifact_result",
        )
    selected = valid[0]
    expected_media = (
        QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
        if context.artifact_request_kind == "feedback_pdf"
        else QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
    )
    if selected.evidence_reference is not None or selected.media_type != expected_media:
        raise _source_integrity(
            "Quillan feedback result disagrees with the planned representation.",
            stage="quillan_artifact_result",
        )
    return selected


class QuillanAuthorizedArtifactSourceProvider:
    """Acquire one exact planned Quillan Artifact only through its public API."""

    def __init__(
        self,
        *,
        artifact_request_kind: str,
        context_resolver: QuillanArtifactSourceContextResolver,
        authorization_gate: QuillanArtifactAuthorizationGate,
        purpose: str = QUILLAN_ARTIFACT_SNAPSHOT_PURPOSE,
    ) -> None:
        descriptor, _, _, _ = _request_spec(artifact_request_kind)
        self._descriptor = descriptor
        self._artifact_request_kind = artifact_request_kind
        self._context_resolver = context_resolver
        self._authorization_gate = authorization_gate
        try:
            self._purpose = require_text(purpose, "purpose", maximum=256)
        except VitrineModelValidationError as error:
            raise _invalid_request(
                "Quillan Artifact Snapshot purpose is invalid.",
                stage="quillan_artifact_provider",
            ) from error

    @property
    def descriptor(self) -> SnapshotSourceProviderDescriptor:
        return self._descriptor

    def resolve(
        self, request: SnapshotSourceRequest
    ) -> SnapshotAuthorizedSourceBytesResult:
        try:
            context = self._context_resolver.resolve(request)
        except SnapshotMaterializationError:
            raise
        except Exception as error:
            raise _source_unavailable(
                "Quillan Artifact source context could not be resolved.",
                stage="quillan_artifact_context",
            ) from error
        if not isinstance(context, QuillanArtifactSourceContext):
            raise _source_integrity(
                "Quillan Artifact source resolver returned an invalid context.",
                stage="quillan_artifact_context",
            )
        if context.artifact_request_kind != self._artifact_request_kind:
            raise _source_integrity(
                "Quillan Artifact source context disagrees with provider kind.",
                stage="quillan_artifact_context",
            )
        expected_evidence = _validate_context(request, context, self.descriptor)

        # Quillan is imported only after the immutable Vitrine/Core source context
        # is fixed. The producer API itself calls the bridge before native I/O.
        api = _load_quillan_artifact_api()
        bridge = _QuillanAuthorizationBridge(
            snapshot_request=request,
            context=context,
            authorization_gate=self._authorization_gate,
            decision_factory=api.decision_factory,
            purpose=self._purpose,
        )
        try:
            raw_results = api.read(
                context.workspace_root,
                context.manifest,
                context.student_id,
                context.artifact_request_kind,
                purpose=self._purpose,
                authorization_gate=bridge,
            )
        except api.authorization_error as error:
            if bridge.integrity_mismatch:
                raise _source_integrity(
                    "Quillan Artifact authorization request disagreed with planned provenance.",
                    stage="quillan_artifact_authorization",
                ) from error
            if bridge.last_outcome == "denied":
                raise _source_unavailable(
                    "Quillan Artifact authorization was denied.",
                    stage="quillan_artifact_authorization_denied",
                ) from error
            raise _source_unavailable(
                "Quillan Artifact authorization was unresolved.",
                stage="quillan_artifact_authorization_unresolved",
            ) from error
        except api.integrity_error as error:
            raise _source_integrity(
                "Quillan Artifact historical or byte integrity verification failed.",
                stage="quillan_artifact_read",
            ) from error
        except api.validation_error as error:
            raise _source_integrity(
                "Quillan Artifact request failed producer validation.",
                stage="quillan_artifact_read",
            ) from error
        except (api.unavailable_error, api.read_error) as error:
            raise _source_unavailable(
                "Quillan Artifact source is unavailable.",
                stage="quillan_artifact_read",
            ) from error
        except SnapshotMaterializationError:
            raise
        except Exception as error:
            raise _source_unavailable(
                "Quillan Artifact source could not be acquired.",
                stage="quillan_artifact_read",
            ) from error

        authorized = _verified_result(
            raw_results=raw_results,
            api=api,
            bridge=bridge,
            request=request,
            context=context,
            expected_evidence=expected_evidence,
        )
        artifact = request.entry_plan.source_artifact
        assert artifact is not None
        acquisition_contract = (
            SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT
            if self._artifact_request_kind == "student_work"
            else SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
        )
        return SnapshotAuthorizedSourceBytesResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=context.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            content=authorized.data,
            media_type=authorized.media_type,
            source_digest=DigestReference(value=authorized.sha256),
            byte_size=authorized.byte_size,
            acquisition_contract_version=acquisition_contract,
        )

    def confirm_stability(
        self,
        request: SnapshotSourceRequest,
        result: SnapshotSourceResult,
    ) -> bool:
        raise _invalid_request(
            "Producer-authorized immutable Quillan bytes do not use filesystem stability.",
            stage="quillan_artifact_stability",
        )


def build_quillan_artifact_source_provider(
    *,
    artifact_request_kind: str,
    context_resolver: QuillanArtifactSourceContextResolver,
    authorization_gate: QuillanArtifactAuthorizationGate,
    purpose: str = QUILLAN_ARTIFACT_SNAPSHOT_PURPOSE,
) -> QuillanAuthorizedArtifactSourceProvider:
    """Build one exact Quillan provider without importing Quillan."""

    return QuillanAuthorizedArtifactSourceProvider(
        artifact_request_kind=artifact_request_kind,
        context_resolver=context_resolver,
        authorization_gate=authorization_gate,
        purpose=purpose,
    )


def build_quillan_artifact_source_providers(
    *,
    context_resolver: QuillanArtifactSourceContextResolver,
    authorization_gate: QuillanArtifactAuthorizationGate,
    purpose: str = QUILLAN_ARTIFACT_SNAPSHOT_PURPOSE,
) -> tuple[QuillanAuthorizedArtifactSourceProvider, ...]:
    """Build the closed set of exact Quillan Artifact providers lazily."""

    return tuple(
        build_quillan_artifact_source_provider(
            artifact_request_kind=kind,
            context_resolver=context_resolver,
            authorization_gate=authorization_gate,
            purpose=purpose,
        )
        for kind in ("student_work", "feedback_pdf", "feedback_markdown")
    )


__all__ = [
    "QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION",
    "QUILLAN_ARTIFACT_AUTHORIZATION_OUTCOMES",
    "QUILLAN_ARTIFACT_REQUEST_KINDS",
    "QUILLAN_ARTIFACT_SNAPSHOT_PURPOSE",
    "QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR",
    "QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_ID",
    "QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR",
    "QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_ID",
    "QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR",
    "QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_ID",
    "QuillanArtifactAuthorizationDecision",
    "QuillanArtifactAuthorizationGate",
    "QuillanArtifactAuthorizationRequest",
    "QuillanArtifactSourceContext",
    "QuillanArtifactSourceContextResolver",
    "QuillanAuthorizedArtifactSourceProvider",
    "build_quillan_artifact_source_provider",
    "build_quillan_artifact_source_providers",
]
