"""Canonical Vitrine/Core provenance resolver for live Concord Artifact reads.

This module revalidates the frozen Candidate/Selection source chain and exact
Core Publication before a producer Artifact request can occur. It reauthorizes
the manifest read separately from Concord Artifact authorization, invokes only
the audited installed Concord public reader, and reprojects the exact source to
detect Candidate/projection drift.

It performs no Concord native Artifact I/O and imports no Concord package
directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pds_core.academic_work_registration_storage import (
    AcademicWorkRegistrationIntegrityError,
    AcademicWorkRegistrationNotFoundError,
    AcademicWorkRegistrationReadError,
    load_academic_work_registration_revision,
)
from pds_core.registry_services import (
    RegistryServiceIntegrityError,
    RegistryServiceNotFoundError,
    RegistryServiceWriteError,
    get_canonical_publication_record,
    get_canonical_publication_withdrawal,
)

from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_PROJECTION_KIND,
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
    CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
    build_concord_live_adapter,
)
from vitrine.concord_artifact_source import (
    ConcordArtifactSourceContext,
)
from vitrine.models import (
    CandidateEvaluation,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
)
from vitrine.producer_adapters import (
    ProducerProjectionError,
    ProducerReaderError,
)
from vitrine.producer_reader_services import (
    ProducerReaderServiceError,
    SourceReadAuthorizationGate,
    SourceReadAuthorizationRequest,
    build_audited_installed_producer_reader,
    read_authorized_producer_manifest,
)
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotSourceRequest,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

CONCORD_ARTIFACT_SOURCE_READ_OPERATION: Final[str] = (
    "snapshot_concord_source_read"
)
CONCORD_ARTIFACT_CONTEXT_PURPOSE: Final[str] = "build_snapshot"


def _unavailable(message: str, *, stage: str) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(
        "snapshot.source_unavailable",
        message,
        stage=stage,
    )


def _integrity(message: str, *, stage: str) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(
        "snapshot.source_integrity_failed",
        message,
        stage=stage,
    )


def _one_record(
    records: tuple[object, ...],
    record_type: type[object],
    field_name: str,
    record_id: str,
    *,
    stage: str,
) -> object:
    matches = tuple(
        item
        for item in records
        if isinstance(item, record_type)
        and getattr(item, field_name) == record_id
    )
    if len(matches) != 1:
        raise _integrity(
            "Frozen Concord Snapshot provenance does not resolve uniquely.",
            stage=stage,
        )
    return matches[0]


def _publication_matches_reference(publication: object, reference: object) -> bool:
    return (
        getattr(publication, "schema_version", None)
        == getattr(reference, "core_publication_schema_version", None)
        and getattr(publication, "publication_id", None)
        == getattr(reference, "publication_id", None)
        and getattr(publication, "work", None) == getattr(reference, "work", None)
        and getattr(publication, "source_record", None)
        == getattr(reference, "source_record", None)
        and getattr(publication, "publication_kind", None)
        == getattr(reference, "publication_kind", None)
        and tuple(getattr(publication, "capabilities", ()))
        == tuple(getattr(reference, "capabilities", ()))
        and getattr(publication, "record_set_id", None)
        == getattr(reference, "record_set_id", None)
        and getattr(publication, "record_set_revision", None)
        == getattr(reference, "record_set_revision", None)
        and getattr(publication, "manifest_contract_version", None)
        == getattr(reference, "manifest_contract_version", None)
        and getattr(publication, "manifest_path", None)
        == getattr(reference, "manifest_path", None)
        and getattr(publication, "manifest_digest_algorithm", None)
        == getattr(reference, "manifest_digest_algorithm", None)
        and getattr(publication, "manifest_digest", None)
        == getattr(reference, "manifest_digest", None)
        and getattr(publication, "published_at", None)
        == getattr(reference, "published_at", None)
        and getattr(publication, "academic_work_registration_revision", None)
        == getattr(reference, "academic_work_registration_revision", None)
        and getattr(publication, "supersedes_publication_id", None)
        == getattr(reference, "supersedes_publication_id", None)
    )


def _registration_matches_snapshot(
    registration: object,
    snapshot: object,
) -> bool:
    return (
        getattr(registration, "registration_revision", None)
        == getattr(snapshot, "registration_revision", None)
        and getattr(registration, "producer_contract_version", None)
        == getattr(snapshot, "producer_contract_version", None)
        and getattr(registration, "title", None)
        == getattr(snapshot, "title_snapshot", None)
        and getattr(registration, "work_kind", None)
        == getattr(snapshot, "work_kind", None)
        and getattr(registration, "academic_intent", None)
        == getattr(snapshot, "academic_intent", None)
        and getattr(registration, "lifecycle", None)
        == getattr(snapshot, "lifecycle", None)
        and tuple(getattr(registration, "source_records", ()))
        == tuple(getattr(snapshot, "source_records", ()))
    )


def _require_live_concord_contract(
    publication: object,
    registration: object,
) -> None:
    source = getattr(publication, "source_record", None)
    if (
        getattr(getattr(publication, "work", None), "module_id", None) != "concord"
        or getattr(publication, "schema_version", None) != "1"
        or getattr(publication, "publication_kind", None) != "academic_result_set"
        or getattr(publication, "manifest_contract_version", None)
        != "concord_academic_result_manifest_v1"
        or getattr(registration, "producer_contract_version", None)
        != "concord_academic_work_v1"
        or source is None
        or getattr(source, "module_id", None) != "concord"
        or getattr(source, "record_kind", None) != "activity"
        or getattr(source, "contract_version", None) != "concord_activity_v1"
        or "criterion_scores" not in tuple(getattr(publication, "capabilities", ()))
    ):
        raise _integrity(
            "Frozen source no longer satisfies the live Concord contract.",
            stage="concord_artifact_core_contract",
        )


def _assert_candidate_source_matches_entry(
    request: SnapshotSourceRequest,
    records: tuple[object, ...],
) -> PortfolioCandidate:
    entry = request.entry_plan
    if (
        entry.candidate_id is None
        or entry.candidate_evaluation_id is None
        or entry.selection_id is None
        or entry.source_publication_id is None
        or entry.source_artifact is None
    ):
        raise _integrity(
            "Concord Snapshot Entry is missing frozen Candidate provenance.",
            stage="concord_artifact_candidate",
        )

    candidate = _one_record(
        records,
        PortfolioCandidate,
        "candidate_id",
        entry.candidate_id,
        stage="concord_artifact_candidate",
    )
    assert isinstance(candidate, PortfolioCandidate)
    evaluation = _one_record(
        records,
        CandidateEvaluation,
        "candidate_evaluation_id",
        entry.candidate_evaluation_id,
        stage="concord_artifact_candidate",
    )
    assert isinstance(evaluation, CandidateEvaluation)
    selection = _one_record(
        records,
        PortfolioSelection,
        "selection_id",
        entry.selection_id,
        stage="concord_artifact_selection",
    )
    assert isinstance(selection, PortfolioSelection)

    if entry.placement_id is not None:
        placement = _one_record(
            records,
            PortfolioPlacement,
            "placement_id",
            entry.placement_id,
            stage="concord_artifact_selection",
        )
        assert isinstance(placement, PortfolioPlacement)
        if (
            placement.selection_id != selection.selection_id
            or placement.portfolio_id != candidate.portfolio_id
            or placement.profile_binding_id != candidate.profile_binding_id
        ):
            raise _integrity(
                "Concord Snapshot Placement disagrees with the frozen Selection.",
                stage="concord_artifact_selection",
            )

    endpoint = candidate.source_endpoint
    if (
        candidate.candidate_evaluation_id != evaluation.candidate_evaluation_id
        or evaluation.source_endpoint != endpoint
        or selection.candidate_id != candidate.candidate_id
        or selection.candidate_evaluation_id != candidate.candidate_evaluation_id
        or (
            selection.portfolio_id,
            selection.portfolio_subject_id,
            selection.profile_binding_id,
            selection.profile_revision,
        )
        != (
            candidate.portfolio_id,
            candidate.portfolio_subject_id,
            candidate.profile_binding_id,
            candidate.profile_revision,
        )
        or entry.source_publication_id
        != endpoint.core_publication.publication_id
        or entry.producer_module_id != "concord"
        or endpoint.producer_source.producer_module_id != "concord"
        or endpoint.producer_source.source_record_kind != "score_evidence_link"
        or endpoint.producer_source.projection_contract_version
        != CONCORD_LIVE_PROJECTION_CONTRACT_VERSION
        or entry.projection_kind != CONCORD_ARTIFACT_REPRESENTATION_KIND
        or entry.projection_contract_version
        != CONCORD_LIVE_PROJECTION_CONTRACT_VERSION
        or entry.source_artifact != endpoint.source_artifact
        or endpoint.source_artifact is None
        or endpoint.source_artifact.artifact_kind != "collaborative_artifact"
        or endpoint.source_artifact.representation_kind
        != CONCORD_ARTIFACT_REPRESENTATION_KIND
        or endpoint.source_artifact.source_locator is not None
        or endpoint.source_artifact.source_digest is not None
        or endpoint.source_artifact.byte_size is not None
        or entry.producer_source_digest_claim is not None
        or entry.media_type != endpoint.source_artifact.media_type
    ):
        raise _integrity(
            "Concord Snapshot Entry does not preserve the exact Candidate source.",
            stage="concord_artifact_candidate",
        )
    return candidate


def _assert_reprojection_matches_candidate(
    *,
    candidate: PortfolioCandidate,
    public_model: object,
) -> None:
    try:
        batch = build_concord_live_adapter().project(public_model)
    except ProducerProjectionError as error:
        raise _integrity(
            "Verified Concord manifest could not reproduce the frozen Candidate source.",
            stage="concord_artifact_reprojection",
        ) from error

    endpoint = candidate.source_endpoint
    matches = tuple(
        source
        for source in batch.projected_sources
        if source.projection_kind == CONCORD_ARTIFACT_PROJECTION_KIND
        and source.producer_source == endpoint.producer_source
        and source.source_artifact == endpoint.source_artifact
        and source.source_privacy == endpoint.source_privacy
    )
    if len(matches) != 1:
        raise _integrity(
            "Verified Concord manifest does not reproduce one exact Candidate source.",
            stage="concord_artifact_reprojection",
        )

    projected = matches[0]
    relationship_keys = {
        (
            item.source_subject_kind,
            item.source_subject_id,
            item.relationship_kind,
            item.relationship_authority,
            item.supporting_source_reference,
        )
        for item in projected.source_relationships
    }
    for assertion in endpoint.subject_relationship_assertions:
        key = (
            assertion.source_subject_kind,
            assertion.source_subject_id,
            assertion.relationship_kind,
            assertion.relationship_authority,
            assertion.supporting_source_reference,
        )
        if key not in relationship_keys:
            raise _integrity(
                "Frozen Candidate relationship is absent from the verified Concord projection.",
                stage="concord_artifact_reprojection",
            )


@dataclass(frozen=True, slots=True)
class CanonicalConcordArtifactSourceContextResolver:
    """Resolve one selected Concord Artifact from canonical Vitrine/Core state."""

    workspace_root: Path
    source_read_authorization_gate: SourceReadAuthorizationGate
    purpose: str = CONCORD_ARTIFACT_CONTEXT_PURPOSE

    def __post_init__(self) -> None:
        root = Path(self.workspace_root).absolute()
        object.__setattr__(self, "workspace_root", root)
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Concord Artifact context purpose is invalid.",
                stage="concord_artifact_context",
            )

    def resolve(
        self,
        request: SnapshotSourceRequest,
    ) -> ConcordArtifactSourceContext:
        try:
            _current, loaded_records = load_current_records_with_state(
                self.workspace_root
            )
        except (VitrineStorageNotFoundError, VitrineStorageError) as error:
            raise _unavailable(
                "Vitrine canonical source context is unavailable.",
                stage="concord_artifact_candidate",
            ) from error
        records = tuple(loaded_records)
        candidate = _assert_candidate_source_matches_entry(request, records)
        endpoint = candidate.source_endpoint
        reference = endpoint.core_publication

        try:
            publication = get_canonical_publication_record(
                self.workspace_root,
                reference.publication_id,
            )
        except RegistryServiceNotFoundError as error:
            raise _unavailable(
                "Canonical Concord Publication is unavailable.",
                stage="concord_artifact_core_publication",
            ) from error
        except (
            RegistryServiceIntegrityError,
            RegistryServiceWriteError,
        ) as error:
            raise _integrity(
                "Canonical Concord Publication could not be verified.",
                stage="concord_artifact_core_publication",
            ) from error
        if not _publication_matches_reference(publication, reference):
            raise _integrity(
                "Canonical Concord Publication differs from the frozen Candidate source.",
                stage="concord_artifact_core_publication",
            )

        try:
            withdrawal = get_canonical_publication_withdrawal(
                self.workspace_root,
                publication.publication_id,
            )
        except (
            RegistryServiceNotFoundError,
            RegistryServiceIntegrityError,
            RegistryServiceWriteError,
        ) as error:
            raise _integrity(
                "Canonical Concord Publication withdrawal state could not be verified.",
                stage="concord_artifact_core_publication",
            ) from error
        if withdrawal is not None:
            raise _unavailable(
                "Frozen Concord Publication has been withdrawn.",
                stage="concord_artifact_core_publication",
            )

        snapshot = reference.registration_snapshot
        revision = reference.academic_work_registration_revision
        if snapshot is None or revision is None:
            raise _integrity(
                "Frozen Concord Publication is missing Academic Work provenance.",
                stage="concord_artifact_registration",
            )
        try:
            registration = load_academic_work_registration_revision(
                self.workspace_root,
                publication.work,
                revision,
            )
        except AcademicWorkRegistrationNotFoundError as error:
            raise _unavailable(
                "Frozen Concord Academic Work Registration is unavailable.",
                stage="concord_artifact_registration",
            ) from error
        except (
            AcademicWorkRegistrationIntegrityError,
            AcademicWorkRegistrationReadError,
        ) as error:
            raise _integrity(
                "Frozen Concord Academic Work Registration could not be verified.",
                stage="concord_artifact_registration",
            ) from error
        if not _registration_matches_snapshot(registration, snapshot):
            raise _integrity(
                "Concord Academic Work Registration differs from frozen Candidate provenance.",
                stage="concord_artifact_registration",
            )
        _require_live_concord_contract(publication, registration)

        authorization_request = SourceReadAuthorizationRequest(
            portfolio_id=candidate.portfolio_id,
            portfolio_subject_id=candidate.portfolio_subject_id,
            publication_id=publication.publication_id,
            operation=CONCORD_ARTIFACT_SOURCE_READ_OPERATION,
            purpose=self.purpose,
        )
        reader = build_audited_installed_producer_reader("concord")
        try:
            read = read_authorized_producer_manifest(
                self.workspace_root,
                publication=publication,
                authorization_gate=self.source_read_authorization_gate,
                authorization_request=authorization_request,
                reader=reader,
            )
        except ProducerReaderServiceError as error:
            if error.code in {
                "source_read.authorization_denied",
                "source_read.authorization_unresolved",
                "source_read.manifest_missing",
            }:
                raise _unavailable(
                    "Concord manifest source read could not be authorized or resolved.",
                    stage="concord_artifact_manifest",
                ) from error
            raise _integrity(
                "Concord manifest integrity verification failed.",
                stage="concord_artifact_manifest",
            ) from error
        except ProducerReaderError as error:
            if error.code == "reader.unavailable":
                raise _unavailable(
                    "Installed Concord public reader is unavailable.",
                    stage="concord_artifact_manifest",
                ) from error
            raise _integrity(
                "Installed Concord public reader rejected the frozen manifest.",
                stage="concord_artifact_manifest",
            ) from error

        _assert_reprojection_matches_candidate(
            candidate=candidate,
            public_model=read.public_model,
        )

        return ConcordArtifactSourceContext(
            workspace_root=self.workspace_root,
            manifest=read.public_model,
            source_publication_id=publication.publication_id,
            score_evidence_link_id=endpoint.producer_source.source_record_id,
        )


def build_canonical_concord_artifact_source_context_resolver(
    workspace_root: str | Path,
    *,
    source_read_authorization_gate: SourceReadAuthorizationGate,
    purpose: str = CONCORD_ARTIFACT_CONTEXT_PURPOSE,
) -> CanonicalConcordArtifactSourceContextResolver:
    """Build the production resolver without importing Concord."""

    return CanonicalConcordArtifactSourceContextResolver(
        workspace_root=Path(workspace_root),
        source_read_authorization_gate=source_read_authorization_gate,
        purpose=purpose,
    )


__all__ = [
    "CONCORD_ARTIFACT_CONTEXT_PURPOSE",
    "CONCORD_ARTIFACT_SOURCE_READ_OPERATION",
    "CanonicalConcordArtifactSourceContextResolver",
    "build_canonical_concord_artifact_source_context_resolver",
]
