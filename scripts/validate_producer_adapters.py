"""Validate issue #32 producer-adapter contracts and synthetic fixture boundaries."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from vitrine.development_adapters import (
    CONCORD_FIXTURE_SUPPORT_REQUEST,
    QUILLAN_FIXTURE_SUPPORT_REQUEST,
    SCOREFORM_FIXTURE_SUPPORT_REQUEST,
    build_development_fixture_adapter_registry,
)
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerManifestReader,
    ProducerProjectionAdapter,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionAdapterRegistry,
    ProducerProjectionBatch,
    build_adapter_registry,
)

EXPECTED_RUNTIME_HASHES = {
    "improvement-foundational-records-v1.json": "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8",
    "showcase-foundational-records-v1.json": "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360",
}


class _ConflictAdapter:
    def __init__(
        self,
        base: ProducerProjectionAdapter,
        declaration: ProducerProjectionAdapterDeclaration,
    ) -> None:
        self._base = base
        self._declaration = declaration

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return self._declaration

    @property
    def reader(self) -> ProducerManifestReader:
        return self._base.reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        return self._base.project(public_model)


def _fixture_bytes(root: Path, producer: str) -> bytes:
    return (root / "fixtures" / "producer-adapters" / producer / "manifest.json").read_bytes()


def _require_error_code(callback: Callable[[], object], expected: str) -> None:
    try:
        callback()
    except ProducerAdapterError as error:
        if error.code != expected:
            raise RuntimeError(f"expected {expected}, received {error.code}") from error
    else:
        raise RuntimeError(f"expected producer adapter failure {expected}")


def validate(root: Path) -> None:
    ordinary = build_adapter_registry()
    if ordinary.adapters:
        raise RuntimeError("ordinary registry unexpectedly contains adapters")

    fixture_registry = build_development_fixture_adapter_registry()
    if not fixture_registry.adapters or any(
        item.declaration.integration_kind != "development_fixture"
        for item in fixture_registry.adapters
    ):
        raise RuntimeError("development fixture registry is invalid")

    reversed_registry = ProducerProjectionAdapterRegistry(
        adapters=tuple(reversed(fixture_registry.adapters))
    )
    if tuple(item.declaration.identity for item in fixture_registry.adapters) != tuple(
        item.declaration.identity for item in reversed_registry.adapters
    ):
        raise RuntimeError("adapter registry ordering depends on input order")

    scoreform = fixture_registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    scoreform_batch = scoreform.project(scoreform.reader.read(_fixture_bytes(root, "scoreform")))
    if len(scoreform_batch.projected_sources) != 2:
        raise RuntimeError("ScoreForm fixture did not preserve separate attempts")
    scoreform_text = repr(scoreform_batch)
    if "2:blank" not in scoreform_text or "3:ambiguous" not in scoreform_text:
        raise RuntimeError("ScoreForm fixture did not preserve response states")
    for marker in (
        "PRIVATE_ANSWER_KEY_DO_NOT_PROJECT",
        "PRIVATE_DETECTOR_INTERNAL_DO_NOT_PROJECT",
        "PRIVATE_ROUTE_QR_DO_NOT_PROJECT",
        "PRIVATE_SCAN_REVIEW_NOTE_DO_NOT_PROJECT",
    ):
        if marker in scoreform_text:
            raise RuntimeError("ScoreForm fixture leaked prohibited data")

    quillan = fixture_registry.select_adapter(QUILLAN_FIXTURE_SUPPORT_REQUEST)
    quillan_batch = quillan.project(quillan.reader.read(_fixture_bytes(root, "quillan")))
    quillan_text = repr(quillan_batch)
    if "PRIVATE_TEACHER_NOTE_DO_NOT_PROJECT" in quillan_text:
        raise RuntimeError("Quillan fixture leaked a private teacher note")
    if "evidence_candidate" in quillan_text or "evidence_duplicate" in quillan_text:
        raise RuntimeError("Quillan fixture projected non-approved evidence")

    concord = fixture_registry.select_adapter(CONCORD_FIXTURE_SUPPORT_REQUEST)
    concord_batch = concord.project(concord.reader.read(_fixture_bytes(root, "concord")))
    artifact = next(
        item
        for item in concord_batch.projected_sources
        if item.projection_kind == "concord_fixture:artifact"
    )
    member_only = tuple(
        item
        for item in artifact.source_relationships
        if item.source_subject_id == "student_member_only"
    )
    if {item.relationship_kind for item in member_only} != {"group_member"}:
        raise RuntimeError("Concord Group Membership became authorship")
    score_sources = tuple(
        item
        for item in concord_batch.projected_sources
        if item.projection_kind == "concord_fixture:score_summary"
    )
    if not score_sources or any(
        {relationship.relationship_kind for relationship in source.source_relationships}
        != {"group_score_target"}
        for source in score_sources
    ):
        raise RuntimeError("Concord Group Score became an individual Score")

    unknown = replace(
        SCOREFORM_FIXTURE_SUPPORT_REQUEST,
        manifest_contract_version="vitrine_fixture_unknown_manifest_v1",
    )
    _require_error_code(
        lambda: fixture_registry.select_adapter(unknown), "adapter.unsupported_contract"
    )

    competitor = _ConflictAdapter(
        scoreform,
        replace(scoreform.declaration, adapter_id="vitrine_scoreform_fixture_competitor"),
    )
    conflict_registry = ProducerProjectionAdapterRegistry(adapters=(scoreform, competitor))
    _require_error_code(
        lambda: conflict_registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST),
        "adapter.conflict",
    )

    live_scoreform = ProducerAdapterSupportRequest(
        producer_module_id="scoreform",
        core_publication_schema_version="1",
        publication_kind="academic_result_set",
        manifest_contract_version="scoreform_academic_result_manifest_v1",
        producer_contract_version="scoreform_academic_work_v1",
        source_record_kind=None,
        source_record_contract_version=None,
        capabilities=("points", "question_evidence", "multiple_attempts"),
    )
    _require_error_code(
        lambda: fixture_registry.select_adapter(live_scoreform),
        "adapter.unsupported_contract",
    )

    fixture_root = root / "tests" / "fixtures" / "runtime-models"
    for filename, expected in EXPECTED_RUNTIME_HASHES.items():
        actual = hashlib.sha256((fixture_root / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"foundational fixture hash changed: {filename}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        validate(root)
    except (OSError, RuntimeError, ProducerAdapterError) as error:
        print(f"Producer-adapter validation failed: {error}")
        return 1
    print("PASS producer adapter validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
