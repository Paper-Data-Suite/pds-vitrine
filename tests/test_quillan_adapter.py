from __future__ import annotations

import base64
import builtins
import importlib
import io
import json
import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from vitrine import cli
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerProjectionError,
    build_adapter_registry,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND,
    QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE,
    QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
)
from vitrine.released_producer_contracts import QUILLAN_LIVE_SUPPORT_KEY

_REVIEW_ID = re.compile(r"^quillan_review_[0-9a-f]{64}$")
_PRIVATE_PROMPT = "PRIVATE_PUBLIC_PROMPT_OUTSIDE_BOUNDED_REVIEW_CONTEXT"
_UNSELECTED_MARKERS = (
    "PRIVATE_CANDIDATE_EVIDENCE",
    "PRIVATE_DUPLICATE_EVIDENCE",
    "PRIVATE_EXCLUDED_EVIDENCE",
)
_LONG_INCLUDED_TEXT = "Rationale section. " * 120


@dataclass(frozen=True)
class _Manifest:
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: object
    work: object
    source_snapshot: object
    assignment: object
    students: tuple[object, ...]


def _published(disposition: str, text: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(disposition=disposition, text=text)


def _source(path: str, digest_char: str, contract_version: str) -> SimpleNamespace:
    return SimpleNamespace(
        relative_path=path,
        sha256=digest_char * 64,
        contract_version=contract_version,
    )


def _manifest() -> _Manifest:
    rating_scale = SimpleNamespace(
        scale_id="quillan_scale_alpha",
        levels=(
            SimpleNamespace(value=1, label="Emerging", description="Minimum level."),
            SimpleNamespace(value=2, label="Developing", description="Middle level."),
            SimpleNamespace(value=3, label="Secure", description="Upper level."),
        ),
    )
    assignment = SimpleNamespace(
        assignment_id="essay_alpha",
        title="Essay Alpha",
        writing_type="literary_analysis",
        student_prompt=_PRIVATE_PROMPT,
        standards_profile_id="njsls_ela_10",
        focus_standard_ids=("RL.CR.9-10.1", "W.AW.9-10.1"),
        review_unit=SimpleNamespace(
            type="paragraph",
            singular_label="Paragraph",
            plural_label="Paragraphs",
        ),
        rating_scale=rating_scale,
        basic_requirements=SimpleNamespace(
            paragraphs_min=3,
            paragraphs_max=6,
            word_count_min=500,
            word_count_max=1200,
            required_elements=("claim", "evidence", "analysis"),
        ),
        minimum_requirement_policy=SimpleNamespace(
            allow_return_without_full_review=True
        ),
    )
    timestamp = datetime(2026, 8, 29, 14, 30, tzinfo=timezone.utc)
    observations = (
        SimpleNamespace(
            observation_id="observation_not_applicable",
            standard_id="RL.CR.9-10.1",
            applicable=False,
            evidence_present=None,
            rating=None,
            rationale=_published("absent"),
            include_in_feedback=False,
            updated_at=timestamp,
        ),
        SimpleNamespace(
            observation_id="observation_no_evidence",
            standard_id="W.AW.9-10.1",
            applicable=True,
            evidence_present=False,
            rating=None,
            rationale=_published("withheld"),
            include_in_feedback=True,
            updated_at=timestamp,
        ),
        SimpleNamespace(
            observation_id="observation_minimum_rating",
            standard_id="RL.CR.9-10.1",
            applicable=True,
            evidence_present=True,
            rating=1,
            rationale=_published("included", "Public observation rationale."),
            include_in_feedback=True,
            updated_at=timestamp,
        ),
    )
    review_units = (
        SimpleNamespace(
            unit_id="unit_second_in_label_sort",
            sequence=1,
            label="Zeta opening",
            unit_type="paragraph",
            standard_observations=observations[:2],
        ),
        SimpleNamespace(
            unit_id="unit_first_in_label_sort",
            sequence=2,
            label="Alpha closing",
            unit_type="paragraph",
            standard_observations=observations[2:],
        ),
    )
    feedback = SimpleNamespace(
        include_review_unit_observations=True,
        include_overall_standard_ratings=False,
        standard_feedback=(
            SimpleNamespace(
                standard_id="RL.CR.9-10.1",
                include_overall_rating=True,
                include_overall_rationale=False,
                included_observation_ids=("observation_minimum_rating",),
                comments=(
                    SimpleNamespace(
                        feedback_comment_id="feedback_included",
                        text=_published("included", "Public feedback comment."),
                        include_in_feedback=True,
                        created_at=timestamp,
                    ),
                    SimpleNamespace(
                        feedback_comment_id="feedback_withheld",
                        text=_published("withheld"),
                        include_in_feedback=False,
                        created_at=timestamp,
                    ),
                ),
            ),
        ),
    )
    alpha_review = SimpleNamespace(
        class_id="english10_p2",
        assignment_id="essay_alpha",
        student_id="student_alpha",
        review_state="ratings_complete",
        minimum_requirement_outcome=SimpleNamespace(
            status="unmet_continue_review",
            returned_without_full_review=False,
            updated_at=timestamp,
            teacher_note=_published("withheld"),
        ),
        review_units=review_units,
        overall_standard_ratings=(
            SimpleNamespace(
                standard_id="RL.CR.9-10.1",
                rating=1,
                rationale=_published("included", _LONG_INCLUDED_TEXT),
                include_in_feedback=True,
                updated_at=timestamp,
            ),
        ),
        feedback=feedback,
    )
    evidence_references = (
        SimpleNamespace(
            page_id="pg_44444444444444444444444444444444",
            evidence_id="evidence_selected_alpha_1",
            observation_id="obs_66666666666666666666666666666666",
            route_id="rt_77777777777777777777777777777777",
            issuance_id="iss_11111111111111111111111111111111",
            generation_id="gen_22222222222222222222222222222222",
            artifact_id="art_33333333333333333333333333333333",
            source_page_number=2,
            source_scan_id="scan_alpha",
            source_sha256="7" * 64,
            routed_evidence_sha256="8" * 64,
        ),
        SimpleNamespace(
            page_id="pg_55555555555555555555555555555555",
            evidence_id="evidence_selected_alpha_2",
            observation_id="obs_99999999999999999999999999999999",
            route_id="rt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            issuance_id="iss_11111111111111111111111111111111",
            generation_id="gen_22222222222222222222222222222222",
            artifact_id="art_33333333333333333333333333333333",
            source_page_number=3,
            source_scan_id="scan_alpha",
            source_sha256="7" * 64,
            routed_evidence_sha256="9" * 64,
        ),
    )
    alpha = SimpleNamespace(
        student_id="student_alpha",
        source_snapshot=SimpleNamespace(
            submission=_source(
                "students/student_alpha/submission.json", "c", "1"
            ),
            review=_source("students/student_alpha/review.json", "d", "2"),
        ),
        submission=SimpleNamespace(
            class_id="english10_p2",
            assignment_id="essay_alpha",
            student_id="student_alpha",
            submission_state="reviewed",
            entry_method="pds2_response_pages",
            expected_pages=2,
            digital_provenance=SimpleNamespace(
                issuance_id="iss_11111111111111111111111111111111",
                generation_id="gen_22222222222222222222222222222222",
                artifact_id="art_33333333333333333333333333333333",
                expected_page_ids=(
                    "pg_44444444444444444444444444444444",
                    "pg_55555555555555555555555555555555",
                ),
                evidence_references=evidence_references,
            ),
        ),
        review=alpha_review,
    )
    beta = SimpleNamespace(
        student_id="student_beta",
        source_snapshot=SimpleNamespace(
            submission=_source("students/student_beta/submission.json", "e", "1"),
            review=_source("students/student_beta/review.json", "f", "2"),
        ),
        submission=SimpleNamespace(
            class_id="english10_p2",
            assignment_id="essay_alpha",
            student_id="student_beta",
            submission_state="reviewed",
            entry_method="plain_paper_manual",
            expected_pages=None,
            digital_provenance=None,
        ),
        review=SimpleNamespace(
            class_id="english10_p2",
            assignment_id="essay_alpha",
            student_id="student_beta",
            review_state="returned_without_full_review",
            minimum_requirement_outcome=SimpleNamespace(
                status="returned_without_full_review",
                returned_without_full_review=True,
                updated_at=timestamp,
                teacher_note=_published("included", "Return for revision."),
            ),
            review_units=(),
            overall_standard_ratings=(),
            feedback=SimpleNamespace(
                include_review_unit_observations=False,
                include_overall_standard_ratings=False,
                standard_feedback=(),
            ),
        ),
    )
    return _Manifest(
        record_type="quillan_academic_result_manifest",
        contract_version="quillan_academic_result_manifest_v1",
        producer_module_id="quillan",
        generated_at=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
        record_set=SimpleNamespace(record_set_id="academic_results", revision=7),
        work=SimpleNamespace(
            module_id="quillan", class_id="english10_p2", work_id="essay_alpha"
        ),
        source_snapshot=_source("assignment.json", "b", "2"),
        assignment=assignment,
        students=(alpha, beta),
    )


def _import_quillan_adapter_without_producer_import(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "quillan" or name.startswith("quillan."):
            raise AssertionError("Quillan package import must remain lazy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("vitrine.quillan_adapter", None)
    return importlib.import_module("vitrine.quillan_adapter")


def _project(monkeypatch: pytest.MonkeyPatch, manifest: object | None = None) -> Any:
    import vitrine.quillan_adapter as quillan_adapter

    monkeypatch.setattr(
        quillan_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest)
        if name == "quillan.academic_result_manifest"
        else None,
    )
    return quillan_adapter.build_quillan_live_adapter().project(
        _manifest() if manifest is None else manifest
    )


def _source_for(batch: Any, student_id: str) -> Any:
    return next(
        source
        for source in batch.projected_sources
        if source.projection_kind == QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND
        and source.source_relationships[0].source_subject_id == student_id
    )


def _sources_for_kind(batch: Any, projection_kind: str) -> tuple[Any, ...]:
    return tuple(
        source
        for source in batch.projected_sources
        if source.projection_kind == projection_kind
    )


def _fields(source: Any) -> dict[str, object]:
    return {field.key: field.value for field in source.display_snapshot.fields}


def _payload(source: Any) -> dict[str, Any]:
    chunks = _fields(source)["review_payload_json_base64_chunks"]
    assert isinstance(chunks, tuple)
    assert all(isinstance(chunk, str) and len(chunk) <= 900 for chunk in chunks)
    encoded = "".join(chunks).encode("ascii")
    return json.loads(base64.b64decode(encoded).decode("utf-8"))


def test_live_declaration_uses_frozen_quillan_contract_and_installed_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _import_quillan_adapter_without_producer_import(monkeypatch)
    declaration = module.QUILLAN_LIVE_ADAPTER_DECLARATION
    adapter = module.build_quillan_live_adapter()

    assert declaration.adapter_id == "vitrine_quillan_live_adapter"
    assert declaration.adapter_contract_version == "vitrine_quillan_live_adapter_v1"
    assert declaration.candidate_projection_contract_version == (
        "vitrine_candidate_projection_v1"
    )
    assert declaration.support_key is QUILLAN_LIVE_SUPPORT_KEY
    assert declaration.support_key.source_record_kind is None
    assert declaration.support_key.source_record_contract_version is None
    assert declaration.integration_kind == "live"
    assert declaration.supported_source_families == (
        "assessment_result",
        "feedback",
        "student_work",
    )
    assert declaration.supported_representation_families == (
        "feedback",
        "result_summary",
        "student_work",
    )
    assert declaration.diagnostic_contract_version == "vitrine_adapter_diagnostic_v1"
    assert declaration.public_reader_id == (
        "vitrine_installed_quillan_academic_result_reader"
    )
    assert declaration.reader_contract_version == (
        "quillan_academic_result_reader_v1"
    )
    assert declaration.reader_package_identity == "quillan"
    assert adapter.declaration is declaration
    assert adapter.reader.descriptor.public_reader_id == declaration.public_reader_id


def test_live_module_and_adapter_construction_do_not_import_quillan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        name
        for name in sys.modules
        if name == "quillan" or name.startswith("quillan.")
    }
    module = _import_quillan_adapter_without_producer_import(monkeypatch)
    adapter = module.build_quillan_live_adapter()
    _ = adapter.declaration
    _ = adapter.reader.descriptor
    after = {
        name
        for name in sys.modules
        if name == "quillan" or name.startswith("quillan.")
    }
    assert after == before


def test_live_adapter_show_is_available_without_importing_quillan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.quillan_adapter as quillan_adapter

    def forbidden_import(_name: str) -> object:
        raise AssertionError("adapter diagnostics must not import Quillan")

    monkeypatch.setattr(quillan_adapter, "import_module", forbidden_import)
    output = io.StringIO()
    error = io.StringIO()
    assert (
        cli.main(
            ["adapters", "show", "vitrine_quillan_live_adapter"],
            output=output,
            error=error,
        )
        == 0
    )
    text = output.getvalue()
    assert "Integration kind: live" in text
    assert "Producer module: quillan" in text
    assert "quillan_academic_result_manifest_v1" in text
    assert "vitrine_installed_quillan_academic_result_reader" in text
    assert "Required capabilities: standards_ratings" in text
    assert "student_" not in text
    assert error.getvalue() == ""


def test_default_registry_matches_exact_quillan_support_and_rejects_mismatch() -> None:
    key = QUILLAN_LIVE_SUPPORT_KEY
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
    selected = registry.select_adapter(request)
    assert selected.declaration.adapter_id == "vitrine_quillan_live_adapter"

    wrong = replace(request, source_record_kind="assignment")
    with pytest.raises(ProducerAdapterError) as caught:
        registry.select_adapter(wrong)
    assert caught.value.code == "adapter.unsupported_contract"


def test_projection_resolves_only_public_manifest_contract_not_artifact_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.quillan_adapter as quillan_adapter

    imported: list[str] = []

    def resolve(name: str) -> object:
        imported.append(name)
        if name == "quillan.academic_result_manifest":
            return SimpleNamespace(AcademicResultManifest=_Manifest)
        raise AssertionError(f"unexpected Quillan import: {name}")

    monkeypatch.setattr(quillan_adapter, "import_module", resolve)
    quillan_adapter.build_quillan_live_adapter().project(_manifest())
    assert imported == ["quillan.academic_result_manifest"]


def test_projection_emits_one_logical_review_summary_per_student_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    reviews = _sources_for_kind(batch, QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND)
    assert len(reviews) == 2
    assert {
        source.source_relationships[0].source_subject_id for source in reviews
    } == {"student_alpha", "student_beta"}

    for source in reviews:
        relationship = source.source_relationships[0]
        assert source.projection_kind == QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND
        assert source.source_artifact.artifact_kind == (
            QUILLAN_REVIEW_SUMMARY_ARTIFACT_KIND
        )
        assert source.source_artifact.media_type == QUILLAN_REVIEW_SUMMARY_MEDIA_TYPE
        assert source.source_artifact.source_locator is None
        assert source.source_artifact.source_digest is None
        assert source.source_artifact.byte_size is None
        assert relationship.source_subject_kind == "core_student"
        assert relationship.relationship_kind == "submission_subject"
        assert relationship.relationship_authority == "quillan"
        assert _REVIEW_ID.fullmatch(source.producer_source.source_record_id)
        assert source.producer_source.native_revision == 7
        assert source.source_privacy.subject_scope == "single_subject"
        assert source.source_privacy.minimum_necessary_projection_required is True


def test_projection_preserves_review_requirements_scale_and_null_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_for(_project(monkeypatch), "student_alpha")
    fields = _fields(source)
    payload = _payload(source)

    assert fields["review_state"] == "ratings_complete"
    assert fields["minimum_requirement_status"] == "unmet_continue_review"
    assert fields["minimum_requirement_returned_without_full_review"] is False
    assert fields["rating_scale_id"] == "quillan_scale_alpha"
    assert fields["rating_scale_values"] == (1, 2, 3)
    assert fields["review_unit_ids"] == (
        "unit_second_in_label_sort",
        "unit_first_in_label_sort",
    )
    assert fields["review_unit_sequences"] == (1, 2)
    assert fields["observation_applicable"] == (False, True, True)
    assert fields["observation_evidence_present"] == (None, False, True)
    assert fields["observation_ratings"] == (None, None, 1)
    assert fields["overall_rating_values"] == (1,)

    assignment = payload["assignment"]
    assert [level["value"] for level in assignment["rating_scale"]["levels"]] == [
        1,
        2,
        3,
    ]
    assert assignment["basic_requirements"] == {
        "paragraphs_max": 6,
        "paragraphs_min": 3,
        "required_elements": ["claim", "evidence", "analysis"],
        "word_count_max": 1200,
        "word_count_min": 500,
    }
    assert assignment["minimum_requirement_policy"] == {
        "allow_return_without_full_review": True
    }
    units = payload["review"]["review_units"]
    assert [unit["unit_id"] for unit in units] == [
        "unit_second_in_label_sort",
        "unit_first_in_label_sort",
    ]


def test_projection_preserves_published_text_and_feedback_without_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_for(_project(monkeypatch), "student_alpha")
    fields = _fields(source)
    payload = _payload(source)

    assert fields["minimum_requirement_teacher_note_disposition"] == "withheld"
    assert fields["observation_rationale_dispositions"] == (
        "absent",
        "withheld",
        "included",
    )
    assert fields["overall_rating_rationale_dispositions"] == ("included",)
    assert fields["feedback_comment_text_dispositions"] == (
        "included",
        "withheld",
    )
    minimum = payload["review"]["minimum_requirement_outcome"]
    assert minimum["teacher_note"] == {"disposition": "withheld", "text": None}
    observations = [
        observation
        for unit in payload["review"]["review_units"]
        for observation in unit["standard_observations"]
    ]
    assert observations[0]["rationale"] == {"disposition": "absent", "text": None}
    assert observations[1]["rationale"] == {
        "disposition": "withheld",
        "text": None,
    }
    assert observations[2]["rationale"]["text"] == "Public observation rationale."
    overall = payload["review"]["overall_standard_ratings"][0]
    assert overall["rating"] == 1
    assert overall["rationale"]["text"] == _LONG_INCLUDED_TEXT
    feedback = payload["review"]["feedback"]
    assert feedback["include_review_unit_observations"] is True
    assert feedback["include_overall_standard_ratings"] is False
    standard_feedback = feedback["standard_feedback"][0]
    assert standard_feedback["include_overall_rating"] is True
    assert standard_feedback["include_overall_rationale"] is False
    assert standard_feedback["included_observation_ids"] == [
        "observation_minimum_rating"
    ]
    assert standard_feedback["comments"][1]["text"] == {
        "disposition": "withheld",
        "text": None,
    }


def test_projection_preserves_source_lineage_without_authorizing_native_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_for(_project(monkeypatch), "student_alpha")
    fields = _fields(source)
    payload = _payload(source)

    assert fields["assignment_source_relative_path"] == "assignment.json"
    assert fields["assignment_source_sha256"] == "b" * 64
    assert fields["submission_source_relative_path"] == (
        "students/student_alpha/submission.json"
    )
    assert fields["submission_source_sha256"] == "c" * 64
    assert fields["review_source_relative_path"] == "students/student_alpha/review.json"
    assert fields["review_source_sha256"] == "d" * 64
    assert source.source_artifact.source_locator is None
    assert payload["student_source_snapshot"]["review"]["relative_path"] == (
        "students/student_alpha/review.json"
    )


def test_selected_pds2_evidence_projects_independently_in_public_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    evidence_sources = _sources_for_kind(
        batch, QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND
    )
    assert len(evidence_sources) == 2
    assert {
        source.source_relationships[0].source_subject_id
        for source in evidence_sources
    } == {"student_alpha"}
    ordered = sorted(evidence_sources, key=lambda item: _fields(item)["evidence_sequence"])
    assert [_fields(source)["evidence_id"] for source in ordered] == [
        "evidence_selected_alpha_1",
        "evidence_selected_alpha_2",
    ]
    assert [_fields(source)["evidence_sequence"] for source in ordered] == [1, 2]

    first = ordered[0]
    fields = _fields(first)
    assert fields["artifact_request_kind"] == "student_work"
    assert fields["page_id"] == "pg_44444444444444444444444444444444"
    assert fields["observation_id"] == "obs_66666666666666666666666666666666"
    assert fields["route_id"] == "rt_77777777777777777777777777777777"
    assert fields["source_page_number"] == 2
    assert fields["source_scan_id"] == "scan_alpha"
    assert fields["source_sha256"] == "7" * 64
    assert fields["routed_evidence_sha256"] == "8" * 64
    assert first.source_artifact.artifact_kind == "original_student_work"
    assert first.source_artifact.media_type == QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE
    assert first.source_artifact.source_locator is None
    assert first.source_artifact.source_digest is None
    assert first.source_artifact.byte_size is None
    assert re.fullmatch(r"quillan_evidence_[0-9a-f]{64}", first.source_artifact.artifact_id)


def test_feedback_capabilities_are_distinct_exact_representations_without_existence_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    pdf_sources = _sources_for_kind(batch, QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND)
    markdown_sources = _sources_for_kind(
        batch, QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND
    )
    assert len(pdf_sources) == 2
    assert len(markdown_sources) == 2

    for source in pdf_sources:
        assert source.source_artifact.artifact_kind == "rendered_feedback"
        assert source.source_artifact.media_type == QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
        assert _fields(source)["artifact_request_kind"] == "feedback_pdf"
        assert source.source_artifact.source_locator is None
        assert source.source_artifact.source_digest is None
        assert source.source_artifact.byte_size is None
        assert re.fullmatch(
            r"quillan_feedback_[0-9a-f]{64}", source.source_artifact.artifact_id
        )

    for source in markdown_sources:
        assert source.source_artifact.artifact_kind == "rendered_feedback"
        assert source.source_artifact.media_type == QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
        assert _fields(source)["artifact_request_kind"] == "feedback_markdown"
        assert source.source_artifact.source_locator is None
        assert source.source_artifact.source_digest is None
        assert source.source_artifact.byte_size is None

    rendered = repr((*pdf_sources, *markdown_sources)).lower()
    assert "available=true" not in rendered
    assert "artifact_exists" not in rendered


def test_slice2_projection_uses_only_public_selected_evidence_and_no_artifact_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _project(monkeypatch)
    rendered = repr(batch)
    for marker in _UNSELECTED_MARKERS:
        assert marker not in rendered
    assert _PRIVATE_PROMPT not in rendered
    assert "routed_evidence_path" not in rendered
    assert "feedback_pdf_path" not in rendered
    assert "feedback_markdown_path" not in rendered



def test_plain_paper_result_remains_distinct_without_fabricated_digital_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_for(_project(monkeypatch), "student_beta")
    fields = _fields(source)
    payload = _payload(source)

    assert fields["submission_entry_method"] == "plain_paper_manual"
    assert fields["submission_expected_pages"] is None
    assert fields["review_state"] == "returned_without_full_review"
    assert fields["minimum_requirement_status"] == "returned_without_full_review"
    assert payload["submission"]["digital_provenance"] is None
    assert source.source_artifact.artifact_kind == "assessment_summary"
    assert source.source_artifact.source_locator is None

    beta_sources = tuple(
        item
        for item in _project(monkeypatch).projected_sources
        if item.source_relationships[0].source_subject_id == "student_beta"
    )
    assert all(
        item.projection_kind != QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND
        for item in beta_sources
    )
    assert {
        item.projection_kind for item in beta_sources
    } == {
        QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND,
        QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
        QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    }


def test_artifact_capability_identity_does_not_depend_on_native_rating_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _project(monkeypatch)
    changed = _manifest()
    alpha = changed.students[0]
    alpha.review.overall_standard_ratings[0].rating = 3
    alpha.review.review_units[1].standard_observations[0].rating = 3
    projected = _project(monkeypatch, changed)

    def capability_ids(batch: Any) -> set[str]:
        return {
            source.producer_source.source_record_id
            for source in batch.projected_sources
            if source.projection_kind
            in {
                QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
                QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
                QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
            }
        }

    assert capability_ids(baseline) == capability_ids(projected)


def test_projection_does_not_normalize_native_ratings_into_consumer_judgments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = repr(_project(monkeypatch)).lower()
    for prohibited in (
        "percentage",
        "proficiency",
        "mastery",
        "portfolio_score",
        "candidate_score",
        "letter_grade",
    ):
        assert prohibited not in rendered


def test_adapter_rejects_non_quillan_public_model_with_safe_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.quillan_adapter as quillan_adapter

    monkeypatch.setattr(
        quillan_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest),
    )
    with pytest.raises(ProducerProjectionError) as caught:
        quillan_adapter.build_quillan_live_adapter().project(object())
    assert caught.value.code == "projection.invalid_input"
    assert caught.value.stage == "projection"
    assert "student_alpha" not in str(caught.value)

def test_issue104_future_quillan_reader_projects_public_candidate_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A future distribution retains the live public reader and adapter path."""
    from pds_core.publication_compatibility import (
        PublicationContractSupport,
        PublicationProducerProfile,
        PublicationReaderSupport,
    )

    import vitrine.producer_reader_compatibility as compatibility
    import vitrine.producer_reader_services as reader_services
    from vitrine.producer_reader_services import build_audited_installed_producer_reader
    from vitrine.released_producer_contracts import (
        RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    )

    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["quillan"]
    key = audit.support_key
    future_version = "99.123.456"
    assert audit.release_version != future_version
    profile = PublicationProducerProfile(
        module_id="quillan",
        display_name="Synthetic future Quillan",
        supported_core_publication_schema_versions=frozenset(
            {key.core_publication_schema_version}
        ),
        supported_academic_work_contract_versions=frozenset(
            {key.producer_contract_version}
            if key.producer_contract_version is not None
            else ()
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind=key.publication_kind,
                manifest_contract_versions=frozenset({key.manifest_contract_version}),
                supported_capabilities=frozenset(audit.advertised_capabilities),
                reader_support=(
                    PublicationReaderSupport(
                        manifest_contract_version=key.manifest_contract_version,
                        distribution_name=audit.distribution_name,
                        reader_contract_version="quillan_academic_result_reader_v1",
                    ),
                ),
            ),
        ),
    )
    calls: list[bytes] = []

    def public_reader(payload: bytes) -> _Manifest:
        calls.append(payload)
        return _manifest()

    monkeypatch.setattr(reader_services.metadata, "version", lambda _name: future_version)
    monkeypatch.setattr(
        compatibility,
        "discover_publication_producer_profiles",
        lambda: (profile,),
    )
    monkeypatch.setattr(
        reader_services,
        "import_module",
        lambda _name: SimpleNamespace(**{audit.public_reader_symbol: public_reader}),
    )

    reader = build_audited_installed_producer_reader("quillan")
    manifest_bytes = b'{"synthetic_future_quillan":true}'
    public_model = reader.read(manifest_bytes)
    assert calls == [manifest_bytes]
    assert isinstance(public_model, _Manifest)

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
    adapter = build_adapter_registry().select_adapter(request)
    assert adapter.declaration.adapter_id == "vitrine_quillan_live_adapter"

    import vitrine.quillan_adapter as quillan_adapter

    monkeypatch.setattr(
        quillan_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest)
        if name == "quillan.academic_result_manifest"
        else None,
    )
    batch = adapter.project(public_model)
    review_sources = _sources_for_kind(batch, QUILLAN_REVIEW_SUMMARY_REPRESENTATION_KIND)
    assert {source.source_relationships[0].source_subject_id for source in review_sources} == {
        "student_alpha",
        "student_beta",
    }
    assert len(_sources_for_kind(batch, QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND)) == 2
    rendered = repr(batch)
    assert _PRIVATE_PROMPT not in rendered
    for private_marker in _UNSELECTED_MARKERS:
        assert private_marker not in rendered

def test_issue104_future_quillan_canonical_candidate_and_guided_curation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A future stable-contract Quillan reader reaches persisted teacher curation.

    Canonical Core storage, discovery, Candidate persistence, and guided curation
    are real. The manifest bytes and public Quillan model remain test fixtures;
    this is not an installed producer package or Artifact-byte integration test.
    """
    from pds_core.academic_catalog import (
        PublicationCatalogQuery,
        rebuild_academic_catalog,
    )
    from pds_core.publication_compatibility import (
        PublicationContractSupport,
        PublicationProducerProfile,
        PublicationProducerRegistry,
        PublicationReaderSupport,
    )

    import vitrine.producer_reader_compatibility as compatibility
    import vitrine.producer_reader_services as reader_services
    from scripts.candidate_fixture_support import (
        ACTOR,
        DeterministicIds,
        StaticAuthorizationGate,
        _publish_fixture,
        build_candidate_fixture_workspace,
        fixed_clock,
    )
    from scripts.curation_fixture_support import StaticCurationAuthorityGate
    from vitrine.candidate_review import (
        execute_candidate_decision,
        execute_selection_placement,
        plan_candidate_decision,
        plan_selection_placement,
    )
    from vitrine.candidate_services import (
        CandidateDiscoveryRequest,
        discover_and_evaluate_candidates,
    )
    from vitrine.models import (
        PortfolioCandidate,
        PortfolioPlacement,
        PortfolioSelection,
    )
    from vitrine.producer_adapters import build_adapter_registry
    from vitrine.released_producer_contracts import (
        RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    )
    from vitrine.storage import load_current_records

    setup = build_candidate_fixture_workspace(tmp_path)
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["quillan"]
    key = audit.support_key
    contract = "quillan_academic_result_reader_v1"
    future_version = "99.123.456"
    profile = PublicationProducerProfile(
        module_id="quillan",
        display_name="Synthetic stable-contract future Quillan",
        supported_core_publication_schema_versions=frozenset(
            {key.core_publication_schema_version}
        ),
        supported_academic_work_contract_versions=frozenset(
            {key.producer_contract_version}
            if key.producer_contract_version is not None
            else ()
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind=key.publication_kind,
                manifest_contract_versions=frozenset(
                    {key.manifest_contract_version}
                ),
                supported_capabilities=frozenset({"standards_ratings"}),
                allows_missing_source_record=True,
                reader_support=(
                    PublicationReaderSupport(
                        manifest_contract_version=key.manifest_contract_version,
                        distribution_name=audit.distribution_name,
                        reader_contract_version=contract,
                    ),
                ),
            ),
        ),
    )
    publication_id, manifest_path = _publish_fixture(
        setup.workspace,
        module_id="quillan",
        work_id="essay_alpha",
        producer_contract_version="quillan_academic_work_v1",
        manifest_contract_version="quillan_academic_result_manifest_v1",
        fixture_path=(
            Path(__file__).resolve().parents[1]
            / "fixtures/producer-adapters/quillan/manifest.json"
        ),
        source_record=None,
        capabilities=("standards_ratings",),
        record_set_id="issue104_future_quillan",
    )
    rebuild_academic_catalog(setup.workspace)

    # The metadata announces a future package version but retains the exact
    # supported reader contract and public API; the package itself is not installed.
    read_calls: list[bytes] = []

    def public_read(payload: bytes) -> object:
        read_calls.append(payload)
        return _manifest()

    monkeypatch.setattr(
        reader_services.metadata, "version", lambda _name: future_version
    )
    monkeypatch.setattr(
        compatibility,
        "discover_publication_producer_profiles",
        lambda: (profile,),
    )
    monkeypatch.setattr(
        reader_services,
        "import_module",
        lambda _name: SimpleNamespace(**{audit.public_reader_symbol: public_read}),
    )
    import vitrine.quillan_adapter as quillan_adapter

    monkeypatch.setattr(
        quillan_adapter,
        "import_module",
        lambda name: SimpleNamespace(AcademicResultManifest=_Manifest)
        if name == "quillan.academic_result_manifest"
        else None,
    )
    gate = StaticAuthorizationGate("allowed")
    discovery = discover_and_evaluate_candidates(
        setup.workspace,
        CandidateDiscoveryRequest(
            portfolio_id=setup.portfolio_id,
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="quillan", state="current", limit=10
            ),
            expected_state_revision=setup.state_revision,
        ),
        producer_registry=PublicationProducerRegistry(profiles=(profile,)),
        adapter_registry=build_adapter_registry(),
        authorization_gate=gate,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert discovery.findings == ()
    assert len(read_calls) == 1
    assert read_calls[0] == manifest_path.read_bytes()
    assert len(gate.requests) == 1
    assert gate.requests[0].publication_id == publication_id

    candidates = tuple(
        result.candidate
        for result in discovery.evaluation_results
        if result.candidate is not None
    )
    assert candidates
    assert all(
        item.source_endpoint.core_publication.publication_id == publication_id
        and item.source_endpoint.producer_source.producer_module_id == "quillan"
        and item.source_endpoint.producer_source.reader_contract_version == contract
        for item in candidates
    )
    work = tuple(item for item in candidates if "student_work" in item.eligible_section_ids)
    feedback = tuple(
        item for item in candidates if "feedback_context" in item.eligible_section_ids
    )
    assert len(work) == 2
    assert len(feedback) == 2
    assert {item.candidate_id for item in work}.isdisjoint(
        {item.candidate_id for item in feedback}
    )
    assert all(
        item.candidate is None
        for item in discovery.evaluation_results
        if item.projected_source.source_relationships[0].source_subject_id
        == "student_beta"
    )

    before_curation = load_current_records(setup.workspace)
    assert not any(isinstance(item, PortfolioSelection) for item in before_curation)
    assert not any(isinstance(item, PortfolioPlacement) for item in before_curation)

    for candidate, section in ((work[0], "student_work"), (feedback[0], "feedback_context")):
        entry_id = f"candidate:{candidate.candidate_id}"
        select_plan = plan_candidate_decision(
            setup.workspace,
            entry_id=entry_id,
            decision="select",
            proposed_section_ids=(section,),
        )
        selected = execute_candidate_decision(
            setup.workspace,
            select_plan,
            actor=ACTOR,
            authority_gate=StaticCurationAuthorityGate(),
            rationale_text="Teacher explicitly selected future-version Quillan evidence.",
        )
        selection = next(
            item for item in selected.records if isinstance(item, PortfolioSelection)
        )
        assert selection.candidate_id == candidate.candidate_id
        place_plan = plan_selection_placement(
            setup.workspace,
            entry_id=entry_id,
            selection_id=selection.selection_id,
            section_id=section,
        )
        placed = execute_selection_placement(
            setup.workspace,
            place_plan,
            placed_by=ACTOR,
            authority_gate=StaticCurationAuthorityGate(),
        )
        placement = next(
            item for item in placed.records if isinstance(item, PortfolioPlacement)
        )
        assert placement.selection_id == selection.selection_id
        assert placement.section_id == section

    persisted = load_current_records(setup.workspace)
    assert {item.candidate_id for item in persisted if isinstance(item, PortfolioCandidate)} == {
        item.candidate_id for item in candidates
    }
    assert len(tuple(item for item in persisted if isinstance(item, PortfolioSelection))) == 2
    assert len(tuple(item for item in persisted if isinstance(item, PortfolioPlacement))) == 2
    # The test uses only the already-supported producer-owned contract. The
    # future distribution version is intentionally *not* a runtime whitelist.
    assert future_version != audit.release_version
