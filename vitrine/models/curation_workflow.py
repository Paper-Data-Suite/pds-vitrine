"""Additive curation workflow records layered around the frozen #28 models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final, cast

from .candidates import CANDIDATE_CONDITION_STATES
from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    lower_key_tuple,
    require_aware_datetime,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ProfileRevisionRef

SELECTION_PROPOSAL_RECORD_TYPE: Final[str] = "selection_proposal"
SELECTION_DECISION_RECORD_TYPE: Final[str] = "selection_decision"
SELECTION_LIFECYCLE_EVENT_RECORD_TYPE: Final[str] = "selection_lifecycle_event"
PLACEMENT_LIFECYCLE_EVENT_RECORD_TYPE: Final[str] = "placement_lifecycle_event"
ARRANGEMENT_POINTER_RECORD_TYPE: Final[str] = "section_arrangement_pointer_revision"
CURATION_RATIONALE_RECORD_TYPE: Final[str] = "curation_rationale"
CURATION_ANNOTATION_RECORD_TYPE: Final[str] = "curation_annotation"
PORTFOLIO_REFLECTION_RECORD_TYPE: Final[str] = "portfolio_reflection"
CURATION_REVIEW_DECISION_RECORD_TYPE: Final[str] = "curation_review_decision"
COMPOSITION_INVENTORY_RECORD_TYPE: Final[str] = "working_portfolio_composition_inventory"
COMPOSITION_POINTER_RECORD_TYPE: Final[str] = "working_portfolio_composition_pointer_revision"

PROPOSAL_ORIGINS: Final[frozenset[str]] = frozenset(
    {
        "student",
        "teacher",
        "authorized_reviewer",
        "direct_selection",
        "imported_prior_curation",
        "system_suggestion",
    }
)
SELECTION_DECISIONS: Final[frozenset[str]] = frozenset(
    {"accepted", "rejected", "changes_requested", "withdrawn", "expired"}
)
SELECTION_LIFECYCLE_KINDS: Final[frozenset[str]] = frozenset(
    {"activated", "withdrawn", "replaced", "invalidated", "superseded"}
)
PLACEMENT_LIFECYCLE_KINDS: Final[frozenset[str]] = frozenset(
    {"activated", "withdrawn", "replaced", "invalidated"}
)
CURATION_TARGET_KINDS: Final[frozenset[str]] = frozenset(
    {
        "selection_proposal",
        "selection",
        "placement",
        "arrangement",
        "section",
        "annotation",
        "reflection",
        "composition",
        "portfolio",
        "checkpoint",
    }
)
ANNOTATION_PURPOSES: Final[frozenset[str]] = frozenset(
    {
        "curator_context",
        "source_context",
        "comparison_note",
        "standards_context",
        "caption",
        "accessibility_description",
    }
)
ANNOTATION_SCOPES: Final[frozenset[str]] = frozenset(
    {"selection", "placement", "section", "comparison_set", "composition"}
)
REFLECTION_SCOPES: Final[frozenset[str]] = frozenset(
    {"selection", "placement", "comparison_set", "section", "checkpoint", "portfolio"}
)
REFLECTION_CONTENT_MODES: Final[frozenset[str]] = frozenset(
    {"inline_text", "structured_response", "external_reference"}
)
CURATION_REVIEW_DECISIONS: Final[frozenset[str]] = frozenset(
    {"approved", "rejected", "changes_requested", "acknowledged", "waived"}
)
COMPOSITION_COHERENCE_STATES: Final[frozenset[str]] = frozenset(
    {"coherent", "coherent_with_unresolved_obligations"}
)


def _profile_revision(value: object, field_name: str) -> ProfileRevisionRef:
    if not isinstance(value, ProfileRevisionRef):
        raise VitrineModelValidationError(f"{field_name} must be ProfileRevisionRef.")
    return value


def _actor(value: object, field_name: str) -> ActorAttribution:
    if not isinstance(value, ActorAttribution):
        raise VitrineModelValidationError(f"{field_name} must be ActorAttribution.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationTargetRef:
    target_kind: str
    target_id: str
    target_revision: int | None = None
    semantic_role: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_kind",
            require_enum(self.target_kind, "target_kind", CURATION_TARGET_KINDS),
        )
        object.__setattr__(
            self, "target_id", require_identifier(self.target_id, "target_id")
        )
        if self.target_revision is not None:
            object.__setattr__(
                self,
                "target_revision",
                require_positive_int(self.target_revision, "target_revision"),
            )
        object.__setattr__(
            self,
            "semantic_role",
            require_optional_text(self.semantic_role, "semantic_role", maximum=128),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationRevisionRef:
    record_kind: str
    record_id: str
    revision: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "record_kind",
            require_enum(
                self.record_kind,
                "record_kind",
                frozenset({"annotation", "reflection"}),
            ),
        )
        object.__setattr__(
            self, "record_id", require_identifier(self.record_id, "record_id")
        )
        object.__setattr__(
            self, "revision", require_positive_int(self.revision, "revision")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionProposal:
    selection_proposal_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    candidate_id: str
    candidate_evaluation_id: str
    proposer: ActorAttribution
    proposal_origin: str
    proposed_section_ids: tuple[str, ...]
    intended_profile_requirement_ids: tuple[str, ...]
    candidate_condition_state_snapshot: str
    proposed_at: datetime
    rationale_id: str | None = None
    predecessor_proposal_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SELECTION_PROPOSAL_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SELECTION_PROPOSAL_RECORD_TYPE
        )
        for name in (
            "selection_proposal_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "candidate_id",
            "candidate_evaluation_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "profile_revision", _profile_revision(self.profile_revision, "profile_revision")
        )
        object.__setattr__(self, "proposer", _actor(self.proposer, "proposer"))
        object.__setattr__(
            self,
            "proposal_origin",
            require_enum(self.proposal_origin, "proposal_origin", PROPOSAL_ORIGINS),
        )
        object.__setattr__(
            self,
            "proposed_section_ids",
            identifier_tuple(self.proposed_section_ids, "proposed_section_ids", nonempty=True),
        )
        object.__setattr__(
            self,
            "intended_profile_requirement_ids",
            identifier_tuple(
                self.intended_profile_requirement_ids,
                "intended_profile_requirement_ids",
            ),
        )
        object.__setattr__(
            self,
            "candidate_condition_state_snapshot",
            require_enum(
                self.candidate_condition_state_snapshot,
                "candidate_condition_state_snapshot",
                CANDIDATE_CONDITION_STATES,
            ),
        )
        object.__setattr__(
            self, "proposed_at", require_aware_datetime(self.proposed_at, "proposed_at")
        )
        if self.rationale_id is not None:
            object.__setattr__(
                self, "rationale_id", require_identifier(self.rationale_id, "rationale_id")
            )
        if self.predecessor_proposal_id is not None:
            predecessor = require_identifier(
                self.predecessor_proposal_id, "predecessor_proposal_id"
            )
            if predecessor == self.selection_proposal_id:
                raise VitrineModelValidationError(
                    "predecessor_proposal_id must differ from selection_proposal_id."
                )
            object.__setattr__(self, "predecessor_proposal_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionDecision:
    selection_decision_id: str
    selection_proposal_id: str
    decision: str
    decided_at: datetime
    decided_by: ActorAttribution
    authority_reference: str
    matched_profile_requirement_ids: tuple[str, ...] = ()
    condition_codes: tuple[str, ...] = ()
    rationale_id: str | None = None
    resulting_selection_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SELECTION_DECISION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SELECTION_DECISION_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "selection_decision_id",
            require_identifier(self.selection_decision_id, "selection_decision_id"),
        )
        object.__setattr__(
            self,
            "selection_proposal_id",
            require_identifier(self.selection_proposal_id, "selection_proposal_id"),
        )
        object.__setattr__(
            self, "decision", require_enum(self.decision, "decision", SELECTION_DECISIONS)
        )
        object.__setattr__(
            self, "decided_at", require_aware_datetime(self.decided_at, "decided_at")
        )
        object.__setattr__(self, "decided_by", _actor(self.decided_by, "decided_by"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        object.__setattr__(
            self,
            "matched_profile_requirement_ids",
            identifier_tuple(
                self.matched_profile_requirement_ids, "matched_profile_requirement_ids"
            ),
        )
        object.__setattr__(
            self,
            "condition_codes",
            lower_key_tuple(self.condition_codes, "condition_codes"),
        )
        if self.rationale_id is not None:
            object.__setattr__(
                self, "rationale_id", require_identifier(self.rationale_id, "rationale_id")
            )
        if self.resulting_selection_id is not None:
            object.__setattr__(
                self,
                "resulting_selection_id",
                require_identifier(self.resulting_selection_id, "resulting_selection_id"),
            )
        if self.decision == "accepted" and self.resulting_selection_id is None:
            raise VitrineModelValidationError(
                "accepted decisions require resulting_selection_id."
            )
        if self.decision != "accepted" and self.resulting_selection_id is not None:
            raise VitrineModelValidationError(
                "non-accepted decisions must not set resulting_selection_id."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionLifecycleEvent:
    selection_lifecycle_event_id: str
    selection_id: str
    event_kind: str
    event_at: datetime
    actor: ActorAttribution
    authority_reference: str
    reason: str
    predecessor_event_id: str | None = None
    basis_selection_decision_id: str | None = None
    successor_selection_ids: tuple[str, ...] = ()
    affected_placement_ids: tuple[str, ...] = ()
    unresolved_condition_codes: tuple[str, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SELECTION_LIFECYCLE_EVENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SELECTION_LIFECYCLE_EVENT_RECORD_TYPE
        )
        for name in ("selection_lifecycle_event_id", "selection_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "event_kind",
            require_enum(self.event_kind, "event_kind", SELECTION_LIFECYCLE_KINDS),
        )
        object.__setattr__(
            self, "event_at", require_aware_datetime(self.event_at, "event_at")
        )
        object.__setattr__(self, "actor", _actor(self.actor, "actor"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        object.__setattr__(self, "reason", require_text(self.reason, "reason", maximum=1000))
        if self.predecessor_event_id is not None:
            predecessor = require_identifier(
                self.predecessor_event_id, "predecessor_event_id"
            )
            if predecessor == self.selection_lifecycle_event_id:
                raise VitrineModelValidationError(
                    "predecessor_event_id must differ from selection_lifecycle_event_id."
                )
            object.__setattr__(self, "predecessor_event_id", predecessor)
        if self.basis_selection_decision_id is not None:
            object.__setattr__(
                self,
                "basis_selection_decision_id",
                require_identifier(
                    self.basis_selection_decision_id, "basis_selection_decision_id"
                ),
            )
        object.__setattr__(
            self,
            "successor_selection_ids",
            identifier_tuple(self.successor_selection_ids, "successor_selection_ids"),
        )
        object.__setattr__(
            self,
            "affected_placement_ids",
            identifier_tuple(self.affected_placement_ids, "affected_placement_ids"),
        )
        object.__setattr__(
            self,
            "unresolved_condition_codes",
            lower_key_tuple(
                self.unresolved_condition_codes, "unresolved_condition_codes"
            ),
        )
        if self.event_kind in {"replaced", "superseded"}:
            if len(self.successor_selection_ids) != 1:
                raise VitrineModelValidationError(
                    "replaced/superseded Selection events require exactly one successor."
                )
        elif self.successor_selection_ids:
            raise VitrineModelValidationError(
                "only replaced/superseded Selection events may identify a successor."
            )
        if self.event_kind == "activated":
            if self.basis_selection_decision_id is None:
                raise VitrineModelValidationError(
                    "activated Selection events require basis_selection_decision_id."
                )
            if self.predecessor_event_id is not None:
                raise VitrineModelValidationError(
                    "activated Selection events must be lifecycle roots."
                )
        else:
            if self.basis_selection_decision_id is not None:
                raise VitrineModelValidationError(
                    "terminal Selection events must not identify an activation basis."
                )
            if self.predecessor_event_id is None:
                raise VitrineModelValidationError(
                    "terminal Selection events require an explicit predecessor."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class PlacementLifecycleEvent:
    placement_lifecycle_event_id: str
    placement_id: str
    event_kind: str
    event_at: datetime
    actor: ActorAttribution
    authority_reference: str
    reason: str
    predecessor_event_id: str | None = None
    successor_placement_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PLACEMENT_LIFECYCLE_EVENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PLACEMENT_LIFECYCLE_EVENT_RECORD_TYPE
        )
        for name in ("placement_lifecycle_event_id", "placement_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "event_kind",
            require_enum(self.event_kind, "event_kind", PLACEMENT_LIFECYCLE_KINDS),
        )
        object.__setattr__(
            self, "event_at", require_aware_datetime(self.event_at, "event_at")
        )
        object.__setattr__(self, "actor", _actor(self.actor, "actor"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        object.__setattr__(self, "reason", require_text(self.reason, "reason", maximum=1000))
        if self.predecessor_event_id is not None:
            predecessor = require_identifier(
                self.predecessor_event_id, "predecessor_event_id"
            )
            if predecessor == self.placement_lifecycle_event_id:
                raise VitrineModelValidationError(
                    "predecessor_event_id must differ from placement_lifecycle_event_id."
                )
            object.__setattr__(self, "predecessor_event_id", predecessor)
        if self.successor_placement_id is not None:
            object.__setattr__(
                self,
                "successor_placement_id",
                require_identifier(self.successor_placement_id, "successor_placement_id"),
            )
        if self.event_kind == "replaced" and self.successor_placement_id is None:
            raise VitrineModelValidationError(
                "replaced Placement events require successor_placement_id."
            )
        if self.event_kind != "replaced" and self.successor_placement_id is not None:
            raise VitrineModelValidationError(
                "only replaced Placement events may identify a successor."
            )
        if self.event_kind == "activated":
            if self.predecessor_event_id is not None:
                raise VitrineModelValidationError(
                    "activated Placement events must be lifecycle roots."
                )
        elif self.predecessor_event_id is None:
            raise VitrineModelValidationError(
                "terminal Placement events require an explicit predecessor."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionArrangementPointerRevision:
    arrangement_pointer_id: str
    pointer_revision: int
    portfolio_id: str
    profile_binding_id: str
    section_id: str
    arrangement_id: str
    pointed_at: datetime
    pointed_by: ActorAttribution
    authority_reference: str
    predecessor_pointer_revision: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=ARRANGEMENT_POINTER_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, ARRANGEMENT_POINTER_RECORD_TYPE
        )
        for name in (
            "arrangement_pointer_id",
            "portfolio_id",
            "profile_binding_id",
            "section_id",
            "arrangement_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "pointer_revision", require_positive_int(self.pointer_revision, "pointer_revision")
        )
        object.__setattr__(
            self, "pointed_at", require_aware_datetime(self.pointed_at, "pointed_at")
        )
        object.__setattr__(self, "pointed_by", _actor(self.pointed_by, "pointed_by"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        if self.predecessor_pointer_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_pointer_revision, "predecessor_pointer_revision"
            )
            if predecessor >= self.pointer_revision:
                raise VitrineModelValidationError(
                    "predecessor_pointer_revision must be lower than pointer_revision."
                )
            object.__setattr__(self, "predecessor_pointer_revision", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationRationale:
    rationale_id: str
    portfolio_id: str
    profile_binding_id: str
    target_kind: str
    target_id: str
    action_kind: str
    author: ActorAttribution
    created_at: datetime
    text: str
    profile_requirement_ids: tuple[str, ...] = ()
    predecessor_rationale_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=CURATION_RATIONALE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, CURATION_RATIONALE_RECORD_TYPE
        )
        for name in ("rationale_id", "portfolio_id", "profile_binding_id", "target_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "target_kind",
            require_enum(self.target_kind, "target_kind", CURATION_TARGET_KINDS),
        )
        object.__setattr__(
            self,
            "action_kind",
            require_controlled_key(self.action_kind, "action_kind"),
        )
        object.__setattr__(self, "author", _actor(self.author, "author"))
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        object.__setattr__(self, "text", require_text(self.text, "text", maximum=4000))
        object.__setattr__(
            self,
            "profile_requirement_ids",
            identifier_tuple(self.profile_requirement_ids, "profile_requirement_ids"),
        )
        if self.predecessor_rationale_id is not None:
            predecessor = require_identifier(
                self.predecessor_rationale_id, "predecessor_rationale_id"
            )
            if predecessor == self.rationale_id:
                raise VitrineModelValidationError(
                    "predecessor_rationale_id must differ from rationale_id."
                )
            object.__setattr__(self, "predecessor_rationale_id", predecessor)


def _target_refs(values: object, field_name: str) -> tuple[CurationTargetRef, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise VitrineModelValidationError(f"{field_name} must be a collection.")
    result: tuple[object, ...] = tuple(values)
    if not result or any(not isinstance(item, CurationTargetRef) for item in result):
        raise VitrineModelValidationError(
            f"{field_name} must contain CurationTargetRef values."
        )
    if len(set(result)) != len(result):
        raise VitrineModelValidationError(f"{field_name} must not contain duplicates.")
    return tuple(cast(CurationTargetRef, item) for item in result)


def _validate_scope_targets(
    scope: str, targets: tuple[CurationTargetRef, ...], *, reflection: bool
) -> None:
    expected_kind = {
        "selection": "selection",
        "placement": "placement",
        "section": "section",
        "composition": "composition",
        "checkpoint": "checkpoint",
        "portfolio": "portfolio",
    }.get(scope)
    if scope == "comparison_set":
        if len(targets) < 2 or any(item.target_kind != "selection" for item in targets):
            raise VitrineModelValidationError(
                "comparison_set requires at least two Selection targets."
            )
        if reflection and any(item.semantic_role is None for item in targets):
            raise VitrineModelValidationError(
                "comparison Reflection targets require explicit semantic_role values."
            )
        return
    if expected_kind is None or len(targets) != 1 or targets[0].target_kind != expected_kind:
        raise VitrineModelValidationError(
            f"{scope} scope requires exactly one {expected_kind or scope} target."
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationAnnotation:
    annotation_id: str
    annotation_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    purpose: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    author: ActorAttribution
    created_at: datetime
    language: str
    content_format: str
    content: str
    intended_presentation_class: str | None = None
    predecessor_annotation_revision: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=CURATION_ANNOTATION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, CURATION_ANNOTATION_RECORD_TYPE
        )
        for name in (
            "annotation_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "annotation_revision",
            require_positive_int(self.annotation_revision, "annotation_revision"),
        )
        object.__setattr__(
            self, "profile_revision", _profile_revision(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "purpose",
            require_enum(
                self.purpose,
                "purpose",
                ANNOTATION_PURPOSES,
                allow_extension=True,
            ),
        )
        scope = require_enum(self.target_scope, "target_scope", ANNOTATION_SCOPES)
        object.__setattr__(self, "target_scope", scope)
        targets = _target_refs(self.target_references, "target_references")
        _validate_scope_targets(scope, targets, reflection=False)
        object.__setattr__(self, "target_references", targets)
        object.__setattr__(self, "author", _actor(self.author, "author"))
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        object.__setattr__(self, "language", require_text(self.language, "language", maximum=64))
        object.__setattr__(
            self,
            "content_format",
            require_controlled_key(self.content_format, "content_format"),
        )
        object.__setattr__(self, "content", require_text(self.content, "content", maximum=12000))
        object.__setattr__(
            self,
            "intended_presentation_class",
            require_optional_text(
                self.intended_presentation_class,
                "intended_presentation_class",
                maximum=128,
            ),
        )
        if self.predecessor_annotation_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_annotation_revision, "predecessor_annotation_revision"
            )
            if predecessor >= self.annotation_revision:
                raise VitrineModelValidationError(
                    "predecessor_annotation_revision must be lower than annotation_revision."
                )
            object.__setattr__(self, "predecessor_annotation_revision", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioReflection:
    reflection_id: str
    reflection_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    prompt_snapshot: str
    author: ActorAttribution
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    content_mode: str
    language: str
    content_format: str
    content: str
    created_at: datetime
    predecessor_reflection_revision: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PORTFOLIO_REFLECTION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PORTFOLIO_REFLECTION_RECORD_TYPE
        )
        for name in (
            "reflection_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "reflection_requirement_id",
            "prompt_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "reflection_revision",
            require_positive_int(self.reflection_revision, "reflection_revision"),
        )
        object.__setattr__(
            self, "profile_revision", _profile_revision(self.profile_revision, "profile_revision")
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
        object.__setattr__(self, "author", _actor(self.author, "author"))
        scope = require_enum(self.target_scope, "target_scope", REFLECTION_SCOPES)
        object.__setattr__(self, "target_scope", scope)
        targets = _target_refs(self.target_references, "target_references")
        _validate_scope_targets(scope, targets, reflection=True)
        object.__setattr__(self, "target_references", targets)
        object.__setattr__(
            self,
            "content_mode",
            require_enum(self.content_mode, "content_mode", REFLECTION_CONTENT_MODES),
        )
        object.__setattr__(self, "language", require_text(self.language, "language", maximum=64))
        object.__setattr__(
            self,
            "content_format",
            require_controlled_key(self.content_format, "content_format"),
        )
        object.__setattr__(self, "content", require_text(self.content, "content", maximum=16000))
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if self.predecessor_reflection_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_reflection_revision, "predecessor_reflection_revision"
            )
            if predecessor >= self.reflection_revision:
                raise VitrineModelValidationError(
                    "predecessor_reflection_revision must be lower than reflection_revision."
                )
            object.__setattr__(self, "predecessor_reflection_revision", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationReviewDecision:
    curation_review_decision_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    decision: str
    reviewed_at: datetime
    reviewed_by: ActorAttribution
    authority_reference: str
    reason: str
    approval_requirement_id: str | None = None
    required_follow_up_codes: tuple[str, ...] = ()
    predecessor_review_decision_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=CURATION_REVIEW_DECISION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, CURATION_REVIEW_DECISION_RECORD_TYPE
        )
        for name in (
            "curation_review_decision_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "profile_revision", _profile_revision(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "target_scope",
            require_controlled_key(self.target_scope, "target_scope"),
        )
        object.__setattr__(
            self,
            "target_references",
            _target_refs(self.target_references, "target_references"),
        )
        object.__setattr__(
            self,
            "decision",
            require_enum(self.decision, "decision", CURATION_REVIEW_DECISIONS),
        )
        object.__setattr__(
            self, "reviewed_at", require_aware_datetime(self.reviewed_at, "reviewed_at")
        )
        object.__setattr__(self, "reviewed_by", _actor(self.reviewed_by, "reviewed_by"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        object.__setattr__(self, "reason", require_text(self.reason, "reason", maximum=2000))
        if self.approval_requirement_id is not None:
            object.__setattr__(
                self,
                "approval_requirement_id",
                require_identifier(self.approval_requirement_id, "approval_requirement_id"),
            )
        object.__setattr__(
            self,
            "required_follow_up_codes",
            lower_key_tuple(self.required_follow_up_codes, "required_follow_up_codes"),
        )
        if self.predecessor_review_decision_id is not None:
            predecessor = require_identifier(
                self.predecessor_review_decision_id, "predecessor_review_decision_id"
            )
            if predecessor == self.curation_review_decision_id:
                raise VitrineModelValidationError(
                    "predecessor_review_decision_id must differ from decision identity."
                )
            object.__setattr__(self, "predecessor_review_decision_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkingPortfolioCompositionInventory:
    portfolio_id: str
    composition_revision: int
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    included_rationale_ids: tuple[str, ...]
    included_curation_revisions: tuple[CurationRevisionRef, ...]
    applicable_review_decision_ids: tuple[str, ...]
    related_profile_requirement_ids: tuple[str, ...]
    unresolved_obligation_codes: tuple[str, ...]
    coherence_state: str
    created_at: datetime
    created_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=COMPOSITION_INVENTORY_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, COMPOSITION_INVENTORY_RECORD_TYPE
        )
        object.__setattr__(
            self, "portfolio_id", require_identifier(self.portfolio_id, "portfolio_id")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        object.__setattr__(
            self,
            "profile_binding_id",
            require_identifier(self.profile_binding_id, "profile_binding_id"),
        )
        object.__setattr__(
            self, "profile_revision", _profile_revision(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "included_rationale_ids",
            identifier_tuple(self.included_rationale_ids, "included_rationale_ids"),
        )
        revisions = tuple(self.included_curation_revisions)
        if any(not isinstance(item, CurationRevisionRef) for item in revisions):
            raise VitrineModelValidationError(
                "included_curation_revisions must contain CurationRevisionRef values."
            )
        if len(set(revisions)) != len(revisions):
            raise VitrineModelValidationError(
                "included_curation_revisions must not contain duplicates."
            )
        object.__setattr__(self, "included_curation_revisions", revisions)
        object.__setattr__(
            self,
            "applicable_review_decision_ids",
            identifier_tuple(
                self.applicable_review_decision_ids, "applicable_review_decision_ids"
            ),
        )
        object.__setattr__(
            self,
            "related_profile_requirement_ids",
            identifier_tuple(
                self.related_profile_requirement_ids, "related_profile_requirement_ids"
            ),
        )
        object.__setattr__(
            self,
            "unresolved_obligation_codes",
            lower_key_tuple(
                self.unresolved_obligation_codes, "unresolved_obligation_codes"
            ),
        )
        object.__setattr__(
            self,
            "coherence_state",
            require_enum(
                self.coherence_state,
                "coherence_state",
                COMPOSITION_COHERENCE_STATES,
            ),
        )
        if self.unresolved_obligation_codes and self.coherence_state != "coherent_with_unresolved_obligations":
            raise VitrineModelValidationError(
                "unresolved obligations require coherent_with_unresolved_obligations."
            )
        if not self.unresolved_obligation_codes and self.coherence_state != "coherent":
            raise VitrineModelValidationError(
                "coherent state must not claim unresolved obligations."
            )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        object.__setattr__(self, "created_by", _actor(self.created_by, "created_by"))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkingPortfolioCompositionPointerRevision:
    composition_pointer_id: str
    pointer_revision: int
    portfolio_id: str
    profile_binding_id: str
    composition_revision: int
    pointed_at: datetime
    pointed_by: ActorAttribution
    authority_reference: str
    predecessor_pointer_revision: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=COMPOSITION_POINTER_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, COMPOSITION_POINTER_RECORD_TYPE
        )
        for name in ("composition_pointer_id", "portfolio_id", "profile_binding_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "pointer_revision", require_positive_int(self.pointer_revision, "pointer_revision")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        object.__setattr__(
            self, "pointed_at", require_aware_datetime(self.pointed_at, "pointed_at")
        )
        object.__setattr__(self, "pointed_by", _actor(self.pointed_by, "pointed_by"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        if self.predecessor_pointer_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_pointer_revision, "predecessor_pointer_revision"
            )
            if predecessor >= self.pointer_revision:
                raise VitrineModelValidationError(
                    "predecessor_pointer_revision must be lower than pointer_revision."
                )
            object.__setattr__(self, "predecessor_pointer_revision", predecessor)


__all__ = [
    "ANNOTATION_PURPOSES",
    "ANNOTATION_SCOPES",
    "ARRANGEMENT_POINTER_RECORD_TYPE",
    "COMPOSITION_COHERENCE_STATES",
    "COMPOSITION_INVENTORY_RECORD_TYPE",
    "COMPOSITION_POINTER_RECORD_TYPE",
    "CURATION_ANNOTATION_RECORD_TYPE",
    "CURATION_RATIONALE_RECORD_TYPE",
    "CURATION_REVIEW_DECISION_RECORD_TYPE",
    "CURATION_REVIEW_DECISIONS",
    "CURATION_TARGET_KINDS",
    "CurationAnnotation",
    "CurationRationale",
    "CurationReviewDecision",
    "CurationRevisionRef",
    "CurationTargetRef",
    "PLACEMENT_LIFECYCLE_EVENT_RECORD_TYPE",
    "PLACEMENT_LIFECYCLE_KINDS",
    "PORTFOLIO_REFLECTION_RECORD_TYPE",
    "PROPOSAL_ORIGINS",
    "PlacementLifecycleEvent",
    "PortfolioReflection",
    "REFLECTION_CONTENT_MODES",
    "REFLECTION_SCOPES",
    "SELECTION_DECISION_RECORD_TYPE",
    "SELECTION_DECISIONS",
    "SELECTION_LIFECYCLE_EVENT_RECORD_TYPE",
    "SELECTION_LIFECYCLE_KINDS",
    "SELECTION_PROPOSAL_RECORD_TYPE",
    "SectionArrangementPointerRevision",
    "SelectionDecision",
    "SelectionLifecycleEvent",
    "SelectionProposal",
    "WorkingPortfolioCompositionInventory",
    "WorkingPortfolioCompositionPointerRevision",
]
