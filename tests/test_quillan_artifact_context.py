from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

import vitrine.quillan_artifact_context as context_module
from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    CorePublicationSourceReference,
    DigestReference,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    PortfolioSubjectRelationshipAssertion,
    ProducerSourceReference,
    ProfileRevisionRef,
    SnapshotEntryPlan,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.producer_adapters import (
    ProjectedProducerRelationship,
    ProjectedProducerSource,
    ProjectionDisplaySnapshot,
)
from vitrine.producer_reader_services import ProducerReaderServiceError
from vitrine.quillan_adapter import QUILLAN_PRIVACY_POLICY_REFERENCE
from vitrine.quillan_artifact_context import (
    QUILLAN_ARTIFACT_CONTEXT_PURPOSE,
    QUILLAN_ARTIFACT_SOURCE_READ_OPERATION,
    build_canonical_quillan_artifact_source_context_resolver,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_ARTIFACT_KIND,
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

NOW = datetime(2026, 9, 2, 18, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_alpha",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_alpha",
    profile_revision=1,
)
WORK = ModuleWorkRef("quillan", "class_alpha", "assignment_alpha")
ASSIGNMENT_SOURCE = ModuleRecordRef(
    "quillan",
    "assignment",
    "assignment_alpha",
    "2",
)
EVIDENCE_ID = "evidence_alpha"
EVIDENCE_BYTES = b"\x89PNG\r\n\x1a\nselected live Quillan evidence\n"
EVIDENCE_SHA256 = hashlib.sha256(EVIDENCE_BYTES).hexdigest()


class _ReadGate:
    pass


def _privacy() -> SourcePrivacyMetadata:
    return SourcePrivacyMetadata(
        classification="student_record",
        subject_scope="single_subject",
        metadata_visibility="internal",
        collaborator_information_present=False,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=False,
        multi_subject_review_required=False,
        minimum_necessary_projection_required=True,
        policy_reference=QUILLAN_PRIVACY_POLICY_REFERENCE,
    )


def _source_id(request_kind: str) -> str:
    if request_kind == "student_work":
        return quillan_evidence_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
            evidence_id=EVIDENCE_ID,
        )
    if request_kind == "feedback_pdf":
        return quillan_feedback_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
            artifact_request_kind="feedback_pdf",
        )
    raise AssertionError(request_kind)


def _representation(request_kind: str) -> tuple[str, str, str]:
    if request_kind == "student_work":
        return (
            QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
            QUILLAN_STUDENT_WORK_ARTIFACT_KIND,
            QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
        )
    if request_kind == "feedback_pdf":
        return (
            QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
            QUILLAN_FEEDBACK_ARTIFACT_KIND,
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
        )
    raise AssertionError(request_kind)


def _artifact(request_kind: str = "student_work") -> SourceArtifactReference:
    representation, artifact_kind, media_type = _representation(request_kind)
    return SourceArtifactReference(
        artifact_id=_source_id(request_kind),
        artifact_kind=artifact_kind,
        representation_kind=representation,
        media_type=media_type,
        source_locator=None,
        native_revision=4,
        source_digest=None,
        byte_size=None,
        language=None,
        accessibility_relationship=None,
    )


def _producer_source(request_kind: str = "student_work") -> ProducerSourceReference:
    source_id = _source_id(request_kind)
    return ProducerSourceReference(
        producer_module_id="quillan",
        producer_contract_version="quillan_academic_work_v1",
        source_record_kind="artifact_capability",
        source_record_id=source_id,
        source_record_contract_version=None,
        native_revision=4,
        native_lifecycle="ratings_complete",
        native_disposition=request_kind,
        lineage_reference=quillan_review_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
        ),
        reader_contract_version="vitrine_installed_producer_reader_v1",
        projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    )


def _core_reference() -> CorePublicationSourceReference:
    return CorePublicationSourceReference(
        core_publication_schema_version="1",
        publication_id="publication_alpha",
        work=WORK,
        source_record=None,
        publication_kind="academic_result_set",
        capabilities=("standards_ratings",),
        record_set_id="academic_results",
        record_set_revision=4,
        manifest_contract_version="quillan_academic_result_manifest_v1",
        manifest_path=(
            "modules/quillan/classes/class_alpha/works/assignment_alpha/"
            "exports/manifests/academic_results/4.json"
        ),
        manifest_digest_algorithm="sha256",
        manifest_digest="a" * 64,
        published_at=NOW,
        academic_work_registration_revision=2,
        registration_snapshot=AcademicWorkRegistrationSnapshot(
            registration_revision=2,
            producer_contract_version="quillan_academic_work_v1",
            title_snapshot="Writing Assignment",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=(ASSIGNMENT_SOURCE,),
        ),
        supersedes_publication_id=None,
        observed_series_state="current_selectable",
        observed_withdrawal_state="not_withdrawn",
        verified_at=NOW,
    )


def _endpoint(request_kind: str = "student_work") -> CandidateSourceEndpoint:
    source_id = _source_id(request_kind)
    assertion = PortfolioSubjectRelationshipAssertion(
        assertion_id=f"assertion_{request_kind}",
        portfolio_subject_id="subject_alpha",
        subject_link_id="subject_link_alpha",
        source_subject_kind="core_student",
        source_subject_id="student_alpha",
        relationship_kind="submission_subject",
        relationship_authority="quillan",
        supporting_source_reference=source_id,
        verified_at=NOW,
        verified_by=ACTOR,
    )
    return CandidateSourceEndpoint(
        core_publication=_core_reference(),
        producer_source=_producer_source(request_kind),
        source_artifact=_artifact(request_kind),
        subject_relationship_assertions=(assertion,),
        source_privacy=_privacy(),
    )


def _records(request_kind: str = "student_work") -> tuple[object, ...]:
    endpoint = _endpoint(request_kind)
    evaluation = CandidateEvaluation(
        candidate_evaluation_id="evaluation_alpha",
        portfolio_id="portfolio_alpha",
        portfolio_subject_id="subject_alpha",
        profile_binding_id="binding_alpha",
        profile_revision=PROFILE,
        requesting_actor=ACTOR,
        purpose="build_snapshot",
        source_endpoint=endpoint,
        availability_observations=(),
        matched_profile_rule_ids=(),
        eligible_section_ids=("student_work",),
        outcome="eligible",
        reason_codes=("candidate:eligible",),
        evaluated_at=NOW,
        evaluator_contract_version="vitrine_candidate_evaluator_v1",
    )
    candidate = PortfolioCandidate(
        candidate_id="candidate_alpha",
        portfolio_id="portfolio_alpha",
        portfolio_subject_id="subject_alpha",
        profile_binding_id="binding_alpha",
        profile_revision=PROFILE,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_endpoint=endpoint,
        eligible_profile_rule_ids=(),
        eligible_section_ids=("student_work",),
        condition_state="ready_for_consideration",
        display_snapshot="Quillan Artifact capability",
        created_at=NOW,
        created_by=ACTOR,
    )
    selection = PortfolioSelection(
        selection_id="selection_alpha",
        portfolio_id=candidate.portfolio_id,
        portfolio_subject_id=candidate.portfolio_subject_id,
        profile_binding_id=candidate.profile_binding_id,
        profile_revision=candidate.profile_revision,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        selected_at=NOW,
        selected_by=ACTOR,
        selection_reason="Teacher explicitly selected this represented Quillan source.",
    )
    placement = PortfolioPlacement(
        placement_id="placement_alpha",
        portfolio_id=candidate.portfolio_id,
        profile_binding_id=candidate.profile_binding_id,
        selection_id=selection.selection_id,
        section_id="student_work",
        presentation=None,
        placed_at=NOW,
        placed_by=ACTOR,
    )
    return evaluation, candidate, selection, placement


def _entry(request_kind: str = "student_work") -> SnapshotEntryPlan:
    representation, _, media_type = _representation(request_kind)
    target = (
        "student-work/01-quillan-selected-work"
        if request_kind == "student_work"
        else "feedback/01-quillan-feedback.pdf"
    )
    return SnapshotEntryPlan(
        entry_plan_id="entry_alpha",
        plan_position=1,
        section_id="student_work",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="selection_alpha",
        placement_id="placement_alpha",
        candidate_id="candidate_alpha",
        candidate_evaluation_id="evaluation_alpha",
        source_publication_id="publication_alpha",
        producer_module_id="quillan",
        projection_kind=representation,
        projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
        source_artifact=_artifact(request_kind),
        producer_source_digest_claim=None,
        target_relative_path=target,
        media_type=media_type,
    )


def _request(
    entry: SnapshotEntryPlan | None = None,
    *,
    request_kind: str = "student_work",
) -> SnapshotSourceRequest:
    return SnapshotSourceRequest(
        snapshot_build_plan_id="snapshot_plan_alpha",
        snapshot_build_attempt_id="snapshot_attempt_alpha",
        entry_plan=_entry(request_kind) if entry is None else entry,
    )


def _canonical_publication() -> SimpleNamespace:
    reference = _core_reference()
    return SimpleNamespace(
        schema_version=reference.core_publication_schema_version,
        publication_id=reference.publication_id,
        work=reference.work,
        source_record=reference.source_record,
        publication_kind=reference.publication_kind,
        capabilities=reference.capabilities,
        record_set_id=reference.record_set_id,
        record_set_revision=reference.record_set_revision,
        manifest_contract_version=reference.manifest_contract_version,
        manifest_path=reference.manifest_path,
        manifest_digest_algorithm=reference.manifest_digest_algorithm,
        manifest_digest=reference.manifest_digest,
        published_at=reference.published_at,
        academic_work_registration_revision=(
            reference.academic_work_registration_revision
        ),
        supersedes_publication_id=reference.supersedes_publication_id,
    )


def _registration() -> SimpleNamespace:
    snapshot = _core_reference().registration_snapshot
    assert snapshot is not None
    return SimpleNamespace(
        registration_revision=snapshot.registration_revision,
        producer_contract_version=snapshot.producer_contract_version,
        title=snapshot.title_snapshot,
        work_kind=snapshot.work_kind,
        academic_intent=snapshot.academic_intent,
        lifecycle=snapshot.lifecycle,
        source_records=snapshot.source_records,
    )


def _manifest(*, entry_method: str = "pds2_response_pages") -> SimpleNamespace:
    evidence = SimpleNamespace(
        evidence_id=EVIDENCE_ID,
        routed_evidence_sha256=EVIDENCE_SHA256,
    )
    provenance = (
        SimpleNamespace(evidence_references=(evidence,))
        if entry_method == "pds2_response_pages"
        else None
    )
    student = SimpleNamespace(
        student_id="student_alpha",
        submission=SimpleNamespace(
            entry_method=entry_method,
            digital_provenance=provenance,
        ),
    )
    return SimpleNamespace(
        work=WORK,
        record_set=SimpleNamespace(record_set_id="academic_results", revision=4),
        students=(student,),
    )


def _projected_source(request_kind: str = "student_work") -> ProjectedProducerSource:
    source_id = _source_id(request_kind)
    representation, _, _ = _representation(request_kind)
    return ProjectedProducerSource(
        projection_kind=representation,
        producer_source=_producer_source(request_kind),
        source_artifact=_artifact(request_kind),
        source_relationships=(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id="student_alpha",
                relationship_kind="submission_subject",
                relationship_authority="quillan",
                supporting_source_reference=source_id,
            ),
        ),
        source_privacy=_privacy(),
        display_snapshot=ProjectionDisplaySnapshot(
            title="Quillan Artifact capability",
        ),
    )


class _FakeAdapter:
    def __init__(
        self,
        sources: tuple[ProjectedProducerSource, ...],
    ) -> None:
        self.sources = sources

    def project(self, public_model: object) -> SimpleNamespace:
        return SimpleNamespace(projected_sources=self.sources)


def _install_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    *,
    request_kind: str = "student_work",
    projected_sources: tuple[ProjectedProducerSource, ...] | None = None,
    withdrawal: object | None = None,
) -> tuple[SimpleNamespace, list[object]]:
    manifest = _manifest()
    reads: list[object] = []
    sources = (
        (_projected_source(request_kind),)
        if projected_sources is None
        else projected_sources
    )

    monkeypatch.setattr(
        context_module,
        "load_current_records_with_state",
        lambda root: (SimpleNamespace(state_revision=9), _records(request_kind)),
    )
    monkeypatch.setattr(
        context_module,
        "get_canonical_publication_record",
        lambda root, publication_id: _canonical_publication(),
    )
    monkeypatch.setattr(
        context_module,
        "get_canonical_publication_withdrawal",
        lambda root, publication_id: withdrawal,
    )
    monkeypatch.setattr(
        context_module,
        "load_academic_work_registration_revision",
        lambda root, work, revision: _registration(),
    )
    monkeypatch.setattr(
        context_module,
        "build_quillan_live_adapter",
        lambda: _FakeAdapter(sources),
    )

    def read_manifest(*args: Any, **kwargs: Any) -> SimpleNamespace:
        reads.append(kwargs["authorization_request"])
        return SimpleNamespace(public_model=manifest)

    monkeypatch.setattr(
        context_module,
        "read_authorized_producer_manifest",
        read_manifest,
    )
    return manifest, reads


def test_production_context_revalidates_selection_core_and_selected_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, reads = _install_happy_path(monkeypatch)
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    context = resolver.resolve(_request())

    assert context.workspace_root == (tmp_path / "workspace").absolute()
    assert context.manifest is manifest
    assert context.source_publication_id == "publication_alpha"
    assert context.student_id == "student_alpha"
    assert context.artifact_request_kind == "student_work"
    assert context.evidence_id == EVIDENCE_ID
    assert len(reads) == 1
    authorization = reads[0]
    assert getattr(authorization, "portfolio_id") == "portfolio_alpha"
    assert getattr(authorization, "portfolio_subject_id") == "subject_alpha"
    assert getattr(authorization, "publication_id") == "publication_alpha"
    assert getattr(authorization, "operation") == QUILLAN_ARTIFACT_SOURCE_READ_OPERATION
    assert getattr(authorization, "purpose") == QUILLAN_ARTIFACT_CONTEXT_PURPOSE


def test_feedback_context_revalidates_exact_representation_without_existence_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, reads = _install_happy_path(monkeypatch, request_kind="feedback_pdf")
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    context = resolver.resolve(_request(request_kind="feedback_pdf"))

    assert context.manifest is manifest
    assert context.student_id == "student_alpha"
    assert context.artifact_request_kind == "feedback_pdf"
    assert context.evidence_id is None
    assert len(reads) == 1


def test_context_requires_explicit_selection_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_value, reads = _install_happy_path(monkeypatch)
    entry = replace(_entry(), selection_id="selection_other")
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request(entry))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_selection"
    assert reads == []


def test_context_refuses_withdrawn_publication_before_manifest_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_value, reads = _install_happy_path(
        monkeypatch,
        withdrawal=SimpleNamespace(publication_id="publication_alpha"),
    )
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == "quillan_artifact_core_publication"
    assert reads == []


def test_context_maps_manifest_read_denial_without_artifact_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_value, _reads = _install_happy_path(monkeypatch)

    def denied(*args: Any, **kwargs: Any) -> object:
        raise ProducerReaderServiceError(
            "source_read.authorization_denied",
            "denied",
            stage="source_authorization",
        )

    monkeypatch.setattr(context_module, "read_authorized_producer_manifest", denied)
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == "quillan_artifact_manifest"


def test_context_rejects_candidate_not_reproduced_by_verified_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_value, _reads = _install_happy_path(
        monkeypatch,
        projected_sources=(),
    )
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_reprojection"


def test_context_rejects_registration_source_contract_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_value, reads = _install_happy_path(monkeypatch)
    drifted = _registration()
    drifted.source_records = (
        ModuleRecordRef("quillan", "assignment", "assignment_alpha", "3"),
    )
    monkeypatch.setattr(
        context_module,
        "load_academic_work_registration_revision",
        lambda root, work, revision: drifted,
    )
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_registration"
    assert reads == []


def test_context_construction_remains_quillan_lazy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projections = 0

    def fail_adapter() -> object:
        nonlocal projections
        projections += 1
        raise AssertionError("Quillan projection must remain lazy")

    monkeypatch.setattr(context_module, "build_quillan_live_adapter", fail_adapter)
    resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    assert resolver.workspace_root == (tmp_path / "workspace").absolute()
    assert projections == 0


def test_selected_quillan_evidence_materializes_authorized_exact_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.quillan_artifact_source as quillan_source
    from vitrine.models import (
        SnapshotBuildAttempt,
        SnapshotBuildPlan,
        SnapshotExportPlan,
    )
    from vitrine.quillan_artifact_source import (
        QuillanArtifactAuthorizationDecision,
        build_quillan_artifact_source_provider,
    )
    from vitrine.snapshot_custody import create_snapshot_staging
    from vitrine.snapshot_materialization import (
        SnapshotBuildAuthorityDecision,
        SnapshotSourceProviderRegistry,
        copy_planned_source_to_staging,
    )
    from vitrine.snapshot_state import snapshot_plan_fingerprint

    manifest, manifest_reads = _install_happy_path(monkeypatch)
    evidence = manifest.students[0].submission.digital_provenance.evidence_references[0]

    class _ProducerDecision:
        def __init__(self, *, status: str) -> None:
            self.status = status

    class _AuthorizedResult:
        pass

    class _AuthorizationError(Exception):
        pass

    class _ValidationError(Exception):
        pass

    class _UnavailableError(Exception):
        pass

    class _IntegrityError(Exception):
        pass

    class _ReadError(Exception):
        pass

    native_io_calls = 0

    def read_artifacts(
        workspace_root: Path,
        public_manifest: object,
        student_id: str,
        artifact_kind: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> tuple[object, ...]:
        nonlocal native_io_calls
        producer_request = SimpleNamespace(
            work=getattr(public_manifest, "work"),
            record_set_id=getattr(getattr(public_manifest, "record_set"), "record_set_id"),
            record_set_revision=getattr(getattr(public_manifest, "record_set"), "revision"),
            student_id=student_id,
            artifact_kind=artifact_kind,
            purpose=purpose,
        )
        decision = getattr(authorization_gate, "authorize")(producer_request)
        if getattr(decision, "status", None) != "allowed":
            raise _AuthorizationError("authorization not affirmed")
        native_io_calls += 1
        result = _AuthorizedResult()
        result.artifact_kind = "student_work"
        result.work = producer_request.work
        result.record_set_revision = producer_request.record_set_revision
        result.student_id = student_id
        result.relative_path = "producer/private/selected-evidence.png"
        result.media_type = "image/png"
        result.sha256 = EVIDENCE_SHA256
        result.byte_size = len(EVIDENCE_BYTES)
        result.data = EVIDENCE_BYTES
        result.evidence_reference = evidence
        return (result,)

    monkeypatch.setattr(
        quillan_source,
        "_load_quillan_artifact_api",
        lambda: SimpleNamespace(
            decision_factory=_ProducerDecision,
            result_type=_AuthorizedResult,
            read=read_artifacts,
            authorization_error=_AuthorizationError,
            validation_error=_ValidationError,
            unavailable_error=_UnavailableError,
            integrity_error=_IntegrityError,
            read_error=_ReadError,
        ),
    )

    class _ArtifactGate:
        def __init__(self) -> None:
            self.calls = 0
            self.last_request: object | None = None

        def authorize(self, request: object) -> QuillanArtifactAuthorizationDecision:
            self.calls += 1
            self.last_request = request
            return QuillanArtifactAuthorizationDecision(
                outcome="allowed",
                authority_reference="explicit_quillan_artifact_authority",
            )

    class _BuildGate:
        def authorize(self, request: object) -> SnapshotBuildAuthorityDecision:
            return SnapshotBuildAuthorityDecision(
                outcome="allowed",
                authority_reference="explicit_snapshot_build_authority",
            )

    context_resolver = build_canonical_quillan_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )
    artifact_gate = _ArtifactGate()
    provider = build_quillan_artifact_source_provider(
        artifact_request_kind="student_work",
        context_resolver=context_resolver,
        authorization_gate=artifact_gate,
    )
    entry = _entry()
    provisional = SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_alpha",
        snapshot_build_request_id="snapshot_request_alpha",
        snapshot_series_id="snapshot_series_alpha",
        plan_revision=1,
        portfolio_id="portfolio_alpha",
        portfolio_subject_id="subject_alpha",
        profile_binding_id="binding_alpha",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_alpha",
        entry_plans=(entry,),
        export_plans=(
            SnapshotExportPlan(
                export_plan_id="directory_export_alpha",
                export_format="directory_package",
                export_contract_version="snapshot_directory_v1",
                included_entry_plan_ids=(entry.entry_plan_id,),
                excluded_entry_plan_ids=(),
                configuration_digest=DigestReference(value="3" * 64),
            ),
        ),
        required_review_references=(),
        acknowledged_obligation_codes=(),
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        builder_contract_id="snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint="0" * 64,
    )
    plan = replace(
        provisional,
        plan_fingerprint=snapshot_plan_fingerprint(provisional),
    )
    attempt = SnapshotBuildAttempt(
        snapshot_build_attempt_id="snapshot_attempt_alpha",
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        attempt_number=1,
        builder_id="snapshot_builder",
        builder_version="1",
        started_at=NOW,
        staging_reference="staging_snapshot_attempt_alpha",
        started_by=ACTOR,
    )
    staging = create_snapshot_staging(
        tmp_path / "snapshot-custody",
        attempt.snapshot_build_attempt_id,
    )

    copied = copy_planned_source_to_staging(
        plan=plan,
        attempt=attempt,
        entry_plan_id=entry.entry_plan_id,
        staging=staging,
        authority_gate=_BuildGate(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
    )

    expected_digest = DigestReference(value=EVIDENCE_SHA256)
    assert copied.acquired_source_digest == expected_digest
    assert copied.copied_output_digest == expected_digest
    assert copied.byte_size == len(EVIDENCE_BYTES)
    assert copied.media_type == "image/png"
    assert copied.source_stability_result == "not_applicable"
    assert staging.content_path(entry.target_relative_path or "").read_bytes() == EVIDENCE_BYTES
    assert len(manifest_reads) == 1
    assert artifact_gate.calls == 1
    assert native_io_calls == 1
    authorization = artifact_gate.last_request
    assert authorization is not None
    assert getattr(authorization, "source_artifact_id") == _source_id("student_work")
    assert getattr(authorization, "student_id") == "student_alpha"
    assert getattr(authorization, "artifact_kind") == "student_work"
    assert getattr(authorization, "evidence_id") == EVIDENCE_ID
