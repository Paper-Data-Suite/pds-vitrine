"""Frozen Quillan live-adapter contract identities for Vitrine issue #60.

Slice 0 records only cross-boundary identities and deterministic opaque source-ID
construction. It does not import Quillan, read producer state, project Candidates,
authorize Artifacts, or resolve producer-native paths.
"""

from __future__ import annotations

import hashlib
from typing import Final

from vitrine.snapshot_materialization import SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE

QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION: Final[str] = "vitrine_candidate_projection_v1"

QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND: Final[str] = "quillan:review_summary"
QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND: Final[str] = (
    "quillan:selected_student_work"
)
QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND: Final[str] = "quillan:feedback_pdf"
QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND: Final[str] = (
    "quillan:feedback_markdown"
)

QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND: Final[str] = "assessment_summary"
QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE: Final[str] = (
    "application/vnd.pds.vitrine.quillan-review-summary+json"
)
QUILLAN_STUDENT_WORK_ARTIFACT_KIND: Final[str] = "original_student_work"
QUILLAN_FEEDBACK_ARTIFACT_KIND: Final[str] = "rendered_feedback"

QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE: Final[str] = (
    SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE
)
QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES: Final[tuple[str, ...]] = (
    "image/jpeg",
    "image/png",
    "image/tiff",
)
QUILLAN_FEEDBACK_PDF_MEDIA_TYPE: Final[str] = "application/pdf"
QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE: Final[str] = "text/markdown; charset=utf-8"

QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID: Final[str] = (
    "vitrine_quillan_authorized_artifact_source_provider"
)
QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION: Final[str] = (
    "vitrine_quillan_authorized_artifact_source_provider_v1"
)

QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY: Final[
    tuple[str, str, str, str, str]
] = (
    "quillan",
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
)
QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY: Final[
    tuple[str, str, str, str, str]
] = (
    "quillan",
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
)
QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY: Final[
    tuple[str, str, str, str, str]
] = (
    "quillan",
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
)

_QUILLAN_SOURCE_ID_CONTRACT: Final[str] = "vitrine_quillan_source_identity_v1"


def _identity_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{field_name} must be nonempty text without NUL.")
    return value


def _length_delimited_sha256(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        encoded = part.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def _opaque_source_id(prefix: str, parts: tuple[str, ...]) -> str:
    checked = tuple(
        _identity_text(value, f"identity_parts[{index}]")
        for index, value in enumerate(parts)
    )
    return f"{prefix}_{_length_delimited_sha256(checked)}"


def quillan_review_source_id(*, class_id: str, work_id: str, student_id: str) -> str:
    """Return one deterministic Vitrine-owned identity for a Quillan review summary."""

    return _opaque_source_id(
        "quillan_review",
        (
            _QUILLAN_SOURCE_ID_CONTRACT,
            "quillan",
            _identity_text(class_id, "class_id"),
            _identity_text(work_id, "work_id"),
            _identity_text(student_id, "student_id"),
            QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
        ),
    )


def quillan_evidence_source_id(
    *,
    class_id: str,
    work_id: str,
    student_id: str,
    evidence_id: str,
) -> str:
    """Return one deterministic Vitrine-owned identity for selected student work."""

    return _opaque_source_id(
        "quillan_evidence",
        (
            _QUILLAN_SOURCE_ID_CONTRACT,
            "quillan",
            _identity_text(class_id, "class_id"),
            _identity_text(work_id, "work_id"),
            _identity_text(student_id, "student_id"),
            QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
            _identity_text(evidence_id, "evidence_id"),
        ),
    )


def quillan_feedback_source_id(
    *,
    class_id: str,
    work_id: str,
    student_id: str,
    artifact_request_kind: str,
) -> str:
    """Return one deterministic Vitrine-owned identity for Quillan feedback."""

    if artifact_request_kind == "feedback_pdf":
        source_kind = QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND
    elif artifact_request_kind == "feedback_markdown":
        source_kind = QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND
    else:
        raise ValueError(
            "artifact_request_kind must be feedback_pdf or feedback_markdown."
        )
    return _opaque_source_id(
        "quillan_feedback",
        (
            _QUILLAN_SOURCE_ID_CONTRACT,
            "quillan",
            _identity_text(class_id, "class_id"),
            _identity_text(work_id, "work_id"),
            _identity_text(student_id, "student_id"),
            source_kind,
            artifact_request_kind,
        ),
    )


__all__ = [
    "QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_FAMILY_ID",
    "QUILLAN_AUTHORIZED_ARTIFACT_SOURCE_PROVIDER_VERSION",
    "QUILLAN_FEEDBACK_ARTIFACT_KIND",
    "QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE",
    "QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND",
    "QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY",
    "QUILLAN_FEEDBACK_PDF_MEDIA_TYPE",
    "QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND",
    "QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY",
    "QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION",
    "QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND",
    "QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE",
    "QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND",
    "QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND",
    "QUILLAN_STUDENT_WORK_ARTIFACT_KIND",
    "QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES",
    "QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE",
    "QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY",
    "quillan_evidence_source_id",
    "quillan_feedback_source_id",
    "quillan_review_source_id",
]
