"""Versioned Portfolio Profile models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    lower_key_tuple,
    require_aware_datetime,
    require_date,
    require_enum,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_school_year_value,
    require_text,
    text_tuple,
    tuple_of,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ProfileRevisionRef

PROFILE_PURPOSE_KINDS: Final[frozenset[str]] = frozenset(
    {"improvement", "showcase", "parent_guardian_conference", "regulated"}
)
SECTION_OBLIGATIONS: Final[frozenset[str]] = frozenset(
    {"required", "optional", "conditional", "prohibited"}
)
REFLECTION_REQUIREMENTS: Final[frozenset[str]] = frozenset(
    {"none", "optional", "required"}
)
AUDIENCE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "student",
        "teacher_internal",
        "parent_guardian",
        "institutional_reviewer",
        "external_reviewer",
        "regulated_submission",
        "public",
    }
)

PROFILE_FAMILY_RECORD_TYPE: Final[str] = "portfolio_profile_family"
PROFILE_REVISION_RECORD_TYPE: Final[str] = "portfolio_profile_revision"
PROFILE_BINDING_RECORD_TYPE: Final[str] = "portfolio_profile_binding"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileApplicability:
    jurisdiction: str | None = None
    institution_id: str | None = None
    program_id: str | None = None
    school_years: tuple[str, ...] = ()
    cohorts: tuple[str, ...] = ()
    grade_bands: tuple[str, ...] = ()
    content_areas: tuple[str, ...] = ()
    pathway: str | None = None
    effective_from: date | None = None
    effective_through: date | None = None
    authority_reference: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("jurisdiction", "pathway", "authority_reference"):
            object.__setattr__(
                self,
                field_name,
                require_optional_text(getattr(self, field_name), field_name, maximum=500),
            )
        for field_name in ("institution_id", "program_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, require_identifier(value, field_name)
                )
        object.__setattr__(
            self,
            "school_years",
            tuple_of(
                self.school_years,
                "school_years",
                require_school_year_value,
                unique=True,
            ),
        )
        object.__setattr__(
            self, "cohorts", identifier_tuple(self.cohorts, "cohorts")
        )
        object.__setattr__(
            self, "grade_bands", text_tuple(self.grade_bands, "grade_bands")
        )
        object.__setattr__(
            self,
            "content_areas",
            lower_key_tuple(self.content_areas, "content_areas"),
        )
        if self.effective_from is not None:
            object.__setattr__(
                self,
                "effective_from",
                require_date(self.effective_from, "effective_from"),
            )
        if self.effective_through is not None:
            object.__setattr__(
                self,
                "effective_through",
                require_date(self.effective_through, "effective_through"),
            )
        if (
            self.effective_from is not None
            and self.effective_through is not None
            and self.effective_through < self.effective_from
        ):
            raise VitrineModelValidationError("effective_through must not precede effective_from.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileSectionDefinition:
    section_id: str
    label: str
    purpose: str
    order: int
    obligation: str
    minimum_placements: int
    maximum_placements: int | None
    allowed_candidate_kinds: tuple[str, ...]
    required_relationship_kinds: tuple[str, ...]
    reflection_requirement: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "section_id", require_identifier(self.section_id, "section_id")
        )
        object.__setattr__(self, "label", require_text(self.label, "label", maximum=200))
        object.__setattr__(
            self, "purpose", require_text(self.purpose, "purpose", maximum=1000)
        )
        object.__setattr__(self, "order", require_positive_int(self.order, "order"))
        object.__setattr__(
            self,
            "obligation",
            require_enum(self.obligation, "obligation", SECTION_OBLIGATIONS),
        )
        if isinstance(self.minimum_placements, bool) or not isinstance(
            self.minimum_placements, int
        ) or self.minimum_placements < 0:
            raise VitrineModelValidationError("minimum_placements must be a nonnegative integer.")
        if self.maximum_placements is not None:
            if isinstance(self.maximum_placements, bool) or not isinstance(
                self.maximum_placements, int
            ) or self.maximum_placements < 0:
                raise VitrineModelValidationError("maximum_placements must be nonnegative or null.")
            if self.maximum_placements < self.minimum_placements:
                raise VitrineModelValidationError(
                    "maximum_placements must not be less than minimum_placements."
                )
        if self.obligation == "prohibited":
            if self.minimum_placements != 0 or self.maximum_placements != 0:
                raise VitrineModelValidationError(
                    "prohibited sections must set both placement cardinalities to zero."
                )
        object.__setattr__(
            self,
            "allowed_candidate_kinds",
            lower_key_tuple(
                self.allowed_candidate_kinds,
                "allowed_candidate_kinds",
                nonempty=self.obligation != "prohibited",
            ),
        )
        object.__setattr__(
            self,
            "required_relationship_kinds",
            lower_key_tuple(
                self.required_relationship_kinds, "required_relationship_kinds"
            ),
        )
        object.__setattr__(
            self,
            "reflection_requirement",
            require_enum(
                self.reflection_requirement,
                "reflection_requirement",
                REFLECTION_REQUIREMENTS,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileAudienceRule:
    audience_rule_id: str
    audience_class: str
    purpose: str
    allowed_content_classes: tuple[str, ...]
    prohibited_content_classes: tuple[str, ...]
    required_review_classes: tuple[str, ...]
    presentation_class: str
    retention_policy_reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "audience_rule_id",
            require_identifier(self.audience_rule_id, "audience_rule_id"),
        )
        object.__setattr__(
            self,
            "audience_class",
            require_enum(self.audience_class, "audience_class", AUDIENCE_CLASSES),
        )
        object.__setattr__(
            self, "purpose", require_text(self.purpose, "purpose", maximum=1000)
        )
        for field_name in (
            "allowed_content_classes",
            "prohibited_content_classes",
            "required_review_classes",
        ):
            object.__setattr__(
                self,
                field_name,
                lower_key_tuple(getattr(self, field_name), field_name),
            )
        overlap = set(self.allowed_content_classes) & set(
            self.prohibited_content_classes
        )
        if overlap:
            raise VitrineModelValidationError(
                "allowed_content_classes and prohibited_content_classes overlap."
            )
        object.__setattr__(
            self,
            "presentation_class",
            require_text(self.presentation_class, "presentation_class", maximum=128),
        )
        object.__setattr__(
            self,
            "retention_policy_reference",
            require_optional_text(
                self.retention_policy_reference,
                "retention_policy_reference",
                maximum=500,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileFamily:
    profile_family_id: str
    label: str
    purpose_kind: str
    created_at: datetime
    created_by: ActorAttribution
    description: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_FAMILY_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PROFILE_FAMILY_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "profile_family_id",
            require_identifier(self.profile_family_id, "profile_family_id"),
        )
        object.__setattr__(self, "label", require_text(self.label, "label", maximum=200))
        object.__setattr__(
            self,
            "purpose_kind",
            require_enum(self.purpose_kind, "purpose_kind", PROFILE_PURPOSE_KINDS),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "description",
            require_optional_text(self.description, "description", maximum=2000),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileRevision:
    portfolio_profile_id: str
    profile_revision: int
    profile_family_id: str | None
    predecessor_revision: int | None
    label: str
    purpose_kind: str
    applicability: ProfileApplicability
    sections: tuple[ProfileSectionDefinition, ...]
    audience_rules: tuple[ProfileAudienceRule, ...]
    created_at: datetime
    created_by: ActorAttribution
    source_authority_references: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_REVISION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PROFILE_REVISION_RECORD_TYPE
        )
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
        if self.profile_family_id is not None:
            object.__setattr__(
                self,
                "profile_family_id",
                require_identifier(self.profile_family_id, "profile_family_id"),
            )
        if self.predecessor_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_revision, "predecessor_revision"
            )
            if predecessor >= self.profile_revision:
                raise VitrineModelValidationError(
                    "predecessor_revision must be lower than profile_revision."
                )
            object.__setattr__(self, "predecessor_revision", predecessor)
        object.__setattr__(self, "label", require_text(self.label, "label", maximum=200))
        object.__setattr__(
            self,
            "purpose_kind",
            require_enum(self.purpose_kind, "purpose_kind", PROFILE_PURPOSE_KINDS),
        )
        if not isinstance(self.applicability, ProfileApplicability):
            raise VitrineModelValidationError("applicability must be a ProfileApplicability.")
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "audience_rules", tuple(self.audience_rules))
        if not self.sections:
            raise VitrineModelValidationError("sections must not be empty.")
        if any(not isinstance(item, ProfileSectionDefinition) for item in self.sections):
            raise VitrineModelValidationError("sections must contain ProfileSectionDefinition values.")
        if any(not isinstance(item, ProfileAudienceRule) for item in self.audience_rules):
            raise VitrineModelValidationError("audience_rules must contain ProfileAudienceRule values.")
        if len({item.section_id for item in self.sections}) != len(self.sections):
            raise VitrineModelValidationError("section IDs must be unique within a Profile Revision.")
        if len({item.order for item in self.sections}) != len(self.sections):
            raise VitrineModelValidationError("section order values must be unique.")
        if tuple(sorted(self.sections, key=lambda item: item.order)) != self.sections:
            raise VitrineModelValidationError("sections must be stored in ascending explicit order.")
        if len({item.audience_rule_id for item in self.audience_rules}) != len(
            self.audience_rules
        ):
            raise VitrineModelValidationError("audience rule IDs must be unique.")
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "source_authority_references",
            text_tuple(
                self.source_authority_references, "source_authority_references"
            ),
        )
        object.__setattr__(
            self,
            "known_limitations",
            text_tuple(self.known_limitations, "known_limitations"),
        )

    @property
    def reference(self) -> ProfileRevisionRef:
        return ProfileRevisionRef(
            portfolio_profile_id=self.portfolio_profile_id,
            profile_revision=self.profile_revision,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileBinding:
    profile_binding_id: str
    portfolio_id: str
    profile_revision: ProfileRevisionRef
    bound_at: datetime
    bound_by: ActorAttribution
    binding_reason: str | None = None
    predecessor_binding_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_BINDING_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PROFILE_BINDING_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "profile_binding_id",
            require_identifier(self.profile_binding_id, "profile_binding_id"),
        )
        object.__setattr__(
            self, "portfolio_id", require_identifier(self.portfolio_id, "portfolio_id")
        )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be a ProfileRevisionRef.")
        object.__setattr__(
            self, "bound_at", require_aware_datetime(self.bound_at, "bound_at")
        )
        if not isinstance(self.bound_by, ActorAttribution):
            raise VitrineModelValidationError("bound_by must be an ActorAttribution.")
        object.__setattr__(
            self,
            "binding_reason",
            require_optional_text(self.binding_reason, "binding_reason", maximum=1000),
        )
        if self.predecessor_binding_id is not None:
            predecessor = require_identifier(
                self.predecessor_binding_id, "predecessor_binding_id"
            )
            if predecessor == self.profile_binding_id:
                raise VitrineModelValidationError(
                    "predecessor_binding_id must differ from profile_binding_id."
                )
            object.__setattr__(self, "predecessor_binding_id", predecessor)
