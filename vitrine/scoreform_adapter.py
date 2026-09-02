"""Pure live ScoreForm Academic Result projection for Vitrine.

Issue #59 consumes only the already validated public ScoreForm model returned by
the #58 installed reader.  This module performs no manifest parsing, workspace
access, retained-artifact access, attempt selection, Grade/proficiency inference,
or Candidate policy.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from importlib import import_module
from typing import Final, Protocol, cast

from vitrine.models.common import require_identifier, require_positive_int
from vitrine.models.errors import VitrineModelValidationError
from vitrine.models.sources import (
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.producer_adapters import (
    ProducerManifestReader,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProjectedProducerRelationship,
    ProjectedProducerSource,
    ProjectionDisplaySnapshot,
    ProjectionField,
)
from vitrine.producer_reader_services import (
    INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
    build_audited_installed_producer_reader,
)
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    SCOREFORM_LIVE_SUPPORT_KEY,
)

SCOREFORM_LIVE_ADAPTER_ID: Final[str] = "vitrine_scoreform_live_adapter"
SCOREFORM_LIVE_ADAPTER_CONTRACT_VERSION: Final[str] = (
    "vitrine_scoreform_live_adapter_v1"
)
SCOREFORM_LIVE_PROJECTION_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_projection_v1"
)
SCOREFORM_LIVE_DIAGNOSTIC_CONTRACT_VERSION: Final[str] = (
    "vitrine_adapter_diagnostic_v1"
)
SCOREFORM_ATTEMPT_PROJECTION_KIND: Final[str] = "scoreform:attempt_summary"
SCOREFORM_ATTEMPT_MEDIA_TYPE: Final[str] = (
    "application/vnd.pds.vitrine.scoreform-attempt-summary+json"
)
SCOREFORM_PRIVACY_POLICY_REFERENCE: Final[str] = (
    "vitrine_live_scoreform_minimum_necessary_v1"
)

_SCOREFORM_AUDIT = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]
_SCOREFORM_READER_DESCRIPTOR = build_audited_installed_producer_reader(
    "scoreform"
).descriptor

SCOREFORM_LIVE_ADAPTER_DECLARATION: Final[ProducerProjectionAdapterDeclaration] = (
    ProducerProjectionAdapterDeclaration(
        adapter_id=SCOREFORM_LIVE_ADAPTER_ID,
        adapter_contract_version=SCOREFORM_LIVE_ADAPTER_CONTRACT_VERSION,
        candidate_projection_contract_version=(
            SCOREFORM_LIVE_PROJECTION_CONTRACT_VERSION
        ),
        support_key=SCOREFORM_LIVE_SUPPORT_KEY,
        public_reader_id=_SCOREFORM_READER_DESCRIPTOR.public_reader_id,
        reader_contract_version=INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
        reader_package_identity=_SCOREFORM_AUDIT.distribution_name,
        supported_source_families=("assessment_result",),
        supported_representation_families=("result_summary",),
        diagnostic_contract_version=SCOREFORM_LIVE_DIAGNOSTIC_CONTRACT_VERSION,
        integration_kind="live",
    )
)


class _Question(Protocol):
    question_number: int
    points_possible: int
    standard_ids: tuple[str, ...]


class _Assignment(Protocol):
    assignment_id: str
    title: str
    question_count: int
    layout_id: str
    total_points: int
    standards_profile_id: str | None
    questions: tuple[_Question, ...]


class _Response(Protocol):
    question_number: int
    response_state: str
    selected_answer: str | None
    correct: bool


class _Attempt(Protocol):
    attempt_number: int
    result_origin: str
    recorded_at: datetime
    points_earned: int
    points_possible: int
    responses: tuple[_Response, ...]
    provenance: object


class _StudentResults(Protocol):
    student_id: str
    attempts: tuple[_Attempt, ...]


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _Work(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _AssignmentSource(Protocol):
    sha256: str


class _ResultsHistorySource(Protocol):
    sha256: str
    result_schema_version: str


class _SourceSnapshot(Protocol):
    assignment: _AssignmentSource
    results_history: _ResultsHistorySource


class _AcademicResultManifest(Protocol):
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: _RecordSet
    work: _Work
    source_snapshot: _SourceSnapshot
    assignment: _Assignment
    students: tuple[_StudentResults, ...]


class _Pds2ScanProvenance(Protocol):
    issuance_id: str
    generation_id: str
    artifact_id: str
    page_ids: tuple[str, ...]
    route_ids: tuple[str, ...]
    logical_pages: tuple[int, ...]
    source_scan_id: str
    source_page_numbers: tuple[int, ...]
    retained_source_path: str
    source_sha256: str


class _ReviewReference(Protocol):
    failure_id: str


class _ScanReviewManualProvenance(Protocol):
    review_reference: _ReviewReference


def _length_delimited_sha256(fields: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for field in fields:
        encoded = field.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def scoreform_attempt_projection_identity(
    *,
    class_id: str,
    assignment_id: str,
    student_id: str,
    attempt_number: int,
) -> str:
    """Return one stable opaque Vitrine identity for a ScoreForm native attempt.

    Identity intentionally excludes score, timestamp, response content, and all
    other mutable display/evidence values.  The student identifier participates
    in the digest but is never exposed in the returned identifier.
    """

    try:
        normalized_class_id = require_identifier(class_id, "class_id")
        normalized_assignment_id = require_identifier(assignment_id, "assignment_id")
        normalized_student_id = require_identifier(student_id, "student_id")
        normalized_attempt_number = require_positive_int(
            attempt_number, "attempt_number"
        )
    except VitrineModelValidationError as error:
        raise ProducerProjectionError(
            "projection.invalid_input",
            "projection_identity",
            "ScoreForm attempt projection identity inputs are invalid.",
            adapter_id=SCOREFORM_LIVE_ADAPTER_ID,
            producer_module_id="scoreform",
        ) from error

    digest = _length_delimited_sha256(
        (
            "scoreform",
            normalized_class_id,
            normalized_assignment_id,
            normalized_student_id,
            str(normalized_attempt_number),
            SCOREFORM_ATTEMPT_PROJECTION_KIND,
        )
    )
    return f"scoreform_attempt_{digest}"


def _work_lineage_reference(class_id: str, assignment_id: str) -> str:
    digest = _length_delimited_sha256(("scoreform", class_id, assignment_id, "work"))
    return f"scoreform_work_{digest}"


def _canonical_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _projection_error(code: str, stage: str, message: str) -> ProducerProjectionError:
    return ProducerProjectionError(
        code,
        stage,
        message,
        adapter_id=SCOREFORM_LIVE_ADAPTER_ID,
        producer_module_id="scoreform",
        publication_kind=SCOREFORM_LIVE_SUPPORT_KEY.publication_kind,
        manifest_contract_version=SCOREFORM_LIVE_SUPPORT_KEY.manifest_contract_version,
    )


def _single_subject_privacy() -> SourcePrivacyMetadata:
    return SourcePrivacyMetadata(
        classification="student_record",
        subject_scope="single_subject",
        metadata_visibility="internal",
        collaborator_information_present=False,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=False,
        multi_subject_review_required=False,
        minimum_necessary_projection_required=True,
        policy_reference=SCOREFORM_PRIVACY_POLICY_REFERENCE,
    )


def _question_points(questions: tuple[_Question, ...]) -> tuple[str, ...]:
    return tuple(
        f"{question.question_number}:{question.points_possible}"
        for question in questions
    )


def _question_alignments(questions: tuple[_Question, ...]) -> tuple[str, ...]:
    return tuple(
        f"{question.question_number}:{standard_id}"
        for question in questions
        for standard_id in question.standard_ids
    )


def _response_states(responses: tuple[_Response, ...]) -> tuple[str, ...]:
    return tuple(
        f"{response.question_number}:{response.response_state}"
        for response in responses
    )


def _selected_answer_presence(responses: tuple[_Response, ...]) -> tuple[str, ...]:
    return tuple(
        f"{response.question_number}:"
        f"{'present' if response.selected_answer is not None else 'absent'}"
        for response in responses
    )


def _response_correctness(responses: tuple[_Response, ...]) -> tuple[str, ...]:
    return tuple(
        f"{response.question_number}:{'true' if response.correct else 'false'}"
        for response in responses
    )


def _provenance_fields(
    *,
    attempt: _Attempt,
    pds2_type: type[object],
    plain_paper_type: type[object],
    scan_review_type: type[object],
) -> tuple[ProjectionField, ...]:
    provenance = attempt.provenance
    fields: list[ProjectionField] = [
        ProjectionField(key="provenance_kind", value=attempt.result_origin)
    ]
    if attempt.result_origin == "pds2_scan":
        if not isinstance(provenance, pds2_type):
            raise TypeError("ScoreForm pds2_scan provenance type mismatch")
        scan = cast(_Pds2ScanProvenance, provenance)
        fields.extend(
            (
                ProjectionField(key="pds2_issuance_id", value=scan.issuance_id),
                ProjectionField(key="pds2_generation_id", value=scan.generation_id),
                ProjectionField(key="pds2_artifact_id", value=scan.artifact_id),
                ProjectionField(key="pds2_page_ids", value=scan.page_ids),
                ProjectionField(key="pds2_route_ids", value=scan.route_ids),
                ProjectionField(key="pds2_logical_pages", value=scan.logical_pages),
                ProjectionField(key="pds2_source_scan_id", value=scan.source_scan_id),
                ProjectionField(
                    key="pds2_source_page_numbers",
                    value=scan.source_page_numbers,
                ),
                ProjectionField(key="pds2_source_sha256", value=scan.source_sha256),
            )
        )
    elif attempt.result_origin == "plain_paper_manual":
        if not isinstance(provenance, plain_paper_type):
            raise TypeError("ScoreForm plain-paper provenance type mismatch")
    elif attempt.result_origin == "scan_review_manual":
        if not isinstance(provenance, scan_review_type):
            raise TypeError("ScoreForm scan-review provenance type mismatch")
        review = cast(_ScanReviewManualProvenance, provenance)
        fields.append(
            ProjectionField(
                key="scan_review_failure_id",
                value=review.review_reference.failure_id,
            )
        )
    else:
        raise TypeError("ScoreForm result origin is unsupported")
    return tuple(fields)


def _project_attempt(
    *,
    manifest: _AcademicResultManifest,
    student: _StudentResults,
    attempt: _Attempt,
    pds2_type: type[object],
    plain_paper_type: type[object],
    scan_review_type: type[object],
) -> ProjectedProducerSource:
    assignment = manifest.assignment
    attempt_id = scoreform_attempt_projection_identity(
        class_id=manifest.work.class_id,
        assignment_id=assignment.assignment_id,
        student_id=student.student_id,
        attempt_number=attempt.attempt_number,
    )
    producer_source = ProducerSourceReference(
        producer_module_id="scoreform",
        producer_contract_version="scoreform_academic_work_v1",
        source_record_kind="academic_result_attempt",
        source_record_id=attempt_id,
        source_record_contract_version=None,
        native_revision=attempt.attempt_number,
        native_lifecycle="recorded",
        native_disposition="attempt",
        lineage_reference=_work_lineage_reference(
            manifest.work.class_id, assignment.assignment_id
        ),
        reader_contract_version=SCOREFORM_LIVE_ADAPTER_DECLARATION.reader_contract_version,
        projection_contract_version=(
            SCOREFORM_LIVE_ADAPTER_DECLARATION.candidate_projection_contract_version
        ),
    )
    base_fields = (
        ProjectionField(key="manifest_record_type", value=manifest.record_type),
        ProjectionField(
            key="manifest_contract_version", value=manifest.contract_version
        ),
        ProjectionField(key="producer_module_id", value=manifest.producer_module_id),
        ProjectionField(key="record_set_id", value=manifest.record_set.record_set_id),
        ProjectionField(key="record_set_revision", value=manifest.record_set.revision),
        ProjectionField(
            key="manifest_generated_at", value=_canonical_timestamp(manifest.generated_at)
        ),
        ProjectionField(
            key="assignment_source_sha256",
            value=manifest.source_snapshot.assignment.sha256,
        ),
        ProjectionField(
            key="results_history_source_sha256",
            value=manifest.source_snapshot.results_history.sha256,
        ),
        ProjectionField(
            key="results_history_schema_version",
            value=manifest.source_snapshot.results_history.result_schema_version,
        ),
        ProjectionField(key="class_id", value=manifest.work.class_id),
        ProjectionField(key="work_id", value=manifest.work.work_id),
        ProjectionField(key="assignment_id", value=assignment.assignment_id),
        ProjectionField(key="question_count", value=assignment.question_count),
        ProjectionField(key="layout_id", value=assignment.layout_id),
        ProjectionField(key="total_points", value=assignment.total_points),
        ProjectionField(
            key="standards_profile_id", value=assignment.standards_profile_id
        ),
        ProjectionField(
            key="question_numbers",
            value=tuple(question.question_number for question in assignment.questions),
        ),
        ProjectionField(
            key="question_points_possible",
            value=_question_points(assignment.questions),
        ),
        ProjectionField(
            key="question_standard_alignments",
            value=_question_alignments(assignment.questions),
        ),
        ProjectionField(key="attempt_number", value=attempt.attempt_number),
        ProjectionField(key="result_origin", value=attempt.result_origin),
        ProjectionField(
            key="recorded_at", value=_canonical_timestamp(attempt.recorded_at)
        ),
        ProjectionField(key="points_earned", value=attempt.points_earned),
        ProjectionField(key="points_possible", value=attempt.points_possible),
        ProjectionField(
            key="response_states", value=_response_states(attempt.responses)
        ),
        ProjectionField(
            key="selected_answer_presence",
            value=_selected_answer_presence(attempt.responses),
        ),
        ProjectionField(
            key="response_correctness",
            value=_response_correctness(attempt.responses),
        ),
    )
    return ProjectedProducerSource(
        projection_kind=SCOREFORM_ATTEMPT_PROJECTION_KIND,
        producer_source=producer_source,
        source_artifact=SourceArtifactReference(
            artifact_id=f"{attempt_id}_summary",
            artifact_kind="assessment_summary",
            representation_kind=SCOREFORM_ATTEMPT_PROJECTION_KIND,
            media_type=SCOREFORM_ATTEMPT_MEDIA_TYPE,
            source_locator=None,
            native_revision=attempt.attempt_number,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        source_relationships=(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id=student.student_id,
                relationship_kind="attempt_subject",
                relationship_authority="scoreform",
                supporting_source_reference=attempt_id,
            ),
        ),
        source_privacy=_single_subject_privacy(),
        display_snapshot=ProjectionDisplaySnapshot(
            title=f"{assignment.title} — Attempt {attempt.attempt_number}",
            summary="Native ScoreForm assessment evidence for one recorded attempt.",
            fields=base_fields
            + _provenance_fields(
                attempt=attempt,
                pds2_type=pds2_type,
                plain_paper_type=plain_paper_type,
                scan_review_type=scan_review_type,
            ),
        ),
    )


class ScoreFormLiveProjectionAdapter:
    """Project each exact validated ScoreForm student attempt independently."""

    def __init__(self) -> None:
        self._reader: ProducerManifestReader = build_audited_installed_producer_reader(
            "scoreform"
        )

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return SCOREFORM_LIVE_ADAPTER_DECLARATION

    @property
    def reader(self) -> ProducerManifestReader:
        return self._reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        """Project one validated public ScoreForm manifest without selecting attempts."""

        try:
            contract = import_module("scoreform.academic_result_manifest")
            manifest_type = getattr(contract, "AcademicResultManifest")
            pds2_type = getattr(contract, "Pds2ScanProvenance")
            plain_paper_type = getattr(contract, "PlainPaperManualProvenance")
            scan_review_type = getattr(contract, "ScanReviewManualProvenance")
        except Exception as error:
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live ScoreForm projection contract could not be resolved.",
            ) from error
        if not all(
            isinstance(value, type)
            for value in (
                manifest_type,
                pds2_type,
                plain_paper_type,
                scan_review_type,
            )
        ):
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live ScoreForm projection contract has an incompatible type surface.",
            )
        if not isinstance(public_model, manifest_type):
            raise _projection_error(
                "projection.invalid_input",
                "projection",
                "Live ScoreForm adapter requires the validated public ScoreForm model.",
            )

        manifest = cast(_AcademicResultManifest, public_model)
        try:
            sources = tuple(
                _project_attempt(
                    manifest=manifest,
                    student=student,
                    attempt=attempt,
                    pds2_type=pds2_type,
                    plain_paper_type=plain_paper_type,
                    scan_review_type=scan_review_type,
                )
                for student in manifest.students
                for attempt in student.attempts
            )
            return ProducerProjectionBatch(
                adapter_id=self.declaration.adapter_id,
                adapter_contract_version=self.declaration.adapter_contract_version,
                reader_id=self.declaration.public_reader_id,
                reader_contract_version=self.declaration.reader_contract_version,
                candidate_projection_contract_version=(
                    self.declaration.candidate_projection_contract_version
                ),
                support_key=self.declaration.support_key,
                projected_sources=sources,
                diagnostic_codes=(),
            )
        except ProducerProjectionError:
            raise
        except Exception as error:
            raise _projection_error(
                "projection.failed",
                "projection",
                "Live ScoreForm projection failed.",
            ) from error


def build_scoreform_live_adapter() -> ScoreFormLiveProjectionAdapter:
    """Build the live adapter without importing or discovering ScoreForm."""

    return ScoreFormLiveProjectionAdapter()


__all__ = [
    "SCOREFORM_ATTEMPT_MEDIA_TYPE",
    "SCOREFORM_ATTEMPT_PROJECTION_KIND",
    "SCOREFORM_LIVE_ADAPTER_CONTRACT_VERSION",
    "SCOREFORM_LIVE_ADAPTER_DECLARATION",
    "SCOREFORM_LIVE_ADAPTER_ID",
    "SCOREFORM_LIVE_DIAGNOSTIC_CONTRACT_VERSION",
    "SCOREFORM_LIVE_PROJECTION_CONTRACT_VERSION",
    "SCOREFORM_PRIVACY_POLICY_REFERENCE",
    "ScoreFormLiveProjectionAdapter",
    "build_scoreform_live_adapter",
    "scoreform_attempt_projection_identity",
]
