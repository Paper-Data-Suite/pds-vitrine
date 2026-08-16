#!/usr/bin/env python3
"""Execute one compact synthetic chain through public workflow interfaces."""

# ruff: noqa: E402
from __future__ import annotations

import io
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.candidate_fixture_support import StaticAuthorizationGate
from scripts.curation_fixture_support import (
    DeterministicIds,
    StaticCurationAuthorityGate,
)
from scripts.improvement_portfolio_fixture_support import (
    LATER_SCHOOL_YEAR,
    REFLECTION_REQUIREMENT_ID,
    STUDENT,
    SUBJECT_ID,
    TEACHER,
    build_interface_workflow_prerequisites,
    fixed_clock,
)
from scripts.validate_snapshot_workflows import (
    EXPORT_CONFIGURATION_BYTES,
    REFLECTION_CONFIGURATION_BYTES,
    REFLECTION_RENDERER_CONTRACT,
    REFLECTION_RENDERER_ID,
    REFLECTION_RENDERER_VERSION,
    REFLECTION_TEMPLATE_BYTES,
    _digest,
    _FixtureAuthorityGate,
    _provider_registry,
    _ReflectionFixtureRenderer,
)
from vitrine.cli import main as cli_main
from vitrine.curation_services import create_reflection
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.menu import run_menu
from vitrine.models import (
    AudienceContext,
    CandidateEvaluation,
    CurationTargetRef,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SelectionProposal,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotSeries,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.conversion import value_to_json
from vitrine.profile_services import ProfileBindingContext, bind_portfolio_profile
from vitrine.snapshot_materialization import SnapshotRendererRegistry
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_context import (
    VitrineWorkflowDependencies,
    default_workflow_dependencies,
)


def _run(arguments: list[str], dependencies: VitrineWorkflowDependencies) -> str:
    output, error = io.StringIO(), io.StringIO()
    if cli_main(arguments, output=output, error=error, dependencies=dependencies) != 0:
        raise RuntimeError(f"interface command failed: {error.getvalue().strip()}")
    return output.getvalue()


def _records(workspace: Path) -> tuple[object, ...]:
    return load_current_records(workspace)


def _copied_entry(
    *,
    candidate: PortfolioCandidate,
    evaluation: CandidateEvaluation,
    selection: PortfolioSelection,
    placement: PortfolioPlacement,
    position: int,
) -> SnapshotEntryPlan:
    artifact = candidate.source_endpoint.source_artifact
    if artifact is None or artifact.source_locator is None:
        raise RuntimeError("interface Candidate lacks an exact source Artifact")
    source_id = candidate.source_endpoint.producer_source.source_record_id
    target = {
        "baseline_argument": "baseline/argument.txt",
        "revised_argument": "later/argument.txt",
        "revised_feedback": "later/student-feedback.txt",
    }[source_id]
    return SnapshotEntryPlan(
        entry_plan_id=f"entry-plan-interface-{position}",
        plan_position=position,
        section_id=placement.section_id,
        ordinal=position - 1 if placement.section_id == "later_work" else 1,
        semantic_role=source_id,
        materialization_kind="copied_source",
        content_class="student_work" if artifact.artifact_kind == "original_student_work" else "feedback",
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=candidate.source_endpoint.producer_source.projection_contract_version,
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target,
        media_type=artifact.media_type,
    )


def _plan_file(
    workspace: Path,
    *,
    reflection: PortfolioReflection,
    composition: WorkingPortfolioCompositionRevision,
    inventory: WorkingPortfolioCompositionInventory,
) -> tuple[Path, tuple[SnapshotEntryPlan, ...]]:
    records = _records(workspace)
    candidates = {item.candidate_id: item for item in records if isinstance(item, PortfolioCandidate)}
    evaluations = {item.candidate_evaluation_id: item for item in records if isinstance(item, CandidateEvaluation)}
    selections = {item.selection_id: item for item in records if isinstance(item, PortfolioSelection)}
    placement_by_id = {
        item.placement_id: item
        for item in records
        if isinstance(item, PortfolioPlacement)
    }
    placements = tuple(placement_by_id[item] for item in composition.placement_ids)
    copied = tuple(
        _copied_entry(
            candidate=candidates[selections[item.selection_id].candidate_id],
            evaluation=evaluations[candidates[selections[item.selection_id].candidate_id].candidate_evaluation_id],
            selection=selections[item.selection_id],
            placement=item,
            position=index,
        )
        for index, item in enumerate(placements, 1)
    )
    reflection_entry = SnapshotEntryPlan(
        entry_plan_id="entry-plan-interface-reflection",
        plan_position=len(copied) + 1,
        section_id="reflection",
        ordinal=1,
        semantic_role="student_reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="reflection/student-comparison.md",
        media_type="text/markdown",
        renderer_id=REFLECTION_RENDERER_ID,
        renderer_version=REFLECTION_RENDERER_VERSION,
        renderer_contract_version=REFLECTION_RENDERER_CONTRACT,
        renderer_configuration_digest=_digest(REFLECTION_CONFIGURATION_BYTES),
        renderer_template_digest=_digest(REFLECTION_TEMPLATE_BYTES),
        input_references=(
            SnapshotInputReference(record_type="portfolio_reflection", record_id=reflection.reflection_id, record_revision=reflection.reflection_revision),
            SnapshotInputReference(record_type="working_portfolio_composition_revision", record_id=composition.portfolio_id, record_revision=composition.composition_revision),
        ),
    )
    entries = (*copied, reflection_entry)
    export = SnapshotExportPlan(
        export_plan_id="export-plan-interface-directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=_digest(EXPORT_CONFIGURATION_BYTES),
    )
    payload = {
        "entry_plans": [value_to_json(item) for item in entries],
        "export_plans": [value_to_json(export)],
        "acknowledged_obligation_codes": list(inventory.unresolved_obligation_codes),
    }
    path = workspace / "interface-snapshot-plan.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path, entries


def validate() -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-interface-workflow-") as raw:
        prerequisites = build_interface_workflow_prerequisites(Path(raw))
        workspace = prerequisites.workspace
        workspace_text = str(workspace)
        dependencies = replace(
            default_workflow_dependencies(),
            producer_registry=build_development_fixture_producer_registry(),
            adapter_registry=build_development_fixture_adapter_registry(),
            source_read_authorization_gate=StaticAuthorizationGate("allowed"),
            curation_authority_gate=StaticCurationAuthorityGate(),
            development_fixture_mode=True,
        )
        created = _run([
            "portfolio", "create", "--subject-id", SUBJECT_ID,
            "--title", "Interface acceptance Portfolio", "--actor-id", TEACHER.actor_id,
            "--workspace-root", workspace_text,
        ], dependencies)
        if "Created Portfolio:" not in created:
            raise RuntimeError("Portfolio create interface did not execute")
        portfolio = next(item for item in _records(workspace) if isinstance(item, Portfolio))
        bind_portfolio_profile(
            workspace, portfolio.portfolio_id, prerequisites.profile_revision.reference,
            actor=TEACHER, binding_reason="Execute interface acceptance chain.",
            context=ProfileBindingContext(school_year=LATER_SCHOOL_YEAR),
            expected_state_revision=load_current_state(workspace).state_revision,
            clock=fixed_clock,
        )
        _run([
            "candidate", "discover", portfolio.portfolio_id, "--purpose", "improvement",
            "--module-id", "vitrine_quillan_fixture", "--actor-id", TEACHER.actor_id,
            "--workspace-root", workspace_text,
        ], dependencies)
        candidates = tuple(item for item in _records(workspace) if isinstance(item, PortfolioCandidate))
        if len(candidates) != 3:
            raise RuntimeError("interface discovery did not create the exact Candidates")
        _run(["candidate", "list", portfolio.portfolio_id, "--workspace-root", workspace_text], dependencies)
        _run(["candidate", "show", candidates[0].candidate_id, "--workspace-root", workspace_text], dependencies)
        by_source = {item.source_endpoint.producer_source.source_record_id: item for item in candidates}
        first = by_source["baseline_argument"]
        _run([
            "selection", "propose", portfolio.portfolio_id, first.candidate_id,
            "--section-id", "baseline", "--actor-id", TEACHER.actor_id,
            "--workspace-root", workspace_text,
        ], dependencies)
        proposal = next(
            item
            for item in _records(workspace)
            if isinstance(item, SelectionProposal)
        )
        _run([
            "selection", "decide", portfolio.portfolio_id, proposal.selection_proposal_id,
            "--decision", "accepted", "--actor-id", TEACHER.actor_id,
            "--workspace-root", workspace_text,
        ], dependencies)
        for source_id in ("revised_argument", "revised_feedback"):
            _run([
                "selection", "add", portfolio.portfolio_id, by_source[source_id].candidate_id,
                "--section-id", "later_work", "--actor-id", TEACHER.actor_id,
                "--workspace-root", workspace_text,
            ], dependencies)
        selections = tuple(item for item in _records(workspace) if isinstance(item, PortfolioSelection))
        for selection in selections:
            candidate = next(item for item in candidates if item.candidate_id == selection.candidate_id)
            section = "baseline" if candidate is first else "later_work"
            _run([
                "arrangement", "place", portfolio.portfolio_id, selection.selection_id,
                "--section-id", section, "--actor-id", TEACHER.actor_id,
                "--workspace-root", workspace_text,
            ], dependencies)
        _run(["arrangement", "show", portfolio.portfolio_id, "--section-id", "later_work", "--workspace-root", workspace_text], dependencies)
        later_placements = tuple(item for item in _records(workspace) if isinstance(item, PortfolioPlacement) and item.section_id == "later_work")
        _run([
            "arrangement", "reorder", portfolio.portfolio_id, "--section-id", "later_work",
            *(item.placement_id for item in reversed(later_placements)),
            "--expected-arrangement-pointer-revision", str(len(later_placements)),
            "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text,
        ], dependencies)
        reflected = create_reflection(
            workspace, portfolio_id=portfolio.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="interface-comparison", prompt_version="1",
            prompt_snapshot="Compare the baseline and later work.", author=STUDENT,
            target_scope="comparison_set",
            target_references=(
                CurationTargetRef(
                    target_kind="selection",
                    target_id=next(
                        item.selection_id
                        for item in selections
                        if item.candidate_id == by_source["baseline_argument"].candidate_id
                    ),
                    semantic_role="baseline",
                ),
                CurationTargetRef(
                    target_kind="selection",
                    target_id=next(
                        item.selection_id
                        for item in selections
                        if item.candidate_id == by_source["revised_argument"].candidate_id
                    ),
                    semantic_role="later",
                ),
            ),
            content="I revised my claim and connected evidence to my reasoning.",
            expected_state_revision=load_current_state(workspace).state_revision,
            authority_gate=StaticCurationAuthorityGate(), clock=fixed_clock,
            id_factory=DeterministicIds(),
        )
        reflection = next(item for item in reflected.records if isinstance(item, PortfolioReflection))
        _run(["composition", "build", portfolio.portfolio_id, "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], dependencies)
        composition = next(item for item in _records(workspace) if isinstance(item, WorkingPortfolioCompositionRevision))
        inventory = next(item for item in _records(workspace) if isinstance(item, WorkingPortfolioCompositionInventory))
        _run(["composition", "show", portfolio.portfolio_id, "--workspace-root", workspace_text], dependencies)
        audience_rule = prerequisites.profile_revision.audience_rules[0]
        _run(["audience", "create", portfolio.portfolio_id, "--audience-rule-id", audience_rule.audience_rule_id, "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], dependencies)
        audience = next(item for item in _records(workspace) if isinstance(item, AudienceContext))
        _run(["audience", "show", audience.audience_context_id, "--workspace-root", workspace_text], dependencies)
        _run(["snapshot", "series", "create", portfolio.portfolio_id, "--audience-context-id", audience.audience_context_id, "--purpose", "interface_acceptance", "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], dependencies)
        series = next(item for item in _records(workspace) if isinstance(item, SnapshotSeries))
        _run(["snapshot", "request", series.snapshot_series_id, "--composition-revision", str(composition.composition_revision), "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], dependencies)
        request = next(item for item in _records(workspace) if isinstance(item, SnapshotBuildRequest))
        plan_path, entries = _plan_file(workspace, reflection=reflection, composition=composition, inventory=inventory)
        _run(["snapshot", "plan", request.snapshot_build_request_id, "--from-plan-json", str(plan_path), "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], dependencies)
        plan = next(item for item in _records(workspace) if isinstance(item, SnapshotBuildPlan))
        _run(["snapshot", "plan-show", plan.snapshot_build_plan_id, "--workspace-root", workspace_text], dependencies)
        build_dependencies = replace(
            dependencies,
            snapshot_build_authority_gate=_FixtureAuthorityGate(),
            snapshot_source_providers=_provider_registry(entries, prerequisites.source_root),
            snapshot_renderers=SnapshotRendererRegistry((_ReflectionFixtureRenderer(reflection=reflection),)),
        )
        built = _run(["snapshot", "build", plan.snapshot_build_plan_id, "--actor-id", TEACHER.actor_id, "--workspace-root", workspace_text], build_dependencies)
        if "Sealed Edition:" not in built:
            raise RuntimeError("Snapshot build did not seal an Edition")
        verified = _run(["snapshot", "verify", series.snapshot_series_id, "--edition", "1", "--workspace-root", workspace_text], build_dependencies)
        if "Edition verification: verified" not in verified:
            raise RuntimeError("exact Edition verification did not execute")
        menu_output = io.StringIO()
        if run_menu(input_fn=lambda _prompt: "Q", output=menu_output, clear_fn=lambda: None) != 0 or "Portfolios" not in menu_output.getvalue():
            raise RuntimeError("teacher menu did not unwind from its Portfolio screen")
        ordinary = default_workflow_dependencies()
        if ordinary.adapter_registry.adapters or ordinary.producer_registry.profiles:
            raise RuntimeError("ordinary runtime silently enabled development fixtures")


def main() -> int:
    validate()
    print("PASS interface workflow validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
