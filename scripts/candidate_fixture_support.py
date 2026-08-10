"""Development-only Core/Vitrine fixture workspace support for issue #33 tests."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pds_core.academic_catalog import rebuild_academic_catalog
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.publication_records import PublicationCapability
from pds_core.registry_services import (
    AcademicWorkRegistrationRequest,
    PublicationManifestRequest,
    publish_manifest_revision,
    register_academic_work,
)
from pds_core.rosters import ROSTER_REQUIRED_COLUMNS, validate_roster_rows
from pds_core.routes import module_work_dir
from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef
from pds_core.workspace import ensure_workspace_root

from vitrine.candidate_services import (
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
)
from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    Portfolio,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    VitrineRecord,
)
from vitrine.storage import commit_record_batch, load_current_state

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
SCHOOL_YEAR = "2026-2027"
CLASS_ID = "english10_p2"
STUDENT_ID = "student_alpha"

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="candidate_fixture_teacher",
    owning_system="vitrine",
    role_snapshot="teacher",
)


@dataclass(frozen=True, slots=True)
class CandidateFixtureWorkspace:
    workspace: Path
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    scoreform_publication_id: str
    quillan_publication_id: str
    concord_publication_id: str
    manifest_paths: dict[str, Path]

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision


@dataclass
class DeterministicIds:
    counters: dict[str, int]

    def __init__(self) -> None:
        self.counters = {}

    def __call__(self, prefix: str) -> str:
        value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = value
        return f"{prefix}_{value}"


def fixed_clock() -> datetime:
    return NOW


class StaticAuthorizationGate:
    def __init__(self, outcome: str = "allowed") -> None:
        self.outcome = outcome
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        return SourceReadAuthorizationDecision(
            outcome=self.outcome,
            reason_codes=("fixture_permission",),
        )


def _profile_records(
    *,
    link_student: bool,
    link_class_id: str,
    conflicting_student_link: bool,
    allow_assessment_summary: bool,
) -> tuple[VitrineRecord, ...]:
    subject = PortfolioSubject(
        portfolio_subject_id="subject_candidate_fixture",
        created_at=NOW,
        created_by=ACTOR,
        display_name_snapshot="Synthetic Student",
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_candidate_fixture",
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=NOW,
        created_by=ACTOR,
        title_snapshot="Candidate Fixture Portfolio",
    )
    link = PortfolioSubjectClassLink(
        subject_link_id="subject_link_candidate_fixture",
        portfolio_subject_id=subject.portfolio_subject_id,
        student_reference=ClassQualifiedStudentRef(
            class_id=link_class_id,
            student_id=STUDENT_ID if link_student else "student_other",
            school_year=SCHOOL_YEAR,
        ),
        confirmed_at=NOW,
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="fixture_roster",
    )
    family = PortfolioProfileFamily(
        profile_family_id="family_candidate_fixture",
        label="Candidate Fixture Profiles",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=ACTOR,
    )
    assessment_sections = (
        (
            ProfileSectionDefinition(
                section_id="assessment_context",
                label="Assessment Context",
                purpose="Assessment summaries available for later curation.",
                order=1,
                obligation="optional",
                minimum_placements=0,
                maximum_placements=None,
                allowed_candidate_kinds=("assessment_summary",),
                required_relationship_kinds=("attempt_subject",),
                reflection_requirement="none",
            ),
        )
        if allow_assessment_summary
        else ()
    )
    sections = (
        *assessment_sections,
        ProfileSectionDefinition(
            section_id="student_work",
            label="Student Work",
            purpose="Student work available for later curation.",
            order=2,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=(),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="authored_work",
            label="Authored Work",
            purpose="Work with explicit Artifact Author support.",
            order=3,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("artifact_author",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="contribution_work",
            label="Documented Contribution",
            purpose="Collaborative work with a documented contribution.",
            order=4,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("documented_contributor",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="feedback_context",
            label="Feedback Context",
            purpose="Student-facing feedback available for later curation.",
            order=5,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("feedback",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id="profile_candidate_fixture",
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Candidate Evaluation Fixture",
        purpose_kind="improvement",
        applicability=ProfileApplicability(school_years=(SCHOOL_YEAR,)),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="student_internal",
                audience_class="student",
                purpose="Synthetic student review.",
                allowed_content_classes=(
                    "assessment_summary",
                    "feedback",
                    "student_work",
                ),
                prohibited_content_classes=("private_teacher_note",),
                required_review_classes=("privacy_review",),
                presentation_class="student_portfolio",
            ),
        ),
        created_at=NOW,
        created_by=ACTOR,
        source_authority_references=("fixture_policy",),
    )
    requirements = tuple(
        PortfolioProfileRequirement(
            portfolio_profile_id=revision.portfolio_profile_id,
            profile_revision=revision.profile_revision,
            requirement_id=f"{section.section_id}_candidate_rule",
            requirement_kind="section",
            obligation="optional",
            title=f"{section.label} candidate rule",
            statement="Candidate may be considered for this fixture section.",
            scope_kind="section",
            satisfaction_class="candidate_eligibility",
            scope_reference=section.section_id,
            authority_references=("fixture_policy",),
        )
        for section in sections
    )
    lifecycle = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id="profile_event_candidate_fixture",
        profile_revision=revision.reference,
        event_kind="activated",
        event_at=NOW,
        effective_at=NOW,
        actor=ACTOR,
        reason="Activate synthetic Candidate fixture Profile.",
        authority_reference="fixture_policy",
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="profile_binding_candidate_fixture",
        portfolio_id=portfolio.portfolio_id,
        profile_revision=revision.reference,
        bound_at=NOW,
        bound_by=ACTOR,
        binding_reason="Synthetic Candidate discovery validation.",
    )
    records: list[VitrineRecord] = [
        subject, portfolio, link, family, revision, *requirements, lifecycle, binding
    ]
    if conflicting_student_link:
        other_subject = PortfolioSubject(
            portfolio_subject_id="subject_candidate_conflict",
            created_at=NOW,
            created_by=ACTOR,
            display_name_snapshot="Synthetic Conflicting Subject",
        )
        other_link = PortfolioSubjectClassLink(
            subject_link_id="subject_link_candidate_conflict",
            portfolio_subject_id=other_subject.portfolio_subject_id,
            student_reference=ClassQualifiedStudentRef(
                class_id=CLASS_ID, student_id=STUDENT_ID, school_year=SCHOOL_YEAR
            ),
            confirmed_at=NOW,
            confirmed_by=ACTOR,
            confirmation_basis="teacher_confirmed",
            authority_reference="fixture_conflict",
        )
        records.extend((other_subject, other_link))
    return tuple(records)


def _write_class_context(workspace: Path) -> None:
    metadata = create_class_metadata(
        CLASS_ID,
        SCHOOL_YEAR,
        created_at=NOW,
        module_details={},
    )
    write_class_metadata_for_class(workspace, metadata)
    roster = validate_roster_rows(
        ROSTER_REQUIRED_COLUMNS,
        (
            {
                "class_id": CLASS_ID,
                "student_id": "student_alpha",
                "last_name": "Alpha",
                "first_name": "Student",
                "period": "2",
            },
            {
                "class_id": CLASS_ID,
                "student_id": "student_beta",
                "last_name": "Beta",
                "first_name": "Student",
                "period": "2",
            },
            {
                "class_id": CLASS_ID,
                "student_id": "student_member_only",
                "last_name": "Member",
                "first_name": "Student",
                "period": "2",
            },
            {
                "class_id": CLASS_ID,
                "student_id": "student_other",
                "last_name": "Other",
                "first_name": "Student",
                "period": "2",
            },
        ),
    )
    write_class_roster(workspace, roster)


def _publish_fixture(
    workspace: Path,
    *,
    module_id: str,
    work_id: str,
    producer_contract_version: str,
    manifest_contract_version: str,
    fixture_path: Path,
    source_record: ModuleRecordRef | None,
    capabilities: tuple[PublicationCapability, ...],
    record_set_id: str,
) -> tuple[str, Path]:
    work = ModuleWorkRef(module_id, CLASS_ID, work_id)
    work_root = module_work_dir(workspace, work)
    work_root.mkdir(parents=True, exist_ok=True)
    registration = register_academic_work(
        workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version=producer_contract_version,
            title=f"Synthetic {work_id}",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=() if source_record is None else (source_record,),
        ),
    ).registration
    manifest_path = (
        work_root / "exports" / "manifests" / record_set_id / "1.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture_path, manifest_path)
    relative_manifest = manifest_path.relative_to(workspace).as_posix()
    publication = publish_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work,
            source_record=source_record,
            publication_kind="academic_result_set",
            capabilities=capabilities,
            record_set_id=record_set_id,
            record_set_revision=1,
            manifest_contract_version=manifest_contract_version,
            manifest_path=relative_manifest,
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    return publication.publication_id, manifest_path


def build_candidate_fixture_workspace(
    base: Path,
    *,
    link_student: bool = True,
    link_class_id: str = CLASS_ID,
    conflicting_student_link: bool = False,
    allow_assessment_summary: bool = True,
) -> CandidateFixtureWorkspace:
    workspace = ensure_workspace_root(base / "workspace", create=True)
    _write_class_context(workspace)
    commit_record_batch(
        workspace,
        _profile_records(
            link_student=link_student,
            link_class_id=link_class_id,
            conflicting_student_link=conflicting_student_link,
            allow_assessment_summary=allow_assessment_summary,
        ),
        expected_state_revision=None,
    )

    scoreform_id, scoreform_path = _publish_fixture(
        workspace,
        module_id="vitrine_scoreform_fixture",
        work_id="argument_assessment",
        producer_contract_version="vitrine_fixture_scoreform_academic_work_v1",
        manifest_contract_version="vitrine_fixture_scoreform_manifest_v1",
        fixture_path=ROOT / "fixtures" / "producer-adapters" / "scoreform" / "manifest.json",
        source_record=None,
        capabilities=("multiple_attempts", "points", "question_evidence"),
        record_set_id="scoreform_fixture_results",
    )
    quillan_source = ModuleRecordRef(
        "vitrine_quillan_fixture",
        "submission",
        "submission_alpha",
        "vitrine_fixture_quillan_submission_v1",
    )
    quillan_id, quillan_path = _publish_fixture(
        workspace,
        module_id="vitrine_quillan_fixture",
        work_id="literary_analysis",
        producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
        manifest_contract_version="vitrine_fixture_quillan_manifest_v1",
        fixture_path=ROOT / "fixtures" / "producer-adapters" / "quillan" / "manifest.json",
        source_record=quillan_source,
        capabilities=(),
        record_set_id="quillan_fixture_results",
    )
    concord_source = ModuleRecordRef(
        "vitrine_concord_fixture",
        "artifact_instance",
        "artifact_water_quality",
        "vitrine_fixture_concord_artifact_v1",
    )
    concord_id, concord_path = _publish_fixture(
        workspace,
        module_id="vitrine_concord_fixture",
        work_id="water_quality_activity",
        producer_contract_version="vitrine_fixture_concord_academic_work_v1",
        manifest_contract_version="vitrine_fixture_concord_manifest_v1",
        fixture_path=ROOT / "fixtures" / "producer-adapters" / "concord" / "manifest.json",
        source_record=concord_source,
        capabilities=("criterion_scores",),
        record_set_id="concord_fixture_results",
    )
    rebuild_academic_catalog(workspace)
    return CandidateFixtureWorkspace(
        workspace=workspace,
        portfolio_id="portfolio_candidate_fixture",
        portfolio_subject_id="subject_candidate_fixture",
        profile_binding_id="profile_binding_candidate_fixture",
        scoreform_publication_id=scoreform_id,
        quillan_publication_id=quillan_id,
        concord_publication_id=concord_id,
        manifest_paths={
            "vitrine_scoreform_fixture": scoreform_path,
            "vitrine_quillan_fixture": quillan_path,
            "vitrine_concord_fixture": concord_path,
        },
    )


__all__ = [
    "ACTOR",
    "CLASS_ID",
    "CandidateFixtureWorkspace",
    "DeterministicIds",
    "NOW",
    "SCHOOL_YEAR",
    "STUDENT_ID",
    "StaticAuthorizationGate",
    "build_candidate_fixture_workspace",
    "fixed_clock",
]
