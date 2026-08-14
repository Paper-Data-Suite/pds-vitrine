"""Development-only orchestration for the representative showcase Portfolio slice."""

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

from scripts.candidate_fixture_support import StaticAuthorizationGate
from scripts.curation_fixture_support import StaticCurationAuthorityGate
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    CandidateEvaluationResult,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    create_annotation,
    create_working_composition,
    decide_selection_proposal,
    place_selection,
    propose_candidate_selection,
    review_curation_target,
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
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileFamily,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
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
from vitrine.subject_services import IdentityDecisionContext, create_portfolio_subject

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_ROOT = ROOT / "fixtures" / "representative-portfolios" / "showcase"
SHARED_ROOT = ROOT / "fixtures" / "representative-portfolios" / "shared"
NOW = datetime(2026, 8, 14, 17, 0, tzinfo=timezone.utc)

PORTFOLIO_ID = "portfolio-showcase-syn-001"
SUBJECT_ID = "portfolio-subject-syn-001"
PROFILE_FAMILY_ID = "profile-family-show-001"
PROFILE_ID = "profile-showcase-rev-001"
PROFILE_BINDING_ID = "profile-binding-showcase-001"
APPROVAL_REQUIREMENT_ID = "showcase_collaborator_treatment_review"
AUDIENCE_ID = "audience-show-external"
CLASS_ID = "class-ela12-syn"
SCHOOL_YEAR = "2025-2026"
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

ATTRIBUTION_TEXT = (
    "Audience-safe attribution: Created by Synthetic Group 7. The Portfolio Subject "
    "contributed the methods paragraph and chart explanation. Collaborator display "
    "names are intentionally omitted."
)
RATIONALE_TEXT = (
    "The individual analysis demonstrates close reading. The collaborative artifact "
    "demonstrates contribution to a shared investigation. The attribution statement "
    "preserves the subject contribution without displaying collaborator identities."
)


def fixed_clock() -> datetime:
    return NOW


class ShowcaseIds:
    """Deterministic IDs, preserving accepted representative identities where useful."""

    def __init__(self) -> None:
        self._exact: dict[str, list[str]] = {
            "subject": [SUBJECT_ID],
            "link": ["subject-link-showcase-001"],
            "display": ["subject-display-showcase-001"],
            "decision": ["subject-decision-showcase-create-001", "subject-decision-showcase-link-001"],
            "profile_event": ["profile-event-showcase-activated-001"],
            "profile_binding": [PROFILE_BINDING_ID],
            "candidate": ["candidate-show-polished", "candidate-show-group"],
            "selection_proposal": ["selection-proposal-show-polished", "selection-proposal-show-group"],
            "selection_decision": ["selection-decision-show-polished", "selection-decision-show-group"],
            "selection": ["selection-show-polished", "selection-show-group"],
            "placement": ["placement-show-001", "placement-show-002"],
            "annotation": ["annotation-show-attribution", "annotation-show-rationale"],
            "curation_review": ["collaborator-review-show-001"],
            "snapshot_series": ["snapshot-series-show-001"],
            "snapshot_request": ["snapshot-build-request-show-001"],
            "snapshot_plan": ["snapshot-build-plan-show-001"],
            "snapshot_attempt": ["snapshot-build-attempt-show-001"],
            "snapshot_seal": ["snapshot-seal-show-001"],
        }
        self._counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        index = self._counts.get(prefix, 0)
        self._counts[prefix] = index + 1
        values = self._exact.get(prefix, [])
        return values[index] if index < len(values) else f"{prefix}-show-{index + 1:03d}"


@dataclass(frozen=True, slots=True)
class ShowcasePortfolioFixture:
    workspace: Path
    source_root: Path
    ids: ShowcaseIds
    publications: tuple[str, str]
    projection_results: tuple[CandidateEvaluationResult, ...]
    evaluations: tuple[CandidateEvaluation, ...]
    candidates: tuple[PortfolioCandidate, ...]
    proposals: tuple[SelectionProposal, ...]
    decisions: tuple[SelectionDecision, ...]
    selections: tuple[PortfolioSelection, ...]
    placements: tuple[PortfolioPlacement, ...]
    attribution: CurationAnnotation
    rationale: CurationAnnotation
    review: CurationReviewDecision
    composition: WorkingPortfolioCompositionRevision
    inventory: WorkingPortfolioCompositionInventory
    audience: AudienceContext

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision

    def candidate(self, source_record_id: str) -> PortfolioCandidate:
        return next(
            item for item in self.candidates
            if item.source_endpoint.producer_source.source_record_id == source_record_id
        )

    def selection(self, source_record_id: str) -> PortfolioSelection:
        candidate = self.candidate(source_record_id)
        return next(item for item in self.selections if item.candidate_id == candidate.candidate_id)

    def placement(self, source_record_id: str) -> PortfolioPlacement:
        selection = self.selection(source_record_id)
        return next(item for item in self.placements if item.selection_id == selection.selection_id)


def _write_class_context(workspace: Path) -> None:
    write_class_metadata_for_class(
        workspace,
        create_class_metadata(CLASS_ID, SCHOOL_YEAR, created_at=NOW, module_details={}),
    )
    roster = validate_roster_rows(
        ROSTER_REQUIRED_COLUMNS,
        (
            {"class_id": CLASS_ID, "student_id": STUDENT_ID, "last_name": "Student", "first_name": "Synthetic", "period": "1"},
            {"class_id": CLASS_ID, "student_id": "same-looking-showcase-syn-001", "last_name": "Student", "first_name": "Synthetic", "period": "1"},
        ),
    )
    write_class_roster(workspace, roster)


def _profile() -> tuple[PortfolioProfileFamily, PortfolioProfileRevision, tuple[PortfolioProfileRequirement, ...]]:
    family = PortfolioProfileFamily(
        profile_family_id=PROFILE_FAMILY_ID,
        label="Representative Showcase Portfolio",
        purpose_kind="showcase",
        created_at=NOW,
        created_by=TEACHER,
    )
    sections = (
        ProfileSectionDefinition(
            section_id="featured_work", label="Featured Work",
            purpose="Polished individual work.", order=1, obligation="required",
            minimum_placements=1, maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="collaboration", label="Collaboration",
            purpose="Reviewed collaborative evidence with an exact documented contribution.",
            order=2, obligation="required", minimum_placements=1, maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("documented_contributor",),
            reflection_requirement="none",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id=PROFILE_ID,
        profile_revision=1,
        profile_family_id=PROFILE_FAMILY_ID,
        predecessor_revision=None,
        label="Representative Showcase Profile",
        purpose_kind="showcase",
        applicability=ProfileApplicability(school_years=(SCHOOL_YEAR,)),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="external-review-showcase",
                audience_class="external_reviewer",
                purpose="Minimum-necessary synthetic external-review showcase.",
                allowed_content_classes=("student_work", "audience_safe_attribution", "curation_rationale", "portfolio_index"),
                prohibited_content_classes=("private_teacher_note", "raw_collaborator_data", "secure_assessment_content", "restricted_internal"),
                required_review_classes=("privacy_review",),
                presentation_class="showcase",
            ),
        ),
        created_at=NOW,
        created_by=TEACHER,
        source_authority_references=("representative-synthetic-showcase-policy",),
        known_limitations=("Curation review is not recipient or disclosure authorization.",),
    )
    requirements = tuple(
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
            authority_references=("representative-synthetic-showcase-policy",),
        ) for section in sections
    ) + (
        PortfolioProfileRequirement(
            portfolio_profile_id=PROFILE_ID,
            profile_revision=1,
            requirement_id=APPROVAL_REQUIREMENT_ID,
            requirement_kind="approval",
            obligation="required",
            title="Showcase collaborator treatment review",
            statement="Review exact collaborative curation and minimum-necessary presentation.",
            scope_kind="portfolio",
            satisfaction_class="curation_review",
            authority_references=("representative-synthetic-showcase-policy",),
        ),
    )
    return family, revision, requirements


def _initialize(workspace: Path, ids: ShowcaseIds) -> None:
    context = IdentityDecisionContext(
        actor=TEACHER,
        authority_source="representative-synthetic-roster",
        basis_type="direct_teacher_knowledge",
        basis_summary="Exact class-qualified synthetic roster relationship.",
    )
    created = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id=CLASS_ID, student_id=STUDENT_ID, school_year=SCHOOL_YEAR),
        context=context,
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    if created.subject_ids != (SUBJECT_ID,):
        raise RuntimeError("showcase Subject identity is not exact")
    commit_record_batch(
        workspace,
        (Portfolio(portfolio_id=PORTFOLIO_ID, portfolio_subject_id=SUBJECT_ID, created_at=NOW, created_by=TEACHER, title_snapshot="Synthetic Showcase Portfolio"),),
        expected_state_revision=load_current_state(workspace).state_revision,
    )
    family, revision, requirements = _profile()
    create_profile_family(workspace, family, expected_state_revision=load_current_state(workspace).state_revision)
    create_profile_revision(workspace, revision, requirements, expected_state_revision=load_current_state(workspace).state_revision)
    activate_profile_revision(
        workspace, revision.reference, actor=TEACHER,
        reason="Activate representative synthetic showcase Profile.",
        authority_reference="representative-synthetic-showcase-policy",
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock, id_factory=ids,
    )
    bind_portfolio_profile(
        workspace, PORTFOLIO_ID, revision.reference, actor=TEACHER,
        binding_reason="Execute representative showcase vertical slice.",
        context=ProfileBindingContext(school_year=SCHOOL_YEAR),
        expected_state_revision=load_current_state(workspace).state_revision,
        clock=fixed_clock, id_factory=ids,
    )


def _publish(workspace: Path, *, module_id: str, work_id: str, source_record: ModuleRecordRef, manifest: Path, record_set: str, capabilities: tuple[PublicationCapability, ...]) -> str:
    work = ModuleWorkRef(module_id, CLASS_ID, work_id)
    root = module_work_dir(workspace, work)
    root.mkdir(parents=True, exist_ok=True)
    registration = register_academic_work(
        workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version=f"vitrine_fixture_{'quillan' if 'quillan' in module_id else 'concord'}_academic_work_v1",
            title=f"Synthetic {work_id}", work_kind="assignment", academic_intent="formative",
            lifecycle="active", source_records=(source_record,),
        ),
    ).registration
    target = root / "exports" / "manifests" / record_set / "1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, target)
    return publish_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work, source_record=source_record, publication_kind="academic_result_set",
            capabilities=capabilities, record_set_id=record_set, record_set_revision=1,
            manifest_contract_version=f"vitrine_fixture_{'quillan' if 'quillan' in module_id else 'concord'}_manifest_v1",
            manifest_path=target.relative_to(workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication.publication_id


def _discover(workspace: Path, ids: ShowcaseIds, module_id: str) -> tuple[CandidateEvaluationResult, ...]:
    result = discover_and_evaluate_candidates(
        workspace,
        CandidateDiscoveryRequest(
            portfolio_id=PORTFOLIO_ID, requesting_actor=TEACHER, requested_purpose="showcase",
            catalog_query=PublicationCatalogQuery(module_id=module_id, state="current", limit=10),
            expected_state_revision=load_current_state(workspace).state_revision,
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock, id_factory=ids,
    )
    return result.evaluation_results


def _select(workspace: Path, ids: ShowcaseIds, candidate: PortfolioCandidate, section: str) -> tuple[SelectionProposal, SelectionDecision, PortfolioSelection]:
    proposed = propose_candidate_selection(
        workspace, portfolio_id=PORTFOLIO_ID, candidate_id=candidate.candidate_id,
        proposer=STUDENT, proposal_origin="student", proposed_section_ids=(section,),
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Explicit synthetic student showcase choice.",
        clock=fixed_clock, id_factory=ids,
    )
    proposal = next(item for item in proposed.records if isinstance(item, SelectionProposal))
    decided = decide_selection_proposal(
        workspace, portfolio_id=PORTFOLIO_ID,
        selection_proposal_id=proposal.selection_proposal_id, decision="accepted",
        decided_by=TEACHER,
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(acknowledge_conditions=True),
        rationale_text="Accept exact evidence while acknowledging any Candidate condition.",
        clock=fixed_clock, id_factory=ids,
    )
    return (
        proposal,
        next(item for item in decided.records if isinstance(item, SelectionDecision)),
        next(item for item in decided.records if isinstance(item, PortfolioSelection)),
    )


def _place(workspace: Path, ids: ShowcaseIds, selection: PortfolioSelection, section: str) -> PortfolioPlacement:
    heads = project_curation_state(load_current_records(workspace)).arrangement_pointer_heads(PORTFOLIO_ID, PROFILE_BINDING_ID, section)
    result = place_selection(
        workspace, portfolio_id=PORTFOLIO_ID, selection_id=selection.selection_id,
        section_id=section, placed_by=STUDENT,
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_arrangement_pointer_revision=heads[0].pointer_revision if len(heads) == 1 else None,
        authority_gate=StaticCurationAuthorityGate(), clock=fixed_clock, id_factory=ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def _prepare_sources(base: Path) -> Path:
    root = base.resolve()
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    shutil.copyfile(SHARED_ROOT / "artifact-bytes" / "quillan" / "polished-literary-analysis.txt", artifacts / "polished-literary-analysis.txt")
    shutil.copyfile(SHARED_ROOT / "artifact-bytes" / "concord" / "group-artifact.txt", artifacts / "group-artifact.txt")
    return root.resolve(strict=True)


def build_showcase_portfolio_fixture(base: Path, *, complete_curation: bool = True) -> ShowcasePortfolioFixture | tuple[Path, tuple[CandidateEvaluationResult, ...]]:
    """Compose generic runtime services; this is fixture support, not a production API."""
    workspace = ensure_workspace_root(base / "workspace", create=True)
    ids = ShowcaseIds()
    _write_class_context(workspace)
    _initialize(workspace, ids)
    polished_publication = _publish(
        workspace, module_id="vitrine_quillan_fixture", work_id="quillan-work-polished",
        source_record=ModuleRecordRef("vitrine_quillan_fixture", "submission", "submission_showcase_polished", "vitrine_fixture_quillan_submission_v1"),
        manifest=SHOWCASE_ROOT / "runtime" / "polished-manifest.json",
        record_set="showcase_polished", capabilities=(),
    )
    concord_publication = _publish(
        workspace, module_id="vitrine_concord_fixture", work_id="concord-work-syn-001",
        source_record=ModuleRecordRef("vitrine_concord_fixture", "artifact_instance", "concord-artifact-syn-001", "vitrine_fixture_concord_artifact_v1"),
        manifest=SHOWCASE_ROOT / "runtime" / "concord-manifest.json",
        record_set="showcase_concord", capabilities=("criterion_scores",),
    )
    rebuild_academic_catalog(workspace)
    projection_results = (*_discover(workspace, ids, "vitrine_quillan_fixture"), *_discover(workspace, ids, "vitrine_concord_fixture"))
    if not complete_curation:
        return workspace, projection_results
    candidates = tuple(item.candidate for item in projection_results if item.candidate is not None)
    evaluations = tuple(item.evaluation for item in projection_results)
    if len(candidates) != 2:
        raise RuntimeError("showcase discovery did not create exactly two Candidates")
    by_source = {item.source_endpoint.producer_source.source_record_id: item for item in candidates}
    selected = (
        _select(workspace, ids, by_source["polished_literary_analysis"], "featured_work"),
        _select(workspace, ids, by_source["concord-artifact-syn-001"], "collaboration"),
    )
    proposals = tuple(item[0] for item in selected)
    decisions = tuple(item[1] for item in selected)
    selections = tuple(item[2] for item in selected)
    placements = (
        _place(workspace, ids, selections[0], "featured_work"),
        _place(workspace, ids, selections[1], "collaboration"),
    )
    annotation_result = create_annotation(
        workspace, portfolio_id=PORTFOLIO_ID, purpose="curator_context",
        target_scope="selection",
        target_references=(CurationTargetRef(target_kind="selection", target_id=selections[1].selection_id, semantic_role="collaborative_artifact"),),
        author=TEACHER, content=ATTRIBUTION_TEXT,
        intended_presentation_class="showcase",
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(), clock=fixed_clock, id_factory=ids,
    )
    attribution = next(item for item in annotation_result.records if isinstance(item, CurationAnnotation))
    rationale_result = create_annotation(
        workspace, portfolio_id=PORTFOLIO_ID, purpose="comparison_note",
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(target_kind="selection", target_id=selections[0].selection_id, semantic_role="individual_work"),
            CurationTargetRef(target_kind="selection", target_id=selections[1].selection_id, semantic_role="collaborative_artifact"),
        ),
        author=STUDENT, content=RATIONALE_TEXT,
        intended_presentation_class="showcase",
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(), clock=fixed_clock, id_factory=ids,
    )
    rationale = next(item for item in rationale_result.records if isinstance(item, CurationAnnotation))
    reviewed = review_curation_target(
        workspace, portfolio_id=PORTFOLIO_ID, target_scope="showcase_collaborator_treatment",
        target_references=(
            CurationTargetRef(target_kind="selection", target_id=selections[1].selection_id, semantic_role="reviewed_artifact"),
            CurationTargetRef(target_kind="annotation", target_id=attribution.annotation_id, target_revision=attribution.annotation_revision, semantic_role="audience_safe_attribution"),
        ),
        decision="approved", reviewed_by=TEACHER,
        reason="Exact synthetic bytes and attribution omit collaborator display names, preserve collective Group authorship and the documented Subject contribution; this is curation review, not disclosure authorization.",
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(), clock=fixed_clock, id_factory=ids,
    )
    review = next(item for item in reviewed.records if isinstance(item, CurationReviewDecision))
    composed = create_working_composition(
        workspace, portfolio_id=PORTFOLIO_ID, created_by=STUDENT,
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze exact representative showcase curation state.",
        clock=fixed_clock, id_factory=ids,
    )
    composition = next(item for item in composed.records if isinstance(item, WorkingPortfolioCompositionRevision))
    inventory = next(item for item in composed.records if isinstance(item, WorkingPortfolioCompositionInventory))
    profile = next(item for item in load_current_records(workspace) if isinstance(item, PortfolioProfileRevision) and item.reference == composition.profile_revision)
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id=AUDIENCE_ID, portfolio_id=PORTFOLIO_ID,
        portfolio_subject_id=SUBJECT_ID, profile_binding_id=PROFILE_BINDING_ID,
        profile_revision=composition.profile_revision, audience_rule_id=rule.audience_rule_id,
        audience_class=rule.audience_class, purpose=rule.purpose,
        subject_scope="portfolio_subject", allowed_content_classes=rule.allowed_content_classes,
        prohibited_content_classes=rule.prohibited_content_classes,
        required_review_classes=rule.required_review_classes,
        presentation_class=rule.presentation_class,
        retention_policy_reference=rule.retention_policy_reference,
        created_at=NOW, created_by=TEACHER,
    )
    commit_record_batch(workspace, (audience,), expected_state_revision=load_current_state(workspace).state_revision)
    return ShowcasePortfolioFixture(
        workspace=workspace, source_root=_prepare_sources(base / "producer-source"), ids=ids,
        publications=(polished_publication, concord_publication),
        projection_results=projection_results, evaluations=evaluations, candidates=candidates,
        proposals=proposals, decisions=decisions, selections=selections, placements=placements,
        attribution=attribution, rationale=rationale, review=review,
        composition=composition, inventory=inventory, audience=audience,
    )


__all__ = [
    "APPROVAL_REQUIREMENT_ID", "ATTRIBUTION_TEXT", "AUDIENCE_ID", "CLASS_ID",
    "PORTFOLIO_ID", "PROFILE_BINDING_ID", "PROFILE_ID", "RATIONALE_TEXT",
    "SCHOOL_YEAR", "STUDENT", "STUDENT_ID", "SUBJECT_ID", "TEACHER",
    "ShowcasePortfolioFixture", "build_showcase_portfolio_fixture", "fixed_clock",
]
