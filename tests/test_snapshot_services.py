from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.curation_fixture_support import ACTOR, STUDENT_ACTOR, fixed_clock
from scripts.snapshot_fixture_support import build_snapshot_fixture_workspace
from vitrine.models import (
    DigestReference,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotEntry,
    SnapshotEntryPlan,
    SnapshotExportArtifact,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotManifest,
    SnapshotMaterializationProvenance,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
    SnapshotSeries,
    WorkingPortfolioCompositionRevision,
)
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    inspect_snapshot_series_lock,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    abandon_snapshot_build_attempt_after_recovery,
    advance_snapshot_current_pointer,
    create_snapshot_directory_export,
    inspect_snapshot_attempt_recovery,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotRendererDescriptor,
    SnapshotRendererRegistry,
    SnapshotRenderRequest,
    SnapshotRenderResult,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)
from vitrine.snapshot_sealing import snapshot_digest
from vitrine.snapshot_services import (
    SnapshotWorkflowError,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import load_current_records, load_current_state


def _records(setup: object):
    return load_current_records(getattr(setup, "workspace"))


def _prepare(tmp_path: Path):
    prepared = build_snapshot_fixture_workspace(tmp_path)
    return (
        prepared,
        prepared.composition,
        prepared.inventory,
        prepared.audience,
        prepared.baseline_selection,
        prepared.later_selection,
        prepared.baseline_placement,
        prepared.later_placement,
    )


def _source_entry(
    *,
    setup: object,
    selection: PortfolioSelection,
    placement: PortfolioPlacement,
    position: int,
) -> SnapshotEntryPlan:
    candidate = next(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == selection.candidate_id
    )
    artifact = candidate.source_endpoint.source_artifact
    assert artifact is not None and artifact.source_locator is not None
    content_class = {
        "original_student_work": "student_work",
        "rendered_feedback": "feedback",
        "assessment_summary": "assessment_summary",
        "collaborative_artifact": "student_work",
    }[artifact.artifact_kind]
    return SnapshotEntryPlan(
        entry_plan_id=f"entry_plan_{placement.section_id}",
        plan_position=position,
        section_id=placement.section_id,
        ordinal=1,
        semantic_role="selected_work",
        materialization_kind="copied_source",
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=f"{placement.section_id}/work-{position}.txt",
        media_type=artifact.media_type,
    )


def _series_and_request(setup: object, composition: WorkingPortfolioCompositionRevision):
    series_result = create_snapshot_series(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        audience_context_id="audience_snapshot_fixture",
        snapshot_purpose="improvement",
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    series = next(item for item in series_result.records if isinstance(item, SnapshotSeries))
    request_result = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=composition.composition_revision,
        requested_by=ACTOR,
        idempotency_key="snapshot-request-idempotency",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    request = next(
        item for item in request_result.records if isinstance(item, SnapshotBuildRequest)
    )
    return series, request


def test_request_plan_attempt_lifecycle_is_persisted_and_replay_safe(tmp_path: Path) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    series, request = _series_and_request(setup, composition)

    replay = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=composition.composition_revision,
        requested_by=ACTOR,
        idempotency_key="snapshot-request-idempotency",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert replay.disposition == "existing"
    assert replay.records == (request,)
    assert request.curation_review_decision_ids == inventory.applicable_review_decision_ids

    entries = (
        _source_entry(
            setup=setup,
            selection=baseline_selection,
            placement=baseline_placement,
            position=1,
        ),
        _source_entry(
            setup=setup,
            selection=later_selection,
            placement=later_placement,
            position=2,
        ),
    )
    export = SnapshotExportPlan(
        export_plan_id="export_plan_directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="1" * 64),
    )
    planned = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
    assert plan.composition_revision == composition.composition_revision
    assert tuple(item.placement_id for item in plan.entry_plans) == (
        baseline_placement.placement_id,
        later_placement.placement_id,
    )

    replay_plan = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert replay_plan.disposition == "existing"
    assert replay_plan.records == (plan,)

    started = start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert started.attempt.attempt_number == 1
    assert started.staging_root.is_dir()
    assert started.attempt in load_current_records(setup.workspace)
    with pytest.raises(SnapshotWorkflowError) as error:
        start_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
            started_by=ACTOR,
            expected_state_revision=load_current_state(setup.workspace).state_revision,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert error.value.code == "snapshot.attempt_conflict"


def test_request_idempotency_key_rejects_changed_intent(tmp_path: Path) -> None:
    setup, composition, *_ = _prepare(tmp_path)
    series, _ = _series_and_request(setup, composition)
    with pytest.raises(SnapshotWorkflowError) as error:
        request_snapshot_build(
            setup.workspace,
            snapshot_series_id=series.snapshot_series_id,
            composition_revision=composition.composition_revision,
            requested_by=STUDENT_ACTOR,
            idempotency_key="snapshot-request-idempotency",
            expected_state_revision=setup.state_revision,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert error.value.code == "snapshot.request_conflict"


def test_plan_rejects_candidate_retargeting_and_arrangement_reordering(tmp_path: Path) -> None:
    (
        setup,
        composition,
        _,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    _, request = _series_and_request(setup, composition)
    baseline_entry = _source_entry(
        setup=setup,
        selection=baseline_selection,
        placement=baseline_placement,
        position=1,
    )
    later_entry = _source_entry(
        setup=setup,
        selection=later_selection,
        placement=later_placement,
        position=2,
    )
    wrong_candidate = setup.candidate("evidence_approved")
    retargeted = replace(
        baseline_entry,
        candidate_id=wrong_candidate.candidate_id,
        candidate_evaluation_id=wrong_candidate.candidate_evaluation_id,
    )
    export = SnapshotExportPlan(
        export_plan_id="export_plan_directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=(retargeted.entry_plan_id, later_entry.entry_plan_id),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="2" * 64),
    )
    with pytest.raises(SnapshotWorkflowError) as error:
        plan_snapshot_build(
            setup.workspace,
            snapshot_build_request_id=request.snapshot_build_request_id,
            entry_plans=(retargeted, later_entry),
            export_plans=(export,),
            planned_by=ACTOR,
            expected_state_revision=setup.state_revision,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert error.value.code == "snapshot.plan_source_mismatch"

    later_first = replace(later_entry, plan_position=1)
    baseline_second = replace(baseline_entry, plan_position=2)
    reordered_export = replace(
        export,
        included_entry_plan_ids=(later_first.entry_plan_id, baseline_second.entry_plan_id),
    )
    with pytest.raises(SnapshotWorkflowError) as error:
        plan_snapshot_build(
            setup.workspace,
            snapshot_build_request_id=request.snapshot_build_request_id,
            entry_plans=(later_first, baseline_second),
            export_plans=(reordered_export,),
            planned_by=ACTOR,
            expected_state_revision=setup.state_revision,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert error.value.code == "snapshot.plan_order_invalid"


def test_plan_requires_explicit_accounting_for_every_composition_placement(tmp_path: Path) -> None:
    (
        setup,
        composition,
        _,
        _,
        baseline_selection,
        _,
        baseline_placement,
        _,
    ) = _prepare(tmp_path)
    _, request = _series_and_request(setup, composition)
    baseline_entry = _source_entry(
        setup=setup,
        selection=baseline_selection,
        placement=baseline_placement,
        position=1,
    )
    export = SnapshotExportPlan(
        export_plan_id="export_plan_directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=(baseline_entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="3" * 64),
    )
    with pytest.raises(SnapshotWorkflowError) as error:
        plan_snapshot_build(
            setup.workspace,
            snapshot_build_request_id=request.snapshot_build_request_id,
            entry_plans=(baseline_entry,),
            export_plans=(export,),
            planned_by=ACTOR,
            expected_state_revision=setup.state_revision,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert error.value.code == "snapshot.plan_inventory_incomplete"


def test_attempt_record_is_persisted_before_staging_conflict_is_reported(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    _, request = _series_and_request(setup, composition)
    entries = (
        _source_entry(
            setup=setup,
            selection=baseline_selection,
            placement=baseline_placement,
            position=1,
        ),
        _source_entry(
            setup=setup,
            selection=later_selection,
            placement=later_placement,
            position=2,
        ),
    )
    export = SnapshotExportPlan(
        export_plan_id="export_plan_directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="4" * 64),
    )
    planned = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
    predicted_attempt_id = setup.ids("snapshot_attempt")
    # Reproduce the deterministic fixture factory's next value by using a dedicated factory
    # for the actual service call rather than mutating canonical state through guessing.
    class FixedId:
        def __call__(self, prefix: str) -> str:
            if prefix == "snapshot_attempt":
                return predicted_attempt_id
            if prefix == "snapshot_attempt_result":
                return "snapshot_attempt_result_staging_conflict"
            raise AssertionError(prefix)

    staging = setup.workspace / "vitrine" / "snapshots" / "staging" / predicted_attempt_id
    staging.mkdir(parents=True)
    with pytest.raises(SnapshotWorkflowError) as error:
        start_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_plan_id=plan.snapshot_build_plan_id,
            started_by=ACTOR,
            expected_state_revision=setup.state_revision,
            clock=fixed_clock,
            id_factory=FixedId(),
        )
    assert error.value.code == "snapshot.staging_conflict"
    persisted = load_current_records(setup.workspace)
    attempts = tuple(
        item
        for item in persisted
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_attempt_id == predicted_attempt_id
    )
    results = tuple(
        item
        for item in persisted
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == predicted_attempt_id
    )
    assert len(attempts) == 1
    assert len(results) == 1
    assert results[0].terminal_outcome == "failed"
    assert all(
        outcome.disposition == "failed_blocking"
        for outcome in results[0].entry_outcomes
    )



class _ExecutionAuthority:
    def __init__(self, outcome: str = "allowed") -> None:
        self.outcome = outcome
        self.calls = 0

    def authorize(self, request: object) -> SnapshotBuildAuthorityDecision:
        self.calls += 1
        return SnapshotBuildAuthorityDecision(
            outcome=self.outcome,
            authority_reference=(
                "snapshot_execution_fixture_authority"
                if self.outcome == "allowed"
                else None
            ),
        )


class _ExecutionSourceProvider:
    def __init__(self, root: Path, entry: SnapshotEntryPlan) -> None:
        assert entry.producer_module_id is not None
        assert entry.projection_kind is not None
        assert entry.projection_contract_version is not None
        assert entry.source_artifact is not None
        self.root = root
        self.resolve_calls = 0
        self.descriptor = SnapshotSourceProviderDescriptor(
            provider_id="snapshot_execution_fixture_provider",
            provider_version="1",
            producer_module_id=entry.producer_module_id,
            projection_kind=entry.projection_kind,
            projection_contract_version=entry.projection_contract_version,
            artifact_kind=entry.source_artifact.artifact_kind,
            representation_kind=entry.source_artifact.representation_kind,
        )

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotSourceResult:
        self.resolve_calls += 1
        artifact = request.entry_plan.source_artifact
        assert artifact is not None
        assert artifact.source_locator is not None
        assert request.entry_plan.source_publication_id is not None
        return SnapshotSourceResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=request.entry_plan.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            source_root=self.root,
            source_relative_path=artifact.source_locator,
        )

    def confirm_stability(
        self, request: SnapshotSourceRequest, result: SnapshotSourceResult
    ) -> bool:
        return True


class _ExecutionRenderer:
    descriptor = SnapshotRendererDescriptor(
        renderer_id="snapshot_execution_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_execution_renderer_v1",
    )

    def __init__(self, configuration_digest: DigestReference) -> None:
        self.configuration_digest = configuration_digest
        self.calls = 0

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        self.calls += 1
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=b"# Snapshot Index\n\nExact frozen composition.\n",
            media_type="text/markdown",
            configuration_digest=self.configuration_digest,
        )


def _execution_plan(
    setup: object,
    composition: WorkingPortfolioCompositionRevision,
    inventory: object,
    baseline_selection: PortfolioSelection,
    later_selection: PortfolioSelection,
    baseline_placement: PortfolioPlacement,
    later_placement: PortfolioPlacement,
    *,
    include_generated: bool,
    permitted_first_omission: str | None = None,
):
    _, request = _series_and_request(setup, composition)
    entries = [
        replace(
            _source_entry(
                setup=setup,
                selection=baseline_selection,
                placement=baseline_placement,
                position=1,
            ),
            permitted_omission_reason=permitted_first_omission,
        ),
        _source_entry(
            setup=setup,
            selection=later_selection,
            placement=later_placement,
            position=2,
        ),
    ]
    render_config = DigestReference(value="9" * 64)
    if include_generated:
        entries.append(
            SnapshotEntryPlan(
                entry_plan_id="entry_plan_generated_index",
                plan_position=3,
                section_id="baseline",
                ordinal=2,
                semantic_role="index",
                materialization_kind="generated_vitrine",
                content_class="student_work",
                target_relative_path="index.md",
                media_type="text/markdown",
                renderer_id="snapshot_execution_renderer",
                renderer_version="1",
                renderer_contract_version="snapshot_execution_renderer_v1",
                renderer_configuration_digest=render_config,
                input_references=(
                    SnapshotInputReference(
                        record_type="working_portfolio_composition_revision",
                        record_id=composition.portfolio_id,
                        record_revision=composition.composition_revision,
                    ),
                ),
            )
        )
    entry_tuple = tuple(entries)
    export = SnapshotExportPlan(
        export_plan_id="export_plan_execution",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entry_tuple),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="8" * 64),
    )
    planned = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entry_tuple,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=getattr(
            inventory, "unresolved_obligation_codes"
        ),
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
    started = start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return plan, started.attempt, render_config


def _source_registry_for_plan(
    tmp_path: Path, plan: SnapshotBuildPlan
) -> tuple[SnapshotSourceProviderRegistry, _ExecutionSourceProvider]:
    copied = next(
        item for item in plan.entry_plans if item.materialization_kind == "copied_source"
    )
    root = (tmp_path / "execution_sources").resolve()
    for entry in plan.entry_plans:
        if entry.materialization_kind != "copied_source":
            continue
        artifact = entry.source_artifact
        assert artifact is not None and artifact.source_locator is not None
        target = root.joinpath(*artifact.source_locator.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            f"fixture bytes for {artifact.artifact_id}\n".encode("utf-8")
        )
        target.write_bytes(payload)
        # Candidate fixtures intentionally do not ship producer Artifact bytes or
        # digest claims yet, so the exact plan may legitimately carry no claim.
        assert artifact.source_digest is None
    provider = _ExecutionSourceProvider(root, copied)
    return SnapshotSourceProviderRegistry((provider,)), provider


def test_attempt_execution_authorizes_once_and_prepares_copied_and_generated_bytes(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, render_config = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=True,
    )
    providers, provider = _source_registry_for_plan(tmp_path, plan)
    renderer = _ExecutionRenderer(render_config)
    authority = _ExecutionAuthority()

    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=authority,
        source_providers=providers,
        renderers=SnapshotRendererRegistry((renderer,)),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert authority.calls == 1
    assert provider.resolve_calls == 2
    assert renderer.calls == 1
    assert tuple(item.disposition for item in executed.entries) == (
        "prepared_bytes",
        "prepared_bytes",
        "prepared_bytes",
    )
    assert not any(
        isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
        for item in load_current_records(setup.workspace)
    )
    assert (executed.staging_root / "index.md").exists() is False
    assert (executed.staging_root / "content" / "index.md").read_bytes().startswith(
        b"# Snapshot Index"
    )


def test_denied_attempt_authority_persists_failure_before_source_access(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, _ = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=False,
    )
    providers, provider = _source_registry_for_plan(tmp_path, plan)
    authority = _ExecutionAuthority("denied")

    with pytest.raises(SnapshotWorkflowError) as captured:
        execute_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            authority_gate=authority,
            source_providers=providers,
            renderers=SnapshotRendererRegistry(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert captured.value.code == "snapshot.authority_denied"
    assert authority.calls == 1
    assert provider.resolve_calls == 0
    results = tuple(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
    )
    assert len(results) == 1
    assert results[0].terminal_outcome == "failed"
    assert all(
        outcome.disposition == "failed_blocking"
        for outcome in results[0].entry_outcomes
    )


def test_permitted_source_unavailability_remains_pending_until_seal(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, _ = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=False,
        permitted_first_omission="source_unavailable",
    )
    copied = tuple(
        item for item in plan.entry_plans if item.materialization_kind == "copied_source"
    )
    root = (tmp_path / "partial_sources").resolve()
    # Only the second exact source exists.
    second_artifact = copied[1].source_artifact
    assert second_artifact is not None and second_artifact.source_locator is not None
    second_target = root.joinpath(*second_artifact.source_locator.split("/"))
    second_target.parent.mkdir(parents=True, exist_ok=True)
    second_target.write_bytes(b"available second source\n")
    provider = _ExecutionSourceProvider(root, copied[0])

    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_ExecutionAuthority(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
        renderers=SnapshotRendererRegistry(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert tuple(item.disposition for item in executed.entries) == (
        "omission_pending",
        "prepared_bytes",
    )
    assert executed.entries[0].pending_omission_reason == "source_unavailable"
    assert not any(
        isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
        for item in load_current_records(setup.workspace)
    )


def test_blocking_materialization_failure_persists_terminal_attempt_history(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, _ = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=False,
    )
    copied = next(
        item for item in plan.entry_plans if item.materialization_kind == "copied_source"
    )
    missing_root = (tmp_path / "missing_sources").resolve()
    missing_root.mkdir()
    provider = _ExecutionSourceProvider(missing_root, copied)

    with pytest.raises(SnapshotWorkflowError) as captured:
        execute_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            authority_gate=_ExecutionAuthority(),
            source_providers=SnapshotSourceProviderRegistry((provider,)),
            renderers=SnapshotRendererRegistry(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert captured.value.code == "snapshot.materialization_failed"
    results = tuple(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
    )
    assert len(results) == 1
    assert results[0].terminal_outcome == "failed"
    assert all(
        outcome.disposition == "failed_blocking"
        for outcome in results[0].entry_outcomes
    )
    assert results[0].findings[0].code == "snapshot.source_unavailable"


def test_seal_materializes_omission_copied_generated_manifest_and_edition(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, render_config = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=True,
        permitted_first_omission="source_unavailable",
    )
    copied_entries = tuple(
        item for item in plan.entry_plans if item.materialization_kind == "copied_source"
    )
    source_root = (tmp_path / "sealing_sources").resolve()
    second_artifact = copied_entries[1].source_artifact
    assert second_artifact is not None and second_artifact.source_locator is not None
    second_target = source_root.joinpath(*second_artifact.source_locator.split("/"))
    second_target.parent.mkdir(parents=True, exist_ok=True)
    second_target.write_bytes(b"seal-ready copied source\n")
    provider = _ExecutionSourceProvider(source_root, copied_entries[0])
    renderer = _ExecutionRenderer(render_config)

    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_ExecutionAuthority(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
        renderers=SnapshotRendererRegistry((renderer,)),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert tuple(item.disposition for item in executed.entries) == (
        "omission_pending",
        "prepared_bytes",
        "prepared_bytes",
    )

    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert sealed.edition.edition_number == 1
    assert sealed.edition.predecessor_edition is None
    assert sealed.attempt_result.terminal_outcome == "sealed"
    assert sealed.edition_path is not None
    assert sealed.edition_path.exists()
    assert not executed.staging_root.exists()
    manifest_path = sealed.edition_path / "internal" / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    assert snapshot_digest(manifest_bytes) == sealed.seal.manifest_digest
    assert sealed.seal.manifest_digest != sealed.seal.logical_inventory_digest
    manifest_value = json.loads(manifest_bytes)
    assert "manifest_digest" not in manifest_value
    assert (
        manifest_value["logical_inventory"]["contract_version"]
        == "vitrine_snapshot_logical_inventory_v1"
    )
    assert tuple(
        item["disposition"] for item in manifest_value["entries"]
    ) == ("omitted_permitted", "included", "included")

    persisted = load_current_records(setup.workspace)
    editions = tuple(item for item in persisted if isinstance(item, SnapshotEdition))
    manifests = tuple(item for item in persisted if isinstance(item, SnapshotManifest))
    seals = tuple(item for item in persisted if isinstance(item, SnapshotSeal))
    entries = tuple(item for item in persisted if isinstance(item, SnapshotEntry))
    omissions = tuple(item for item in persisted if isinstance(item, SnapshotOmission))
    materializations = tuple(
        item for item in persisted if isinstance(item, SnapshotMaterializationRecord)
    )
    materialization_provenance = tuple(
        item
        for item in persisted
        if isinstance(item, SnapshotMaterializationProvenance)
    )
    results = tuple(
        item
        for item in persisted
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
    )

    assert editions == (sealed.edition,)
    assert manifests == (sealed.manifest,)
    assert seals == (sealed.seal,)
    assert len(entries) == 2
    assert len(omissions) == 1
    assert omissions[0].reason_code == "source_unavailable"
    assert len(materializations) == 2
    assert {item.materialization_kind for item in materializations} == {
        "copied_source",
        "generated_vitrine",
    }
    assert len(materialization_provenance) == 2
    assert results == (sealed.attempt_result,)
    assert tuple(item.disposition for item in sealed.attempt_result.entry_outcomes) == (
        "omitted_permitted",
        "included",
        "included",
    )



def test_sealed_edition_verifies_exports_advances_pointer_and_detects_tamper(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, render_config = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=True,
        permitted_first_omission="source_unavailable",
    )
    copied_entries = tuple(
        item for item in plan.entry_plans if item.materialization_kind == "copied_source"
    )
    source_root = (tmp_path / "distribution_sources").resolve()
    second_artifact = copied_entries[1].source_artifact
    assert second_artifact is not None and second_artifact.source_locator is not None
    second_target = source_root.joinpath(*second_artifact.source_locator.split("/"))
    second_target.parent.mkdir(parents=True, exist_ok=True)
    second_target.write_bytes(b"distribution-ready copied source\n")
    provider = _ExecutionSourceProvider(source_root, copied_entries[0])
    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_ExecutionAuthority(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
        renderers=SnapshotRendererRegistry((_ExecutionRenderer(render_config),)),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert sealed.edition_path is not None
    with pytest.raises(SnapshotCustodyError) as captured:
        inspect_snapshot_series_lock(
            setup.workspace, snapshot_series_id=sealed.edition.snapshot_series_id
        )
    assert captured.value.code == "snapshot.build_lock_missing"

    verified = verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    assert verified.manifest_digest == sealed.seal.manifest_digest
    assert verified.logical_inventory_digest == sealed.seal.logical_inventory_digest

    export = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="snapshot_export_fixture",
    )
    assert export.export_path.exists()
    assert export.export_artifact.validation_result == "verified"
    assert len(export.export_artifact.included_entry_ids) == 2
    assert export.export_artifact.excluded_entry_ids == ()
    export_verification = verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
        verified_at=fixed_clock(),
    )
    assert (
        export_verification.directory_inventory_digest
        == export.export_artifact.directory_inventory_digest
    )
    replay = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=export.state_revision,
        generated_at=fixed_clock(),
        artifact_id="snapshot_export_replay_must_not_be_used",
    )
    assert replay.state_revision == export.state_revision
    assert (
        replay.export_artifact.snapshot_export_artifact_id
        == export.export_artifact.snapshot_export_artifact_id
    )

    pointer = advance_snapshot_current_pointer(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        expected_state_revision=export.state_revision,
        expected_pointer_revision=None,
        expected_current_edition=None,
        pointed_by=ACTOR,
        authority_reference="fixture_snapshot_pointer_authority",
        reason="Publish first sealed fixture Edition as current.",
        pointed_at=fixed_clock(),
        pointer_id="snapshot_pointer_fixture",
    )
    assert pointer.pointer.pointer_revision == 1
    assert pointer.pointer.edition_number == 1

    persisted = load_current_records(setup.workspace)
    assert any(
        isinstance(item, SnapshotExportArtifact)
        and item.snapshot_export_artifact_id == "snapshot_export_fixture"
        for item in persisted
    )
    assert any(
        isinstance(item, SnapshotCurrentPointerRevision)
        and item.snapshot_current_pointer_id == "snapshot_pointer_fixture"
        for item in persisted
    )

    # Historical verification is custody/canonical-state based; producer access is
    # irrelevant. Tampering the immutable Edition is detected independently.
    copied_entry = next(
        item
        for item in persisted
        if isinstance(item, SnapshotEntry)
        and item.snapshot_edition == sealed.edition.reference
        and item.relative_path != "index.md"
    )
    target = sealed.edition_path / "content" / copied_entry.relative_path
    target.write_bytes(target.read_bytes() + b"tamper")
    with pytest.raises(SnapshotDistributionError) as captured:
        verify_snapshot_edition(
            setup.workspace,
            snapshot_series_id=sealed.edition.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            verified_at=fixed_clock(),
        )
    assert captured.value.code == "snapshot_distribution.verification_failed"


def test_unresolved_attempt_recovery_is_explicit_and_preserves_staging(
    tmp_path: Path,
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    _, attempt, _ = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=False,
    )
    residue = (
        setup.workspace
        / "vitrine"
        / "snapshots"
        / "staging"
        / attempt.snapshot_build_attempt_id
        / "content"
        / "residue.bin"
    )
    residue.write_bytes(b"interrupted execution residue\n")

    inspection = inspect_snapshot_attempt_recovery(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
    )
    assert inspection.recovery_required
    assert inspection.staging_exists
    assert inspection.staging_has_residue
    assert inspection.build_lock_present
    assert inspection.build_lock_matches_attempt
    assert inspection.build_lock_sha256 is not None
    assert inspection.sealed_edition_numbers == ()
    audit = inspect_snapshot_custody(setup.workspace)
    audit_codes = {item.code for item in audit.findings}
    assert "snapshot.custody.incomplete_attempt" in audit_codes
    assert "snapshot.custody.build_lock_present" in audit_codes

    # Once sealing metadata exists, recovery must quarantine the allocated
    # Edition identity rather than make it reusable through abandonment.
    manifest = residue.parent.parent / "internal" / "manifest.json"
    manifest.write_bytes(b"{}\n")
    uncertain = inspect_snapshot_custody(setup.workspace)
    uncertain_codes = {item.code for item in uncertain.findings}
    assert "snapshot.custody.ambiguous_edition_target" in uncertain_codes
    assert "snapshot.custody.durability_uncertainty" in uncertain_codes
    with pytest.raises(SnapshotDistributionError) as captured:
        abandon_snapshot_build_attempt_after_recovery(
            setup.workspace,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            recovered_by=ACTOR,
            authority_reference="fixture_recovery_authority",
            reason="Unsafe abandonment must be rejected.",
            completed_at=fixed_clock(),
            result_id="snapshot_attempt_result_must_not_exist",
        )
    assert captured.value.code == "snapshot_distribution.recovery_unsafe"
    assert manifest.exists()
    manifest.unlink()

    recovered = abandon_snapshot_build_attempt_after_recovery(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        recovered_by=ACTOR,
        authority_reference="fixture_recovery_authority",
        reason="Operator inspected interrupted fixture staging and abandoned the Attempt.",
        completed_at=fixed_clock(),
        result_id="snapshot_attempt_result_recovery_fixture",
    )
    assert (
        recovered.attempt_result.terminal_outcome
        == "abandoned_after_explicit_recovery"
    )
    assert residue.exists()
    assert tuple(
        item.disposition for item in recovered.attempt_result.entry_outcomes
    ) == ("failed_blocking", "failed_blocking")

    after = inspect_snapshot_attempt_recovery(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
    )
    assert not after.recovery_required
    assert after.terminal_result_id == "snapshot_attempt_result_recovery_fixture"
    assert after.staging_has_residue
    assert not after.build_lock_present



def test_post_seal_publication_failure_preserves_canonical_edition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, _ = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=False,
    )
    providers, _ = _source_registry_for_plan(tmp_path, plan)
    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_ExecutionAuthority(),
        source_providers=providers,
        renderers=SnapshotRendererRegistry(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    def fail_publication(*_args: object, **_kwargs: object) -> Path:
        raise SnapshotCustodyError(
            "snapshot.edition_publish_failed",
            "Injected post-seal Edition publication failure.",
        )

    monkeypatch.setattr(
        "vitrine.snapshot_services.publish_snapshot_staging_as_edition",
        fail_publication,
    )
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert sealed.edition_path is None
    assert sealed.attempt_result.terminal_outcome == "partial_success_after_seal"
    assert sealed.attempt_result.sealed_snapshot_edition == sealed.edition.reference
    assert sealed.attempt_result.findings[0].code == "snapshot.edition_publish_failed"
    records = load_current_records(setup.workspace)
    assert any(
        isinstance(item, SnapshotEdition) and item.reference == sealed.edition.reference
        for item in records
    )
    assert any(
        isinstance(item, SnapshotManifest)
        and item.manifest_id == sealed.manifest.manifest_id
        for item in records
    )
    assert any(
        isinstance(item, SnapshotSeal) and item.seal_id == sealed.seal.seal_id
        for item in records
    )
    with pytest.raises(SnapshotDistributionError) as captured:
        verify_snapshot_edition(
            setup.workspace,
            snapshot_series_id=sealed.edition.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            verified_at=fixed_clock(),
        )
    assert captured.value.code == "snapshot_distribution.edition_unpublished"
    audit_codes = {item.code for item in inspect_snapshot_custody(setup.workspace).findings}
    assert "snapshot.custody.canonical_edition_missing_custody" in audit_codes
    with pytest.raises(SnapshotCustodyError) as captured_lock:
        inspect_snapshot_series_lock(
            setup.workspace, snapshot_series_id=sealed.edition.snapshot_series_id
        )
    assert captured_lock.value.code == "snapshot.build_lock_missing"
