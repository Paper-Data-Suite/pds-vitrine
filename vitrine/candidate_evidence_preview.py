"""Read-only exact-authority foundation for Candidate evidence preview.

This module resolves one persisted Candidate Inbox entry to its exact stored
CandidateSourceEndpoint. It performs no producer reads, manifest reads, Artifact
byte acquisition, temporary materialization, launching, Selection, Placement,
or persistence.

Human-readable labels are deliberately absent from request and authorization
contracts. Exact canonical references remain the only routing authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from vitrine.candidate_inbox import (
    CandidateInboxError,
    get_candidate_inbox_detail,
)
from vitrine.models import ActorAttribution, CandidateSourceEndpoint
from vitrine.models.common import (
    lower_key_tuple,
    require_enum,
    require_identifier,
    require_positive_int,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError

CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_evidence_preview_v1"
)
CANDIDATE_EVIDENCE_PREVIEW_OPERATION: Final[str] = "candidate_evidence_preview"
CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = (
    frozenset({"allowed", "denied", "unresolved"})
)
CANDIDATE_EVIDENCE_PREVIEW_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate_evidence_preview.invalid_request",
        "candidate_evidence_preview.entry_not_found",
        "candidate_evidence_preview.state_invalid",
        "candidate_evidence_preview.state_conflict",
        "candidate_evidence_preview.context_mismatch",
        "candidate_evidence_preview.source_unavailable",
        "candidate_evidence_preview.authorization_denied",
        "candidate_evidence_preview.authorization_unresolved",
    }
)


class CandidateEvidencePreviewError(RuntimeError):
    """Stable privacy-safe Candidate evidence-preview foundation failure."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in CANDIDATE_EVIDENCE_PREVIEW_CODES:
            raise ValueError(
                f"unsupported Candidate evidence-preview error code: {code}"
            )
        if not isinstance(stage, str) or not stage:
            raise ValueError("stage must be nonempty.")
        self.code = code
        self.stage = stage
        super().__init__(message)


def _optional_identifier(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    return require_identifier(value, name)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewRequest:
    """Exact persisted-entry request; display text is intentionally absent."""

    portfolio_id: str
    portfolio_subject_id: str
    entry_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    requesting_actor: ActorAttribution
    requested_purpose: str
    observed_state_revision: int

    def __post_init__(self) -> None:
        try:
            for name in ("portfolio_id", "portfolio_subject_id"):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            object.__setattr__(
                self,
                "entry_id",
                require_text(self.entry_id, "entry_id", maximum=500),
            )
            object.__setattr__(
                self,
                "candidate_id",
                _optional_identifier(self.candidate_id, "candidate_id"),
            )
            object.__setattr__(
                self,
                "candidate_evaluation_id",
                _optional_identifier(
                    self.candidate_evaluation_id,
                    "candidate_evaluation_id",
                ),
            )
            if (
                self.candidate_id is None
                and self.candidate_evaluation_id is None
            ):
                raise VitrineModelValidationError(
                    "preview requires Candidate or Evaluation authority."
                )
            if not isinstance(self.requesting_actor, ActorAttribution):
                raise VitrineModelValidationError(
                    "requesting_actor must be ActorAttribution."
                )
            object.__setattr__(
                self,
                "requested_purpose",
                require_text(
                    self.requested_purpose,
                    "requested_purpose",
                    maximum=500,
                ),
            )
            object.__setattr__(
                self,
                "observed_state_revision",
                require_positive_int(
                    self.observed_state_revision,
                    "observed_state_revision",
                ),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview request is invalid.",
                stage="request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthority:
    """Exact transient source authority resolved from canonical Vitrine state."""

    contract_version: str
    operation: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    entry_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    requesting_actor: ActorAttribution
    requested_purpose: str
    source_publication_id: str
    producer_module_id: str
    source_record_kind: str
    source_record_id: str
    source_artifact_id: str | None
    artifact_kind: str | None
    representation_kind: str | None
    media_type: str | None
    source_endpoint: CandidateSourceEndpoint

    def __post_init__(self) -> None:
        if self.contract_version != CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION:
            raise ValueError("unexpected Candidate evidence-preview contract.")
        if self.operation != CANDIDATE_EVIDENCE_PREVIEW_OPERATION:
            raise ValueError("unexpected Candidate evidence-preview operation.")
        if not isinstance(self.source_endpoint, CandidateSourceEndpoint):
            raise ValueError("source_endpoint must be CandidateSourceEndpoint.")


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthorizationRequest:
    """Exact authorization context for producer Artifact preview access."""

    operation: str
    portfolio_id: str
    portfolio_subject_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    source_publication_id: str
    producer_module_id: str
    source_artifact_id: str | None
    artifact_kind: str | None
    representation_kind: str | None
    requesting_actor: ActorAttribution
    purpose: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "operation",
                require_enum(
                    self.operation,
                    "operation",
                    frozenset({CANDIDATE_EVIDENCE_PREVIEW_OPERATION}),
                ),
            )
            for name in (
                "portfolio_id",
                "portfolio_subject_id",
                "source_publication_id",
                "producer_module_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            for name in (
                "candidate_id",
                "candidate_evaluation_id",
                "source_artifact_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    _optional_identifier(getattr(self, name), name),
                )
            for name in ("artifact_kind", "representation_kind"):
                value = getattr(self, name)
                if value is not None:
                    object.__setattr__(
                        self,
                        name,
                        require_text(value, name, maximum=256),
                    )
            if not isinstance(self.requesting_actor, ActorAttribution):
                raise VitrineModelValidationError(
                    "requesting_actor must be ActorAttribution."
                )
            object.__setattr__(
                self,
                "purpose",
                require_text(self.purpose, "purpose", maximum=500),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview authorization request is invalid.",
                stage="authorization_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthorizationDecision:
    """Explicit allow/deny/unresolved decision for preview Artifact access."""

    outcome: str
    authority_reference: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "outcome",
                require_enum(
                    self.outcome,
                    "outcome",
                    CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES,
                ),
            )
            if self.authority_reference is not None:
                object.__setattr__(
                    self,
                    "authority_reference",
                    require_text(
                        self.authority_reference,
                        "authority_reference",
                        maximum=500,
                    ),
                )
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview authorization decision is invalid.",
                stage="authorization",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Allowed Candidate evidence preview requires authority_reference.",
                stage="authorization",
            )


class CandidateEvidencePreviewAuthorizationGate(Protocol):
    def authorize(
        self,
        request: CandidateEvidencePreviewAuthorizationRequest,
    ) -> CandidateEvidencePreviewAuthorizationDecision: ...


def resolve_candidate_evidence_preview_authority(
    workspace_root: str | Path,
    request: CandidateEvidencePreviewRequest,
) -> CandidateEvidencePreviewAuthority:
    """Resolve exact persisted preview authority without producer access."""

    if not isinstance(request, CandidateEvidencePreviewRequest):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "request must be CandidateEvidencePreviewRequest.",
            stage="request",
        )

    try:
        detail = get_candidate_inbox_detail(workspace_root, request.entry_id)
    except CandidateInboxError as error:
        code = (
            "candidate_evidence_preview.entry_not_found"
            if error.code == "candidate_inbox.entry_not_found"
            else "candidate_evidence_preview.state_invalid"
        )
        raise CandidateEvidencePreviewError(
            code,
            "Exact Candidate Inbox preview authority is unavailable.",
            stage="inbox_resolution",
        ) from error

    if detail.observed_state_revision != request.observed_state_revision:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.state_conflict",
            "Vitrine state changed after the Candidate entry was observed.",
            stage="state_replay",
        )

    item = detail.item
    if (
        item.portfolio_id != request.portfolio_id
        or item.portfolio_subject_id != request.portfolio_subject_id
        or item.candidate_id != request.candidate_id
        or item.current_evaluation_id != request.candidate_evaluation_id
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.context_mismatch",
            "Candidate evidence-preview authority no longer matches the exact entry.",
            stage="context_replay",
        )

    endpoint = (
        None
        if detail.evaluation is None
        else detail.evaluation.source_endpoint
    )
    if endpoint is None and detail.candidate is not None:
        endpoint = detail.candidate.source_endpoint
    if endpoint is None:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.source_unavailable",
            "Exact persisted Candidate source authority is unavailable.",
            stage="source_resolution",
        )

    publication = endpoint.core_publication
    producer = endpoint.producer_source
    artifact = endpoint.source_artifact
    return CandidateEvidencePreviewAuthority(
        contract_version=CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
        operation=CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
        observed_state_revision=detail.observed_state_revision,
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=request.requesting_actor,
        requested_purpose=request.requested_purpose,
        source_publication_id=publication.publication_id,
        producer_module_id=producer.producer_module_id,
        source_record_kind=producer.source_record_kind,
        source_record_id=producer.source_record_id,
        source_artifact_id=None if artifact is None else artifact.artifact_id,
        artifact_kind=None if artifact is None else artifact.artifact_kind,
        representation_kind=(
            None if artifact is None else artifact.representation_kind
        ),
        media_type=None if artifact is None else artifact.media_type,
        source_endpoint=endpoint,
    )


def build_candidate_evidence_preview_authorization_request(
    authority: CandidateEvidencePreviewAuthority,
) -> CandidateEvidencePreviewAuthorizationRequest:
    """Build exact producer-Artifact authorization context from resolved state."""

    if not isinstance(authority, CandidateEvidencePreviewAuthority):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "authority must be CandidateEvidencePreviewAuthority.",
            stage="authorization_request",
        )
    return CandidateEvidencePreviewAuthorizationRequest(
        operation=CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
        portfolio_id=authority.portfolio_id,
        portfolio_subject_id=authority.portfolio_subject_id,
        candidate_id=authority.candidate_id,
        candidate_evaluation_id=authority.candidate_evaluation_id,
        source_publication_id=authority.source_publication_id,
        producer_module_id=authority.producer_module_id,
        source_artifact_id=authority.source_artifact_id,
        artifact_kind=authority.artifact_kind,
        representation_kind=authority.representation_kind,
        requesting_actor=authority.requesting_actor,
        purpose=authority.requested_purpose,
    )


def authorize_candidate_evidence_preview(
    gate: CandidateEvidencePreviewAuthorizationGate,
    request: CandidateEvidencePreviewAuthorizationRequest,
) -> CandidateEvidencePreviewAuthorizationDecision:
    """Require one explicit allowed preview decision and otherwise fail closed."""

    if not isinstance(request, CandidateEvidencePreviewAuthorizationRequest):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "Preview authorization request is invalid.",
            stage="authorization_request",
        )
    try:
        decision = gate.authorize(request)
    except Exception as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization could not be established.",
            stage="authorization",
        ) from error
    if not isinstance(
        decision,
        CandidateEvidencePreviewAuthorizationDecision,
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview gate returned an invalid decision.",
            stage="authorization",
        )
    if decision.outcome == "denied":
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_denied",
            "Candidate evidence-preview authorization was denied.",
            stage="authorization",
        )
    if decision.outcome != "allowed":
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization is unresolved.",
            stage="authorization",
        )
    return decision


__all__ = [
    "CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES",
    "CANDIDATE_EVIDENCE_PREVIEW_CODES",
    "CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION",
    "CANDIDATE_EVIDENCE_PREVIEW_OPERATION",
    "CandidateEvidencePreviewAuthorizationDecision",
    "CandidateEvidencePreviewAuthorizationGate",
    "CandidateEvidencePreviewAuthorizationRequest",
    "CandidateEvidencePreviewAuthority",
    "CandidateEvidencePreviewError",
    "CandidateEvidencePreviewRequest",
    "authorize_candidate_evidence_preview",
    "build_candidate_evidence_preview_authorization_request",
    "resolve_candidate_evidence_preview_authority",
]
