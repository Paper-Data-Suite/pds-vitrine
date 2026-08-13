"""Development-only prepared fixture support for issue #35 Snapshot workflows."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.candidate_fixture_support import DeterministicIds
from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    CurationFixtureWorkspace,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import (
    create_reflection,
    create_working_composition,
    place_selection,
    select_candidate_directly,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    AudienceContext,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSelection,
    VitrineRecord,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)


@dataclass(frozen=True, slots=True)
class SnapshotFixtureWorkspace:
    curation_setup: CurationFixtureWorkspace
    composition: WorkingPortfolioCompositionRevision
    inventory: WorkingPortfolioCompositionInventory
    audience: AudienceContext
    baseline_selection: PortfolioSelection
    later_selection: PortfolioSelection
    baseline_placement: PortfolioPlacement
    later_placement: PortfolioPlacement

    @property
    def workspace(self) -> Path:
        return self.curation_setup.workspace

    @property
    def portfolio_id(self) -> str:
        return self.curation_setup.portfolio_id

    @property
    def profile_binding_id(self) -> str:
        return self.curation_setup.profile_binding_id

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision

    @property
    def ids(self) -> DeterministicIds:
        return self.curation_setup.ids

    def candidate(self, source_record_id: str) -> PortfolioCandidate:
        return self.curation_setup.candidate(source_record_id)


@dataclass(frozen=True, slots=True)
class RepresentativeSnapshotFixtureWorkspace:
    """Prepared issue #35 fixture with work, feedback, assessment, and Reflection."""

    curation_setup: CurationFixtureWorkspace
    composition: WorkingPortfolioCompositionRevision
    inventory: WorkingPortfolioCompositionInventory
    audience: AudienceContext
    baseline_selection: PortfolioSelection
    later_selection: PortfolioSelection
    feedback_selection: PortfolioSelection
    scoreform_selection: PortfolioSelection
    baseline_placement: PortfolioPlacement
    later_placement: PortfolioPlacement
    feedback_placement: PortfolioPlacement
    scoreform_placement: PortfolioPlacement
    reflection: PortfolioReflection

    @property
    def workspace(self) -> Path:
        return self.curation_setup.workspace

    @property
    def portfolio_id(self) -> str:
        return self.curation_setup.portfolio_id

    @property
    def profile_binding_id(self) -> str:
        return self.curation_setup.profile_binding_id

    @property
    def state_revision(self) -> int:
        return load_current_state(self.workspace).state_revision

    @property
    def ids(self) -> DeterministicIds:
        return self.curation_setup.ids

    def candidate(self, source_record_id: str) -> PortfolioCandidate:
        return self.curation_setup.candidate(source_record_id)


def _records(setup: CurationFixtureWorkspace) -> tuple[VitrineRecord, ...]:
    return load_current_records(setup.workspace)


def _direct_select(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
    section_id: str,
) -> PortfolioSelection:
    result = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioSelection))


def _place(
    setup: CurationFixtureWorkspace,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    state = project_curation_state(_records(setup))
    heads = state.arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, section_id
    )
    pointer = heads[0].pointer_revision if len(heads) == 1 else None
    result = place_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_arrangement_pointer_revision=pointer,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def _build_uncached_snapshot_fixture_workspace(base: Path) -> SnapshotFixtureWorkspace:
    setup = build_curation_fixture_workspace(base)
    baseline_selection = _direct_select(
        setup, setup.candidate("evidence_selected"), "baseline"
    )
    later_selection = _direct_select(
        setup, setup.candidate("evidence_approved"), "later_work"
    )
    baseline_placement = _place(setup, baseline_selection, "baseline")
    later_placement = _place(setup, later_selection, "later_work")
    composition_result = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze exact state for Snapshot planning.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    composition = next(
        item
        for item in composition_result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in composition_result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    profile = next(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == composition.profile_revision
    )
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id="audience_snapshot_fixture",
        portfolio_id=composition.portfolio_id,
        portfolio_subject_id=composition.portfolio_subject_id,
        profile_binding_id=composition.profile_binding_id,
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
        created_at=fixed_clock(),
        created_by=ACTOR,
    )
    commit_record_batch(
        setup.workspace,
        (audience,),
        expected_state_revision=setup.state_revision,
    )
    return SnapshotFixtureWorkspace(
        curation_setup=setup,
        composition=composition,
        inventory=inventory,
        audience=audience,
        baseline_selection=baseline_selection,
        later_selection=later_selection,
        baseline_placement=baseline_placement,
        later_placement=later_placement,
    )


def _audience_for_composition(
    setup: CurationFixtureWorkspace,
    composition: WorkingPortfolioCompositionRevision,
    *,
    audience_context_id: str,
) -> AudienceContext:
    profile = next(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == composition.profile_revision
    )
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id=audience_context_id,
        portfolio_id=composition.portfolio_id,
        portfolio_subject_id=composition.portfolio_subject_id,
        profile_binding_id=composition.profile_binding_id,
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
        created_at=fixed_clock(),
        created_by=ACTOR,
    )
    commit_record_batch(
        setup.workspace,
        (audience,),
        expected_state_revision=setup.state_revision,
    )
    return audience


def _build_uncached_representative_snapshot_fixture_workspace(
    base: Path,
) -> RepresentativeSnapshotFixtureWorkspace:
    setup = build_curation_fixture_workspace(base)
    baseline_selection = _direct_select(
        setup, setup.candidate("evidence_selected"), "baseline"
    )
    later_selection = _direct_select(
        setup, setup.candidate("evidence_approved"), "later_work"
    )
    feedback_selection = _direct_select(
        setup, setup.candidate("feedback_student"), "feedback"
    )
    scoreform_selection = _direct_select(
        setup, setup.candidate("argument_assessment_attempt_1"), "assessment"
    )
    baseline_placement = _place(setup, baseline_selection, "baseline")
    later_placement = _place(setup, later_selection, "later_work")
    feedback_placement = _place(setup, feedback_selection, "feedback")
    scoreform_placement = _place(setup, scoreform_selection, "assessment")
    reflection_result = create_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="compare_growth_prompt",
        prompt_version="1",
        prompt_snapshot="Compare these two works and explain what changed.",
        author=STUDENT_ACTOR,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=baseline_selection.selection_id,
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=later_selection.selection_id,
                semantic_role="later",
            ),
        ),
        content="I changed my use of textual evidence between these drafts.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item
        for item in reflection_result.records
        if isinstance(item, PortfolioReflection)
    )
    composition_result = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze representative exact state for Snapshot acceptance.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    composition = next(
        item
        for item in composition_result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in composition_result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    if not any(
        item.record_kind == "reflection"
        and item.record_id == reflection.reflection_id
        and item.revision == reflection.reflection_revision
        for item in inventory.included_curation_revisions
    ):
        raise RuntimeError("representative Composition did not freeze exact Reflection.")
    audience = _audience_for_composition(
        setup,
        composition,
        audience_context_id="audience_snapshot_representative",
    )
    return RepresentativeSnapshotFixtureWorkspace(
        curation_setup=setup,
        composition=composition,
        inventory=inventory,
        audience=audience,
        baseline_selection=baseline_selection,
        later_selection=later_selection,
        feedback_selection=feedback_selection,
        scoreform_selection=scoreform_selection,
        baseline_placement=baseline_placement,
        later_placement=later_placement,
        feedback_placement=feedback_placement,
        scoreform_placement=scoreform_placement,
        reflection=reflection,
    )


_REPRESENTATIVE_TEMPLATE_DIRECTORY: TemporaryDirectory[str] | None = None
_REPRESENTATIVE_TEMPLATE_SETUP: RepresentativeSnapshotFixtureWorkspace | None = None


def _representative_snapshot_fixture_template() -> RepresentativeSnapshotFixtureWorkspace:
    global _REPRESENTATIVE_TEMPLATE_DIRECTORY, _REPRESENTATIVE_TEMPLATE_SETUP
    if _REPRESENTATIVE_TEMPLATE_SETUP is not None:
        return _REPRESENTATIVE_TEMPLATE_SETUP
    directory = TemporaryDirectory(
        prefix="vitrine-representative-snapshot-fixture-template-"
    )
    try:
        setup = _build_uncached_representative_snapshot_fixture_workspace(
            Path(directory.name)
        )
    except Exception:
        directory.cleanup()
        raise
    _REPRESENTATIVE_TEMPLATE_DIRECTORY = directory
    _REPRESENTATIVE_TEMPLATE_SETUP = setup
    return setup


def build_representative_snapshot_fixture_workspace(
    base: Path,
) -> RepresentativeSnapshotFixtureWorkspace:
    """Clone the complete deterministic issue #35 representative fixture."""

    template = _representative_snapshot_fixture_template()
    destination = base / "workspace"
    shutil.copytree(template.workspace, destination)
    candidate_template = template.curation_setup.candidate_setup
    manifest_paths = {
        module_id: destination / path.relative_to(template.workspace)
        for module_id, path in candidate_template.manifest_paths.items()
    }
    candidate_setup = replace(
        candidate_template,
        workspace=destination,
        manifest_paths=manifest_paths,
    )
    curation_setup = CurationFixtureWorkspace(
        candidate_setup=candidate_setup,
        portfolio_id=template.curation_setup.portfolio_id,
        profile_binding_id=template.curation_setup.profile_binding_id,
        candidate_ids_by_source=dict(
            template.curation_setup.candidate_ids_by_source
        ),
        candidate_records_by_source=dict(
            template.curation_setup.candidate_records_by_source
        ),
        ids=DeterministicIds(),
    )
    return RepresentativeSnapshotFixtureWorkspace(
        curation_setup=curation_setup,
        composition=template.composition,
        inventory=template.inventory,
        audience=template.audience,
        baseline_selection=template.baseline_selection,
        later_selection=template.later_selection,
        feedback_selection=template.feedback_selection,
        scoreform_selection=template.scoreform_selection,
        baseline_placement=template.baseline_placement,
        later_placement=template.later_placement,
        feedback_placement=template.feedback_placement,
        scoreform_placement=template.scoreform_placement,
        reflection=template.reflection,
    )


_TEMPLATE_DIRECTORY: TemporaryDirectory[str] | None = None
_TEMPLATE_SETUP: SnapshotFixtureWorkspace | None = None


def _snapshot_fixture_template() -> SnapshotFixtureWorkspace:
    global _TEMPLATE_DIRECTORY, _TEMPLATE_SETUP
    if _TEMPLATE_SETUP is not None:
        return _TEMPLATE_SETUP
    directory = TemporaryDirectory(prefix="vitrine-snapshot-fixture-template-")
    try:
        setup = _build_uncached_snapshot_fixture_workspace(Path(directory.name))
    except Exception:
        directory.cleanup()
        raise
    _TEMPLATE_DIRECTORY = directory
    _TEMPLATE_SETUP = setup
    return setup


def build_snapshot_fixture_workspace(base: Path) -> SnapshotFixtureWorkspace:
    """Clone one deterministic Snapshot-ready baseline into an isolated test root."""
    template = _snapshot_fixture_template()
    destination = base / "workspace"
    shutil.copytree(template.workspace, destination)

    candidate_template = template.curation_setup.candidate_setup
    manifest_paths = {
        module_id: destination / path.relative_to(template.workspace)
        for module_id, path in candidate_template.manifest_paths.items()
    }
    candidate_setup = replace(
        candidate_template,
        workspace=destination,
        manifest_paths=manifest_paths,
    )
    ids = DeterministicIds()
    curation_setup = CurationFixtureWorkspace(
        candidate_setup=candidate_setup,
        portfolio_id=template.curation_setup.portfolio_id,
        profile_binding_id=template.curation_setup.profile_binding_id,
        candidate_ids_by_source=dict(
            template.curation_setup.candidate_ids_by_source
        ),
        candidate_records_by_source=dict(
            template.curation_setup.candidate_records_by_source
        ),
        ids=ids,
    )
    return SnapshotFixtureWorkspace(
        curation_setup=curation_setup,
        composition=template.composition,
        inventory=template.inventory,
        audience=template.audience,
        baseline_selection=template.baseline_selection,
        later_selection=template.later_selection,
        baseline_placement=template.baseline_placement,
        later_placement=template.later_placement,
    )


__all__ = [
    "RepresentativeSnapshotFixtureWorkspace",
    "SnapshotFixtureWorkspace",
    "build_representative_snapshot_fixture_workspace",
    "build_snapshot_fixture_workspace",
]
