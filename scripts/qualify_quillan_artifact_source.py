"""Qualify Vitrine's Quillan Artifact bridge against exact release wheels."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.standards import (
    StandardDefinition,
    StandardsLibrary,
    StandardsProfile,
    write_workspace_standards_library,
)
from quillan.academic_result_manifest_generation import (
    build_academic_result_manifest,
    load_academic_result_manifest_generation_context,
)
from quillan.assignment_workflows import (
    build_assignment_config,
    write_assignment_config,
)
from quillan.printable_response_packet import (
    generate_printable_response_packet,
    plan_printable_response_packet,
)
from quillan.work_paths import quillan_work_ref

from vitrine.models import SnapshotEntryPlan
from vitrine.quillan_adapter import build_quillan_live_adapter
from vitrine.quillan_artifact_source import (
    QuillanArtifactAuthorizationDecision,
    QuillanArtifactSourceContext,
    build_quillan_artifact_source_provider,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
)
from vitrine.released_producer_contracts import (
    CORE_0_6_3_AUDIT,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT,
    SnapshotMaterializationError,
    SnapshotSourceRequest,
)

CLASS_ID = "vitrine_quillan_artifact_qualification"
ASSIGNMENT_ID = "qualification_assignment"
STUDENT_ID = "00107"
STANDARD_ID = "synthetic:W.VITRINE.1"
PROFILE_ID = "synthetic_vitrine_profile"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _cli(arguments: list[str], *, workspace: Path, cwd: Path) -> str:
    env = os.environ.copy()
    env["PDS_WORKSPACE_ROOT"] = str(workspace)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", "from quillan.cli import main; raise SystemExit(main())", *arguments],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Quillan command failed {arguments!r}: {result.stdout}\n{result.stderr}"
        )
    return result.stdout


def _build_native_state(workspace: Path, work: Path) -> object:
    write_class_roster(
        workspace,
        create_roster(
            CLASS_ID,
            ({"student_id": STUDENT_ID, "last_name": "Student", "first_name": "Synthetic", "period": "1"},),
        ),
    )
    write_workspace_standards_library(
        workspace,
        StandardsLibrary(
            standards=(
                StandardDefinition(
                    standard_id=STANDARD_ID,
                    code="W.VITRINE.1",
                    source="synthetic",
                    short_name="Synthetic Writing",
                    description="Synthetic standard for Vitrine qualification.",
                    available_modules=("quillan",),
                ),
            ),
            profiles=(
                StandardsProfile(
                    profile_id=PROFILE_ID,
                    standards=(STANDARD_ID,),
                    title="Synthetic Vitrine Profile",
                ),
            ),
        ),
    )
    assignment = build_assignment_config(
        assignment_id=ASSIGNMENT_ID,
        title="Vitrine Quillan Artifact Qualification",
        class_id=CLASS_ID,
        writing_type="argument",
        student_prompt="Write one harmless synthetic response.",
        standards_profile_id=PROFILE_ID,
        focus_standard_ids=[STANDARD_ID],
        review_unit={"type": "paragraph", "singular_label": "paragraph", "plural_label": "paragraphs"},
        rating_scale={
            "scale_id": "synthetic_two_level",
            "levels": [
                {"value": 1, "label": "Developing", "description": "Developing evidence."},
                {"value": 2, "label": "Meeting", "description": "Meeting evidence."},
            ],
        },
        basic_requirements={"paragraphs_min": 1},
        minimum_requirement_policy={"allow_return_without_full_review": True},
    )
    write_assignment_config(workspace, CLASS_ID, assignment)
    packet = generate_printable_response_packet(
        plan_printable_response_packet(
            workspace,
            CLASS_ID,
            ASSIGNMENT_ID,
            pages_per_student=1,
        )
    )
    _require(packet.success and packet.installed, "Quillan qualification packet did not install")
    routed = _cli(["route-scan", str(packet.output_path)], workspace=workspace, cwd=work)
    _require("quillan=1" in routed, "Quillan qualification scan did not route exactly one page")

    identity = [CLASS_ID, ASSIGNMENT_ID, STUDENT_ID]
    commands = (
        ["requirements", "set-check", *identity, "--requirement-key", "paragraphs_min", "--met", "true"],
        ["requirements", "set-outcome", *identity, "--outcome", "met"],
        ["review-units", "set", *identity, "--count", "1"],
        ["observations", "set", *identity, "--unit-id", "paragraph_1", "--standard-id", STANDARD_ID, "--applicable", "true", "--evidence-present", "true", "--rating", "2", "--rationale", "Synthetic evidence is present.", "--include-in-feedback", "true"],
        ["observations", "mark-complete", *identity, "--yes"],
        ["ratings", "set", *identity, "--standard-id", STANDARD_ID, "--rating", "2", "--rationale", "Synthetic overall rating.", "--include-in-feedback", "true"],
        ["ratings", "mark-complete", *identity, "--yes"],
        ["feedback", "set-options", *identity, "--standard-id", STANDARD_ID, "--include-overall-rating", "true", "--include-overall-rationale", "true", "--observation-ids", "observation_0001"],
        ["feedback", "add-comment", *identity, "--standard-id", STANDARD_ID, "--text", "Synthetic student-facing feedback.", "--include-in-feedback", "true"],
        ["feedback", "mark-composed", *identity, "--yes"],
        ["review-workflow", "set-state", *identity, "--state", "ready_for_export", "--yes"],
        ["export-feedback", *identity, "--format", "both"],
    )
    for command in commands:
        _cli(command, workspace=workspace, cwd=work)

    context = load_academic_result_manifest_generation_context(
        workspace,
        quillan_work_ref(CLASS_ID, ASSIGNMENT_ID),
    )
    return build_academic_result_manifest(
        context,
        record_set_revision=1,
        generated_at=datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc),
    )


@dataclass(frozen=True)
class _Resolver:
    context: QuillanArtifactSourceContext

    def resolve(self, request: SnapshotSourceRequest) -> QuillanArtifactSourceContext:
        del request
        return self.context


class _AllowedGate:
    def authorize(self, request: object) -> QuillanArtifactAuthorizationDecision:
        del request
        return QuillanArtifactAuthorizationDecision(
            outcome="allowed",
            authority_reference="exact_wheel_qualification",
        )


class _DeniedGate:
    def authorize(self, request: object) -> QuillanArtifactAuthorizationDecision:
        del request
        return QuillanArtifactAuthorizationDecision(outcome="denied")


def _entry(source: object, *, index: int) -> SnapshotEntryPlan:
    artifact = getattr(source, "source_artifact")
    representation = getattr(source, "projection_kind")
    target = {
        QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND: "student-work/selected-evidence",
        QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND: "feedback/student-feedback.pdf",
        QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND: "feedback/student-feedback.md",
    }[representation]
    return SnapshotEntryPlan(
        entry_plan_id=f"entry_{index}",
        plan_position=index,
        section_id="qualification",
        ordinal=index,
        semantic_role="student_work" if representation == QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND else "feedback",
        materialization_kind="copied_source",
        content_class="student_work" if representation == QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND else "feedback",
        selection_id=f"selection_{index}",
        candidate_id=f"candidate_{index}",
        candidate_evaluation_id=f"evaluation_{index}",
        source_publication_id="publication_quillan_qualification",
        producer_module_id="quillan",
        projection_kind=representation,
        projection_contract_version=getattr(getattr(source, "producer_source"), "projection_contract_version"),
        source_artifact=artifact,
        producer_source_digest_claim=None,
        target_relative_path=target,
        media_type=artifact.media_type,
    )


def _request(entry: SnapshotEntryPlan) -> SnapshotSourceRequest:
    return SnapshotSourceRequest(
        snapshot_build_plan_id="snapshot_plan_qualification",
        snapshot_build_attempt_id="snapshot_attempt_qualification",
        entry_plan=entry,
    )


def qualify() -> None:
    quillan_audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["quillan"]
    _require(metadata.version(CORE_0_6_3_AUDIT.distribution_name) == "0.6.3", "Core exact-wheel version changed")
    _require(metadata.version(quillan_audit.distribution_name) == "0.10.0", "Quillan exact-wheel version changed")

    with tempfile.TemporaryDirectory(prefix="vitrine-quillan-artifact-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        work = root / "work"
        workspace.mkdir()
        work.mkdir()
        manifest = _build_native_state(workspace, work)
        batch = build_quillan_live_adapter().project(manifest)
        sources = tuple(
            source
            for source in batch.projected_sources
            if source.projection_kind in {
                QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
                QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
                QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
            }
        )
        _require(len(sources) == 3, "Quillan exact-wheel Artifact projection cardinality changed")

        for index, source in enumerate(sources, start=1):
            representation = source.projection_kind
            kind = {
                QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND: "student_work",
                QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND: "feedback_pdf",
                QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND: "feedback_markdown",
            }[representation]
            evidence_id = None
            if kind == "student_work":
                evidence_id = next(
                    field.value
                    for field in source.display_snapshot.fields
                    if field.key == "evidence_id"
                )
            context = QuillanArtifactSourceContext(
                workspace_root=workspace.absolute(),
                manifest=manifest,
                source_publication_id="publication_quillan_qualification",
                student_id=STUDENT_ID,
                artifact_request_kind=kind,
                evidence_id=evidence_id,
            )
            provider = build_quillan_artifact_source_provider(
                artifact_request_kind=kind,
                context_resolver=_Resolver(context),
                authorization_gate=_AllowedGate(),
            )
            result = provider.resolve(_request(_entry(source, index=index)))
            _require(result.byte_size == len(result.content), f"{kind} byte size changed")
            _require(
                result.source_digest is not None
                and result.source_digest.value == hashlib.sha256(result.content).hexdigest(),
                f"{kind} digest changed",
            )
            expected_contract = (
                SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT
                if kind == "student_work"
                else SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
            )
            _require(result.acquisition_contract_version == expected_contract, f"{kind} acquisition contract changed")

        selected = next(source for source in sources if source.projection_kind == QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND)
        denied_context = QuillanArtifactSourceContext(
            workspace_root=(workspace / "definitely-missing").absolute(),
            manifest=manifest,
            source_publication_id="publication_quillan_qualification",
            student_id=STUDENT_ID,
            artifact_request_kind="student_work",
            evidence_id=next(field.value for field in selected.display_snapshot.fields if field.key == "evidence_id"),
        )
        denied_provider = build_quillan_artifact_source_provider(
            artifact_request_kind="student_work",
            context_resolver=_Resolver(denied_context),
            authorization_gate=_DeniedGate(),
        )
        try:
            denied_provider.resolve(_request(_entry(selected, index=9)))
        except SnapshotMaterializationError as error:
            _require(error.stage == "quillan_artifact_authorization_denied", "denied Quillan Artifact crossed native-I/O boundary")
        else:
            raise RuntimeError("denied Quillan Artifact unexpectedly resolved")

    print(
        "PASS exact-wheel Quillan Artifact source qualification",
        metadata.version("pds-core"),
        metadata.version("quillan"),
    )


if __name__ == "__main__":
    qualify()
