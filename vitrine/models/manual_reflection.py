"""Typed/manual Reflection entry provenance with separated authorship."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    require_aware_datetime,
    require_identifier,
    require_positive_int,
    require_record_envelope,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ClassQualifiedStudentRef

REFLECTION_MANUAL_ENTRY_PROVENANCE_RECORD_TYPE: Final[str] = (
    "reflection_manual_entry_provenance"
)
REFLECTION_MANUAL_ENTRY_MODE: Final[str] = "typed_by_authorized_adult"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionManualEntryProvenance:
    """Provenance for a typed/manual Reflection recorded by an adult."""

    manual_entry_provenance_id: str
    reflection_id: str
    reflection_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    subject_link_id: str
    student_reference: ClassQualifiedStudentRef
    entry_mode: str
    recorded_at: datetime
    recorded_by: ActorAttribution
    authority_reference: str
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(
        default=REFLECTION_MANUAL_ENTRY_PROVENANCE_RECORD_TYPE
    )

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            REFLECTION_MANUAL_ENTRY_PROVENANCE_RECORD_TYPE,
        )
        for name in (
            "manual_entry_provenance_id",
            "reflection_id",
            "portfolio_id",
            "portfolio_subject_id",
            "subject_link_id",
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
        if not isinstance(self.student_reference, ClassQualifiedStudentRef):
            raise VitrineModelValidationError(
                "student_reference must be a ClassQualifiedStudentRef."
            )
        if self.entry_mode != REFLECTION_MANUAL_ENTRY_MODE:
            raise VitrineModelValidationError(
                "entry_mode must be 'typed_by_authorized_adult'."
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
    "REFLECTION_MANUAL_ENTRY_MODE",
    "REFLECTION_MANUAL_ENTRY_PROVENANCE_RECORD_TYPE",
    "ReflectionManualEntryProvenance",
]
