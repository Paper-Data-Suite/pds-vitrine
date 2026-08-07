"""Candidate evaluation and positive Candidate models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    lower_key_tuple,
    require_aware_datetime,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_record_envelope,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, ProfileRevisionRef
from .sources import (
    CorePublicationSourceReference,
    PortfolioSubjectRelationshipAssertion,
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)

AVAILABILITY_DIMENSIONS: Final[frozenset[str]] = frozenset(
    {
        "canonical_publication",
        "registration",
        "series_state",
        "producer_profile",
        "adapter_support",
        "producer_reader",
        "manifest_integrity",
        "producer_parse",
        "source_resolution",
        "artifact_availability",
        "source_authorization",
        "subject_relationship",
        "profile_eligibility",
        "disclosure_review",
    }
)
EVALUATION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"eligible", "conditionally_eligible", "ineligible", "unresolved", "suppressed"}
)
CANDIDATE_CONDITION_STATES: Final[frozenset[str]] = frozenset(
    {
        "ready_for_consideration",
        "review_required",
        "rights_review_required",
        "collaborator_review_required",
        "accessible_representation_required",
        "teacher_confirmation_required",
    }
)

CANDIDATE_EVALUATION_RECORD_TYPE: Final[str] = "candidate_evaluation"
CANDIDATE_RECORD_TYPE: Final[str] = "portfolio_candidate"


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateAvailabilityObservation:
    dimension: str
    outcome: str
    checked_at: datetime
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimension",
            require_enum(self.dimension, "dimension", AVAILABILITY_DIMENSIONS),
        )
        object.__setattr__(
            self,
            "outcome",
            require_controlled_key(self.outcome, "outcome"),
        )
        object.__setattr__(
            self,
            "checked_at",
            require_aware_datetime(self.checked_at, "checked_at"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            lower_key_tuple(self.reason_codes, "reason_codes"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateSourceEndpoint:
    core_publication: CorePublicationSourceReference
    producer_source: ProducerSourceReference
    source_artifact: SourceArtifactReference | None
    subject_relationship_assertions: tuple[
        PortfolioSubjectRelationshipAssertion, ...
    ]
    source_privacy: SourcePrivacyMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.core_publication, CorePublicationSourceReference):
            raise VitrineModelValidationError("core_publication must be a CorePublicationSourceReference.")
        if not isinstance(self.producer_source, ProducerSourceReference):
            raise VitrineModelValidationError("producer_source must be a ProducerSourceReference.")
        if self.source_artifact is not None and not isinstance(
            self.source_artifact, SourceArtifactReference
        ):
            raise VitrineModelValidationError("source_artifact must be a SourceArtifactReference or null.")
        object.__setattr__(
            self,
            "subject_relationship_assertions",
            tuple(self.subject_relationship_assertions),
        )
        if any(
            not isinstance(item, PortfolioSubjectRelationshipAssertion)
            for item in self.subject_relationship_assertions
        ):
            raise VitrineModelValidationError(
                "subject_relationship_assertions must contain assertion values."
            )
        ids = [item.assertion_id for item in self.subject_relationship_assertions]
        if len(set(ids)) != len(ids):
            raise VitrineModelValidationError("subject relationship assertion IDs must be unique.")
        if not isinstance(self.source_privacy, SourcePrivacyMetadata):
            raise VitrineModelValidationError("source_privacy must be SourcePrivacyMetadata.")
        if (
            self.producer_source.producer_module_id
            != self.core_publication.work.module_id
        ):
            raise VitrineModelValidationError(
                "producer source module must match Core publication work module."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvaluation:
    candidate_evaluation_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    requesting_actor: ActorAttribution
    purpose: str
    source_endpoint: CandidateSourceEndpoint | None
    availability_observations: tuple[CandidateAvailabilityObservation, ...]
    matched_profile_rule_ids: tuple[str, ...]
    eligible_section_ids: tuple[str, ...]
    outcome: str
    reason_codes: tuple[str, ...]
    evaluated_at: datetime
    evaluator_contract_version: str
    predecessor_evaluation_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=CANDIDATE_EVALUATION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, CANDIDATE_EVALUATION_RECORD_TYPE
        )
        for field_name in (
            "candidate_evaluation_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
        ):
            object.__setattr__(
                self, field_name, require_identifier(getattr(self, field_name), field_name)
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        if not isinstance(self.requesting_actor, ActorAttribution):
            raise VitrineModelValidationError("requesting_actor must be ActorAttribution.")
        object.__setattr__(
            self, "purpose", require_text(self.purpose, "purpose", maximum=500)
        )
        if self.source_endpoint is not None and not isinstance(
            self.source_endpoint, CandidateSourceEndpoint
        ):
            raise VitrineModelValidationError("source_endpoint must be CandidateSourceEndpoint or null.")
        object.__setattr__(
            self,
            "availability_observations",
            tuple(self.availability_observations),
        )
        if any(
            not isinstance(item, CandidateAvailabilityObservation)
            for item in self.availability_observations
        ):
            raise VitrineModelValidationError(
                "availability_observations must contain observation values."
            )
        dimensions = [item.dimension for item in self.availability_observations]
        if len(set(dimensions)) != len(dimensions):
            raise VitrineModelValidationError("availability dimensions must be unique.")
        object.__setattr__(
            self,
            "matched_profile_rule_ids",
            identifier_tuple(
                self.matched_profile_rule_ids, "matched_profile_rule_ids"
            ),
        )
        object.__setattr__(
            self,
            "eligible_section_ids",
            identifier_tuple(self.eligible_section_ids, "eligible_section_ids"),
        )
        object.__setattr__(
            self,
            "outcome",
            require_enum(self.outcome, "outcome", EVALUATION_OUTCOMES),
        )
        object.__setattr__(
            self, "reason_codes", lower_key_tuple(self.reason_codes, "reason_codes")
        )
        if self.outcome in {"eligible", "conditionally_eligible"}:
            if self.source_endpoint is None:
                raise VitrineModelValidationError("positive evaluations require source_endpoint.")
            if not self.eligible_section_ids:
                raise VitrineModelValidationError("positive evaluations require eligible_section_ids.")
        object.__setattr__(
            self,
            "evaluated_at",
            require_aware_datetime(self.evaluated_at, "evaluated_at"),
        )
        object.__setattr__(
            self,
            "evaluator_contract_version",
            require_identifier(
                self.evaluator_contract_version, "evaluator_contract_version"
            ),
        )
        if self.predecessor_evaluation_id is not None:
            predecessor = require_identifier(
                self.predecessor_evaluation_id, "predecessor_evaluation_id"
            )
            if predecessor == self.candidate_evaluation_id:
                raise VitrineModelValidationError(
                    "predecessor_evaluation_id must differ from candidate_evaluation_id."
                )
            object.__setattr__(self, "predecessor_evaluation_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioCandidate:
    candidate_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    candidate_evaluation_id: str
    source_endpoint: CandidateSourceEndpoint
    eligible_profile_rule_ids: tuple[str, ...]
    eligible_section_ids: tuple[str, ...]
    condition_state: str
    display_snapshot: str
    created_at: datetime
    created_by: ActorAttribution
    predecessor_candidate_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=CANDIDATE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, CANDIDATE_RECORD_TYPE
        )
        for field_name in (
            "candidate_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "candidate_evaluation_id",
        ):
            object.__setattr__(
                self, field_name, require_identifier(getattr(self, field_name), field_name)
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        if not isinstance(self.source_endpoint, CandidateSourceEndpoint):
            raise VitrineModelValidationError("source_endpoint must be CandidateSourceEndpoint.")
        object.__setattr__(
            self,
            "eligible_profile_rule_ids",
            identifier_tuple(
                self.eligible_profile_rule_ids,
                "eligible_profile_rule_ids",
            ),
        )
        object.__setattr__(
            self,
            "eligible_section_ids",
            identifier_tuple(
                self.eligible_section_ids, "eligible_section_ids", nonempty=True
            ),
        )
        object.__setattr__(
            self,
            "condition_state",
            require_enum(
                self.condition_state,
                "condition_state",
                CANDIDATE_CONDITION_STATES,
            ),
        )
        object.__setattr__(
            self,
            "display_snapshot",
            require_text(self.display_snapshot, "display_snapshot", maximum=500),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")
        if self.predecessor_candidate_id is not None:
            predecessor = require_identifier(
                self.predecessor_candidate_id, "predecessor_candidate_id"
            )
            if predecessor == self.candidate_id:
                raise VitrineModelValidationError(
                    "predecessor_candidate_id must differ from candidate_id."
                )
            object.__setattr__(self, "predecessor_candidate_id", predecessor)
