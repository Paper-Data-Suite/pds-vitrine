from __future__ import annotations

import builtins
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from vitrine.development_adapters import (
    CONCORD_FIXTURE_SUPPORT_REQUEST,
    QUILLAN_FIXTURE_SUPPORT_REQUEST,
    SCOREFORM_FIXTURE_SUPPORT_REQUEST,
    build_development_fixture_adapter_registry,
)
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "producer-adapters"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name / "manifest.json").read_bytes()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


class _WrappedAdapter:
    def __init__(self, base: object, declaration: ProducerProjectionAdapterDeclaration) -> None:
        self._base = base
        self._declaration = declaration

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return self._declaration

    @property
    def reader(self) -> object:
        return self._base.reader  # type: ignore[attr-defined]

    def project(self, public_model: object) -> object:
        return self._base.project(public_model)  # type: ignore[attr-defined]


def test_support_request_is_immutable_and_capabilities_are_deterministic() -> None:
    request = ProducerAdapterSupportRequest(
        producer_module_id="fixture_module",
        core_publication_schema_version="1",
        publication_kind="academic_result_set",
        manifest_contract_version="fixture_manifest_v1",
        producer_contract_version="fixture_work_v1",
        source_record_kind=None,
        source_record_contract_version=None,
        capabilities=("question_evidence", "points", "multiple_attempts"),
    )
    assert request.capabilities == ("multiple_attempts", "points", "question_evidence")
    with pytest.raises(FrozenInstanceError):
        request.publication_kind = "intervention_record_set"  # type: ignore[misc]


def test_support_key_distinguishes_absent_and_unversioned_source_record() -> None:
    absent = ProducerAdapterSupportKey(
        producer_module_id="fixture_module",
        core_publication_schema_version="1",
        publication_kind="academic_result_set",
        manifest_contract_version="fixture_manifest_v1",
        producer_contract_version="fixture_work_v1",
        source_record_kind=None,
        source_record_contract_version=None,
        required_capabilities=(),
    )
    unversioned = replace(absent, source_record_kind="submission")
    assert absent != unversioned
    assert absent.source_record_kind is None
    assert unversioned.source_record_kind == "submission"
    assert unversioned.source_record_contract_version is None


def test_support_request_rejects_version_without_source_record() -> None:
    with pytest.raises(ProducerAdapterError) as raised:
        ProducerAdapterSupportRequest(
            producer_module_id="fixture_module",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="fixture_manifest_v1",
            producer_contract_version="fixture_work_v1",
            source_record_kind=None,
            source_record_contract_version="submission_v1",
            capabilities=(),
        )
    assert raised.value.code == "adapter.invalid_support_request"


def test_support_request_rejects_wildcard_contracts() -> None:
    with pytest.raises(ProducerAdapterError) as raised:
        replace(SCOREFORM_FIXTURE_SUPPORT_REQUEST, manifest_contract_version="*")
    assert raised.value.code == "adapter.invalid_support_request"


def test_default_registry_contains_completed_live_adapters_and_rejects_fixture_injection() -> None:
    ordinary = build_adapter_registry()
    assert tuple(item.declaration.adapter_id for item in ordinary.adapters) == (
        "vitrine_concord_live_adapter",
        "vitrine_quillan_live_adapter",
        "vitrine_scoreform_live_adapter",
    )
    assert all(
        item.declaration.integration_kind == "live" for item in ordinary.adapters
    )
    assert {
        item.declaration.support_key.producer_module_id for item in ordinary.adapters
    } == {"concord", "quillan", "scoreform"}
    fixture_adapter = build_development_fixture_adapter_registry().adapters[0]
    with pytest.raises(ProducerAdapterError) as raised:
        build_adapter_registry(adapters=(fixture_adapter,))
    assert raised.value.code == "adapter.fixture_not_enabled"


def test_development_registry_order_is_deterministic() -> None:
    registry = build_development_fixture_adapter_registry()
    reversed_registry = ProducerProjectionAdapterRegistry(
        adapters=tuple(reversed(registry.adapters))
    )
    assert [item.declaration.identity for item in registry.adapters] == [
        item.declaration.identity for item in reversed_registry.adapters
    ]


def test_duplicate_adapter_identity_is_rejected() -> None:
    base = build_development_fixture_adapter_registry().adapters[0]
    duplicate = _WrappedAdapter(base, base.declaration)
    with pytest.raises(ProducerAdapterError) as raised:
        ProducerProjectionAdapterRegistry(adapters=(base, duplicate))
    assert raised.value.code == "adapter.duplicate_identity"


def test_identical_support_claim_is_conflict_not_tiebroken() -> None:
    registry = build_development_fixture_adapter_registry()
    base = registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    competing = _WrappedAdapter(
        base,
        replace(base.declaration, adapter_id="vitrine_scoreform_fixture_competitor"),
    )
    conflicted = ProducerProjectionAdapterRegistry(adapters=(competing, base))
    with pytest.raises(ProducerAdapterError) as raised:
        conflicted.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    assert raised.value.code == "adapter.conflict"
    assert "matching_adapters" in dict(raised.value.diagnostic_fields)


def test_overlapping_capability_claim_is_conflict() -> None:
    registry = build_development_fixture_adapter_registry()
    base = registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    broad_key = replace(base.declaration.support_key, required_capabilities=("points",))
    competing = _WrappedAdapter(
        base,
        replace(
            base.declaration,
            adapter_id="vitrine_scoreform_fixture_broad",
            support_key=broad_key,
        ),
    )
    conflicted = ProducerProjectionAdapterRegistry(adapters=(base, competing))
    with pytest.raises(ProducerAdapterError) as raised:
        conflicted.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    assert raised.value.code == "adapter.conflict"


def test_newest_or_highest_adapter_version_does_not_break_conflict() -> None:
    registry = build_development_fixture_adapter_registry()
    base = registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    competing = _WrappedAdapter(
        base,
        replace(
            base.declaration,
            adapter_id="vitrine_scoreform_fixture_newer",
            adapter_contract_version="vitrine_fixture_adapter_v99",
        ),
    )
    conflicted = ProducerProjectionAdapterRegistry(adapters=(base, competing))
    with pytest.raises(ProducerAdapterError) as raised:
        conflicted.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    assert raised.value.code == "adapter.conflict"


def test_unknown_contract_is_structured_and_never_falls_back_to_a_reader() -> None:
    registry = build_development_fixture_adapter_registry()
    unknown = replace(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST,
        manifest_contract_version="vitrine_fixture_unknown_manifest_v1",
    )
    with pytest.raises(ProducerAdapterError) as raised:
        registry.select_adapter(unknown)
    assert raised.value.code == "adapter.unsupported_contract"
    assert raised.value.producer_module_id == "vitrine_scoreform_fixture"
    fields = dict(raised.value.diagnostic_fields)
    assert fields["manifest_contract_version"] == "vitrine_fixture_unknown_manifest_v1"
    assert "student" not in str(raised.value).lower()


def test_fixture_reader_requires_immutable_bytes() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(bytearray(_fixture("scoreform")))  # type: ignore[arg-type]
    assert raised.value.code == "reader.validation_failed"


def test_fixture_reader_rejects_duplicate_keys_as_decode_failure() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    malformed = b'{"fixture_contract":"a","fixture_contract":"b"}\n'
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(malformed)
    assert raised.value.code == "reader.decode_failed"


def test_fixture_reader_rejects_unknown_fields_as_validation_failure() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    data = json.loads(_fixture("scoreform"))
    data["unknown"] = "not allowed"
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(_canonical(data))
    assert raised.value.code == "reader.validation_failed"


def test_fixture_reader_rejects_missing_fields_as_validation_failure() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    data = json.loads(_fixture("scoreform"))
    del data["attempts"]
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(_canonical(data))
    assert raised.value.code == "reader.validation_failed"


def test_fixture_reader_rejects_noncanonical_bytes() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    data = json.loads(_fixture("scoreform"))
    noncanonical = json.dumps(data, indent=2).encode() + b"\n"
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(noncanonical)
    assert raised.value.code == "reader.validation_failed"


def test_fixture_reader_performs_no_filesystem_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _fixture("scoreform")
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )

    def fail_open(*_: object, **__: object) -> object:
        raise AssertionError("fixture reader attempted filesystem access")

    monkeypatch.setattr(builtins, "open", fail_open)
    monkeypatch.setattr(Path, "open", fail_open)
    adapter.reader.read(payload)


def test_scoreform_projection_preserves_attempts_and_response_states() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    batch = adapter.project(adapter.reader.read(_fixture("scoreform")))
    assert len(batch.projected_sources) == 2
    assert {item.producer_source.native_revision for item in batch.projected_sources} == {1, 2}
    states = {
        value
        for item in batch.projected_sources
        for field in item.display_snapshot.fields
        if field.key == "response_states"
        for value in field.value
    }
    assert "2:blank" in states
    assert "3:ambiguous" in states
    field_maps = [
        {field.key: field.value for field in item.display_snapshot.fields}
        for item in batch.projected_sources
    ]
    assert {fields["class_id"] for fields in field_maps} == {"english10_p2"}
    assert {fields["provenance_kind"] for fields in field_maps} == {
        "pds2_scan",
        "scan_review_manual",
    }
    assert {fields["provenance_source_revision"] for fields in field_maps} == {3, 4}
    rendered = repr(batch)
    for prohibited in (
        "PRIVATE_ANSWER_KEY_DO_NOT_PROJECT",
        "PRIVATE_DETECTOR_INTERNAL_DO_NOT_PROJECT",
        "PRIVATE_ROUTE_QR_DO_NOT_PROJECT",
        "PRIVATE_SCAN_REVIEW_NOTE_DO_NOT_PROJECT",
        "private/scans",
    ):
        assert prohibited not in rendered
    assert "grade" not in rendered.lower()
    assert "proficiency" not in rendered.lower()


def test_scoreform_fixture_cannot_claim_live_scoreform_contract() -> None:
    registry = build_development_fixture_adapter_registry()
    live = ProducerAdapterSupportRequest(
        producer_module_id="scoreform",
        core_publication_schema_version="1",
        publication_kind="academic_result_set",
        manifest_contract_version="scoreform_academic_result_manifest_v1",
        producer_contract_version="scoreform_academic_work_v1",
        source_record_kind=None,
        source_record_contract_version=None,
        capabilities=("points", "question_evidence", "multiple_attempts"),
    )
    with pytest.raises(ProducerAdapterError) as raised:
        registry.select_adapter(live)
    assert raised.value.code == "adapter.unsupported_contract"


def test_quillan_projects_only_selected_approved_work_and_student_feedback() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        QUILLAN_FIXTURE_SUPPORT_REQUEST
    )
    batch = adapter.project(adapter.reader.read(_fixture("quillan")))
    kinds = [item.projection_kind for item in batch.projected_sources]
    assert kinds.count("quillan_fixture:student_work") == 2
    assert kinds.count("quillan_fixture:student_feedback") == 1
    rendered = repr(batch)
    for excluded in (
        "evidence_candidate",
        "evidence_duplicate",
        "evidence_excluded",
        "evidence_replacement",
        "feedback_private",
        "PRIVATE_FEEDBACK_SUMMARY_DO_NOT_PROJECT",
        "PRIVATE_TEACHER_NOTE_DO_NOT_PROJECT",
        "private/quillan/reviews/student_alpha.json",
        "PRIVATE_QUILLAN_ROUTE_METADATA_DO_NOT_PROJECT",
    ):
        assert excluded not in rendered


def test_quillan_fixture_does_not_claim_live_quillan_contract() -> None:
    registry = build_development_fixture_adapter_registry()
    live_like = replace(
        QUILLAN_FIXTURE_SUPPORT_REQUEST,
        producer_module_id="quillan",
        manifest_contract_version="quillan_publication_manifest_v1",
        producer_contract_version="quillan_academic_work_v1",
    )
    with pytest.raises(ProducerAdapterError) as raised:
        registry.select_adapter(live_like)
    assert raised.value.code == "adapter.unsupported_contract"


def test_concord_preserves_membership_authorship_contribution_and_group_score() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        CONCORD_FIXTURE_SUPPORT_REQUEST
    )
    batch = adapter.project(adapter.reader.read(_fixture("concord")))
    artifact = next(
        item for item in batch.projected_sources if item.projection_kind == "concord_fixture:artifact"
    )
    member_relationships = [
        item
        for item in artifact.source_relationships
        if item.source_subject_id == "student_member_only"
    ]
    assert {item.relationship_kind for item in member_relationships} == {"group_member"}
    assert any(
        item.relationship_kind == "documented_contributor"
        and item.source_subject_id == "student_alpha"
        for item in artifact.source_relationships
    )
    score_sources = [
        item
        for item in batch.projected_sources
        if item.projection_kind == "concord_fixture:score_summary"
    ]
    assert len(score_sources) == 2
    assert all(
        {relationship.relationship_kind for relationship in item.source_relationships}
        == {"group_score_target"}
        for item in score_sources
    )
    deferred = next(
        item for item in score_sources if item.producer_source.native_disposition == "deferred"
    )
    assert not any(field.key == "native_value" for field in deferred.display_snapshot.fields)
    rendered = repr(batch).lower()
    assert "grade" not in rendered
    assert "mastery" not in rendered


def test_concord_projection_retains_collaborative_privacy_state() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        CONCORD_FIXTURE_SUPPORT_REQUEST
    )
    batch = adapter.project(adapter.reader.read(_fixture("concord")))
    artifact = next(
        item for item in batch.projected_sources if item.projection_kind == "concord_fixture:artifact"
    )
    assert artifact.source_privacy.subject_scope == "multi_subject"
    assert artifact.source_privacy.collaborator_information_present is True
    assert artifact.source_privacy.multi_subject_review_required is True


def test_concord_fixture_does_not_claim_live_concord_contract() -> None:
    registry = build_development_fixture_adapter_registry()
    live_like = replace(
        CONCORD_FIXTURE_SUPPORT_REQUEST,
        producer_module_id="concord",
        manifest_contract_version="concord_result_manifest_v1",
        producer_contract_version="concord_academic_work_v1",
    )
    with pytest.raises(ProducerAdapterError) as raised:
        registry.select_adapter(live_like)
    assert raised.value.code == "adapter.unsupported_contract"


def test_projection_provenance_and_output_are_deterministic() -> None:
    registry = build_development_fixture_adapter_registry()
    adapter = registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    first = adapter.project(adapter.reader.read(_fixture("scoreform")))
    second = adapter.project(adapter.reader.read(_fixture("scoreform")))
    assert first == second
    assert first.adapter_id == adapter.declaration.adapter_id
    assert first.adapter_contract_version == adapter.declaration.adapter_contract_version
    assert first.reader_id == adapter.declaration.public_reader_id
    assert first.reader_contract_version == adapter.declaration.reader_contract_version
    assert (
        first.candidate_projection_contract_version
        == adapter.declaration.candidate_projection_contract_version
    )


def test_projection_rejects_unvalidated_input() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST
    )
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.project({"looks": "close enough"})
    assert raised.value.code == "projection.invalid_input"


def test_reader_failure_does_not_echo_private_payload_or_absolute_path() -> None:
    adapter = build_development_fixture_adapter_registry().select_adapter(
        QUILLAN_FIXTURE_SUPPORT_REQUEST
    )
    data = json.loads(_fixture("quillan"))
    data["private_absolute_path"] = r"C:\Users\teacher\private-student-note.txt"
    payload = _canonical(data)
    with pytest.raises(ProducerAdapterError) as raised:
        adapter.reader.read(payload)
    text = str(raised.value)
    assert raised.value.code == "reader.validation_failed"
    assert "C:\\Users" not in text
    assert "private-student-note" not in text


def test_unsupported_diagnostics_are_deterministic_and_contract_only() -> None:
    registry = build_development_fixture_adapter_registry()
    unknown = replace(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST,
        manifest_contract_version="vitrine_fixture_unknown_manifest_v1",
        capabilities=("question_evidence", "points", "multiple_attempts"),
    )
    with pytest.raises(ProducerAdapterError) as raised:
        registry.select_adapter(unknown)
    error = raised.value
    assert error.code == "adapter.unsupported_contract"
    assert error.diagnostic_fields == tuple(sorted(error.diagnostic_fields))
    text = repr(error.diagnostic_fields)
    assert "student_alpha" not in text
    assert "PRIVATE_" not in text
    assert "C:\\" not in text
