from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

import vitrine.concord_artifact_context as context_module
from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_PROJECTION_KIND,
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
    CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
)
from vitrine.concord_artifact_context import (
    CONCORD_ARTIFACT_CONTEXT_PURPOSE,
    CONCORD_ARTIFACT_SOURCE_READ_OPERATION,
    build_canonical_concord_artifact_source_context_resolver,
)
from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    CorePublicationSourceReference,
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
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotSourceRequest,
)

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
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
WORK = ModuleWorkRef("concord", "class_alpha", "activity_alpha")
SOURCE_RECORD = ModuleRecordRef(
    "concord",
    "activity",
    "activity_alpha",
    "concord_activity_v1",
)


class _ReadGate:
    pass


def _privacy() -> SourcePrivacyMetadata:
    return SourcePrivacyMetadata(
        classification="group_and_teacher",
        subject_scope="multiple_subjects",
        metadata_visibility="internal",
        collaborator_information_present=True,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=True,
        multi_subject_review_required=True,
        minimum_necessary_projection_required=True,
        policy_reference="vitrine_live_concord_minimum_necessary_v1",
    )


def _artifact() -> SourceArtifactReference:
    return SourceArtifactReference(
        artifact_id="artifact_alpha",
        artifact_kind="collaborative_artifact",
        representation_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
        media_type="application/pdf",
        source_locator=None,
        native_revision=7,
        source_digest=None,
        byte_size=None,
        language=None,
        accessibility_relationship=None,
    )


def _producer_source() -> ProducerSourceReference:
    return ProducerSourceReference(
        producer_module_id="concord",
        producer_contract_version="concord_academic_work_v1",
        source_record_kind="score_evidence_link",
        source_record_id="link_alpha",
        source_record_contract_version=None,
        native_revision=None,
        native_lifecycle="active",
        native_disposition="primary",
        lineage_reference="score_alpha",
        reader_contract_version="vitrine_installed_producer_reader_v1",
        projection_contract_version=CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
    )


def _core_reference() -> CorePublicationSourceReference:
    return CorePublicationSourceReference(
        core_publication_schema_version="1",
        publication_id="publication_alpha",
        work=WORK,
        source_record=SOURCE_RECORD,
        publication_kind="academic_result_set",
        capabilities=("criterion_scores", "moderated_scores"),
        record_set_id="academic_results",
        record_set_revision=4,
        manifest_contract_version="concord_academic_result_manifest_v1",
        manifest_path=(
            "modules/concord/classes/class_alpha/works/activity_alpha/"
            "exports/manifests/academic_results/4.json"
        ),
        manifest_digest_algorithm="sha256",
        manifest_digest="a" * 64,
        published_at=NOW,
        academic_work_registration_revision=2,
        registration_snapshot=AcademicWorkRegistrationSnapshot(
            registration_revision=2,
            producer_contract_version="concord_academic_work_v1",
            title_snapshot="Collaborative Activity",
            work_kind="activity",
            academic_intent="formative",
            lifecycle="active",
            source_records=(SOURCE_RECORD,),
        ),
        supersedes_publication_id=None,
        observed_series_state="current_selectable",
        observed_withdrawal_state="not_withdrawn",
        verified_at=NOW,
    )


def _endpoint() -> CandidateSourceEndpoint:
    assertion = PortfolioSubjectRelationshipAssertion(
        assertion_id="assertion_alpha",
        portfolio_subject_id="subject_alpha",
        subject_link_id="subject_link_alpha",
        source_subject_kind="core_student",
        source_subject_id="student_alpha",
        relationship_kind="individual_score_target",
        relationship_authority="concord",
        supporting_source_reference="score_alpha",
        verified_at=NOW,
        verified_by=ACTOR,
    )
    return CandidateSourceEndpoint(
        core_publication=_core_reference(),
        producer_source=_producer_source(),
        source_artifact=_artifact(),
        subject_relationship_assertions=(assertion,),
        source_privacy=_privacy(),
    )


def _records() -> tuple[object, ...]:
    endpoint = _endpoint()
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
        condition_state="collaborator_review_required",
        display_snapshot="Concord Artifact evidence",
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
        selection_reason="Teacher explicitly selected the represented Artifact evidence.",
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


def _entry() -> SnapshotEntryPlan:
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
        producer_module_id="concord",
        projection_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
        projection_contract_version=CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
        source_artifact=_artifact(),
        producer_source_digest_claim=None,
        target_relative_path="student-work/01-concord-artifact.pdf",
        media_type="application/pdf",
    )


def _request(entry: SnapshotEntryPlan | None = None) -> SnapshotSourceRequest:
    return SnapshotSourceRequest(
        snapshot_build_plan_id="snapshot_plan_alpha",
        snapshot_build_attempt_id="snapshot_attempt_alpha",
        entry_plan=_entry() if entry is None else entry,
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


def _projected_source() -> ProjectedProducerSource:
    return ProjectedProducerSource(
        projection_kind=CONCORD_ARTIFACT_PROJECTION_KIND,
        producer_source=_producer_source(),
        source_artifact=_artifact(),
        source_relationships=(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id="student_alpha",
                relationship_kind="individual_score_target",
                relationship_authority="concord",
                supporting_source_reference="score_alpha",
            ),
        ),
        source_privacy=_privacy(),
        display_snapshot=ProjectionDisplaySnapshot(
            title="Concord Artifact evidence",
        ),
    )


class _FakeAdapter:
    def __init__(
        self,
        sources: tuple[ProjectedProducerSource, ...] = (_projected_source(),),
    ) -> None:
        self.sources = sources

    def project(self, public_model: object) -> SimpleNamespace:
        return SimpleNamespace(projected_sources=self.sources)


def _install_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    *,
    projected_sources: tuple[ProjectedProducerSource, ...] = (
        _projected_source(),
    ),
    withdrawal: object | None = None,
) -> tuple[object, list[object]]:
    manifest = SimpleNamespace(
        work=WORK,
        record_set=SimpleNamespace(record_set_id="academic_results", revision=4),
        projection=SimpleNamespace(source_snapshot_revision=7),
    )
    reads: list[object] = []

    monkeypatch.setattr(
        context_module,
        "load_current_records_with_state",
        lambda root: (SimpleNamespace(state_revision=9), _records()),
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
        "build_concord_live_adapter",
        lambda: _FakeAdapter(projected_sources),
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


def test_production_context_resolver_revalidates_selection_core_and_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, reads = _install_happy_path(monkeypatch)
    gate = _ReadGate()
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=gate,  # type: ignore[arg-type]
    )

    context = resolver.resolve(_request())

    assert context.workspace_root == (tmp_path / "workspace").absolute()
    assert context.manifest is manifest
    assert context.source_publication_id == "publication_alpha"
    assert context.score_evidence_link_id == "link_alpha"
    assert len(reads) == 1
    authorization = reads[0]
    assert getattr(authorization, "portfolio_id") == "portfolio_alpha"
    assert getattr(authorization, "portfolio_subject_id") == "subject_alpha"
    assert getattr(authorization, "publication_id") == "publication_alpha"
    assert getattr(authorization, "operation") == CONCORD_ARTIFACT_SOURCE_READ_OPERATION
    assert getattr(authorization, "purpose") == CONCORD_ARTIFACT_CONTEXT_PURPOSE


def test_context_resolver_requires_explicit_selection_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, reads = _install_happy_path(monkeypatch)
    entry = replace(_entry(), selection_id="selection_other")
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request(entry))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_selection"
    assert reads == []


def test_context_resolver_refuses_withdrawn_publication_before_manifest_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, reads = _install_happy_path(
        monkeypatch,
        withdrawal=SimpleNamespace(publication_id="publication_alpha"),
    )
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == "concord_artifact_core_publication"
    assert reads == []


def test_context_resolver_maps_source_read_denial_without_artifact_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, _reads = _install_happy_path(monkeypatch)

    def denied(*args: Any, **kwargs: Any) -> object:
        raise ProducerReaderServiceError(
            "source_read.authorization_denied",
            "denied",
            stage="source_authorization",
        )

    monkeypatch.setattr(
        context_module,
        "read_authorized_producer_manifest",
        denied,
    )
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == "concord_artifact_manifest"


def test_context_resolver_rejects_candidate_not_reproduced_by_verified_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, _reads = _install_happy_path(monkeypatch, projected_sources=())
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_reprojection"


def test_context_resolver_rejects_frozen_registration_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest, reads = _install_happy_path(monkeypatch)
    drifted = _registration()
    drifted.producer_contract_version = "concord_academic_work_v2"
    monkeypatch.setattr(
        context_module,
        "load_academic_work_registration_revision",
        lambda root, work, revision: drifted,
    )
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        resolver.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_registration"
    assert reads == []


def test_context_resolver_construction_is_concord_lazy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_adapter() -> object:
        nonlocal imports
        imports += 1
        raise AssertionError("Concord adapter projection must remain lazy")

    monkeypatch.setattr(context_module, "build_concord_live_adapter", fail_adapter)
    resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )

    assert resolver.workspace_root == (tmp_path / "workspace").absolute()
    assert imports == 0

def test_selected_concord_artifact_materializes_authorized_pdf_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib

    import vitrine.concord_artifact_source as concord_source
    from vitrine.concord_artifact_source import (
        ConcordArtifactAuthorizationDecision,
        build_concord_artifact_source_provider,
    )
    from vitrine.models import (
        DigestReference,
        SnapshotBuildAttempt,
        SnapshotBuildPlan,
        SnapshotExportPlan,
    )
    from vitrine.snapshot_custody import create_snapshot_staging
    from vitrine.snapshot_materialization import (
        SnapshotBuildAuthorityDecision,
        SnapshotSourceProviderRegistry,
        copy_planned_source_to_staging,
    )
    from vitrine.snapshot_state import snapshot_plan_fingerprint

    pdf = b"%PDF-1.4\nselected live Concord Artifact\n%%EOF\n"
    pdf_sha256 = hashlib.sha256(pdf).hexdigest()
    _manifest, manifest_reads = _install_happy_path(monkeypatch)

    class _ProducerDecision:
        def __init__(self, *, status: str) -> None:
            self.status = status

    class _AuthorizedResult:
        pass

    class _AuthorizationError(Exception):
        pass

    class _ValidationError(Exception):
        pass

    class _NotFoundError(Exception):
        pass

    class _UnavailableError(Exception):
        pass

    class _AmbiguityError(Exception):
        pass

    class _IntegrityError(Exception):
        pass

    native_io_calls = 0

    def read_artifact(
        workspace_root: Path,
        manifest: object,
        score_evidence_link_id: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> object:
        nonlocal native_io_calls
        evidence = SimpleNamespace(
            evidence_kind="artifact_instance",
            owning_system="concord",
            record_id="artifact_alpha",
        )
        producer_request = SimpleNamespace(
            work=getattr(manifest, "work"),
            record_set_id=getattr(getattr(manifest, "record_set"), "record_set_id"),
            record_set_revision=getattr(getattr(manifest, "record_set"), "revision"),
            source_snapshot_revision=getattr(
                getattr(manifest, "projection"), "source_snapshot_revision"
            ),
            score_record_id="score_alpha",
            score_evidence_link_id=score_evidence_link_id,
            evidence_reference=evidence,
            purpose=purpose,
        )
        decision = getattr(authorization_gate, "authorize")(producer_request)
        if getattr(decision, "status", None) != "allowed":
            raise _AuthorizationError("authorization not affirmed")
        native_io_calls += 1
        result = _AuthorizedResult()
        result.representation = "returned_artifact_pdf"
        result.work = producer_request.work
        result.record_set_revision = producer_request.record_set_revision
        result.source_snapshot_revision = producer_request.source_snapshot_revision
        result.score_record_id = producer_request.score_record_id
        result.score_evidence_link_id = producer_request.score_evidence_link_id
        result.evidence_reference = evidence
        result.artifact = SimpleNamespace(
            artifact_instance_id="artifact_alpha",
            pages=(),
        )
        result.media_type = "application/pdf"
        result.sha256 = pdf_sha256
        result.byte_size = len(pdf)
        result.content = pdf
        return result

    monkeypatch.setattr(
        concord_source,
        "_load_concord_artifact_api",
        lambda: SimpleNamespace(
            decision_factory=_ProducerDecision,
            result_type=_AuthorizedResult,
            read=read_artifact,
            authorization_error=_AuthorizationError,
            validation_error=_ValidationError,
            not_found_error=_NotFoundError,
            unavailable_error=_UnavailableError,
            ambiguity_error=_AmbiguityError,
            integrity_error=_IntegrityError,
        ),
    )

    class _ArtifactGate:
        def __init__(self) -> None:
            self.calls = 0

        def authorize(self, request: object) -> ConcordArtifactAuthorizationDecision:
            self.calls += 1
            return ConcordArtifactAuthorizationDecision(
                outcome="allowed",
                authority_reference="explicit_concord_artifact_authority",
            )

    class _BuildGate:
        def authorize(self, request: object) -> SnapshotBuildAuthorityDecision:
            return SnapshotBuildAuthorityDecision(
                outcome="allowed",
                authority_reference="explicit_snapshot_build_authority",
            )

    context_resolver = build_canonical_concord_artifact_source_context_resolver(
        tmp_path / "workspace",
        source_read_authorization_gate=_ReadGate(),  # type: ignore[arg-type]
    )
    artifact_gate = _ArtifactGate()
    provider = build_concord_artifact_source_provider(
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

    expected_digest = DigestReference(value=pdf_sha256)
    assert copied.acquired_source_digest == expected_digest
    assert copied.copied_output_digest == expected_digest
    assert copied.byte_size == len(pdf)
    assert copied.source_stability_result == "not_applicable"
    assert staging.content_path(entry.target_relative_path or "").read_bytes() == pdf
    assert len(manifest_reads) == 1
    assert artifact_gate.calls == 1
    assert native_io_calls == 1

