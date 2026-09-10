from __future__ import annotations

from pathlib import Path

import pytest

from scripts.curation_fixture_support import ACTOR, fixed_clock
from scripts.snapshot_fixture_support import build_snapshot_fixture_workspace
from vitrine.attention import VitrineAttentionQuery, evaluate_vitrine_attention
from vitrine.models import (
    DigestReference,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotSeries,
)
from vitrine.snapshot_distribution import create_snapshot_directory_export
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotRendererRegistry,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)
from vitrine.snapshot_services import (
    SnapshotWorkflowError,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import load_current_records


class _Authority:
    def __init__(self, outcome: str = "allowed") -> None:
        self.outcome = outcome

    def authorize(self, _request: object) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome=self.outcome,
            authority_reference=(
                "attention_snapshot_fixture_authority"
                if self.outcome == "allowed"
                else None
            ),
        )


class _SourceProvider:
    def __init__(self, root: Path, entry: SnapshotEntryPlan) -> None:
        assert entry.producer_module_id is not None
        assert entry.projection_kind is not None
        assert entry.projection_contract_version is not None
        assert entry.source_artifact is not None
        self.root = root
        self.descriptor = SnapshotSourceProviderDescriptor(
            provider_id="attention_snapshot_fixture_provider",
            provider_version="1",
            producer_module_id=entry.producer_module_id,
            projection_kind=entry.projection_kind,
            projection_contract_version=entry.projection_contract_version,
            artifact_kind=entry.source_artifact.artifact_kind,
            representation_kind=entry.source_artifact.representation_kind,
        )

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotSourceResult:
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
        self,
        _request: SnapshotSourceRequest,
        _result: SnapshotSourceResult,
    ) -> bool:
        return True


def _records(setup: object):
    return load_current_records(getattr(setup, "workspace"))


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
    assert artifact is not None
    assert artifact.source_locator is not None
    return SnapshotEntryPlan(
        entry_plan_id=f"attention_entry_{position}",
        plan_position=position,
        section_id=placement.section_id,
        ordinal=1,
        semantic_role="selected_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        source_publication_id=(
            candidate.source_endpoint.core_publication.publication_id
        ),
        producer_module_id=(
            candidate.source_endpoint.producer_source.producer_module_id
        ),
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=f"{placement.section_id}/work-{position}.txt",
        media_type=artifact.media_type,
    )


def _series_and_request(setup: object) -> tuple[SnapshotSeries, SnapshotBuildRequest]:
    series_result = create_snapshot_series(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        audience_context_id=setup.audience.audience_context_id,
        snapshot_purpose="improvement",
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    series = next(
        item for item in series_result.records if isinstance(item, SnapshotSeries)
    )
    request_result = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=setup.composition.composition_revision,
        requested_by=ACTOR,
        idempotency_key="attention-snapshot-request",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    request = next(
        item
        for item in request_result.records
        if isinstance(item, SnapshotBuildRequest)
    )
    return series, request


def _plan(
    setup: object,
    *,
    permitted_first_omission: str | None = None,
) -> SnapshotBuildPlan:
    _, request = _series_and_request(setup)
    entries = (
        _source_entry(
            setup=setup,
            selection=setup.baseline_selection,
            placement=setup.baseline_placement,
            position=1,
        ),
        _source_entry(
            setup=setup,
            selection=setup.later_selection,
            placement=setup.later_placement,
            position=2,
        ),
    )
    if permitted_first_omission is not None:
        from dataclasses import replace

        entries = (
            replace(
                entries[0],
                permitted_omission_reason=permitted_first_omission,
            ),
            entries[1],
        )
    export = SnapshotExportPlan(
        export_plan_id="attention_export_plan",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="a" * 64),
    )
    result = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=(
            setup.inventory.unresolved_obligation_codes
        ),
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(
        item for item in result.records if isinstance(item, SnapshotBuildPlan)
    )


def _providers(
    tmp_path: Path,
    plan: SnapshotBuildPlan,
    *,
    omit_first: bool = False,
) -> SnapshotSourceProviderRegistry:
    entries = tuple(
        item
        for item in plan.entry_plans
        if item.materialization_kind == "copied_source"
    )
    root = (tmp_path / "attention_sources").resolve()
    for index, entry in enumerate(entries):
        artifact = entry.source_artifact
        assert artifact is not None
        assert artifact.source_locator is not None
        if omit_first and index == 0:
            continue
        target = root.joinpath(*artifact.source_locator.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"attention source {index}\n".encode())
    return SnapshotSourceProviderRegistry((_SourceProvider(root, entries[0]),))


def _start(setup: object, plan: SnapshotBuildPlan):
    return start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )


def _seal(
    setup: object,
    plan: SnapshotBuildPlan,
    attempt_id: str,
    providers: SnapshotSourceProviderRegistry,
):
    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_Authority(),
        source_providers=providers,
        renderers=SnapshotRendererRegistry(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )


def _summary(report: object, code: str):
    return next(
        (
            item
            for item in getattr(report, "summaries")
            if item.code == code
        ),
        None,
    )


def test_incomplete_attempt_is_one_recovery_build_despite_build_lock(
    tmp_path: Path,
) -> None:
    setup = build_snapshot_fixture_workspace(tmp_path)
    plan = _plan(setup)
    _start(setup, plan)

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    recovery = _summary(report, "vitrine_snapshot_recovery_required")
    assert recovery is not None
    assert recovery.count == 1
    assert recovery.portfolio_id == setup.portfolio_id
    assert "snapshot_attempt_incomplete" in recovery.reason_codes


def test_historical_failed_attempt_drops_after_later_attempt_seals(
    tmp_path: Path,
) -> None:
    setup = build_snapshot_fixture_workspace(tmp_path)
    plan = _plan(setup)
    first = _start(setup, plan)
    providers = _providers(tmp_path, plan)

    with pytest.raises(SnapshotWorkflowError) as captured:
        execute_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_attempt_id=first.attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            authority_gate=_Authority("denied"),
            source_providers=providers,
            renderers=SnapshotRendererRegistry(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert captured.value.code == "snapshot.authority_denied"

    failed = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    failed_summary = _summary(failed, "vitrine_snapshot_build_failed")
    assert failed_summary is not None
    assert failed_summary.count == 1

    second = _start(setup, plan)
    sealed = _seal(
        setup,
        plan,
        second.attempt.snapshot_build_attempt_id,
        providers,
    )
    assert sealed.attempt_result.terminal_outcome == "sealed"

    after = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    assert _summary(after, "vitrine_snapshot_build_failed") is None
    pending = _summary(after, "vitrine_export_pending_after_seal")
    assert pending is not None
    assert pending.count == 1


def test_current_sealed_omission_persists_but_export_pending_resolves(
    tmp_path: Path,
) -> None:
    setup = build_snapshot_fixture_workspace(tmp_path)
    plan = _plan(setup, permitted_first_omission="source_unavailable")
    started = _start(setup, plan)
    sealed = _seal(
        setup,
        plan,
        started.attempt.snapshot_build_attempt_id,
        _providers(tmp_path, plan, omit_first=True),
    )

    before_export = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    omission = _summary(before_export, "vitrine_omission_source_unavailable")
    assert omission is not None
    assert omission.count == 1
    assert _summary(before_export, "vitrine_export_pending_after_seal") is not None

    create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="attention_export_complete",
    )

    after_export = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    assert _summary(after_export, "vitrine_export_pending_after_seal") is None
    assert _summary(after_export, "vitrine_export_verification_problem") is None
    assert _summary(after_export, "vitrine_omission_source_unavailable") is not None


def test_corrupt_current_export_is_reported_once_not_double_counted(
    tmp_path: Path,
) -> None:
    setup = build_snapshot_fixture_workspace(tmp_path)
    plan = _plan(setup)
    started = _start(setup, plan)
    sealed = _seal(
        setup,
        plan,
        started.attempt.snapshot_build_attempt_id,
        _providers(tmp_path, plan),
    )
    export = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="attention_export_corrupt",
    )
    target = next(path for path in export.export_path.rglob("*") if path.is_file())
    target.write_bytes(target.read_bytes() + b"tamper")

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    problem = _summary(report, "vitrine_export_verification_problem")
    assert problem is not None
    assert problem.count == 1
    assert _summary(report, "vitrine_export_pending_after_seal") is None


def test_unscoped_orphan_staging_is_workspace_only_integrity_attention(
    tmp_path: Path,
) -> None:
    setup = build_snapshot_fixture_workspace(tmp_path)
    orphan = (
        setup.workspace
        / "vitrine"
        / "snapshots"
        / "staging"
        / "orphan_attention_staging"
    )
    orphan.mkdir(parents=True)
    (orphan / "residue.bin").write_bytes(b"orphan\n")

    workspace_report = evaluate_vitrine_attention(setup.workspace)
    scoped_report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    integrity = _summary(workspace_report, "vitrine_snapshot_integrity_problem")
    assert integrity is not None
    assert integrity.portfolio_id is None
    assert "snapshot.custody.orphan_staging" in integrity.reason_codes
    assert _summary(scoped_report, "vitrine_snapshot_integrity_problem") is None
