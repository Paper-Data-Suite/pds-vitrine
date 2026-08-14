"""Development-only executable support for the improvement Portfolio slice.

This module composes the generic identity, Candidate, curation, and Snapshot-ready
records.  It is deliberately fixture support rather than a production
``build_improvement_portfolio`` API.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery, rebuild_academic_catalog
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
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

from scripts.candidate_fixture_support import (
    DeterministicIds,
    StaticAuthorizationGate,
)
from scripts.curation_fixture_support import StaticCurationAuthorityGate
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    create_reflection,
    create_working_composition,
    decide_selection_proposal,
    place_selection,
    propose_candidate_selection,
)
from vitrine.curation_state import project_curation_state
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    CandidateEvaluation,
    ClassQualifiedStudentRef,
    CurationTargetRef,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileFamily,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSelection,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    SelectionDecision,
    SelectionProposal,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    activate_profile_revision,
    bind_portfolio_profile,
    create_profile_family,
    create_profile_revision,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)
from vitrine.subject_services import (
    IdentityDecisionContext,
    create_portfolio_subject,
    link_portfolio_subject,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "fixtures" / "representative-portfolios"
IMPROVEMENT_ROOT = FIXTURE_ROOT / "improvement"
NOW = datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)

PORTFOLIO_ID = "portfolio-improvement-syn-001"
SUBJECT_ID = "portfolio-subject-syn-001"
PROFILE_ID = "profile-improvement-rev-001"
PROFILE_BINDING_ID = "profile-binding-improvement-001"
PROFILE_FAMILY_ID = "profile-family-imp-001"
REFLECTION_REQUIREMENT_ID = "improvement-comparison-reflection"
BASELINE_CLASS_ID = "class-ela10-syn"
BASELINE_SCHOOL_YEAR = "2023-2024"
LATER_CLASS_ID = "class-ela11-syn"
LATER_SCHOOL_YEAR = "2024-2025"
STUDENT_ID = "student-syn-001"

TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="actor-teacher-syn-001",
    owning_system="vitrine",
    role_snapshot="teacher",
)
STUDENT = ActorAttribution(
    actor_kind="core_student",
    actor_id=STUDENT_ID,
    owning_system="pds-core",
    role_snapshot="student",
)


def fixed_clock() -> datetime:
    return NOW


@dataclass(frozen=True, slots=True)
class ImprovementPortfolioFixture:
    workspace: Path
    source_root: Path
    ids: DeterministicIds
    publications: tuple[str, str]
    evaluations: tuple[CandidateEvaluation, ...]
    candidates: tuple[PortfolioCandidate, ...]
    proposals: tuple[SelectionProposal, ...]
    decisions: tuple[SelectionDecision, ...]
    selections: tuple[PortfolioSelection, ...]
    placements: tuple[PortfolioPlacement, ...]
    reflection: PortfolioReflection
    composition: WorkingPortfolioCompositionRevision
    inventory: WorkingPortfolioCompositionInventory
    audience: AudienceContext

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision

    def candidate(self, source_record_id: str) -> PortfolioCandidate:
        return next(
            item
            for item in self.candidates
            if item.source_endpoint.producer_source.source_record_id == source_record_id
        )

    def selection(self, source_record_id: str) -> PortfolioSelection:
        candidate = self.candidate(source_record_id)
        return next(item for item in self.selections if item.candidate_id == candidate.candidate_id)

    def placement(self, source_record_id: str) -> PortfolioPlacement:
        selection = self.selection(source_record_id)
        return next(item for item in self.placements if item.selection_id == selection.selection_id)


class _ExactFixtureIds:
    """Return deterministic identities required by the #30/#31 service slice."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[str, ...]] = {
            "subject": (SUBJECT_ID,),
            "link": (
                "subject-link-ela10-syn-001",
                "subject-link-ela11-syn-001",
            ),
            "display": (
                "subject-display-ela10-syn-001",
                "subject-display-ela11-syn-001",
            ),
            "decision": (
                "subject-decision-create-syn-001",
                "subject-decision-link-ela10-syn-001",
                "subject-decision-link-ela11-syn-001",
            ),
            "profile_event": ("profile-event-improvement-activated-001",),
            "profile_binding": (PROFILE_BINDING_ID,),
        }
        self._positions: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        values = self._values.get(prefix)
        if values is None:
            raise RuntimeError(f"unexpected identity/profile fixture ID prefix: {prefix}")
        position = self._positions.get(prefix, 0)
        if position >= len(values):
            raise RuntimeError(f"exhausted identity/profile fixture IDs for prefix: {prefix}")
        self._positions[prefix] = position + 1
        return values[position]


def _profile_definitions() -> tuple[
    PortfolioProfileFamily,
    PortfolioProfileRevision,
    tuple[PortfolioProfileRequirement, ...],
]:
    family = PortfolioProfileFamily(
        profile_family_id=PROFILE_FAMILY_ID,
        label="Representative Improvement Portfolio",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=TEACHER,
    )
    sections = (
        ProfileSectionDefinition(
            section_id="baseline",
            label="Baseline",
            purpose="Explicit baseline student writing.",
            order=1,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="later_work",
            label="Later Work and Feedback",
            purpose=(
                "Explicit later writing followed by its separate student-facing "
                "feedback."
            ),
            order=2,
            obligation="required",
            minimum_placements=2,
            maximum_placements=2,
            allowed_candidate_kinds=("student_work", "feedback"),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="reflection",
            label="Reflection",
            purpose=(
                "Student-authored comparison of the exact baseline and later "
                "Selections."
            ),
            order=3,
            obligation="required",
            minimum_placements=0,
            maximum_placements=0,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=(),
            reflection_requirement="required",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id=PROFILE_ID,
        profile_revision=1,
        profile_family_id=PROFILE_FAMILY_ID,
        predecessor_revision=None,
        label="Representative Improvement Profile",
        purpose_kind="improvement",
        applicability=ProfileApplicability(
            school_years=(BASELINE_SCHOOL_YEAR, LATER_SCHOOL_YEAR)
        ),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="student-facing-improvement",
                audience_class="student",
                purpose=(
                    "Student-facing review of explicitly curated improvement "
                    "evidence."
                ),
                allowed_content_classes=("student_work", "feedback", "reflection"),
                prohibited_content_classes=("private_teacher_note",),
                required_review_classes=(),
                presentation_class="student_portfolio",
            ),
        ),
        created_at=NOW,
        created_by=TEACHER,
        source_authority_references=("representative-synthetic-policy",),
        known_limitations=("Fixture purpose does not calculate improvement.",),
    )
    section_requirements = tuple(
        PortfolioProfileRequirement(
            portfolio_profile_id=PROFILE_ID,
            profile_revision=1,
            requirement_id=f"{section.section_id}-section-requirement",
            requirement_kind="section",
            obligation="required",
            title=f"{section.label} requirement",
            statement="The exact section Arrangement must satisfy its cardinality.",
            scope_kind="section",
            satisfaction_class="placement_cardinality",
            scope_reference=section.section_id,
            authority_references=("representative-synthetic-policy",),
        )
        for section in sections
        if section.section_id != "reflection"
    )
    reflection_requirement = PortfolioProfileRequirement(
        portfolio_profile_id=PROFILE_ID,
        profile_revision=1,
        requirement_id=REFLECTION_REQUIREMENT_ID,
        requirement_kind="reflection",
        obligation="required",
        title="Student comparison reflection",
        statement=(
            "The student interprets the explicitly ordered baseline and later "
            "Selections."
        ),
        scope_kind="section",
        scope_reference="reflection",
        satisfaction_class="reflection_presence",
        authority_references=("representative-synthetic-policy",),
    )
    return family, revision, (*section_requirements, reflection_requirement)


def _initialize_identity_and_profile(
    workspace: Path,
    *,
    include_later_link: bool,
) -> None:
    """Exercise the #30 Subject and #31 Profile application-service boundaries."""

    ids = _ExactFixtureIds()
    identity_context = IdentityDecisionContext(
        actor=TEACHER,
        authority_source="representative-synthetic-roster",
        basis_type="direct_teacher_knowledge",
        basis_summary=(
            "Synthetic fixture explicitly confirms the class-qualified roster "
            "relationship."
        ),
    )
    baseline_reference = ClassQualifiedStudentRef(
        class_id=BASELINE_CLASS_ID,
        student_id=STUDENT_ID,
        school_year=BASELINE_SCHOOL_YEAR,
    )
    created = create_portfolio_subject(
        workspace,
        baseline_reference,
        context=identity_context,
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    if created.subject_ids != (SUBJECT_ID,):
        raise RuntimeError("Subject service did not create the exact fixture Subject")
    if include_later_link:
        link_portfolio_subject(
            workspace,
            SUBJECT_ID,
            ClassQualifiedStudentRef(
                class_id=LATER_CLASS_ID,
                student_id=STUDENT_ID,
                school_year=LATER_SCHOOL_YEAR,
            ),
            context=identity_context,
            expected_state_revision=load_current_state(workspace).state_revision,
            clock=fixed_clock,
            id_factory=ids,
        )

    portfolio = Portfolio(
        portfolio_id=PORTFOLIO_ID,
        portfolio_subject_id=SUBJECT_ID,
        created_at=NOW,
        created_by=TEACHER,
        title_snapshot="Synthetic Improvement Portfolio",
    )
    commit_record_batch(
        workspace,
        (portfolio,),
        expected_state_revision=load_current_state(workspace).state_revision,
    )

    family, revision, requirements = _profile_definitions()
    create_profile_family(
        workspace,
        family,
        expected_state_revision=load_current_state(workspace).state_revision,
    )
    create_profile_revision(
        workspace,
        revision,
        requirements,
        expected_state_revision=load_current_state(workspace).state_revision,
    )
    activate_profile_revision(
        workspace,
        revision.reference,
        actor=TEACHER,
        reason="Activate the representative synthetic improvement Profile.",
        authority_reference="representative-synthetic-policy",
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    bound = bind_portfolio_profile(
        workspace,
        PORTFOLIO_ID,
        revision.reference,
        actor=TEACHER,
        binding_reason="Execute the representative improvement vertical slice.",
        context=ProfileBindingContext(school_year=LATER_SCHOOL_YEAR),
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    if bound.record_ids != (PROFILE_BINDING_ID,):
        raise RuntimeError("Profile service did not create the exact fixture Binding")


def _write_class_context(workspace: Path, class_id: str, school_year: str, period: str) -> None:
    metadata = create_class_metadata(class_id, school_year, created_at=NOW, module_details={})
    write_class_metadata_for_class(workspace, metadata)
    roster = validate_roster_rows(
        ROSTER_REQUIRED_COLUMNS,
        (
            {
                "class_id": class_id,
                "student_id": STUDENT_ID,
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": period,
            },
            {
                "class_id": class_id,
                "student_id": "same-looking-unlinked-syn-001",
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": period,
            },
        ),
    )
    write_class_roster(workspace, roster)


def _publish(
    workspace: Path,
    *,
    class_id: str,
    work_id: str,
    source_id: str,
    manifest_fixture: Path,
) -> tuple[str, Path]:
    work = ModuleWorkRef("vitrine_quillan_fixture", class_id, work_id)
    work_root = module_work_dir(workspace, work)
    work_root.mkdir(parents=True, exist_ok=True)
    source_record = ModuleRecordRef(
        "vitrine_quillan_fixture",
        "submission",
        source_id,
        "vitrine_fixture_quillan_submission_v1",
    )
    registration = register_academic_work(
        workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
            title=f"Synthetic {work_id}",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=(source_record,),
        ),
    ).registration
    manifest_path = work_root / "exports" / "manifests" / "improvement_fixture" / "1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest_fixture, manifest_path)
    publication = publish_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work,
            source_record=source_record,
            publication_kind="academic_result_set",
            capabilities=(),
            record_set_id="improvement_fixture",
            record_set_revision=1,
            manifest_contract_version="vitrine_fixture_quillan_manifest_v1",
            manifest_path=manifest_path.relative_to(workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    return publication.publication_id, manifest_path


def _prepare_sources(destination: Path) -> Path:
    source_root = destination.resolve()
    artifacts = source_root / "artifacts"
    artifacts.mkdir(parents=True)
    source = FIXTURE_ROOT / "shared" / "artifact-bytes" / "quillan"
    for name in ("baseline-argument.txt", "revised-argument.txt", "revised-feedback.txt"):
        shutil.copyfile(source / name, artifacts / name)
    return source_root.resolve(strict=True)


def _select(
    workspace: Path,
    ids: DeterministicIds,
    candidate: PortfolioCandidate,
    section_id: str,
) -> tuple[SelectionProposal, SelectionDecision, PortfolioSelection]:
    proposed = propose_candidate_selection(
        workspace,
        portfolio_id=PORTFOLIO_ID,
        candidate_id=candidate.candidate_id,
        proposer=STUDENT,
        proposal_origin="student",
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Explicit synthetic student curation decision.",
        clock=fixed_clock,
        id_factory=ids,
    )
    proposal = next(item for item in proposed.records if isinstance(item, SelectionProposal))
    decided = decide_selection_proposal(
        workspace,
        portfolio_id=PORTFOLIO_ID,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="accepted",
        decided_by=TEACHER,
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Accept the student's exact synthetic evidence choice.",
        clock=fixed_clock,
        id_factory=ids,
    )
    decision = next(item for item in decided.records if isinstance(item, SelectionDecision))
    selection = next(item for item in decided.records if isinstance(item, PortfolioSelection))
    return proposal, decision, selection


def _place(
    workspace: Path,
    ids: DeterministicIds,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    state = project_curation_state(load_current_records(workspace))
    heads = state.arrangement_pointer_heads(PORTFOLIO_ID, PROFILE_BINDING_ID, section_id)
    pointer_revision = heads[0].pointer_revision if len(heads) == 1 else None
    result = place_selection(
        workspace,
        portfolio_id=PORTFOLIO_ID,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=STUDENT,
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_arrangement_pointer_revision=pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def build_improvement_portfolio_fixture(
    base: Path,
    *,
    include_later_link: bool = True,
    complete_curation: bool = True,
) -> ImprovementPortfolioFixture | tuple[Path, tuple[CandidateEvaluation, ...], tuple[PortfolioCandidate, ...]]:
    """Execute the representative identity/Profile/Candidate/curation fixture.

    ``complete_curation=False`` is a focused negative-test hook: it stops after
    Candidate discovery without fabricating Selections.
    """

    workspace = ensure_workspace_root(base / "workspace", create=True)
    _write_class_context(workspace, BASELINE_CLASS_ID, BASELINE_SCHOOL_YEAR, "2")
    _write_class_context(workspace, LATER_CLASS_ID, LATER_SCHOOL_YEAR, "4")
    _initialize_identity_and_profile(
        workspace,
        include_later_link=include_later_link,
    )
    baseline_publication, _ = _publish(
        workspace,
        class_id=BASELINE_CLASS_ID,
        work_id="baseline_argument",
        source_id="submission_baseline_syn_001",
        manifest_fixture=IMPROVEMENT_ROOT / "runtime" / "baseline-manifest.json",
    )
    later_publication, _ = _publish(
        workspace,
        class_id=LATER_CLASS_ID,
        work_id="revised_argument",
        source_id="submission_revised_syn_001",
        manifest_fixture=IMPROVEMENT_ROOT / "runtime" / "later-manifest.json",
    )
    rebuild_academic_catalog(workspace)
    ids = DeterministicIds()
    discovery = discover_and_evaluate_candidates(
        workspace,
        CandidateDiscoveryRequest(
            portfolio_id=PORTFOLIO_ID,
            requesting_actor=TEACHER,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="vitrine_quillan_fixture", state="current", limit=10
            ),
            expected_state_revision=load_current_state(workspace).state_revision,
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=ids,
    )
    evaluations = tuple(item.evaluation for item in discovery.evaluation_results)
    candidates = tuple(
        item.candidate for item in discovery.evaluation_results if item.candidate is not None
    )
    if not complete_curation:
        return workspace, evaluations, candidates
    if len(candidates) != 3:
        raise RuntimeError("representative discovery did not create exactly three Candidates")
    by_source = {
        item.source_endpoint.producer_source.source_record_id: item for item in candidates
    }
    selected = (
        _select(workspace, ids, by_source["baseline_argument"], "baseline"),
        _select(workspace, ids, by_source["revised_argument"], "later_work"),
        _select(workspace, ids, by_source["revised_feedback"], "later_work"),
    )
    proposals = tuple(item[0] for item in selected)
    decisions = tuple(item[1] for item in selected)
    selections = tuple(item[2] for item in selected)
    placements = (
        _place(workspace, ids, selections[0], "baseline"),
        _place(workspace, ids, selections[1], "later_work"),
        _place(workspace, ids, selections[2], "later_work"),
    )
    reflected = create_reflection(
        workspace,
        portfolio_id=PORTFOLIO_ID,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="compare-baseline-later",
        prompt_version="1",
        prompt_snapshot="Compare the baseline and later writing and explain what you changed.",
        author=STUDENT,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[0].selection_id,
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[1].selection_id,
                semantic_role="later",
            ),
        ),
        content=(
            "I made the later claim more specific and connected each quoted detail "
            "to my reasoning. This is my comparison of the two pieces."
        ),
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=ids,
    )
    reflection = next(item for item in reflected.records if isinstance(item, PortfolioReflection))
    composed = create_working_composition(
        workspace,
        portfolio_id=PORTFOLIO_ID,
        created_by=STUDENT,
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze the exact representative improvement curation state.",
        clock=fixed_clock,
        id_factory=ids,
    )
    composition = next(
        item for item in composed.records if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item for item in composed.records if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    profile = next(
        item
        for item in load_current_records(workspace)
        if isinstance(item, PortfolioProfileRevision) and item.reference == composition.profile_revision
    )
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id="audience-imp-student",
        portfolio_id=PORTFOLIO_ID,
        portfolio_subject_id=SUBJECT_ID,
        profile_binding_id=PROFILE_BINDING_ID,
        profile_revision=composition.profile_revision,
        audience_rule_id=rule.audience_rule_id,
        audience_class=rule.audience_class,
        purpose=rule.purpose,
        subject_scope="portfolio_subject",
        allowed_content_classes=rule.allowed_content_classes,
        prohibited_content_classes=rule.prohibited_content_classes,
        required_review_classes=rule.required_review_classes,
        presentation_class=rule.presentation_class,
        retention_policy_reference=rule.retention_policy_reference,
        created_at=NOW,
        created_by=TEACHER,
    )
    commit_record_batch(
        workspace, (audience,), expected_state_revision=load_current_state(workspace).state_revision
    )
    source_root = _prepare_sources(base / "producer-source")
    return ImprovementPortfolioFixture(
        workspace=workspace,
        source_root=source_root,
        ids=ids,
        publications=(baseline_publication, later_publication),
        evaluations=evaluations,
        candidates=candidates,
        proposals=proposals,
        decisions=decisions,
        selections=selections,
        placements=placements,
        reflection=reflection,
        composition=composition,
        inventory=inventory,
        audience=audience,
    )


__all__ = [
    "BASELINE_CLASS_ID",
    "BASELINE_SCHOOL_YEAR",
    "IMPROVEMENT_ROOT",
    "ImprovementPortfolioFixture",
    "LATER_CLASS_ID",
    "LATER_SCHOOL_YEAR",
    "NOW",
    "PORTFOLIO_ID",
    "PROFILE_BINDING_ID",
    "PROFILE_ID",
    "REFLECTION_REQUIREMENT_ID",
    "STUDENT",
    "STUDENT_ID",
    "SUBJECT_ID",
    "TEACHER",
    "build_improvement_portfolio_fixture",
    "fixed_clock",
]
