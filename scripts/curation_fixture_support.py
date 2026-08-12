"""Development-only fixture support for issue #34 curation workflows."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    NOW,
    STUDENT_ID,
    CandidateFixtureWorkspace,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    VitrineRecord,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_state,
)

CURATION_PORTFOLIO_ID = "portfolio_curation_fixture"
CURATION_PROFILE_ID = "profile_curation_fixture"
CURATION_BINDING_ID = "profile_binding_curation_fixture"
REFLECTION_REQUIREMENT_ID = "reflection_growth_comparison"
APPROVAL_REQUIREMENT_ID = "approval_teacher_review"

STUDENT_ACTOR = ActorAttribution(
    actor_kind="core_student",
    actor_id=STUDENT_ID,
    owning_system="core",
    role_snapshot="student",
)


class StaticCurationAuthorityGate:
    """Explicit synthetic curation-authority decision for tests only."""

    def __init__(
        self,
        outcome: str = "allowed",
        *,
        acknowledge_conditions: bool = True,
        waiver_permitted: bool = False,
    ) -> None:
        self.outcome = outcome
        self.acknowledge_conditions = acknowledge_conditions
        self.waiver_permitted = waiver_permitted
        self.requests: list[CurationAuthorityRequest] = []

    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        self.requests.append(request)
        acknowledged = (
            (request.candidate_condition_state,)
            if self.acknowledge_conditions
            and request.candidate_condition_state is not None
            and request.candidate_condition_state != "ready_for_consideration"
            else ()
        )
        return CurationAuthorityDecision(
            outcome=self.outcome,
            authority_reference=(
                "fixture_curation_authority" if self.outcome == "allowed" else None
            ),
            reason_codes=("fixture_authority",),
            acknowledged_condition_codes=acknowledged,
            waiver_permitted=self.waiver_permitted,
        )


@dataclass(frozen=True, slots=True)
class CurationFixtureWorkspace:
    candidate_setup: CandidateFixtureWorkspace
    portfolio_id: str
    profile_binding_id: str
    candidate_ids_by_source: dict[str, str]
    candidate_records_by_source: dict[str, PortfolioCandidate]
    ids: DeterministicIds

    @property
    def workspace(self) -> Path:
        return self.candidate_setup.workspace

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision

    def candidate(self, source_record_id: str) -> PortfolioCandidate:
        return self.candidate_records_by_source[source_record_id]


def _curation_profile_records(subject_id: str) -> tuple[VitrineRecord, ...]:
    portfolio = Portfolio(
        portfolio_id=CURATION_PORTFOLIO_ID,
        portfolio_subject_id=subject_id,
        created_at=NOW,
        created_by=ACTOR,
        title_snapshot="Synthetic Curation Portfolio",
    )
    family = PortfolioProfileFamily(
        profile_family_id="family_curation_fixture",
        label="Synthetic Curation Profiles",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=ACTOR,
    )
    sections = (
        ProfileSectionDefinition(
            section_id="baseline",
            label="Baseline",
            purpose="One baseline student-work sample.",
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
            label="Later Work",
            purpose="One later student-work sample.",
            order=2,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="feedback",
            label="Feedback",
            purpose="Student-facing feedback context.",
            order=3,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=1,
            allowed_candidate_kinds=("feedback",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="assessment",
            label="Assessment",
            purpose="At most one assessment summary.",
            order=4,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=1,
            allowed_candidate_kinds=("assessment_summary",),
            required_relationship_kinds=("attempt_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="collaborative",
            label="Collaborative Work",
            purpose="Collaborative artifact with documented contribution.",
            order=5,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("documented_contributor",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="gallery",
            label="Gallery",
            purpose="Multiple explicitly ordered student-work samples.",
            order=6,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="prohibited_internal",
            label="Prohibited Internal",
            purpose="Synthetic prohibited section.",
            order=7,
            obligation="prohibited",
            minimum_placements=0,
            maximum_placements=0,
            allowed_candidate_kinds=(),
            required_relationship_kinds=(),
            reflection_requirement="none",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id=CURATION_PROFILE_ID,
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Synthetic Improvement Curation",
        purpose_kind="improvement",
        applicability=ProfileApplicability(school_years=("2026-2027",)),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="student_internal",
                audience_class="student",
                purpose="Synthetic internal curation review.",
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
        source_authority_references=("fixture_curation_policy",),
    )
    section_requirements = tuple(
        PortfolioProfileRequirement(
            portfolio_profile_id=revision.portfolio_profile_id,
            profile_revision=revision.profile_revision,
            requirement_id=f"{section.section_id}_section_rule",
            requirement_kind="section",
            obligation=section.obligation,
            title=f"{section.label} section rule",
            statement="Synthetic machine-checkable section rule.",
            scope_kind="section",
            satisfaction_class="placement_cardinality",
            scope_reference=section.section_id,
            authority_references=("fixture_curation_policy",),
        )
        for section in sections
    )
    reflection = PortfolioProfileRequirement(
        portfolio_profile_id=revision.portfolio_profile_id,
        profile_revision=revision.profile_revision,
        requirement_id=REFLECTION_REQUIREMENT_ID,
        requirement_kind="reflection",
        obligation="required",
        title="Growth comparison reflection",
        statement="Student authors one comparison reflection.",
        scope_kind="portfolio",
        satisfaction_class="reflection_presence",
        authority_references=("fixture_curation_policy",),
    )
    approval = PortfolioProfileRequirement(
        portfolio_profile_id=revision.portfolio_profile_id,
        profile_revision=revision.profile_revision,
        requirement_id=APPROVAL_REQUIREMENT_ID,
        requirement_kind="approval",
        obligation="optional",
        title="Teacher curation review",
        statement="Teacher may review an exact curation target.",
        scope_kind="portfolio",
        satisfaction_class="curation_review",
        authority_references=("fixture_curation_policy",),
    )
    lifecycle = PortfolioProfileLifecycleEvent(
        profile_lifecycle_event_id="profile_event_curation_fixture",
        profile_revision=revision.reference,
        event_kind="activated",
        event_at=NOW,
        effective_at=NOW,
        actor=ACTOR,
        reason="Activate synthetic curation fixture Profile.",
        authority_reference="fixture_curation_policy",
    )
    binding = PortfolioProfileBinding(
        profile_binding_id=CURATION_BINDING_ID,
        portfolio_id=portfolio.portfolio_id,
        profile_revision=revision.reference,
        bound_at=NOW,
        bound_by=ACTOR,
        binding_reason="Synthetic issue 34 curation validation.",
    )
    return (
        portfolio,
        family,
        revision,
        *section_requirements,
        reflection,
        approval,
        lifecycle,
        binding,
    )


def _build_uncached_curation_fixture_workspace(base: Path) -> CurationFixtureWorkspace:
    setup = build_candidate_fixture_workspace(base)
    commit_record_batch(
        setup.workspace,
        _curation_profile_records(setup.portfolio_subject_id),
        expected_state_revision=setup.state_revision,
    )
    ids = DeterministicIds()
    candidate_ids: dict[str, str] = {}
    candidate_records: dict[str, PortfolioCandidate] = {}
    for module_id in (
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
        "vitrine_concord_fixture",
    ):
        state_revision = load_current_state(setup.workspace).state_revision
        result = discover_and_evaluate_candidates(
            setup.workspace,
            CandidateDiscoveryRequest(
                portfolio_id=CURATION_PORTFOLIO_ID,
                requesting_actor=ACTOR,
                requested_purpose="improvement",
                catalog_query=PublicationCatalogQuery(
                    module_id=module_id,
                    state="current",
                    limit=20,
                ),
                expected_state_revision=state_revision,
            ),
            producer_registry=build_development_fixture_producer_registry(),
            adapter_registry=build_development_fixture_adapter_registry(),
            authorization_gate=StaticAuthorizationGate("allowed"),
            clock=fixed_clock,
            id_factory=ids,
        )
        for item in result.evaluation_results:
            if item.candidate is not None:
                source_record_id = item.projected_source.producer_source.source_record_id
                candidate_ids[source_record_id] = item.candidate.candidate_id
                candidate_records[source_record_id] = item.candidate
    return CurationFixtureWorkspace(
        candidate_setup=setup,
        portfolio_id=CURATION_PORTFOLIO_ID,
        profile_binding_id=CURATION_BINDING_ID,
        candidate_ids_by_source=candidate_ids,
        candidate_records_by_source=candidate_records,
        ids=DeterministicIds(),
    )


_TEMPLATE_DIRECTORY: TemporaryDirectory[str] | None = None
_TEMPLATE_SETUP: CurationFixtureWorkspace | None = None


def _curation_fixture_template() -> CurationFixtureWorkspace:
    global _TEMPLATE_DIRECTORY, _TEMPLATE_SETUP
    if _TEMPLATE_SETUP is not None:
        return _TEMPLATE_SETUP
    directory = TemporaryDirectory(prefix="vitrine-curation-fixture-template-")
    try:
        setup = _build_uncached_curation_fixture_workspace(Path(directory.name))
    except Exception:
        directory.cleanup()
        raise
    _TEMPLATE_DIRECTORY = directory
    _TEMPLATE_SETUP = setup
    return setup


def build_curation_fixture_workspace(base: Path) -> CurationFixtureWorkspace:
    """Clone one deterministic prepared curation baseline into an isolated test root."""
    template = _curation_fixture_template()
    destination = base / "workspace"
    shutil.copytree(template.workspace, destination)
    manifest_paths = {
        module_id: destination / path.relative_to(template.workspace)
        for module_id, path in template.candidate_setup.manifest_paths.items()
    }
    candidate_setup = replace(
        template.candidate_setup,
        workspace=destination,
        manifest_paths=manifest_paths,
    )
    return CurationFixtureWorkspace(
        candidate_setup=candidate_setup,
        portfolio_id=template.portfolio_id,
        profile_binding_id=template.profile_binding_id,
        candidate_ids_by_source=dict(template.candidate_ids_by_source),
        candidate_records_by_source=dict(template.candidate_records_by_source),
        ids=DeterministicIds(),
    )


__all__ = [
    "ACTOR",
    "APPROVAL_REQUIREMENT_ID",
    "CURATION_BINDING_ID",
    "CURATION_PORTFOLIO_ID",
    "CurationFixtureWorkspace",
    "DeterministicIds",
    "NOW",
    "REFLECTION_REQUIREMENT_ID",
    "STUDENT_ACTOR",
    "StaticCurationAuthorityGate",
    "build_curation_fixture_workspace",
    "fixed_clock",
]
