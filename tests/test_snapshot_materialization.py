from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    ProfileRevisionRef,
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SourceArtifactReference,
)
from vitrine.snapshot_custody import create_snapshot_staging
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotCopiedBytesResult,
    SnapshotGeneratedBytesResult,
    SnapshotMaterializationError,
    SnapshotRendererDescriptor,
    SnapshotRendererRegistry,
    SnapshotRenderRequest,
    SnapshotRenderResult,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
    copy_planned_source_to_staging,
    render_planned_entry_to_staging,
)
from vitrine.snapshot_state import snapshot_plan_fingerprint

NOW = datetime(2026, 8, 12, 20, 0, tzinfo=timezone.utc)
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
RENDER_CONFIG = DigestReference(value="2" * 64)
EXPORT_CONFIG = DigestReference(value="3" * 64)


def _sha(value: bytes) -> DigestReference:
    return DigestReference(value=hashlib.sha256(value).hexdigest())


def _copied_entry(payload: bytes) -> SnapshotEntryPlan:
    source_digest = _sha(payload)
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_work",
        plan_position=1,
        section_id="baseline",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="selection_work",
        placement_id="placement_work",
        candidate_id="candidate_work",
        candidate_evaluation_id="candidate_evaluation_work",
        source_publication_id="publication_work",
        producer_module_id="vitrine_quillan_fixture",
        projection_kind="student_work",
        projection_contract_version="fixture_projection_v1",
        source_artifact=SourceArtifactReference(
            artifact_id="artifact_work",
            artifact_kind="original_student_work",
            representation_kind="student_work",
            media_type="text/plain",
            source_locator="approved/work.txt",
            native_revision=1,
            source_digest=source_digest,
            byte_size=len(payload),
            language="en",
            accessibility_relationship=None,
        ),
        producer_source_digest_claim=source_digest,
        target_relative_path="baseline/01-work.txt",
        media_type="text/plain",
    )


def _generated_entry() -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_reflection",
        plan_position=2,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="reflection/01-reflection.md",
        media_type="text/markdown",
        renderer_id="vitrine_reflection_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_reflection_v1",
        renderer_configuration_digest=RENDER_CONFIG,
        input_references=(
            SnapshotInputReference(
                record_type="portfolio_reflection",
                record_id="reflection_1",
                record_revision=1,
            ),
        ),
    )


def _plan(payload: bytes) -> SnapshotBuildPlan:
    entries = (_copied_entry(payload), _generated_entry())
    provisional = SnapshotBuildPlan(
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
        entry_plans=entries,
        export_plans=(
            SnapshotExportPlan(
                export_plan_id="directory_export_plan_1",
                export_format="directory_package",
                export_contract_version="snapshot_directory_v1",
                included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
                excluded_entry_plan_ids=(),
                configuration_digest=EXPORT_CONFIG,
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
    return replace(provisional, plan_fingerprint=snapshot_plan_fingerprint(provisional))


def _attempt(plan: SnapshotBuildPlan) -> SnapshotBuildAttempt:
    return SnapshotBuildAttempt(
        snapshot_build_attempt_id="snapshot_attempt_1",
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        attempt_number=1,
        builder_id="snapshot_builder",
        builder_version="1",
        started_at=NOW,
        staging_reference="staging_snapshot_attempt_1",
        started_by=ACTOR,
    )


class _AuthorityGate:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.calls = 0

    def authorize(self, request: object) -> SnapshotBuildAuthorityDecision:
        self.calls += 1
        return SnapshotBuildAuthorityDecision(
            outcome=self.outcome,
            authority_reference="fixture_authority" if self.outcome == "allowed" else None,
        )


class _FileProvider:
    descriptor = SnapshotSourceProviderDescriptor(
        provider_id="quillan_fixture_source_provider",
        provider_version="1",
        producer_module_id="vitrine_quillan_fixture",
        projection_kind="student_work",
        projection_contract_version="fixture_projection_v1",
        artifact_kind="original_student_work",
        representation_kind="student_work",
    )

    def __init__(self, root: Path, *, mutate_during_stability: bool = False) -> None:
        self.root = root
        self.mutate_during_stability = mutate_during_stability
        self.resolve_calls = 0

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotSourceResult:
        self.resolve_calls += 1
        return SnapshotSourceResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id="publication_work",
            source_artifact_id="artifact_work",
            source_root=self.root,
            source_relative_path="approved/work.txt",
        )

    def confirm_stability(
        self, request: SnapshotSourceRequest, result: SnapshotSourceResult
    ) -> bool:
        if self.mutate_during_stability:
            (self.root / result.source_relative_path).write_bytes(b"changed source\n")
        return True


class _Renderer:
    descriptor = SnapshotRendererDescriptor(
        renderer_id="vitrine_reflection_renderer",
        renderer_version="1",
        renderer_contract_version="snapshot_reflection_v1",
    )

    def __init__(self) -> None:
        self.calls = 0

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        self.calls += 1
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=b"# Reflection\n\nExact revision 1.\n",
            media_type="text/markdown",
            configuration_digest=RENDER_CONFIG,
            template_digest=None,
            language="en",
        )


def test_exact_copy_preserves_independent_digest_layers(tmp_path: Path) -> None:
    payload = b"approved student work\n"
    source_root = tmp_path / "producer"
    source_file = source_root / "approved" / "work.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(payload)

    plan = _plan(payload)
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)
    gate = _AuthorityGate("allowed")
    provider = _FileProvider(source_root.resolve())

    result = copy_planned_source_to_staging(
        plan=plan,
        attempt=attempt,
        entry_plan_id="entry_plan_work",
        staging=staging,
        authority_gate=gate,
        source_providers=SnapshotSourceProviderRegistry((provider,)),
    )

    assert isinstance(result, SnapshotCopiedBytesResult)
    assert result.acquired_source_digest == _sha(payload)
    assert result.copied_output_digest == _sha(payload)
    assert result.byte_size == len(payload)
    assert staging.content_path(result.target_relative_path).read_bytes() == payload
    assert gate.calls == 1
    assert provider.resolve_calls == 1


def test_denied_authority_reads_no_source_content(tmp_path: Path) -> None:
    payload = b"approved student work\n"
    source_root = tmp_path / "producer"
    source_file = source_root / "approved" / "work.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(payload)
    plan = _plan(payload)
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)
    provider = _FileProvider(source_root.resolve())

    with pytest.raises(SnapshotMaterializationError) as captured:
        copy_planned_source_to_staging(
            plan=plan,
            attempt=attempt,
            entry_plan_id="entry_plan_work",
            staging=staging,
            authority_gate=_AuthorityGate("denied"),
            source_providers=SnapshotSourceProviderRegistry((provider,)),
        )
    assert captured.value.code == "snapshot.authority_denied"
    assert provider.resolve_calls == 0
    assert not any(staging.content_root.rglob("*"))


def test_missing_exact_provider_fails_closed(tmp_path: Path) -> None:
    payload = b"approved student work\n"
    plan = _plan(payload)
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)

    with pytest.raises(SnapshotMaterializationError) as captured:
        copy_planned_source_to_staging(
            plan=plan,
            attempt=attempt,
            entry_plan_id="entry_plan_work",
            staging=staging,
            authority_gate=_AuthorityGate("allowed"),
            source_providers=SnapshotSourceProviderRegistry(),
        )
    assert captured.value.code == "snapshot.source_provider_missing"


def test_source_mutation_during_acquisition_fails_closed(tmp_path: Path) -> None:
    payload = b"approved student work\n"
    source_root = tmp_path / "producer"
    source_file = source_root / "approved" / "work.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(payload)
    plan = _plan(payload)
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)

    with pytest.raises(SnapshotMaterializationError) as captured:
        copy_planned_source_to_staging(
            plan=plan,
            attempt=attempt,
            entry_plan_id="entry_plan_work",
            staging=staging,
            authority_gate=_AuthorityGate("allowed"),
            source_providers=SnapshotSourceProviderRegistry(
                (_FileProvider(source_root.resolve(), mutate_during_stability=True),)
            ),
        )
    assert captured.value.code == "snapshot.source_changed_during_acquisition"
    assert not staging.content_path("baseline/01-work.txt").exists()


def test_generated_entry_requires_exact_renderer_configuration(tmp_path: Path) -> None:
    payload = b"approved student work\n"
    plan = _plan(payload)
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)
    renderer = _Renderer()

    result = render_planned_entry_to_staging(
        plan=plan,
        attempt=attempt,
        entry_plan_id="entry_plan_reflection",
        staging=staging,
        authority_gate=_AuthorityGate("allowed"),
        renderers=SnapshotRendererRegistry((renderer,)),
    )

    assert isinstance(result, SnapshotGeneratedBytesResult)
    assert result.configuration_digest == RENDER_CONFIG
    assert result.output_digest == _sha(b"# Reflection\n\nExact revision 1.\n")
    assert renderer.calls == 1
    assert staging.content_path(result.target_relative_path).read_bytes() == (
        b"# Reflection\n\nExact revision 1.\n"
    )
