"""Transient instructional presentation for Candidate evidence.

This projection translates exact persisted Candidate/Evaluation source state into
teacher-readable evidence language. Display labels and representation-family keys
are presentation only; exact Candidate, Evaluation, source-record, and Artifact
identities remain the authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from vitrine.candidate_inbox import CandidateInboxDetail
from vitrine.models import CandidateSourceEndpoint

CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_evidence_presentation_v1"
)

_MODULE_FAMILIES: Final[dict[str, str]] = {
    "scoreform": "scoreform",
    "vitrine_scoreform_fixture": "scoreform",
    "quillan": "quillan",
    "vitrine_quillan_fixture": "quillan",
    "concord": "concord",
    "vitrine_concord_fixture": "concord",
}


@dataclass(frozen=True, slots=True)
class CandidateEvidenceProfileRole:
    """One exact Evaluation-matched Profile section plus its display label."""

    section_id: str
    label: str | None


@dataclass(frozen=True, slots=True)
class CandidateEvidencePresentation:
    """Instructional projection over one exact Candidate Inbox detail."""

    contract_version: str
    candidate_id: str | None
    current_evaluation_id: str | None
    evidence_kind: str | None
    work_title: str
    variant_label: str | None
    representation_label: str | None
    primary_label: str
    profile_fit: tuple[CandidateEvidenceProfileRole, ...]
    curation_state: str
    representation_family_key: str | None
    source_record_id: str | None
    source_artifact_id: str | None
    representation_kind: str | None


def _source_endpoint(detail: CandidateInboxDetail) -> CandidateSourceEndpoint | None:
    evaluation = getattr(detail, "evaluation", None)
    if evaluation is not None and isinstance(
        evaluation.source_endpoint, CandidateSourceEndpoint
    ):
        return evaluation.source_endpoint
    candidate = getattr(detail, "candidate", None)
    if candidate is not None and isinstance(
        candidate.source_endpoint, CandidateSourceEndpoint
    ):
        return candidate.source_endpoint
    return None


def _module_family(endpoint: CandidateSourceEndpoint) -> str | None:
    return _MODULE_FAMILIES.get(endpoint.producer_source.producer_module_id)


def _evidence_kind(endpoint: CandidateSourceEndpoint) -> str:
    family = _module_family(endpoint)
    producer = endpoint.producer_source
    artifact = endpoint.source_artifact
    artifact_kind = None if artifact is None else artifact.artifact_kind
    representation_kind = None if artifact is None else artifact.representation_kind

    if family == "scoreform" and artifact_kind == "assessment_summary":
        return "Assessment Attempt"

    if family == "quillan":
        if (
            representation_kind == "quillan:review_summary"
            or producer.source_record_kind == "academic_result_review"
        ):
            return "Review"
        if (
            representation_kind == "quillan:selected_student_work"
            or artifact_kind == "original_student_work"
            or producer.native_disposition == "student_work"
        ):
            return "Student Work"
        if (
            representation_kind
            in {"quillan:feedback_pdf", "quillan:feedback_markdown"}
            or artifact_kind == "rendered_feedback"
            or producer.native_disposition in {"feedback_pdf", "feedback_markdown"}
        ):
            return "Feedback"

    if family == "concord":
        if artifact_kind == "collaborative_artifact":
            return "Collaborative Work"
        if (
            artifact_kind == "assessment_summary"
            or producer.source_record_kind in {"score_record", "score_evidence_link"}
        ):
            return "Assessment Evidence"

    if artifact_kind == "rendered_feedback":
        return "Feedback"
    if artifact_kind in {"original_student_work", "collaborative_artifact"}:
        return "Student Work"
    if artifact_kind == "assessment_summary":
        return "Assessment Evidence"
    return "Evidence"


def _work_title(detail: CandidateInboxDetail, endpoint: CandidateSourceEndpoint) -> str:
    registration = endpoint.core_publication.registration_snapshot
    if registration is not None:
        return registration.title_snapshot
    return detail.item.source_display_label


def _variant_label(
    endpoint: CandidateSourceEndpoint,
    evidence_kind: str,
) -> str | None:
    if _module_family(endpoint) != "scoreform" or evidence_kind != "Assessment Attempt":
        return None
    revision = endpoint.producer_source.native_revision
    if isinstance(revision, int) and not isinstance(revision, bool) and revision > 0:
        return f"Attempt {revision}"
    if isinstance(revision, str) and revision.isdecimal() and int(revision) > 0:
        return f"Attempt {int(revision)}"
    return None


def _representation_label(
    endpoint: CandidateSourceEndpoint,
    evidence_kind: str,
) -> str | None:
    if evidence_kind != "Feedback":
        return None
    artifact = endpoint.source_artifact
    if artifact is None:
        return None
    if artifact.representation_kind == "quillan:feedback_pdf":
        return "PDF"
    if artifact.representation_kind == "quillan:feedback_markdown":
        return "Markdown"
    media_type = artifact.media_type.casefold()
    if media_type == "application/pdf":
        return "PDF"
    if media_type.startswith("text/markdown"):
        return "Markdown"
    return None


def _representation_family_key(
    endpoint: CandidateSourceEndpoint,
    evidence_kind: str,
) -> str | None:
    if _module_family(endpoint) != "quillan" or evidence_kind != "Feedback":
        return None
    lineage = endpoint.producer_source.lineage_reference
    if lineage is None:
        return None
    return f"quillan:feedback:{lineage}"


def _profile_fit(
    detail: CandidateInboxDetail,
) -> tuple[CandidateEvidenceProfileRole, ...]:
    labels = {
        section.section_id: section.label for section in detail.profile_revision.sections
    }
    return tuple(
        CandidateEvidenceProfileRole(
            section_id=section_id,
            label=labels.get(section_id),
        )
        for section_id in detail.item.eligible_section_ids
    )


def build_candidate_evidence_presentation(
    detail: CandidateInboxDetail,
) -> CandidateEvidencePresentation:
    """Build one read-only instructional projection from exact Vitrine state."""

    endpoint = _source_endpoint(detail)
    if endpoint is None:
        return CandidateEvidencePresentation(
            contract_version=CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
            candidate_id=detail.item.candidate_id,
            current_evaluation_id=detail.item.current_evaluation_id,
            evidence_kind=None,
            work_title=detail.item.source_display_label,
            variant_label=None,
            representation_label=None,
            primary_label=detail.item.source_display_label,
            profile_fit=_profile_fit(detail),
            curation_state=detail.item.selected_state,
            representation_family_key=None,
            source_record_id=None,
            source_artifact_id=None,
            representation_kind=None,
        )

    evidence_kind = _evidence_kind(endpoint)
    work_title = _work_title(detail, endpoint)
    variant_label = _variant_label(endpoint, evidence_kind)
    representation_label = _representation_label(endpoint, evidence_kind)
    label_parts = [evidence_kind, work_title]
    if variant_label is not None:
        label_parts.append(variant_label)
    primary_label = " — ".join(label_parts)
    if representation_label is not None:
        primary_label = f"{primary_label} ({representation_label})"

    artifact = endpoint.source_artifact
    return CandidateEvidencePresentation(
        contract_version=CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
        candidate_id=detail.item.candidate_id,
        current_evaluation_id=detail.item.current_evaluation_id,
        evidence_kind=evidence_kind,
        work_title=work_title,
        variant_label=variant_label,
        representation_label=representation_label,
        primary_label=primary_label,
        profile_fit=_profile_fit(detail),
        curation_state=detail.item.selected_state,
        representation_family_key=_representation_family_key(
            endpoint,
            evidence_kind,
        ),
        source_record_id=endpoint.producer_source.source_record_id,
        source_artifact_id=None if artifact is None else artifact.artifact_id,
        representation_kind=(
            None if artifact is None else artifact.representation_kind
        ),
    )


__all__ = [
    "CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION",
    "CandidateEvidencePresentation",
    "CandidateEvidenceProfileRole",
    "build_candidate_evidence_presentation",
]
