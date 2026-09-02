"""Qualify Vitrine's Concord Artifact source bridge against exact release wheels."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from concord.academic_result_manifest_generation import (
    GenerateAcademicResultManifestRequest,
    generate_academic_result_manifest,
)
from concord.academic_result_publication import publish_concord_academic_results
from concord.academic_result_reader import read_academic_result_manifest
from concord.academic_work_registration import register_concord_academic_work
from concord.models import (
    EffectiveContext,
    EvidenceReference,
    ParticipantReference,
    PrivacyPolicy,
    ScoreTargetReference,
    ScoringScaleLevel,
    SubjectReference,
)
from concord.routing.rendering import RenderArtifactPagesRequest, render_artifact_pages
from concord.routing.scan_intake import route_scan_sources
from concord.storage import load_current_record_graph
from concord.workflows import (
    AddArtifactAuthorRequest,
    AddArtifactReviewRequest,
    AddArtifactSubjectRequest,
    AddMembershipsRequest,
    AddModerationRecordRequest,
    AddScoreRequest,
    AssembleArtifactRequest,
    CreateActivityContextRequest,
    CreateCriterionSetRequest,
    CreateGroupRequest,
    CreateScoringScaleRequest,
    CriterionSpec,
    GroupMemberSpec,
    ScoreEvidenceLinkSpec,
    SelectActivityCriterionSetsRequest,
    WorkflowActor,
    add_artifact_author,
    add_artifact_review,
    add_artifact_subject,
    add_memberships,
    add_moderation_record,
    add_score,
    assemble_returned_artifact,
    create_activity_context,
    create_criterion_set,
    create_group,
    create_scoring_scale,
    select_activity_criterion_sets,
)
from concord.workflows.artifact_page import (
    ArtifactPagePlan,
    PrepareArtifactPagesRequest,
    prepare_artifact_pages,
)
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.routing_models import ModuleWorkRef
from pds_core.standards import (
    StandardDefinition,
    StandardsLibrary,
    StandardsProfile,
    write_workspace_standards_library,
)
from pds_core.workspace import ensure_workspace_root

from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_PROJECTION_KIND,
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
)
from vitrine.concord_artifact_source import (
    CONCORD_ARTIFACT_SNAPSHOT_PURPOSE,
    ConcordArtifactAuthorizationDecision,
    ConcordArtifactAuthorizationRequest,
    ConcordArtifactSourceContext,
    build_concord_artifact_source_provider,
)
from vitrine.models import SnapshotEntryPlan
from vitrine.producer_adapters import (
    ProducerAdapterSupportRequest,
    build_adapter_registry,
)
from vitrine.released_producer_contracts import (
    CORE_0_6_3_AUDIT,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SnapshotMaterializationError,
    SnapshotSourceRequest,
)

CLASS_ID = "vitrine_concord_artifact_qualification"
ACTIVITY_ID = "qualification_activity"
SESSION_ID = "qualification_session"
GROUP_ID = "qualification_group"
STUDENT_1 = "synthetic_student_1"
STUDENT_2 = "synthetic_student_2"
STANDARD_ID = "qualification_standard"
PROFILE_ID = "qualification_profile"
ARTIFACT_ID = "qualification_artifact"
ARTIFACT_PAGE_ID = "qualification_artifact_page"
EVIDENCE_LINK_ID = "qualification_evidence_link"
GROUP_SCORE_ID = "qualification_group_score"
STUDENT_SCORE_ID = "qualification_student_score"
SCALE_ID = "qualification_scale"
CRITERION_SET_ID = "qualification_criteria"
GROUP_CRITERION_ID = "qualification_group_criterion"
STUDENT_CRITERION_ID = "qualification_student_criterion"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _actor() -> WorkflowActor:
    return WorkflowActor(
        actor_id="synthetic_teacher",
        display_label="Synthetic Teacher",
        role_label="teacher",
    )


def _student_subject(student_id: str = STUDENT_2) -> SubjectReference:
    return SubjectReference(
        subject_kind="core_student",
        subject_id=student_id,
        owning_system="core",
    )


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_kind="artifact_instance",
        owning_system="concord",
        record_id=ARTIFACT_ID,
        moderation_requirement="not_required",
    )


def _standards() -> StandardsLibrary:
    return StandardsLibrary(
        standards=(
            StandardDefinition(
                standard_id=STANDARD_ID,
                code="SYN.VITRINE.1",
                source="synthetic",
                short_name="Synthetic Vitrine qualification standard",
                description="Synthetic standard for exact-wheel qualification.",
                available_modules=("concord",),
            ),
        ),
        profiles=(
            StandardsProfile(
                profile_id=PROFILE_ID,
                standards=(STANDARD_ID,),
                title="Synthetic Vitrine qualification profile",
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class _NativeState:
    standards: StandardsLibrary
    snapshot_revision: int


def _build_native_state(workspace: Path) -> _NativeState:
    root = ensure_workspace_root(workspace)
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            CLASS_ID,
            "2026-2027",
            created_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        ),
    )
    write_class_roster(
        root,
        create_roster(
            CLASS_ID,
            (
                {
                    "student_id": STUDENT_1,
                    "last_name": "Synthetic",
                    "first_name": "One",
                    "period": "qualification",
                },
                {
                    "student_id": STUDENT_2,
                    "last_name": "Synthetic",
                    "first_name": "Two",
                    "period": "qualification",
                },
            ),
        ),
    )
    standards = _standards()
    write_workspace_standards_library(root, standards)

    created = create_activity_context(
        CreateActivityContextRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            title="Synthetic Vitrine Concord Artifact qualification",
            activity_type="project",
            scoring_orientation="mixed",
            standards_profile_id=PROFILE_ID,
            focus_standard_ids=(STANDARD_ID,),
            session_id=SESSION_ID,
            actor=_actor(),
            activity_status="active",
            session_status="active",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    group = create_group(
        CreateGroupRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            group_id=GROUP_ID,
            label="Synthetic Vitrine qualification group",
            status="active",
            expected_snapshot_revision=created.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    memberships = add_memberships(
        AddMembershipsRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            group_id=GROUP_ID,
            members=(
                GroupMemberSpec(
                    membership_id="qualification_membership_1",
                    student_id=STUDENT_1,
                    effective_context=EffectiveContext(
                        activity_id=ACTIVITY_ID,
                        session_ids=(SESSION_ID,),
                    ),
                ),
                GroupMemberSpec(
                    membership_id="qualification_membership_2",
                    student_id=STUDENT_2,
                    effective_context=EffectiveContext(
                        activity_id=ACTIVITY_ID,
                        session_ids=(SESSION_ID,),
                    ),
                ),
            ),
            expected_snapshot_revision=group.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    prepared = prepare_artifact_pages(
        PrepareArtifactPagesRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            template_version_id="qualification_template",
            artifact_category="observation",
            expected_snapshot_revision=memberships.commit.snapshot_revision,
            actor=_actor(),
            pages=(
                ArtifactPagePlan(
                    page_number=1,
                    artifact_page_id=ARTIFACT_PAGE_ID,
                ),
            ),
            session_id=SESSION_ID,
            group_id=GROUP_ID,
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    rendered = render_artifact_pages(
        RenderArtifactPagesRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            expected_snapshot_revision=prepared.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
    )
    routed = route_scan_sources((rendered.output_path,), workspace_root=root)
    _require(
        routed.dispatched_count == 1 and routed.failure_count == 0,
        "Concord PDS2 route/intake did not return exactly one Artifact Page.",
    )
    loaded = load_current_record_graph(
        root,
        ModuleWorkRef("concord", CLASS_ID, ACTIVITY_ID),
        standards_library=standards,
    )
    _require(
        loaded.graph.artifact_pages[0].page_status == "returned"
        and loaded.graph.artifact_instances[0].artifact_status == "returned",
        "Concord returned Artifact state was not established.",
    )
    assembled = assemble_returned_artifact(
        AssembleArtifactRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            expected_snapshot_revision=loaded.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
    )
    _require(
        assembled.output_path.is_file() and assembled.manifest_path.is_file(),
        "Concord returned Artifact assembly did not create bounded outputs.",
    )
    author = add_artifact_author(
        AddArtifactAuthorRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            artifact_author_id="qualification_author",
            author_reference=ParticipantReference(
                participant_kind="core_student",
                participant_id=STUDENT_1,
                owning_system="core",
            ),
            authorship_mode="observer",
            attribution_status="confirmed",
            attribution_source="teacher",
            expected_snapshot_revision=loaded.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    subject = add_artifact_subject(
        AddArtifactSubjectRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            artifact_subject_id="qualification_subject",
            subject_reference=_student_subject(),
            subject_role="observed_participant",
            confirmation_status="confirmed",
            assignment_source="teacher",
            expected_snapshot_revision=author.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    review = add_artifact_review(
        AddArtifactReviewRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            artifact_instance_id=ARTIFACT_ID,
            artifact_review_id="qualification_review",
            readability_judgment="readable",
            page_completeness_judgment="complete",
            filing_judgment="correct",
            author_judgment="confirmed",
            subject_judgment="confirmed",
            privacy_judgment="teacher_restricted",
            relevance_judgment="relevant",
            moderation_requirement="required",
            scoring_readiness="not_ready",
            review_outcome="moderation_required",
            notes="Synthetic private qualification review note.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=subject.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    moderation = add_moderation_record(
        AddModerationRecordRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            moderation_record_id="qualification_moderation",
            target_evidence_reference=_evidence(),
            target_subject_references=(_student_subject(),),
            status="accepted_with_qualification",
            permitted_use="support_named_subject",
            rationale="Synthetic private qualification moderation rationale.",
            qualification="Synthetic qualification use for the named subject.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=review.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    scale = create_scoring_scale(
        CreateScoringScaleRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            scoring_scale_id=SCALE_ID,
            lineage_id="qualification_scale_lineage",
            name="Synthetic Vitrine qualification scale",
            revision=1,
            scale_type="ordinal",
            levels=(
                ScoringScaleLevel(
                    value=1,
                    label="Beginning",
                    meaning="Synthetic beginning evidence.",
                    position=1,
                ),
                ScoringScaleLevel(
                    value=2,
                    label="Developing",
                    meaning="Synthetic developing evidence.",
                    position=2,
                ),
                ScoringScaleLevel(
                    value=3,
                    label="Secure",
                    meaning="Synthetic secure evidence.",
                    position=3,
                ),
            ),
            status="active",
            expected_snapshot_revision=moderation.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    criteria = create_criterion_set(
        CreateCriterionSetRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            criterion_set_id=CRITERION_SET_ID,
            lineage_id="qualification_criteria_lineage",
            name="Synthetic Vitrine qualification criteria",
            purpose="Exercise exact-wheel Vitrine Concord Artifact acquisition.",
            revision=1,
            scope="activity_specific",
            criterion_set_kind="mixed",
            criteria=(
                CriterionSpec(
                    criterion_id=GROUP_CRITERION_ID,
                    key="collaboration",
                    label="Collaboration",
                    definition="Synthetic group collaboration evidence.",
                    criterion_kind="local",
                    supported_target_kinds=("concord_group",),
                    default_scoring_scale_id=SCALE_ID,
                ),
                CriterionSpec(
                    criterion_id=STUDENT_CRITERION_ID,
                    key="reasoning",
                    label="Reasoning",
                    definition="Synthetic standard-backed reasoning evidence.",
                    criterion_kind="standard_backed",
                    standard_id=STANDARD_ID,
                    supported_target_kinds=("core_student",),
                    default_scoring_scale_id=SCALE_ID,
                ),
            ),
            status="active",
            standards_profile_id=PROFILE_ID,
            expected_snapshot_revision=scale.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    selected = select_activity_criterion_sets(
        SelectActivityCriterionSetsRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            criterion_set_ids=(CRITERION_SET_ID,),
            expected_snapshot_revision=criteria.commit.snapshot_revision,
            actor=_actor(),
        ),
        workspace_root=root,
        standards_library=standards,
    )
    group_score = add_score(
        AddScoreRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            score_record_id=GROUP_SCORE_ID,
            target_reference=ScoreTargetReference(
                target_kind="concord_group",
                target_id=GROUP_ID,
                owning_system="concord",
            ),
            criterion_id=GROUP_CRITERION_ID,
            scoring_scale_id=SCALE_ID,
            disposition="scored",
            value=2,
            basis="professional_judgment",
            rationale="Synthetic private group qualification rationale.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=selected.commit.snapshot_revision,
            actor=_actor(),
            session_id=SESSION_ID,
        ),
        workspace_root=root,
        standards_library=standards,
    )
    student_score = add_score(
        AddScoreRequest(
            class_id=CLASS_ID,
            activity_id=ACTIVITY_ID,
            score_record_id=STUDENT_SCORE_ID,
            target_reference=ScoreTargetReference(
                target_kind="core_student",
                target_id=STUDENT_2,
                owning_system="core",
            ),
            criterion_id=STUDENT_CRITERION_ID,
            scoring_scale_id=SCALE_ID,
            disposition="scored",
            value=3,
            basis="linked_evidence",
            evidence_links=(
                ScoreEvidenceLinkSpec(
                    score_evidence_link_id=EVIDENCE_LINK_ID,
                    evidence_reference=_evidence(),
                    relevance_description=(
                        "Synthetic represented Artifact supports reasoning."
                    ),
                    subject_context=(_student_subject(),),
                    significance="primary",
                    moderation_record_id="qualification_moderation",
                ),
            ),
            rationale="Synthetic private student qualification rationale.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=group_score.commit.snapshot_revision,
            actor=_actor(),
            session_id=SESSION_ID,
        ),
        workspace_root=root,
        standards_library=standards,
    )
    return _NativeState(
        standards=standards,
        snapshot_revision=student_score.commit.snapshot_revision,
    )


@dataclass(frozen=True, slots=True)
class _ContextResolver:
    workspace_root: Path
    manifest: object
    publication_id: str

    def resolve(self, request: SnapshotSourceRequest) -> ConcordArtifactSourceContext:
        return ConcordArtifactSourceContext(
            workspace_root=self.workspace_root,
            manifest=self.manifest,
            source_publication_id=self.publication_id,
            score_evidence_link_id=EVIDENCE_LINK_ID,
        )


class _ArtifactGate:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.calls = 0
        self.last_request: ConcordArtifactAuthorizationRequest | None = None

    def authorize(
        self, request: ConcordArtifactAuthorizationRequest
    ) -> ConcordArtifactAuthorizationDecision:
        self.calls += 1
        self.last_request = request
        return ConcordArtifactAuthorizationDecision(
            outcome=self.outcome,
            authority_reference=(
                "exact_wheel_qualification_authority"
                if self.outcome == "allowed"
                else None
            ),
        )


def _qualify(workspace: Path) -> None:
    concord_audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["concord"]
    _require(
        metadata.version(CORE_0_6_3_AUDIT.distribution_name)
        == CORE_0_6_3_AUDIT.release_version,
        "exact Core release is not installed",
    )
    _require(
        metadata.version(concord_audit.distribution_name)
        == concord_audit.release_version,
        "exact Concord release is not installed",
    )

    native = _build_native_state(workspace)
    registration = register_concord_academic_work(
        workspace,
        CLASS_ID,
        ACTIVITY_ID,
        academic_intent="summative",
        lifecycle="active",
    ).registration
    _require(
        registration.registration_revision == 1,
        "Concord Academic Work Registration revision changed",
    )
    request = GenerateAcademicResultManifestRequest(
        class_id=CLASS_ID,
        activity_id=ACTIVITY_ID,
        expected_snapshot_revision=native.snapshot_revision,
        actor=_actor(),
        revision_reason="initial",
    )
    generated = generate_academic_result_manifest(
        request,
        workspace_root=workspace,
        standards_library=native.standards,
    )
    manifest = read_academic_result_manifest(generated.content)
    published = publish_concord_academic_results(
        request,
        workspace_root=workspace,
        standards_library=native.standards,
    )
    publication_id = published.publication.publication_id

    key = concord_audit.support_key
    adapter_request = ProducerAdapterSupportRequest(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
        capabilities=(
            "criterion_scores",
            "moderated_scores",
            "standards_ratings",
        ),
    )
    batch = build_adapter_registry().select_adapter(adapter_request).project(manifest)
    artifact_source = next(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_evidence_link"
        and source.producer_source.source_record_id == EVIDENCE_LINK_ID
    )
    artifact = artifact_source.source_artifact
    _require(
        artifact_source.projection_kind == CONCORD_ARTIFACT_PROJECTION_KIND
        and artifact.artifact_id == ARTIFACT_ID
        and artifact.representation_kind == CONCORD_ARTIFACT_REPRESENTATION_KIND
        and artifact.source_locator is None
        and artifact.source_digest is None
        and artifact.byte_size is None
        and artifact.native_revision == manifest.projection.source_snapshot_revision,
        "live Concord adapter changed Artifact evidence projection semantics",
    )

    entry = SnapshotEntryPlan(
        entry_plan_id="qualification_entry_plan",
        plan_position=1,
        section_id="evidence",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="qualification_selection",
        placement_id="qualification_placement",
        candidate_id="qualification_candidate",
        candidate_evaluation_id="qualification_candidate_evaluation",
        source_publication_id=publication_id,
        producer_module_id="concord",
        projection_kind=artifact.representation_kind,
        projection_contract_version=batch.candidate_projection_contract_version,
        source_artifact=artifact,
        producer_source_digest_claim=None,
        target_relative_path="evidence/qualification-artifact.pdf",
        media_type="application/pdf",
    )
    source_request = SnapshotSourceRequest(
        snapshot_build_plan_id="qualification_snapshot_plan",
        snapshot_build_attempt_id="qualification_snapshot_attempt",
        entry_plan=entry,
    )
    resolver = _ContextResolver(
        workspace_root=workspace.resolve(),
        manifest=manifest,
        publication_id=publication_id,
    )
    gate = _ArtifactGate("allowed")
    provider = build_concord_artifact_source_provider(
        context_resolver=resolver,
        authorization_gate=gate,
    )
    result = provider.resolve(source_request)

    _require(
        gate.calls == 1 and gate.last_request is not None,
        "Vitrine Concord Artifact gate was not invoked exactly once",
    )
    gate_request = gate.last_request
    _require(
        gate_request.operation == "read_concord_artifact"
        and gate_request.source_publication_id == publication_id
        and gate_request.source_artifact_id == ARTIFACT_ID
        and gate_request.source_snapshot_revision
        == manifest.projection.source_snapshot_revision
        and gate_request.score_record_id == STUDENT_SCORE_ID
        and gate_request.score_evidence_link_id == EVIDENCE_LINK_ID
        and gate_request.evidence_kind == "artifact_instance"
        and gate_request.evidence_record_id == ARTIFACT_ID
        and gate_request.purpose == CONCORD_ARTIFACT_SNAPSHOT_PURPOSE,
        "Vitrine Concord Artifact authorization request changed exact provenance",
    )
    _require(
        result.acquisition_contract_version
        == SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
        and result.source_publication_id == publication_id
        and result.source_artifact_id == ARTIFACT_ID
        and result.media_type == "application/pdf"
        and result.content.startswith(b"%PDF")
        and result.byte_size == len(result.content)
        and result.source_digest is not None
        and result.source_digest.value == _sha256(result.content),
        "Vitrine Concord provider did not return exact authorized PDF bytes",
    )

    denied = build_concord_artifact_source_provider(
        context_resolver=resolver,
        authorization_gate=_ArtifactGate("denied"),
    )
    try:
        denied.resolve(source_request)
    except SnapshotMaterializationError as error:
        _require(
            error.code == "snapshot.source_unavailable"
            and error.stage == "concord_artifact_authorization_denied",
            "Vitrine Concord denied authorization mapping changed",
        )
    else:
        raise RuntimeError("denied Concord Artifact authorization returned bytes")

    print(
        "PASS exact-wheel Concord Artifact source qualification",
        metadata.version("pds-core"),
        metadata.version("pds-concord"),
        len(result.content),
        result.source_digest.value,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(
            prefix="vitrine-concord-artifact-qualification-"
        ) as temporary:
            _qualify(Path(temporary) / "workspace")
        return 0
    except (OSError, RuntimeError, SnapshotMaterializationError) as error:
        print(f"Concord Artifact source qualification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
