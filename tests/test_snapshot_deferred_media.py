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
    SnapshotEditionRef,
    SnapshotEntry,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SourceArtifactReference,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY,
    QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY,
    QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
    quillan_review_source_id,
)
from vitrine.snapshot_custody import create_snapshot_staging
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT,
    SnapshotAuthorizedSourceBytesResult,
    SnapshotBuildAuthorityDecision,
    SnapshotCopiedBytesResult,
    SnapshotMaterializationError,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
    copy_planned_source_to_staging,
)
from vitrine.snapshot_services import (
    SnapshotAttemptExecutionResult,
    SnapshotPreparedEntry,
    _build_sealed_records,
    _logical_entry_json,
    _manifest_entry_json,
)
from vitrine.snapshot_state import snapshot_plan_fingerprint

NOW = datetime(2026, 9, 2, 22, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="quillan_slice0_teacher",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_quillan_slice0",
    profile_revision=1,
)


def _sha(payload: bytes) -> DigestReference:
    return DigestReference(value=hashlib.sha256(payload).hexdigest())


def _plan(payload: bytes, *, target_relative_path: str = "evidence/student-work") -> SnapshotBuildPlan:
    digest = _sha(payload)
    entry = SnapshotEntryPlan(
        entry_plan_id="entry_plan_quillan_student_work",
        plan_position=1,
        section_id="evidence",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="selection_quillan_student_work",
        placement_id="placement_quillan_student_work",
        candidate_id="candidate_quillan_student_work",
        candidate_evaluation_id="candidate_evaluation_quillan_student_work",
        source_publication_id="publication_quillan_student_work",
        producer_module_id="quillan",
        projection_kind="quillan:selected_student_work",
        projection_contract_version="vitrine_candidate_projection_v1",
        source_artifact=SourceArtifactReference(
            artifact_id="quillan_evidence_" + "1" * 64,
            artifact_kind="original_student_work",
            representation_kind="quillan:selected_student_work",
            media_type=QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
            source_locator=None,
            native_revision=1,
            source_digest=digest,
            byte_size=len(payload),
            language=None,
            accessibility_relationship=None,
        ),
        producer_source_digest_claim=digest,
        target_relative_path=target_relative_path,
        media_type=QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    )
    export = SnapshotExportPlan(
        export_plan_id="export_plan_quillan_slice0",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=(entry.entry_plan_id,),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="2" * 64),
    )
    provisional = SnapshotBuildPlan(
        snapshot_build_plan_id="snapshot_plan_quillan_slice0",
        snapshot_build_request_id="snapshot_request_quillan_slice0",
        snapshot_series_id="snapshot_series_quillan_slice0",
        plan_revision=1,
        portfolio_id="portfolio_quillan_slice0",
        portfolio_subject_id="subject_quillan_slice0",
        profile_binding_id="profile_binding_quillan_slice0",
        profile_revision=PROFILE,
        composition_revision=1,
        audience_context_id="audience_quillan_slice0",
        entry_plans=(entry,),
        export_plans=(export,),
        required_review_references=(),
        acknowledged_obligation_codes=(),
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        builder_contract_id="vitrine_snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint="0" * 64,
    )
    return replace(provisional, plan_fingerprint=snapshot_plan_fingerprint(provisional))


def _attempt(plan: SnapshotBuildPlan) -> SnapshotBuildAttempt:
    return SnapshotBuildAttempt(
        snapshot_build_attempt_id="snapshot_attempt_quillan_slice0",
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        attempt_number=1,
        builder_id="vitrine_snapshot_builder",
        builder_version="1",
        started_at=NOW,
        staging_reference="snapshot_attempt_quillan_slice0",
        started_by=ACTOR,
    )


class _AuthorityGate:
    def authorize(self, request: object) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="quillan_slice0_build_authority",
        )


class _DeferredMediaProvider:
    descriptor = SnapshotSourceProviderDescriptor(
        provider_id="quillan_slice0_student_work_provider",
        provider_version="quillan_slice0_student_work_provider_v1",
        producer_module_id="quillan",
        projection_kind="quillan:selected_student_work",
        projection_contract_version="vitrine_candidate_projection_v1",
        artifact_kind="original_student_work",
        representation_kind="quillan:selected_student_work",
        concrete_media_types=QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    )

    def __init__(
        self,
        payload: bytes,
        *,
        media_type: str = "image/jpeg",
        acquisition_contract_version: str = (
            SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT
        ),
    ) -> None:
        self.payload = payload
        self.media_type = media_type
        self.acquisition_contract_version = acquisition_contract_version
        self.resolve_calls = 0
        self.confirm_calls = 0

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotAuthorizedSourceBytesResult:
        self.resolve_calls += 1
        artifact = request.entry_plan.source_artifact
        assert artifact is not None
        return SnapshotAuthorizedSourceBytesResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=request.entry_plan.source_publication_id or "",
            source_artifact_id=artifact.artifact_id,
            content=self.payload,
            media_type=self.media_type,
            source_digest=_sha(self.payload),
            byte_size=len(self.payload),
            acquisition_contract_version=self.acquisition_contract_version,
        )

    def confirm_stability(
        self,
        request: SnapshotSourceRequest,
        result: SnapshotSourceResult,
    ) -> bool:
        self.confirm_calls += 1
        raise AssertionError("authorized immutable bytes must not use filesystem stability")


def _copy(
    tmp_path: Path,
    *,
    plan: SnapshotBuildPlan,
    provider: _DeferredMediaProvider,
) -> SnapshotCopiedBytesResult:
    attempt = _attempt(plan)
    staging = create_snapshot_staging(tmp_path, attempt.snapshot_build_attempt_id)
    return copy_planned_source_to_staging(
        plan=plan,
        attempt=attempt,
        entry_plan_id=plan.entry_plans[0].entry_plan_id,
        staging=staging,
        authority_gate=_AuthorityGate(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
    )


def test_deferred_authorized_media_concretizes_only_after_provider_resolution(
    tmp_path: Path,
) -> None:
    payload = b"synthetic selected student-work bytes"
    plan = _plan(payload)
    provider = _DeferredMediaProvider(payload, media_type="image/jpeg")

    result = _copy(tmp_path, plan=plan, provider=provider)

    assert plan.entry_plans[0].media_type == "application/octet-stream"
    assert plan.entry_plans[0].source_artifact is not None
    assert plan.entry_plans[0].source_artifact.media_type == "application/octet-stream"
    assert result.media_type == "image/jpeg"
    assert result.acquired_source_digest == _sha(payload)
    assert result.copied_output_digest == _sha(payload)
    assert result.source_stability_result == "not_applicable"
    assert provider.resolve_calls == 1
    assert provider.confirm_calls == 0


def test_deferred_authorized_media_rejects_unadvertised_concrete_type(
    tmp_path: Path,
) -> None:
    payload = b"synthetic selected student-work bytes"
    plan = _plan(payload)
    provider = _DeferredMediaProvider(payload, media_type="application/pdf")

    with pytest.raises(SnapshotMaterializationError) as captured:
        _copy(tmp_path, plan=plan, provider=provider)

    assert captured.value.code == "snapshot.source_integrity_failed"


def test_deferred_plan_cannot_use_legacy_exact_media_contract(tmp_path: Path) -> None:
    payload = b"synthetic selected student-work bytes"
    plan = _plan(payload)
    provider = _DeferredMediaProvider(
        payload,
        media_type="image/png",
        acquisition_contract_version=SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        _copy(tmp_path, plan=plan, provider=provider)

    assert captured.value.code == "snapshot.source_integrity_failed"


def test_deferred_media_requires_suffix_neutral_snapshot_target(tmp_path: Path) -> None:
    payload = b"synthetic selected student-work bytes"
    plan = _plan(payload, target_relative_path="evidence/student-work.png")
    provider = _DeferredMediaProvider(payload, media_type="image/tiff")

    with pytest.raises(SnapshotMaterializationError) as captured:
        _copy(tmp_path, plan=plan, provider=provider)

    assert captured.value.code == "snapshot.source_integrity_failed"


def test_concrete_media_survives_manifest_logical_inventory_and_sealed_entry(
    tmp_path: Path,
) -> None:
    payload = b"synthetic selected student-work bytes"
    plan = _plan(payload)
    copied = _copy(tmp_path, plan=plan, provider=_DeferredMediaProvider(payload))
    attempt = _attempt(plan)
    prepared = SnapshotPreparedEntry(
        entry_plan_id=plan.entry_plans[0].entry_plan_id,
        disposition="prepared_bytes",
        copied_bytes=copied,
    )

    manifest_projection = _manifest_entry_json(
        plan.entry_plans[0],
        prepared,
        materialization_id="snapshot_materialization_preview",
        snapshot_entry_id="snapshot_entry_preview",
        snapshot_omission_id=None,
    )
    logical_projection = _logical_entry_json(plan.entry_plans[0], prepared)
    assert manifest_projection["media_type"] == "image/jpeg"
    assert logical_projection["media_type"] == "image/jpeg"

    execution = SnapshotAttemptExecutionResult(
        state_revision=1,
        attempt=attempt,
        plan=plan,
        staging_root=tmp_path,
        authority_reference="quillan_slice0_build_authority",
        entries=(prepared,),
    )
    counts: dict[str, int] = {}

    def ids(prefix: str) -> str:
        counts[prefix] = counts.get(prefix, 0) + 1
        return f"{prefix}_{counts[prefix]}"

    records, _, _, _, _, _ = _build_sealed_records(
        execution=execution,
        edition_ref=SnapshotEditionRef(
            snapshot_series_id=plan.snapshot_series_id,
            edition_number=1,
        ),
        predecessor_edition=None,
        sealed_at=NOW,
        sealed_by=ACTOR,
        id_factory=ids,
    )
    entry = next(item for item in records if isinstance(item, SnapshotEntry))
    assert entry.media_type == "image/jpeg"


def test_quillan_slice0_support_keys_and_opaque_ids_are_deterministic() -> None:
    assert QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY == (
        "quillan",
        "quillan:selected_student_work",
        "vitrine_candidate_projection_v1",
        "original_student_work",
        "quillan:selected_student_work",
    )
    assert QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY[-2:] == (
        "rendered_feedback",
        "quillan:feedback_pdf",
    )
    assert QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY[-2:] == (
        "rendered_feedback",
        "quillan:feedback_markdown",
    )

    review = quillan_review_source_id(
        class_id="english10_p2",
        work_id="unit1_essay",
        student_id="student_001",
    )
    review_again = quillan_review_source_id(
        class_id="english10_p2",
        work_id="unit1_essay",
        student_id="student_001",
    )
    evidence = quillan_evidence_source_id(
        class_id="english10_p2",
        work_id="unit1_essay",
        student_id="student_001",
        evidence_id="obs_0123456789abcdef0123456789abcdef",
    )
    feedback_pdf = quillan_feedback_source_id(
        class_id="english10_p2",
        work_id="unit1_essay",
        student_id="student_001",
        artifact_request_kind="feedback_pdf",
    )
    feedback_markdown = quillan_feedback_source_id(
        class_id="english10_p2",
        work_id="unit1_essay",
        student_id="student_001",
        artifact_request_kind="feedback_markdown",
    )

    assert review == review_again
    assert review.startswith("quillan_review_") and len(review) == len("quillan_review_") + 64
    assert evidence.startswith("quillan_evidence_") and len(evidence) == len("quillan_evidence_") + 64
    assert feedback_pdf.startswith("quillan_feedback_")
    assert feedback_pdf != feedback_markdown
    assert len({review, evidence, feedback_pdf, feedback_markdown}) == 4
