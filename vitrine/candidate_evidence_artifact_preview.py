"""Transient producer-authorized Artifact bytes for Candidate evidence preview.

This module consumes a CandidateEvidencePreviewPreparedContext produced by the
exact revalidation service. It never resolves producer-native paths and never
creates Snapshot plans, attempts, materializations, or durable preview state.

For live Quillan and Concord evidence, the producer public Artifact API remains
responsible for authorization ordering and native workspace integrity. Vitrine's
Candidate preview authorization is bridged into that producer-owned gate only
after the producer request is checked against exact Candidate provenance.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Callable, Final, Protocol, cast

from vitrine.candidate_evidence_preview import (
    CandidateEvidencePreviewAuthorizationDecision,
    CandidateEvidencePreviewAuthorizationGate,
    CandidateEvidencePreviewAuthorizationRequest,
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewPreparedContext,
    CandidateEvidencePreviewRequest,
    build_candidate_evidence_preview_authorization_request,
    resolve_candidate_evidence_preview_authority,
)
from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_MEDIA_TYPE,
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
)
from vitrine.models.common import require_identifier, require_text
from vitrine.models.errors import VitrineModelValidationError
from vitrine.producer_adapters import ProjectedProducerSource
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
)

CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_evidence_artifact_preview_v1"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidenceArtifactPreview:
    """Transient exact bytes returned by an authorized producer public API."""

    contract_version: str
    source_publication_id: str
    source_artifact_id: str
    producer_module_id: str
    artifact_kind: str
    representation_kind: str
    media_type: str
    sha256: str
    byte_size: int
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        try:
            if self.contract_version != (
                CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION
            ):
                raise VitrineModelValidationError(
                    "unexpected Candidate Artifact-preview contract."
                )
            for name in (
                "source_publication_id",
                "source_artifact_id",
                "producer_module_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            for name in (
                "artifact_kind",
                "representation_kind",
                "media_type",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_text(getattr(self, name), name, maximum=256),
                )
            object.__setattr__(
                self,
                "sha256",
                require_text(self.sha256, "sha256", maximum=64),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate Artifact preview result is invalid.",
                stage="artifact_preview_result",
            ) from error
        if type(self.content) is not bytes:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Candidate Artifact preview content is not immutable bytes.",
                stage="artifact_preview_result",
            )
        if (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size < 0
            or self.byte_size != len(self.content)
        ):
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Candidate Artifact preview byte size is inconsistent.",
                stage="artifact_preview_result",
            )
        if (
            len(self.sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.sha256)
            or hashlib.sha256(self.content).hexdigest() != self.sha256
        ):
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Candidate Artifact preview digest is inconsistent.",
                stage="artifact_preview_result",
            )


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _QuillanWork(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _QuillanEvidenceReference(Protocol):
    evidence_id: str
    routed_evidence_sha256: str


class _QuillanDigitalProvenance(Protocol):
    evidence_references: tuple[_QuillanEvidenceReference, ...]


class _QuillanSubmission(Protocol):
    entry_method: str
    digital_provenance: _QuillanDigitalProvenance | None


class _QuillanStudent(Protocol):
    student_id: str
    submission: _QuillanSubmission


class _QuillanManifest(Protocol):
    record_set: _RecordSet
    work: _QuillanWork
    students: tuple[_QuillanStudent, ...]


class _QuillanProducerRequest(Protocol):
    work: object
    record_set_id: str
    record_set_revision: int
    student_id: str
    artifact_kind: str
    purpose: str


class _QuillanAuthorizedArtifact(Protocol):
    artifact_kind: str
    work: object
    record_set_revision: int
    student_id: str
    media_type: str
    sha256: str
    byte_size: int
    data: bytes
    evidence_reference: _QuillanEvidenceReference | None


@dataclass(frozen=True, slots=True)
class _QuillanApi:
    decision_factory: Callable[..., object]
    result_type: type[object]
    read: Callable[..., object]
    authorization_error: type[BaseException]
    validation_error: type[BaseException]
    unavailable_error: type[BaseException]
    integrity_error: type[BaseException]
    read_error: type[BaseException]


class _ConcordProjection(Protocol):
    source_snapshot_revision: int


class _ConcordManifest(Protocol):
    work: object
    record_set: _RecordSet
    projection: _ConcordProjection


class _ConcordEvidenceReference(Protocol):
    evidence_kind: str
    owning_system: str
    record_id: str


class _ConcordProducerRequest(Protocol):
    work: object
    record_set_id: str
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _ConcordEvidenceReference
    purpose: str


class _ConcordArtifactPage(Protocol):
    artifact_page_id: str


class _ConcordArtifactProjection(Protocol):
    artifact_instance_id: str
    pages: tuple[_ConcordArtifactPage, ...]


class _ConcordAuthorizedArtifact(Protocol):
    representation: str
    work: object
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _ConcordEvidenceReference
    artifact: _ConcordArtifactProjection
    media_type: str
    sha256: str
    byte_size: int
    content: bytes


@dataclass(frozen=True, slots=True)
class _ConcordApi:
    decision_factory: Callable[..., object]
    result_type: type[object]
    read: Callable[..., object]
    authorization_error: type[BaseException]
    validation_error: type[BaseException]
    not_found_error: type[BaseException]
    unavailable_error: type[BaseException]
    ambiguity_error: type[BaseException]
    integrity_error: type[BaseException]


def _artifact_error(
    code: str,
    message: str,
    *,
    stage: str,
) -> CandidateEvidencePreviewError:
    return CandidateEvidencePreviewError(code, message, stage=stage)


def _exception_type(value: object) -> type[BaseException]:
    if not isinstance(value, type) or not issubclass(value, BaseException):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_contract_unavailable",
            "Installed producer Artifact API has an incompatible exception surface.",
            stage="artifact_preview_contract",
        )
    return value


def _load_quillan_api() -> _QuillanApi:
    try:
        module = import_module("quillan.academic_result_artifacts")
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_contract_unavailable",
            "Installed Quillan Artifact API is unavailable.",
            stage="artifact_preview_contract",
        ) from error
    decision_type = getattr(
        module,
        "AcademicResultArtifactAuthorizationDecision",
        None,
    )
    result_type = getattr(module, "AuthorizedAcademicResultArtifact", None)
    read = getattr(module, "read_authorized_academic_result_artifacts", None)
    if (
        not isinstance(decision_type, type)
        or not isinstance(result_type, type)
        or not callable(read)
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_contract_unavailable",
            "Installed Quillan Artifact API has an incompatible public surface.",
            stage="artifact_preview_contract",
        )
    return _QuillanApi(
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


def _load_concord_api() -> _ConcordApi:
    try:
        module = import_module("concord.academic_result_artifacts")
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_contract_unavailable",
            "Installed Concord Artifact API is unavailable.",
            stage="artifact_preview_contract",
        ) from error
    decision_type = getattr(
        module,
        "AcademicResultArtifactAuthorizationDecision",
        None,
    )
    result_type = getattr(module, "AuthorizedAcademicResultArtifact", None)
    read = getattr(module, "read_authorized_academic_result_artifact", None)
    if (
        not isinstance(decision_type, type)
        or not isinstance(result_type, type)
        or not callable(read)
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_contract_unavailable",
            "Installed Concord Artifact API has an incompatible public surface.",
            stage="artifact_preview_contract",
        )
    return _ConcordApi(
        decision_factory=cast(Callable[..., object], decision_type),
        result_type=result_type,
        read=cast(Callable[..., object], read),
        authorization_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactAuthorizationError",
                None,
            )
        ),
        validation_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactValidationError",
                None,
            )
        ),
        not_found_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactNotFoundError",
                None,
            )
        ),
        unavailable_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactUnavailableError",
                None,
            )
        ),
        ambiguity_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactAmbiguityError",
                None,
            )
        ),
        integrity_error=_exception_type(
            getattr(
                module,
                "ConcordAcademicResultArtifactIntegrityError",
                None,
            )
        ),
    )


def _projection_field(source: ProjectedProducerSource, key: str) -> object:
    matches = tuple(
        item.value for item in source.display_snapshot.fields if item.key == key
    )
    if len(matches) != 1:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Exact Candidate projection is missing required Artifact provenance.",
            stage="artifact_preview_context",
        )
    return matches[0]


def _text_projection_field(source: ProjectedProducerSource, key: str) -> str:
    value = _projection_field(source, key)
    if not isinstance(value, str) or not value:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Exact Candidate Artifact provenance is invalid.",
            stage="artifact_preview_context",
        )
    return value


def _single_quillan_student_id(source: ProjectedProducerSource) -> str:
    matches = tuple(
        item.source_subject_id
        for item in source.source_relationships
        if item.source_subject_kind == "core_student"
        and item.relationship_kind == "submission_subject"
    )
    if len(matches) != 1:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Candidate source does not resolve one represented student.",
            stage="artifact_preview_context",
        )
    return matches[0]


def _quillan_request_kind(source: ProjectedProducerSource) -> str:
    representation = source.source_artifact.representation_kind
    expected = {
        QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND: "student_work",
        QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND: "feedback_pdf",
        QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND: "feedback_markdown",
    }.get(representation)
    if expected is None:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_not_supported",
            "This Quillan representation has no byte-bearing Candidate preview.",
            stage="artifact_preview_context",
        )
    if _text_projection_field(source, "artifact_request_kind") != expected:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Candidate representation disagrees with projected Artifact provenance.",
            stage="artifact_preview_context",
        )
    return expected


def _quillan_student(
    manifest: _QuillanManifest,
    student_id: str,
) -> _QuillanStudent:
    matches = tuple(
        student for student in manifest.students if student.student_id == student_id
    )
    if len(matches) != 1:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan public model does not resolve one represented student.",
            stage="artifact_preview_context",
        )
    return matches[0]


def _quillan_expected_evidence(
    manifest: _QuillanManifest,
    *,
    student_id: str,
    evidence_id: str,
) -> _QuillanEvidenceReference:
    student = _quillan_student(manifest, student_id)
    provenance = student.submission.digital_provenance
    if (
        student.submission.entry_method != "pds2_response_pages"
        or provenance is None
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan student-work Candidate is not represented digital evidence.",
            stage="artifact_preview_context",
        )
    matches = tuple(
        item
        for item in provenance.evidence_references
        if item.evidence_id == evidence_id
    )
    if len(matches) != 1:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Candidate does not resolve one exact evidence reference.",
            stage="artifact_preview_context",
        )
    return matches[0]


class _PreviewAuthorizationBridge:
    """Bridge one exact Candidate-preview decision into a producer gate."""

    def __init__(
        self,
        *,
        preview_request: CandidateEvidencePreviewAuthorizationRequest,
        authorization_gate: CandidateEvidencePreviewAuthorizationGate,
        decision_factory: Callable[..., object],
        validate_producer_request: Callable[[object], bool],
    ) -> None:
        self._preview_request = preview_request
        self._authorization_gate = authorization_gate
        self._decision_factory = decision_factory
        self._validate_producer_request = validate_producer_request
        self.last_outcome: str | None = None
        self.preview_error: CandidateEvidencePreviewError | None = None
        self.integrity_mismatch = False
        self.producer_request: object | None = None

    def _decision(self, status: str) -> object:
        try:
            return self._decision_factory(status=status)
        except Exception as error:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_contract_unavailable",
                "Installed producer authorization model is incompatible.",
                stage="artifact_preview_contract",
            ) from error

    def authorize(self, value: object) -> object:
        try:
            valid = self._validate_producer_request(value)
        except Exception:
            valid = False
        if not valid:
            self.integrity_mismatch = True
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        self.producer_request = value
        try:
            decision = self._authorization_gate.authorize(self._preview_request)
        except Exception:
            self.preview_error = CandidateEvidencePreviewError(
                "candidate_evidence_preview.authorization_unresolved",
                "Candidate evidence-preview authorization could not be established.",
                stage="authorization",
            )
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        if not isinstance(
            decision,
            CandidateEvidencePreviewAuthorizationDecision,
        ):
            self.preview_error = CandidateEvidencePreviewError(
                "candidate_evidence_preview.authorization_unresolved",
                "Candidate evidence-preview gate returned an invalid decision.",
                stage="authorization",
            )
            self.last_outcome = "unresolved"
            return self._decision("unresolved")
        self.last_outcome = decision.outcome
        if decision.outcome == "allowed":
            if decision.authority_reference is None:
                self.preview_error = CandidateEvidencePreviewError(
                    "candidate_evidence_preview.authorization_unresolved",
                    "Candidate evidence-preview authorization is unresolved.",
                    stage="authorization",
                )
                self.last_outcome = "unresolved"
                return self._decision("unresolved")
            return self._decision("allowed")
        if decision.outcome == "denied":
            self.preview_error = CandidateEvidencePreviewError(
                "candidate_evidence_preview.authorization_denied",
                "Candidate evidence-preview authorization was denied.",
                stage="authorization",
            )
            return self._decision("denied")
        self.preview_error = CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization is unresolved.",
            stage="authorization",
        )
        return self._decision("unresolved")


def _replay_authority(
    workspace_root: str | Path,
    context: CandidateEvidencePreviewPreparedContext,
) -> None:
    authority = context.result.authority
    request = CandidateEvidencePreviewRequest(
        portfolio_id=authority.portfolio_id,
        portfolio_subject_id=authority.portfolio_subject_id,
        entry_id=authority.entry_id,
        candidate_id=authority.candidate_id,
        candidate_evaluation_id=authority.candidate_evaluation_id,
        requesting_actor=authority.requesting_actor,
        requested_purpose=authority.requested_purpose,
        observed_state_revision=authority.observed_state_revision,
    )
    current = resolve_candidate_evidence_preview_authority(
        workspace_root,
        request,
    )
    if current != authority:
        raise _artifact_error(
            "candidate_evidence_preview.state_conflict",
            "Candidate preview authority changed before Artifact acquisition.",
            stage="artifact_preview_state_replay",
        )


def _artifact_result(
    context: CandidateEvidencePreviewPreparedContext,
    *,
    content: bytes,
    media_type: str,
    sha256: str,
    byte_size: int,
) -> CandidateEvidenceArtifactPreview:
    authority = context.result.authority
    source = context.result.verified_source
    artifact = source.source_artifact
    if authority.source_artifact_id != artifact.artifact_id:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Candidate Artifact authority disagrees with the verified source.",
            stage="artifact_preview_result",
        )
    return CandidateEvidenceArtifactPreview(
        contract_version=CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
        source_publication_id=authority.source_publication_id,
        source_artifact_id=artifact.artifact_id,
        producer_module_id=source.producer_source.producer_module_id,
        artifact_kind=artifact.artifact_kind,
        representation_kind=artifact.representation_kind,
        media_type=media_type,
        sha256=sha256,
        byte_size=byte_size,
        content=content,
    )


def _acquire_quillan(
    context: CandidateEvidencePreviewPreparedContext,
    authorization_gate: CandidateEvidencePreviewAuthorizationGate,
) -> CandidateEvidenceArtifactPreview:
    source = context.result.verified_source
    artifact = source.source_artifact
    manifest = cast(_QuillanManifest, context.producer_public_model)
    student_id = _single_quillan_student_id(source)
    request_kind = _quillan_request_kind(source)

    try:
        if (
            manifest.work.module_id != "quillan"
            or manifest.record_set.revision != artifact.native_revision
            or manifest.record_set.revision < 1
        ):
            raise ValueError
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan public model disagrees with exact Candidate history.",
            stage="artifact_preview_context",
        ) from error

    expected_evidence: _QuillanEvidenceReference | None = None
    if request_kind == "student_work":
        if (
            artifact.artifact_kind != "original_student_work"
            or artifact.media_type != QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE
        ):
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan student-work Candidate contract is inconsistent.",
                stage="artifact_preview_context",
            )
        evidence_id = _text_projection_field(source, "evidence_id")
        expected_id = quillan_evidence_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student_id,
            evidence_id=evidence_id,
        )
        expected_evidence = _quillan_expected_evidence(
            manifest,
            student_id=student_id,
            evidence_id=evidence_id,
        )
    else:
        expected_media = (
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
            if request_kind == "feedback_pdf"
            else QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
        )
        if (
            artifact.artifact_kind != "rendered_feedback"
            or artifact.media_type != expected_media
        ):
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan feedback Candidate contract is inconsistent.",
                stage="artifact_preview_context",
            )
        expected_id = quillan_feedback_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student_id,
            artifact_request_kind=request_kind,
        )
    if artifact.artifact_id != expected_id:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Candidate Artifact identity is inconsistent.",
            stage="artifact_preview_context",
        )

    preview_request = build_candidate_evidence_preview_authorization_request(
        context.result.authority
    )
    api = _load_quillan_api()

    def validate(value: object) -> bool:
        producer = cast(_QuillanProducerRequest, value)
        return (
            producer.work == manifest.work
            and producer.record_set_id == manifest.record_set.record_set_id
            and producer.record_set_revision == manifest.record_set.revision
            and producer.record_set_revision == artifact.native_revision
            and producer.student_id == student_id
            and producer.artifact_kind == request_kind
            and producer.purpose == context.result.authority.requested_purpose
        )

    bridge = _PreviewAuthorizationBridge(
        preview_request=preview_request,
        authorization_gate=authorization_gate,
        decision_factory=api.decision_factory,
        validate_producer_request=validate,
    )
    try:
        raw = api.read(
            Path(context.workspace_root),
            manifest,
            student_id,
            request_kind,
            purpose=context.result.authority.requested_purpose,
            authorization_gate=bridge,
        )
    except api.authorization_error as error:
        if bridge.integrity_mismatch:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan authorization request disagreed with Candidate provenance.",
                stage="artifact_preview_authorization",
            ) from error
        if bridge.preview_error is not None:
            raise bridge.preview_error from error
        raise _artifact_error(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization is unresolved.",
            stage="authorization",
        ) from error
    except (api.integrity_error, api.validation_error) as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Artifact integrity or producer validation failed.",
            stage="artifact_preview_read",
        ) from error
    except (api.unavailable_error, api.read_error) as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_unavailable",
            "Quillan Artifact source is unavailable.",
            stage="artifact_preview_read",
        ) from error
    except CandidateEvidencePreviewError:
        raise
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_unavailable",
            "Quillan Artifact source could not be acquired.",
            stage="artifact_preview_read",
        ) from error

    if bridge.last_outcome != "allowed" or bridge.producer_request is None:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan returned Artifact bytes without affirmed preview authorization.",
            stage="artifact_preview_result",
        )
    if not isinstance(raw, tuple) or not raw:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Artifact API returned an incompatible result set.",
            stage="artifact_preview_result",
        )
    if any(not isinstance(item, api.result_type) for item in raw):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Quillan Artifact API returned an incompatible result.",
            stage="artifact_preview_result",
        )

    valid: list[_QuillanAuthorizedArtifact] = []
    for item in raw:
        authorized = cast(_QuillanAuthorizedArtifact, item)
        try:
            mismatch = (
                authorized.artifact_kind != request_kind
                or authorized.work != manifest.work
                or authorized.record_set_revision != manifest.record_set.revision
                or authorized.student_id != student_id
                or type(authorized.data) is not bytes
                or isinstance(authorized.byte_size, bool)
                or not isinstance(authorized.byte_size, int)
                or authorized.byte_size != len(authorized.data)
                or hashlib.sha256(authorized.data).hexdigest()
                != authorized.sha256
            )
        except Exception:
            mismatch = True
        if mismatch:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan Artifact result does not match exact Candidate provenance.",
                stage="artifact_preview_result",
            )
        valid.append(authorized)

    if request_kind == "student_work":
        assert expected_evidence is not None
        student = _quillan_student(manifest, student_id)
        provenance = student.submission.digital_provenance
        assert provenance is not None
        expected_results = provenance.evidence_references
        if len(valid) != len(expected_results):
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan student-work result cardinality disagrees with public provenance.",
                stage="artifact_preview_result",
            )
        for item, reference in zip(valid, expected_results, strict=True):
            if (
                item.evidence_reference != reference
                or item.sha256 != reference.routed_evidence_sha256
                or item.media_type not in QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES
            ):
                raise _artifact_error(
                    "candidate_evidence_preview.artifact_source_integrity_failed",
                    "Quillan student-work bytes disagree with public provenance.",
                    stage="artifact_preview_result",
                )
        matches = tuple(
            item
            for item in valid
            if item.evidence_reference is not None
            and item.evidence_reference.evidence_id == expected_evidence.evidence_id
        )
        if len(matches) != 1:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan results do not resolve the exact Candidate evidence.",
                stage="artifact_preview_result",
            )
        selected = matches[0]
    else:
        if len(valid) != 1:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan feedback result is not the exact requested representation.",
                stage="artifact_preview_result",
            )
        selected = valid[0]
        expected_media = (
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
            if request_kind == "feedback_pdf"
            else QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
        )
        if (
            selected.evidence_reference is not None
            or selected.media_type != expected_media
        ):
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Quillan feedback result disagrees with Candidate representation.",
                stage="artifact_preview_result",
            )

    return _artifact_result(
        context,
        content=selected.data,
        media_type=selected.media_type,
        sha256=selected.sha256,
        byte_size=selected.byte_size,
    )


def _concord_context_fields(
    source: ProjectedProducerSource,
) -> tuple[str, str, str]:
    if (
        source.producer_source.source_record_kind != "score_evidence_link"
        or source.source_artifact.artifact_kind != "collaborative_artifact"
        or source.source_artifact.representation_kind
        != CONCORD_ARTIFACT_REPRESENTATION_KIND
        or source.source_artifact.media_type != CONCORD_ARTIFACT_MEDIA_TYPE
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord Candidate Artifact contract is inconsistent.",
            stage="artifact_preview_context",
        )
    score_record_id = _text_projection_field(
        source,
        "score_evidence_parent_score_record_id",
    )
    evidence_kind = _text_projection_field(source, "evidence_kind")
    evidence_record_id = _text_projection_field(source, "evidence_record_id")
    if (
        evidence_kind not in {"artifact_instance", "artifact_page"}
        or _text_projection_field(source, "evidence_owning_system") != "concord"
        or evidence_record_id != source.source_artifact.artifact_id
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord Candidate evidence reference is inconsistent.",
            stage="artifact_preview_context",
        )
    return score_record_id, evidence_kind, evidence_record_id


def _acquire_concord(
    context: CandidateEvidencePreviewPreparedContext,
    authorization_gate: CandidateEvidencePreviewAuthorizationGate,
) -> CandidateEvidenceArtifactPreview:
    source = context.result.verified_source
    artifact = source.source_artifact
    manifest = cast(_ConcordManifest, context.producer_public_model)
    score_record_id, evidence_kind, evidence_record_id = _concord_context_fields(
        source
    )
    score_evidence_link_id = source.producer_source.source_record_id

    try:
        if (
            manifest.record_set.revision < 1
            or manifest.projection.source_snapshot_revision
            != artifact.native_revision
        ):
            raise ValueError
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord public model disagrees with exact Candidate history.",
            stage="artifact_preview_context",
        ) from error

    preview_request = build_candidate_evidence_preview_authorization_request(
        context.result.authority
    )
    api = _load_concord_api()

    def validate(value: object) -> bool:
        producer = cast(_ConcordProducerRequest, value)
        evidence = producer.evidence_reference
        return (
            producer.work == manifest.work
            and producer.record_set_id == manifest.record_set.record_set_id
            and producer.record_set_revision == manifest.record_set.revision
            and producer.source_snapshot_revision
            == manifest.projection.source_snapshot_revision
            and producer.source_snapshot_revision == artifact.native_revision
            and producer.score_record_id == score_record_id
            and producer.score_evidence_link_id == score_evidence_link_id
            and evidence.owning_system == "concord"
            and evidence.evidence_kind == evidence_kind
            and evidence.record_id == evidence_record_id
            and producer.purpose == context.result.authority.requested_purpose
        )

    bridge = _PreviewAuthorizationBridge(
        preview_request=preview_request,
        authorization_gate=authorization_gate,
        decision_factory=api.decision_factory,
        validate_producer_request=validate,
    )
    try:
        raw = api.read(
            Path(context.workspace_root),
            manifest,
            score_evidence_link_id,
            purpose=context.result.authority.requested_purpose,
            authorization_gate=bridge,
        )
    except api.authorization_error as error:
        if bridge.integrity_mismatch:
            raise _artifact_error(
                "candidate_evidence_preview.artifact_source_integrity_failed",
                "Concord authorization request disagreed with Candidate provenance.",
                stage="artifact_preview_authorization",
            ) from error
        if bridge.preview_error is not None:
            raise bridge.preview_error from error
        raise _artifact_error(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization is unresolved.",
            stage="authorization",
        ) from error
    except (api.integrity_error, api.validation_error) as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord Artifact integrity or producer validation failed.",
            stage="artifact_preview_read",
        ) from error
    except (
        api.not_found_error,
        api.unavailable_error,
        api.ambiguity_error,
    ) as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_unavailable",
            "Concord Artifact source is unavailable.",
            stage="artifact_preview_read",
        ) from error
    except CandidateEvidencePreviewError:
        raise
    except Exception as error:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_unavailable",
            "Concord Artifact source could not be acquired.",
            stage="artifact_preview_read",
        ) from error

    if bridge.last_outcome != "allowed" or bridge.producer_request is None:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord returned Artifact bytes without affirmed preview authorization.",
            stage="artifact_preview_result",
        )
    if not isinstance(raw, api.result_type):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord Artifact API returned an incompatible result.",
            stage="artifact_preview_result",
        )
    authorized = cast(_ConcordAuthorizedArtifact, raw)
    evidence = authorized.evidence_reference
    try:
        mismatch = (
            authorized.representation != "returned_artifact_pdf"
            or authorized.work != manifest.work
            or authorized.record_set_revision != manifest.record_set.revision
            or authorized.source_snapshot_revision
            != manifest.projection.source_snapshot_revision
            or authorized.source_snapshot_revision != artifact.native_revision
            or authorized.score_record_id != score_record_id
            or authorized.score_evidence_link_id != score_evidence_link_id
            or evidence.owning_system != "concord"
            or evidence.evidence_kind != evidence_kind
            or evidence.record_id != evidence_record_id
            or authorized.media_type != CONCORD_ARTIFACT_MEDIA_TYPE
            or type(authorized.content) is not bytes
            or not authorized.content.startswith(b"%PDF")
            or isinstance(authorized.byte_size, bool)
            or not isinstance(authorized.byte_size, int)
            or authorized.byte_size != len(authorized.content)
            or hashlib.sha256(authorized.content).hexdigest()
            != authorized.sha256
        )
        if evidence_kind == "artifact_instance":
            mismatch = (
                mismatch
                or authorized.artifact.artifact_instance_id
                != evidence_record_id
            )
        else:
            page_ids = tuple(
                page.artifact_page_id for page in authorized.artifact.pages
            )
            mismatch = mismatch or evidence_record_id not in page_ids
    except Exception:
        mismatch = True
    if mismatch:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_source_integrity_failed",
            "Concord Artifact result does not match exact Candidate provenance.",
            stage="artifact_preview_result",
        )

    return _artifact_result(
        context,
        content=authorized.content,
        media_type=authorized.media_type,
        sha256=authorized.sha256,
        byte_size=authorized.byte_size,
    )


def acquire_candidate_evidence_artifact_preview(
    workspace_root: str | Path,
    context: CandidateEvidencePreviewPreparedContext,
    *,
    authorization_gate: CandidateEvidencePreviewAuthorizationGate,
) -> CandidateEvidenceArtifactPreview:
    """Acquire one exact byte-bearing Candidate preview through producer APIs."""

    if not isinstance(context, CandidateEvidencePreviewPreparedContext):
        raise _artifact_error(
            "candidate_evidence_preview.invalid_request",
            "Candidate Artifact preview requires a prepared preview context.",
            stage="artifact_preview_request",
        )
    result = context.result
    if (
        result.preview_kind != "artifact_preview"
        or not result.artifact_authorization_required
    ):
        raise _artifact_error(
            "candidate_evidence_preview.artifact_not_supported",
            "This Candidate does not have a byte-bearing preview representation.",
            stage="artifact_preview_request",
        )

    _replay_authority(workspace_root, context)
    module_id = result.verified_source.producer_source.producer_module_id
    if module_id == "quillan":
        acquired = _acquire_quillan(context, authorization_gate)
    elif module_id == "concord":
        acquired = _acquire_concord(context, authorization_gate)
    else:
        raise _artifact_error(
            "candidate_evidence_preview.artifact_not_supported",
            "This producer has no released byte-bearing Candidate preview bridge.",
            stage="artifact_preview_request",
        )
    _replay_authority(workspace_root, context)
    return acquired


__all__ = [
    "CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION",
    "CandidateEvidenceArtifactPreview",
    "acquire_candidate_evidence_artifact_preview",
]
