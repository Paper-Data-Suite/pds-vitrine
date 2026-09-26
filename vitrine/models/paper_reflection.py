"""Immutable paper-Reflection issuance and response-page records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    require_aware_datetime,
    require_date,
    require_enum,
    require_identifier,
    require_positive_int,
    require_record_envelope,
    require_relative_path,
    require_sha256,
    require_text,
)
from .curation_workflow import REFLECTION_SCOPES, CurationTargetRef
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ClassQualifiedStudentRef, ProfileRevisionRef

REFLECTION_PROMPT_ISSUANCE_RECORD_TYPE: Final[str] = "reflection_prompt_issuance"
REFLECTION_RESPONSE_PAGE_RECORD_TYPE: Final[str] = "reflection_response_page"


def _target_refs(
    values: tuple[CurationTargetRef, ...], field_name: str
) -> tuple[CurationTargetRef, ...]:
    items = tuple(values)
    if not items:
        raise VitrineModelValidationError(f"{field_name} must not be empty.")
    if any(not isinstance(item, CurationTargetRef) for item in items):
        raise VitrineModelValidationError(
            f"{field_name} must contain CurationTargetRef values."
        )
    return items


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionPromptIssuance:
    """Frozen context for one student paper-Reflection packet."""

    issuance_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    prompt_snapshot: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    subject_link_id: str
    student_reference: ClassQualifiedStudentRef
    response_page_ids: tuple[str, ...]
    issued_at: datetime
    issued_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=REFLECTION_PROMPT_ISSUANCE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_PROMPT_ISSUANCE_RECORD_TYPE,
        )
        for name in (
            "issuance_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "reflection_requirement_id",
            "prompt_id",
            "subject_link_id",
        ):
            object.__setattr__(
                self, name, require_identifier(getattr(self, name), name)
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError(
                "profile_revision must be ProfileRevisionRef."
            )
        object.__setattr__(
            self,
            "prompt_version",
            require_text(self.prompt_version, "prompt_version", maximum=128),
        )
        object.__setattr__(
            self,
            "prompt_snapshot",
            require_text(self.prompt_snapshot, "prompt_snapshot", maximum=4000),
        )
        object.__setattr__(
            self,
            "target_scope",
            require_enum(self.target_scope, "target_scope", REFLECTION_SCOPES),
        )
        object.__setattr__(
            self,
            "target_references",
            _target_refs(self.target_references, "target_references"),
        )
        if not isinstance(self.student_reference, ClassQualifiedStudentRef):
            raise VitrineModelValidationError(
                "student_reference must be ClassQualifiedStudentRef."
            )
        page_ids = identifier_tuple(
            self.response_page_ids, "response_page_ids", nonempty=True
        )
        if len(page_ids) != len(set(page_ids)):
            raise VitrineModelValidationError(
                "response_page_ids must contain unique page identities."
            )
        object.__setattr__(self, "response_page_ids", page_ids)
        object.__setattr__(
            self, "issued_at", require_aware_datetime(self.issued_at, "issued_at")
        )
        if not isinstance(self.issued_by, ActorAttribution):
            raise VitrineModelValidationError(
                "issued_by must be ActorAttribution."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionResponsePage:
    """One immutable routable page belonging to a Reflection issuance."""

    response_page_id: str
    issuance_id: str
    class_id: str
    work_id: str
    route_id: str
    logical_page_number: int
    total_pages: int
    created_at: datetime
    created_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=REFLECTION_RESPONSE_PAGE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_RESPONSE_PAGE_RECORD_TYPE,
        )
        for name in (
            "response_page_id",
            "issuance_id",
            "class_id",
            "work_id",
            "route_id",
        ):
            object.__setattr__(
                self, name, require_identifier(getattr(self, name), name)
            )
        page_number = require_positive_int(
            self.logical_page_number, "logical_page_number"
        )
        total_pages = require_positive_int(self.total_pages, "total_pages")
        if page_number > total_pages:
            raise VitrineModelValidationError(
                "logical_page_number must not exceed total_pages."
            )
        object.__setattr__(self, "logical_page_number", page_number)
        object.__setattr__(self, "total_pages", total_pages)
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError(
                "created_by must be ActorAttribution."
            )


REFLECTION_RETURNED_PAPER_EVIDENCE_RECORD_TYPE: Final[str] = (
    "reflection_returned_paper_evidence"
)
REFLECTION_RETURNED_PAPER_EVIDENCE_KIND: Final[str] = "core_retained_source_page"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionReturnedPaperEvidence:
    """Immutable evidence that one routed page came from one Core-retained scan."""

    returned_paper_evidence_id: str
    issuance_id: str
    response_page_id: str
    route_id: str
    class_id: str
    work_id: str
    source_scan_id: str
    source_filename: str
    source_page_number: int
    retained_source_relative_path: str
    source_sha256: str
    intake_timestamp: datetime
    intake_date: date
    evidence_kind: str = field(default=REFLECTION_RETURNED_PAPER_EVIDENCE_KIND)
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(
        default=REFLECTION_RETURNED_PAPER_EVIDENCE_RECORD_TYPE
    )

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_RETURNED_PAPER_EVIDENCE_RECORD_TYPE,
        )
        for name in (
            "returned_paper_evidence_id",
            "issuance_id",
            "response_page_id",
            "route_id",
            "class_id",
            "work_id",
            "source_scan_id",
        ):
            object.__setattr__(
                self,
                name,
                require_identifier(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "source_filename",
            require_text(self.source_filename, "source_filename", maximum=512),
        )
        object.__setattr__(
            self,
            "source_page_number",
            require_positive_int(
                self.source_page_number,
                "source_page_number",
            ),
        )
        object.__setattr__(
            self,
            "retained_source_relative_path",
            require_relative_path(
                self.retained_source_relative_path,
                "retained_source_relative_path",
            ),
        )
        object.__setattr__(
            self,
            "source_sha256",
            require_sha256(self.source_sha256, "source_sha256"),
        )
        object.__setattr__(
            self,
            "intake_timestamp",
            require_aware_datetime(
                self.intake_timestamp,
                "intake_timestamp",
            ),
        )
        object.__setattr__(
            self,
            "intake_date",
            require_date(self.intake_date, "intake_date"),
        )
        if self.evidence_kind != REFLECTION_RETURNED_PAPER_EVIDENCE_KIND:
            raise VitrineModelValidationError(
                "evidence_kind must be 'core_retained_source_page'."
            )


__all__ = [
    "REFLECTION_PROMPT_ISSUANCE_RECORD_TYPE",
    "REFLECTION_RESPONSE_PAGE_RECORD_TYPE",
    "REFLECTION_RETURNED_PAPER_EVIDENCE_KIND",
    "REFLECTION_RETURNED_PAPER_EVIDENCE_RECORD_TYPE",
    "ReflectionPromptIssuance",
    "ReflectionResponsePage",
    "ReflectionReturnedPaperEvidence",
]
