"""Qualify Vitrine #58 installed readers against exact audited release wheels."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

_SIBLING_ROOTS = ("scoreform", "quillan", "concord")


@dataclass(frozen=True, slots=True)
class WheelSpec:
    distribution_name: str
    release_version: str
    wheel_filename: str
    wheel_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _audit_specs() -> tuple[WheelSpec, ...]:
    from vitrine.released_producer_contracts import (
        CORE_0_6_3_AUDIT,
        RELEASED_PRODUCER_CONTRACTS,
    )

    return (
        WheelSpec(
            distribution_name=CORE_0_6_3_AUDIT.distribution_name,
            release_version=CORE_0_6_3_AUDIT.release_version,
            wheel_filename=CORE_0_6_3_AUDIT.wheel_filename,
            wheel_sha256=CORE_0_6_3_AUDIT.wheel_sha256,
        ),
        *(
            WheelSpec(
                distribution_name=audit.distribution_name,
                release_version=audit.release_version,
                wheel_filename=audit.wheel_filename,
                wheel_sha256=audit.wheel_sha256,
            )
            for audit in RELEASED_PRODUCER_CONTRACTS
        ),
    )


def _resolve_exact_wheels(wheel_dir: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for spec in _audit_specs():
        path = wheel_dir / spec.wheel_filename
        if not path.is_file():
            raise RuntimeError(f"missing audited wheel: {spec.wheel_filename}")
        actual = _sha256(path)
        if actual != spec.wheel_sha256:
            raise RuntimeError(
                f"wheel digest mismatch for {spec.wheel_filename}: {actual}"
            )
        paths.append(path)
    return tuple(paths)


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _scoreform_bytes() -> bytes:
    return _canonical_json_bytes(
        {
            "assignment": {
                "assignment_id": "qualification_quiz",
                "choices": ["A", "B", "C", "D"],
                "layout_id": "standard_15q_abcd_v1",
                "question_count": 3,
                "questions": [
                    {
                        "points_possible": 1,
                        "question_number": 1,
                        "standard_ids": ["standard_reading_1"],
                    },
                    {
                        "points_possible": 1,
                        "question_number": 2,
                        "standard_ids": [],
                    },
                    {
                        "points_possible": 1,
                        "question_number": 3,
                        "standard_ids": ["standard_language_2", "standard_reading_3"],
                    },
                ],
                "standards_profile_id": "qualification_profile",
                "title": "Installed ScoreForm Projection Qualification",
                "total_points": 3,
            },
            "contract_version": "scoreform_academic_result_manifest_v1",
            "generated_at": "2026-08-31T20:00:00.000000Z",
            "producer_module_id": "scoreform",
            "record_set": {
                "record_set_id": "qualification_results",
                "revision": 1,
            },
            "record_type": "scoreform_academic_result_manifest",
            "source_snapshot": {
                "assignment": {
                    "contract_version": None,
                    "relative_path": "assignment.json",
                    "sha256": "a" * 64,
                },
                "results_history": {
                    "relative_path": "results.csv",
                    "result_schema_version": "2",
                    "sha256": "b" * 64,
                },
            },
            "students": [
                {
                    "attempts": [
                        {
                            "attempt_number": 1,
                            "points_earned": 2,
                            "points_possible": 3,
                            "provenance": {
                                "artifact_id": "artifact_alpha",
                                "generation_id": "generation_alpha",
                                "issuance_id": "issuance_alpha",
                                "logical_pages": [1, 2],
                                "page_ids": ["page_alpha_1", "page_alpha_2"],
                                "retained_source_path": "scans/source/2026-08-20/qualification-private.pdf",
                                "route_ids": ["route_alpha_1", "route_alpha_2"],
                                "source_page_numbers": [4, 5],
                                "source_scan_id": "scan_alpha",
                                "source_sha256": "c" * 64,
                            },
                            "recorded_at": "2026-08-20T14:30:00.000000Z",
                            "responses": [
                                {
                                    "correct": True,
                                    "question_number": 1,
                                    "response_state": "selected",
                                    "selected_answer": "A",
                                },
                                {
                                    "correct": False,
                                    "question_number": 2,
                                    "response_state": "blank",
                                    "selected_answer": None,
                                },
                                {
                                    "correct": True,
                                    "question_number": 3,
                                    "response_state": "selected",
                                    "selected_answer": "C",
                                },
                            ],
                            "result_origin": "pds2_scan",
                        },
                        {
                            "attempt_number": 2,
                            "points_earned": 1,
                            "points_possible": 3,
                            "provenance": {
                                "review_reference": {"failure_id": "failure_alpha"}
                            },
                            "recorded_at": "2026-08-21T14:30:00.000000Z",
                            "responses": [
                                {
                                    "correct": True,
                                    "question_number": 1,
                                    "response_state": "selected",
                                    "selected_answer": "B",
                                },
                                {
                                    "correct": False,
                                    "question_number": 2,
                                    "response_state": "ambiguous",
                                    "selected_answer": None,
                                },
                                {
                                    "correct": False,
                                    "question_number": 3,
                                    "response_state": "selected",
                                    "selected_answer": "D",
                                },
                            ],
                            "result_origin": "scan_review_manual",
                        },
                    ],
                    "student_id": "student_alpha",
                },
                {
                    "attempts": [
                        {
                            "attempt_number": 1,
                            "points_earned": 3,
                            "points_possible": 3,
                            "provenance": {},
                            "recorded_at": "2026-08-22T14:30:00.000000Z",
                            "responses": [
                                {
                                    "correct": True,
                                    "question_number": 1,
                                    "response_state": "selected",
                                    "selected_answer": "A",
                                },
                                {
                                    "correct": True,
                                    "question_number": 2,
                                    "response_state": "selected",
                                    "selected_answer": "B",
                                },
                                {
                                    "correct": True,
                                    "question_number": 3,
                                    "response_state": "selected",
                                    "selected_answer": "C",
                                },
                            ],
                            "result_origin": "plain_paper_manual",
                        }
                    ],
                    "student_id": "student_beta",
                },
            ],
            "work": {
                "class_id": "class_qualification",
                "module_id": "scoreform",
                "work_id": "qualification_quiz",
            },
        }
    )

def _quillan_bytes() -> bytes:
    return _canonical_json_bytes(
        {
            "assignment": {
                "assignment_id": "qualification_essay",
                "basic_requirements": {
                    "paragraphs_max": None,
                    "paragraphs_min": 4,
                    "required_elements": ["claim", "textual evidence"],
                    "word_count_max": 1500,
                    "word_count_min": 800,
                },
                "focus_standard_ids": ["njsls-ela:RL.CR.9-10.1"],
                "minimum_requirement_policy": {
                    "allow_return_without_full_review": True,
                },
                "rating_scale": {
                    "levels": [
                        {
                            "description": "Limited evidence.",
                            "label": "Beginning",
                            "value": 0,
                        },
                        {
                            "description": "Consistent evidence.",
                            "label": "Secure",
                            "value": 4,
                        },
                    ],
                    "scale_id": "quillan_qualification_v1",
                },
                "review_unit": {
                    "plural_label": "Paragraphs",
                    "singular_label": "Paragraph",
                    "type": "paragraph",
                },
                "standards_profile_id": "qualification_profile",
                "student_prompt": "Explain the evidence.",
                "title": "Installed Reader Qualification",
                "writing_type": "literary_analysis",
            },
            "contract_version": "quillan_academic_result_manifest_v1",
            "generated_at": "2026-08-31T20:00:00Z",
            "producer_module_id": "quillan",
            "record_set": {
                "record_set_id": "qualification_results",
                "revision": 1,
            },
            "record_type": "quillan_academic_result_manifest",
            "source_snapshot": {
                "contract_version": "2",
                "relative_path": "assignment.json",
                "sha256": "0" * 64,
            },
            "students": [
                {
                    "review": {
                        "assignment_id": "qualification_essay",
                        "class_id": "class_qualification",
                        "feedback": {
                            "include_overall_standard_ratings": False,
                            "include_review_unit_observations": False,
                            "standard_feedback": [],
                        },
                        "minimum_requirement_outcome": {
                            "returned_without_full_review": True,
                            "status": "returned_without_full_review",
                            "teacher_note": {
                                "disposition": "withheld",
                                "text": None,
                            },
                            "updated_at": "2026-08-31T19:59:00Z",
                        },
                        "overall_standard_ratings": [],
                        "review_state": "returned_without_full_review",
                        "review_units": [],
                        "student_id": "student_qualification",
                    },
                    "source_snapshot": {
                        "review": {
                            "contract_version": "2",
                            "relative_path": (
                                "submissions/student_qualification/review.json"
                            ),
                            "sha256": "2" * 64,
                        },
                        "submission": {
                            "contract_version": "1",
                            "relative_path": (
                                "submissions/student_qualification/submission.json"
                            ),
                            "sha256": "1" * 64,
                        },
                    },
                    "student_id": "student_qualification",
                    "submission": {
                        "assignment_id": "qualification_essay",
                        "class_id": "class_qualification",
                        "digital_provenance": None,
                        "entry_method": "plain_paper_manual",
                        "expected_pages": None,
                        "student_id": "student_qualification",
                        "submission_state": "unreviewed",
                    },
                }
            ],
            "work": {
                "class_id": "class_qualification",
                "module_id": "quillan",
                "work_id": "qualification_essay",
            },
        }
    )


def _concord_bytes() -> bytes:
    manifest_module = importlib.import_module("concord.academic_result_manifest")
    routing = importlib.import_module("pds_core.routing_models")

    def cls(name: str) -> Any:
        return getattr(manifest_module, name)

    ModuleWorkRef = getattr(routing, "ModuleWorkRef")
    ModuleRecordRef = getattr(routing, "ModuleRecordRef")

    actor = cls("PublicActor")(
        actor_kind="authorized_adult",
        actor_id="teacher-qualification",
        owning_system="concord",
    )
    student = cls("SubjectReferenceProjection")(
        subject_kind="core_student",
        subject_id="student-qualification",
        owning_system="core",
        contract_version=None,
    )
    criterion_set = cls("CriterionSetProjection")(
        criterion_set_id="set-local",
        lineage_id="lineage-local",
        revision=1,
        criterion_set_kind="local",
        scope="activity_specific",
        criterion_ids=("criterion-local",),
        status="active",
        supersedes_criterion_set_id=None,
        standards_profile_id=None,
    )
    criterion = cls("CriterionProjection")(
        criterion_id="criterion-local",
        criterion_set_id="set-local",
        key="collaboration",
        label="Collaboration",
        definition="Demonstrates collaborative practice.",
        criterion_kind="local",
        supported_target_kinds=("core_student",),
        status="active",
        standard_id=None,
        alignment_standard_ids=(),
        default_scoring_scale_id="scale-local",
    )
    scale = cls("ScoringScaleProjection")(
        scoring_scale_id="scale-local",
        lineage_id="scale-lineage-local",
        name="Qualification scale",
        revision=1,
        scale_type="teacher_defined",
        levels=(
            cls("ScaleLevelProjection")(
                1,
                "Observed",
                "Observed evidence.",
                None,
                None,
            ),
        ),
        status="active",
        supersedes_scoring_scale_id=None,
    )
    score = cls("ScoreProjection")(
        score_record_id="score-local",
        activity_id="activity-qualification",
        session_id=None,
        target_reference=cls("TargetReferenceProjection")(
            target_kind="core_student",
            target_id="student-qualification",
            owning_system="core",
            contract_version=None,
        ),
        criterion_id="criterion-local",
        score_kind="local",
        standard_id=None,
        scoring_scale_id="scale-local",
        disposition="scored",
        value=1,
        basis="professional_judgment",
        scorer=actor,
        scored_at=datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc),
        moderation_complete=True,
        status_reason=None,
        supersedes_score_record_id=None,
        current_state="current",
    )
    manifest = cls("AcademicResultManifest")(
        record_type=getattr(
            manifest_module,
            "ACADEMIC_RESULT_MANIFEST_RECORD_TYPE",
        ),
        contract_version=getattr(
            manifest_module,
            "ACADEMIC_RESULT_MANIFEST_CONTRACT_VERSION",
        ),
        producer_module_id="concord",
        generated_at=datetime(2026, 8, 31, 20, 1, tzinfo=timezone.utc),
        record_set=cls("ManifestRecordSet")("academic_results", 1),
        work=ModuleWorkRef(
            "concord",
            "class-qualification",
            "activity-qualification",
        ),
        source_activity=ModuleRecordRef(
            module_id="concord",
            record_kind="activity",
            record_id="activity-qualification",
            contract_version="concord_activity_v1",
        ),
        projection=cls("ManifestProjection")(
            source_snapshot_revision=1,
            projection_digest_algorithm="sha256",
            projection_digest="0" * 64,
            generated_by=actor,
            revision_reason="initial",
        ),
        activity_context=cls("ActivityContextProjection")(
            activity_id="activity-qualification",
            class_id="class-qualification",
            title="Installed Reader Qualification",
            scoring_orientation="local_criteria_only",
            standards_profile_id=None,
            focus_standard_ids=(),
            criterion_set_ids=("set-local",),
        ),
        criterion_sets=(criterion_set,),
        criteria=(criterion,),
        scoring_scales=(scale,),
        scores=(score,),
        score_evidence_links=(),
        moderation_records=(),
        standards_result_projection=(),
        privacy=cls("PrivacyProjection")(
            classification="teacher_and_subjects",
            audience_references=(student,),
            policy_reference=None,
            inherited_from=None,
        ),
    )
    sealed = getattr(manifest_module, "with_semantic_projection_digest")(manifest)
    result = getattr(manifest_module, "academic_result_manifest_to_bytes")(sealed)
    if type(result) is not bytes:
        raise RuntimeError("Concord public manifest writer did not return bytes.")
    return result


def _loaded_siblings() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in sys.modules
            if any(
                name == root or name.startswith(f"{root}.")
                for root in _SIBLING_ROOTS
            )
        )
    )


def _inside_qualification(fixture_dir: Path) -> None:
    from vitrine.producer_reader_services import (
        build_audited_installed_producer_readers,
    )
    from vitrine.released_producer_contracts import (
        CORE_0_6_3_AUDIT,
        RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    )

    expected_versions = {
        CORE_0_6_3_AUDIT.distribution_name: CORE_0_6_3_AUDIT.release_version,
        **{
            audit.distribution_name: audit.release_version
            for audit in RELEASED_PRODUCER_CONTRACT_BY_MODULE.values()
        },
    }
    for distribution, expected in expected_versions.items():
        actual = metadata.version(distribution)
        if actual != expected:
            raise RuntimeError(
                f"qualification environment has {distribution} {actual}; "
                f"expected audited release {expected}"
            )

    before = _loaded_siblings()
    if before:
        raise RuntimeError(
            "producer packages were imported before reader binding construction: "
            + ", ".join(before)
        )

    readers = build_audited_installed_producer_readers()
    if _loaded_siblings():
        raise RuntimeError(
            "reader binding construction eagerly imported a producer package"
        )

    payloads = {
        "scoreform": (fixture_dir / "scoreform.json").read_bytes(),
        "quillan": (fixture_dir / "quillan.json").read_bytes(),
        "concord": (fixture_dir / "concord.json").read_bytes(),
    }

    by_module = {reader.audit.producer_module_id: reader for reader in readers}
    if tuple(sorted(by_module)) != ("concord", "quillan", "scoreform"):
        raise RuntimeError("audited installed reader set changed")

    models: dict[str, object] = {}
    for module_id in ("scoreform", "quillan", "concord"):
        reader = by_module[module_id]
        audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[module_id]
        model = reader.read(payloads[module_id])
        models[module_id] = model
        if getattr(model, "producer_module_id", None) != module_id:
            raise RuntimeError(f"{module_id} reader returned the wrong producer model")
        if (
            getattr(model, "contract_version", None)
            != audit.support_key.manifest_contract_version
        ):
            raise RuntimeError(
                f"{module_id} reader returned the wrong manifest contract"
            )
        if reader.descriptor.integration_kind != "live":
            raise RuntimeError(f"{module_id} reader is not a live binding")
        print(
            "PASS",
            module_id,
            audit.distribution_name,
            metadata.version(audit.distribution_name),
            reader.descriptor.public_reader_id,
            hashlib.sha256(payloads[module_id]).hexdigest(),
        )

    from vitrine.producer_adapters import (
        ProducerAdapterSupportRequest,
        build_adapter_registry,
    )
    from vitrine.released_producer_contracts import (
        CONCORD_LIVE_SUPPORT_KEY,
        QUILLAN_LIVE_SUPPORT_KEY,
        SCOREFORM_LIVE_SUPPORT_KEY,
    )

    scoreform_profile_module = importlib.import_module("scoreform.pds_publication")
    get_scoreform_profile = getattr(
        scoreform_profile_module, "get_publication_producer_profile", None
    )
    if not callable(get_scoreform_profile):
        raise RuntimeError("exact ScoreForm wheel is missing its public producer Profile")
    scoreform_profile = get_scoreform_profile()
    if scoreform_profile.module_id != "scoreform":
        raise RuntimeError("exact ScoreForm wheel returned the wrong producer Profile")
    if scoreform_profile.supported_core_publication_schema_versions != frozenset({"1"}):
        raise RuntimeError("ScoreForm Profile Core publication support changed")
    if scoreform_profile.supported_academic_work_contract_versions != frozenset(
        {"scoreform_academic_work_v1"}
    ):
        raise RuntimeError("ScoreForm Profile academic-work support changed")
    if len(scoreform_profile.publication_contracts) != 1:
        raise RuntimeError("ScoreForm Profile publication contract count changed")
    profile_contract = scoreform_profile.publication_contracts[0]
    if profile_contract.publication_kind != "academic_result_set":
        raise RuntimeError("ScoreForm Profile publication kind changed")
    if profile_contract.manifest_contract_versions != frozenset(
        {"scoreform_academic_result_manifest_v1"}
    ):
        raise RuntimeError("ScoreForm Profile manifest contract changed")
    if profile_contract.supported_capabilities != frozenset(
        {"multiple_attempts", "points", "question_evidence"}
    ):
        raise RuntimeError("ScoreForm Profile capabilities changed")
    if profile_contract.source_record_contracts or not profile_contract.allows_missing_source_record:
        raise RuntimeError("ScoreForm Profile source-record semantics changed")

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
    adapter = build_adapter_registry().select_adapter(request)
    batch = adapter.project(models["scoreform"])
    if len(batch.projected_sources) != 3:
        raise RuntimeError("ScoreForm live adapter did not preserve all three attempts")

    projected = {
        (
            source.source_relationships[0].source_subject_id,
            source.producer_source.native_revision,
        ): source
        for source in batch.projected_sources
    }
    expected_attempts = {
        ("student_alpha", 1),
        ("student_alpha", 2),
        ("student_beta", 1),
    }
    if set(projected) != expected_attempts:
        raise RuntimeError("ScoreForm live adapter changed attempt cardinality or subjects")
    alpha_one = projected[("student_alpha", 1)]
    alpha_two = projected[("student_alpha", 2)]
    alpha_one_fields = {
        field.key: field.value for field in alpha_one.display_snapshot.fields
    }
    alpha_two_fields = {
        field.key: field.value for field in alpha_two.display_snapshot.fields
    }
    if alpha_one_fields["points_earned"] != 2 or alpha_two_fields["points_earned"] != 1:
        raise RuntimeError("ScoreForm live adapter selected/ranked attempts instead of preserving them")
    if alpha_one_fields["response_states"] != (
        "1:selected",
        "2:blank",
        "3:selected",
    ):
        raise RuntimeError("ScoreForm live adapter changed response-state evidence")
    if alpha_two_fields["response_states"] != (
        "1:selected",
        "2:ambiguous",
        "3:selected",
    ):
        raise RuntimeError("ScoreForm live adapter collapsed ambiguous response state")
    if alpha_one_fields["question_standard_alignments"] != (
        "1:standard_reading_1",
        "3:standard_language_2",
        "3:standard_reading_3",
    ):
        raise RuntimeError("ScoreForm live adapter changed standard alignments")
    if alpha_one.source_artifact.source_locator is not None:
        raise RuntimeError("ScoreForm summary unexpectedly exposes a source locator")
    if alpha_one.source_artifact.source_digest is not None:
        raise RuntimeError("ScoreForm summary borrowed a retained scan digest")
    if "retained_source_path" in alpha_one_fields:
        raise RuntimeError("ScoreForm live adapter exposed retained_source_path")
    if "qualification-private.pdf" in repr(batch):
        raise RuntimeError("ScoreForm live adapter leaked retained scan path")
    if any(
        field.key == "selected_answer"
        for source in batch.projected_sources
        for field in source.display_snapshot.fields
    ):
        raise RuntimeError("ScoreForm live adapter exposed selected-answer content")
    lowered = repr(batch).lower()
    for prohibited in ("grade", "proficiency", "mastery", "portfolio-worthy", "selected attempt"):
        if prohibited in lowered:
            raise RuntimeError(f"ScoreForm live adapter inferred prohibited semantics: {prohibited}")

    print(
        "PASS exact-wheel ScoreForm live projection qualification",
        metadata.version("pds-core"),
        metadata.version("scoreform"),
        len(batch.projected_sources),
    )

    quillan_profile_module = importlib.import_module("quillan.pds_publication")
    get_quillan_profile = getattr(
        quillan_profile_module, "get_publication_producer_profile", None
    )
    if not callable(get_quillan_profile):
        raise RuntimeError("exact Quillan wheel is missing its public producer Profile")
    quillan_profile = get_quillan_profile()
    if quillan_profile.module_id != "quillan":
        raise RuntimeError("exact Quillan wheel returned the wrong producer Profile")
    if quillan_profile.supported_core_publication_schema_versions != frozenset({"1"}):
        raise RuntimeError("Quillan Profile Core publication support changed")
    if quillan_profile.supported_academic_work_contract_versions != frozenset(
        {"quillan_academic_work_v1"}
    ):
        raise RuntimeError("Quillan Profile academic-work support changed")
    if len(quillan_profile.publication_contracts) != 1:
        raise RuntimeError("Quillan Profile publication contract count changed")
    quillan_contract = quillan_profile.publication_contracts[0]
    if quillan_contract.publication_kind != "academic_result_set":
        raise RuntimeError("Quillan Profile publication kind changed")
    if quillan_contract.manifest_contract_versions != frozenset(
        {"quillan_academic_result_manifest_v1"}
    ):
        raise RuntimeError("Quillan Profile manifest contract changed")
    if quillan_contract.supported_capabilities != frozenset({"standards_ratings"}):
        raise RuntimeError("Quillan Profile capabilities changed")
    if quillan_contract.source_record_contracts or not quillan_contract.allows_missing_source_record:
        raise RuntimeError("Quillan Profile source-record semantics changed")

    quillan_key = QUILLAN_LIVE_SUPPORT_KEY
    quillan_request = ProducerAdapterSupportRequest(
        producer_module_id=quillan_key.producer_module_id,
        core_publication_schema_version=quillan_key.core_publication_schema_version,
        publication_kind=quillan_key.publication_kind,
        manifest_contract_version=quillan_key.manifest_contract_version,
        producer_contract_version=quillan_key.producer_contract_version,
        source_record_kind=quillan_key.source_record_kind,
        source_record_contract_version=quillan_key.source_record_contract_version,
        capabilities=quillan_key.required_capabilities,
    )
    quillan_adapter = build_adapter_registry().select_adapter(quillan_request)
    quillan_batch = quillan_adapter.project(models["quillan"])
    quillan_representations = {source.projection_kind for source in quillan_batch.projected_sources}
    expected_quillan = {
        "quillan:review_summary",
        "quillan:feedback_pdf",
        "quillan:feedback_markdown",
    }
    if quillan_representations != expected_quillan or len(quillan_batch.projected_sources) != 3:
        raise RuntimeError("Quillan exact-wheel plain-paper projection cardinality changed")
    if any(source.projection_kind == "quillan:selected_student_work" for source in quillan_batch.projected_sources):
        raise RuntimeError("Quillan plain-paper exact-wheel projection fabricated digital work")
    for source in quillan_batch.projected_sources:
        if len(source.source_relationships) != 1 or source.source_relationships[0].source_subject_id != "student_qualification":
            raise RuntimeError("Quillan exact-wheel student relationship changed")
        if source.source_artifact is None or source.source_artifact.source_locator is not None:
            raise RuntimeError("Quillan exact-wheel projection fabricated source access")
    lowered = repr(quillan_batch).lower()
    if "explain the evidence" in lowered:
        raise RuntimeError("Quillan exact-wheel projection leaked private assignment prompt")
    for prohibited in ("proficiency", "mastery", "portfolio-worthy"):
        if prohibited in lowered:
            raise RuntimeError(f"Quillan live adapter inferred prohibited semantics: {prohibited}")

    print(
        "PASS exact-wheel Quillan live projection qualification",
        metadata.version("pds-core"),
        metadata.version("quillan"),
        len(quillan_batch.projected_sources),
    )

    concord_profile_module = importlib.import_module("concord.pds_publication")
    get_concord_profile = getattr(
        concord_profile_module, "get_publication_producer_profile", None
    )
    if not callable(get_concord_profile):
        raise RuntimeError("exact Concord wheel is missing its public producer Profile")
    concord_profile = get_concord_profile()
    if concord_profile.module_id != "concord":
        raise RuntimeError("exact Concord wheel returned the wrong producer Profile")
    if concord_profile.supported_core_publication_schema_versions != frozenset({"1"}):
        raise RuntimeError("Concord Profile Core publication support changed")
    if concord_profile.supported_academic_work_contract_versions != frozenset(
        {"concord_academic_work_v1"}
    ):
        raise RuntimeError("Concord Profile academic-work support changed")
    if len(concord_profile.publication_contracts) != 1:
        raise RuntimeError("Concord Profile publication contract count changed")
    concord_contract = concord_profile.publication_contracts[0]
    if concord_contract.publication_kind != "academic_result_set":
        raise RuntimeError("Concord Profile publication kind changed")
    if concord_contract.manifest_contract_versions != frozenset(
        {"concord_academic_result_manifest_v1"}
    ):
        raise RuntimeError("Concord Profile manifest contract changed")
    if concord_contract.supported_capabilities != frozenset(
        {"criterion_scores", "moderated_scores", "standards_ratings"}
    ):
        raise RuntimeError("Concord Profile capabilities changed")
    if len(concord_contract.source_record_contracts) != 1:
        raise RuntimeError("Concord Profile source-record support changed")
    concord_source = concord_contract.source_record_contracts[0]
    if (
        concord_source.record_kind != "activity"
        or concord_source.contract_versions != frozenset({"concord_activity_v1"})
        or concord_source.allows_unversioned
        or concord_contract.allows_missing_source_record
    ):
        raise RuntimeError("Concord Profile Activity source-record semantics changed")

    concord_key = CONCORD_LIVE_SUPPORT_KEY
    concord_request = ProducerAdapterSupportRequest(
        producer_module_id=concord_key.producer_module_id,
        core_publication_schema_version=concord_key.core_publication_schema_version,
        publication_kind=concord_key.publication_kind,
        manifest_contract_version=concord_key.manifest_contract_version,
        producer_contract_version=concord_key.producer_contract_version,
        source_record_kind=concord_key.source_record_kind,
        source_record_contract_version=concord_key.source_record_contract_version,
        capabilities=(
            "criterion_scores",
            "moderated_scores",
            "standards_ratings",
        ),
    )
    concord_adapter = build_adapter_registry().select_adapter(concord_request)
    concord_batch = concord_adapter.project(models["concord"])
    if len(concord_batch.projected_sources) != 1:
        raise RuntimeError("Concord live adapter changed exact-wheel Score cardinality")
    concord_score = concord_batch.projected_sources[0]
    if concord_score.projection_kind != "concord:score_summary":
        raise RuntimeError("Concord exact-wheel projection kind changed")
    if concord_score.producer_source.source_record_id != "score-local":
        raise RuntimeError("Concord exact-wheel Score identity changed")
    if (
        len(concord_score.source_relationships) != 1
        or concord_score.source_relationships[0].relationship_kind
        != "individual_score_target"
        or concord_score.source_relationships[0].source_subject_id
        != "student-qualification"
    ):
        raise RuntimeError("Concord exact-wheel student Score target changed")
    concord_fields = {
        field.key: field.value for field in concord_score.display_snapshot.fields
    }
    expected_fields = {
        "criterion_kind": "local",
        "scoring_scale_type": "teacher_defined",
        "scale_level_values": (1,),
        "scale_level_value_types": ("int",),
        "score_disposition": "scored",
        "score_native_value": 1,
        "score_native_value_type": "int",
        "score_current_state": "current",
    }
    for field, expected_value in expected_fields.items():
        if concord_fields.get(field) != expected_value:
            raise RuntimeError(
                f"Concord exact-wheel projection changed {field}"
            )
    if (
        concord_score.source_artifact.source_locator is not None
        or concord_score.source_artifact.source_digest is not None
        or concord_score.source_artifact.byte_size is not None
    ):
        raise RuntimeError("Concord Score summary fabricated source access metadata")
    concord_lowered = repr(concord_batch).lower()
    for prohibited in (
        "grade",
        "proficiency",
        "mastery",
        "portfolio-worthy",
        "selected score",
    ):
        if prohibited in concord_lowered:
            raise RuntimeError(
                f"Concord live adapter inferred prohibited semantics: {prohibited}"
            )

    print(
        "PASS exact-wheel Concord live projection qualification",
        metadata.version("pds-core"),
        metadata.version("pds-concord"),
        len(concord_batch.projected_sources),
    )

    from vitrine.compatibility_diagnostics import (
        diagnose_installed_producer_readiness,
    )

    readiness = diagnose_installed_producer_readiness()
    readiness_by_producer = {
        report.producer_module_id: report for report in readiness
    }
    if tuple(sorted(readiness_by_producer)) != (
        "concord",
        "quillan",
        "scoreform",
    ):
        raise RuntimeError("issue #62 installed-readiness producer set changed")
    for producer in ("scoreform", "quillan", "concord"):
        report = readiness_by_producer[producer]
        if not report.ready:
            raise RuntimeError(
                f"issue #62 exact-wheel readiness is not ready for {producer}"
            )
        checks = {item.stage: item for item in report.checks}
        expected_artifact_outcome = (
            "not_applicable" if producer == "scoreform" else "ready"
        )
        if checks["artifact_api"].outcome != expected_artifact_outcome:
            raise RuntimeError(
                f"issue #62 Artifact readiness changed for {producer}"
            )
        audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[producer]
        distribution_fields = dict(checks["reader_distribution"].safe_fields)
        if (
            distribution_fields.get("installed_distribution_version")
            != audit.release_version
        ):
            raise RuntimeError(
                f"issue #62 qualification provenance changed for {producer}"
            )

    print("PASS exact-wheel issue #62 installed-readiness qualification")

    print("PASS exact-wheel installed producer reader qualification")


def _build_concord_fixture(path: Path) -> None:
    path.write_bytes(_concord_bytes())
    print("PASS Concord canonical qualification fixture", _sha256(path))


def qualify(wheel_dir: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    wheels = _resolve_exact_wheels(wheel_dir)
    print("Verified audited wheel artifacts:")
    for path in wheels:
        print(" ", path.name)

    with tempfile.TemporaryDirectory(prefix="vitrine-producer-readers-") as temporary:
        temp = Path(temporary)
        environment = temp / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)

        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                *[str(path) for path in wheels],
            ],
            check=True,
        )

        fixture_dir = temp / "fixtures"
        fixture_dir.mkdir()
        (fixture_dir / "scoreform.json").write_bytes(_scoreform_bytes())
        (fixture_dir / "quillan.json").write_bytes(_quillan_bytes())

        child_env = os.environ.copy()
        existing = child_env.get("PYTHONPATH")
        child_env["PYTHONPATH"] = (
            str(repository_root)
            if not existing
            else os.pathsep.join((str(repository_root), existing))
        )
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"

        subprocess.run(
            [
                str(python),
                str(Path(__file__).resolve()),
                "--build-concord-fixture",
                str(fixture_dir / "concord.json"),
            ],
            cwd=repository_root,
            env=child_env,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                str(Path(__file__).resolve()),
                "--inside",
                "--fixture-dir",
                str(fixture_dir),
            ],
            cwd=repository_root,
            env=child_env,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                str(
                    repository_root
                    / "scripts"
                    / "qualify_concord_artifact_source.py"
                ),
            ],
            cwd=repository_root,
            env=child_env,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                str(
                    repository_root
                    / "scripts"
                    / "qualify_quillan_artifact_source.py"
                ),
            ],
            cwd=repository_root,
            env=child_env,
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="directory containing the exact #57 audited release wheels",
    )
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fixture-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--build-concord-fixture",
        type=Path,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    try:
        if args.build_concord_fixture is not None:
            _build_concord_fixture(args.build_concord_fixture)
            return 0
        if args.inside:
            if args.fixture_dir is None:
                raise RuntimeError("--inside requires --fixture-dir")
            _inside_qualification(args.fixture_dir)
            return 0
        qualify(args.wheel_dir.expanduser().resolve())
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Installed producer reader qualification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
