from __future__ import annotations

import builtins
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.snapshot_fixture_support import (
    build_representative_snapshot_fixture_workspace,
)
from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.models import PortfolioCandidate
from vitrine.snapshot_materialization import (
    SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
)
from vitrine.storage import load_current_records_with_state
from vitrine.working_composition import prepare_working_composition


class _DescriptorOnlyProvider:
    def __init__(self, descriptor: SnapshotSourceProviderDescriptor) -> None:
        self._descriptor = descriptor
        self.resolve_calls = 0

    @property
    def descriptor(self) -> SnapshotSourceProviderDescriptor:
        return self._descriptor

    def resolve(self, request: object) -> object:
        self.resolve_calls += 1
        raise AssertionError("read-only preparation must not resolve source bytes")

    def confirm_stability(self, request: object, result: object) -> bool:
        raise AssertionError("read-only preparation must not confirm source stability")


def _provider_for(
    candidate: PortfolioCandidate,
    *,
    provider_id: str = "issue68_fixture_provider",
    concrete_media_types: tuple[str, ...] = (),
) -> _DescriptorOnlyProvider:
    endpoint = candidate.source_endpoint
    artifact = endpoint.source_artifact
    assert artifact is not None
    return _DescriptorOnlyProvider(
        SnapshotSourceProviderDescriptor(
            provider_id=provider_id,
            provider_version="1",
            producer_module_id=endpoint.producer_source.producer_module_id,
            projection_kind=artifact.representation_kind,
            projection_contract_version=(
                endpoint.producer_source.projection_contract_version
            ),
            artifact_kind=artifact.artifact_kind,
            representation_kind=artifact.representation_kind,
            concrete_media_types=concrete_media_types,
        )
    )




def _candidate_with_module(
    candidate: PortfolioCandidate, module_id: str
) -> PortfolioCandidate:
    endpoint = candidate.source_endpoint
    core = replace(
        endpoint.core_publication,
        work=replace(endpoint.core_publication.work, module_id=module_id),
    )
    producer = replace(endpoint.producer_source, producer_module_id=module_id)
    return replace(
        candidate,
        source_endpoint=replace(
            endpoint,
            core_publication=core,
            producer_source=producer,
        ),
    )


def _records_with_candidate(
    records: tuple[object, ...], candidate: PortfolioCandidate
) -> tuple[object, ...]:
    return tuple(
        candidate
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == candidate.candidate_id
        else item
        for item in records
    )

def _prepare_fixture(tmp_path: Path):
    setup = build_representative_snapshot_fixture_workspace(tmp_path)
    working = prepare_working_composition(setup.workspace, setup.portfolio_id)
    return setup, working


def _patch_prepared_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    working: object,
    current: object,
    records: tuple[object, ...],
) -> None:
    import vitrine.current_portfolio_build as module

    monkeypatch.setattr(
        module,
        "prepare_working_composition",
        lambda *_args, **_kwargs: working,
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (current, records),
    )


def test_first_party_plan_uses_profile_then_frozen_arrangement_order(
    tmp_path: Path,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
    )

    expected = tuple(
        placement.placement_id
        for section in working.sections
        for placement in section.placements
    )
    assert tuple(item.placement_id for item in prepared.planned_items) == expected
    assert tuple(item.plan_position for item in prepared.planned_items) == tuple(
        range(1, len(expected) + 1)
    )


def test_exact_provider_plans_copied_source_without_source_byte_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    altered = _records_with_candidate(records, candidate)
    _patch_prepared_state(
        monkeypatch, working=working, current=current, records=altered
    )
    artifact = candidate.source_endpoint.source_artifact
    assert artifact is not None
    concrete = () if artifact.media_type != SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE else (
        "application/pdf",
    )
    provider = _provider_for(candidate, concrete_media_types=concrete)

    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=SnapshotSourceProviderRegistry((provider,)),
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert item.materialization_kind == "copied_source"
    assert item.provider_disposition == "exact_provider"
    assert item.provider_id == provider.descriptor.provider_id
    assert item.target_relative_path is not None
    assert item.export_file is True
    assert provider.resolve_calls == 0
    assert item.entry_plan_id in prepared.directory_export.included_entry_plan_ids


def test_missing_exact_provider_is_reference_only_with_no_export_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    altered = _records_with_candidate(records, candidate)
    _patch_prepared_state(
        monkeypatch, working=working, current=current, records=altered
    )

    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert item.materialization_kind == "reference_only"
    assert item.provider_disposition == "reference_only_no_exact_provider"
    assert item.target_relative_path is None
    assert item.media_type is None
    assert item.export_file is False
    assert "no exact byte-capable" in item.explanation
    assert item.entry_plan_id in prepared.directory_export.excluded_entry_plan_ids


def test_live_scoreform_assessment_policy_is_reference_only_without_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    scoreform = setup.candidate("argument_assessment_attempt_1")
    endpoint = scoreform.source_endpoint
    artifact = endpoint.source_artifact
    assert artifact is not None and artifact.artifact_kind == "assessment_summary"

    live_candidate = _candidate_with_module(scoreform, "scoreform")
    altered = _records_with_candidate(records, live_candidate)
    _patch_prepared_state(
        monkeypatch,
        working=working,
        current=current,
        records=altered,
    )

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "scoreform" or name.startswith("scoreform."):
            raise AssertionError("Current Portfolio preparation imported ScoreForm")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    def forbidden_read_bytes(_path: Path) -> bytes:
        raise AssertionError("Current Portfolio preparation read source bytes")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == live_candidate.candidate_id
    )

    assert item.producer_module_id == "scoreform"
    assert item.content_class == "assessment_summary"
    assert item.materialization_kind == "reference_only"
    assert item.provider_disposition == "reference_only_by_producer_contract"
    assert item.target_relative_path is None
    assert item.media_type is None
    assert item.export_file is False


def test_deferred_media_path_is_suffix_neutral(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    endpoint = candidate.source_endpoint
    artifact = endpoint.source_artifact
    assert artifact is not None
    deferred_artifact = replace(
        artifact,
        media_type=SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE,
        source_locator=None,
    )
    deferred_endpoint = replace(endpoint, source_artifact=deferred_artifact)
    deferred_candidate = replace(candidate, source_endpoint=deferred_endpoint)
    altered = tuple(
        deferred_candidate
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == candidate.candidate_id
        else item
        for item in records
    )
    _patch_prepared_state(
        monkeypatch,
        working=working,
        current=current,
        records=altered,
    )
    provider = _provider_for(
        deferred_candidate,
        concrete_media_types=("application/pdf", "text/markdown"),
    )

    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=SnapshotSourceProviderRegistry((provider,)),
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == deferred_candidate.candidate_id
    )

    assert item.materialization_kind == "copied_source"
    assert item.media_type == SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE
    assert item.target_relative_path is not None
    assert "." not in item.target_relative_path.rsplit("/", 1)[-1]
    assert provider.resolve_calls == 0


def test_audience_prohibited_content_is_explicit_planned_omission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    rule = next(
        value
        for value in working.audience_rules
        if value.audience_rule_id == setup.audience.audience_rule_id
    )
    restricted = replace(
        rule,
        allowed_content_classes=("assessment_summary", "feedback"),
        prohibited_content_classes=("student_work",),
    )
    altered_working = replace(working, audience_rules=(restricted,))
    current, records = load_current_records_with_state(setup.workspace)
    _patch_prepared_state(
        monkeypatch,
        working=altered_working,
        current=current,
        records=records,
    )
    candidate = setup.candidate("evidence_selected")

    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=restricted.audience_rule_id,
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert item.materialization_kind == "reference_only"
    assert item.provider_disposition == "audience_prohibited"
    assert item.permitted_omission_reason == "audience_prohibited"
    assert item.export_file is False
    assert item.entry_plan is not None
    assert item.entry_plan.permitted_omission_reason == "audience_prohibited"


def test_conflicting_exact_providers_block_instead_of_downgrading_silently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    altered_records = _records_with_candidate(records, candidate)
    _patch_prepared_state(
        monkeypatch, working=working, current=current, records=altered_records
    )
    provider_a = _provider_for(candidate, provider_id="issue68_conflict_a")
    provider_b = _provider_for(candidate, provider_id="issue68_conflict_b")

    prepared = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=SnapshotSourceProviderRegistry((provider_a, provider_b)),
    )
    item = next(
        value
        for value in prepared.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert item.materialization_kind == "reference_only"
    assert item.provider_disposition == "source_provider_conflict"
    assert item.export_file is False
    assert "source_provider_conflict" in prepared.blocking_reasons
    assert provider_a.resolve_calls == 0
    assert provider_b.resolve_calls == 0


def test_display_text_does_not_enter_deterministic_ids_paths_or_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    altered_records = _records_with_candidate(records, candidate)
    provider = _provider_for(candidate)
    registry = SnapshotSourceProviderRegistry((provider,))
    _patch_prepared_state(
        monkeypatch,
        working=working,
        current=current,
        records=altered_records,
    )
    first = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=registry,
    )

    changed_sections = tuple(
        replace(
            section,
            placements=tuple(
                replace(
                    placement,
                    candidate_display_snapshot="Sensitive Local Display Name",
                    display_title="Teacher-facing local label",
                )
                if placement.candidate_id == candidate.candidate_id
                else placement
                for placement in section.placements
            ),
        )
        for section in working.sections
    )
    changed_working = replace(working, sections=changed_sections)
    _patch_prepared_state(
        monkeypatch,
        working=changed_working,
        current=current,
        records=altered_records,
    )
    second = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=registry,
    )
    first_item = next(
        value
        for value in first.planned_items
        if value.candidate_id == candidate.candidate_id
    )
    second_item = next(
        value
        for value in second.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert first_item.entry_plan_id == second_item.entry_plan_id
    assert first_item.target_relative_path == second_item.target_relative_path
    assert first.preparation_fingerprint == second.preparation_fingerprint
    assert "Sensitive" not in second_item.entry_plan_id
    assert second_item.target_relative_path is not None
    assert "Sensitive" not in second_item.target_relative_path


def test_provider_identity_is_bound_into_plan_identity_and_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, working = _prepare_fixture(tmp_path)
    current, records = load_current_records_with_state(setup.workspace)
    candidate = _candidate_with_module(setup.candidate("evidence_selected"), "quillan")
    altered_records = _records_with_candidate(records, candidate)
    _patch_prepared_state(
        monkeypatch, working=working, current=current, records=altered_records
    )
    first_provider = _provider_for(candidate, provider_id="issue68_provider_a")
    second_provider = _provider_for(candidate, provider_id="issue68_provider_b")

    first = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=SnapshotSourceProviderRegistry((first_provider,)),
    )
    second = prepare_current_portfolio_build(
        setup.workspace,
        setup.portfolio_id,
        audience_rule_id=setup.audience.audience_rule_id,
        source_providers=SnapshotSourceProviderRegistry((second_provider,)),
    )
    first_item = next(
        value
        for value in first.planned_items
        if value.candidate_id == candidate.candidate_id
    )
    second_item = next(
        value
        for value in second.planned_items
        if value.candidate_id == candidate.candidate_id
    )

    assert first_item.entry_plan_id != second_item.entry_plan_id
    assert first.preparation_fingerprint != second.preparation_fingerprint
