"""Audience-context model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    lower_key_tuple,
    require_aware_datetime,
    require_enum,
    require_identifier,
    require_optional_text,
    require_record_envelope,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ProfileRevisionRef
from .profiles import AUDIENCE_CLASSES

AUDIENCE_CONTEXT_RECORD_TYPE: Final[str] = "audience_context"


@dataclass(frozen=True, slots=True, kw_only=True)
class AudienceContext:
    audience_context_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    audience_rule_id: str
    audience_class: str
    purpose: str
    subject_scope: str
    allowed_content_classes: tuple[str, ...]
    prohibited_content_classes: tuple[str, ...]
    required_review_classes: tuple[str, ...]
    presentation_class: str
    retention_policy_reference: str | None
    created_at: datetime
    created_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=AUDIENCE_CONTEXT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, AUDIENCE_CONTEXT_RECORD_TYPE
        )
        for field_name in (
            "audience_context_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_rule_id",
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
            "audience_class",
            require_enum(self.audience_class, "audience_class", AUDIENCE_CLASSES),
        )
        object.__setattr__(
            self, "purpose", require_text(self.purpose, "purpose", maximum=1000)
        )
        object.__setattr__(
            self,
            "subject_scope",
            require_text(self.subject_scope, "subject_scope", maximum=256),
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
        if set(self.allowed_content_classes) & set(self.prohibited_content_classes):
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
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")
