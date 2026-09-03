"""Pure live Quillan Academic Result projection for Vitrine.

Issue #60 Slice 2 consumes only the already validated public Quillan model returned
by the installed producer reader. It projects logical review summaries plus exact
selected-evidence and feedback Artifact capabilities. This module performs no
manifest parsing, native workspace access, Artifact authorization, Artifact reads,
Grade/proficiency inference, or Candidate policy.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from importlib import import_module
from typing import Final, Protocol, cast

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
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND,
    QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE,
    QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
    quillan_review_source_id,
)
from vitrine.released_producer_contracts import (
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)

QUILLAN_LIVE_ADAPTER_ID: Final[str] = "vitrine_quillan_live_adapter"
QUILLAN_LIVE_ADAPTER_CONTRACT_VERSION: Final[str] = (
    "vitrine_quillan_live_adapter_v1"
)
QUILLAN_LIVE_DIAGNOSTIC_CONTRACT_VERSION: Final[str] = (
    "vitrine_adapter_diagnostic_v1"
)
QUILLAN_PRIVACY_POLICY_REFERENCE: Final[str] = (
    "vitrine_live_quillan_minimum_necessary_v1"
)
_REVIEW_PAYLOAD_CHUNK_SIZE: Final[int] = 900

_QUILLAN_AUDIT = RELEASED_PRODUCER_CONTRACT_BY_MODULE["quillan"]
_QUILLAN_READER_DESCRIPTOR = build_audited_installed_producer_reader(
    "quillan"
).descriptor

QUILLAN_LIVE_ADAPTER_DECLARATION: Final[ProducerProjectionAdapterDeclaration] = (
    ProducerProjectionAdapterDeclaration(
        adapter_id=QUILLAN_LIVE_ADAPTER_ID,
        adapter_contract_version=QUILLAN_LIVE_ADAPTER_CONTRACT_VERSION,
        candidate_projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
        support_key=QUILLAN_LIVE_SUPPORT_KEY,
        public_reader_id=_QUILLAN_READER_DESCRIPTOR.public_reader_id,
        reader_contract_version=INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
        reader_package_identity=_QUILLAN_AUDIT.distribution_name,
        supported_source_families=(
            "assessment_result",
            "feedback",
            "student_work",
        ),
        supported_representation_families=(
            "feedback",
            "result_summary",
            "student_work",
        ),
        diagnostic_contract_version=QUILLAN_LIVE_DIAGNOSTIC_CONTRACT_VERSION,
        integration_kind="live",
    )
)


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _Work(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _SourceRecordSnapshot(Protocol):
    relative_path: str
    sha256: str
    contract_version: str


class _StudentSourceSnapshot(Protocol):
    submission: _SourceRecordSnapshot
    review: _SourceRecordSnapshot


class _ReviewUnitDefinition(Protocol):
    type: str
    singular_label: str
    plural_label: str


class _RatingScaleLevel(Protocol):
    value: int
    label: str
    description: str


class _RatingScale(Protocol):
    scale_id: str
    levels: tuple[_RatingScaleLevel, ...]


class _BasicRequirements(Protocol):
    paragraphs_min: int | None
    paragraphs_max: int | None
    word_count_min: int | None
    word_count_max: int | None
    required_elements: tuple[str, ...]


class _MinimumRequirementPolicy(Protocol):
    allow_return_without_full_review: bool


class _Assignment(Protocol):
    assignment_id: str
    title: str
    writing_type: str
    standards_profile_id: str
    focus_standard_ids: tuple[str, ...]
    review_unit: _ReviewUnitDefinition
    rating_scale: _RatingScale
    basic_requirements: _BasicRequirements
    minimum_requirement_policy: _MinimumRequirementPolicy


class _EvidenceReference(Protocol):
    page_id: str
    evidence_id: str
    observation_id: str
    route_id: str
    issuance_id: str
    generation_id: str
    artifact_id: str
    source_page_number: int
    source_scan_id: str
    source_sha256: str
    routed_evidence_sha256: str


class _DigitalSubmissionProvenance(Protocol):
    issuance_id: str
    generation_id: str
    artifact_id: str
    expected_page_ids: tuple[str, ...]
    evidence_references: tuple[_EvidenceReference, ...]


class _Submission(Protocol):
    class_id: str
    assignment_id: str
    student_id: str
    submission_state: str
    entry_method: str
    expected_pages: int | None
    digital_provenance: _DigitalSubmissionProvenance | None


class _PublishedText(Protocol):
    disposition: str
    text: str | None


class _MinimumRequirementOutcome(Protocol):
    status: str
    returned_without_full_review: bool
    updated_at: datetime | None
    teacher_note: _PublishedText


class _StandardObservation(Protocol):
    observation_id: str
    standard_id: str
    applicable: bool
    evidence_present: bool | None
    rating: int | None
    rationale: _PublishedText
    include_in_feedback: bool
    updated_at: datetime


class _ReviewUnit(Protocol):
    unit_id: str
    sequence: int
    label: str
    unit_type: str
    standard_observations: tuple[_StandardObservation, ...]


class _OverallStandardRating(Protocol):
    standard_id: str
    rating: int
    rationale: _PublishedText
    include_in_feedback: bool
    updated_at: datetime


class _FeedbackComment(Protocol):
    feedback_comment_id: str
    text: _PublishedText
    include_in_feedback: bool
    created_at: datetime


class _StandardFeedback(Protocol):
    standard_id: str
    include_overall_rating: bool
    include_overall_rationale: bool
    included_observation_ids: tuple[str, ...]
    comments: tuple[_FeedbackComment, ...]


class _FeedbackComposition(Protocol):
    include_review_unit_observations: bool
    include_overall_standard_ratings: bool
    standard_feedback: tuple[_StandardFeedback, ...]


class _Review(Protocol):
    class_id: str
    assignment_id: str
    student_id: str
    review_state: str
    minimum_requirement_outcome: _MinimumRequirementOutcome
    review_units: tuple[_ReviewUnit, ...]
    overall_standard_ratings: tuple[_OverallStandardRating, ...]
    feedback: _FeedbackComposition


class _StudentResult(Protocol):
    student_id: str
    source_snapshot: _StudentSourceSnapshot
    submission: _Submission
    review: _Review


class _AcademicResultManifest(Protocol):
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: _RecordSet
    work: _Work
    source_snapshot: _SourceRecordSnapshot
    assignment: _Assignment
    students: tuple[_StudentResult, ...]


def _canonical_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _optional_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _canonical_timestamp(value)


def _published_text_payload(value: _PublishedText) -> dict[str, object]:
    return {"disposition": value.disposition, "text": value.text}


def _source_snapshot_payload(value: _SourceRecordSnapshot) -> dict[str, object]:
    return {
        "relative_path": value.relative_path,
        "sha256": value.sha256,
        "contract_version": value.contract_version,
    }


def _assignment_payload(assignment: _Assignment) -> dict[str, object]:
    return {
        "assignment_id": assignment.assignment_id,
        "title": assignment.title,
        "writing_type": assignment.writing_type,
        "standards_profile_id": assignment.standards_profile_id,
        "focus_standard_ids": assignment.focus_standard_ids,
        "review_unit": {
            "type": assignment.review_unit.type,
            "singular_label": assignment.review_unit.singular_label,
            "plural_label": assignment.review_unit.plural_label,
        },
        "rating_scale": {
            "scale_id": assignment.rating_scale.scale_id,
            "levels": tuple(
                {
                    "value": level.value,
                    "label": level.label,
                    "description": level.description,
                }
                for level in assignment.rating_scale.levels
            ),
        },
        "basic_requirements": {
            "paragraphs_min": assignment.basic_requirements.paragraphs_min,
            "paragraphs_max": assignment.basic_requirements.paragraphs_max,
            "word_count_min": assignment.basic_requirements.word_count_min,
            "word_count_max": assignment.basic_requirements.word_count_max,
            "required_elements": assignment.basic_requirements.required_elements,
        },
        "minimum_requirement_policy": {
            "allow_return_without_full_review": (
                assignment.minimum_requirement_policy.allow_return_without_full_review
            )
        },
    }


def _submission_payload(submission: _Submission) -> dict[str, object]:
    digital = submission.digital_provenance
    digital_payload: dict[str, object] | None = None
    if digital is not None:
        digital_payload = {
            "issuance_id": digital.issuance_id,
            "generation_id": digital.generation_id,
            "artifact_id": digital.artifact_id,
            "expected_page_ids": digital.expected_page_ids,
        }
    return {
        "class_id": submission.class_id,
        "assignment_id": submission.assignment_id,
        "submission_state": submission.submission_state,
        "entry_method": submission.entry_method,
        "expected_pages": submission.expected_pages,
        "digital_provenance": digital_payload,
    }


def _observation_payload(observation: _StandardObservation) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id,
        "standard_id": observation.standard_id,
        "applicable": observation.applicable,
        "evidence_present": observation.evidence_present,
        "rating": observation.rating,
        "rationale": _published_text_payload(observation.rationale),
        "include_in_feedback": observation.include_in_feedback,
        "updated_at": _canonical_timestamp(observation.updated_at),
    }


def _review_unit_payload(unit: _ReviewUnit) -> dict[str, object]:
    return {
        "unit_id": unit.unit_id,
        "sequence": unit.sequence,
        "label": unit.label,
        "unit_type": unit.unit_type,
        "standard_observations": tuple(
            _observation_payload(observation)
            for observation in unit.standard_observations
        ),
    }


def _overall_rating_payload(rating: _OverallStandardRating) -> dict[str, object]:
    return {
        "standard_id": rating.standard_id,
        "rating": rating.rating,
        "rationale": _published_text_payload(rating.rationale),
        "include_in_feedback": rating.include_in_feedback,
        "updated_at": _canonical_timestamp(rating.updated_at),
    }


def _feedback_comment_payload(comment: _FeedbackComment) -> dict[str, object]:
    return {
        "feedback_comment_id": comment.feedback_comment_id,
        "text": _published_text_payload(comment.text),
        "include_in_feedback": comment.include_in_feedback,
        "created_at": _canonical_timestamp(comment.created_at),
    }


def _standard_feedback_payload(feedback: _StandardFeedback) -> dict[str, object]:
    return {
        "standard_id": feedback.standard_id,
        "include_overall_rating": feedback.include_overall_rating,
        "include_overall_rationale": feedback.include_overall_rationale,
        "included_observation_ids": feedback.included_observation_ids,
        "comments": tuple(
            _feedback_comment_payload(comment) for comment in feedback.comments
        ),
    }


def _review_payload(review: _Review) -> dict[str, object]:
    minimum = review.minimum_requirement_outcome
    feedback = review.feedback
    return {
        "class_id": review.class_id,
        "assignment_id": review.assignment_id,
        "review_state": review.review_state,
        "minimum_requirement_outcome": {
            "status": minimum.status,
            "returned_without_full_review": minimum.returned_without_full_review,
            "updated_at": _optional_timestamp(minimum.updated_at),
            "teacher_note": _published_text_payload(minimum.teacher_note),
        },
        "review_units": tuple(
            _review_unit_payload(unit) for unit in review.review_units
        ),
        "overall_standard_ratings": tuple(
            _overall_rating_payload(rating)
            for rating in review.overall_standard_ratings
        ),
        "feedback": {
            "include_review_unit_observations": (
                feedback.include_review_unit_observations
            ),
            "include_overall_standard_ratings": (
                feedback.include_overall_standard_ratings
            ),
            "standard_feedback": tuple(
                _standard_feedback_payload(item) for item in feedback.standard_feedback
            ),
        },
    }


def _semantic_payload(
    *, manifest: _AcademicResultManifest, student: _StudentResult
) -> dict[str, object]:
    return {
        "manifest": {
            "record_type": manifest.record_type,
            "contract_version": manifest.contract_version,
            "producer_module_id": manifest.producer_module_id,
            "generated_at": _canonical_timestamp(manifest.generated_at),
            "record_set": {
                "record_set_id": manifest.record_set.record_set_id,
                "revision": manifest.record_set.revision,
            },
        },
        "work": {
            "module_id": manifest.work.module_id,
            "class_id": manifest.work.class_id,
            "work_id": manifest.work.work_id,
        },
        "assignment_source_snapshot": _source_snapshot_payload(
            manifest.source_snapshot
        ),
        "assignment": _assignment_payload(manifest.assignment),
        "student_source_snapshot": {
            "submission": _source_snapshot_payload(student.source_snapshot.submission),
            "review": _source_snapshot_payload(student.source_snapshot.review),
        },
        "submission": _submission_payload(student.submission),
        "review": _review_payload(student.review),
    }


def _payload_chunks(payload: dict[str, object]) -> tuple[str, ...]:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    encoded = base64.b64encode(rendered).decode("ascii")
    return tuple(
        encoded[index : index + _REVIEW_PAYLOAD_CHUNK_SIZE]
        for index in range(0, len(encoded), _REVIEW_PAYLOAD_CHUNK_SIZE)
    )


def _projection_error(code: str, stage: str, message: str) -> ProducerProjectionError:
    return ProducerProjectionError(
        code,
        stage,
        message,
        adapter_id=QUILLAN_LIVE_ADAPTER_ID,
        producer_module_id="quillan",
        publication_kind=QUILLAN_LIVE_SUPPORT_KEY.publication_kind,
        manifest_contract_version=QUILLAN_LIVE_SUPPORT_KEY.manifest_contract_version,
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
        policy_reference=QUILLAN_PRIVACY_POLICY_REFERENCE,
    )


def _project_student(
    *, manifest: _AcademicResultManifest, student: _StudentResult
) -> ProjectedProducerSource:
    source_id = quillan_review_source_id(
        class_id=manifest.work.class_id,
        work_id=manifest.work.work_id,
        student_id=student.student_id,
    )
    review = student.review
    minimum = review.minimum_requirement_outcome
    observations = tuple(
        observation
        for unit in review.review_units
        for observation in unit.standard_observations
    )
    feedback_comments = tuple(
        comment
        for feedback in review.feedback.standard_feedback
        for comment in feedback.comments
    )
    fields = (
        ProjectionField(key="manifest_record_type", value=manifest.record_type),
        ProjectionField(
            key="manifest_contract_version", value=manifest.contract_version
        ),
        ProjectionField(key="producer_module_id", value=manifest.producer_module_id),
        ProjectionField(key="record_set_id", value=manifest.record_set.record_set_id),
        ProjectionField(key="record_set_revision", value=manifest.record_set.revision),
        ProjectionField(
            key="manifest_generated_at",
            value=_canonical_timestamp(manifest.generated_at),
        ),
        ProjectionField(key="class_id", value=manifest.work.class_id),
        ProjectionField(key="work_id", value=manifest.work.work_id),
        ProjectionField(key="assignment_id", value=manifest.assignment.assignment_id),
        ProjectionField(key="writing_type", value=manifest.assignment.writing_type),
        ProjectionField(
            key="standards_profile_id", value=manifest.assignment.standards_profile_id
        ),
        ProjectionField(
            key="focus_standard_ids", value=manifest.assignment.focus_standard_ids
        ),
        ProjectionField(
            key="assignment_source_relative_path",
            value=manifest.source_snapshot.relative_path,
        ),
        ProjectionField(
            key="assignment_source_sha256", value=manifest.source_snapshot.sha256
        ),
        ProjectionField(
            key="assignment_source_contract_version",
            value=manifest.source_snapshot.contract_version,
        ),
        ProjectionField(
            key="submission_source_relative_path",
            value=student.source_snapshot.submission.relative_path,
        ),
        ProjectionField(
            key="submission_source_sha256",
            value=student.source_snapshot.submission.sha256,
        ),
        ProjectionField(
            key="submission_source_contract_version",
            value=student.source_snapshot.submission.contract_version,
        ),
        ProjectionField(
            key="review_source_relative_path",
            value=student.source_snapshot.review.relative_path,
        ),
        ProjectionField(
            key="review_source_sha256", value=student.source_snapshot.review.sha256
        ),
        ProjectionField(
            key="review_source_contract_version",
            value=student.source_snapshot.review.contract_version,
        ),
        ProjectionField(
            key="submission_state", value=student.submission.submission_state
        ),
        ProjectionField(
            key="submission_entry_method", value=student.submission.entry_method
        ),
        ProjectionField(
            key="submission_expected_pages", value=student.submission.expected_pages
        ),
        ProjectionField(key="review_state", value=review.review_state),
        ProjectionField(key="minimum_requirement_status", value=minimum.status),
        ProjectionField(
            key="minimum_requirement_returned_without_full_review",
            value=minimum.returned_without_full_review,
        ),
        ProjectionField(
            key="minimum_requirement_updated_at",
            value=_optional_timestamp(minimum.updated_at),
        ),
        ProjectionField(
            key="minimum_requirement_teacher_note_disposition",
            value=minimum.teacher_note.disposition,
        ),
        ProjectionField(
            key="rating_scale_id", value=manifest.assignment.rating_scale.scale_id
        ),
        ProjectionField(
            key="rating_scale_values",
            value=tuple(
                level.value for level in manifest.assignment.rating_scale.levels
            ),
        ),
        ProjectionField(
            key="review_unit_ids",
            value=tuple(unit.unit_id for unit in review.review_units),
        ),
        ProjectionField(
            key="review_unit_sequences",
            value=tuple(unit.sequence for unit in review.review_units),
        ),
        ProjectionField(
            key="observation_ids",
            value=tuple(observation.observation_id for observation in observations),
        ),
        ProjectionField(
            key="observation_standard_ids",
            value=tuple(observation.standard_id for observation in observations),
        ),
        ProjectionField(
            key="observation_applicable",
            value=tuple(observation.applicable for observation in observations),
        ),
        ProjectionField(
            key="observation_evidence_present",
            value=tuple(observation.evidence_present for observation in observations),
        ),
        ProjectionField(
            key="observation_ratings",
            value=tuple(observation.rating for observation in observations),
        ),
        ProjectionField(
            key="observation_rationale_dispositions",
            value=tuple(
                observation.rationale.disposition for observation in observations
            ),
        ),
        ProjectionField(
            key="observation_include_in_feedback",
            value=tuple(
                observation.include_in_feedback for observation in observations
            ),
        ),
        ProjectionField(
            key="overall_rating_standard_ids",
            value=tuple(
                rating.standard_id for rating in review.overall_standard_ratings
            ),
        ),
        ProjectionField(
            key="overall_rating_values",
            value=tuple(rating.rating for rating in review.overall_standard_ratings),
        ),
        ProjectionField(
            key="overall_rating_rationale_dispositions",
            value=tuple(
                rating.rationale.disposition
                for rating in review.overall_standard_ratings
            ),
        ),
        ProjectionField(
            key="feedback_include_review_unit_observations",
            value=review.feedback.include_review_unit_observations,
        ),
        ProjectionField(
            key="feedback_include_overall_standard_ratings",
            value=review.feedback.include_overall_standard_ratings,
        ),
        ProjectionField(
            key="feedback_standard_ids",
            value=tuple(item.standard_id for item in review.feedback.standard_feedback),
        ),
        ProjectionField(
            key="feedback_comment_ids",
            value=tuple(comment.feedback_comment_id for comment in feedback_comments),
        ),
        ProjectionField(
            key="feedback_comment_text_dispositions",
            value=tuple(comment.text.disposition for comment in feedback_comments),
        ),
        ProjectionField(
            key="review_payload_json_base64_chunks",
            value=_payload_chunks(
                _semantic_payload(manifest=manifest, student=student)
            ),
        ),
    )
    return ProjectedProducerSource(
        projection_kind=QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
        producer_source=ProducerSourceReference(
            producer_module_id="quillan",
            producer_contract_version="quillan_academic_work_v1",
            source_record_kind="academic_result_review",
            source_record_id=source_id,
            source_record_contract_version=None,
            native_revision=manifest.record_set.revision,
            native_lifecycle=review.review_state,
            native_disposition=student.submission.entry_method,
            lineage_reference=None,
            reader_contract_version=(
                QUILLAN_LIVE_ADAPTER_DECLARATION.reader_contract_version
            ),
            projection_contract_version=(
                QUILLAN_LIVE_ADAPTER_DECLARATION.candidate_projection_contract_version
            ),
        ),
        source_artifact=SourceArtifactReference(
            artifact_id=f"{source_id}_summary",
            artifact_kind=QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND,
            representation_kind=QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
            media_type=QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE,
            source_locator=None,
            native_revision=manifest.record_set.revision,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        source_relationships=_student_relationship(
            student_id=student.student_id,
            supporting_source_reference=source_id,
        ),
        source_privacy=_single_subject_privacy(),
        display_snapshot=ProjectionDisplaySnapshot(
            title=f"Quillan review — {manifest.assignment.assignment_id}",
            summary=(
                "Native Quillan review evidence for one represented student result."
            ),
            fields=fields,
        ),
    )


def _student_relationship(
    *, student_id: str, supporting_source_reference: str
) -> tuple[ProjectedProducerRelationship, ...]:
    return (
        ProjectedProducerRelationship(
            source_subject_kind="core_student",
            source_subject_id=student_id,
            relationship_kind="submission_subject",
            relationship_authority="quillan",
            supporting_source_reference=supporting_source_reference,
        ),
    )


def _artifact_capability_source(
    *,
    manifest: _AcademicResultManifest,
    student: _StudentResult,
    source_id: str,
    projection_kind: str,
    artifact_kind: str,
    media_type: str,
    request_kind: str,
    title: str,
    fields: tuple[ProjectionField, ...],
) -> ProjectedProducerSource:
    return ProjectedProducerSource(
        projection_kind=projection_kind,
        producer_source=ProducerSourceReference(
            producer_module_id="quillan",
            producer_contract_version="quillan_academic_work_v1",
            source_record_kind="artifact_capability",
            source_record_id=source_id,
            source_record_contract_version=None,
            native_revision=manifest.record_set.revision,
            native_lifecycle=student.review.review_state,
            native_disposition=request_kind,
            lineage_reference=quillan_review_source_id(
                class_id=manifest.work.class_id,
                work_id=manifest.work.work_id,
                student_id=student.student_id,
            ),
            reader_contract_version=(
                QUILLAN_LIVE_ADAPTER_DECLARATION.reader_contract_version
            ),
            projection_contract_version=(
                QUILLAN_LIVE_ADAPTER_DECLARATION.candidate_projection_contract_version
            ),
        ),
        source_artifact=SourceArtifactReference(
            artifact_id=source_id,
            artifact_kind=artifact_kind,
            representation_kind=projection_kind,
            media_type=media_type,
            source_locator=None,
            native_revision=manifest.record_set.revision,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        source_relationships=_student_relationship(
            student_id=student.student_id,
            supporting_source_reference=source_id,
        ),
        source_privacy=_single_subject_privacy(),
        display_snapshot=ProjectionDisplaySnapshot(
            title=title,
            summary=(
                "Quillan Artifact capability only; availability and bytes remain "
                "authorization-gated producer concerns."
            ),
            fields=fields,
        ),
    )


def _project_selected_evidence(
    *, manifest: _AcademicResultManifest, student: _StudentResult
) -> tuple[ProjectedProducerSource, ...]:
    provenance = student.submission.digital_provenance
    if student.submission.entry_method != "pds2_response_pages" or provenance is None:
        return ()

    results: list[ProjectedProducerSource] = []
    for sequence, evidence in enumerate(provenance.evidence_references, start=1):
        source_id = quillan_evidence_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student.student_id,
            evidence_id=evidence.evidence_id,
        )
        fields = (
            ProjectionField(key="artifact_request_kind", value="student_work"),
            ProjectionField(key="evidence_sequence", value=sequence),
            ProjectionField(key="page_id", value=evidence.page_id),
            ProjectionField(key="evidence_id", value=evidence.evidence_id),
            ProjectionField(key="observation_id", value=evidence.observation_id),
            ProjectionField(key="route_id", value=evidence.route_id),
            ProjectionField(key="issuance_id", value=evidence.issuance_id),
            ProjectionField(key="generation_id", value=evidence.generation_id),
            ProjectionField(key="artifact_id", value=evidence.artifact_id),
            ProjectionField(
                key="source_page_number", value=evidence.source_page_number
            ),
            ProjectionField(key="source_scan_id", value=evidence.source_scan_id),
            ProjectionField(key="source_sha256", value=evidence.source_sha256),
            ProjectionField(
                key="routed_evidence_sha256",
                value=evidence.routed_evidence_sha256,
            ),
            ProjectionField(
                key="record_set_id", value=manifest.record_set.record_set_id
            ),
            ProjectionField(
                key="record_set_revision", value=manifest.record_set.revision
            ),
            ProjectionField(key="class_id", value=manifest.work.class_id),
            ProjectionField(key="work_id", value=manifest.work.work_id),
            ProjectionField(
                key="submission_source_sha256",
                value=student.source_snapshot.submission.sha256,
            ),
        )
        results.append(
            _artifact_capability_source(
                manifest=manifest,
                student=student,
                source_id=source_id,
                projection_kind=QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
                artifact_kind=QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
                media_type=QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
                request_kind="student_work",
                title=f"Quillan selected evidence — {manifest.assignment.assignment_id}",
                fields=fields,
            )
        )
    return tuple(results)


def _project_feedback_capabilities(
    *, manifest: _AcademicResultManifest, student: _StudentResult
) -> tuple[ProjectedProducerSource, ...]:
    results: list[ProjectedProducerSource] = []
    feedback_specs = (
        (
            "feedback_pdf",
            QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
        ),
        (
            "feedback_markdown",
            QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
            QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
        ),
    )
    for request_kind, representation_kind, media_type in feedback_specs:
        source_id = quillan_feedback_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student.student_id,
            artifact_request_kind=request_kind,
        )
        fields = (
            ProjectionField(key="artifact_request_kind", value=request_kind),
            ProjectionField(
                key="record_set_id", value=manifest.record_set.record_set_id
            ),
            ProjectionField(
                key="record_set_revision", value=manifest.record_set.revision
            ),
            ProjectionField(key="class_id", value=manifest.work.class_id),
            ProjectionField(key="work_id", value=manifest.work.work_id),
            ProjectionField(key="review_state", value=student.review.review_state),
            ProjectionField(
                key="review_source_sha256",
                value=student.source_snapshot.review.sha256,
            ),
            ProjectionField(
                key="review_source_contract_version",
                value=student.source_snapshot.review.contract_version,
            ),
        )
        results.append(
            _artifact_capability_source(
                manifest=manifest,
                student=student,
                source_id=source_id,
                projection_kind=representation_kind,
                artifact_kind=QUILLAN_FEEDBACK_ARTIFACT_KIND,
                media_type=media_type,
                request_kind=request_kind,
                title=f"Quillan feedback capability — {manifest.assignment.assignment_id}",
                fields=fields,
            )
        )
    return tuple(results)


class QuillanLiveProjectionAdapter:
    """Project each exact validated Quillan StudentResult independently."""

    def __init__(self) -> None:
        self._reader: ProducerManifestReader = build_audited_installed_producer_reader(
            "quillan"
        )

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return QUILLAN_LIVE_ADAPTER_DECLARATION

    @property
    def reader(self) -> ProducerManifestReader:
        return self._reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        """Project one validated public Quillan manifest without Artifact access."""

        try:
            contract = import_module("quillan.academic_result_manifest")
            manifest_type = getattr(contract, "AcademicResultManifest")
        except Exception as error:
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live Quillan projection contract could not be resolved.",
            ) from error
        if not isinstance(manifest_type, type):
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live Quillan projection contract has an incompatible type surface.",
            )
        if not isinstance(public_model, manifest_type):
            raise _projection_error(
                "projection.invalid_input",
                "projection",
                "Live Quillan adapter requires the validated public Quillan model.",
            )

        manifest = cast(_AcademicResultManifest, public_model)
        try:
            sources = tuple(
                source
                for student in manifest.students
                for source in (
                    _project_student(manifest=manifest, student=student),
                    *_project_selected_evidence(manifest=manifest, student=student),
                    *_project_feedback_capabilities(manifest=manifest, student=student),
                )
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
                "Live Quillan projection failed.",
            ) from error


def build_quillan_live_adapter() -> QuillanLiveProjectionAdapter:
    """Build the live adapter without importing or discovering Quillan."""

    return QuillanLiveProjectionAdapter()


__all__ = [
    "QUILLAN_LIVE_ADAPTER_CONTRACT_VERSION",
    "QUILLAN_LIVE_ADAPTER_DECLARATION",
    "QUILLAN_LIVE_ADAPTER_ID",
    "QUILLAN_LIVE_DIAGNOSTIC_CONTRACT_VERSION",
    "QUILLAN_PRIVACY_POLICY_REFERENCE",
    "QuillanLiveProjectionAdapter",
    "build_quillan_live_adapter",
]
