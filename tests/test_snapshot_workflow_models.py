from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from vitrine.models.common import SCHEMA_VERSION
from vitrine.models.errors import VitrineModelValidationError
from vitrine.models.identity import (
    ActorAttribution,
    DigestReference,
    ProfileRevisionRef,
    SnapshotEditionRef,
)
from vitrine.models.snapshot_workflow import (
    SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE,
    SNAPSHOT_BUILD_PLAN_RECORD_TYPE,
    SNAPSHOT_BUILD_REQUEST_RECORD_TYPE,
    SNAPSHOT_SERIES_RECORD_TYPE,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryOutcome,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotSeries,
)
from vitrine.snapshot_state import snapshot_plan_fingerprint

NOW = datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="snapshot_fixture_teacher",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_snapshot_fixture",
    profile_revision=1,
)
CONFIG_DIGEST = DigestReference(value="1" * 64)


def _generated_entry(*, path: str = "01-reflection.md") -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_reflection",
        plan_position=1,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path=path,
        media_type="text/markdown",
        renderer_id="vitrine_reflection_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_reflection_v1",
        renderer_configuration_digest=DigestReference(value="2" * 64),
        input_references=(
            SnapshotInputReference(
                record_type="working_portfolio_composition_revision",
                record_id="portfolio_snapshot_fixture",
                record_revision=1,
            ),
        ),
    )


def _request() -> SnapshotBuildRequest:
    return SnapshotBuildRequest(
        snapshot_build_request_id="snapshot_request_1",
        snapshot_series_id="snapshot_series_1",
        portfolio_id="portfolio_snapshot_fixture",
        portfolio_subject_id="subject_snapshot_fixture",
        profile_binding_id="profile_binding_snapshot_fixture",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_snapshot_fixture",
        snapshot_purpose="improvement",
        requested_export_formats=("directory_package",),
        requested_by=ACTOR,
        requested_at=NOW,
        idempotency_key="snapshot-request-retry-1",
    )


def _plan(*, fingerprint: str = "0" * 64) -> SnapshotBuildPlan:
    entry = _generated_entry()
    return SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_1",
        snapshot_build_request_id="snapshot_request_1",
        snapshot_series_id="snapshot_series_1",
        plan_revision=1,
        portfolio_id="portfolio_snapshot_fixture",
        portfolio_subject_id="subject_snapshot_fixture",
        profile_binding_id="profile_binding_snapshot_fixture",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_snapshot_fixture",
        entry_plans=(entry,),
        export_plans=(
            SnapshotExportPlan(
                export_plan_id="directory_export_plan_1",
                export_format="directory_package",
                export_contract_version="snapshot_directory_v1",
                included_entry_plan_ids=(entry.entry_plan_id,),
                excluded_entry_plan_ids=(),
                configuration_digest=CONFIG_DIGEST,
            ),
        ),
        required_review_references=(),
        acknowledged_obligation_codes=(),
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        builder_contract_id="snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint=fingerprint,
    )


def test_snapshot_control_plane_models_have_additive_record_envelopes() -> None:
    series = SnapshotSeries(
        snapshot_series_id="snapshot_series_1",
        portfolio_id="portfolio_snapshot_fixture",
        portfolio_subject_id="subject_snapshot_fixture",
        snapshot_purpose="improvement",
        audience_context_id="audience_snapshot_fixture",
        created_at=NOW,
        created_by=ACTOR,
    )
    request = _request()
    plan = _plan()

    assert (series.schema_version, series.record_type) == (
        SCHEMA_VERSION,
        SNAPSHOT_SERIES_RECORD_TYPE,
    )
    assert request.record_type == SNAPSHOT_BUILD_REQUEST_RECORD_TYPE
    assert plan.record_type == SNAPSHOT_BUILD_PLAN_RECORD_TYPE


def test_generated_entry_plan_requires_exact_renderer_inputs_without_source_claims() -> None:
    valid = _generated_entry()
    assert valid.input_references[0].record_revision == 1
    assert valid.renderer_configuration_digest == DigestReference(value="2" * 64)

    with pytest.raises(
        VitrineModelValidationError,
        match="must not fabricate producer source provenance",
    ):
        replace(valid, candidate_id="candidate_not_allowed")

    with pytest.raises(
        VitrineModelValidationError,
        match="renderer_configuration_digest",
    ):
        replace(valid, renderer_configuration_digest=None)

    with pytest.raises(
        VitrineModelValidationError,
        match="cannot declare permitted omissions",
    ):
        replace(valid, permitted_omission_reason="representation_unavailable")


def test_snapshot_entry_path_rejects_uri_or_drive_style_colon_syntax() -> None:
    with pytest.raises(VitrineModelValidationError, match="colon syntax"):
        _generated_entry(path="http:artifact.md")


def test_build_plan_requires_export_to_partition_the_complete_entry_inventory() -> None:
    entry = _generated_entry()
    second = replace(
        entry,
        entry_plan_id="entry_plan_index",
        plan_position=2,
        ordinal=2,
        semantic_role="index",
        target_relative_path="02-index.md",
    )
    export = SnapshotExportPlan(
        export_plan_id="directory_export_plan_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=CONFIG_DIGEST,
    )

    with pytest.raises(VitrineModelValidationError, match="complete Entry Plan inventory"):
        replace(_plan(), entry_plans=(entry, second), export_plans=(export,))


def test_plan_fingerprint_excludes_only_the_fingerprint_field() -> None:
    plan = _plan()
    digest = snapshot_plan_fingerprint(plan)
    finalized = replace(plan, plan_fingerprint=digest)

    assert len(digest) == 64
    assert snapshot_plan_fingerprint(finalized) == digest
    assert snapshot_plan_fingerprint(replace(finalized, planned_at=NOW)) == digest


def test_attempt_result_is_separate_and_failed_result_cannot_claim_edition() -> None:
    failed = SnapshotBuildAttemptResult(
        snapshot_build_attempt_result_id="snapshot_attempt_result_1",
        snapshot_build_attempt_id="snapshot_attempt_1",
        completed_at=NOW,
        terminal_outcome="failed",
        entry_outcomes=(
            SnapshotEntryOutcome(
                entry_plan_id="entry_plan_reflection",
                disposition="failed_blocking",
                finding_codes=("snapshot.render_failed",),
            ),
        ),
    )
    assert failed.record_type == SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE
    assert failed.sealed_snapshot_edition is None

    with pytest.raises(VitrineModelValidationError, match="must not claim an Edition"):
        replace(
            failed,
            sealed_snapshot_edition=SnapshotEditionRef(
                snapshot_series_id="snapshot_series_1",
                edition_number=1,
            ),
        )
