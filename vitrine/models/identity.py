"""Portfolio, subject, and shared reference models."""

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
    require_lower_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_school_year_value,
    require_sha256,
    require_text,
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
SUBJECT_DISPLAY_SNAPSHOT_RECORD_TYPE: Final[str] = (
    "portfolio_subject_display_snapshot"
)
IDENTITY_DECISION_RECORD_TYPE: Final[str] = "portfolio_subject_identity_decision"
SUBJECT_IDENTITY_TRANSITION_RECORD_TYPE: Final[str] = (
    "portfolio_subject_identity_transition"
)

IDENTITY_DECISION_TYPES: Final[frozenset[str]] = frozenset(
    {
        "create_subject",
        "confirm_link",
        "invalidate_link",
        "supersede_link",
        "merge_subjects",
        "split_subject",
        "invalidate_subject",
        "supersede_subject",
    }
)
SUBJECT_TRANSITION_TYPES: Final[frozenset[str]] = frozenset(
    {"merge", "split", "invalidate", "supersede"}
)
IDENTITY_BASIS_TYPES: Final[frozenset[str]] = frozenset(
    {
        "direct_teacher_knowledge",
        "authorized_institutional_crosswalk",
        "verified_sis_information",
        "student_confirmation",
        "parent_or_guardian_confirmation",
        "transfer_or_enrollment_record",
        "migration_from_reviewed_source",
        "other_authorized_basis",
    }
)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubjectDisplaySnapshot:
    display_snapshot_id: str
    subject_link_id: str
    student_reference: ClassQualifiedStudentRef
    first_name: str
    last_name: str
    display_name: str
    captured_at: datetime
    preferred_name: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SUBJECT_DISPLAY_SNAPSHOT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            SUBJECT_DISPLAY_SNAPSHOT_RECORD_TYPE,
        )
        object.__setattr__(
            self,
            "display_snapshot_id",
            require_identifier(self.display_snapshot_id, "display_snapshot_id"),
        )
        object.__setattr__(
            self,
            "subject_link_id",
            require_identifier(self.subject_link_id, "subject_link_id"),
        )
        if not isinstance(self.student_reference, ClassQualifiedStudentRef):
            raise VitrineModelValidationError(
                "student_reference must be a ClassQualifiedStudentRef."
            )
        for field_name in ("first_name", "last_name", "display_name"):
            object.__setattr__(
                self,
                field_name,
                require_text(getattr(self, field_name), field_name, maximum=300),
            )
        object.__setattr__(
            self,
            "preferred_name",
            require_optional_text(
                self.preferred_name, "preferred_name", maximum=300
            ),
        )
        expected_display = f"{self.preferred_name or self.first_name} {self.last_name}"
        if self.display_name != expected_display:
            raise VitrineModelValidationError(
                "display_name must be the deterministic preferred-or-first name plus last name."
            )
        object.__setattr__(
            self,
            "captured_at",
            require_aware_datetime(self.captured_at, "captured_at"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubjectIdentityDecision:
    identity_decision_id: str
    decision_type: str
    subject_ids: tuple[str, ...]
    subject_link_ids: tuple[str, ...]
    decided_at: datetime
    decided_by: ActorAttribution
    authority_source: str
    basis_type: str
    basis_summary: str
    external_basis_ref: str | None = None
    supersedes_decision_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=IDENTITY_DECISION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, IDENTITY_DECISION_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "identity_decision_id",
            require_identifier(self.identity_decision_id, "identity_decision_id"),
        )
        object.__setattr__(
            self,
            "decision_type",
            require_enum(
                self.decision_type, "decision_type", IDENTITY_DECISION_TYPES
            ),
        )
        object.__setattr__(
            self,
            "subject_ids",
            identifier_tuple(self.subject_ids, "subject_ids"),
        )
        object.__setattr__(
            self,
            "subject_link_ids",
            identifier_tuple(self.subject_link_ids, "subject_link_ids"),
        )
        if not self.subject_ids and not self.subject_link_ids:
            raise VitrineModelValidationError(
                "identity decision must reference at least one subject or link."
            )
        object.__setattr__(
            self,
            "decided_at",
            require_aware_datetime(self.decided_at, "decided_at"),
        )
        if not isinstance(self.decided_by, ActorAttribution):
            raise VitrineModelValidationError(
                "decided_by must be an ActorAttribution."
            )
        object.__setattr__(
            self,
            "authority_source",
            require_text(self.authority_source, "authority_source", maximum=500),
        )
        object.__setattr__(
            self,
            "basis_type",
            require_enum(self.basis_type, "basis_type", IDENTITY_BASIS_TYPES),
        )
        object.__setattr__(
            self,
            "basis_summary",
            require_text(self.basis_summary, "basis_summary", maximum=1000),
        )
        object.__setattr__(
            self,
            "external_basis_ref",
            require_optional_text(
                self.external_basis_ref, "external_basis_ref", maximum=500
            ),
        )
        if self.supersedes_decision_id is not None:
            predecessor = require_identifier(
                self.supersedes_decision_id, "supersedes_decision_id"
            )
            if predecessor == self.identity_decision_id:
                raise VitrineModelValidationError(
                    "supersedes_decision_id must differ from identity_decision_id."
                )
            object.__setattr__(self, "supersedes_decision_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectAssociationAllocation:
    predecessor_link_ids: tuple[str, ...]
    successor_subject_id: str
    successor_link_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "predecessor_link_ids",
            identifier_tuple(
                self.predecessor_link_ids,
                "predecessor_link_ids",
                nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "successor_subject_id",
            require_identifier(self.successor_subject_id, "successor_subject_id"),
        )
        object.__setattr__(
            self,
            "successor_link_id",
            require_identifier(self.successor_link_id, "successor_link_id"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubjectIdentityTransition:
    subject_identity_transition_id: str
    transition_type: str
    identity_decision_id: str
    predecessor_subject_ids: tuple[str, ...]
    successor_subject_ids: tuple[str, ...]
    association_allocations: tuple[SubjectAssociationAllocation, ...]
    affected_portfolio_ids: tuple[str, ...]
    supersedes_transition_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SUBJECT_IDENTITY_TRANSITION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            SUBJECT_IDENTITY_TRANSITION_RECORD_TYPE,
        )
        object.__setattr__(
            self,
            "subject_identity_transition_id",
            require_identifier(
                self.subject_identity_transition_id,
                "subject_identity_transition_id",
            ),
        )
        object.__setattr__(
            self,
            "transition_type",
            require_enum(
                self.transition_type,
                "transition_type",
                SUBJECT_TRANSITION_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "identity_decision_id",
            require_identifier(self.identity_decision_id, "identity_decision_id"),
        )
        object.__setattr__(
            self,
            "predecessor_subject_ids",
            identifier_tuple(
                self.predecessor_subject_ids,
                "predecessor_subject_ids",
                nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "successor_subject_ids",
            identifier_tuple(self.successor_subject_ids, "successor_subject_ids"),
        )
        object.__setattr__(
            self,
            "association_allocations",
            tuple(self.association_allocations),
        )
        if any(
            not isinstance(item, SubjectAssociationAllocation)
            for item in self.association_allocations
        ):
            raise VitrineModelValidationError(
                "association_allocations must contain SubjectAssociationAllocation values."
            )
        object.__setattr__(
            self,
            "affected_portfolio_ids",
            identifier_tuple(self.affected_portfolio_ids, "affected_portfolio_ids"),
        )
        if self.transition_type == "merge":
            if len(self.predecessor_subject_ids) < 2 or len(self.successor_subject_ids) != 1:
                raise VitrineModelValidationError(
                    "merge requires at least two predecessors and exactly one successor."
                )
        elif self.transition_type == "split":
            if len(self.predecessor_subject_ids) != 1 or len(self.successor_subject_ids) < 2:
                raise VitrineModelValidationError(
                    "split requires exactly one predecessor and at least two successors."
                )
        elif self.transition_type == "invalidate":
            if self.successor_subject_ids:
                raise VitrineModelValidationError(
                    "invalidate must not identify successor subjects."
                )
        elif self.transition_type == "supersede":
            if len(self.successor_subject_ids) != 1:
                raise VitrineModelValidationError(
                    "supersede requires exactly one successor subject."
                )
        if set(self.predecessor_subject_ids) & set(self.successor_subject_ids):
            raise VitrineModelValidationError(
                "a subject cannot be its own predecessor and successor."
            )
        if self.supersedes_transition_id is not None:
            predecessor = require_identifier(
                self.supersedes_transition_id, "supersedes_transition_id"
            )
            if predecessor == self.subject_identity_transition_id:
                raise VitrineModelValidationError(
                    "supersedes_transition_id must differ from transition identity."
                )
            object.__setattr__(self, "supersedes_transition_id", predecessor)
