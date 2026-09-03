"""Canonical Vitrine/Core provenance resolver for live Quillan Artifact reads.

Issue #60 Slice 4 revalidates the frozen Candidate/Selection source chain and exact
Core Publication before a Quillan Artifact request can occur. It separately
authorizes and rereads the immutable public manifest through the audited installed
reader, reprojects the exact source, and returns only the producer context required
by the Slice-3 authorization-gated Artifact provider.

This module performs no Quillan native Artifact I/O and imports no Quillan package
directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, cast

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
from vitrine.quillan_adapter import build_quillan_live_adapter
from vitrine.quillan_artifact_source import QuillanArtifactSourceContext
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
    quillan_review_source_id,
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

QUILLAN_ARTIFACT_SOURCE_READ_OPERATION: Final[str] = "snapshot_quillan_source_read"
QUILLAN_ARTIFACT_CONTEXT_PURPOSE: Final[str] = "build_snapshot"


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
        if isinstance(item, record_type) and getattr(item, field_name) == record_id
    )
    if len(matches) != 1:
        raise _integrity(
            "Frozen Quillan Snapshot provenance does not resolve uniquely.",
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


def _registration_matches_snapshot(registration: object, snapshot: object) -> bool:
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


def _require_live_quillan_contract(publication: object, registration: object) -> None:
    work = getattr(publication, "work", None)
    registration_sources = tuple(getattr(registration, "source_records", ()))
    registration_source = registration_sources[0] if len(registration_sources) == 1 else None
    if (
        getattr(work, "module_id", None) != "quillan"
        or getattr(publication, "schema_version", None) != "1"
        or getattr(publication, "publication_kind", None) != "academic_result_set"
        or getattr(publication, "manifest_contract_version", None)
        != "quillan_academic_result_manifest_v1"
        or getattr(registration, "producer_contract_version", None)
        != "quillan_academic_work_v1"
        or getattr(publication, "source_record", None) is not None
        or "standards_ratings" not in tuple(getattr(publication, "capabilities", ()))
        or registration_source is None
        or getattr(registration_source, "module_id", None) != "quillan"
        or getattr(registration_source, "record_kind", None) != "assignment"
        or getattr(registration_source, "record_id", None)
        != getattr(work, "work_id", None)
        or getattr(registration_source, "contract_version", None) != "2"
    ):
        raise _integrity(
            "Frozen source no longer satisfies the live Quillan contract.",
            stage="quillan_artifact_core_contract",
        )


def _representation_spec(representation_kind: str) -> tuple[str, str, str]:
    if representation_kind == QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND:
        return (
            "student_work",
            QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
            QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
        )
    if representation_kind == QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND:
        return (
            "feedback_pdf",
            QUILLAN_FEEDBACK_ARTIFACT_KIND,
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
        )
    if representation_kind == QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND:
        return (
            "feedback_markdown",
            QUILLAN_FEEDBACK_ARTIFACT_KIND,
            QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
        )
    raise _integrity(
        "Frozen Quillan Candidate does not identify an Artifact-capable representation.",
        stage="quillan_artifact_candidate",
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
            "Quillan Snapshot Entry is missing frozen Candidate provenance.",
            stage="quillan_artifact_candidate",
        )

    candidate = _one_record(
        records,
        PortfolioCandidate,
        "candidate_id",
        entry.candidate_id,
        stage="quillan_artifact_candidate",
    )
    assert isinstance(candidate, PortfolioCandidate)
    evaluation = _one_record(
        records,
        CandidateEvaluation,
        "candidate_evaluation_id",
        entry.candidate_evaluation_id,
        stage="quillan_artifact_candidate",
    )
    assert isinstance(evaluation, CandidateEvaluation)
    selection = _one_record(
        records,
        PortfolioSelection,
        "selection_id",
        entry.selection_id,
        stage="quillan_artifact_selection",
    )
    assert isinstance(selection, PortfolioSelection)

    if entry.placement_id is not None:
        placement = _one_record(
            records,
            PortfolioPlacement,
            "placement_id",
            entry.placement_id,
            stage="quillan_artifact_selection",
        )
        assert isinstance(placement, PortfolioPlacement)
        if (
            placement.selection_id != selection.selection_id
            or placement.portfolio_id != candidate.portfolio_id
            or placement.profile_binding_id != candidate.profile_binding_id
        ):
            raise _integrity(
                "Quillan Snapshot Placement disagrees with the frozen Selection.",
                stage="quillan_artifact_selection",
            )

    endpoint = candidate.source_endpoint
    source_artifact = endpoint.source_artifact
    if source_artifact is None:
        raise _integrity(
            "Quillan Candidate has no exact source Artifact.",
            stage="quillan_artifact_candidate",
        )
    request_kind, artifact_kind, media_type = _representation_spec(
        source_artifact.representation_kind
    )
    producer_source = endpoint.producer_source
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
        or entry.source_publication_id != endpoint.core_publication.publication_id
        or entry.producer_module_id != "quillan"
        or producer_source.producer_module_id != "quillan"
        or producer_source.source_record_kind != "artifact_capability"
        or producer_source.source_record_id != source_artifact.artifact_id
        or producer_source.native_revision != source_artifact.native_revision
        or producer_source.native_disposition != request_kind
        or producer_source.projection_contract_version
        != QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION
        or entry.projection_kind != source_artifact.representation_kind
        or entry.projection_contract_version
        != QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION
        or entry.source_artifact != source_artifact
        or source_artifact.artifact_kind != artifact_kind
        or source_artifact.media_type != media_type
        or source_artifact.source_locator is not None
        or source_artifact.source_digest is not None
        or source_artifact.byte_size is not None
        or entry.producer_source_digest_claim is not None
        or entry.media_type != source_artifact.media_type
    ):
        raise _integrity(
            "Quillan Snapshot Entry does not preserve the exact Candidate source.",
            stage="quillan_artifact_candidate",
        )
    return candidate


class _EvidenceReference(Protocol):
    evidence_id: str


class _DigitalProvenance(Protocol):
    evidence_references: tuple[_EvidenceReference, ...]


class _Submission(Protocol):
    entry_method: str
    digital_provenance: _DigitalProvenance | None


class _StudentResult(Protocol):
    student_id: str
    submission: _Submission


class _Work(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _Manifest(Protocol):
    work: _Work
    students: tuple[_StudentResult, ...]


def _manifest_student(manifest: _Manifest, student_id: str) -> _StudentResult:
    matches = tuple(item for item in manifest.students if item.student_id == student_id)
    if len(matches) != 1:
        raise _integrity(
            "Verified Quillan manifest does not resolve one represented student.",
            stage="quillan_artifact_reprojection",
        )
    return matches[0]


def _relationship_key(value: object) -> tuple[object, ...]:
    return (
        getattr(value, "source_subject_kind", None),
        getattr(value, "source_subject_id", None),
        getattr(value, "relationship_kind", None),
        getattr(value, "relationship_authority", None),
        getattr(value, "supporting_source_reference", None),
    )


def _assert_reprojection_matches_candidate(
    *,
    candidate: PortfolioCandidate,
    public_model: object,
) -> tuple[str, str, str | None]:
    try:
        batch = build_quillan_live_adapter().project(public_model)
    except ProducerProjectionError as error:
        raise _integrity(
            "Verified Quillan manifest could not reproduce the frozen Candidate source.",
            stage="quillan_artifact_reprojection",
        ) from error

    endpoint = candidate.source_endpoint
    source_artifact = endpoint.source_artifact
    assert source_artifact is not None
    matches = tuple(
        source
        for source in batch.projected_sources
        if source.projection_kind == source_artifact.representation_kind
        and source.producer_source == endpoint.producer_source
        and source.source_artifact == source_artifact
        and source.source_privacy == endpoint.source_privacy
    )
    if len(matches) != 1:
        raise _integrity(
            "Verified Quillan manifest does not reproduce one exact Candidate source.",
            stage="quillan_artifact_reprojection",
        )

    projected = matches[0]
    relationship_keys = {_relationship_key(item) for item in projected.source_relationships}
    for assertion in endpoint.subject_relationship_assertions:
        if _relationship_key(assertion) not in relationship_keys:
            raise _integrity(
                "Frozen Candidate relationship is absent from the verified Quillan projection.",
                stage="quillan_artifact_reprojection",
            )

    student_relationships = tuple(
        item
        for item in projected.source_relationships
        if item.source_subject_kind == "core_student"
        and item.relationship_kind == "submission_subject"
        and item.relationship_authority == "quillan"
    )
    if len(student_relationships) != 1:
        raise _integrity(
            "Verified Quillan Artifact source does not identify one exact student.",
            stage="quillan_artifact_reprojection",
        )
    student_id = student_relationships[0].source_subject_id
    request_kind, _, _ = _representation_spec(source_artifact.representation_kind)
    producer_source = projected.producer_source
    if (
        producer_source.native_disposition != request_kind
        or producer_source.source_record_id != source_artifact.artifact_id
        or student_relationships[0].supporting_source_reference
        != source_artifact.artifact_id
    ):
        raise _integrity(
            "Verified Quillan Artifact capability disagrees with frozen source identity.",
            stage="quillan_artifact_reprojection",
        )

    manifest = cast(_Manifest, public_model)
    try:
        if manifest.work.module_id != "quillan":
            raise ValueError
    except Exception as error:
        raise _integrity(
            "Verified Quillan manifest has incompatible work identity.",
            stage="quillan_artifact_reprojection",
        ) from error
    student = _manifest_student(manifest, student_id)
    expected_lineage = quillan_review_source_id(
        class_id=manifest.work.class_id,
        work_id=manifest.work.work_id,
        student_id=student_id,
    )
    if producer_source.lineage_reference != expected_lineage:
        raise _integrity(
            "Verified Quillan Artifact capability has incompatible review lineage.",
            stage="quillan_artifact_reprojection",
        )

    if request_kind == "student_work":
        provenance = student.submission.digital_provenance
        if student.submission.entry_method != "pds2_response_pages" or provenance is None:
            raise _integrity(
                "Verified Quillan student-work Candidate is not represented digital evidence.",
                stage="quillan_artifact_reprojection",
            )
        evidence_matches = tuple(
            reference
            for reference in provenance.evidence_references
            if quillan_evidence_source_id(
                class_id=manifest.work.class_id,
                work_id=manifest.work.work_id,
                student_id=student_id,
                evidence_id=reference.evidence_id,
            )
            == source_artifact.artifact_id
        )
        if len(evidence_matches) != 1:
            raise _integrity(
                "Verified Quillan manifest does not reproduce the exact selected evidence.",
                stage="quillan_artifact_reprojection",
            )
        return student_id, request_kind, evidence_matches[0].evidence_id

    expected_feedback_id = quillan_feedback_source_id(
        class_id=manifest.work.class_id,
        work_id=manifest.work.work_id,
        student_id=student_id,
        artifact_request_kind=request_kind,
    )
    if expected_feedback_id != source_artifact.artifact_id:
        raise _integrity(
            "Verified Quillan manifest does not reproduce the exact feedback capability.",
            stage="quillan_artifact_reprojection",
        )
    return student_id, request_kind, None


@dataclass(frozen=True, slots=True)
class CanonicalQuillanArtifactSourceContextResolver:
    """Resolve one selected Quillan Artifact from canonical Vitrine/Core state."""

    workspace_root: Path
    source_read_authorization_gate: SourceReadAuthorizationGate
    purpose: str = QUILLAN_ARTIFACT_CONTEXT_PURPOSE

    def __post_init__(self) -> None:
        root = Path(self.workspace_root).absolute()
        object.__setattr__(self, "workspace_root", root)
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise SnapshotMaterializationError(
                "snapshot.invalid_request",
                "Quillan Artifact context purpose is invalid.",
                stage="quillan_artifact_context",
            )

    def resolve(self, request: SnapshotSourceRequest) -> QuillanArtifactSourceContext:
        try:
            _current, loaded_records = load_current_records_with_state(self.workspace_root)
        except (VitrineStorageNotFoundError, VitrineStorageError) as error:
            raise _unavailable(
                "Vitrine canonical source context is unavailable.",
                stage="quillan_artifact_candidate",
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
                "Canonical Quillan Publication is unavailable.",
                stage="quillan_artifact_core_publication",
            ) from error
        except (RegistryServiceIntegrityError, RegistryServiceWriteError) as error:
            raise _integrity(
                "Canonical Quillan Publication could not be verified.",
                stage="quillan_artifact_core_publication",
            ) from error
        if not _publication_matches_reference(publication, reference):
            raise _integrity(
                "Canonical Quillan Publication differs from the frozen Candidate source.",
                stage="quillan_artifact_core_publication",
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
                "Canonical Quillan Publication withdrawal state could not be verified.",
                stage="quillan_artifact_core_publication",
            ) from error
        if withdrawal is not None:
            raise _unavailable(
                "Frozen Quillan Publication has been withdrawn.",
                stage="quillan_artifact_core_publication",
            )

        snapshot = reference.registration_snapshot
        revision = reference.academic_work_registration_revision
        if snapshot is None or revision is None:
            raise _integrity(
                "Frozen Quillan Publication is missing Academic Work provenance.",
                stage="quillan_artifact_registration",
            )
        try:
            registration = load_academic_work_registration_revision(
                self.workspace_root,
                publication.work,
                revision,
            )
        except AcademicWorkRegistrationNotFoundError as error:
            raise _unavailable(
                "Frozen Quillan Academic Work Registration is unavailable.",
                stage="quillan_artifact_registration",
            ) from error
        except (
            AcademicWorkRegistrationIntegrityError,
            AcademicWorkRegistrationReadError,
        ) as error:
            raise _integrity(
                "Frozen Quillan Academic Work Registration could not be verified.",
                stage="quillan_artifact_registration",
            ) from error
        if not _registration_matches_snapshot(registration, snapshot):
            raise _integrity(
                "Quillan Academic Work Registration differs from frozen Candidate provenance.",
                stage="quillan_artifact_registration",
            )
        _require_live_quillan_contract(publication, registration)

        authorization_request = SourceReadAuthorizationRequest(
            portfolio_id=candidate.portfolio_id,
            portfolio_subject_id=candidate.portfolio_subject_id,
            publication_id=publication.publication_id,
            operation=QUILLAN_ARTIFACT_SOURCE_READ_OPERATION,
            purpose=self.purpose,
        )
        reader = build_audited_installed_producer_reader("quillan")
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
                    "Quillan manifest source read could not be authorized or resolved.",
                    stage="quillan_artifact_manifest",
                ) from error
            raise _integrity(
                "Quillan manifest integrity verification failed.",
                stage="quillan_artifact_manifest",
            ) from error
        except ProducerReaderError as error:
            if error.code == "reader.unavailable":
                raise _unavailable(
                    "Installed Quillan public reader is unavailable.",
                    stage="quillan_artifact_manifest",
                ) from error
            raise _integrity(
                "Installed Quillan public reader rejected the frozen manifest.",
                stage="quillan_artifact_manifest",
            ) from error

        student_id, artifact_request_kind, evidence_id = (
            _assert_reprojection_matches_candidate(
                candidate=candidate,
                public_model=read.public_model,
            )
        )
        return QuillanArtifactSourceContext(
            workspace_root=self.workspace_root,
            manifest=read.public_model,
            source_publication_id=publication.publication_id,
            student_id=student_id,
            artifact_request_kind=artifact_request_kind,
            evidence_id=evidence_id,
        )


def build_canonical_quillan_artifact_source_context_resolver(
    workspace_root: str | Path,
    *,
    source_read_authorization_gate: SourceReadAuthorizationGate,
    purpose: str = QUILLAN_ARTIFACT_CONTEXT_PURPOSE,
) -> CanonicalQuillanArtifactSourceContextResolver:
    """Build the production resolver without importing Quillan."""

    return CanonicalQuillanArtifactSourceContextResolver(
        workspace_root=Path(workspace_root),
        source_read_authorization_gate=source_read_authorization_gate,
        purpose=purpose,
    )


__all__ = [
    "QUILLAN_ARTIFACT_CONTEXT_PURPOSE",
    "QUILLAN_ARTIFACT_SOURCE_READ_OPERATION",
    "CanonicalQuillanArtifactSourceContextResolver",
    "build_canonical_quillan_artifact_source_context_resolver",
]
