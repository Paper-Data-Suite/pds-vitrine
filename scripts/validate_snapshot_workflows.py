"""Validate the executable immutable Snapshot build workflow for issue #35."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.curation_fixture_support import ACTOR, fixed_clock
from scripts.snapshot_fixture_support import (
    RepresentativeSnapshotFixtureWorkspace,
    build_representative_snapshot_fixture_workspace,
)
from vitrine.models import (
    CandidateEvaluation,
    DigestReference,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEdition,
    SnapshotEntry,
    SnapshotEntryPlan,
    SnapshotExportArtifact,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeries,
    VitrineRecord,
)
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    inspect_snapshot_series_lock,
)
from vitrine.snapshot_distribution import (
    advance_snapshot_current_pointer,
    create_snapshot_directory_export,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
    SnapshotMaterializationError,
    SnapshotRendererDescriptor,
    SnapshotRendererRegistry,
    SnapshotRenderRequest,
    SnapshotRenderResult,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)
from vitrine.snapshot_services import (
    SnapshotAttemptExecutionResult,
    SnapshotWorkflowError,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import load_current_records

SNAPSHOT_FIXTURE_ROOT = ROOT / "fixtures" / "snapshot-workflows"

LOCKED_RUNTIME_FIXTURE_HASHES = {
    "tests/fixtures/runtime-models/improvement-foundational-records-v1.json": (
        "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8"
    ),
    "tests/fixtures/runtime-models/showcase-foundational-records-v1.json": (
        "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360"
    ),
}

SCOREFORM_RENDERER_ID = "vitrine_fixture_scoreform_snapshot_renderer"
SCOREFORM_RENDERER_VERSION = "1"
SCOREFORM_RENDERER_CONTRACT = "vitrine_fixture_scoreform_snapshot_renderer_v1"
REFLECTION_RENDERER_ID = "vitrine_fixture_reflection_snapshot_renderer"
REFLECTION_RENDERER_VERSION = "1"
REFLECTION_RENDERER_CONTRACT = "vitrine_fixture_reflection_snapshot_renderer_v1"

SCOREFORM_STRUCTURED_INPUT_SHA256 = (
    "39163a02bef62ef1ba48cf316c8216d10d8d8fe67afe07081eb4af10881c232a"
)
SCOREFORM_CONFIGURATION_BYTES = (
    b'{"format":"markdown","language":"en","renderer":"scoreform_attempt_summary",'
    b'"structured_input_sha256":"'
    + SCOREFORM_STRUCTURED_INPUT_SHA256.encode("ascii")
    + b'"}\n'
)
SCOREFORM_TEMPLATE_BYTES = (
    b"# {title}\n\n- Attempt origin: `{origin}`\n- Points: {earned} / {possible}\n"
)
REFLECTION_CONFIGURATION_BYTES = (
    b'{"format":"markdown","language":"en","renderer":"portfolio_reflection"}\n'
)
REFLECTION_TEMPLATE_BYTES = b"# Student Reflection\n\n{content}\n"
EXPORT_CONFIGURATION_BYTES = (
    b'{"export_format":"directory_package","internal_manifest":false}\n'
)


class SnapshotValidationError(RuntimeError):
    """One deterministic validation failure."""


@dataclass(frozen=True, slots=True)
class _FixtureAuthorityGate:
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        if request.operation != "build_snapshot":
            return SnapshotBuildAuthorityDecision(outcome="denied")
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="snapshot_fixture_local_build_authority",
        )


@dataclass
class _FixtureSourceProvider:
    descriptor: SnapshotSourceProviderDescriptor
    source_root: Path
    allowed: dict[tuple[str, str], str]

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotSourceResult:
        artifact = request.entry_plan.source_artifact
        publication_id = request.entry_plan.source_publication_id
        if artifact is None or publication_id is None:
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Fixture source request lacks exact planned source identity.",
                stage="fixture_source_resolution",
            )
        key = (publication_id, artifact.artifact_id)
        expected = self.allowed.get(key)
        if (
            expected is None
            or artifact.source_locator is None
            or artifact.source_locator != expected
        ):
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Fixture provider refuses a source outside its exact approved inventory.",
                stage="fixture_source_resolution",
            )
        return SnapshotSourceResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=publication_id,
            source_artifact_id=artifact.artifact_id,
            source_root=self.source_root,
            source_relative_path=expected,
        )

    def confirm_stability(
        self, request: SnapshotSourceRequest, result: SnapshotSourceResult
    ) -> bool:
        artifact = request.entry_plan.source_artifact
        return (
            artifact is not None
            and result.source_artifact_id == artifact.artifact_id
            and result.source_publication_id
            == request.entry_plan.source_publication_id
        )


@dataclass
class _ScoreFormFixtureRenderer:
    expected_candidate_id: str
    structured: dict[str, object]
    descriptor: SnapshotRendererDescriptor = SnapshotRendererDescriptor(
        renderer_id=SCOREFORM_RENDERER_ID,
        renderer_version=SCOREFORM_RENDERER_VERSION,
        renderer_contract_version=SCOREFORM_RENDERER_CONTRACT,
    )

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        candidate_refs = tuple(
            item
            for item in request.entry_plan.input_references
            if item.record_type == "portfolio_candidate"
        )
        if (
            len(candidate_refs) != 1
            or candidate_refs[0].record_id != self.expected_candidate_id
            or candidate_refs[0].record_revision is not None
        ):
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "ScoreForm fixture renderer requires one exact planned Candidate.",
                stage="render",
            )
        required = {
            "attempt_number",
            "attempt_origin",
            "points_earned",
            "points_possible",
            "response_states",
            "source_record_id",
            "standard_alignments",
        }
        if set(self.structured) != required:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "ScoreForm structured fixture has an unexpected shape.",
                stage="render",
            )
        states = self.structured["response_states"]
        standards = self.structured["standard_alignments"]
        if not isinstance(states, list) or not isinstance(standards, list):
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "ScoreForm structured fixture lists are invalid.",
                stage="render",
            )
        content = (
            "# Synthetic Argument Assessment — Attempt "
            f"{self.structured['attempt_number']}\n\n"
            f"- Attempt origin: `{self.structured['attempt_origin']}`\n"
            f"- Points: {self.structured['points_earned']} / "
            f"{self.structured['points_possible']}\n"
            "- Response states: "
            + ", ".join(f"`{item}`" for item in states)
            + "\n- Standards: "
            + ", ".join(f"`{item}`" for item in standards)
            + "\n"
        ).encode("utf-8")
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=content,
            media_type="text/markdown",
            configuration_digest=_digest(SCOREFORM_CONFIGURATION_BYTES),
            template_digest=_digest(SCOREFORM_TEMPLATE_BYTES),
            language="en",
        )


@dataclass
class _ReflectionFixtureRenderer:
    reflection: PortfolioReflection
    descriptor: SnapshotRendererDescriptor = SnapshotRendererDescriptor(
        renderer_id=REFLECTION_RENDERER_ID,
        renderer_version=REFLECTION_RENDERER_VERSION,
        renderer_contract_version=REFLECTION_RENDERER_CONTRACT,
    )

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        refs = tuple(
            item
            for item in request.entry_plan.input_references
            if item.record_type == "portfolio_reflection"
        )
        if (
            len(refs) != 1
            or refs[0].record_id != self.reflection.reflection_id
            or refs[0].record_revision != self.reflection.reflection_revision
        ):
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Reflection fixture renderer requires the exact frozen Reflection revision.",
                stage="render",
            )
        content = (
            "# Student Reflection\n\n" + self.reflection.content + "\n"
        ).encode("utf-8")
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=content,
            media_type="text/markdown",
            configuration_digest=_digest(REFLECTION_CONFIGURATION_BYTES),
            template_digest=_digest(REFLECTION_TEMPLATE_BYTES),
            language=self.reflection.language,
        )


def _digest(value: bytes) -> DigestReference:
    return DigestReference(value=hashlib.sha256(value).hexdigest())


def _records(setup: RepresentativeSnapshotFixtureWorkspace) -> tuple[VitrineRecord, ...]:
    return load_current_records(setup.workspace)


def _candidate_for_selection(
    setup: RepresentativeSnapshotFixtureWorkspace,
    selection: PortfolioSelection,
) -> PortfolioCandidate:
    values = tuple(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == selection.candidate_id
    )
    if len(values) != 1:
        raise SnapshotValidationError("exact Selection Candidate did not resolve.")
    return values[0]


def _evaluation_for_candidate(
    setup: RepresentativeSnapshotFixtureWorkspace,
    candidate: PortfolioCandidate,
) -> CandidateEvaluation:
    values = tuple(
        item
        for item in _records(setup)
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == candidate.candidate_evaluation_id
    )
    if len(values) != 1:
        raise SnapshotValidationError("exact Candidate Evaluation did not resolve.")
    return values[0]


def _source_entry(
    setup: RepresentativeSnapshotFixtureWorkspace,
    *,
    selection: PortfolioSelection,
    placement: PortfolioPlacement,
    entry_plan_id: str,
    position: int,
    target_relative_path: str,
    semantic_role: str,
    permitted_omission_reason: str | None = None,
) -> SnapshotEntryPlan:
    candidate = _candidate_for_selection(setup, selection)
    artifact = candidate.source_endpoint.source_artifact
    if artifact is None or artifact.source_locator is None:
        raise SnapshotValidationError("copied source fixture requires exact Artifact locator.")
    content_class = {
        "original_student_work": "student_work",
        "rendered_feedback": "feedback",
    }.get(artifact.artifact_kind)
    if content_class is None:
        raise SnapshotValidationError("unexpected copied fixture Artifact kind.")
    return SnapshotEntryPlan(
        entry_plan_id=entry_plan_id,
        plan_position=position,
        section_id=placement.section_id,
        ordinal=1,
        semantic_role=semantic_role,
        materialization_kind="copied_source",
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target_relative_path,
        media_type=artifact.media_type,
        permitted_omission_reason=permitted_omission_reason,
    )


def _scoreform_entry(
    setup: RepresentativeSnapshotFixtureWorkspace,
    *,
    position: int,
) -> SnapshotEntryPlan:
    selection = setup.scoreform_selection
    placement = setup.scoreform_placement
    candidate = _candidate_for_selection(setup, selection)
    evaluation = _evaluation_for_candidate(setup, candidate)
    if (
        candidate.source_endpoint.producer_source.source_record_id
        != "argument_assessment_attempt_1"
    ):
        raise SnapshotValidationError("fixture ScoreForm Candidate changed identity.")
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_scoreform_attempt_1",
        plan_position=position,
        section_id=placement.section_id,
        ordinal=1,
        semantic_role="assessment_summary",
        materialization_kind="generated_vitrine",
        content_class="assessment_summary",
        target_relative_path="assessment/attempt-1.md",
        media_type="text/markdown",
        renderer_id=SCOREFORM_RENDERER_ID,
        renderer_version=SCOREFORM_RENDERER_VERSION,
        renderer_contract_version=SCOREFORM_RENDERER_CONTRACT,
        renderer_configuration_digest=_digest(SCOREFORM_CONFIGURATION_BYTES),
        renderer_template_digest=_digest(SCOREFORM_TEMPLATE_BYTES),
        input_references=(
            SnapshotInputReference(
                record_type="portfolio_selection",
                record_id=selection.selection_id,
            ),
            SnapshotInputReference(
                record_type="portfolio_placement",
                record_id=placement.placement_id,
            ),
            SnapshotInputReference(
                record_type="portfolio_candidate",
                record_id=candidate.candidate_id,
            ),
            SnapshotInputReference(
                record_type="candidate_evaluation",
                record_id=evaluation.candidate_evaluation_id,
            ),
        ),
    )


def _reflection_entry(
    setup: RepresentativeSnapshotFixtureWorkspace,
    *,
    position: int,
) -> SnapshotEntryPlan:
    reflection = setup.reflection
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_student_reflection",
        plan_position=position,
        section_id="later_work",
        ordinal=2,
        semantic_role="student_reflection",
        materialization_kind="generated_vitrine",
        content_class="student_work",
        target_relative_path="later/reflection.md",
        media_type="text/markdown",
        renderer_id=REFLECTION_RENDERER_ID,
        renderer_version=REFLECTION_RENDERER_VERSION,
        renderer_contract_version=REFLECTION_RENDERER_CONTRACT,
        renderer_configuration_digest=_digest(REFLECTION_CONFIGURATION_BYTES),
        renderer_template_digest=_digest(REFLECTION_TEMPLATE_BYTES),
        input_references=(
            SnapshotInputReference(
                record_type="portfolio_reflection",
                record_id=reflection.reflection_id,
                record_revision=reflection.reflection_revision,
            ),
            SnapshotInputReference(
                record_type="working_portfolio_composition_revision",
                record_id=setup.composition.portfolio_id,
                record_revision=setup.composition.composition_revision,
            ),
        ),
    )


def _entry_plans(
    setup: RepresentativeSnapshotFixtureWorkspace,
    *,
    later_omission: bool,
) -> tuple[SnapshotEntryPlan, ...]:
    return (
        _source_entry(
            setup,
            selection=setup.baseline_selection,
            placement=setup.baseline_placement,
            entry_plan_id="entry_plan_quillan_baseline",
            position=1,
            target_relative_path="baseline/work.txt",
            semantic_role="baseline_work",
        ),
        _source_entry(
            setup,
            selection=setup.later_selection,
            placement=setup.later_placement,
            entry_plan_id="entry_plan_quillan_later",
            position=2,
            target_relative_path="later/work.txt",
            semantic_role="later_work",
            permitted_omission_reason=(
                "source_unavailable" if later_omission else None
            ),
        ),
        _source_entry(
            setup,
            selection=setup.feedback_selection,
            placement=setup.feedback_placement,
            entry_plan_id="entry_plan_quillan_feedback",
            position=3,
            target_relative_path="feedback/student-feedback.md",
            semantic_role="student_feedback",
        ),
        _scoreform_entry(setup, position=4),
        _reflection_entry(setup, position=5),
    )


def _provider_registry(
    entries: tuple[SnapshotEntryPlan, ...], source_root: Path
) -> SnapshotSourceProviderRegistry:
    grouped: dict[
        tuple[str, str, str, str, str],
        dict[tuple[str, str], str],
    ] = {}
    for entry in entries:
        if entry.materialization_kind != "copied_source":
            continue
        artifact = entry.source_artifact
        if (
            artifact is None
            or artifact.source_locator is None
            or entry.producer_module_id is None
            or entry.projection_kind is None
            or entry.projection_contract_version is None
            or entry.source_publication_id is None
        ):
            raise SnapshotValidationError("copied Entry Plan is incomplete.")
        support_key = (
            entry.producer_module_id,
            entry.projection_kind,
            entry.projection_contract_version,
            artifact.artifact_kind,
            artifact.representation_kind,
        )
        grouped.setdefault(support_key, {})[
            (entry.source_publication_id, artifact.artifact_id)
        ] = artifact.source_locator
    providers = []
    for number, (support_key, allowed) in enumerate(
        sorted(grouped.items()), start=1
    ):
        providers.append(
            _FixtureSourceProvider(
                descriptor=SnapshotSourceProviderDescriptor(
                    provider_id=f"snapshot_fixture_source_provider_{number}",
                    provider_version="1",
                    producer_module_id=support_key[0],
                    projection_kind=support_key[1],
                    projection_contract_version=support_key[2],
                    artifact_kind=support_key[3],
                    representation_kind=support_key[4],
                ),
                source_root=source_root,
                allowed=allowed,
            )
        )
    return SnapshotSourceProviderRegistry(tuple(providers))


def _structured_scoreform() -> dict[str, object]:
    path = SNAPSHOT_FIXTURE_ROOT / "structured" / "scoreform-attempt-1.json"
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != SCOREFORM_STRUCTURED_INPUT_SHA256:
        raise SnapshotValidationError(
            "structured ScoreForm fixture changed from the Plan-bound input digest."
        )
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotValidationError(
            "structured ScoreForm fixture is not valid UTF-8 JSON."
        ) from error
    if not isinstance(value, dict):
        raise SnapshotValidationError("structured ScoreForm fixture must be one object.")
    return value


def _renderer_registry(
    setup: RepresentativeSnapshotFixtureWorkspace,
) -> SnapshotRendererRegistry:
    scoreform_candidate = _candidate_for_selection(
        setup, setup.scoreform_selection
    )
    return SnapshotRendererRegistry(
        (
            _ScoreFormFixtureRenderer(
                expected_candidate_id=scoreform_candidate.candidate_id,
                structured=_structured_scoreform(),
            ),
            _ReflectionFixtureRenderer(reflection=setup.reflection),
        )
    )


def _series_request_plan_attempt(
    setup: RepresentativeSnapshotFixtureWorkspace,
    *,
    later_omission: bool,
    key_suffix: str,
) -> tuple[
    SnapshotSeries,
    SnapshotBuildRequest,
    SnapshotBuildPlan,
    SnapshotBuildAttempt,
    tuple[SnapshotEntryPlan, ...],
]:
    series_result = create_snapshot_series(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        audience_context_id=setup.audience.audience_context_id,
        snapshot_purpose="improvement",
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    series = next(
        item for item in series_result.records if isinstance(item, SnapshotSeries)
    )
    request_result = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=setup.composition.composition_revision,
        requested_by=ACTOR,
        idempotency_key=f"snapshot-validator-{key_suffix}",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    request = next(
        item
        for item in request_result.records
        if isinstance(item, SnapshotBuildRequest)
    )
    entries = _entry_plans(setup, later_omission=later_omission)
    export = SnapshotExportPlan(
        export_plan_id=f"export_plan_{key_suffix}",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=_digest(EXPORT_CONFIGURATION_BYTES),
    )
    plan_result = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=setup.inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(
        item for item in plan_result.records if isinstance(item, SnapshotBuildPlan)
    )
    started = start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return series, request, plan, started.attempt, entries


def validate_locked_runtime_fixture_hashes(root: Path = ROOT) -> None:
    for relative_path, expected in LOCKED_RUNTIME_FIXTURE_HASHES.items():
        path = root / relative_path
        if not path.is_file():
            raise SnapshotValidationError(
                f"locked runtime fixture is missing: {relative_path}"
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SnapshotValidationError(
                f"locked runtime fixture changed: {relative_path}"
            )


def validate_snapshot_fixture_index(root: Path = ROOT) -> None:
    fixture_root = root / "fixtures" / "snapshot-workflows"
    index_path = fixture_root / "fixture-index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotValidationError("Snapshot fixture index is unreadable.") from error
    if (
        not isinstance(index, dict)
        or index.get("fixture_contract") != "vitrine_snapshot_workflow_fixture_v1"
        or index.get("fixture_version") != "1"
        or index.get("integration_kind") != "development_fixture"
    ):
        raise SnapshotValidationError("Snapshot fixture index contract is invalid.")
    rows = index.get("files")
    if not isinstance(rows, list) or not rows:
        raise SnapshotValidationError("Snapshot fixture index has no files.")
    declared: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise SnapshotValidationError("Snapshot fixture index row is invalid.")
        relative = raw.get("path")
        digest = raw.get("sha256")
        size = raw.get("size")
        if (
            not isinstance(relative, str)
            or not relative
            or relative.startswith("/")
            or "\\" in relative
            or ".." in Path(relative).parts
            or not isinstance(digest, str)
            or len(digest) != 64
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise SnapshotValidationError("Snapshot fixture index row is malformed.")
        if relative in declared:
            raise SnapshotValidationError("Snapshot fixture index duplicates a path.")
        declared.add(relative)
        path = fixture_root.joinpath(*relative.split("/"))
        if not path.is_file():
            raise SnapshotValidationError(
                f"Snapshot fixture payload is missing: {relative}"
            )
        payload = path.read_bytes()
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise SnapshotValidationError(
                f"Snapshot fixture payload digest/size mismatch: {relative}"
            )
    actual = {
        path.relative_to(fixture_root).as_posix()
        for path in fixture_root.rglob("*")
        if path.is_file()
        and path.name not in {"README.md", "fixture-index.json"}
    }
    if actual != declared:
        raise SnapshotValidationError(
            "Snapshot fixture index does not exactly cover committed fixture payloads."
        )


def _copy_source_fixture(destination: Path) -> Path:
    source = SNAPSHOT_FIXTURE_ROOT / "source-root"
    shutil.copytree(source, destination)
    return destination.resolve(strict=True)


def _assert_success_inventory(
    setup: RepresentativeSnapshotFixtureWorkspace,
    execution: SnapshotAttemptExecutionResult,
    edition_path: Path,
) -> None:
    dispositions = tuple(item.disposition for item in execution.entries)
    if dispositions != (
        "prepared_bytes",
        "omission_pending",
        "prepared_bytes",
        "prepared_bytes",
        "prepared_bytes",
    ):
        raise SnapshotValidationError(
            f"unexpected representative prepared dispositions: {dispositions}"
        )
    content_root = edition_path / "content"
    expected_files = {
        "baseline/work.txt",
        "feedback/student-feedback.md",
        "assessment/attempt-1.md",
        "later/reflection.md",
    }
    actual_files = {
        path.relative_to(content_root).as_posix()
        for path in content_root.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise SnapshotValidationError(
            f"sealed representative byte inventory differs: {sorted(actual_files)}"
        )
    if (content_root / "baseline/work.txt").read_bytes() != (
        SNAPSHOT_FIXTURE_ROOT
        / "source-root"
        / "artifacts"
        / "selected-analysis.txt"
    ).read_bytes():
        raise SnapshotValidationError("Quillan student work was not copied exactly.")
    if (content_root / "feedback/student-feedback.md").read_bytes() != (
        SNAPSHOT_FIXTURE_ROOT
        / "source-root"
        / "artifacts"
        / "student-feedback.md"
    ).read_bytes():
        raise SnapshotValidationError("Quillan student feedback was not copied exactly.")
    if (content_root / "assessment/attempt-1.md").read_bytes() != (
        SNAPSHOT_FIXTURE_ROOT / "expected" / "scoreform-attempt-1.md"
    ).read_bytes():
        raise SnapshotValidationError(
            "structured ScoreForm fixture did not render deterministically."
        )
    if (content_root / "later/reflection.md").read_bytes() != (
        SNAPSHOT_FIXTURE_ROOT / "expected" / "reflection.md"
    ).read_bytes():
        raise SnapshotValidationError(
            "exact frozen Reflection did not render deterministically."
        )
    if (content_root / "later/work.txt").exists():
        raise SnapshotValidationError("permitted omitted source unexpectedly materialized.")
    records = _records(setup)
    omissions = tuple(
        item
        for item in records
        if isinstance(item, SnapshotOmission)
        and item.reason_code == "source_unavailable"
    )
    if len(omissions) != 1:
        raise SnapshotValidationError("exactly one permitted Snapshot Omission is required.")
    if omissions[0].selection_id != setup.later_selection.selection_id:
        raise SnapshotValidationError("Snapshot Omission lost exact Selection provenance.")


def _validate_successful_build(base: Path) -> None:
    setup = build_representative_snapshot_fixture_workspace(base / "success")
    source_root = _copy_source_fixture(base / "success-source")
    # Exact planned later source becomes unavailable; Plan explicitly permits this.
    (source_root / "artifacts" / "approved-paragraph.txt").unlink()
    series, _, plan, attempt, entries = _series_request_plan_attempt(
        setup,
        later_omission=True,
        key_suffix="success",
    )
    execution = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_FixtureAuthorityGate(),
        source_providers=_provider_registry(entries, source_root),
        renderers=_renderer_registry(setup),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=execution,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    if sealed.edition_path is None:
        raise SnapshotValidationError("sealed Edition custody path is absent.")
    _assert_success_inventory(setup, execution, sealed.edition_path)
    verification = verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    if verification.manifest_digest != sealed.seal.manifest_digest:
        raise SnapshotValidationError("Manifest digest verification did not reproduce.")
    if (
        verification.logical_inventory_digest
        != sealed.seal.logical_inventory_digest
    ):
        raise SnapshotValidationError(
            "logical-inventory digest verification did not reproduce."
        )
    export = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="snapshot_export_representative",
    )
    export_verification = verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
        verified_at=fixed_clock(),
    )
    if (
        export_verification.directory_inventory_digest
        != export.export_artifact.directory_inventory_digest
    ):
        raise SnapshotValidationError("directory Export digest did not reproduce.")
    replay = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=export.state_revision,
        generated_at=fixed_clock(),
        artifact_id="snapshot_export_replay_unused",
    )
    if (
        replay.export_artifact.snapshot_export_artifact_id
        != export.export_artifact.snapshot_export_artifact_id
        or replay.state_revision != export.state_revision
    ):
        raise SnapshotValidationError("exact Export replay rewrote immutable Export state.")
    pointer = advance_snapshot_current_pointer(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        expected_state_revision=export.state_revision,
        expected_pointer_revision=None,
        expected_current_edition=None,
        pointed_by=ACTOR,
        authority_reference="snapshot_fixture_pointer_authority",
        reason="Promote verified representative fixture Edition.",
        pointed_at=fixed_clock(),
        pointer_id="snapshot_current_pointer_representative",
    )
    if pointer.pointer.edition_number != sealed.edition.edition_number:
        raise SnapshotValidationError("explicit Current Pointer target is wrong.")
    # Original producer fixture availability is no longer required after sealing.
    shutil.rmtree(source_root)
    verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
        verified_at=fixed_clock(),
    )
    try:
        inspect_snapshot_series_lock(
            setup.workspace, snapshot_series_id=series.snapshot_series_id
        )
    except SnapshotCustodyError as error:
        if error.code != "snapshot.build_lock_missing":
            raise
    else:
        raise SnapshotValidationError("sealed Attempt left its Series build lock.")
    records = _records(setup)
    if len([item for item in records if isinstance(item, SnapshotEdition)]) != 1:
        raise SnapshotValidationError("representative successful build must seal one Edition.")
    if len([item for item in records if isinstance(item, SnapshotExportArtifact)]) != 1:
        raise SnapshotValidationError("representative build must persist one Export Artifact.")
    terminal = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
    )
    if len(terminal) != 1 or terminal[0].terminal_outcome != "sealed":
        raise SnapshotValidationError("successful Attempt terminal history is incorrect.")
    materializations = tuple(
        item
        for item in records
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == sealed.edition.reference
    )
    entries_persisted = tuple(
        item
        for item in records
        if isinstance(item, SnapshotEntry)
        and item.snapshot_edition == sealed.edition.reference
    )
    if len(materializations) != 4 or len(entries_persisted) != 4:
        raise SnapshotValidationError(
            "representative Edition requires four byte-bearing Materializations/Entries."
        )
    if (
        sealed.seal.manifest_digest == sealed.seal.logical_inventory_digest
        or sealed.seal.manifest_digest
        == export.export_artifact.directory_inventory_digest
        or sealed.seal.logical_inventory_digest
        == export.export_artifact.directory_inventory_digest
    ):
        raise SnapshotValidationError("Snapshot digest layers were collapsed.")
    forbidden = (
        b"PRIVATE_TEACHER_NOTE",
        b"PRIVATE_ANSWER_KEY",
        b"PRIVATE_SCAN_REVIEW_NOTE",
        b"proficiency",
        b"mastery",
    )
    for path in export.export_path.rglob("*"):
        if path.is_file():
            payload = path.read_bytes()
            if any(marker in payload for marker in forbidden):
                raise SnapshotValidationError(
                    f"forbidden producer/private semantic leaked into Export: {path.name}"
                )
    if (export.export_path / "internal" / "manifest.json").exists():
        raise SnapshotValidationError("internal Snapshot Manifest leaked into Export.")
    custody = inspect_snapshot_custody(setup.workspace)
    errors = tuple(item for item in custody.findings if item.severity == "error")
    if errors:
        raise SnapshotValidationError(
            f"sealed representative custody audit has errors: {[item.code for item in errors]}"
        )


def _validate_blocking_failure(base: Path) -> None:
    setup = build_representative_snapshot_fixture_workspace(base / "blocking")
    source_root = _copy_source_fixture(base / "blocking-source")
    # Baseline has no permitted omission, so exact-source loss blocks sealing.
    (source_root / "artifacts" / "selected-analysis.txt").unlink()
    series, _, _, attempt, entries = _series_request_plan_attempt(
        setup,
        later_omission=True,
        key_suffix="blocking",
    )
    try:
        execute_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            authority_gate=_FixtureAuthorityGate(),
            source_providers=_provider_registry(entries, source_root),
            renderers=_renderer_registry(setup),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    except SnapshotWorkflowError as error:
        if error.code != "snapshot.materialization_failed":
            raise SnapshotValidationError(
                f"unexpected blocking failure code: {error.code}"
            ) from error
    else:
        raise SnapshotValidationError("unpermitted missing source did not block Attempt.")
    records = _records(setup)
    if any(isinstance(item, SnapshotEdition) for item in records):
        raise SnapshotValidationError("blocking pre-seal failure created an Edition.")
    terminal = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
    )
    if len(terminal) != 1 or terminal[0].terminal_outcome != "failed":
        raise SnapshotValidationError("blocking Attempt terminal history is missing.")
    if not all(
        outcome.disposition == "failed_blocking"
        for outcome in terminal[0].entry_outcomes
        if outcome.disposition != "reference_only"
    ):
        raise SnapshotValidationError("blocking Attempt silently omitted planned items.")
    try:
        inspect_snapshot_series_lock(
            setup.workspace, snapshot_series_id=series.snapshot_series_id
        )
    except SnapshotCustodyError as error:
        if error.code != "snapshot.build_lock_missing":
            raise
    else:
        raise SnapshotValidationError("failed Attempt left its Series build lock.")


def validate() -> None:
    validate_locked_runtime_fixture_hashes()
    validate_snapshot_fixture_index()
    with tempfile.TemporaryDirectory(
        prefix="vitrine-snapshot-workflow-validation-"
    ) as temporary:
        root = Path(temporary)
        _validate_successful_build(root)
        _validate_blocking_failure(root)


def main() -> int:
    try:
        validate()
        print("PASS immutable Snapshot workflow validation")
        return 0
    except (
        OSError,
        RuntimeError,
        SnapshotCustodyError,
        SnapshotMaterializationError,
        SnapshotWorkflowError,
    ) as error:
        print(f"Snapshot workflow validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
