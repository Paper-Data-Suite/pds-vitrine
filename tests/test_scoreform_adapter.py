from __future__ import annotations

import builtins
import importlib
import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerProjectionError,
    build_adapter_registry,
)
from vitrine.producer_reader_services import INSTALLED_PRODUCER_READER_CONTRACT_VERSION
from vitrine.released_producer_contracts import SCOREFORM_LIVE_SUPPORT_KEY
from vitrine.workflow_context import default_workflow_dependencies

_ATTEMPT_ID = re.compile(r"^scoreform_attempt_[0-9a-f]{64}$")
_SELECTED_ANSWERS = (
    "PRIVATE_ALPHA_A",
    "PRIVATE_ALPHA_B",
    "PRIVATE_ALPHA_C",
    "PRIVATE_ALPHA_D",
    "PRIVATE_BETA_A",
    "PRIVATE_BETA_B",
    "PRIVATE_BETA_C",
)


@dataclass(frozen=True)
class _Question:
    question_number: int
    points_possible: int
    standard_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Assignment:
    assignment_id: str
    title: str
    question_count: int
    layout_id: str
    total_points: int
    standards_profile_id: str | None
    questions: tuple[_Question, ...]


@dataclass(frozen=True)
class _Response:
    question_number: int
    response_state: str
    selected_answer: str | None
    correct: bool


@dataclass(frozen=True)
class _Pds2ScanProvenance:
    issuance_id: str
    generation_id: str
    artifact_id: str
    page_ids: tuple[str, ...]
    route_ids: tuple[str, ...]
    logical_pages: tuple[int, ...]
    source_scan_id: str
    source_page_numbers: tuple[int, ...]
    retained_source_path: str
    source_sha256: str


@dataclass(frozen=True)
class _PlainPaperManualProvenance:
    pass


@dataclass(frozen=True)
class _ReviewReference:
    failure_id: str


@dataclass(frozen=True)
class _ScanReviewManualProvenance:
    review_reference: _ReviewReference


@dataclass(frozen=True)
class _Attempt:
    attempt_number: int
    result_origin: str
    recorded_at: datetime
    points_earned: int
    points_possible: int
    responses: tuple[_Response, ...]
    provenance: object


@dataclass(frozen=True)
class _StudentResults:
    student_id: str
    attempts: tuple[_Attempt, ...]


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
class _AssignmentSource:
    sha256: str


@dataclass(frozen=True)
class _ResultsHistorySource:
    sha256: str
    result_schema_version: str


@dataclass(frozen=True)
class _SourceSnapshot:
    assignment: _AssignmentSource
    results_history: _ResultsHistorySource


@dataclass(frozen=True)
class _Manifest:
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: _RecordSet
    work: _Work
    source_snapshot: _SourceSnapshot
    assignment: _Assignment
    students: tuple[object, ...]


def _import_scoreform_adapter_without_producer_import(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "scoreform" or name.startswith("scoreform."):
            raise AssertionError("ScoreForm package import must remain lazy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("vitrine.scoreform_adapter", None)
    return importlib.import_module("vitrine.scoreform_adapter")


def _contract_module() -> SimpleNamespace:
    return SimpleNamespace(
        AcademicResultManifest=_Manifest,
        Pds2ScanProvenance=_Pds2ScanProvenance,
        PlainPaperManualProvenance=_PlainPaperManualProvenance,
        ScanReviewManualProvenance=_ScanReviewManualProvenance,
    )


def _responses(
    states: tuple[tuple[str, str | None, bool], ...]
) -> tuple[_Response, ...]:
    return tuple(
        _Response(
            question_number=index,
            response_state=state,
            selected_answer=selected_answer,
            correct=correct,
        )
        for index, (state, selected_answer, correct) in enumerate(states, start=1)
    )


def _manifest() -> _Manifest:
    questions = (
        _Question(1, 1, ("ela_reading_1",)),
        _Question(2, 1, ()),
        _Question(3, 1, ("ela_language_2", "ela_reading_3")),
    )
    alpha_attempt_1 = _Attempt(
        attempt_number=1,
        result_origin="pds2_scan",
        recorded_at=datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc),
        points_earned=2,
        points_possible=3,
        responses=_responses(
            (
                ("selected", _SELECTED_ANSWERS[0], True),
                ("blank", None, False),
                ("selected", _SELECTED_ANSWERS[1], True),
            )
        ),
        provenance=_Pds2ScanProvenance(
            issuance_id="issuance_alpha",
            generation_id="generation_alpha",
            artifact_id="artifact_alpha",
            page_ids=("page_alpha_1", "page_alpha_2"),
            route_ids=("route_alpha_1", "route_alpha_2"),
            logical_pages=(1, 2),
            source_scan_id="scan_alpha",
            source_page_numbers=(2, 3),
            retained_source_path="scans/source/2026-08-20/PRIVATE-alpha.pdf",
            source_sha256="a" * 64,
        ),
    )
    alpha_attempt_2 = _Attempt(
        attempt_number=2,
        result_origin="scan_review_manual",
        recorded_at=datetime(2026, 8, 21, 14, 30, tzinfo=timezone.utc),
        points_earned=1,
        points_possible=3,
        responses=_responses(
            (
                ("selected", _SELECTED_ANSWERS[2], True),
                ("ambiguous", None, False),
                ("selected", _SELECTED_ANSWERS[3], False),
            )
        ),
        provenance=_ScanReviewManualProvenance(
            review_reference=_ReviewReference(failure_id="failure_alpha")
        ),
    )
    beta_attempt_1 = _Attempt(
        attempt_number=1,
        result_origin="plain_paper_manual",
        recorded_at=datetime(2026, 8, 22, 14, 30, tzinfo=timezone.utc),
        points_earned=3,
        points_possible=3,
        responses=_responses(
            (
                ("selected", _SELECTED_ANSWERS[4], True),
                ("selected", _SELECTED_ANSWERS[5], True),
                ("selected", _SELECTED_ANSWERS[6], True),
            )
        ),
        provenance=_PlainPaperManualProvenance(),
    )
    return _Manifest(
        record_type="scoreform_academic_result_manifest",
        contract_version="scoreform_academic_result_manifest_v1",
        producer_module_id="scoreform",
        generated_at=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
        record_set=_RecordSet(record_set_id="academic_results", revision=4),
        work=_Work(
            module_id="scoreform",
            class_id="class_alpha",
            work_id="assignment_alpha",
        ),
        source_snapshot=_SourceSnapshot(
            assignment=_AssignmentSource(sha256="b" * 64),
            results_history=_ResultsHistorySource(
                sha256="c" * 64, result_schema_version="2"
            ),
        ),
        assignment=_Assignment(
            assignment_id="assignment_alpha",
            title="Assessment Alpha",
            question_count=3,
            layout_id="three_choice",
            total_points=3,
            standards_profile_id="njsls_ela",
            questions=questions,
        ),
        students=(
            _StudentResults(
                student_id="student_alpha",
                attempts=(alpha_attempt_1, alpha_attempt_2),
            ),
            _StudentResults(student_id="student_beta", attempts=(beta_attempt_1,)),
        ),
    )


def _project(monkeypatch: pytest.MonkeyPatch, manifest: object | None = None) -> object:
    import vitrine.scoreform_adapter as scoreform_adapter

    monkeypatch.setattr(
        scoreform_adapter,
        "import_module",
        lambda name: _contract_module()
        if name == "scoreform.academic_result_manifest"
        else None,
    )
    return scoreform_adapter.build_scoreform_live_adapter().project(
        _manifest() if manifest is None else manifest
    )


def _source(batch: Any, student_id: str, attempt_number: int) -> Any:
    return next(
        source
        for source in batch.projected_sources
        if source.producer_source.native_revision == attempt_number
        and source.source_relationships[0].source_subject_id == student_id
    )


def _fields(source: Any) -> dict[str, object]:
    return {field.key: field.value for field in source.display_snapshot.fields}


def test_live_declaration_uses_frozen_scoreform_contract_and_installed_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _import_scoreform_adapter_without_producer_import(monkeypatch)
    declaration = module.SCOREFORM_LIVE_ADAPTER_DECLARATION
    adapter = module.build_scoreform_live_adapter()

    assert declaration.adapter_id == "vitrine_scoreform_live_adapter"
    assert declaration.adapter_contract_version == "vitrine_scoreform_live_adapter_v1"
    assert declaration.candidate_projection_contract_version == (
        "vitrine_candidate_projection_v1"
    )
    assert declaration.support_key is SCOREFORM_LIVE_SUPPORT_KEY
    assert declaration.integration_kind == "live"
    assert declaration.supported_source_families == ("assessment_result",)
    assert declaration.supported_representation_families == ("result_summary",)
    assert declaration.diagnostic_contract_version == "vitrine_adapter_diagnostic_v1"
    assert declaration.public_reader_id == (
        "vitrine_installed_scoreform_academic_result_reader"
    )
    assert declaration.reader_contract_version == (
        INSTALLED_PRODUCER_READER_CONTRACT_VERSION
    )
    assert declaration.reader_package_identity == "scoreform"
    assert adapter.declaration is declaration
    assert adapter.reader.descriptor.public_reader_id == declaration.public_reader_id
    assert (
        adapter.reader.descriptor.reader_contract_version
        == declaration.reader_contract_version
    )
    assert adapter.reader.descriptor.package_identity == "scoreform"
    assert adapter.reader.descriptor.integration_kind == "live"


def test_live_module_and_adapter_construction_do_not_import_scoreform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        name
        for name in sys.modules
        if name == "scoreform" or name.startswith("scoreform.")
    }
    module = _import_scoreform_adapter_without_producer_import(monkeypatch)

    adapter = module.build_scoreform_live_adapter()
    _ = adapter.declaration
    _ = adapter.reader.descriptor

    after = {
        name
        for name in sys.modules
        if name == "scoreform" or name.startswith("scoreform.")
    }
    assert after == before


def test_completed_live_registry_keeps_scoreform_bound_and_workflow_fail_closed() -> None:
    ordinary = build_adapter_registry()
    assert tuple(item.declaration.adapter_id for item in ordinary.adapters) == (
        "vitrine_concord_live_adapter",
        "vitrine_scoreform_live_adapter",
    )
    scoreform = next(
        item
        for item in ordinary.adapters
        if item.declaration.adapter_id == "vitrine_scoreform_live_adapter"
    )
    assert scoreform.declaration.support_key is SCOREFORM_LIVE_SUPPORT_KEY

    dependencies = default_workflow_dependencies()
    assert dependencies.producer_registry.profiles == ()
    assert dependencies.adapter_registry.adapters == ()
    assert dependencies.development_fixture_mode is False


def test_live_registry_matches_exact_scoreform_support_and_rejects_mismatch() -> None:
    key = SCOREFORM_LIVE_SUPPORT_KEY
    request = ProducerAdapterSupportRequest(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
        capabilities=key.required_capabilities,
    )
    registry = build_adapter_registry()
    assert registry.select_adapter(request).declaration.adapter_id == (
        "vitrine_scoreform_live_adapter"
    )

    wrong = replace(request, manifest_contract_version="scoreform_unknown_manifest_v1")
    with pytest.raises(ProducerAdapterError) as caught:
        registry.select_adapter(wrong)
    assert caught.value.code == "adapter.unsupported_contract"


def test_attempt_projection_identity_is_stable_private_and_attempt_specific() -> None:
    from vitrine.scoreform_adapter import scoreform_attempt_projection_identity

    alpha_attempt_1 = scoreform_attempt_projection_identity(
        class_id="class_alpha",
        assignment_id="assignment_alpha",
        student_id="student_alpha",
        attempt_number=1,
    )
    repeat = scoreform_attempt_projection_identity(
        class_id="class_alpha",
        assignment_id="assignment_alpha",
        student_id="student_alpha",
        attempt_number=1,
    )
    alpha_attempt_2 = scoreform_attempt_projection_identity(
        class_id="class_alpha",
        assignment_id="assignment_alpha",
        student_id="student_alpha",
        attempt_number=2,
    )
    beta_attempt_1 = scoreform_attempt_projection_identity(
        class_id="class_alpha",
        assignment_id="assignment_alpha",
        student_id="student_beta",
        attempt_number=1,
    )

    assert alpha_attempt_1 == repeat
    assert _ATTEMPT_ID.fullmatch(alpha_attempt_1)
    assert alpha_attempt_1 != alpha_attempt_2
    assert alpha_attempt_1 != beta_attempt_1
    assert "student_alpha" not in alpha_attempt_1
    assert "student_beta" not in beta_attempt_1


def test_attempt_projection_identity_rejects_invalid_native_identity() -> None:
    from vitrine.scoreform_adapter import scoreform_attempt_projection_identity

    with pytest.raises(ProducerProjectionError) as caught:
        scoreform_attempt_projection_identity(
            class_id="class_alpha",
            assignment_id="assignment_alpha",
            student_id="student_alpha",
            attempt_number=0,
        )
    assert caught.value.code == "projection.invalid_input"
    assert caught.value.stage == "projection_identity"
    assert "student_alpha" not in str(caught.value)


def test_live_declaration_does_not_add_distribution_version_to_support_key() -> None:
    from vitrine.scoreform_adapter import SCOREFORM_LIVE_ADAPTER_DECLARATION

    declaration = SCOREFORM_LIVE_ADAPTER_DECLARATION
    assert declaration.support_key == SCOREFORM_LIVE_SUPPORT_KEY
    assert not hasattr(declaration.support_key, "distribution_version")
    assert not hasattr(declaration.support_key, "release_version")

    future_package_version_does_not_change_key = replace(
        declaration.support_key,
        required_capabilities=("multiple_attempts", "points", "question_evidence"),
    )
    assert future_package_version_does_not_change_key == SCOREFORM_LIVE_SUPPORT_KEY


def test_projection_emits_exactly_one_source_per_represented_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)

    assert len(batch.projected_sources) == 3
    assert {
        (
            source.source_relationships[0].source_subject_id,
            source.producer_source.native_revision,
        )
        for source in batch.projected_sources
    } == {("student_alpha", 1), ("student_alpha", 2), ("student_beta", 1)}
    assert all(
        source.producer_source.source_record_kind == "academic_result_attempt"
        for source in batch.projected_sources
    )
    assert all(
        source.producer_source.source_record_contract_version is None
        for source in batch.projected_sources
    )


def test_multiple_attempts_survive_without_selection_or_ranking_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    attempt_1 = _source(batch, "student_alpha", 1)
    attempt_2 = _source(batch, "student_alpha", 2)

    assert _fields(attempt_1)["points_earned"] == 2
    assert _fields(attempt_2)["points_earned"] == 1
    assert attempt_1.producer_source.source_record_id != attempt_2.producer_source.source_record_id
    forbidden = {
        "official",
        "best",
        "latest",
        "preferred",
        "replacement",
        "rank",
        "improvement",
        "percentage",
        "grade",
        "mastery",
        "proficiency",
        "rating",
    }
    for source in (attempt_1, attempt_2):
        keys = set(_fields(source))
        assert forbidden.isdisjoint(keys)


def test_response_states_presence_and_correctness_remain_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    attempt_1 = _fields(_source(batch, "student_alpha", 1))
    attempt_2 = _fields(_source(batch, "student_alpha", 2))

    assert attempt_1["response_states"] == (
        "1:selected",
        "2:blank",
        "3:selected",
    )
    assert attempt_2["response_states"] == (
        "1:selected",
        "2:ambiguous",
        "3:selected",
    )
    assert attempt_1["selected_answer_presence"] == (
        "1:present",
        "2:absent",
        "3:present",
    )
    assert attempt_2["selected_answer_presence"] == (
        "1:present",
        "2:absent",
        "3:present",
    )
    assert attempt_1["response_correctness"] == (
        "1:true",
        "2:false",
        "3:true",
    )
    assert attempt_2["response_correctness"] == (
        "1:true",
        "2:false",
        "3:false",
    )


def test_selected_answer_content_is_never_projected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    rendered = repr(batch)

    for secret in _SELECTED_ANSWERS:
        assert secret not in rendered
    for source in batch.projected_sources:
        assert all(secret not in source.producer_source.source_record_id for secret in _SELECTED_ANSWERS)
        assert all(secret not in source.source_artifact.artifact_id for secret in _SELECTED_ANSWERS)
        assert all(secret not in source.display_snapshot.title for secret in _SELECTED_ANSWERS)
        assert all(
            secret not in (source.display_snapshot.summary or "")
            for secret in _SELECTED_ANSWERS
        )


def test_assignment_question_and_standard_alignment_metadata_is_preserved_without_ratings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    fields = _fields(_source(batch, "student_alpha", 1))

    assert fields["class_id"] == "class_alpha"
    assert fields["work_id"] == "assignment_alpha"
    assert fields["assignment_id"] == "assignment_alpha"
    assert fields["question_count"] == 3
    assert fields["layout_id"] == "three_choice"
    assert fields["total_points"] == 3
    assert fields["standards_profile_id"] == "njsls_ela"
    assert fields["question_numbers"] == (1, 2, 3)
    assert fields["question_points_possible"] == ("1:1", "2:1", "3:1")
    assert fields["question_standard_alignments"] == (
        "1:ela_reading_1",
        "3:ela_language_2",
        "3:ela_reading_3",
    )
    assert not any(
        token in key
        for key in fields
        for token in ("rating", "mastery", "proficiency", "standard_score")
    )


def test_manifest_and_source_snapshot_metadata_is_preserved_without_source_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    fields = _fields(_source(batch, "student_alpha", 1))

    assert fields["manifest_record_type"] == "scoreform_academic_result_manifest"
    assert fields["manifest_contract_version"] == "scoreform_academic_result_manifest_v1"
    assert fields["producer_module_id"] == "scoreform"
    assert fields["record_set_id"] == "academic_results"
    assert fields["record_set_revision"] == 4
    assert fields["manifest_generated_at"] == "2026-08-23T12:00:00.000000Z"
    assert fields["assignment_source_sha256"] == "b" * 64
    assert fields["results_history_source_sha256"] == "c" * 64
    assert fields["results_history_schema_version"] == "2"
    assert "assignment.json" not in repr(batch)
    assert "results.csv" not in repr(batch)


def test_pds2_provenance_survives_but_retained_path_never_becomes_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    source = _source(batch, "student_alpha", 1)
    fields = _fields(source)

    assert fields["provenance_kind"] == "pds2_scan"
    assert fields["pds2_issuance_id"] == "issuance_alpha"
    assert fields["pds2_generation_id"] == "generation_alpha"
    assert fields["pds2_artifact_id"] == "artifact_alpha"
    assert fields["pds2_page_ids"] == ("page_alpha_1", "page_alpha_2")
    assert fields["pds2_route_ids"] == ("route_alpha_1", "route_alpha_2")
    assert fields["pds2_logical_pages"] == (1, 2)
    assert fields["pds2_source_scan_id"] == "scan_alpha"
    assert fields["pds2_source_page_numbers"] == (2, 3)
    assert fields["pds2_source_sha256"] == "a" * 64
    assert "retained_source_path" not in fields
    assert "PRIVATE-alpha.pdf" not in repr(batch)
    assert source.source_artifact.source_locator is None
    assert source.source_artifact.source_digest is None
    assert source.source_artifact.byte_size is None


def test_plain_paper_provenance_fabricates_no_scan_or_review_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    fields = _fields(_source(batch, "student_beta", 1))

    assert fields["provenance_kind"] == "plain_paper_manual"
    assert not any(key.startswith("pds2_") for key in fields)
    assert "scan_review_failure_id" not in fields


def test_scan_review_provenance_preserves_only_bounded_failure_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    fields = _fields(_source(batch, "student_alpha", 2))

    assert fields["provenance_kind"] == "scan_review_manual"
    assert fields["scan_review_failure_id"] == "failure_alpha"
    assert not any(key.startswith("pds2_") for key in fields)


def test_attempt_identity_is_unchanged_by_score_timestamp_or_response_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _manifest()
    original_batch = _project(monkeypatch, original)
    original_id = _source(
        original_batch, "student_alpha", 1
    ).producer_source.source_record_id

    alpha = original.students[0]
    assert isinstance(alpha, _StudentResults)
    attempt = alpha.attempts[0]
    changed = replace(
        attempt,
        recorded_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        points_earned=0,
        responses=_responses(
            (
                ("selected", "COMPLETELY_DIFFERENT_A", False),
                ("ambiguous", None, False),
                ("selected", "COMPLETELY_DIFFERENT_B", False),
            )
        ),
    )
    changed_alpha = replace(alpha, attempts=(changed, alpha.attempts[1]))
    changed_manifest = replace(
        original, students=(changed_alpha, original.students[1])
    )
    changed_batch = _project(monkeypatch, changed_manifest)
    changed_id = _source(
        changed_batch, "student_alpha", 1
    ).producer_source.source_record_id

    assert changed_id == original_id


def test_attempt_relationship_artifact_and_privacy_contract_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    source = _source(batch, "student_alpha", 1)
    relationship = source.source_relationships[0]
    privacy = source.source_privacy

    assert len(source.source_relationships) == 1
    assert relationship.source_subject_kind == "core_student"
    assert relationship.source_subject_id == "student_alpha"
    assert relationship.relationship_kind == "attempt_subject"
    assert relationship.relationship_authority == "scoreform"
    assert relationship.supporting_source_reference == source.producer_source.source_record_id
    assert source.source_artifact.artifact_kind == "assessment_summary"
    assert source.source_artifact.representation_kind == "scoreform:attempt_summary"
    assert source.source_artifact.native_revision == 1
    assert source.display_snapshot.title == "Assessment Alpha — Attempt 1"
    assert "student_alpha" not in source.display_snapshot.title
    assert "student_alpha" not in (source.display_snapshot.summary or "")
    assert privacy.classification == "student_record"
    assert privacy.subject_scope == "single_subject"
    assert privacy.metadata_visibility == "internal"
    assert privacy.collaborator_information_present is False
    assert privacy.third_party_information_present is False
    assert privacy.rights_review_required is False
    assert privacy.redaction_review_required is False
    assert privacy.multi_subject_review_required is False
    assert privacy.minimum_necessary_projection_required is True
    assert privacy.policy_reference == "vitrine_live_scoreform_minimum_necessary_v1"


def test_wrong_public_model_is_invalid_input_and_does_not_leak_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.scoreform_adapter as scoreform_adapter

    monkeypatch.setattr(scoreform_adapter, "import_module", lambda _name: _contract_module())
    with pytest.raises(ProducerProjectionError) as caught:
        scoreform_adapter.build_scoreform_live_adapter().project(
            {"student_id": "PRIVATE_STUDENT", "selected_answer": "PRIVATE_ANSWER"}
        )
    assert caught.value.code == "projection.invalid_input"
    assert caught.value.stage == "projection"
    assert "PRIVATE_STUDENT" not in str(caught.value)
    assert "PRIVATE_ANSWER" not in str(caught.value)


def test_unexpected_projection_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingStudent:
        @property
        def attempts(self) -> tuple[_Attempt, ...]:
            raise ValueError("PRIVATE_STUDENT_RESPONSE_AND_PATH")

    broken = replace(_manifest(), students=(_ExplodingStudent(),))
    with pytest.raises(ProducerProjectionError) as caught:
        _project(monkeypatch, broken)
    assert caught.value.code == "projection.failed"
    assert caught.value.stage == "projection"
    assert "PRIVATE_STUDENT_RESPONSE_AND_PATH" not in str(caught.value)


def test_live_scoreform_candidate_path_evaluates_every_attempt_without_selection(
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
    )
    from pds_core.registry_services import (
        AcademicWorkRegistrationRequest,
        PublicationManifestRequest,
        publish_manifest_revision,
        register_academic_work,
    )
    from pds_core.routes import module_work_dir
    from pds_core.routing_models import ModuleWorkRef

    import vitrine.producer_reader_services as producer_reader_services
    import vitrine.scoreform_adapter as scoreform_adapter
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
    from vitrine.storage import load_current_records

    setup = build_candidate_fixture_workspace(tmp_path)
    work_id = "live_scoreform_assessment"
    record_set_id = "live_scoreform_results"
    payload = b'{"test":"verified-live-scoreform-reader-boundary"}\n'
    work = ModuleWorkRef("scoreform", CLASS_ID, work_id)
    work_root = module_work_dir(setup.workspace, work)
    work_root.mkdir(parents=True, exist_ok=True)
    registration = register_academic_work(
        setup.workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version="scoreform_academic_work_v1",
            title="Live ScoreForm Assessment",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=(),
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
            source_record=None,
            publication_kind="academic_result_set",
            capabilities=("multiple_attempts", "points", "question_evidence"),
            record_set_id=record_set_id,
            record_set_revision=1,
            manifest_contract_version="scoreform_academic_result_manifest_v1",
            manifest_path=manifest_path.relative_to(setup.workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    rebuild_academic_catalog(setup.workspace)

    base_manifest = _manifest()
    live_manifest = replace(
        base_manifest,
        record_set=replace(base_manifest.record_set, record_set_id=record_set_id, revision=1),
        work=replace(base_manifest.work, class_id=CLASS_ID, work_id=work_id),
        assignment=replace(
            base_manifest.assignment,
            assignment_id=work_id,
            title="Live ScoreForm Assessment",
        ),
    )
    reader_calls: list[bytes] = []

    def public_reader(value: bytes) -> object:
        reader_calls.append(value)
        if value != payload:
            raise AssertionError("installed ScoreForm reader did not receive exact verified bytes")
        return live_manifest

    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        lambda distribution: "0.11.0" if distribution == "scoreform" else "0.0.0",
    )
    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda name: SimpleNamespace(read_academic_result_manifest=public_reader)
        if name == "scoreform.academic_result_reader"
        else (_ for _ in ()).throw(AssertionError(f"unexpected producer reader import: {name}")),
    )
    monkeypatch.setattr(
        scoreform_adapter,
        "import_module",
        lambda name: _contract_module()
        if name == "scoreform.academic_result_manifest"
        else (_ for _ in ()).throw(AssertionError(f"unexpected projection import: {name}")),
    )

    producer_profile = PublicationProducerProfile(
        module_id="scoreform",
        display_name="ScoreForm",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"scoreform_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {"scoreform_academic_result_manifest_v1"}
                ),
                supported_capabilities=frozenset(
                    {"multiple_attempts", "points", "question_evidence"}
                ),
                source_record_contracts=(),
                allows_missing_source_record=True,
            ),
        ),
    )
    gate = StaticAuthorizationGate("allowed")
    request = CandidateDiscoveryRequest(
        portfolio_id=setup.portfolio_id,
        requesting_actor=ACTOR,
        requested_purpose="improvement",
        catalog_query=PublicationCatalogQuery(module_id="scoreform", state="current", limit=20),
        expected_state_revision=setup.state_revision,
    )
    result = discover_and_evaluate_candidates(
        setup.workspace,
        request,
        producer_registry=PublicationProducerRegistry(profiles=(producer_profile,)),
        adapter_registry=build_adapter_registry(),
        authorization_gate=gate,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.proposed_publication_ids == (publication.publication_id,)
    assert result.findings == ()
    assert reader_calls == [payload]
    assert len(gate.requests) == 1
    assert len(result.evaluation_results) == 3

    by_attempt = {
        (
            item.projected_source.source_relationships[0].source_subject_id,
            item.projected_source.producer_source.native_revision,
        ): item
        for item in result.evaluation_results
    }
    assert set(by_attempt) == {
        ("student_alpha", 1),
        ("student_alpha", 2),
        ("student_beta", 1),
    }
    alpha_one = by_attempt[("student_alpha", 1)]
    alpha_two = by_attempt[("student_alpha", 2)]
    beta_one = by_attempt[("student_beta", 1)]

    assert _fields(alpha_one.projected_source)["points_earned"] == 2
    assert _fields(alpha_two.projected_source)["points_earned"] == 1
    assert alpha_one.evaluation.outcome == "eligible"
    assert alpha_two.evaluation.outcome == "eligible"
    assert alpha_one.candidate is not None
    assert alpha_two.candidate is not None
    assert alpha_one.candidate.candidate_id != alpha_two.candidate.candidate_id
    assert beta_one.evaluation.outcome == "unresolved"
    assert beta_one.candidate is None

    for item in result.evaluation_results:
        endpoint = item.evaluation.source_endpoint
        assert endpoint is not None
        snapshot = endpoint.core_publication.registration_snapshot
        assert snapshot is not None
        assert snapshot.registration_revision == 1
        assert snapshot.producer_contract_version == "scoreform_academic_work_v1"
        observations = {
            observation.dimension: observation.outcome
            for observation in item.evaluation.availability_observations
        }
        assert observations["producer_profile"] == "compatible"
        assert observations["adapter_support"] == "selected"
        assert observations["source_authorization"] == "allowed"
        assert observations["manifest_integrity"] == "verified"
        assert observations["producer_reader"] == "available"
        assert observations["producer_parse"] == "parsed"
        assert observations["disclosure_review"] == "not_evaluated"

    rendered = repr(result.evaluation_results)
    for prohibited in (*_SELECTED_ANSWERS, "PRIVATE-alpha.pdf", "proficiency", "mastery", "Grade"):
        assert prohibited not in rendered

    records = load_current_records(setup.workspace)
    live_evaluations = tuple(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.source_endpoint is not None
        and item.source_endpoint.core_publication.publication_id == publication.publication_id
    )
    live_candidates = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and item.source_endpoint.core_publication.publication_id == publication.publication_id
    )
    assert len(live_evaluations) == 3
    assert len(live_candidates) == 2
    assert not any(isinstance(item, PortfolioSelection) for item in records)
