"""Validate issue #57 released producer contracts and downstream handoff."""

from __future__ import annotations

import re
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.producer_adapters import build_adapter_registry
from vitrine.released_producer_contracts import (
    CONCORD_0_3_0_AUDIT,
    CONCORD_LIVE_SUPPORT_KEY,
    CORE_0_6_3_AUDIT,
    LIVE_PRODUCER_SUPPORT_KEYS,
    QUILLAN_0_10_0_AUDIT,
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_AUDIT_CONTRACT_VERSION,
    RELEASED_PRODUCER_CONTRACTS,
    SCOREFORM_0_11_0_AUDIT,
    SCOREFORM_LIVE_SUPPORT_KEY,
)
from vitrine.released_producer_schema_audit import (
    CONCORD_SEMANTIC_CROSSWALK,
    QUILLAN_SEMANTIC_CROSSWALK,
    RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION,
    SCOREFORM_SEMANTIC_CROSSWALK,
    VITRINE_SCHEMA_SUFFICIENCY,
)

_SIBLING_IMPORT_ROOTS = ("concord", "quillan", "scoreform")
_SIBLING_DISTRIBUTIONS = frozenset({"pds-concord", "quillan", "scoreform"})
_REQUIREMENT_NAME = re.compile(r"^[A-Za-z0-9_.-]+")

_EXPECTED_RELEASES: Mapping[str, tuple[str, str, str]] = {
    "scoreform": (
        "0.11.0",
        "scoreform-0.11.0-py3-none-any.whl",
        "8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44",
    ),
    "quillan": (
        "0.10.0",
        "quillan-0.10.0-py3-none-any.whl",
        "5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9",
    ),
    "concord": (
        "0.3.0",
        "pds_concord-0.3.0-py3-none-any.whl",
        "dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12",
    ),
}

_EXPECTED_SUPPORT_FIELDS: Mapping[str, Mapping[str, object]] = {
    "scoreform": {
        "core_publication_schema_version": "1",
        "publication_kind": "academic_result_set",
        "manifest_contract_version": "scoreform_academic_result_manifest_v1",
        "producer_contract_version": "scoreform_academic_work_v1",
        "source_record_kind": None,
        "source_record_contract_version": None,
        "required_capabilities": (
            "multiple_attempts",
            "points",
            "question_evidence",
        ),
    },
    "quillan": {
        "core_publication_schema_version": "1",
        "publication_kind": "academic_result_set",
        "manifest_contract_version": "quillan_academic_result_manifest_v1",
        "producer_contract_version": "quillan_academic_work_v1",
        "source_record_kind": None,
        "source_record_contract_version": None,
        "required_capabilities": ("standards_ratings",),
    },
    "concord": {
        "core_publication_schema_version": "1",
        "publication_kind": "academic_result_set",
        "manifest_contract_version": "concord_academic_result_manifest_v1",
        "producer_contract_version": "concord_academic_work_v1",
        "source_record_kind": "activity",
        "source_record_contract_version": "concord_activity_v1",
        "required_capabilities": ("criterion_scores",),
    },
}

_REQUIRED_SEMANTICS: Mapping[str, frozenset[str]] = {
    "scoreform": frozenset(
        {
            "core_work_identity",
            "assignment_identity_title_snapshot",
            "student_identity",
            "every_exact_attempt",
            "attempt_number",
            "native_attempt_provenance",
            "attempt_origin_time",
            "points_earned_possible",
            "question_identity_order",
            "question_standard_alignment",
            "response_state",
            "selected_answer_presence",
            "native_correctness_evidence",
            "manifest_source_snapshots",
            "bounded_lineage",
            "retained_scan_path",
            "attempt_selection",
            "grade_or_proficiency",
            "answer_key_inference",
        }
    ),
    "quillan": frozenset(
        {
            "work_assignment_identity",
            "represented_student_identity",
            "assignment_submission_review_snapshots",
            "review_unit_identity_order",
            "observations",
            "applicability_evidence_states",
            "overall_native_ratings",
            "standard_specific_ratings",
            "rating_scale_identity_ordinal",
            "standard_feedback",
            "published_text_state",
            "selected_pds2_evidence",
            "review_source_revision_lineage",
            "student_feedback_relationships",
            "artifact_resolution_provenance",
            "plain_paper_manual_digital_work",
            "private_teacher_notes",
            "unselected_or_private_evidence",
            "rating_normalization",
        }
    ),
    "concord": frozenset(
        {
            "activity_work_identity",
            "activity_scoring_orientation",
            "standards_profile_focus_standards",
            "criterion_set_identity_revision",
            "criterion_identity",
            "criterion_standard_or_local_status",
            "scoring_scale_revision",
            "ordered_scale_levels",
            "type_sensitive_scale_values",
            "score_identity",
            "score_target",
            "score_disposition",
            "score_value",
            "scoring_basis_scorer_time",
            "current_superseded_score_state",
            "score_evidence_link_identity",
            "external_evidence_ownership_reference",
            "moderation_semantics",
            "standards_result_relationships",
            "group_identity",
            "artifact_and_page_identity",
            "author_relationships",
            "subject_relationships",
            "contribution_relationships",
            "recorder_relationships",
            "returned_artifact_pdf",
            "producer_private_paths",
            "grade_or_proficiency",
        }
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _validate_release_artifacts() -> None:
    _require(
        RELEASED_PRODUCER_AUDIT_CONTRACT_VERSION
        == "vitrine_released_producer_contract_audit_v1",
        "unexpected released producer audit contract version",
    )
    _require(CORE_0_6_3_AUDIT.release_version == "0.6.3", "unexpected Core release")
    _require(CORE_0_6_3_AUDIT.release_tag == "v0.6.3", "unexpected Core tag")
    _require(
        CORE_0_6_3_AUDIT.wheel_filename == "pds_core-0.6.3-py3-none-any.whl",
        "unexpected Core wheel filename",
    )
    _require(
        CORE_0_6_3_AUDIT.wheel_sha256
        == "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
        "unexpected Core wheel digest",
    )

    audits = {item.producer_module_id: item for item in RELEASED_PRODUCER_CONTRACTS}
    _require(
        tuple(audits) == ("concord", "quillan", "scoreform"),
        "released producer catalog must be deterministically ordered",
    )
    for module_id, expected in _EXPECTED_RELEASES.items():
        audit = audits[module_id]
        version, wheel, digest = expected
        _require(audit.release_version == version, f"{module_id} release changed")
        _require(audit.wheel_filename == wheel, f"{module_id} wheel changed")
        _require(audit.wheel_sha256 == digest, f"{module_id} digest changed")

    _require(
        SCOREFORM_0_11_0_AUDIT.public_reader_module
        == "scoreform.academic_result_reader",
        "ScoreForm reader module changed",
    )
    _require(
        QUILLAN_0_10_0_AUDIT.artifact_reader_module
        == "quillan.academic_result_artifacts",
        "Quillan artifact boundary changed",
    )
    _require(
        CONCORD_0_3_0_AUDIT.artifact_reader_module
        == "concord.academic_result_artifacts",
        "Concord artifact boundary changed",
    )
    _require(
        SCOREFORM_0_11_0_AUDIT.artifact_access_mode == "none",
        "ScoreForm must not gain artifact access by audit inference",
    )
    _require(
        QUILLAN_0_10_0_AUDIT.artifact_access_mode == "producer_authorized_bytes",
        "Quillan artifact access mode changed",
    )
    _require(
        CONCORD_0_3_0_AUDIT.artifact_access_mode == "producer_authorized_bytes",
        "Concord artifact access mode changed",
    )


def _validate_support_keys() -> None:
    by_module = {item.producer_module_id: item for item in LIVE_PRODUCER_SUPPORT_KEYS}
    _require(
        tuple(by_module) == ("concord", "quillan", "scoreform"),
        "live support keys must remain deterministically ordered",
    )
    _require(
        by_module["scoreform"] == SCOREFORM_LIVE_SUPPORT_KEY,
        "ScoreForm live support key alias mismatch",
    )
    _require(
        by_module["quillan"] == QUILLAN_LIVE_SUPPORT_KEY,
        "Quillan live support key alias mismatch",
    )
    _require(
        by_module["concord"] == CONCORD_LIVE_SUPPORT_KEY,
        "Concord live support key alias mismatch",
    )

    for module_id, expected in _EXPECTED_SUPPORT_FIELDS.items():
        key = by_module[module_id]
        for field_name, expected_value in expected.items():
            actual = getattr(key, field_name)
            _require(
                actual == expected_value,
                f"{module_id} support key field {field_name} changed",
            )

    _require(
        CONCORD_LIVE_SUPPORT_KEY.required_capabilities == ("criterion_scores",),
        "Concord must not require conditional capabilities",
    )


def _validate_schema_audit() -> None:
    _require(
        RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION
        == "vitrine_released_producer_schema_audit_v1",
        "unexpected producer schema audit contract version",
    )
    crosswalks = {
        "scoreform": SCOREFORM_SEMANTIC_CROSSWALK,
        "quillan": QUILLAN_SEMANTIC_CROSSWALK,
        "concord": CONCORD_SEMANTIC_CROSSWALK,
    }
    for module_id, required in _REQUIRED_SEMANTICS.items():
        actual = {item.semantic_id for item in crosswalks[module_id]}
        missing = sorted(required - actual)
        _require(not missing, f"{module_id} crosswalk missing semantics: {missing}")

    extended = {
        item.surface_id: item.extension_contract
        for item in VITRINE_SCHEMA_SUFFICIENCY
        if item.decision == "extended"
    }
    _require(
        extended
        == {
            "snapshot_copied_source_plan": (
                "copied_source_without_required_source_locator_v1"
            ),
            "snapshot_source_provider": "authorized_source_bytes_v1",
        },
        "unexpected Vitrine schema extensions",
    )


def _validate_registry_separation() -> None:
    ordinary = build_adapter_registry()
    _require(
        tuple(item.declaration.adapter_id for item in ordinary.adapters)
        == ("vitrine_scoreform_live_adapter",),
        "ordinary adapter registry must contain exactly the ScoreForm live adapter",
    )
    live = ordinary.adapters[0].declaration
    _require(live.integration_kind == "live", "ScoreForm adapter is not live")
    _require(
        live.support_key is SCOREFORM_LIVE_SUPPORT_KEY,
        "ScoreForm live adapter is not bound to the frozen support key",
    )
    _require(
        live.public_reader_id == "vitrine_installed_scoreform_academic_result_reader",
        "ScoreForm live adapter reader binding changed",
    )

    fixtures = build_development_fixture_adapter_registry()
    _require(bool(fixtures.adapters), "development fixture registry is unexpectedly empty")
    _require(
        all(
            item.declaration.integration_kind == "development_fixture"
            for item in fixtures.adapters
        ),
        "development registry contains a non-fixture adapter",
    )

    fixture_module_ids = {
        item.declaration.support_key.producer_module_id for item in fixtures.adapters
    }
    live_module_ids = {item.producer_module_id for item in LIVE_PRODUCER_SUPPORT_KEYS}
    _require(
        fixture_module_ids.isdisjoint(live_module_ids),
        "development fixture identities overlap live producer identities",
    )


def _requirement_distribution(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement.strip())
    if match is None:
        raise RuntimeError(f"could not parse dependency requirement: {requirement!r}")
    return match.group(0).lower().replace("_", "-")


def _validate_dependency_boundary(root: Path) -> None:
    parsed = tomllib.loads((root / "pyproject.toml").read_text())
    project = cast(dict[str, Any], parsed["project"])
    dependencies = cast(list[str], project["dependencies"])
    names = {_requirement_distribution(item) for item in dependencies}
    forbidden = sorted(names & _SIBLING_DISTRIBUTIONS)
    _require(
        not forbidden,
        f"Vitrine gained hard sibling producer dependencies: {forbidden}",
    )
    _require(
        "pds-core" in names,
        "Vitrine must retain its explicit Core runtime dependency",
    )

    loaded = tuple(
        name
        for name in sys.modules
        if any(
            name == root_name or name.startswith(f"{root_name}.")
            for root_name in _SIBLING_IMPORT_ROOTS
        )
    )
    _require(
        not loaded,
        f"issue #57 validation imported sibling producer packages: {loaded}",
    )


def _validate_handoff_document(root: Path) -> None:
    handoff = root / "docs" / "contracts" / "live-producer-integration-handoff-v1.md"
    text = handoff.read_text(encoding="utf-8")
    for marker in (
        "#58",
        "#59",
        "#60",
        "#61",
        "#62",
        "vitrine_released_producer_contract_audit_v1",
        "vitrine_released_producer_schema_audit_v1",
        "authorized_source_bytes_v1",
        "adapter.unsupported_contract",
        "build_adapter_registry()",
    ):
        _require(marker in text, f"downstream handoff is missing marker {marker!r}")


def validate(root: Path) -> None:
    _validate_release_artifacts()
    _validate_support_keys()
    _validate_schema_audit()
    _validate_registry_separation()
    _validate_dependency_boundary(root)
    _validate_handoff_document(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        validate(root)
    except (KeyError, OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"Released producer contract validation failed: {error}", file=sys.stderr)
        return 1
    print("PASS released producer contract validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
