from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.curation_services import CurationWorkflowError
from vitrine.current_portfolio_build import (
    CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
    CurrentPortfolioAudienceContextResolution,
    CurrentPortfolioBuildPreparation,
    CurrentPortfolioDirectoryExportPreview,
    CurrentPortfolioGeneratedReflection,
    CurrentPortfolioSnapshotSeriesResolution,
)
from vitrine.current_portfolio_execution import (
    CurrentPortfolioExecutionError,
    CurrentPortfolioPlanExecutionResult,
    execute_current_portfolio_build_export,
    execute_prepared_current_portfolio_build,
    execute_prepared_current_portfolio_plan,
    resume_current_portfolio_export,
)
from vitrine.current_portfolio_reflection import (
    current_portfolio_reflection_configuration_digest,
)
from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    CurationTargetRef,
    DigestReference,
    PortfolioReflection,
    ProfileRevisionRef,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotSeries,
    SourceArtifactReference,
)
from vitrine.snapshot_distribution import SnapshotDistributionError
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotRendererRegistry,
    SnapshotRenderRequest,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_services import SnapshotMutationResult, SnapshotWorkflowError
from vitrine.working_composition import (
    WorkingCompositionAudienceSummary,
    WorkingCompositionPayloadPreview,
)

NOW = datetime(2026, 9, 8, 3, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_actor",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_1",
    profile_revision=1,
)
RULE = WorkingCompositionAudienceSummary(
    audience_rule_id="audience_rule_1",
    audience_class="external_reviewer",
    purpose="Exact portfolio review",
    allowed_content_classes=("reflection",),
    prohibited_content_classes=(),
    required_review_classes=(),
    presentation_class="showcase",
    retention_policy_reference=None,
)


def _entry() -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id="entry_reflection_1",
        plan_position=1,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="section-01/01-reflection.txt",
        media_type="text/plain",
        renderer_id="vitrine_portfolio_reflection",
        renderer_version="1",
        renderer_contract_version="vitrine_portfolio_reflection_renderer_v1",
        renderer_configuration_digest=DigestReference(value="1" * 64),
        input_references=(
            SnapshotInputReference(
                record_type="portfolio_reflection",
                record_id="reflection_1",
                record_revision=1,
            ),
        ),
    )


def _generated(entry: SnapshotEntryPlan) -> CurrentPortfolioGeneratedReflection:
    return CurrentPortfolioGeneratedReflection(
        entry_plan_id=entry.entry_plan_id,
        plan_position=entry.plan_position,
        section_id="reflection",
        section_label="Reflection",
        section_order=1,
        position_in_section=1,
        reflection_id="reflection_1",
        reflection_revision=1,
        reflection_requirement_id="reflection_requirement",
        prompt_id="prompt_1",
        prompt_version="1",
        prompt_snapshot_sha256="2" * 64,
        target_scope="portfolio",
        target_references=(),
        content_mode="inline_text",
        content_format="plain_text",
        language="en",
        content_sha256="3" * 64,
        content_class="reflection",
        materialization_kind="generated_vitrine",
        renderer_id=entry.renderer_id or "",
        renderer_version=entry.renderer_version or "",
        renderer_contract_version=entry.renderer_contract_version or "",
        renderer_configuration_sha256=(
            entry.renderer_configuration_digest.value
            if entry.renderer_configuration_digest is not None
            else ""
        ),
        renderer_template_sha256=None,
        target_relative_path=entry.target_relative_path,
        media_type=entry.media_type,
        output_byte_size=23,
        output_sha256="4" * 64,
        export_file=True,
        supported=True,
        explanation="Exact frozen Reflection will be rendered by Vitrine.",
        entry_plan=entry,
    )


def _preparation(
    *,
    audience_disposition: str = "create",
    audience_context_id: str | None = None,
    series_disposition: str = "create",
    snapshot_series_id: str | None = None,
) -> CurrentPortfolioBuildPreparation:
    entry = _entry()
    generated = _generated(entry)
    export = CurrentPortfolioDirectoryExportPreview(
        export_plan_id="export_plan_exact",
        export_format="directory_package",
        export_contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_sha256="5" * 64,
    )
    return CurrentPortfolioBuildPreparation(
        contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        observed_state_revision=10,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision_id=PROFILE.portfolio_profile_id,
        profile_revision_number=PROFILE.profile_revision,
        current_composition_pointer_revision=2,
        current_composition_revision=2,
        working_composition_preparation_fingerprint="6" * 64,
        working_composition_disposition="reuse_exact_current",
        composition_inventory=WorkingCompositionPayloadPreview(
            selection_ids=(),
            placement_ids=(),
            arrangement_ids=(),
            included_rationale_ids=(),
            included_curation_revisions=(),
            applicable_review_decision_ids=(),
            related_profile_requirement_ids=(),
            unresolved_obligation_codes=(),
            coherence_state="coherent",
        ),
        sections=(),
        selections=(),
        unplaced_selection_ids=(),
        selected_audience_rule=RULE,
        audience_context=CurrentPortfolioAudienceContextResolution(
            disposition=audience_disposition,
            matching_audience_context_ids=(
                () if audience_context_id is None else (audience_context_id,)
            ),
            selected_audience_context_id=audience_context_id,
        ),
        snapshot_series=CurrentPortfolioSnapshotSeriesResolution(
            disposition=series_disposition,
            matching_snapshot_series_ids=(
                () if snapshot_series_id is None else (snapshot_series_id,)
            ),
            selected_snapshot_series_id=snapshot_series_id,
        ),
        required_reviews=(),
        applicable_review_decisions=(),
        missing_required_review_classes=(),
        unresolved_obligation_codes=(),
        acknowledged_obligation_codes=(),
        obligation_acknowledgement_complete=True,
        planned_items=(),
        generated_reflections=(generated,),
        directory_export=export,
        warnings=(),
        blocking_reasons=(),
        preparation_fingerprint="7" * 64,
    )


def _audience(audience_context_id: str) -> AudienceContext:
    return AudienceContext(
        audience_context_id=audience_context_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        audience_rule_id=RULE.audience_rule_id,
        audience_class=RULE.audience_class,
        purpose=RULE.purpose,
        subject_scope="portfolio_subject",
        allowed_content_classes=RULE.allowed_content_classes,
        prohibited_content_classes=RULE.prohibited_content_classes,
        required_review_classes=RULE.required_review_classes,
        presentation_class=RULE.presentation_class,
        retention_policy_reference=RULE.retention_policy_reference,
        created_at=NOW,
        created_by=ACTOR,
    )


def _series(snapshot_series_id: str, audience_context_id: str) -> SnapshotSeries:
    return SnapshotSeries(
        snapshot_series_id=snapshot_series_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        snapshot_purpose=RULE.purpose,
        audience_context_id=audience_context_id,
        created_at=NOW,
        created_by=ACTOR,
    )


def _request(
    request_id: str,
    series_id: str,
    audience_context_id: str,
    idempotency_key: str,
) -> SnapshotBuildRequest:
    return SnapshotBuildRequest(
        snapshot_build_request_id=request_id,
        snapshot_series_id=series_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=2,
        audience_context_id=audience_context_id,
        snapshot_purpose=RULE.purpose,
        requested_export_formats=("directory_package",),
        requested_by=ACTOR,
        requested_at=NOW,
        curation_review_decision_ids=(),
        idempotency_key=idempotency_key,
    )


def _plan(
    plan_id: str,
    request: SnapshotBuildRequest,
    entry_plans: tuple[SnapshotEntryPlan, ...],
    export_plans: tuple[SnapshotExportPlan, ...],
    acknowledged_obligation_codes: tuple[str, ...],
) -> SnapshotBuildPlan:
    return SnapshotBuildPlan(
        snapshot_build_plan_id=plan_id,
        snapshot_build_request_id=request.snapshot_build_request_id,
        snapshot_series_id=request.snapshot_series_id,
        plan_revision=1,
        portfolio_id=request.portfolio_id,
        portfolio_subject_id=request.portfolio_subject_id,
        profile_binding_id=request.profile_binding_id,
        profile_revision=request.profile_revision,
        composition_revision=request.composition_revision,
        audience_context_id=request.audience_context_id,
        entry_plans=entry_plans,
        export_plans=export_plans,
        required_review_references=request.curation_review_decision_ids,
        acknowledged_obligation_codes=acknowledged_obligation_codes,
        path_policy_id="snapshot_path_policy",
        digest_policy_id="snapshot_digest_policy",
        builder_contract_id="vitrine_snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint="8" * 64,
    )


def _patch_revalidation(
    monkeypatch: pytest.MonkeyPatch,
    preparation: CurrentPortfolioBuildPreparation,
) -> None:
    import vitrine.current_portfolio_execution as module

    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=preparation.observed_state_revision
        ),
    )
    monkeypatch.setattr(
        module,
        "prepare_current_portfolio_build",
        lambda *_args, **_kwargs: preparation,
    )


def test_blocked_preparation_stops_before_any_canonical_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = replace(_preparation(), blocking_reasons=("missing_required_reviews",))
    calls: list[str] = []
    monkeypatch.setattr(
        module, "load_current_state", lambda *_args: calls.append("load")
    )
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: calls.append("write"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured.value.code == "current_portfolio_build.preparation_blocked"
    assert calls == []


def test_state_change_after_preview_fails_before_first_task_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    writes: list[str] = []
    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args: SimpleNamespace(state_revision=11),
    )
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: writes.append("audience"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured.value.code == "current_portfolio_build.prepared_state_changed"
    assert writes == []


def test_changed_rederived_fingerprint_is_not_silently_substituted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    changed = replace(prepared, preparation_fingerprint="9" * 64)
    writes: list[str] = []
    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args: SimpleNamespace(state_revision=10),
    )
    monkeypatch.setattr(
        module,
        "prepare_current_portfolio_build",
        lambda *_args, **_kwargs: changed,
    )
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: writes.append("audience"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured.value.code == "current_portfolio_build.prepared_state_changed"
    assert writes == []



def test_curation_revalidation_failure_is_translated_before_first_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    writes: list[str] = []
    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args: SimpleNamespace(state_revision=10),
    )

    def fail_reprepare(*_args, **_kwargs):
        raise CurationWorkflowError(
            "curation.composition_inconsistent",
            "synthetic revalidation failure",
            stage="preparation",
        )

    monkeypatch.setattr(module, "prepare_current_portfolio_build", fail_reprepare)
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: writes.append("audience"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured.value.code == "current_portfolio_build.prepared_state_changed"
    assert captured.value.underlying_code == "curation.composition_inconsistent"
    assert writes == []

def test_create_sequence_threads_exact_returned_state_revisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    _patch_revalidation(monkeypatch, prepared)
    calls: list[tuple[str, int]] = []

    def create_audience(*_args, **kwargs):
        calls.append(("audience", kwargs["expected_state_revision"]))
        return SimpleNamespace(context=_audience("audience_created"), state_revision=11)

    def create_series(*_args, **kwargs):
        calls.append(("series", kwargs["expected_state_revision"]))
        series = _series("series_created", kwargs["audience_context_id"])
        return SnapshotMutationResult(
            state_revision=12,
            records=(series,),
            disposition="created",
        )

    def create_request(*_args, **kwargs):
        calls.append(("request", kwargs["expected_state_revision"]))
        request = _request(
            "request_created",
            kwargs["snapshot_series_id"],
            "audience_created",
            kwargs["idempotency_key"],
        )
        return SnapshotMutationResult(
            state_revision=13,
            records=(request,),
            disposition="created",
        )

    def create_plan(*_args, **kwargs):
        calls.append(("plan", kwargs["expected_state_revision"]))
        request = _request(
            kwargs["snapshot_build_request_id"],
            "series_created",
            "audience_created",
            "unused",
        )
        plan = _plan(
            "plan_created",
            request,
            kwargs["entry_plans"],
            kwargs["export_plans"],
            kwargs["acknowledged_obligation_codes"],
        )
        return SnapshotMutationResult(
            state_revision=14,
            records=(plan,),
            disposition="created",
        )

    monkeypatch.setattr(module, "create_audience_context", create_audience)
    monkeypatch.setattr(module, "create_snapshot_series", create_series)
    monkeypatch.setattr(module, "request_snapshot_build", create_request)
    monkeypatch.setattr(module, "plan_snapshot_build", create_plan)

    result = execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert calls == [
        ("audience", 10),
        ("series", 11),
        ("request", 12),
        ("plan", 13),
    ]
    assert result.state_revision == 14
    assert result.audience_context_id == "audience_created"
    assert result.snapshot_series_id == "series_created"
    assert result.snapshot_build_request_id == "request_created"
    assert result.snapshot_build_plan_id == "plan_created"
    assert result.audience_context_disposition == "created"
    assert result.snapshot_series_disposition == "created"


def test_reuse_path_does_not_create_context_or_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation(
        audience_disposition="reuse",
        audience_context_id="audience_existing",
        series_disposition="reuse",
        snapshot_series_id="series_existing",
    )
    _patch_revalidation(monkeypatch, prepared)
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: pytest.fail("Audience Context must be reused"),
    )
    monkeypatch.setattr(
        module,
        "create_snapshot_series",
        lambda *_args, **_kwargs: pytest.fail("Snapshot Series must be reused"),
    )

    def create_request(*_args, **kwargs):
        assert kwargs["expected_state_revision"] == 10
        assert kwargs["snapshot_series_id"] == "series_existing"
        request = _request(
            "request_created",
            "series_existing",
            "audience_existing",
            kwargs["idempotency_key"],
        )
        return SnapshotMutationResult(
            state_revision=11,
            records=(request,),
            disposition="created",
        )

    def create_plan(*_args, **kwargs):
        assert kwargs["expected_state_revision"] == 11
        request = _request(
            kwargs["snapshot_build_request_id"],
            "series_existing",
            "audience_existing",
            "unused",
        )
        plan = _plan(
            "plan_created",
            request,
            kwargs["entry_plans"],
            kwargs["export_plans"],
            kwargs["acknowledged_obligation_codes"],
        )
        return SnapshotMutationResult(
            state_revision=12,
            records=(plan,),
            disposition="created",
        )

    monkeypatch.setattr(module, "request_snapshot_build", create_request)
    monkeypatch.setattr(module, "plan_snapshot_build", create_plan)

    result = execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert result.audience_context_disposition == "reused"
    assert result.snapshot_series_disposition == "reused"
    assert result.state_revision == 12


def test_request_and_plan_freeze_exact_reviewed_export_and_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = replace(
        _preparation(
            audience_disposition="reuse",
            audience_context_id="audience_existing",
            series_disposition="reuse",
            snapshot_series_id="series_existing",
        ),
        unresolved_obligation_codes=("reflection_required",),
        acknowledged_obligation_codes=("reflection_required",),
        obligation_acknowledgement_complete=True,
    )
    _patch_revalidation(monkeypatch, prepared)
    captured: dict[str, object] = {}

    def create_request(*_args, **kwargs):
        captured["idempotency_key"] = kwargs["idempotency_key"]
        request = _request(
            "request_created",
            "series_existing",
            "audience_existing",
            kwargs["idempotency_key"],
        )
        return SnapshotMutationResult(
            state_revision=11,
            records=(request,),
            disposition="created",
        )

    def create_plan(*_args, **kwargs):
        captured["entries"] = kwargs["entry_plans"]
        captured["exports"] = kwargs["export_plans"]
        captured["acknowledged"] = kwargs["acknowledged_obligation_codes"]
        request = _request(
            kwargs["snapshot_build_request_id"],
            "series_existing",
            "audience_existing",
            "unused",
        )
        plan = _plan(
            "plan_created",
            request,
            kwargs["entry_plans"],
            kwargs["export_plans"],
            kwargs["acknowledged_obligation_codes"],
        )
        return SnapshotMutationResult(
            state_revision=12,
            records=(plan,),
            disposition="created",
        )

    monkeypatch.setattr(module, "request_snapshot_build", create_request)
    monkeypatch.setattr(module, "plan_snapshot_build", create_plan)

    result = execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured["entries"] == prepared.snapshot_entry_plans
    export = captured["exports"]
    assert isinstance(export, tuple) and len(export) == 1
    assert export[0].export_plan_id == prepared.directory_export.export_plan_id
    assert export[0].included_entry_plan_ids == (
        prepared.directory_export.included_entry_plan_ids
    )
    assert captured["acknowledged"] == ("reflection_required",)
    assert result.request_idempotency_key.startswith("current_portfolio_build:")
    assert result.request_idempotency_key != (
        f"current_portfolio_build:{prepared.preparation_fingerprint}"
    )



def test_request_key_is_stable_across_create_to_reuse_preparation_transition() -> None:
    import vitrine.current_portfolio_execution as module

    creating = _preparation()
    reused = replace(
        _preparation(
            audience_disposition="reuse",
            audience_context_id="audience_created",
            series_disposition="reuse",
            snapshot_series_id="series_created",
        ),
        preparation_fingerprint="9" * 64,
    )
    first = module._request_idempotency_key(
        creating,
        audience_context_id="audience_created",
        snapshot_series_id="series_created",
        actor=ACTOR,
    )
    second = module._request_idempotency_key(
        reused,
        audience_context_id="audience_created",
        snapshot_series_id="series_created",
        actor=ACTOR,
    )

    assert first == second

def test_mid_sequence_state_conflict_preserves_completed_stage_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    _patch_revalidation(monkeypatch, prepared)
    monkeypatch.setattr(
        module,
        "create_audience_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            context=_audience("audience_created"), state_revision=11
        ),
    )

    def conflict(*_args, **_kwargs):
        raise SnapshotWorkflowError(
            "snapshot.state_conflict",
            "synthetic conflict",
            stage="concurrency",
        )

    monkeypatch.setattr(module, "create_snapshot_series", conflict)

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    error = captured.value
    assert error.code == "current_portfolio_build.execution_state_conflict"
    assert error.underlying_code == "snapshot.state_conflict"
    assert error.completed_stages == ("audience_context",)
    assert error.audience_context_id == "audience_created"
    assert error.snapshot_series_id is None


def test_old_preparation_is_not_silently_replayed_after_state_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    state = {"revision": 10}
    writes: list[str] = []
    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args: SimpleNamespace(state_revision=state["revision"]),
    )
    monkeypatch.setattr(
        module,
        "prepare_current_portfolio_build",
        lambda *_args, **_kwargs: prepared,
    )

    def create_audience(*_args, **_kwargs):
        writes.append("audience")
        state["revision"] = 11
        return SimpleNamespace(context=_audience("audience_created"), state_revision=11)

    def create_series(*_args, **kwargs):
        writes.append("series")
        state["revision"] = 12
        series = _series("series_created", kwargs["audience_context_id"])
        return SnapshotMutationResult(
            state_revision=12,
            records=(series,),
            disposition="created",
        )

    def create_request(*_args, **kwargs):
        writes.append("request")
        state["revision"] = 13
        request = _request(
            "request_created",
            "series_created",
            "audience_created",
            kwargs["idempotency_key"],
        )
        return SnapshotMutationResult(
            state_revision=13,
            records=(request,),
            disposition="created",
        )

    def create_plan(*_args, **kwargs):
        writes.append("plan")
        state["revision"] = 14
        request = _request(
            kwargs["snapshot_build_request_id"],
            "series_created",
            "audience_created",
            "unused",
        )
        plan = _plan(
            "plan_created",
            request,
            kwargs["entry_plans"],
            kwargs["export_plans"],
            kwargs["acknowledged_obligation_codes"],
        )
        return SnapshotMutationResult(
            state_revision=14,
            records=(plan,),
            disposition="created",
        )

    monkeypatch.setattr(module, "create_audience_context", create_audience)
    monkeypatch.setattr(module, "create_snapshot_series", create_series)
    monkeypatch.setattr(module, "request_snapshot_build", create_request)
    monkeypatch.setattr(module, "plan_snapshot_build", create_plan)

    execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)
    assert writes == ["audience", "series", "request", "plan"]

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_prepared_current_portfolio_plan(".", prepared, actor=ACTOR)

    assert captured.value.code == "current_portfolio_build.prepared_state_changed"
    assert writes == ["audience", "series", "request", "plan"]


def test_revalidation_uses_exact_prepared_choices_and_provider_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation(
        audience_disposition="reuse",
        audience_context_id="audience_existing",
        series_disposition="reuse",
        snapshot_series_id="series_existing",
    )
    registry = SnapshotSourceProviderRegistry()
    monkeypatch.setattr(
        module,
        "load_current_state",
        lambda *_args: SimpleNamespace(state_revision=10),
    )
    captured: dict[str, object] = {}

    def reprepare(*_args, **kwargs):
        captured.update(kwargs)
        return prepared

    monkeypatch.setattr(module, "prepare_current_portfolio_build", reprepare)

    def stop_at_request(*_args, **_kwargs):
        raise SnapshotWorkflowError(
            "snapshot.state_conflict",
            "stop after revalidation",
            stage="concurrency",
        )

    monkeypatch.setattr(module, "request_snapshot_build", stop_at_request)

    with pytest.raises(CurrentPortfolioExecutionError):
        execute_prepared_current_portfolio_plan(
            Path("."),
            prepared,
            actor=ACTOR,
            source_providers=registry,
        )

    assert captured["audience_context_id"] == "audience_existing"
    assert captured["snapshot_series_id"] == "series_existing"
    assert captured["acknowledged_obligation_codes"] == ()
    assert captured["source_providers"] is registry


def _plan_execution(
    *,
    state_revision: int = 14,
) -> CurrentPortfolioPlanExecutionResult:
    return CurrentPortfolioPlanExecutionResult(
        contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        preparation_fingerprint="7" * 64,
        initial_state_revision=10,
        state_revision=state_revision,
        audience_context_id="audience_created",
        audience_context_disposition="created",
        snapshot_series_id="series_created",
        snapshot_series_disposition="created",
        snapshot_build_request_id="request_created",
        snapshot_build_request_disposition="created",
        snapshot_build_plan_id="plan_created",
        snapshot_build_plan_disposition="created",
        request_idempotency_key="current_portfolio_build:" + "a" * 64,
    )


def _completion_plan() -> SnapshotBuildPlan:
    entry = _entry()
    export_plan = SnapshotExportPlan(
        export_plan_id="export_plan_exact",
        export_format="directory_package",
        export_contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="5" * 64),
    )
    request = _request(
        "request_created",
        "series_created",
        "audience_created",
        "current_portfolio_build:" + "a" * 64,
    )
    return _plan(
        "plan_created",
        request,
        (entry,),
        (export_plan,),
        (),
    )


def _patch_completion_context(
    monkeypatch: pytest.MonkeyPatch, plan: SnapshotBuildPlan
) -> None:
    import vitrine.current_portfolio_execution as module

    monkeypatch.setattr(
        module,
        "_completion_context",
        lambda *_args, **_kwargs: (plan, SnapshotRendererRegistry(), ()),
    )



def test_full_prepared_executor_shares_one_provider_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    prepared = _preparation()
    plan_result = _plan_execution()
    registry = SnapshotSourceProviderRegistry()
    calls: list[tuple[str, object]] = []
    sentinel = object()

    def freeze_plan(*_args, **kwargs):
        calls.append(("plan", kwargs["source_providers"]))
        return plan_result

    def complete(*_args, **kwargs):
        calls.append(("complete", kwargs["source_providers"]))
        assert _args[1] is plan_result
        assert kwargs["actor"] is ACTOR
        return sentinel

    monkeypatch.setattr(module, "execute_prepared_current_portfolio_plan", freeze_plan)
    monkeypatch.setattr(module, "execute_current_portfolio_build_export", complete)

    result = execute_prepared_current_portfolio_build(
        ".",
        prepared,
        actor=ACTOR,
        authority_gate=SimpleNamespace(),
        source_providers=registry,
    )

    assert result is sentinel
    assert calls == [("plan", registry), ("complete", registry)]

def test_completion_threads_attempt_seal_verify_and_export_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    plan_execution = _plan_execution()
    _patch_completion_context(monkeypatch, plan)
    calls: list[tuple[str, int | None]] = []

    def start(*_args, **kwargs):
        calls.append(("attempt", kwargs["expected_state_revision"]))
        return SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_1", attempt_number=1
            ),
        )

    def execute(*_args, **kwargs):
        calls.append(("materialize", kwargs["expected_state_revision"]))
        return SimpleNamespace(state_revision=15)

    def seal(*_args, **kwargs):
        calls.append(("seal", kwargs["expected_state_revision"]))
        return SimpleNamespace(
            state_revision=16,
            edition=SimpleNamespace(edition_number=1),
            attempt_result=SimpleNamespace(terminal_outcome="sealed"),
        )

    def verify_edition(*_args, **_kwargs):
        calls.append(("verify_edition", None))
        return SimpleNamespace(
            manifest_digest=DigestReference(value="b" * 64),
            logical_inventory_digest=DigestReference(value="c" * 64),
        )

    def export(*_args, **kwargs):
        calls.append(("export", kwargs["expected_state_revision"]))
        return SimpleNamespace(
            state_revision=17,
            export_artifact=SimpleNamespace(
                snapshot_export_artifact_id="export_artifact_1"
            ),
            export_path=Path("exports/exact"),
        )

    def verify_export(*_args, **_kwargs):
        calls.append(("verify_export", None))
        return SimpleNamespace(
            directory_inventory_digest=DigestReference(value="d" * 64)
        )

    monkeypatch.setattr(module, "start_snapshot_build_attempt", start)
    monkeypatch.setattr(module, "execute_snapshot_build_attempt", execute)
    monkeypatch.setattr(module, "seal_snapshot_build_attempt", seal)
    monkeypatch.setattr(module, "verify_snapshot_edition", verify_edition)
    monkeypatch.setattr(module, "create_snapshot_directory_export", export)
    monkeypatch.setattr(module, "verify_snapshot_export", verify_export)

    result = execute_current_portfolio_build_export(
        ".",
        plan_execution,
        actor=ACTOR,
        authority_gate=SimpleNamespace(),
    )

    assert calls == [
        ("attempt", 14),
        ("materialize", 15),
        ("seal", 15),
        ("verify_edition", None),
        ("export", 16),
        ("verify_export", None),
    ]
    assert result.state_revision == 17
    assert result.snapshot_build_attempt_id == "attempt_1"
    assert result.edition_number == 1
    assert result.snapshot_export_artifact_id == "export_artifact_1"
    assert result.export_disposition == "created"
    assert result.current_pointer_advanced is False



def test_completion_context_uses_exact_frozen_reflection_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    entry = replace(
        _entry(),
        renderer_configuration_digest=(
            current_portfolio_reflection_configuration_digest()
        ),
    )
    export_plan = SnapshotExportPlan(
        export_plan_id="export_plan_exact",
        export_format="directory_package",
        export_contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="5" * 64),
    )
    request = _request(
        "request_created",
        "series_created",
        "audience_created",
        "current_portfolio_build:" + "a" * 64,
    )
    plan = _plan("plan_created", request, (entry,), (export_plan,), ())

    def reflection(revision: int, content: str) -> PortfolioReflection:
        return PortfolioReflection(
            reflection_id="reflection_1",
            reflection_revision=revision,
            portfolio_id="portfolio_1",
            portfolio_subject_id="subject_1",
            profile_binding_id="binding_1",
            profile_revision=PROFILE,
            reflection_requirement_id="reflection_requirement",
            prompt_id="prompt_1",
            prompt_version=str(revision),
            prompt_snapshot="What changed?",
            author=ACTOR,
            target_scope="portfolio",
            target_references=(
                CurationTargetRef(
                    target_kind="portfolio",
                    target_id="portfolio_1",
                ),
            ),
            content_mode="inline_text",
            language="en",
            content_format="plain_text",
            content=content,
            created_at=NOW,
            predecessor_reflection_revision=(
                None if revision == 1 else revision - 1
            ),
        )

    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (
            SimpleNamespace(state_revision=14),
            (plan, reflection(1, "frozen revision"), reflection(2, "successor")),
        ),
    )

    loaded_plan, renderers, prior_attempt_ids = module._completion_context(
        ".", _plan_execution()
    )
    renderer = renderers.select(entry)
    rendered = renderer.render(
        SnapshotRenderRequest(
            snapshot_build_plan_id=loaded_plan.snapshot_build_plan_id,
            snapshot_build_attempt_id="attempt_1",
            entry_plan=entry,
        )
    )

    assert prior_attempt_ids == ()
    assert rendered.content == b"frozen revision"


def test_attempt_start_failure_reports_exact_durable_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)

    def fail_start(*_args, **_kwargs):
        raise SnapshotWorkflowError(
            "snapshot.staging_conflict",
            "synthetic staging failure after Attempt persistence",
            stage="staging",
        )

    monkeypatch.setattr(module, "start_snapshot_build_attempt", fail_start)
    monkeypatch.setattr(
        module,
        "_recover_started_attempt_id",
        lambda *_args, **_kwargs: "attempt_persisted",
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == "current_portfolio_build.attempt_start_failed"
    assert captured.value.snapshot_build_attempt_id == "attempt_persisted"
    assert "build_attempt" in captured.value.completed_stages
    assert captured.value.underlying_code == "snapshot.staging_conflict"
    assert captured.value.underlying_stage == "staging"
    assert captured.value.next_safe_action == "inspect_snapshot_recovery"


def test_completion_authority_denial_preserves_attempt_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_denied", attempt_number=1
            ),
        ),
    )

    def deny(*_args, **_kwargs):
        raise SnapshotWorkflowError(
            "snapshot.authority_denied",
            "synthetic denial",
            stage="authority",
        )

    monkeypatch.setattr(module, "execute_snapshot_build_attempt", deny)
    monkeypatch.setattr(
        module,
        "seal_snapshot_build_attempt",
        lambda *_args, **_kwargs: pytest.fail("seal must not run"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == (
        "current_portfolio_build.snapshot_authority_denied"
    )
    assert captured.value.underlying_code == "snapshot.authority_denied"
    assert captured.value.snapshot_build_attempt_id == "attempt_denied"
    assert "build_attempt" in captured.value.completed_stages
    assert captured.value.next_safe_action == "review_snapshot_build_authority"



@pytest.mark.parametrize(
    ("provider_stage", "expected_code"),
    (
        (
            "quillan_artifact_authorization_denied",
            "current_portfolio_build.producer_artifact_authorization_denied",
        ),
        (
            "concord_artifact_authorization_unresolved",
            "current_portfolio_build.producer_artifact_authorization_unresolved",
        ),
    ),
)
def test_producer_artifact_authorization_failure_is_distinguished(
    monkeypatch: pytest.MonkeyPatch,
    provider_stage: str,
    expected_code: str,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_producer_auth",
                attempt_number=1,
            ),
        ),
    )

    def fail_authorization(*_args, **_kwargs):
        cause = SnapshotMaterializationError(
            "snapshot.source_unavailable",
            "synthetic producer authorization failure",
            stage=provider_stage,
        )
        raise SnapshotWorkflowError(
            "snapshot.materialization_failed",
            "synthetic materialization wrapper",
            stage=provider_stage,
        ) from cause

    monkeypatch.setattr(
        module,
        "execute_snapshot_build_attempt",
        fail_authorization,
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == expected_code
    assert captured.value.underlying_code == "snapshot.source_unavailable"
    assert captured.value.underlying_stage == provider_stage
    assert captured.value.snapshot_build_attempt_id == "attempt_producer_auth"
    assert captured.value.next_safe_action == (
        "review_producer_artifact_authorization"
    )


def test_export_failure_reports_sealed_edition_resume_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_1", attempt_number=1
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "execute_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=15),
    )
    monkeypatch.setattr(
        module,
        "seal_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=16,
            edition=SimpleNamespace(edition_number=3),
            attempt_result=SimpleNamespace(terminal_outcome="sealed"),
        ),
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_edition",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest_digest=DigestReference(value="b" * 64),
            logical_inventory_digest=DigestReference(value="c" * 64),
        ),
    )

    def fail_export(*_args, **_kwargs):
        raise SnapshotDistributionError(
            "snapshot_distribution.export_failed",
            "synthetic export failure",
            stage="export",
        )

    monkeypatch.setattr(module, "create_snapshot_directory_export", fail_export)

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == "current_portfolio_build.export_failed"
    assert captured.value.edition_number == 3
    assert captured.value.snapshot_build_attempt_id == "attempt_1"
    assert "snapshot_edition" in captured.value.completed_stages
    assert "edition_verification" in captured.value.completed_stages
    assert captured.value.next_safe_action == (
        "inspect_snapshot_custody_then_resume_export"
    )



def test_export_verification_failure_preserves_artifact_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_1", attempt_number=1
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "execute_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=15),
    )
    monkeypatch.setattr(
        module,
        "seal_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=16,
            edition=SimpleNamespace(edition_number=3),
            attempt_result=SimpleNamespace(terminal_outcome="sealed"),
        ),
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_edition",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest_digest=DigestReference(value="b" * 64),
            logical_inventory_digest=DigestReference(value="c" * 64),
        ),
    )
    monkeypatch.setattr(
        module,
        "create_snapshot_directory_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=17,
            export_artifact=SimpleNamespace(
                snapshot_export_artifact_id="export_artifact_1"
            ),
            export_path=Path("exports/exact"),
        ),
    )

    def fail_verification(*_args, **_kwargs):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "synthetic export verification failure",
            stage="export_verification",
        )

    monkeypatch.setattr(module, "verify_snapshot_export", fail_verification)

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == (
        "current_portfolio_build.export_verification_failed"
    )
    assert captured.value.snapshot_export_artifact_id == "export_artifact_1"
    assert "snapshot_export_artifact" in captured.value.completed_stages
    assert captured.value.next_safe_action == "inspect_snapshot_custody"

def test_resume_export_reuses_exact_existing_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    monkeypatch.setattr(
        module,
        "verify_snapshot_edition",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        module,
        "create_snapshot_directory_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=20,
            export_artifact=SimpleNamespace(
                snapshot_export_artifact_id="export_existing"
            ),
            export_path=Path("exports/existing"),
        ),
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            directory_inventory_digest=DigestReference(value="e" * 64)
        ),
    )

    result = resume_current_portfolio_export(
        ".",
        snapshot_series_id="series_created",
        edition_number=2,
        export_plan_id="export_plan_exact",
        expected_state_revision=20,
    )

    assert result.export_disposition == "existing"
    assert result.snapshot_export_artifact_id == "export_existing"
    assert result.state_revision == 20


def _copied_plan_for_provider(
    *,
    provider_id: str,
    provider_version: str,
) -> tuple[SnapshotBuildPlan, SnapshotSourceProviderDescriptor]:
    import vitrine.current_portfolio_build as build_module

    artifact = SourceArtifactReference(
        artifact_id="artifact_1",
        artifact_kind="original_student_work",
        representation_kind="quillan:selected_student_work",
        media_type="application/pdf",
        source_locator=None,
        native_revision="1",
        source_digest=None,
        byte_size=None,
        language=None,
        accessibility_relationship=None,
    )
    semantic = build_module._entry_semantic_value(
        preparation=SimpleNamespace(
            portfolio_id="portfolio_1",
            portfolio_subject_id="subject_1",
            profile_binding_id="binding_1",
            profile_revision_id=PROFILE.portfolio_profile_id,
            profile_revision_number=PROFILE.profile_revision,
            current_composition_revision=2,
        ),
        section_id="work",
        section_order=1,
        position_in_section=1,
        placement_id="placement_1",
        selection_id="selection_1",
        candidate_id="candidate_1",
        candidate_evaluation_id="evaluation_1",
        publication_id="publication_1",
        producer_module_id="quillan",
        projection_kind=artifact.representation_kind,
        projection_contract_version="projection_v1",
        artifact=artifact,
    )
    entry_id = build_module._final_entry_id(
        semantic,
        materialization_kind="copied_source",
        provider_disposition="exact_provider",
        provider_id=provider_id,
        provider_version=provider_version,
        omission_reason=None,
    )
    entry = SnapshotEntryPlan(
        entry_plan_id=entry_id,
        plan_position=1,
        section_id="work",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="selection_1",
        placement_id="placement_1",
        candidate_id="candidate_1",
        candidate_evaluation_id="evaluation_1",
        source_publication_id="publication_1",
        producer_module_id="quillan",
        projection_kind=artifact.representation_kind,
        projection_contract_version="projection_v1",
        source_artifact=artifact,
        target_relative_path="section-01/01-entry.pdf",
        media_type="application/pdf",
    )
    export_plan = SnapshotExportPlan(
        export_plan_id="export_plan_copy",
        export_format="directory_package",
        export_contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="f" * 64),
    )
    request = _request(
        "request_created",
        "series_created",
        "audience_created",
        "current_portfolio_build:" + "a" * 64,
    )
    plan = _plan("plan_created", request, (entry,), (export_plan,), ())
    descriptor = SnapshotSourceProviderDescriptor(
        provider_id=provider_id,
        provider_version=provider_version,
        producer_module_id="quillan",
        projection_kind=artifact.representation_kind,
        projection_contract_version="projection_v1",
        artifact_kind=artifact.artifact_kind,
        representation_kind=artifact.representation_kind,
    )
    return plan, descriptor


def _provider_registry(
    descriptor: SnapshotSourceProviderDescriptor,
) -> SnapshotSourceProviderRegistry:
    class Provider:
        @property
        def descriptor(self):
            return descriptor

        def resolve(self, request):
            raise AssertionError(request)

        def confirm_stability(self, request, result):
            raise AssertionError((request, result))

    return SnapshotSourceProviderRegistry((Provider(),))


def _patch_copied_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    class ExactProfile:
        reference = PROFILE
        sections = (SimpleNamespace(section_id="work", order=1),)

    monkeypatch.setattr(module, "PortfolioProfileRevision", ExactProfile)
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (
            SimpleNamespace(state_revision=14),
            (ExactProfile(),),
        ),
    )


def test_exact_committed_provider_passes_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan, descriptor = _copied_plan_for_provider(
        provider_id="provider_exact",
        provider_version="1",
    )
    _patch_completion_context(monkeypatch, plan)
    _patch_copied_profile(monkeypatch)
    starts: list[str] = []

    def stop_after_preflight(*_args, **_kwargs):
        starts.append("attempt")
        raise SnapshotWorkflowError(
            "snapshot.attempt_conflict",
            "synthetic stop after provider preflight",
            stage="attempt",
        )

    monkeypatch.setattr(module, "start_snapshot_build_attempt", stop_after_preflight)

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
            source_providers=_provider_registry(descriptor),
        )

    assert captured.value.code == "current_portfolio_build.attempt_start_failed"
    assert starts == ["attempt"]


def test_provider_identity_change_fails_before_attempt_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan, _old_descriptor = _copied_plan_for_provider(
        provider_id="provider_old",
        provider_version="1",
    )
    _new_plan, new_descriptor = _copied_plan_for_provider(
        provider_id="provider_new",
        provider_version="2",
    )
    _patch_completion_context(monkeypatch, plan)
    _patch_copied_profile(monkeypatch)
    starts: list[str] = []
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: starts.append("attempt"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
            source_providers=_provider_registry(new_descriptor),
        )

    assert captured.value.code == "current_portfolio_build.materialization_failed"
    assert captured.value.underlying_code == "snapshot.source_provider_conflict"
    assert captured.value.underlying_stage == "provider_selection"
    assert starts == []


def test_completion_state_drift_stops_before_attempt_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    starts: list[str] = []
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=15), (plan,)),
    )
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: starts.append("attempt"),
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(state_revision=14),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == (
        "current_portfolio_build.execution_state_conflict"
    )
    assert captured.value.stage == "attempt_preflight"
    assert starts == []


def test_post_seal_conflict_reports_only_exact_recoverable_edition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    plan = _completion_plan()
    _patch_completion_context(monkeypatch, plan)
    monkeypatch.setattr(
        module,
        "start_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(
            state_revision=15,
            attempt=SimpleNamespace(
                snapshot_build_attempt_id="attempt_1", attempt_number=1
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "execute_snapshot_build_attempt",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=15),
    )

    def fail_after_seal(*_args, **_kwargs):
        raise SnapshotWorkflowError(
            "snapshot.post_seal_state_conflict",
            "synthetic post-seal conflict",
            stage="post_seal_concurrency",
        )

    monkeypatch.setattr(module, "seal_snapshot_build_attempt", fail_after_seal)
    monkeypatch.setattr(
        module,
        "_recover_post_seal_edition_number",
        lambda *_args, **_kwargs: 4,
    )

    with pytest.raises(CurrentPortfolioExecutionError) as captured:
        execute_current_portfolio_build_export(
            ".",
            _plan_execution(),
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert captured.value.code == "current_portfolio_build.sealing_failed"
    assert captured.value.underlying_code == "snapshot.post_seal_state_conflict"
    assert captured.value.edition_number == 4
    assert "snapshot_edition_sealed" in captured.value.completed_stages
    assert captured.value.next_safe_action == "inspect_post_seal_recovery"
