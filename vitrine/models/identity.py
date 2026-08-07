"""Portfolio, subject, and shared reference models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    require_aware_datetime,
    require_enum,
    require_identifier,
    require_lower_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_school_year_value,
    require_sha256,
)
from .errors import VitrineModelValidationError

ACTOR_KINDS: Final[frozenset[str]] = frozenset(
    {"core_student", "authorized_adult", "system", "external_actor"}
)
CONFIRMATION_BASES: Final[frozenset[str]] = frozenset(
    {"teacher_confirmed", "institution_confirmed", "authorized_import"}
)

PORTFOLIO_RECORD_TYPE: Final[str] = "portfolio"
PORTFOLIO_SUBJECT_RECORD_TYPE: Final[str] = "portfolio_subject"
SUBJECT_LINK_RECORD_TYPE: Final[str] = "portfolio_subject_class_link"


@dataclass(frozen=True, slots=True, kw_only=True)
class VitrineRecordRef:
    record_type: str
    record_id: str
    schema_version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "record_type", require_lower_identifier(self.record_type, "record_type")
        )
        object.__setattr__(
            self, "record_id", require_identifier(self.record_id, "record_id")
        )
        if self.schema_version is not None:
            object.__setattr__(
                self,
                "schema_version",
                require_identifier(self.schema_version, "schema_version"),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ActorAttribution:
    actor_kind: str
    actor_id: str
    owning_system: str
    display_label_snapshot: str | None = None
    role_snapshot: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "actor_kind",
            require_enum(self.actor_kind, "actor_kind", ACTOR_KINDS),
        )
        object.__setattr__(
            self, "actor_id", require_identifier(self.actor_id, "actor_id")
        )
        object.__setattr__(
            self,
            "owning_system",
            require_lower_identifier(self.owning_system, "owning_system"),
        )
        object.__setattr__(
            self,
            "display_label_snapshot",
            require_optional_text(
                self.display_label_snapshot, "display_label_snapshot", maximum=200
            ),
        )
        object.__setattr__(
            self,
            "role_snapshot",
            require_optional_text(self.role_snapshot, "role_snapshot", maximum=200),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DigestReference:
    algorithm: str = "sha256"
    value: str

    def __post_init__(self) -> None:
        if self.algorithm != "sha256":
            raise VitrineModelValidationError("algorithm must be 'sha256'.")
        object.__setattr__(self, "value", require_sha256(self.value, "value"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRevisionRef:
    portfolio_profile_id: str
    profile_revision: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "portfolio_profile_id",
            require_identifier(self.portfolio_profile_id, "portfolio_profile_id"),
        )
        object.__setattr__(
            self,
            "profile_revision",
            require_positive_int(self.profile_revision, "profile_revision"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositionRevisionRef:
    portfolio_id: str
    composition_revision: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "portfolio_id", require_identifier(self.portfolio_id, "portfolio_id")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEditionRef:
    snapshot_series_id: str
    edition_number: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_series_id",
            require_identifier(self.snapshot_series_id, "snapshot_series_id"),
        )
        object.__setattr__(
            self,
            "edition_number",
            require_positive_int(self.edition_number, "edition_number"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassQualifiedStudentRef:
    class_id: str
    student_id: str
    school_year: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "class_id", require_identifier(self.class_id, "class_id")
        )
        object.__setattr__(
            self, "student_id", require_identifier(self.student_id, "student_id")
        )
        object.__setattr__(
            self, "school_year", require_school_year_value(self.school_year)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Portfolio:
    portfolio_id: str
    portfolio_subject_id: str
    created_at: datetime
    created_by: ActorAttribution
    title_snapshot: str | None = None
    description_snapshot: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PORTFOLIO_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PORTFOLIO_RECORD_TYPE
        )
        object.__setattr__(
            self, "portfolio_id", require_identifier(self.portfolio_id, "portfolio_id")
        )
        object.__setattr__(
            self,
            "portfolio_subject_id",
            require_identifier(self.portfolio_subject_id, "portfolio_subject_id"),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "title_snapshot",
            require_optional_text(self.title_snapshot, "title_snapshot", maximum=300),
        )
        object.__setattr__(
            self,
            "description_snapshot",
            require_optional_text(
                self.description_snapshot, "description_snapshot", maximum=2000
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubject:
    portfolio_subject_id: str
    created_at: datetime
    created_by: ActorAttribution
    display_name_snapshot: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PORTFOLIO_SUBJECT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PORTFOLIO_SUBJECT_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "portfolio_subject_id",
            require_identifier(self.portfolio_subject_id, "portfolio_subject_id"),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "display_name_snapshot",
            require_optional_text(
                self.display_name_snapshot, "display_name_snapshot", maximum=300
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubjectClassLink:
    subject_link_id: str
    portfolio_subject_id: str
    student_reference: ClassQualifiedStudentRef
    confirmed_at: datetime
    confirmed_by: ActorAttribution
    confirmation_basis: str
    authority_reference: str | None = None
    predecessor_link_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SUBJECT_LINK_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SUBJECT_LINK_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "subject_link_id",
            require_identifier(self.subject_link_id, "subject_link_id"),
        )
        object.__setattr__(
            self,
            "portfolio_subject_id",
            require_identifier(self.portfolio_subject_id, "portfolio_subject_id"),
        )
        if not isinstance(self.student_reference, ClassQualifiedStudentRef):
            raise VitrineModelValidationError("student_reference must be a ClassQualifiedStudentRef.")
        object.__setattr__(
            self,
            "confirmed_at",
            require_aware_datetime(self.confirmed_at, "confirmed_at"),
        )
        if not isinstance(self.confirmed_by, ActorAttribution):
            raise VitrineModelValidationError("confirmed_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "confirmation_basis",
            require_enum(
                self.confirmation_basis, "confirmation_basis", CONFIRMATION_BASES
            ),
        )
        object.__setattr__(
            self,
            "authority_reference",
            require_optional_text(
                self.authority_reference, "authority_reference", maximum=500
            ),
        )
        if self.predecessor_link_id is not None:
            predecessor = require_identifier(
                self.predecessor_link_id, "predecessor_link_id"
            )
            if predecessor == self.subject_link_id:
                raise VitrineModelValidationError("predecessor_link_id must differ from subject_link_id.")
            object.__setattr__(self, "predecessor_link_id", predecessor)
