from __future__ import annotations

import builtins
import importlib
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from vitrine.producer_adapters import (
    ProducerAdapterSupportRequest,
    ProducerProjectionError,
)
from vitrine.producer_reader_services import INSTALLED_PRODUCER_READER_CONTRACT_VERSION
from vitrine.released_producer_contracts import CONCORD_LIVE_SUPPORT_KEY


@dataclass(frozen=True)
class _Actor:
    actor_kind: str
    actor_id: str
    owning_system: str


@dataclass(frozen=True)
class _RecordSet:
    record_set_id: str
    revision: int


@dataclass(frozen=True)
class _Work:
    module_id: str
    class_id: str
    work_id: str


@dataclass(frozen=True)
class _Record:
    module_id: str
    record_kind: str
    record_id: str
    contract_version: str | None


@dataclass(frozen=True)
class _Projection:
    source_snapshot_revision: int
    projection_digest_algorithm: str
    projection_digest: str
    generated_by: _Actor
    revision_reason: str


@dataclass(frozen=True)
class _Activity:
    activity_id: str
    class_id: str
    title: str
    scoring_orientation: str
    standards_profile_id: str | None
    focus_standard_ids: tuple[str, ...]
    criterion_set_ids: tuple[str, ...]


@dataclass(frozen=True)
class _CriterionSet:
    criterion_set_id: str
    lineage_id: str
    revision: int
    criterion_set_kind: str
    scope: str
    criterion_ids: tuple[str, ...]
    status: str
    supersedes_criterion_set_id: str | None
    standards_profile_id: str | None


@dataclass(frozen=True)
class _Criterion:
    criterion_id: str
    criterion_set_id: str
    key: str
    label: str
    definition: str
    criterion_kind: str
    supported_target_kinds: tuple[str, ...]
    status: str
    standard_id: str | None
    alignment_standard_ids: tuple[str, ...]
    default_scoring_scale_id: str | None


@dataclass(frozen=True)
class _Level:
    value: str | int | float | bool
    label: str
    meaning: str
    position: int | None
    description: str | None


@dataclass(frozen=True)
class _Scale:
    scoring_scale_id: str
    lineage_id: str
    name: str
    revision: int
    scale_type: str
    levels: tuple[_Level, ...]
    status: str
    supersedes_scoring_scale_id: str | None


@dataclass(frozen=True)
class _Target:
    target_kind: str
    target_id: str
    owning_system: str
    contract_version: str | None


@dataclass(frozen=True)
class _Subject:
    subject_kind: str
    subject_id: str
    owning_system: str
    contract_version: str | None


@dataclass(frozen=True)
class _CorePublication:
    publication_id: str
    publication_schema_version: str | None


@dataclass(frozen=True)
class _Locator:
    page_number: int | None
    source_page_index: int | None
    section_label: str | None
    row_label: str | None
    column_label: str | None
    participant_label: str | None
    session_id: str | None


@dataclass(frozen=True)
class _Evidence:
    evidence_kind: str
    owning_system: str
    record_id: str
    contract_version: str | None
    source_publication_reference: _CorePublication | None
    immutable_source_version: str | None
    locator: _Locator | None
    subject_context: tuple[_Subject, ...]
    moderation_requirement: str | None


@dataclass(frozen=True)
class _EvidenceLink:
    score_evidence_link_id: str
    score_record_id: str
    evidence_reference: _Evidence
    evidence_locator: _Locator | None
    subject_context: tuple[_Subject, ...]
    relevance_description: str
    significance: str | None
    moderation_record_id: str | None
    status: str
    supersedes_score_evidence_link_id: str | None


@dataclass(frozen=True)
class _Moderation:
    moderation_record_id: str
    target_evidence_reference: _Evidence
    target_subject_references: tuple[_Subject, ...]
    status: str
    permitted_use: str
    qualification: str | None
    supersedes_moderation_record_id: str | None
    current_state: str


@dataclass(frozen=True)
class _StatusReason:
    reason_code: str
    recorded_by: _Actor
    recorded_at: datetime
    related_record: _Record | None


@dataclass(frozen=True)
class _Score:
    score_record_id: str
    activity_id: str
    session_id: str | None
    target_reference: _Target
    criterion_id: str
    score_kind: str
    standard_id: str | None
    scoring_scale_id: str
    disposition: str
    value: str | int | float | bool | None
    basis: str
    scorer: _Actor
    scored_at: datetime
    moderation_complete: bool
    status_reason: _StatusReason | None
    supersedes_score_record_id: str | None
    current_state: str


@dataclass(frozen=True)
class _StandardsResult:
    score_record_id: str
    standard_id: str


@dataclass(frozen=True)
class _Privacy:
    classification: str
    audience_references: tuple[_Subject, ...]
    policy_reference: _Record | None
    inherited_from: _Record | None


@dataclass(frozen=True)
class _Manifest:
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: _RecordSet
    work: _Work
    source_activity: _Record
    projection: _Projection
    activity_context: _Activity
    criterion_sets: tuple[_CriterionSet, ...]
    criteria: tuple[_Criterion, ...]
    scoring_scales: tuple[_Scale, ...]
    scores: tuple[_Score, ...]
    score_evidence_links: tuple[_EvidenceLink, ...]
    moderation_records: tuple[_Moderation, ...]
    standards_result_projection: tuple[_StandardsResult, ...]
    privacy: _Privacy


def _import_concord_adapter_without_producer_import(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "concord" or name.startswith("concord."):
            raise AssertionError("Concord package import must remain lazy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("vitrine.concord_adapter", None)
    return importlib.import_module("vitrine.concord_adapter")


def _manifest() -> _Manifest:
    actor = _Actor("authorized_adult", "teacher_alpha", "concord")
    standard_set = _CriterionSet(
        "set_standard",
        "lineage_standard",
        2,
        "standard_backed",
        "activity_specific",
        ("criterion_standard",),
        "active",
        "set_standard_old",
        "standards_alpha",
    )
    local_set = _CriterionSet(
        "set_local",
        "lineage_local",
        1,
        "local",
        "activity_specific",
        ("criterion_local",),
        "active",
        None,
        None,
    )
    standard = _Criterion(
        "criterion_standard",
        "set_standard",
        "standard",
        "Standard Criterion",
        "Exact standard-backed criterion.",
        "standard_backed",
        ("core_student",),
        "active",
        "standard_alpha",
        ("standard_alpha", "standard_context"),
        "typed_scale",
    )
    local = _Criterion(
        "criterion_local",
        "set_local",
        "local",
        "Local Criterion",
        "Exact local criterion.",
        "local",
        ("concord_group", "concord_session"),
        "active",
        None,
        (),
        "typed_scale",
    )
    scale = _Scale(
        "typed_scale",
        "typed_scale_lineage",
        "Typed scale",
        3,
        "teacher_defined",
        (
            _Level(1, "Integer", "Integer one", 1, None),
            _Level(1.0, "Float", "Float one", 2, "Float meaning"),
            _Level("1", "String", "String one", 3, None),
            _Level(True, "Boolean", "Boolean true", 4, None),
        ),
        "active",
        "typed_scale_old",
    )
    scored_at = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    old_student = _Score(
        "score_student_old",
        "activity_alpha",
        "session_alpha",
        _Target("core_student", "student_alpha", "core", None),
        "criterion_standard",
        "standard_backed",
        "standard_alpha",
        "typed_scale",
        "scored",
        1,
        "professional_judgment",
        actor,
        scored_at,
        True,
        None,
        None,
        "superseded",
    )
    current_student = _Score(
        "score_student_current",
        "activity_alpha",
        "session_alpha",
        _Target("core_student", "student_alpha", "core", None),
        "criterion_standard",
        "standard_backed",
        "standard_alpha",
        "typed_scale",
        "scored",
        1.0,
        "professional_judgment",
        actor,
        scored_at,
        True,
        None,
        "score_student_old",
        "current",
    )
    group = _Score(
        "score_group",
        "activity_alpha",
        "session_alpha",
        _Target("concord_group", "group_alpha", "concord", "concord_group_v1"),
        "criterion_local",
        "local",
        None,
        "typed_scale",
        "scored",
        True,
        "professional_judgment",
        actor,
        scored_at,
        True,
        None,
        None,
        "current",
    )
    session = _Score(
        "score_session",
        "activity_alpha",
        "session_alpha",
        _Target("concord_session", "session_alpha", "concord", "concord_session_v1"),
        "criterion_local",
        "local",
        None,
        "typed_scale",
        "scored",
        "1",
        "professional_judgment",
        actor,
        scored_at,
        True,
        None,
        None,
        "current",
    )
    absent = _Score(
        "score_absent",
        "activity_alpha",
        "session_alpha",
        _Target("core_student", "student_beta", "core", None),
        "criterion_standard",
        "standard_backed",
        "standard_alpha",
        "typed_scale",
        "absent",
        None,
        "professional_judgment",
        actor,
        scored_at,
        False,
        _StatusReason(
            "absent",
            actor,
            scored_at,
            _Record("concord", "attendance_record", "absence_alpha", None),
        ),
        None,
        "current",
    )

    student_alpha = _Subject("core_student", "student_alpha", "core", None)
    group_alpha = _Subject(
        "concord_group", "group_alpha", "concord", "concord_group_v1"
    )
    artifact = _Evidence(
        "artifact_instance",
        "concord",
        "artifact_alpha",
        "concord_artifact_instance_v1",
        None,
        "snapshot_9",
        _Locator(2, 1, "response", None, None, None, "session_alpha"),
        (student_alpha, group_alpha),
        "required",
    )
    page = _Evidence(
        "artifact_page",
        "concord",
        "artifact_page_alpha",
        "concord_artifact_page_v1",
        None,
        "snapshot_9",
        _Locator(3, 2, None, None, None, None, "session_alpha"),
        (group_alpha,),
        "not_required",
    )
    external = _Evidence(
        "scoreform_result",
        "scoreform",
        "scoreform_result_alpha",
        "scoreform_academic_result_manifest_v1",
        _CorePublication("publication_scoreform_alpha", "1"),
        "record_set_revision_4",
        _Locator(None, None, None, "student_alpha", "attempt_1", None, None),
        (student_alpha,),
        "not_required",
    )

    moderation_old = _Moderation(
        "moderation_old",
        artifact,
        (student_alpha,),
        "accepted_with_qualification",
        "corroborate_only",
        "Use only as corroborating evidence.",
        None,
        "superseded",
    )
    moderation_current = _Moderation(
        "moderation_current",
        artifact,
        (student_alpha,),
        "accepted",
        "support_named_subject",
        None,
        "moderation_old",
        "current",
    )

    links = (
        _EvidenceLink(
            "link_artifact_old",
            "score_student_old",
            artifact,
            artifact.locator,
            (student_alpha,),
            "Historical Artifact evidence.",
            "counterevidence",
            "moderation_old",
            "superseded",
            None,
        ),
        _EvidenceLink(
            "link_artifact_current",
            "score_student_current",
            artifact,
            artifact.locator,
            (student_alpha,),
            "Current Artifact evidence.",
            "primary",
            "moderation_current",
            "active",
            "link_artifact_old",
        ),
        _EvidenceLink(
            "link_artifact_page",
            "score_group",
            page,
            page.locator,
            (group_alpha,),
            "Exact represented Artifact Page.",
            "corroborating",
            None,
            "active",
            None,
        ),
        _EvidenceLink(
            "link_external",
            "score_session",
            external,
            external.locator,
            (student_alpha,),
            "External ScoreForm evidence.",
            "contextual",
            None,
            "inactive",
            None,
        ),
    )
    return _Manifest(
        record_type="concord_academic_result_manifest",
        contract_version="concord_academic_result_manifest_v1",
        producer_module_id="concord",
        generated_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
        record_set=_RecordSet("academic_results", 4),
        work=_Work("concord", "class_alpha", "activity_alpha"),
        source_activity=_Record(
            "concord", "activity", "activity_alpha", "concord_activity_v1"
        ),
        projection=_Projection(
            9,
            "sha256",
            "a" * 64,
            actor,
            "native_state_change",
        ),
        activity_context=_Activity(
            "activity_alpha",
            "class_alpha",
            "Collaborative Activity",
            "mixed",
            "standards_alpha",
            ("standard_alpha", "standard_context"),
            ("set_standard", "set_local"),
        ),
        criterion_sets=(standard_set, local_set),
        criteria=(standard, local),
        scoring_scales=(scale,),
        scores=(old_student, current_student, group, session, absent),
        score_evidence_links=links,
        moderation_records=(moderation_old, moderation_current),
        standards_result_projection=(
            _StandardsResult("score_student_old", "standard_alpha"),
            _StandardsResult("score_student_current", "standard_alpha"),
            _StandardsResult("score_absent", "standard_alpha"),
        ),
        privacy=_Privacy(
            "group_and_teacher",
            (student_alpha, group_alpha),
            None,
            None,
        ),
    )


def _project(monkeypatch: pytest.MonkeyPatch, value: object | None = None) -> Any:
    import vitrine.concord_adapter as concord_adapter

    monkeypatch.setattr(
        concord_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest)
        if name == "concord.academic_result_manifest"
        else None,
    )
    return concord_adapter.build_concord_live_adapter().project(
        _manifest() if value is None else value
    )


def _source(batch: Any, score_id: str) -> Any:
    return next(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_record"
        and source.producer_source.source_record_id == score_id
    )


def _link_source(batch: Any, link_id: str) -> Any:
    return next(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_evidence_link"
        and source.producer_source.source_record_id == link_id
    )


def _fields(source: Any) -> dict[str, object]:
    return {field.key: field.value for field in source.display_snapshot.fields}


def test_declaration_uses_frozen_concord_contract_and_installed_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _import_concord_adapter_without_producer_import(monkeypatch)
    declaration = module.CONCORD_LIVE_ADAPTER_DECLARATION
    adapter = module.build_concord_live_adapter()

    assert declaration.adapter_id == "vitrine_concord_live_adapter"
    assert declaration.adapter_contract_version == "vitrine_concord_live_adapter_v1"
    assert declaration.candidate_projection_contract_version == (
        "vitrine_candidate_projection_v1"
    )
    assert declaration.support_key is CONCORD_LIVE_SUPPORT_KEY
    assert declaration.public_reader_id == (
        "vitrine_installed_concord_academic_result_reader"
    )
    assert declaration.reader_contract_version == (
        INSTALLED_PRODUCER_READER_CONTRACT_VERSION
    )
    assert declaration.reader_package_identity == "pds-concord"
    assert declaration.integration_kind == "live"
    assert declaration.supported_source_families == (
        "collaborative_work",
        "score_summary",
    )
    assert declaration.supported_representation_families == (
        "collaborative_work",
        "result_summary",
    )
    assert adapter.declaration is declaration
    assert adapter.reader.descriptor.package_identity == "pds-concord"


def test_module_and_adapter_construction_do_not_import_concord(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        name for name in sys.modules if name == "concord" or name.startswith("concord.")
    }
    module = _import_concord_adapter_without_producer_import(monkeypatch)
    adapter = module.build_concord_live_adapter()
    _ = adapter.declaration
    _ = adapter.reader.descriptor
    after = {
        name for name in sys.modules if name == "concord" or name.startswith("concord.")
    }
    assert after == before


def test_frozen_support_key_accepts_conditional_capabilities_without_overlap() -> None:
    key = CONCORD_LIVE_SUPPORT_KEY
    base = dict(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
    )

    assert key.matches(
        ProducerAdapterSupportRequest(
            **base, capabilities=("criterion_scores",)
        )
    )
    assert key.matches(
        ProducerAdapterSupportRequest(
            **base,
            capabilities=(
                "criterion_scores",
                "moderated_scores",
                "standards_ratings",
            ),
        )
    )
    assert not key.matches(
        ProducerAdapterSupportRequest(
            **base, capabilities=("standards_ratings",)
        )
    )


def test_projection_emits_one_source_per_score_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    score_sources = tuple(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_record"
    )
    assert len(score_sources) == 5
    assert {
        source.producer_source.source_record_id for source in score_sources
    } == {
        "score_student_old",
        "score_student_current",
        "score_group",
        "score_session",
        "score_absent",
    }
    assert all(
        source.producer_source.source_record_contract_version is None
        for source in score_sources
    )


def test_projection_preserves_score_history_without_selecting_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    old = _source(batch, "score_student_old")
    current = _source(batch, "score_student_current")
    old_fields = _fields(old)
    current_fields = _fields(current)

    assert old.producer_source.native_lifecycle == "superseded"
    assert current.producer_source.native_lifecycle == "current"
    assert old_fields["score_current_state"] == "superseded"
    assert current_fields["score_current_state"] == "current"
    assert current_fields["score_supersedes_score_record_id"] == "score_student_old"
    assert old_fields["score_native_value"] == 1
    assert current_fields["score_native_value"] == 1.0


def test_projection_preserves_type_sensitive_scale_and_score_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    fields = _fields(_source(batch, "score_student_current"))

    values = fields["scale_level_values"]
    types = fields["scale_level_value_types"]
    assert isinstance(values, tuple)
    assert isinstance(types, tuple)
    assert tuple(type(value) for value in values) == (int, float, str, bool)
    assert types == ("int", "float", "string", "bool")
    assert values == (1, 1.0, "1", True)
    assert fields["scale_level_positions"] == (1, 2, 3, 4)

    native_types = {
        score_id: _fields(_source(batch, score_id))["score_native_value_type"]
        for score_id in (
            "score_student_old",
            "score_student_current",
            "score_session",
            "score_group",
        )
    }
    assert native_types == {
        "score_student_old": "int",
        "score_student_current": "float",
        "score_session": "string",
        "score_group": "bool",
    }


def test_group_and_individual_targets_remain_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    student = _source(batch, "score_student_current")
    group = _source(batch, "score_group")
    session = _source(batch, "score_session")

    student_relationships = [
        (item.source_subject_kind, item.relationship_kind)
        for item in student.source_relationships
    ]
    group_relationships = [
        (item.source_subject_kind, item.relationship_kind)
        for item in group.source_relationships
    ]
    assert student_relationships == [("core_student", "individual_score_target")]
    assert group_relationships == [("concord_group", "group_score_target")]
    assert session.source_relationships == ()
    assert _fields(group)["score_target_id"] == "group_alpha"
    assert _fields(session)["score_target_kind"] == "concord_session"


def test_non_score_disposition_remains_valueless_and_preserves_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = _fields(_source(_project(monkeypatch), "score_absent"))

    assert fields["score_disposition"] == "absent"
    assert fields["score_native_value"] is None
    assert fields["score_native_value_type"] == "absent"
    assert fields["status_reason_code"] == "absent"
    assert fields["status_reason_related_record_id"] == "absence_alpha"
    assert fields["standards_result_standard_id"] == "standard_alpha"


def test_projection_preserves_criterion_scale_and_activity_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = _fields(_source(_project(monkeypatch), "score_student_current"))

    assert fields["source_snapshot_revision"] == 9
    assert fields["activity_scoring_orientation"] == "mixed"
    assert fields["activity_focus_standard_ids"] == (
        "standard_alpha",
        "standard_context",
    )
    assert fields["criterion_set_revision"] == 2
    assert fields["criterion_set_supersedes_id"] == "set_standard_old"
    assert fields["criterion_kind"] == "standard_backed"
    assert fields["criterion_alignment_standard_ids"] == (
        "standard_alpha",
        "standard_context",
    )
    assert fields["scoring_scale_revision"] == 3
    assert fields["scoring_scale_supersedes_id"] == "typed_scale_old"


def test_score_projection_is_pure_summary_without_source_locator_or_grade_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)

    score_sources = tuple(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_record"
    )
    for source in score_sources:
        assert source.projection_kind == "concord:score_summary"
        assert source.source_artifact.artifact_kind == "assessment_summary"
        assert source.source_artifact.representation_kind == "concord:score_summary"
        assert source.source_artifact.source_locator is None
        assert source.source_artifact.source_digest is None
        keys = set(_fields(source))
        assert "grade" not in keys
        assert "percentage" not in keys
        assert "proficiency" not in keys
        assert "mastery" not in keys
        assert "portfolio_worth" not in keys



def test_projection_emits_every_score_evidence_link_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    link_sources = tuple(
        source
        for source in batch.projected_sources
        if source.producer_source.source_record_kind == "score_evidence_link"
    )

    assert len(link_sources) == 4
    assert {
        source.producer_source.source_record_id for source in link_sources
    } == {
        "link_artifact_old",
        "link_artifact_current",
        "link_artifact_page",
        "link_external",
    }
    assert {
        source.producer_source.native_lifecycle for source in link_sources
    } == {"active", "inactive", "superseded"}
    assert all(
        source.producer_source.source_record_contract_version is None
        for source in link_sources
    )


def test_score_summaries_preserve_link_history_without_selecting_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    old = _fields(_source(batch, "score_student_old"))
    current = _fields(_source(batch, "score_student_current"))
    group = _fields(_source(batch, "score_group"))
    session = _fields(_source(batch, "score_session"))

    assert old["score_evidence_link_ids"] == ("link_artifact_old",)
    assert old["score_evidence_link_statuses"] == ("superseded",)
    assert old["score_evidence_link_significance"] == ("counterevidence",)
    assert current["score_evidence_link_ids"] == ("link_artifact_current",)
    assert current["score_evidence_link_statuses"] == ("active",)
    assert current["score_evidence_moderation_record_ids"] == (
        "moderation_current",
    )
    assert group["score_evidence_kinds"] == ("artifact_page",)
    assert session["score_evidence_kinds"] == ("scoreform_result",)


def test_concord_artifact_links_project_capability_without_pre_authorized_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    old = _link_source(batch, "link_artifact_old")
    current = _link_source(batch, "link_artifact_current")
    page = _link_source(batch, "link_artifact_page")

    assert old.projection_kind == "concord:artifact_evidence"
    assert current.projection_kind == "concord:artifact_evidence"
    assert page.projection_kind == "concord:artifact_evidence"

    # Two independent Score Evidence Links may point to the same Artifact.
    assert old.producer_source.source_record_id != current.producer_source.source_record_id
    assert old.source_artifact.artifact_id == "artifact_alpha"
    assert current.source_artifact.artifact_id == "artifact_alpha"

    for source in (old, current, page):
        assert source.source_artifact.artifact_kind == "collaborative_artifact"
        assert source.source_artifact.representation_kind == (
            "concord:returned_artifact_pdf"
        )
        assert source.source_artifact.media_type == "application/pdf"
        assert source.source_artifact.source_locator is None
        assert source.source_artifact.source_digest is None
        assert source.source_artifact.byte_size is None
        assert source.source_artifact.native_revision == 9

    assert tuple(
        (item.source_subject_kind, item.relationship_kind)
        for item in old.source_relationships
    ) == (("core_student", "individual_score_target"),)
    assert tuple(
        (item.source_subject_kind, item.relationship_kind)
        for item in current.source_relationships
    ) == (("core_student", "individual_score_target"),)
    assert tuple(
        (item.source_subject_kind, item.relationship_kind)
        for item in page.source_relationships
    ) == (("concord_group", "group_score_target"),)

    assert page.source_artifact.artifact_id == "artifact_page_alpha"
    assert _fields(page)["evidence_kind"] == "artifact_page"
    assert _fields(page)["artifact_resolution_source_snapshot_revision"] == 9


def test_external_evidence_remains_metadata_only_and_is_not_dereferenced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _link_source(_project(monkeypatch), "link_external")
    fields = _fields(source)

    assert source.projection_kind == "concord:evidence_link_summary"
    assert source.source_artifact.artifact_kind == "assessment_summary"
    assert source.source_artifact.representation_kind == (
        "concord:evidence_link_summary"
    )
    assert source.source_artifact.source_locator is None
    assert fields["artifact_resolution_capable"] is False
    assert fields["artifact_resolution_representation"] is None
    assert fields["evidence_kind"] == "scoreform_result"
    assert fields["evidence_owning_system"] == "scoreform"
    assert fields["evidence_source_publication_id"] == (
        "publication_scoreform_alpha"
    )
    assert fields["evidence_source_publication_schema_version"] == "1"
    assert fields["evidence_immutable_source_version"] == "record_set_revision_4"
    assert fields["evidence_reference_locator_row_label"] == "student_alpha"
    assert fields["evidence_reference_locator_column_label"] == "attempt_1"


def test_moderation_history_and_public_qualification_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    old = _fields(_link_source(batch, "link_artifact_old"))
    current = _fields(_link_source(batch, "link_artifact_current"))

    assert old["moderation_record_id"] == "moderation_old"
    assert old["moderation_status"] == "accepted_with_qualification"
    assert old["moderation_permitted_use"] == "corroborate_only"
    assert old["moderation_qualification"] == (
        "Use only as corroborating evidence."
    )
    assert old["moderation_current_state"] == "superseded"

    assert current["moderation_record_id"] == "moderation_current"
    assert current["moderation_status"] == "accepted"
    assert current["moderation_permitted_use"] == "support_named_subject"
    assert current["moderation_qualification"] is None
    assert current["moderation_supersedes_record_id"] == "moderation_old"
    assert current["moderation_current_state"] == "current"
    assert current["moderation_target_subject_ids"] == ("student_alpha",)


def test_privacy_mapping_preserves_producer_classification_without_authorizing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    score = _source(batch, "score_student_current")
    artifact = _link_source(batch, "link_artifact_current")
    external = _link_source(batch, "link_external")

    for source in (score, artifact, external):
        fields = _fields(source)
        assert source.source_privacy.classification == "group_and_teacher"
        assert fields["producer_privacy_classification"] == "group_and_teacher"
        assert fields["producer_privacy_audience_kinds"] == (
            "core_student",
            "concord_group",
        )
        assert fields["producer_privacy_audience_ids"] == (
            "student_alpha",
            "group_alpha",
        )
        assert source.source_privacy.minimum_necessary_projection_required is True

    assert score.source_privacy.multi_subject_review_required is True
    assert artifact.source_privacy.collaborator_information_present is True
    assert artifact.source_privacy.multi_subject_review_required is True
    assert artifact.source_privacy.redaction_review_required is True
    assert external.source_privacy.third_party_information_present is True


def test_evidence_subject_context_does_not_infer_artifact_subject_or_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    artifact = _link_source(batch, "link_artifact_current")
    external = _link_source(batch, "link_external")

    # Evidence-link sources preserve only the exact parent Score target
    # relationship. Evidence subject-context does not manufacture Artifact
    # Subject, authorship, membership, or contribution semantics.
    assert tuple(
        (item.source_subject_kind, item.relationship_kind)
        for item in artifact.source_relationships
    ) == (("core_student", "individual_score_target"),)
    assert external.source_relationships == ()
    fields = _fields(artifact)
    assert fields["score_evidence_subject_kinds"] == ("core_student",)
    assert fields["score_evidence_subject_ids"] == ("student_alpha",)
    assert fields["evidence_reference_subject_kinds"] == (
        "core_student",
        "concord_group",
    )
    assert fields["evidence_reference_subject_ids"] == (
        "student_alpha",
        "group_alpha",
    )

    forbidden_relationships = {
        "artifact_author",
        "artifact_subject",
        "group_member",
        "documented_contributor",
        "group_score_target",
    }
    assert not (
        forbidden_relationships
        & {item.relationship_kind for item in artifact.source_relationships}
    )


def test_projection_rejects_wrong_public_model_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ProducerProjectionError) as caught:
        _project(monkeypatch, object())
    assert caught.value.code == "projection.invalid_input"
    assert caught.value.stage == "projection"


def test_projection_contract_resolution_failure_is_privacy_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.concord_adapter as concord_adapter

    def fail(_: str) -> ModuleType:
        raise ImportError("private installation detail")

    monkeypatch.setattr(concord_adapter, "import_module", fail)
    with pytest.raises(ProducerProjectionError) as caught:
        concord_adapter.build_concord_live_adapter().project(_manifest())
    assert caught.value.code == "projection.failed"
    assert caught.value.stage == "projection_contract"
    assert "private installation detail" not in str(caught.value)

def test_live_concord_candidate_path_preserves_scores_and_artifact_evidence_without_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pds_core.academic_catalog import (
        PublicationCatalogQuery,
        rebuild_academic_catalog,
    )
    from pds_core.publication_compatibility import (
        PublicationContractSupport,
        PublicationProducerProfile,
        PublicationProducerRegistry,
        SourceRecordContractSupport,
    )
    from pds_core.registry_services import (
        AcademicWorkRegistrationRequest,
        PublicationManifestRequest,
        publish_manifest_revision,
        register_academic_work,
    )
    from pds_core.routes import module_work_dir
    from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

    import vitrine.concord_adapter as concord_adapter
    import vitrine.producer_reader_services as producer_reader_services
    from scripts.candidate_fixture_support import (
        ACTOR,
        CLASS_ID,
        DeterministicIds,
        StaticAuthorizationGate,
        build_candidate_fixture_workspace,
        fixed_clock,
    )
    from vitrine.candidate_services import (
        CandidateDiscoveryRequest,
        discover_and_evaluate_candidates,
    )
    from vitrine.models import (
        CandidateEvaluation,
        PortfolioCandidate,
        PortfolioSelection,
    )
    from vitrine.producer_adapters import ProducerProjectionAdapterRegistry
    from vitrine.storage import load_current_records

    setup = build_candidate_fixture_workspace(tmp_path)
    work_id = "live_concord_activity"
    record_set_id = "live_concord_results"
    payload = b'{"test":"verified-live-concord-reader-boundary"}\n'
    work = ModuleWorkRef("concord", CLASS_ID, work_id)
    source_record = ModuleRecordRef(
        "concord",
        "activity",
        work_id,
        "concord_activity_v1",
    )
    work_root = module_work_dir(setup.workspace, work)
    work_root.mkdir(parents=True, exist_ok=True)
    registration = register_academic_work(
        setup.workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version="concord_academic_work_v1",
            title="Live Concord Activity",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=(source_record,),
        ),
    ).registration
    manifest_path = (
        work_root / "exports" / "manifests" / record_set_id / "1.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(payload)
    publication = publish_manifest_revision(
        setup.workspace,
        PublicationManifestRequest(
            work=work,
            source_record=source_record,
            publication_kind="academic_result_set",
            capabilities=(
                "criterion_scores",
                "standards_ratings",
                "moderated_scores",
            ),
            record_set_id=record_set_id,
            record_set_revision=1,
            manifest_contract_version="concord_academic_result_manifest_v1",
            manifest_path=manifest_path.relative_to(setup.workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    rebuild_academic_catalog(setup.workspace)

    base = _manifest()
    live_manifest = replace(
        base,
        record_set=replace(base.record_set, record_set_id=record_set_id, revision=1),
        work=replace(base.work, class_id=CLASS_ID, work_id=work_id),
        source_activity=replace(base.source_activity, record_id=work_id),
        activity_context=replace(
            base.activity_context,
            activity_id=work_id,
            class_id=CLASS_ID,
            title="Live Concord Activity",
        ),
        scores=tuple(replace(score, activity_id=work_id) for score in base.scores),
    )
    reader_calls: list[bytes] = []

    def public_reader(value: bytes) -> object:
        reader_calls.append(value)
        if value != payload:
            raise AssertionError(
                "installed Concord reader did not receive exact verified bytes"
            )
        return live_manifest

    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        lambda distribution: "0.3.0" if distribution == "pds-concord" else "0.0.0",
    )
    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda name: SimpleNamespace(read_academic_result_manifest=public_reader)
        if name == "concord.academic_result_reader"
        else (_ for _ in ()).throw(
            AssertionError(f"unexpected producer reader import: {name}")
        ),
    )
    monkeypatch.setattr(
        concord_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest)
        if name == "concord.academic_result_manifest"
        else (_ for _ in ()).throw(
            AssertionError(f"unexpected Concord projection import: {name}")
        ),
    )

    producer_profile = PublicationProducerProfile(
        module_id="concord",
        display_name="Concord",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"concord_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {"concord_academic_result_manifest_v1"}
                ),
                supported_capabilities=frozenset(
                    {
                        "criterion_scores",
                        "standards_ratings",
                        "moderated_scores",
                    }
                ),
                source_record_contracts=(
                    SourceRecordContractSupport(
                        record_kind="activity",
                        contract_versions=frozenset({"concord_activity_v1"}),
                    ),
                ),
                allows_missing_source_record=False,
            ),
        ),
    )
    gate = StaticAuthorizationGate("allowed")
    result = discover_and_evaluate_candidates(
        setup.workspace,
        CandidateDiscoveryRequest(
            portfolio_id=setup.portfolio_id,
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="concord",
                state="current",
                limit=20,
            ),
            expected_state_revision=setup.state_revision,
        ),
        producer_registry=PublicationProducerRegistry(profiles=(producer_profile,)),
        adapter_registry=ProducerProjectionAdapterRegistry(
            adapters=(concord_adapter.build_concord_live_adapter(),)
        ),
        authorization_gate=gate,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.proposed_publication_ids == (publication.publication_id,)
    assert result.findings == ()
    assert reader_calls == [payload]
    assert len(gate.requests) == 1
    assert len(result.evaluation_results) == 9

    by_source_id = {
        item.projected_source.producer_source.source_record_id: item
        for item in result.evaluation_results
    }
    assert set(by_source_id) == {
        "score_student_old",
        "score_student_current",
        "score_group",
        "score_session",
        "score_absent",
        "link_artifact_old",
        "link_artifact_current",
        "link_artifact_page",
        "link_external",
    }

    old_artifact = by_source_id["link_artifact_old"]
    current_artifact = by_source_id["link_artifact_current"]
    group_page = by_source_id["link_artifact_page"]
    external = by_source_id["link_external"]

    assert old_artifact.evaluation.outcome == "conditionally_eligible"
    assert current_artifact.evaluation.outcome == "conditionally_eligible"
    assert old_artifact.candidate is not None
    assert current_artifact.candidate is not None
    assert old_artifact.candidate.candidate_id != current_artifact.candidate.candidate_id
    assert old_artifact.candidate.condition_state == "collaborator_review_required"
    assert current_artifact.candidate.condition_state == "collaborator_review_required"
    assert group_page.evaluation.outcome == "unresolved"
    assert group_page.candidate is None
    assert external.evaluation.outcome == "unresolved"
    assert external.candidate is None

    assert _fields(by_source_id["score_student_old"].projected_source)[
        "score_current_state"
    ] == "superseded"
    assert _fields(by_source_id["score_student_current"].projected_source)[
        "score_current_state"
    ] == "current"
    assert _fields(by_source_id["score_absent"].projected_source)[
        "score_native_value"
    ] is None

    records = load_current_records(setup.workspace)
    live_evaluations = tuple(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.source_endpoint is not None
        and item.source_endpoint.core_publication.publication_id
        == publication.publication_id
    )
    live_candidates = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and item.source_endpoint.core_publication.publication_id
        == publication.publication_id
    )
    assert len(live_evaluations) == 9
    assert len(live_candidates) == 2
    assert not any(isinstance(item, PortfolioSelection) for item in records)

