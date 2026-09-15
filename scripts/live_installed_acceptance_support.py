"""Installed-only producer/native setup support for Vitrine issue #71 Slice 2.

This file is copied outside the Vitrine checkout and executed only inside the
exact-wheel live environment created by ``qualify_installed_live_portfolio.py``.
It deliberately composes public released producer APIs; it is not Vitrine runtime
code and it does not use Vitrine development fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pds_core.academic_catalog import PublicationCatalogQuery, rebuild_academic_catalog
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.publication_compatibility import build_publication_producer_registry
from pds_core.publication_records import PublicationCapability
from pds_core.rosters import create_roster
from pds_core.standards import (
    StandardDefinition,
    StandardsLibrary,
    StandardsProfile,
    write_workspace_standards_library,
)
from pds_core.workspace import ensure_workspace_root

from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    CandidateDiscoveryResult,
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
    discover_and_evaluate_candidates,
)
from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    ProfileRevisionRef,
)
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
)
from vitrine.producer_adapters import build_adapter_registry
from vitrine.starter_profiles import install_starter_profile
from vitrine.storage import load_current_state
from vitrine.subject_services import (
    IdentityDecisionContext,
    link_portfolio_subject,
    observe_state_revision,
    show_subject,
)

SCHOOL_YEAR = "2026-2027"
MAIN_STUDENT_ID = "synthetic_student"
COLLABORATOR_ID = "synthetic_collaborator"
SCOREFORM_CLASS_ID = "acceptance_scoreform"
SCOREFORM_WORK_ID = "acceptance_quiz"
QUILLAN_CLASS_ID = "acceptance_quillan"
QUILLAN_WORK_ID = "acceptance_response"
QUILLAN_STANDARD_ID = "synthetic:W.ACCEPT.1"
QUILLAN_PROFILE_ID = "synthetic_quillan_profile"
CONCORD_CLASS_ID = "acceptance_concord"
CONCORD_WORK_ID = "acceptance_activity"
CONCORD_STANDARD_ID = "synthetic_collab_accept_1"
CONCORD_PROFILE_ID = "synthetic_concord_profile"
CONCORD_SESSION_ID = "acceptance_session"
CONCORD_GROUP_ID = "acceptance_group"
CONCORD_ARTIFACT_ID = "acceptance_artifact"
CONCORD_ARTIFACT_PAGE_ID = "acceptance_artifact_page"
CONCORD_EVIDENCE_LINK_ID = "acceptance_evidence_link"
PURPOSE = "issue_71_live_installed_acceptance"
NOW = datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ProducerPublication:
    module_id: str
    class_id: str
    work_id: str
    publication_id: str


@dataclass(frozen=True, slots=True)
class LivePortfolioContext:
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str


class DeterministicIds:
    """Small deterministic Vitrine ID factory used only by this synthetic run."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()

    def __call__(self, prefix: str) -> str:
        self._counts[prefix] += 1
        return f"issue71_{prefix}_{self._counts[prefix]:04d}"


class ExactSourceReadGate:
    """Allow only this Portfolio/Subject and the exact freshly published heads."""

    def __init__(
        self,
        *,
        portfolio_id: str,
        portfolio_subject_id: str,
        publication_ids: set[str],
    ) -> None:
        self.portfolio_id = portfolio_id
        self.portfolio_subject_id = portfolio_subject_id
        self.publication_ids = frozenset(publication_ids)
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        allowed = (
            request.portfolio_id == self.portfolio_id
            and request.portfolio_subject_id == self.portfolio_subject_id
            and request.publication_id in self.publication_ids
            and request.operation == "candidate_source_read"
            and request.purpose == PURPOSE
        )
        return SourceReadAuthorizationDecision(
            outcome="allowed" if allowed else "denied",
            reason_codes=("issue_71:synthetic_exact_scope",) if allowed else (),
        )


def _actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="issue71_teacher",
        owning_system="local",
        role_snapshot="teacher",
        display_label_snapshot="Synthetic Issue 71 Teacher",
    )


def _identity_context() -> IdentityDecisionContext:
    return IdentityDecisionContext(
        actor=_actor(),
        authority_source="issue_71_synthetic_acceptance",
        basis_type="direct_teacher_knowledge",
        basis_summary=(
            "Synthetic acceptance explicitly confirms the same learner across "
            "three independent Core class rosters."
        ),
    )


def _student(student_id: str, *, first: str, last: str, period: str) -> dict[str, str]:
    return {
        "student_id": student_id,
        "last_name": last,
        "first_name": first,
        "period": period,
    }


def _write_class(
    workspace: Path,
    class_id: str,
    students: tuple[dict[str, str], ...],
) -> None:
    write_class_metadata_for_class(
        workspace,
        create_class_metadata(class_id, SCHOOL_YEAR, created_at=NOW),
    )
    write_class_roster(workspace, create_roster(class_id, students))


def prepare_core_identity_sources(workspace: Path) -> StandardsLibrary:
    """Create three separate exact class rosters and one shared standards library."""

    ensure_workspace_root(workspace, create=True)
    main = _student(
        MAIN_STUDENT_ID,
        first="Synthetic",
        last="Learner",
        period="acceptance",
    )
    collaborator = _student(
        COLLABORATOR_ID,
        first="Synthetic",
        last="Collaborator",
        period="acceptance",
    )
    _write_class(workspace, SCOREFORM_CLASS_ID, (main,))
    _write_class(workspace, QUILLAN_CLASS_ID, (main,))
    _write_class(workspace, CONCORD_CLASS_ID, (main, collaborator))

    library = StandardsLibrary(
        standards=(
            StandardDefinition(
                standard_id=QUILLAN_STANDARD_ID,
                code="W.ACCEPT.1",
                source="SYNTHETIC",
                short_name="Synthetic writing evidence",
                description="Use harmless synthetic evidence clearly.",
                subject="English Language Arts",
                course="Synthetic Acceptance",
                domain="Writing",
                available_modules=("quillan",),
            ),
            StandardDefinition(
                standard_id=CONCORD_STANDARD_ID,
                code="COLLAB.ACCEPT.1",
                source="SYNTHETIC",
                short_name="Synthetic collaborative reasoning",
                description="Use harmless synthetic collaborative evidence.",
                subject="Synthetic",
                course="Synthetic Acceptance",
                domain="Collaboration",
                available_modules=("concord",),
            ),
        ),
        profiles=(
            StandardsProfile(
                profile_id=QUILLAN_PROFILE_ID,
                standards=(QUILLAN_STANDARD_ID,),
                subject="English Language Arts",
                course="Synthetic Acceptance",
                source="SYNTHETIC",
                title="Synthetic Quillan Acceptance",
            ),
            StandardsProfile(
                profile_id=CONCORD_PROFILE_ID,
                standards=(CONCORD_STANDARD_ID,),
                subject="Synthetic",
                course="Synthetic Acceptance",
                source="SYNTHETIC",
                title="Synthetic Concord Acceptance",
            ),
        ),
    )
    write_workspace_standards_library(workspace, library)
    return library


def build_scoreform_publication(workspace: Path) -> ProducerPublication:
    """Create two native attempts, one immutable manifest, and one Core Publication."""

    from scoreform.academic_result_manifest_generation import (
        generate_academic_result_manifest,
    )
    from scoreform.academic_result_publication import publish_scoreform_academic_results
    from scoreform.academic_work_registration import register_scoreform_academic_work
    from scoreform.layouts import DEFAULT_LAYOUT_ID, require_layout
    from scoreform.page_scoring import ScoredAnswer
    from scoreform.results import ScoreFormRoutedResult, export_scoreform_result_models
    from scoreform.work_paths import initialize_scoreform_work_layout
    from scoreform.workflows import write_assignment_json

    layout = require_layout(DEFAULT_LAYOUT_ID)
    paths = initialize_scoreform_work_layout(workspace, SCOREFORM_CLASS_ID, SCOREFORM_WORK_ID)
    assignment: dict[str, object] = {
        "assignment_id": SCOREFORM_WORK_ID,
        "title": "Synthetic Baseline Assessment",
        "question_count": 3,
        "choices": list(layout.choices),
        "layout_id": layout.layout_id,
        "answer_key": {"1": "A", "2": "B", "3": "C"},
        "standards": {"1": [], "2": [], "3": []},
    }
    if not write_assignment_json(paths.assignment_path, assignment):
        raise RuntimeError("ScoreForm assignment write failed")

    def result(version: int) -> ScoreFormRoutedResult:
        answers = (
            (
                ScoredAnswer(1, "A", True),
                ScoredAnswer(2, "BLANK", False),
                ScoredAnswer(3, "C", True),
            )
            if version == 1
            else (
                ScoredAnswer(1, "B", False),
                ScoredAnswer(2, "B", True),
                ScoredAnswer(3, "AMBIGUOUS", False),
            )
        )
        return ScoreFormRoutedResult(
            result_origin="plain_paper_manual",
            class_id=SCOREFORM_CLASS_ID,
            assignment_id=SCOREFORM_WORK_ID,
            student_id=MAIN_STUDENT_ID,
            last_name="Learner",
            first_name="Synthetic",
            period="acceptance",
            page_display="manual",
            score=sum(answer.correct for answer in answers),
            total_points=3,
            answers=answers,
            source_file="plain_paper_manual_entry",
        )

    for version in (1, 2):
        exported = export_scoreform_result_models((result(version),), workspace_root=workspace)
        if not exported.succeeded or len(exported.appended_attempts) != 1:
            raise RuntimeError(f"ScoreForm native attempt {version} was not appended")

    registration = register_scoreform_academic_work(
        workspace,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        academic_intent="summative",
        lifecycle="active",
    )
    if registration.registration.registration_revision != 1:
        raise RuntimeError("ScoreForm registration did not begin at revision 1")
    generated = generate_academic_result_manifest(
        workspace, SCOREFORM_CLASS_ID, SCOREFORM_WORK_ID
    )
    if len(generated.manifest.students) != 1:
        raise RuntimeError("ScoreForm manifest student population disagrees")
    attempts = generated.manifest.students[0].attempts
    if tuple(item.attempt_number for item in attempts) != (1, 2):
        raise RuntimeError("ScoreForm manifest did not preserve both attempts independently")
    published = publish_scoreform_academic_results(
        workspace,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        manifest_revision=generated.revision,
    )
    return ProducerPublication(
        "scoreform",
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        published.publication.publication_id,
    )


def _quillan_cli(arguments: list[str], *, workspace: Path, cwd: Path) -> str:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PDS_WORKSPACE_ROOT"] = str(workspace)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from quillan.cli import main; raise SystemExit(main())",
            *arguments,
        ],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "installed Quillan command failed: "
            f"{arguments[0]} (exit={result.returncode})"
        )
    return result.stdout


def _render_pdf_pages_to_png(pdf_path: Path, destination: Path) -> tuple[Path, ...]:
    """Render synthetic printable pages without requiring an external Poppler install."""

    import pypdfium2

    destination.mkdir(parents=True, exist_ok=True)
    document = pypdfium2.PdfDocument(str(pdf_path))
    outputs: list[Path] = []
    try:
        for index in range(len(document)):
            page = document[index]
            try:
                bitmap = page.render(scale=3)
                try:
                    image = bitmap.to_pil()
                    output = destination / f"scan-{index + 1:02d}.png"
                    image.save(output, format="PNG")
                    outputs.append(output)
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        document.close()
    return tuple(outputs)


def build_quillan_publication(
    workspace: Path,
    *,
    standards: StandardsLibrary,
    work_root: Path,
) -> ProducerPublication:
    """Run a real printable-response/review/export flow before publishing Quillan."""

    del standards  # workspace library is the authoritative input used by Quillan services.
    from quillan.academic_result_manifest_generation import (
        generate_academic_result_manifest,
    )
    from quillan.academic_result_publication import publish_quillan_academic_results
    from quillan.academic_work_registration import register_quillan_academic_work
    from quillan.assignment_workflows import (
        build_assignment_config,
        write_assignment_config,
    )
    from quillan.printable_response_packet import (
        generate_printable_response_packet,
        plan_printable_response_packet,
    )

    assignment = build_assignment_config(
        assignment_id=QUILLAN_WORK_ID,
        title="Synthetic Later Writing Evidence",
        class_id=QUILLAN_CLASS_ID,
        writing_type="argument",
        student_prompt="Write a harmless synthetic response.",
        standards_profile_id=QUILLAN_PROFILE_ID,
        focus_standard_ids=[QUILLAN_STANDARD_ID],
        review_unit={
            "type": "paragraph",
            "singular_label": "paragraph",
            "plural_label": "paragraphs",
        },
        rating_scale={
            "scale_id": "synthetic_two_level",
            "levels": [
                {"value": 1, "label": "Developing", "description": "Developing."},
                {"value": 2, "label": "Meeting", "description": "Meeting."},
            ],
        },
        basic_requirements={"paragraphs_min": 1},
        minimum_requirement_policy={"allow_return_without_full_review": True},
    )
    write_assignment_config(workspace, QUILLAN_CLASS_ID, assignment)
    packet = generate_printable_response_packet(
        plan_printable_response_packet(
            workspace,
            QUILLAN_CLASS_ID,
            QUILLAN_WORK_ID,
            pages_per_student=1,
        )
    )
    if not packet.success or not packet.installed or len(packet.page_ids) != 1:
        raise RuntimeError("Quillan printable response packet did not install exactly one page")

    scans = _render_pdf_pages_to_png(packet.output_path, work_root / "quillan-scans")
    if len(scans) != 1:
        raise RuntimeError("Quillan synthetic scan rendering did not produce one page")
    routed_output = _quillan_cli(
        ["route-scan", str(scans[0])], workspace=workspace, cwd=work_root
    )
    if "quillan=1" not in routed_output:
        raise RuntimeError("Quillan route-scan did not dispatch exactly one page")

    identity = [QUILLAN_CLASS_ID, QUILLAN_WORK_ID, MAIN_STUDENT_ID]
    commands = (
        [
            "requirements",
            "set-check",
            *identity,
            "--requirement-key",
            "paragraphs_min",
            "--met",
            "true",
        ],
        ["requirements", "set-outcome", *identity, "--outcome", "met"],
        ["review-units", "set", *identity, "--count", "1"],
        [
            "observations",
            "set",
            *identity,
            "--unit-id",
            "paragraph_1",
            "--standard-id",
            QUILLAN_STANDARD_ID,
            "--applicable",
            "true",
            "--evidence-present",
            "true",
            "--rating",
            "2",
            "--rationale",
            "Synthetic evidence is present.",
            "--include-in-feedback",
            "true",
        ],
        ["observations", "mark-complete", *identity, "--yes"],
        [
            "ratings",
            "set",
            *identity,
            "--standard-id",
            QUILLAN_STANDARD_ID,
            "--rating",
            "2",
            "--rationale",
            "Synthetic overall rating.",
            "--include-in-feedback",
            "true",
        ],
        ["ratings", "mark-complete", *identity, "--yes"],
        [
            "feedback",
            "set-options",
            *identity,
            "--standard-id",
            QUILLAN_STANDARD_ID,
            "--include-overall-rating",
            "true",
            "--include-overall-rationale",
            "true",
            "--observation-ids",
            "observation_0001",
        ],
        [
            "feedback",
            "add-comment",
            *identity,
            "--standard-id",
            QUILLAN_STANDARD_ID,
            "--text",
            "Synthetic student-facing feedback.",
            "--include-in-feedback",
            "true",
        ],
        ["feedback", "mark-composed", *identity, "--yes"],
        ["add-note", *identity, "--text", "Synthetic private teacher note."],
        ["review-workflow", "set-state", *identity, "--state", "ready_for_export", "--yes"],
    )
    for command in commands:
        _quillan_cli(command, workspace=workspace, cwd=work_root)
    _quillan_cli(
        ["export-feedback", *identity, "--format", "both"],
        workspace=workspace,
        cwd=work_root,
    )

    registration = register_quillan_academic_work(
        workspace,
        QUILLAN_CLASS_ID,
        QUILLAN_WORK_ID,
        academic_intent="summative",
        lifecycle="active",
    )
    if registration.registration.registration_revision != 1:
        raise RuntimeError("Quillan registration did not begin at revision 1")
    generated = generate_academic_result_manifest(
        workspace, QUILLAN_CLASS_ID, QUILLAN_WORK_ID
    )
    if len(generated.manifest.students) != 1:
        raise RuntimeError("Quillan manifest did not contain exactly one reviewed learner")
    published = publish_quillan_academic_results(
        workspace,
        QUILLAN_CLASS_ID,
        QUILLAN_WORK_ID,
        manifest_revision=generated.revision,
    )
    return ProducerPublication(
        "quillan",
        QUILLAN_CLASS_ID,
        QUILLAN_WORK_ID,
        published.publication.publication_id,
    )


def build_concord_publication(
    workspace: Path,
    *,
    standards: StandardsLibrary,
) -> ProducerPublication:
    """Create collaborative Artifact evidence and publish one Concord result set."""

    from concord.academic_result_manifest_generation import (
        GenerateAcademicResultManifestRequest,
        generate_academic_result_manifest,
    )
    from concord.academic_result_publication import publish_concord_academic_results
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
    from concord.routing.rendering import (
        RenderArtifactPagesRequest,
        render_artifact_pages,
    )
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
    from pds_core.routing_models import ModuleWorkRef

    actor = WorkflowActor(
        actor_id="issue71_teacher",
        display_label="Synthetic Issue 71 Teacher",
        role_label="teacher",
    )
    work = ModuleWorkRef("concord", CONCORD_CLASS_ID, CONCORD_WORK_ID)

    def subject() -> SubjectReference:
        return SubjectReference(
            subject_kind="core_student",
            subject_id=MAIN_STUDENT_ID,
            owning_system="core",
        )

    def evidence() -> EvidenceReference:
        return EvidenceReference(
            evidence_kind="artifact_instance",
            owning_system="concord",
            record_id=CONCORD_ARTIFACT_ID,
            moderation_requirement="not_required",
        )

    created = create_activity_context(
        CreateActivityContextRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            title="Synthetic Collaborative Later Evidence",
            activity_type="project",
            scoring_orientation="mixed",
            standards_profile_id=CONCORD_PROFILE_ID,
            focus_standard_ids=(CONCORD_STANDARD_ID,),
            session_id=CONCORD_SESSION_ID,
            actor=actor,
            activity_status="active",
            session_status="active",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    group = create_group(
        CreateGroupRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            group_id=CONCORD_GROUP_ID,
            label="Synthetic acceptance group",
            status="active",
            expected_snapshot_revision=created.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    memberships = add_memberships(
        AddMembershipsRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            group_id=CONCORD_GROUP_ID,
            members=tuple(
                GroupMemberSpec(
                    membership_id=f"acceptance_membership_{index}",
                    student_id=student_id,
                    effective_context=EffectiveContext(
                        activity_id=CONCORD_WORK_ID,
                        session_ids=(CONCORD_SESSION_ID,),
                    ),
                )
                for index, student_id in enumerate(
                    (MAIN_STUDENT_ID, COLLABORATOR_ID), start=1
                )
            ),
            expected_snapshot_revision=group.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    prepared = prepare_artifact_pages(
        PrepareArtifactPagesRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            template_version_id="acceptance_template",
            artifact_category="observation",
            expected_snapshot_revision=memberships.commit.snapshot_revision,
            actor=actor,
            pages=(
                ArtifactPagePlan(
                    page_number=1,
                    artifact_page_id=CONCORD_ARTIFACT_PAGE_ID,
                ),
            ),
            session_id=CONCORD_SESSION_ID,
            group_id=CONCORD_GROUP_ID,
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    rendered = render_artifact_pages(
        RenderArtifactPagesRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            expected_snapshot_revision=prepared.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
    )
    routed = route_scan_sources((rendered.output_path,), workspace_root=workspace)
    if routed.dispatched_count != 1 or routed.failure_count != 0:
        raise RuntimeError("Concord synthetic Artifact did not route exactly one page")
    loaded = load_current_record_graph(workspace, work, standards_library=standards)
    assembled = assemble_returned_artifact(
        AssembleArtifactRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            expected_snapshot_revision=loaded.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
    )
    if not assembled.output_path.is_file():
        raise RuntimeError("Concord returned Artifact assembly is missing")
    author = add_artifact_author(
        AddArtifactAuthorRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            artifact_author_id="acceptance_author",
            author_reference=ParticipantReference(
                participant_kind="core_student",
                participant_id=COLLABORATOR_ID,
                owning_system="core",
            ),
            authorship_mode="observer",
            attribution_status="confirmed",
            attribution_source="teacher",
            expected_snapshot_revision=loaded.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    artifact_subject = add_artifact_subject(
        AddArtifactSubjectRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            artifact_subject_id="acceptance_subject",
            subject_reference=subject(),
            subject_role="observed_participant",
            confirmation_status="confirmed",
            assignment_source="teacher",
            expected_snapshot_revision=author.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    review = add_artifact_review(
        AddArtifactReviewRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            artifact_instance_id=CONCORD_ARTIFACT_ID,
            artifact_review_id="acceptance_review",
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
            notes="Synthetic private review note.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=artifact_subject.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    moderation = add_moderation_record(
        AddModerationRecordRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            moderation_record_id="acceptance_moderation",
            target_evidence_reference=evidence(),
            target_subject_references=(subject(),),
            status="accepted_with_qualification",
            permitted_use="support_named_subject",
            rationale="Synthetic private moderation rationale.",
            qualification="Synthetic use only for the named subject.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=review.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    scale = create_scoring_scale(
        CreateScoringScaleRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            scoring_scale_id="acceptance_scale",
            lineage_id="acceptance_scale_lineage",
            name="Synthetic acceptance scale",
            revision=1,
            scale_type="ordinal",
            levels=tuple(
                ScoringScaleLevel(
                    value=value,
                    label=label,
                    meaning=f"Synthetic {label.lower()} evidence.",
                    position=value,
                )
                for value, label in (
                    (1, "Beginning"),
                    (2, "Developing"),
                    (3, "Secure"),
                )
            ),
            status="active",
            expected_snapshot_revision=moderation.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    criteria = create_criterion_set(
        CreateCriterionSetRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            criterion_set_id="acceptance_criteria",
            lineage_id="acceptance_criteria_lineage",
            name="Synthetic acceptance criteria",
            purpose="Exercise collaborative live installed evidence.",
            revision=1,
            scope="activity_specific",
            criterion_set_kind="mixed",
            criteria=(
                CriterionSpec(
                    criterion_id="acceptance_group_criterion",
                    key="collaboration",
                    label="Collaboration",
                    definition="Synthetic group collaboration evidence.",
                    criterion_kind="local",
                    supported_target_kinds=("concord_group",),
                    default_scoring_scale_id="acceptance_scale",
                ),
                CriterionSpec(
                    criterion_id="acceptance_standard_criterion",
                    key="reasoning",
                    label="Reasoning",
                    definition="Synthetic standard-backed reasoning evidence.",
                    criterion_kind="standard_backed",
                    standard_id=CONCORD_STANDARD_ID,
                    supported_target_kinds=("core_student",),
                    default_scoring_scale_id="acceptance_scale",
                ),
            ),
            status="active",
            standards_profile_id=CONCORD_PROFILE_ID,
            expected_snapshot_revision=scale.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    selected = select_activity_criterion_sets(
        SelectActivityCriterionSetsRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            criterion_set_ids=("acceptance_criteria",),
            expected_snapshot_revision=criteria.commit.snapshot_revision,
            actor=actor,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )
    student_score = add_score(
        AddScoreRequest(
            class_id=CONCORD_CLASS_ID,
            activity_id=CONCORD_WORK_ID,
            score_record_id="acceptance_student_score",
            target_reference=ScoreTargetReference(
                target_kind="core_student",
                target_id=MAIN_STUDENT_ID,
                owning_system="core",
            ),
            criterion_id="acceptance_standard_criterion",
            scoring_scale_id="acceptance_scale",
            disposition="scored",
            value=3,
            basis="linked_evidence",
            evidence_links=(
                ScoreEvidenceLinkSpec(
                    score_evidence_link_id=CONCORD_EVIDENCE_LINK_ID,
                    evidence_reference=evidence(),
                    relevance_description="Synthetic Artifact supports reasoning.",
                    subject_context=(subject(),),
                    significance="primary",
                    moderation_record_id="acceptance_moderation",
                ),
            ),
            rationale="Synthetic private learner rationale.",
            privacy_policy=PrivacyPolicy(classification="teacher_restricted"),
            expected_snapshot_revision=selected.commit.snapshot_revision,
            actor=actor,
            session_id=CONCORD_SESSION_ID,
        ),
        workspace_root=workspace,
        standards_library=standards,
    )

    registration = register_concord_academic_work(
        workspace,
        CONCORD_CLASS_ID,
        CONCORD_WORK_ID,
        academic_intent="summative",
        lifecycle="active",
    )
    if registration.registration.registration_revision != 1:
        raise RuntimeError("Concord registration did not begin at revision 1")
    request = GenerateAcademicResultManifestRequest(
        class_id=CONCORD_CLASS_ID,
        activity_id=CONCORD_WORK_ID,
        expected_snapshot_revision=student_score.commit.snapshot_revision,
        actor=actor,
        revision_reason="initial",
    )
    generated = generate_academic_result_manifest(
        request,
        workspace_root=workspace,
        standards_library=standards,
    )
    published = publish_concord_academic_results(
        request,
        workspace_root=workspace,
        standards_library=standards,
    )
    if published.publication.manifest_digest != generated.sha256:
        raise RuntimeError("Concord publication did not bind the generated manifest")
    return ProducerPublication(
        "concord",
        CONCORD_CLASS_ID,
        CONCORD_WORK_ID,
        published.publication.publication_id,
    )


def install_improvement_portfolio(
    workspace: Path,
    *,
    ids: DeterministicIds,
) -> LivePortfolioContext:
    """Install the packaged starter and explicitly link all three class identities."""

    actor = _actor()
    install = install_starter_profile(
        "improvement_portfolio_v1",
        workspace_root=workspace,
        actor=actor,
        reason="Install packaged Starter Improvement Portfolio for issue #71 acceptance.",
        authority_reference="vitrine_starter_profile_catalog_v1",
        expected_state_revision=observe_state_revision(workspace),
        clock=lambda: NOW,
        id_factory=ids,
    )
    if install.commit is None:
        raise RuntimeError("Starter Improvement Portfolio install unexpectedly no-op'd")

    scoreform_ref = ClassQualifiedStudentRef(
        school_year=SCHOOL_YEAR,
        class_id=SCOREFORM_CLASS_ID,
        student_id=MAIN_STUDENT_ID,
    )
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=scoreform_ref,
            purpose_kind="improvement",
            profile_revision=ProfileRevisionRef(
                portfolio_profile_id="vitrine_starter_improvement",
                profile_revision=1,
            ),
            subject_action="create_new",
            identity_context=_identity_context(),
            title_snapshot="Synthetic Cross-Producer Improvement Portfolio",
            description_snapshot="Issue #71 synthetic installed acceptance only.",
        ),
        id_factory=ids,
    )
    if not plan.ready:
        raise RuntimeError(f"Vitrine Portfolio setup blocked: {plan.blocking_codes}")
    result = create_portfolio_for_student(
        workspace,
        plan,
        actor=actor,
        binding_reason="issue_71_live_installed_acceptance",
        clock=lambda: NOW,
    )

    for class_id in (QUILLAN_CLASS_ID, CONCORD_CLASS_ID):
        current = observe_state_revision(workspace)
        link_portfolio_subject(
            workspace,
            result.portfolio_subject_id,
            ClassQualifiedStudentRef(
                school_year=SCHOOL_YEAR,
                class_id=class_id,
                student_id=MAIN_STUDENT_ID,
            ),
            context=_identity_context(),
            expected_state_revision=current,
            clock=lambda: NOW,
            id_factory=ids,
        )

    detail = show_subject(workspace, result.portfolio_subject_id)
    linked_classes = {item.reference.class_id for item in detail.current_links}
    expected = {SCOREFORM_CLASS_ID, QUILLAN_CLASS_ID, CONCORD_CLASS_ID}
    if linked_classes != expected:
        raise RuntimeError("Vitrine Subject is not explicitly linked across all producer classes")
    return LivePortfolioContext(
        portfolio_id=result.portfolio_id,
        portfolio_subject_id=result.portfolio_subject_id,
        profile_binding_id=result.profile_binding_id,
    )


def discover_live_candidates(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
    ids: DeterministicIds,
) -> tuple[dict[str, object], ExactSourceReadGate]:
    """Discover all three producer heads through the ordinary live Candidate path."""

    rebuild_academic_catalog(workspace)
    producer_registry = build_publication_producer_registry()
    adapter_registry = build_adapter_registry()
    gate = ExactSourceReadGate(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        publication_ids={item.publication_id for item in publications},
    )
    summaries: dict[str, object] = {}
    expected_artifacts = {
        "scoreform": Counter({"assessment_summary": 2}),
        "quillan": Counter(
            {
                "assessment_summary": 1,
                "original_student_work": 1,
                "rendered_feedback": 2,
            }
        ),
    }

    for publication in publications:
        state_revision = load_current_state(workspace).state_revision
        required_capabilities: tuple[PublicationCapability, ...]
        if publication.module_id == "scoreform":
            required_capabilities = ("multiple_attempts", "points", "question_evidence")
        elif publication.module_id == "quillan":
            required_capabilities = ("standards_ratings",)
        else:
            required_capabilities = ("criterion_scores",)
        result: CandidateDiscoveryResult = discover_and_evaluate_candidates(
            workspace,
            CandidateDiscoveryRequest(
                portfolio_id=portfolio.portfolio_id,
                requesting_actor=_actor(),
                requested_purpose=PURPOSE,
                catalog_query=PublicationCatalogQuery(
                    class_id=publication.class_id,
                    module_id=publication.module_id,
                    work_id=publication.work_id,
                    required_capabilities=required_capabilities,
                    state="current",
                    limit=10,
                ),
                expected_state_revision=state_revision,
            ),
            producer_registry=producer_registry,
            adapter_registry=adapter_registry,
            authorization_gate=gate,
            clock=lambda: NOW,
            id_factory=ids,
        )
        if result.proposed_publication_ids != (publication.publication_id,):
            raise RuntimeError(
                f"{publication.module_id} Candidate discovery proposed the wrong publication"
            )
        if result.findings:
            raise RuntimeError(
                f"{publication.module_id} Candidate discovery returned finding "
                f"{result.findings[0].code}"
            )
        if not result.evaluation_results:
            raise RuntimeError(f"{publication.module_id} produced no Candidate projections")
        if any(item.candidate is None for item in result.evaluation_results):
            raise RuntimeError(
                f"{publication.module_id} produced an ineligible/unresolved projection"
            )
        artifacts = Counter(
            item.projected_source.source_artifact.artifact_kind
            for item in result.evaluation_results
        )
        if publication.module_id in expected_artifacts:
            if artifacts != expected_artifacts[publication.module_id]:
                raise RuntimeError(
                    f"{publication.module_id} projected artifact inventory disagrees: "
                    f"{dict(artifacts)}"
                )
        else:
            if artifacts["collaborative_artifact"] != 1:
                raise RuntimeError(
                    "Concord did not expose exactly one collaborative Artifact capability"
                )
        summaries[publication.module_id] = {
            "publication_count": len(result.proposed_publication_ids),
            "projection_count": len(result.evaluation_results),
            "candidate_count": sum(
                1 for item in result.evaluation_results if item.candidate is not None
            ),
            "artifact_kinds": dict(sorted(artifacts.items())),
            "conditions": sorted(
                {
                    item.candidate.condition_state
                    for item in result.evaluation_results
                    if item.candidate is not None
                }
            ),
        }

    if len(gate.requests) != len(publications):
        raise RuntimeError("source authorization did not occur exactly once per publication")
    return summaries, gate


def low_density_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
