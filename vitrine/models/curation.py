"""Selection, Placement, Arrangement, and Composition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    require_aware_datetime,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ProfileRevisionRef

SELECTION_RECORD_TYPE: Final[str] = "portfolio_selection"
PLACEMENT_RECORD_TYPE: Final[str] = "portfolio_placement"
ARRANGEMENT_RECORD_TYPE: Final[str] = "section_arrangement_revision"
COMPOSITION_RECORD_TYPE: Final[str] = "working_portfolio_composition_revision"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSelection:
    selection_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    candidate_id: str
    candidate_evaluation_id: str
    selected_at: datetime
    selected_by: ActorAttribution
    selection_reason: str | None = None
    predecessor_selection_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SELECTION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SELECTION_RECORD_TYPE
        )
        for field_name in (
            "selection_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "candidate_id",
            "candidate_evaluation_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        object.__setattr__(
            self,
            "selected_at",
            require_aware_datetime(self.selected_at, "selected_at"),
        )
        if not isinstance(self.selected_by, ActorAttribution):
            raise VitrineModelValidationError("selected_by must be ActorAttribution.")
        object.__setattr__(
            self,
            "selection_reason",
            require_optional_text(
                self.selection_reason, "selection_reason", maximum=1000
            ),
        )
        if self.predecessor_selection_id is not None:
            predecessor = require_identifier(
                self.predecessor_selection_id, "predecessor_selection_id"
            )
            if predecessor == self.selection_id:
                raise VitrineModelValidationError(
                    "predecessor_selection_id must differ from selection_id."
                )
            object.__setattr__(self, "predecessor_selection_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class PlacementPresentation:
    display_title: str | None = None
    display_caption: str | None = None
    source_credit: str | None = None
    presentation_note: str | None = None

    def __post_init__(self) -> None:
        limits = {
            "display_title": 300,
            "display_caption": 1000,
            "source_credit": 500,
            "presentation_note": 1000,
        }
        for field_name, maximum in limits.items():
            object.__setattr__(
                self,
                field_name,
                require_optional_text(
                    getattr(self, field_name), field_name, maximum=maximum
                ),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioPlacement:
    placement_id: str
    portfolio_id: str
    profile_binding_id: str
    selection_id: str
    section_id: str
    presentation: PlacementPresentation | None
    placed_at: datetime
    placed_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PLACEMENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, PLACEMENT_RECORD_TYPE
        )
        for field_name in (
            "placement_id",
            "portfolio_id",
            "profile_binding_id",
            "selection_id",
            "section_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        if self.presentation is not None and not isinstance(
            self.presentation, PlacementPresentation
        ):
            raise VitrineModelValidationError("presentation must be PlacementPresentation or null.")
        object.__setattr__(
            self, "placed_at", require_aware_datetime(self.placed_at, "placed_at")
        )
        if not isinstance(self.placed_by, ActorAttribution):
            raise VitrineModelValidationError("placed_by must be ActorAttribution.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionArrangementRevision:
    arrangement_id: str
    portfolio_id: str
    profile_binding_id: str
    section_id: str
    arrangement_revision: int
    placement_ids: tuple[str, ...]
    created_at: datetime
    created_by: ActorAttribution
    predecessor_arrangement_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=ARRANGEMENT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, ARRANGEMENT_RECORD_TYPE
        )
        for field_name in (
            "arrangement_id",
            "portfolio_id",
            "profile_binding_id",
            "section_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "arrangement_revision",
            require_positive_int(self.arrangement_revision, "arrangement_revision"),
        )
        object.__setattr__(
            self,
            "placement_ids",
            identifier_tuple(self.placement_ids, "placement_ids"),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")
        if self.predecessor_arrangement_id is not None:
            predecessor = require_identifier(
                self.predecessor_arrangement_id, "predecessor_arrangement_id"
            )
            if predecessor == self.arrangement_id:
                raise VitrineModelValidationError(
                    "predecessor_arrangement_id must differ from arrangement_id."
                )
            object.__setattr__(self, "predecessor_arrangement_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkingPortfolioCompositionRevision:
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    selection_ids: tuple[str, ...]
    placement_ids: tuple[str, ...]
    arrangement_ids: tuple[str, ...]
    created_at: datetime
    created_by: ActorAttribution
    predecessor_composition_revision: int | None = None
    composition_note: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=COMPOSITION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, COMPOSITION_RECORD_TYPE
        )
        for field_name in (
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        for field_name in ("selection_ids", "placement_ids", "arrangement_ids"):
            object.__setattr__(
                self,
                field_name,
                identifier_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")
        if self.predecessor_composition_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_composition_revision,
                "predecessor_composition_revision",
            )
            if predecessor >= self.composition_revision:
                raise VitrineModelValidationError(
                    "predecessor_composition_revision must be lower than composition_revision."
                )
            object.__setattr__(self, "predecessor_composition_revision", predecessor)
        object.__setattr__(
            self,
            "composition_note",
            require_optional_text(
                self.composition_note, "composition_note", maximum=2000
            ),
        )
