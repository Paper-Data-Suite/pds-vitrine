"""Immutable authorship confirmation and paper-Reflection finalization provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    require_aware_datetime,
    require_enum,
    require_identifier,
    require_positive_int,
    require_record_envelope,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ClassQualifiedStudentRef

REFLECTION_AUTHORSHIP_CONFIRMATION_RECORD_TYPE: Final[str] = (
    "reflection_authorship_confirmation"
)
REFLECTION_PAPER_FINALIZATION_RECORD_TYPE: Final[str] = (
    "reflection_paper_finalization"
)
AUTHORSHIP_CONFIRMATION_BASES: Final[frozenset[str]] = frozenset(
    {"teacher_reviewed_original_paper"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionAuthorshipConfirmation:
    """Adult confirmation that selected returned paper is authored by one student."""

    authorship_confirmation_id: str
    issuance_id: str
    portfolio_id: str
    portfolio_subject_id: str
    subject_link_id: str
    student_reference: ClassQualifiedStudentRef
    returned_paper_evidence_ids: tuple[str, ...]
    confirmation_basis: str
    confirmed_at: datetime
    confirmed_by: ActorAttribution
    authority_reference: str
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(
        default=REFLECTION_AUTHORSHIP_CONFIRMATION_RECORD_TYPE
    )

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_AUTHORSHIP_CONFIRMATION_RECORD_TYPE,
        )
        for name in (
            "authorship_confirmation_id",
            "issuance_id",
            "portfolio_id",
            "portfolio_subject_id",
            "subject_link_id",
        ):
            object.__setattr__(
                self,
                name,
                require_identifier(getattr(self, name), name),
            )
        if not isinstance(self.student_reference, ClassQualifiedStudentRef):
            raise VitrineModelValidationError(
                "student_reference must be a ClassQualifiedStudentRef."
            )
        object.__setattr__(
            self,
            "returned_paper_evidence_ids",
            identifier_tuple(
                self.returned_paper_evidence_ids,
                "returned_paper_evidence_ids",
                nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "confirmation_basis",
            require_enum(
                self.confirmation_basis,
                "confirmation_basis",
                AUTHORSHIP_CONFIRMATION_BASES,
            ),
        )
        object.__setattr__(
            self,
            "confirmed_at",
            require_aware_datetime(self.confirmed_at, "confirmed_at"),
        )
        if not isinstance(self.confirmed_by, ActorAttribution):
            raise VitrineModelValidationError(
                "confirmed_by must be an ActorAttribution."
            )
        if self.confirmed_by.actor_kind != "authorized_adult":
            raise VitrineModelValidationError(
                "confirmed_by must be an authorized_adult."
            )
        object.__setattr__(
            self,
            "authority_reference",
            require_text(
                self.authority_reference,
                "authority_reference",
                maximum=500,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionPaperFinalization:
    """Provenance linking one confirmation to its canonical Reflection."""

    paper_finalization_id: str
    authorship_confirmation_id: str
    reflection_id: str
    reflection_revision: int
    returned_paper_evidence_ids: tuple[str, ...]
    student_author: ActorAttribution
    recorded_at: datetime
    recorded_by: ActorAttribution
    authority_reference: str
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=REFLECTION_PAPER_FINALIZATION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_PAPER_FINALIZATION_RECORD_TYPE,
        )
        for name in (
            "paper_finalization_id",
            "authorship_confirmation_id",
            "reflection_id",
        ):
            object.__setattr__(
                self,
                name,
                require_identifier(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "reflection_revision",
            require_positive_int(
                self.reflection_revision,
                "reflection_revision",
            ),
        )
        object.__setattr__(
            self,
            "returned_paper_evidence_ids",
            identifier_tuple(
                self.returned_paper_evidence_ids,
                "returned_paper_evidence_ids",
                nonempty=True,
            ),
        )
        if not isinstance(self.student_author, ActorAttribution):
            raise VitrineModelValidationError(
                "student_author must be an ActorAttribution."
            )
        if self.student_author.actor_kind != "core_student":
            raise VitrineModelValidationError(
                "student_author must be a core_student."
            )
        object.__setattr__(
            self,
            "recorded_at",
            require_aware_datetime(self.recorded_at, "recorded_at"),
        )
        if not isinstance(self.recorded_by, ActorAttribution):
            raise VitrineModelValidationError(
                "recorded_by must be an ActorAttribution."
            )
        if self.recorded_by.actor_kind != "authorized_adult":
            raise VitrineModelValidationError(
                "recorded_by must be an authorized_adult."
            )
        object.__setattr__(
            self,
            "authority_reference",
            require_text(
                self.authority_reference,
                "authority_reference",
                maximum=500,
            ),
        )


__all__ = [
    "AUTHORSHIP_CONFIRMATION_BASES",
    "REFLECTION_AUTHORSHIP_CONFIRMATION_RECORD_TYPE",
    "REFLECTION_PAPER_FINALIZATION_RECORD_TYPE",
    "ReflectionAuthorshipConfirmation",
    "ReflectionPaperFinalization",
]
