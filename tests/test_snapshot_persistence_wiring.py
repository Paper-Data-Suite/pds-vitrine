from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

import vitrine.storage as storage
from vitrine.models import (
    ActorAttribution,
    DigestReference,
    Portfolio,
    ProfileRevisionRef,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotSeries,
    record_from_dict,
    record_to_dict,
)
from vitrine.record_registry import descriptor_for_record_type
from vitrine.snapshot_state import snapshot_plan_fingerprint
from vitrine.storage import VitrineStorageValidationError
from vitrine.storage.store import key_for_record

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


def _request() -> SnapshotBuildRequest:
    return SnapshotBuildRequest(
        snapshot_build_request_id="snapshot_request_registry",
        snapshot_series_id="snapshot_series_registry",
        portfolio_id="portfolio_snapshot_registry",
        portfolio_subject_id="subject_snapshot_registry",
        profile_binding_id="profile_binding_snapshot_registry",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_snapshot_registry",
        snapshot_purpose="improvement",
        requested_export_formats=("directory_package",),
        requested_by=ACTOR,
        requested_at=NOW,
    )


def _plan() -> SnapshotBuildPlan:
    entry = SnapshotEntryPlan(
        entry_plan_id="entry_plan_registry",
        plan_position=1,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="01-reflection.md",
        media_type="text/markdown",
        renderer_id="vitrine_reflection_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_reflection_v1",
        renderer_configuration_digest=DigestReference(value="2" * 64),
        input_references=(
            SnapshotInputReference(
                record_type="working_portfolio_composition_revision",
                record_id="portfolio_snapshot_registry",
                record_revision=1,
            ),
        ),
    )
    provisional = SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_registry",
        snapshot_build_request_id="snapshot_request_registry",
        snapshot_series_id="snapshot_series_registry",
        plan_revision=1,
        portfolio_id="portfolio_snapshot_registry",
        portfolio_subject_id="subject_snapshot_registry",
        profile_binding_id="profile_binding_snapshot_registry",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_snapshot_registry",
        entry_plans=(entry,),
        export_plans=(
            SnapshotExportPlan(
                export_plan_id="directory_export_plan_registry",
                export_format="directory_package",
                export_contract_version="snapshot_directory_v1",
                included_entry_plan_ids=(entry.entry_plan_id,),
                excluded_entry_plan_ids=(),
                configuration_digest=DigestReference(value="1" * 64),
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
        plan_fingerprint="0" * 64,
    )
    return replace(
        provisional,
        plan_fingerprint=snapshot_plan_fingerprint(provisional),
    )


def test_snapshot_workflow_top_level_records_are_additive_registry_families() -> None:
    expected = {
        "snapshot_series": (("snapshot_series_id",), ()),
        "snapshot_build_request": (("snapshot_build_request_id",), ()),
        "snapshot_build_plan": (("snapshot_build_plan_id",), ()),
        "snapshot_build_attempt": (("snapshot_build_attempt_id",), ()),
        "snapshot_build_attempt_result": (("snapshot_build_attempt_result_id",), ()),
        "snapshot_materialization_provenance": (
            ("snapshot_materialization_provenance_id",),
            (),
        ),
        "snapshot_edition_build_provenance": (
            ("snapshot_edition_build_provenance_id",),
            (),
        ),
        "snapshot_export_artifact": (("snapshot_export_artifact_id",), ()),
        "snapshot_current_pointer_revision": (
            ("snapshot_current_pointer_id", "pointer_revision"),
            ("pointer_revision",),
        ),
    }

    for record_type, (identity_fields, integer_fields) in expected.items():
        descriptor = descriptor_for_record_type(record_type)
        assert descriptor.graph_collection is None
        assert descriptor.identity_fields == identity_fields
        assert descriptor.integer_identity_fields == integer_fields


def test_snapshot_plan_round_trips_through_authoritative_record_conversion() -> None:
    plan = _plan()

    encoded = record_to_dict(plan)
    decoded = record_from_dict(encoded)

    assert decoded == plan
    assert isinstance(decoded, SnapshotBuildPlan)
    assert decoded.entry_plans[0].input_references[0].record_revision == 1


def test_snapshot_record_identity_uses_authoritative_registry() -> None:
    request = _request()

    key = key_for_record(request)

    assert key.record_type == "snapshot_build_request"
    assert key.identity_segments == (request.snapshot_build_request_id,)


def test_public_storage_rejects_invalid_snapshot_state_before_raw_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_commit(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        return object()

    monkeypatch.setattr(storage, "_commit_record_batch", fake_commit)
    series = SnapshotSeries(
        snapshot_series_id="snapshot_series_missing_context",
        portfolio_id="portfolio_missing",
        portfolio_subject_id="subject_missing",
        snapshot_purpose="improvement",
        audience_context_id="audience_missing",
        created_at=NOW,
        created_by=ACTOR,
    )

    with pytest.raises(VitrineStorageValidationError, match="snapshot state is invalid"):
        storage.commit_record_batch(
            "unused",
            (series,),
            expected_state_revision=None,
        )

    assert called is False


def test_public_storage_keeps_unrelated_valid_commits_on_raw_storage_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()

    def fake_commit(*args: object, **kwargs: object) -> object:
        return sentinel

    monkeypatch.setattr(storage, "_commit_record_batch", fake_commit)
    portfolio = Portfolio(
        portfolio_id="portfolio_snapshot_guard_passthrough",
        portfolio_subject_id="subject_snapshot_guard_passthrough",
        created_at=NOW,
        created_by=ACTOR,
    )

    result = storage.commit_record_batch(
        "unused",
        (portfolio,),
        expected_state_revision=None,
    )

    assert result is sentinel
