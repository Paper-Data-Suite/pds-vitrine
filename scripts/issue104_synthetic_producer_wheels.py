"""Disposable synthetic future producer wheels for #104 installed acceptance.

These are NOT released producer wheels and MUST NOT be used for qualification
of the actual ScoreForm, Quillan, or Concord release artifacts. Each wheel has
real Python distribution metadata and a Core publication-producer entry point.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Final

FUTURE_VERSION: Final[str] = "99.123.456"

# name, producer-owned manifest, work contract, reader contract, Core capabilities
PRODUCERS: Final[dict[str, tuple[str, str, str, str, tuple[str, ...]]]] = {
    "scoreform": (
        "scoreform",
        "scoreform_academic_result_manifest_v1",
        "scoreform_academic_work_v1",
        "scoreform_academic_result_reader_v1",
        ("multiple_attempts", "points", "question_evidence"),
    ),
    "quillan": (
        "quillan",
        "quillan_academic_result_manifest_v1",
        "quillan_academic_work_v1",
        "quillan_academic_result_reader_v1",
        ("standards_ratings",),
    ),
    "concord": (
        "pds-concord",
        "concord_academic_result_manifest_v1",
        "concord_academic_work_v1",
        "concord_academic_result_reader_v1",
        ("criterion_scores",),
    ),
}

_PROFILE = '''from __future__ import annotations
import os
from pds_core.publication_compatibility import (
    PublicationContractSupport, PublicationProducerProfile, PublicationReaderSupport,
)

MODULE = __MODULE__
DISTRIBUTION = __DISTRIBUTION__
MANIFEST_CONTRACT = __MANIFEST_CONTRACT__
WORK_CONTRACT = __WORK_CONTRACT__
READER_CONTRACT = __READER_CONTRACT__
CAPABILITIES = __CAPABILITIES__


def get_publication_producer_profile():
    scenario = os.environ.get("PDS_ISSUE104_SCENARIO", "supported")
    target = os.environ.get("PDS_ISSUE104_TARGET", "")
    contract = READER_CONTRACT
    if MODULE == target and scenario == "unsupported":
        contract = MODULE + "_future_reader_v2"
    rows = ()
    if not (MODULE == target and scenario == "missing"):
        rows = (PublicationReaderSupport(
            manifest_contract_version=MANIFEST_CONTRACT,
            distribution_name=DISTRIBUTION,
            reader_contract_version=contract,
        ),)
    return PublicationProducerProfile(
        module_id=MODULE,
        display_name="Synthetic future " + MODULE,
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset({WORK_CONTRACT}),
        publication_contracts=(PublicationContractSupport(
            publication_kind="academic_result_set",
            manifest_contract_versions=frozenset({MANIFEST_CONTRACT}),
            supported_capabilities=frozenset(CAPABILITIES),
            reader_support=rows,
        ),),
    )
'''

_MANIFEST_TYPES = '''from types import SimpleNamespace

class AcademicResultManifest(SimpleNamespace):
    """Minimal synthetic public-model type for installed-wheel acceptance."""

class Pds2ScanProvenance:
    pass

class PlainPaperManualProvenance:
    pass

class ScanReviewManualProvenance:
    pass
'''

_READER = '''from __future__ import annotations
from .synthetic_model import build_manifest


def read_academic_result_manifest(value: bytes):
    if not isinstance(value, bytes) or value != b"issue104:synthetic_public_manifest":
        raise ValueError("Unsupported synthetic manifest bytes")
    return build_manifest()
'''

_COMMON_MODEL = '''from __future__ import annotations
from datetime import datetime, timezone
from types import SimpleNamespace as N
from .academic_result_manifest import AcademicResultManifest, PlainPaperManualProvenance

NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)

def source(path, letter):
    return N(relative_path=path, sha256=letter * 64, contract_version="synthetic_v1")
'''

_SCOREFORM_MODEL = '''
def build_manifest():
    questions = (
        N(question_number=1, points_possible=1, standard_ids=("RL.CR.9-10.1",)),
        N(question_number=2, points_possible=1, standard_ids=("W.AW.9-10.1",)),
    )
    attempts = (
        N(attempt_number=1, result_origin="plain_paper_manual", recorded_at=NOW,
          points_earned=1, points_possible=2,
          responses=(N(question_number=1, response_state="selected", selected_answer="PRIVATE_A", correct=True),
                     N(question_number=2, response_state="blank", selected_answer=None, correct=False)),
          provenance=PlainPaperManualProvenance()),
        N(attempt_number=2, result_origin="plain_paper_manual", recorded_at=NOW,
          points_earned=2, points_possible=2,
          responses=(N(question_number=1, response_state="selected", selected_answer="PRIVATE_B", correct=True),
                     N(question_number=2, response_state="selected", selected_answer="PRIVATE_C", correct=True)),
          provenance=PlainPaperManualProvenance()),
    )
    return AcademicResultManifest(
        record_type="scoreform_academic_result_manifest",
        contract_version="scoreform_academic_result_manifest_v1",
        producer_module_id="scoreform", generated_at=NOW,
        record_set=N(record_set_id="synthetic_results", revision=1),
        work=N(module_id="scoreform", class_id="class_alpha", work_id="quiz_alpha"),
        source_snapshot=N(assignment=N(sha256="a" * 64),
                          results_history=N(sha256="b" * 64, result_schema_version="2")),
        assignment=N(assignment_id="quiz_alpha", title="Synthetic quiz",
                     question_count=2, layout_id="two_choice", total_points=2,
                     standards_profile_id="njsls_ela", questions=questions),
        students=(N(student_id="student_alpha", attempts=attempts),),
    )
'''

_QUILLAN_MODEL = '''
def build_manifest():
    assignment = N(
        assignment_id="essay_alpha", title="Synthetic essay", writing_type="literary_analysis",
        standards_profile_id="njsls_ela", focus_standard_ids=("RL.CR.9-10.1",),
        review_unit=N(type="paragraph", singular_label="Paragraph", plural_label="Paragraphs"),
        rating_scale=N(scale_id="scale_alpha", levels=(
            N(value=1, label="Developing", description="Native scale level"),)),
        basic_requirements=N(paragraphs_min=None, paragraphs_max=None,
                             word_count_min=None, word_count_max=None,
                             required_elements=()),
        minimum_requirement_policy=N(allow_return_without_full_review=True),
    )
    submission = N(
        class_id="class_alpha", assignment_id="essay_alpha", student_id="student_alpha",
        submission_state="submitted", entry_method="plain_paper", expected_pages=None,
        digital_provenance=None,
    )
    review = N(
        class_id="class_alpha", assignment_id="essay_alpha", student_id="student_alpha",
        review_state="ratings_complete",
        minimum_requirement_outcome=N(status="met", returned_without_full_review=False,
                                     updated_at=NOW, teacher_note=N(disposition="absent", text=None)),
        review_units=(), overall_standard_ratings=(),
        feedback=N(include_review_unit_observations=False,
                   include_overall_standard_ratings=False, standard_feedback=()),
    )
    student = N(
        student_id="student_alpha",
        source_snapshot=N(submission=source("submission.json", "b"), review=source("review.json", "c")),
        submission=submission, review=review,
    )
    return AcademicResultManifest(
        record_type="quillan_academic_result_manifest",
        contract_version="quillan_academic_result_manifest_v1",
        producer_module_id="quillan", generated_at=NOW,
        record_set=N(record_set_id="synthetic_results", revision=1),
        work=N(module_id="quillan", class_id="class_alpha", work_id="essay_alpha"),
        source_snapshot=source("assignment.json", "a"), assignment=assignment,
        students=(student,),
    )
'''

_CONCORD_MODEL = '''
def build_manifest():
    actor = N(actor_kind="authorized_adult", actor_id="teacher_alpha", owning_system="concord")
    criterion_set = N(criterion_set_id="set_alpha", lineage_id="set_lineage", revision=1,
                      criterion_set_kind="standard_backed", scope="activity_specific",
                      criterion_ids=("criterion_alpha",), status="active",
                      supersedes_criterion_set_id=None, standards_profile_id="njsls_ela")
    criterion = N(criterion_id="criterion_alpha", criterion_set_id="set_alpha",
                  key="claim", label="Claim", definition="Argument claim",
                  criterion_kind="standard_backed", supported_target_kinds=("core_student",),
                  status="active", standard_id="W.AW.9-10.1",
                  alignment_standard_ids=("W.AW.9-10.1",),
                  default_scoring_scale_id="scale_alpha")
    scale = N(scoring_scale_id="scale_alpha", lineage_id="scale_lineage", name="Native scale",
              revision=1, scale_type="teacher_defined", levels=(
                  N(value="proficient", label="Proficient", meaning="Native label",
                    position=1, description=None),),
              status="active", supersedes_scoring_scale_id=None)
    score = N(score_record_id="score_alpha", activity_id="activity_alpha", session_id=None,
              target_reference=N(target_kind="core_student", target_id="student_alpha",
                                 owning_system="core", contract_version=None),
              criterion_id="criterion_alpha", score_kind="criterion_score",
              standard_id="W.AW.9-10.1", scoring_scale_id="scale_alpha",
              disposition="scored", value="proficient", basis="teacher_judgment",
              scorer=actor, scored_at=NOW, moderation_complete=True,
              status_reason=None, supersedes_score_record_id=None, current_state="current")
    return AcademicResultManifest(
        record_type="concord_academic_result_manifest",
        contract_version="concord_academic_result_manifest_v1",
        producer_module_id="concord", generated_at=NOW,
        record_set=N(record_set_id="synthetic_results", revision=1),
        work=N(module_id="concord", class_id="class_alpha", work_id="activity_alpha"),
        source_activity=N(module_id="concord", record_kind="activity", record_id="activity_alpha",
                          contract_version="concord_activity_v1"),
        projection=N(source_snapshot_revision=1, projection_digest_algorithm="sha256",
                     projection_digest="a" * 64, generated_by=actor,
                     revision_reason="synthetic acceptance"),
        activity_context=N(activity_id="activity_alpha", class_id="class_alpha", title="Synthetic activity",
                           scoring_orientation="criteria", standards_profile_id="njsls_ela",
                           focus_standard_ids=("W.AW.9-10.1",), criterion_set_ids=("set_alpha",)),
        criterion_sets=(criterion_set,), criteria=(criterion,), scoring_scales=(scale,),
        scores=(score,), score_evidence_links=(), moderation_records=(),
        standards_result_projection=(),
        privacy=N(classification="student_record", audience_references=(
            N(subject_kind="core_student", subject_id="student_alpha", owning_system="core",
              contract_version=None),), policy_reference=None, inherited_from=None),
    )
'''

_MODELS: Final[dict[str, str]] = {
    "scoreform": _SCOREFORM_MODEL,
    "quillan": _QUILLAN_MODEL,
    "concord": _CONCORD_MODEL,
}


def _record_bytes(contents: dict[str, bytes], record_path: str) -> bytes:
    rows = []
    for path, content in sorted(contents.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
        rows.append((path, "sha256=" + digest.decode("ascii"), str(len(content))))
    rows.append((record_path, "", ""))
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def create_synthetic_producer_wheel(directory: Path, module: str) -> Path:
    """Create a minimal installable *synthetic* future-version producer wheel."""

    if module not in PRODUCERS:
        raise ValueError("unsupported synthetic producer")
    directory.mkdir(parents=True, exist_ok=True)
    distribution, manifest, work, reader, capabilities = PRODUCERS[module]
    normalized = distribution.replace("-", "_")
    dist_info = f"{normalized}-{FUTURE_VERSION}.dist-info"
    wheel_path = directory / f"{normalized}-{FUTURE_VERSION}-py3-none-any.whl"
    provider = (
        _PROFILE.replace("__MODULE__", repr(module))
        .replace("__DISTRIBUTION__", repr(distribution))
        .replace("__MANIFEST_CONTRACT__", repr(manifest))
        .replace("__WORK_CONTRACT__", repr(work))
        .replace("__READER_CONTRACT__", repr(reader))
        .replace("__CAPABILITIES__", repr(capabilities))
    )
    files: dict[str, bytes] = {
        f"{module}/__init__.py": b"",
        f"{module}/pds_publication.py": provider.encode("utf-8"),
        f"{module}/academic_result_manifest.py": _MANIFEST_TYPES.encode("utf-8"),
        f"{module}/academic_result_reader.py": _READER.encode("utf-8"),
        f"{module}/synthetic_model.py": (_COMMON_MODEL + _MODELS[module]).encode("utf-8"),
        f"{dist_info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {distribution}\nVersion: {FUTURE_VERSION}\n"
            f"Summary: Synthetic issue 104 installed acceptance fixture, not an official release\n"
            f"Requires-Python: >=3.11\n\n"
        ).encode("utf-8"),
        f"{dist_info}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: pds-vitrine-issue104-acceptance\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n"
        ).encode("utf-8"),
        f"{dist_info}/entry_points.txt": (
            "[paper_data_suite.publication_producers]\n"
            f"{module} = {module}.pds_publication:get_publication_producer_profile\n"
        ).encode("utf-8"),
    }
    record_path = f"{dist_info}/RECORD"
    files[record_path] = _record_bytes(files, record_path)
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(files.items()):
            z.writestr(name, content)
    return wheel_path


__all__ = ["FUTURE_VERSION", "PRODUCERS", "create_synthetic_producer_wheel"]
