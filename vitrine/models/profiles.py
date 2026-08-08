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

PROFILE_REQUIREMENT_RECORD_TYPE: Final[str] = "portfolio_profile_requirement"
PROFILE_LIFECYCLE_EVENT_RECORD_TYPE: Final[str] = "portfolio_profile_lifecycle_event"
PROFILE_OVERLAY_RECORD_TYPE: Final[str] = "portfolio_profile_overlay_revision"
PROFILE_COMPOSITION_RECORD_TYPE: Final[str] = "portfolio_profile_composition"
PROFILE_MIGRATION_RECORD_TYPE: Final[str] = "portfolio_profile_migration"

PROFILE_REQUIREMENT_KINDS: Final[frozenset[str]] = frozenset(
    {"section", "selection", "reflection", "audience", "approval", "output"}
)
PROFILE_REQUIREMENT_OBLIGATIONS: Final[frozenset[str]] = frozenset(
    {"required", "optional", "conditional", "prohibited"}
)
PROFILE_LIFECYCLE_EVENT_KINDS: Final[frozenset[str]] = frozenset(
    {"activated", "deprecated", "superseded", "withdrawn", "retired"}
)
PROFILE_OVERLAY_ACTIONS: Final[frozenset[str]] = frozenset({"add", "replace"})
PROFILE_MIGRATION_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"unchanged", "added", "removed", "replaced", "materially_changed", "unresolved_mapping"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileRequirement:
    portfolio_profile_id: str
    profile_revision: int
    requirement_id: str
    requirement_kind: str
    obligation: str
    title: str
    statement: str
    scope_kind: str
    satisfaction_class: str
    authority_references: tuple[str, ...] = ()
    scope_reference: str | None = None
    replaces_requirement_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_REQUIREMENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PROFILE_REQUIREMENT_RECORD_TYPE
        )
        object.__setattr__(self, "portfolio_profile_id", require_identifier(self.portfolio_profile_id, "portfolio_profile_id"))
        object.__setattr__(self, "profile_revision", require_positive_int(self.profile_revision, "profile_revision"))
        object.__setattr__(self, "requirement_id", require_identifier(self.requirement_id, "requirement_id"))
        object.__setattr__(self, "requirement_kind", require_enum(self.requirement_kind, "requirement_kind", PROFILE_REQUIREMENT_KINDS, allow_extension=True))
        object.__setattr__(self, "obligation", require_enum(self.obligation, "obligation", PROFILE_REQUIREMENT_OBLIGATIONS))
        object.__setattr__(self, "title", require_text(self.title, "title", maximum=200))
        object.__setattr__(self, "statement", require_text(self.statement, "statement", maximum=2000))
        object.__setattr__(self, "scope_kind", require_text(self.scope_kind, "scope_kind", maximum=128))
        object.__setattr__(self, "satisfaction_class", require_text(self.satisfaction_class, "satisfaction_class", maximum=128))
        object.__setattr__(self, "authority_references", text_tuple(self.authority_references, "authority_references"))
        object.__setattr__(self, "scope_reference", require_optional_text(self.scope_reference, "scope_reference", maximum=500))
        if self.replaces_requirement_id is not None:
            replacement = require_identifier(self.replaces_requirement_id, "replaces_requirement_id")
            if replacement == self.requirement_id:
                raise VitrineModelValidationError("replaces_requirement_id must differ from requirement_id.")
            object.__setattr__(self, "replaces_requirement_id", replacement)

    @property
    def profile_reference(self) -> ProfileRevisionRef:
        return ProfileRevisionRef(
            portfolio_profile_id=self.portfolio_profile_id,
            profile_revision=self.profile_revision,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileLifecycleEvent:
    profile_lifecycle_event_id: str
    profile_revision: ProfileRevisionRef
    event_kind: str
    event_at: datetime
    effective_at: datetime
    actor: ActorAttribution
    reason: str
    predecessor_event_id: str | None = None
    successor_revision: ProfileRevisionRef | None = None
    authority_reference: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_LIFECYCLE_EVENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PROFILE_LIFECYCLE_EVENT_RECORD_TYPE
        )
        object.__setattr__(self, "profile_lifecycle_event_id", require_identifier(self.profile_lifecycle_event_id, "profile_lifecycle_event_id"))
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be a ProfileRevisionRef.")
        object.__setattr__(self, "event_kind", require_enum(self.event_kind, "event_kind", PROFILE_LIFECYCLE_EVENT_KINDS))
        object.__setattr__(self, "event_at", require_aware_datetime(self.event_at, "event_at"))
        object.__setattr__(self, "effective_at", require_aware_datetime(self.effective_at, "effective_at"))
        if not isinstance(self.actor, ActorAttribution):
            raise VitrineModelValidationError("actor must be an ActorAttribution.")
        object.__setattr__(self, "reason", require_text(self.reason, "reason", maximum=1000))
        if self.predecessor_event_id is not None:
            predecessor = require_identifier(self.predecessor_event_id, "predecessor_event_id")
            if predecessor == self.profile_lifecycle_event_id:
                raise VitrineModelValidationError("predecessor_event_id must differ from profile_lifecycle_event_id.")
            object.__setattr__(self, "predecessor_event_id", predecessor)
        if self.successor_revision is not None:
            if not isinstance(self.successor_revision, ProfileRevisionRef):
                raise VitrineModelValidationError("successor_revision must be a ProfileRevisionRef or null.")
            if self.successor_revision.portfolio_profile_id != self.profile_revision.portfolio_profile_id:
                raise VitrineModelValidationError("successor_revision must belong to the same Profile series.")
            if self.successor_revision == self.profile_revision:
                raise VitrineModelValidationError("successor_revision must differ from profile_revision.")
        object.__setattr__(self, "authority_reference", require_optional_text(self.authority_reference, "authority_reference", maximum=500))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileOverlayRequirement:
    requirement_id: str
    requirement_kind: str
    obligation: str
    title: str
    statement: str
    scope_kind: str
    satisfaction_class: str
    authority_references: tuple[str, ...] = ()
    scope_reference: str | None = None
    replaces_requirement_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "requirement_id", require_identifier(self.requirement_id, "requirement_id"))
        object.__setattr__(self, "requirement_kind", require_enum(self.requirement_kind, "requirement_kind", PROFILE_REQUIREMENT_KINDS, allow_extension=True))
        object.__setattr__(self, "obligation", require_enum(self.obligation, "obligation", PROFILE_REQUIREMENT_OBLIGATIONS))
        object.__setattr__(self, "title", require_text(self.title, "title", maximum=200))
        object.__setattr__(self, "statement", require_text(self.statement, "statement", maximum=2000))
        object.__setattr__(self, "scope_kind", require_text(self.scope_kind, "scope_kind", maximum=128))
        object.__setattr__(self, "satisfaction_class", require_text(self.satisfaction_class, "satisfaction_class", maximum=128))
        object.__setattr__(self, "authority_references", text_tuple(self.authority_references, "authority_references"))
        object.__setattr__(self, "scope_reference", require_optional_text(self.scope_reference, "scope_reference", maximum=500))
        if self.replaces_requirement_id is not None:
            replacement = require_identifier(self.replaces_requirement_id, "replaces_requirement_id")
            if replacement == self.requirement_id:
                raise VitrineModelValidationError("replaces_requirement_id must differ from requirement_id.")
            object.__setattr__(self, "replaces_requirement_id", replacement)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileOverlayRequirementChange:
    action: str
    requirement: ProfileOverlayRequirement

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action",
            require_enum(self.action, "action", PROFILE_OVERLAY_ACTIONS),
        )
        if not isinstance(self.requirement, ProfileOverlayRequirement):
            raise VitrineModelValidationError(
                "requirement must be a ProfileOverlayRequirement."
            )
        if self.action == "add" and self.requirement.replaces_requirement_id is not None:
            raise VitrineModelValidationError(
                "add changes must not set replaces_requirement_id."
            )
        if self.action == "replace" and self.requirement.replaces_requirement_id is None:
            raise VitrineModelValidationError(
                "replace changes require replaces_requirement_id."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileOverlayRevisionRef:
    overlay_id: str
    overlay_revision: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "overlay_id", require_identifier(self.overlay_id, "overlay_id"))
        object.__setattr__(self, "overlay_revision", require_positive_int(self.overlay_revision, "overlay_revision"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileOverlayRevision:
    overlay_id: str
    overlay_revision: int
    predecessor_overlay_revision: int | None
    label: str
    purpose_kind: str
    created_at: datetime
    created_by: ActorAttribution
    authority_reference: str
    component_revisions: tuple[ProfileRevisionRef, ...]
    requirement_changes: tuple[ProfileOverlayRequirementChange, ...] = ()
    section_additions: tuple[ProfileSectionDefinition, ...] = ()
    audience_rule_additions: tuple[ProfileAudienceRule, ...] = ()
    known_limitations: tuple[str, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_OVERLAY_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(self.schema_version, self.record_type, PROFILE_OVERLAY_RECORD_TYPE)
        object.__setattr__(self, "overlay_id", require_identifier(self.overlay_id, "overlay_id"))
        object.__setattr__(self, "overlay_revision", require_positive_int(self.overlay_revision, "overlay_revision"))
        if self.predecessor_overlay_revision is not None:
            predecessor = require_positive_int(self.predecessor_overlay_revision, "predecessor_overlay_revision")
            if predecessor >= self.overlay_revision:
                raise VitrineModelValidationError("predecessor_overlay_revision must be lower than overlay_revision.")
            object.__setattr__(self, "predecessor_overlay_revision", predecessor)
        object.__setattr__(self, "label", require_text(self.label, "label", maximum=200))
        object.__setattr__(self, "purpose_kind", require_enum(self.purpose_kind, "purpose_kind", PROFILE_PURPOSE_KINDS))
        object.__setattr__(self, "created_at", require_aware_datetime(self.created_at, "created_at"))
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be an ActorAttribution.")
        object.__setattr__(self, "authority_reference", require_text(self.authority_reference, "authority_reference", maximum=500))
        object.__setattr__(self, "component_revisions", tuple(self.component_revisions))
        if not self.component_revisions or any(not isinstance(item, ProfileRevisionRef) for item in self.component_revisions):
            raise VitrineModelValidationError("component_revisions must contain at least one ProfileRevisionRef.")
        if len(set(self.component_revisions)) != len(self.component_revisions):
            raise VitrineModelValidationError("component_revisions must not contain duplicates.")
        object.__setattr__(self, "requirement_changes", tuple(self.requirement_changes))
        if any(not isinstance(item, ProfileOverlayRequirementChange) for item in self.requirement_changes):
            raise VitrineModelValidationError("requirement_changes must contain ProfileOverlayRequirementChange values.")
        ids = [item.requirement.requirement_id for item in self.requirement_changes]
        if len(set(ids)) != len(ids):
            raise VitrineModelValidationError("requirement_changes must not repeat a requirement ID.")
        object.__setattr__(self, "section_additions", tuple(self.section_additions))
        object.__setattr__(self, "audience_rule_additions", tuple(self.audience_rule_additions))
        if any(not isinstance(item, ProfileSectionDefinition) for item in self.section_additions):
            raise VitrineModelValidationError("section_additions must contain ProfileSectionDefinition values.")
        if len({item.section_id for item in self.section_additions}) != len(self.section_additions):
            raise VitrineModelValidationError("section_additions must not repeat a section ID.")
        if len({item.order for item in self.section_additions}) != len(self.section_additions):
            raise VitrineModelValidationError("section_additions must not repeat an order value.")
        if any(not isinstance(item, ProfileAudienceRule) for item in self.audience_rule_additions):
            raise VitrineModelValidationError("audience_rule_additions must contain ProfileAudienceRule values.")
        if len({item.audience_rule_id for item in self.audience_rule_additions}) != len(self.audience_rule_additions):
            raise VitrineModelValidationError("audience_rule_additions must not repeat an audience rule ID.")
        object.__setattr__(self, "known_limitations", text_tuple(self.known_limitations, "known_limitations"))

    @property
    def reference(self) -> ProfileOverlayRevisionRef:
        return ProfileOverlayRevisionRef(overlay_id=self.overlay_id, overlay_revision=self.overlay_revision)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileComposition:
    profile_composition_id: str
    effective_profile_revision: ProfileRevisionRef
    component_profile_revisions: tuple[ProfileRevisionRef, ...]
    overlay_revisions: tuple[ProfileOverlayRevisionRef, ...]
    composed_at: datetime
    composed_by: ActorAttribution
    authority_reference: str
    conflict_dispositions: tuple[str, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_COMPOSITION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(self.schema_version, self.record_type, PROFILE_COMPOSITION_RECORD_TYPE)
        object.__setattr__(self, "profile_composition_id", require_identifier(self.profile_composition_id, "profile_composition_id"))
        if not isinstance(self.effective_profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("effective_profile_revision must be a ProfileRevisionRef.")
        object.__setattr__(self, "component_profile_revisions", tuple(self.component_profile_revisions))
        object.__setattr__(self, "overlay_revisions", tuple(self.overlay_revisions))
        if not self.component_profile_revisions or any(not isinstance(item, ProfileRevisionRef) for item in self.component_profile_revisions):
            raise VitrineModelValidationError("component_profile_revisions must contain at least one ProfileRevisionRef.")
        if any(not isinstance(item, ProfileOverlayRevisionRef) for item in self.overlay_revisions):
            raise VitrineModelValidationError("overlay_revisions must contain ProfileOverlayRevisionRef values.")
        if len(set(self.component_profile_revisions)) != len(self.component_profile_revisions):
            raise VitrineModelValidationError("component_profile_revisions must not contain duplicates.")
        if self.effective_profile_revision in self.component_profile_revisions:
            raise VitrineModelValidationError(
                "effective_profile_revision must not also be a component Revision."
            )
        if len(set(self.overlay_revisions)) != len(self.overlay_revisions):
            raise VitrineModelValidationError("overlay_revisions must not contain duplicates.")
        object.__setattr__(self, "composed_at", require_aware_datetime(self.composed_at, "composed_at"))
        if not isinstance(self.composed_by, ActorAttribution):
            raise VitrineModelValidationError("composed_by must be an ActorAttribution.")
        object.__setattr__(self, "authority_reference", require_text(self.authority_reference, "authority_reference", maximum=500))
        object.__setattr__(self, "conflict_dispositions", text_tuple(self.conflict_dispositions, "conflict_dispositions"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRequirementImpact:
    unchanged: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    replaced: tuple[str, ...] = ()
    materially_changed: tuple[str, ...] = ()
    unresolved_mapping: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "unchanged", "added", "removed", "replaced", "materially_changed", "unresolved_mapping"
        ):
            object.__setattr__(self, field_name, identifier_tuple(getattr(self, field_name), field_name))
        all_ids = [
            requirement_id
            for field_name in (
                "unchanged", "added", "removed", "replaced", "materially_changed", "unresolved_mapping"
            )
            for requirement_id in getattr(self, field_name)
        ]
        if len(set(all_ids)) != len(all_ids):
            raise VitrineModelValidationError("requirement impact categories must not overlap.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProfileMigration:
    profile_migration_id: str
    portfolio_id: str
    predecessor_binding_id: str
    successor_binding_id: str
    source_profile_revision: ProfileRevisionRef
    target_profile_revision: ProfileRevisionRef
    requirement_impact: ProfileRequirementImpact
    unresolved_requirement_ids: tuple[str, ...]
    reapproval_requirement_ids: tuple[str, ...]
    migrated_at: datetime
    migrated_by: ActorAttribution
    migration_reason: str
    authority_reference: str
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PROFILE_MIGRATION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(self.schema_version, self.record_type, PROFILE_MIGRATION_RECORD_TYPE)
        object.__setattr__(self, "profile_migration_id", require_identifier(self.profile_migration_id, "profile_migration_id"))
        object.__setattr__(self, "portfolio_id", require_identifier(self.portfolio_id, "portfolio_id"))
        object.__setattr__(self, "predecessor_binding_id", require_identifier(self.predecessor_binding_id, "predecessor_binding_id"))
        object.__setattr__(self, "successor_binding_id", require_identifier(self.successor_binding_id, "successor_binding_id"))
        if self.predecessor_binding_id == self.successor_binding_id:
            raise VitrineModelValidationError("predecessor_binding_id and successor_binding_id must differ.")
        if not isinstance(self.source_profile_revision, ProfileRevisionRef) or not isinstance(self.target_profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("source_profile_revision and target_profile_revision must be ProfileRevisionRef values.")
        if self.source_profile_revision == self.target_profile_revision:
            raise VitrineModelValidationError("target_profile_revision must differ from source_profile_revision.")
        if not isinstance(self.requirement_impact, ProfileRequirementImpact):
            raise VitrineModelValidationError("requirement_impact must be a ProfileRequirementImpact.")
        object.__setattr__(self, "unresolved_requirement_ids", identifier_tuple(self.unresolved_requirement_ids, "unresolved_requirement_ids"))
        object.__setattr__(self, "reapproval_requirement_ids", identifier_tuple(self.reapproval_requirement_ids, "reapproval_requirement_ids"))
        object.__setattr__(self, "migrated_at", require_aware_datetime(self.migrated_at, "migrated_at"))
        if not isinstance(self.migrated_by, ActorAttribution):
            raise VitrineModelValidationError("migrated_by must be an ActorAttribution.")
        object.__setattr__(self, "migration_reason", require_text(self.migration_reason, "migration_reason", maximum=1000))
        object.__setattr__(self, "authority_reference", require_text(self.authority_reference, "authority_reference", maximum=500))
