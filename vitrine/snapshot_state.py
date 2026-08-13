"""Pure projection and validation for additive Snapshot build workflow history."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from vitrine.models.audiences import AudienceContext
from vitrine.models.candidates import CandidateEvaluation, PortfolioCandidate
from vitrine.models.conversion import value_to_json
from vitrine.models.curation import (
    PortfolioPlacement,
    PortfolioSelection,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.curation_workflow import (
    CurationAnnotation,
    CurationReviewDecision,
    PortfolioReflection,
    WorkingPortfolioCompositionInventory,
)
from vitrine.models.errors import ValidationIssue, VitrineRecordGraphError
from vitrine.models.identity import Portfolio
from vitrine.models.profiles import PortfolioProfileBinding
from vitrine.models.snapshot_workflow import (
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEditionBuildProvenance,
    SnapshotExportArtifact,
    SnapshotInputReference,
    SnapshotMaterializationProvenance,
    SnapshotSeries,
)
from vitrine.models.snapshots import (
    SnapshotEdition,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
)


def _issue(
    code: str,
    message: str,
    record_type: str | None = None,
    record_id: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        record_type=record_type,
        record_id=record_id,
    )


def _cycle_representatives(predecessors: dict[str, str | None]) -> tuple[str, ...]:
    representatives: set[str] = set()
    for start in sorted(predecessors):
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start
        while current is not None and current in predecessors:
            if current in positions:
                representatives.add(min(path[positions[current] :]))
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessors[current]
    return tuple(sorted(representatives))


def _portable_path_key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


def snapshot_plan_fingerprint(plan: SnapshotBuildPlan) -> str:
    """Calculate the canonical SHA-256 fingerprint for a Build Plan."""

    value = value_to_json(plan)
    if not isinstance(value, dict):
        raise AssertionError("SnapshotBuildPlan did not serialize to an object")
    canonical = dict(value)
    canonical.pop("plan_fingerprint", None)
    payload = (
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class SnapshotState:
    portfolios: tuple[Portfolio, ...]
    profile_bindings: tuple[PortfolioProfileBinding, ...]
    audience_contexts: tuple[AudienceContext, ...]
    compositions: tuple[WorkingPortfolioCompositionRevision, ...]
    composition_inventories: tuple[WorkingPortfolioCompositionInventory, ...]
    reviews: tuple[CurationReviewDecision, ...]
    annotations: tuple[CurationAnnotation, ...]
    reflections: tuple[PortfolioReflection, ...]
    candidate_evaluations: tuple[CandidateEvaluation, ...]
    candidates: tuple[PortfolioCandidate, ...]
    selections: tuple[PortfolioSelection, ...]
    placements: tuple[PortfolioPlacement, ...]
    materializations: tuple[SnapshotMaterializationRecord, ...]
    entries: tuple[SnapshotEntry, ...]
    omissions: tuple[SnapshotOmission, ...]
    manifests: tuple[SnapshotManifest, ...]
    seals: tuple[SnapshotSeal, ...]
    editions: tuple[SnapshotEdition, ...]
    series: tuple[SnapshotSeries, ...]
    requests: tuple[SnapshotBuildRequest, ...]
    plans: tuple[SnapshotBuildPlan, ...]
    attempts: tuple[SnapshotBuildAttempt, ...]
    attempt_results: tuple[SnapshotBuildAttemptResult, ...]
    materialization_provenance: tuple[SnapshotMaterializationProvenance, ...]
    edition_build_provenance: tuple[SnapshotEditionBuildProvenance, ...]
    export_artifacts: tuple[SnapshotExportArtifact, ...]
    current_pointers: tuple[SnapshotCurrentPointerRevision, ...]

    def pointer_heads(self, snapshot_series_id: str) -> tuple[SnapshotCurrentPointerRevision, ...]:
        values = tuple(
            item
            for item in self.current_pointers
            if item.snapshot_series_id == snapshot_series_id
        )
        predecessor_keys = {
            (item.snapshot_current_pointer_id, item.predecessor_pointer_revision)
            for item in values
            if item.predecessor_pointer_revision is not None
        }
        return tuple(
            sorted(
                (
                    item
                    for item in values
                    if (item.snapshot_current_pointer_id, item.pointer_revision)
                    not in predecessor_keys
                ),
                key=lambda item: (
                    item.snapshot_current_pointer_id,
                    item.pointer_revision,
                ),
            )
        )

    def current_edition(self, snapshot_series_id: str) -> SnapshotEdition | None:
        heads = self.pointer_heads(snapshot_series_id)
        if len(heads) != 1:
            return None
        head = heads[0]
        return next(
            (
                item
                for item in self.editions
                if item.snapshot_series_id == snapshot_series_id
                and item.edition_number == head.edition_number
            ),
            None,
        )

    def result_for_attempt(self, attempt_id: str) -> SnapshotBuildAttemptResult | None:
        values = tuple(
            item
            for item in self.attempt_results
            if item.snapshot_build_attempt_id == attempt_id
        )
        return values[0] if len(values) == 1 else None


def project_snapshot_state(records: Iterable[object]) -> SnapshotState:
    values = tuple(records)
    return SnapshotState(
        portfolios=tuple(item for item in values if isinstance(item, Portfolio)),
        profile_bindings=tuple(
            item for item in values if isinstance(item, PortfolioProfileBinding)
        ),
        audience_contexts=tuple(item for item in values if isinstance(item, AudienceContext)),
        compositions=tuple(
            item
            for item in values
            if isinstance(item, WorkingPortfolioCompositionRevision)
        ),
        composition_inventories=tuple(
            item
            for item in values
            if isinstance(item, WorkingPortfolioCompositionInventory)
        ),
        reviews=tuple(item for item in values if isinstance(item, CurationReviewDecision)),
        annotations=tuple(item for item in values if isinstance(item, CurationAnnotation)),
        reflections=tuple(item for item in values if isinstance(item, PortfolioReflection)),
        candidate_evaluations=tuple(
            item for item in values if isinstance(item, CandidateEvaluation)
        ),
        candidates=tuple(item for item in values if isinstance(item, PortfolioCandidate)),
        selections=tuple(item for item in values if isinstance(item, PortfolioSelection)),
        placements=tuple(item for item in values if isinstance(item, PortfolioPlacement)),
        materializations=tuple(
            item for item in values if isinstance(item, SnapshotMaterializationRecord)
        ),
        entries=tuple(item for item in values if isinstance(item, SnapshotEntry)),
        omissions=tuple(item for item in values if isinstance(item, SnapshotOmission)),
        manifests=tuple(item for item in values if isinstance(item, SnapshotManifest)),
        seals=tuple(item for item in values if isinstance(item, SnapshotSeal)),
        editions=tuple(item for item in values if isinstance(item, SnapshotEdition)),
        series=tuple(item for item in values if isinstance(item, SnapshotSeries)),
        requests=tuple(item for item in values if isinstance(item, SnapshotBuildRequest)),
        plans=tuple(item for item in values if isinstance(item, SnapshotBuildPlan)),
        attempts=tuple(item for item in values if isinstance(item, SnapshotBuildAttempt)),
        attempt_results=tuple(
            item for item in values if isinstance(item, SnapshotBuildAttemptResult)
        ),
        materialization_provenance=tuple(
            item
            for item in values
            if isinstance(item, SnapshotMaterializationProvenance)
        ),
        edition_build_provenance=tuple(
            item for item in values if isinstance(item, SnapshotEditionBuildProvenance)
        ),
        export_artifacts=tuple(
            item for item in values if isinstance(item, SnapshotExportArtifact)
        ),
        current_pointers=tuple(
            item for item in values if isinstance(item, SnapshotCurrentPointerRevision)
        ),
    )


def _input_reference_exists(state: SnapshotState, reference: SnapshotInputReference) -> bool:
    revision = reference.record_revision
    if reference.record_type == "working_portfolio_composition_revision":
        return revision is not None and any(
            item.portfolio_id == reference.record_id
            and item.composition_revision == revision
            for item in state.compositions
        )
    if reference.record_type == "curation_annotation":
        return revision is not None and any(
            item.annotation_id == reference.record_id
            and item.annotation_revision == revision
            for item in state.annotations
        )
    if reference.record_type == "portfolio_reflection":
        return revision is not None and any(
            item.reflection_id == reference.record_id
            and item.reflection_revision == revision
            for item in state.reflections
        )
    if reference.record_type == "portfolio_selection":
        return revision is None and any(
            item.selection_id == reference.record_id for item in state.selections
        )
    if reference.record_type == "portfolio_placement":
        return revision is None and any(
            item.placement_id == reference.record_id for item in state.placements
        )
    if reference.record_type == "portfolio_candidate":
        return revision is None and any(
            item.candidate_id == reference.record_id for item in state.candidates
        )
    if reference.record_type == "candidate_evaluation":
        return revision is None and any(
            item.candidate_evaluation_id == reference.record_id
            for item in state.candidate_evaluations
        )
    return False


def collect_snapshot_state_issues(state: SnapshotState) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    portfolios = {item.portfolio_id: item for item in state.portfolios}
    bindings = {item.profile_binding_id: item for item in state.profile_bindings}
    audiences = {item.audience_context_id: item for item in state.audience_contexts}
    compositions = {
        (item.portfolio_id, item.composition_revision): item
        for item in state.compositions
    }
    inventories = {
        (item.portfolio_id, item.composition_revision): item
        for item in state.composition_inventories
    }
    reviews = {item.curation_review_decision_id: item for item in state.reviews}
    candidates = {item.candidate_id: item for item in state.candidates}
    evaluations = {
        item.candidate_evaluation_id: item for item in state.candidate_evaluations
    }
    selections = {item.selection_id: item for item in state.selections}
    placements = {item.placement_id: item for item in state.placements}
    materializations = {item.materialization_id: item for item in state.materializations}
    omissions = {item.snapshot_omission_id: item for item in state.omissions}
    editions = {
        (item.snapshot_series_id, item.edition_number): item for item in state.editions
    }
    series_by_id = {item.snapshot_series_id: item for item in state.series}
    requests = {item.snapshot_build_request_id: item for item in state.requests}
    plans = {item.snapshot_build_plan_id: item for item in state.plans}
    attempts = {item.snapshot_build_attempt_id: item for item in state.attempts}
    results = {
        item.snapshot_build_attempt_result_id: item for item in state.attempt_results
    }
    exports = {
        item.snapshot_export_artifact_id: item for item in state.export_artifacts
    }

    # Series context and predecessor history.
    series_successors: dict[str, list[str]] = defaultdict(list)
    for series_record in state.series:
        portfolio = portfolios.get(series_record.portfolio_id)
        audience = audiences.get(series_record.audience_context_id)
        if portfolio is None or portfolio.portfolio_subject_id != series_record.portfolio_subject_id:
            issues.append(
                _issue(
                    "snapshot.series_portfolio_mismatch",
                    "Snapshot Series Portfolio or Subject context is invalid.",
                    series_record.record_type,
                    series_record.snapshot_series_id,
                )
            )
        if audience is None or (
            audience.portfolio_id,
            audience.portfolio_subject_id,
        ) != (series_record.portfolio_id, series_record.portfolio_subject_id):
            issues.append(
                _issue(
                    "snapshot.series_audience_mismatch",
                    "Snapshot Series Audience Context is missing or belongs to another Portfolio.",
                    series_record.record_type,
                    series_record.snapshot_series_id,
                )
            )
        if series_record.predecessor_series_id is not None:
            series_predecessor = series_by_id.get(series_record.predecessor_series_id)
            if series_predecessor is None:
                issues.append(
                    _issue(
                        "snapshot.series_predecessor_missing",
                        "Snapshot Series predecessor does not exist.",
                        series_record.record_type,
                        series_record.snapshot_series_id,
                    )
                )
            elif (
                series_predecessor.portfolio_id,
                series_predecessor.portfolio_subject_id,
            ) != (series_record.portfolio_id, series_record.portfolio_subject_id):
                issues.append(
                    _issue(
                        "snapshot.series_predecessor_mismatch",
                        "Snapshot Series predecessor belongs to another Portfolio Subject.",
                        series_record.record_type,
                        series_record.snapshot_series_id,
                    )
                )
            series_successors[series_record.predecessor_series_id].append(series_record.snapshot_series_id)
    for series_predecessor_id, series_successor_ids in sorted(series_successors.items()):
        if len(series_successor_ids) > 1:
            issues.append(
                _issue(
                    "snapshot.series_branch",
                    "Snapshot Series predecessor has multiple successors.",
                    "snapshot_series",
                    series_predecessor_id,
                )
            )
    series_predecessors = {
        series_record.snapshot_series_id: series_record.predecessor_series_id for series_record in state.series
    }
    for cycle in _cycle_representatives(series_predecessors):
        issues.append(
            _issue(
                "snapshot.series_cycle",
                "Snapshot Series predecessor history contains a cycle.",
                "snapshot_series",
                cycle,
            )
        )

    # Request exact context, reviews, idempotency, and predecessor history.
    request_successors: dict[str, list[str]] = defaultdict(list)
    idempotency: dict[tuple[str, str], str] = {}
    for request_record in state.requests:
        request_series = series_by_id.get(request_record.snapshot_series_id)
        request_binding = bindings.get(request_record.profile_binding_id)
        request_audience = audiences.get(request_record.audience_context_id)
        request_composition = compositions.get((request_record.portfolio_id, request_record.composition_revision))
        request_inventory = inventories.get((request_record.portfolio_id, request_record.composition_revision))
        if request_series is None or (
            request_series.portfolio_id,
            request_series.portfolio_subject_id,
            request_series.snapshot_purpose,
            request_series.audience_context_id,
        ) != (
            request_record.portfolio_id,
            request_record.portfolio_subject_id,
            request_record.snapshot_purpose,
            request_record.audience_context_id,
        ):
            issues.append(
                _issue(
                    "snapshot.request_series_mismatch",
                    "Build Request does not match its Snapshot Series.",
                    request_record.record_type,
                    request_record.snapshot_build_request_id,
                )
            )
        if request_binding is None or (
            request_binding.portfolio_id,
            request_binding.profile_revision,
        ) != (request_record.portfolio_id, request_record.profile_revision):
            issues.append(
                _issue(
                    "snapshot.request_binding_mismatch",
                    "Build Request Profile Binding or revision is invalid.",
                    request_record.record_type,
                    request_record.snapshot_build_request_id,
                )
            )
        expected_context = (
            request_record.portfolio_id,
            request_record.portfolio_subject_id,
            request_record.profile_binding_id,
            request_record.profile_revision,
        )
        if request_audience is None or (
            request_audience.portfolio_id,
            request_audience.portfolio_subject_id,
            request_audience.profile_binding_id,
            request_audience.profile_revision,
        ) != expected_context:
            issues.append(
                _issue(
                    "snapshot.request_audience_mismatch",
                    "Build Request Audience Context is missing or inconsistent.",
                    request_record.record_type,
                    request_record.snapshot_build_request_id,
                )
            )
        if request_composition is None or (
            request_composition.portfolio_subject_id,
            request_composition.profile_binding_id,
            request_composition.profile_revision,
        ) != (
            request_record.portfolio_subject_id,
            request_record.profile_binding_id,
            request_record.profile_revision,
        ):
            issues.append(
                _issue(
                    "snapshot.request_composition_mismatch",
                    "Build Request Composition is missing or inconsistent.",
                    request_record.record_type,
                    request_record.snapshot_build_request_id,
                )
            )
        if request_inventory is None or (
            request_inventory.profile_binding_id,
            request_inventory.profile_revision,
        ) != (request_record.profile_binding_id, request_record.profile_revision):
            issues.append(
                _issue(
                    "snapshot.request_inventory_mismatch",
                    "Build Request Composition Inventory is missing or inconsistent.",
                    request_record.record_type,
                    request_record.snapshot_build_request_id,
                )
            )
        for review_id in request_record.curation_review_decision_ids:
            if review_id not in reviews:
                issues.append(
                    _issue(
                        "snapshot.request_review_missing",
                        "Build Request references a missing Curation Review Decision.",
                        request_record.record_type,
                        request_record.snapshot_build_request_id,
                    )
                )
        if request_record.idempotency_key is not None:
            request_idempotency_key = (request_record.snapshot_series_id, request_record.idempotency_key)
            prior_request_id = idempotency.get(request_idempotency_key)
            if prior_request_id is not None and prior_request_id != request_record.snapshot_build_request_id:
                issues.append(
                    _issue(
                        "snapshot.request_idempotency_conflict",
                        "Snapshot Request idempotency key was reused for another Request.",
                        request_record.record_type,
                        request_record.snapshot_build_request_id,
                    )
                )
            idempotency[request_idempotency_key] = request_record.snapshot_build_request_id
        if request_record.predecessor_request_id is not None:
            request_predecessor = requests.get(request_record.predecessor_request_id)
            if request_predecessor is None:
                issues.append(
                    _issue(
                        "snapshot.request_predecessor_missing",
                        "Build Request predecessor does not exist.",
                        request_record.record_type,
                        request_record.snapshot_build_request_id,
                    )
                )
            elif (
                request_predecessor.snapshot_series_id,
                request_predecessor.portfolio_id,
                request_predecessor.profile_binding_id,
            ) != (
                request_record.snapshot_series_id,
                request_record.portfolio_id,
                request_record.profile_binding_id,
            ):
                issues.append(
                    _issue(
                        "snapshot.request_predecessor_mismatch",
                        "Build Request predecessor belongs to another Snapshot context.",
                        request_record.record_type,
                        request_record.snapshot_build_request_id,
                    )
                )
            request_successors[request_record.predecessor_request_id].append(
                request_record.snapshot_build_request_id
            )
    for request_predecessor_id, request_successor_ids in sorted(request_successors.items()):
        if len(request_successor_ids) > 1:
            issues.append(
                _issue(
                    "snapshot.request_branch",
                    "Build Request predecessor has multiple successors.",
                    "snapshot_build_request",
                    request_predecessor_id,
                )
            )
    request_predecessors = {
        request_record.snapshot_build_request_id: request_record.predecessor_request_id
        for request_record in state.requests
    }
    for cycle in _cycle_representatives(request_predecessors):
        issues.append(
            _issue(
                "snapshot.request_cycle",
                "Build Request predecessor history contains a cycle.",
                "snapshot_build_request",
                cycle,
            )
        )

    # Plan exact context, frozen source references, path policy, and fingerprint.
    plan_successors: dict[str, list[str]] = defaultdict(list)
    for plan_record in state.plans:
        plan_request = requests.get(plan_record.snapshot_build_request_id)
        if plan_request is None or (
            plan_request.snapshot_series_id,
            plan_request.portfolio_id,
            plan_request.portfolio_subject_id,
            plan_request.profile_binding_id,
            plan_request.profile_revision,
            plan_request.composition_revision,
            plan_request.audience_context_id,
        ) != (
            plan_record.snapshot_series_id,
            plan_record.portfolio_id,
            plan_record.portfolio_subject_id,
            plan_record.profile_binding_id,
            plan_record.profile_revision,
            plan_record.composition_revision,
            plan_record.audience_context_id,
        ):
            issues.append(
                _issue(
                    "snapshot.plan_request_mismatch",
                    "Build Plan does not reproduce the exact Build Request context.",
                    plan_record.record_type,
                    plan_record.snapshot_build_plan_id,
                )
            )
        if plan_request is not None:
            plan_formats = tuple(export.export_format for export in plan_record.export_plans)
            if tuple(plan_request.requested_export_formats) != plan_formats:
                issues.append(
                    _issue(
                        "snapshot.plan_export_mismatch",
                        "Build Plan Export formats differ from the Request.",
                        plan_record.record_type,
                        plan_record.snapshot_build_plan_id,
                    )
                )
        if snapshot_plan_fingerprint(plan_record) != plan_record.plan_fingerprint:
            issues.append(
                _issue(
                    "snapshot.plan_fingerprint_mismatch",
                    "Build Plan fingerprint does not match canonical Plan content.",
                    plan_record.record_type,
                    plan_record.snapshot_build_plan_id,
                )
            )
        for review_id in plan_record.required_review_references:
            if review_id not in reviews:
                issues.append(
                    _issue(
                        "snapshot.plan_review_missing",
                        "Build Plan references a missing Curation Review Decision.",
                        plan_record.record_type,
                        plan_record.snapshot_build_plan_id,
                    )
                )
        plan_inventory = inventories.get((plan_record.portfolio_id, plan_record.composition_revision))
        if plan_inventory is not None and not set(
            plan_record.acknowledged_obligation_codes
        ).issubset(plan_inventory.unresolved_obligation_codes):
            issues.append(
                _issue(
                    "snapshot.plan_obligation_mismatch",
                    "Build Plan acknowledges an obligation not frozen by the Composition Inventory.",
                    plan_record.record_type,
                    plan_record.snapshot_build_plan_id,
                )
            )
        path_keys: dict[str, str] = {}
        for entry in plan_record.entry_plans:
            if entry.target_relative_path is not None:
                path_key = _portable_path_key(entry.target_relative_path)
                prior_entry_plan_id = path_keys.get(path_key)
                if prior_entry_plan_id is not None:
                    issues.append(
                        _issue(
                            "snapshot.plan_path_collision",
                            "Build Plan contains colliding portable Entry paths.",
                            plan_record.record_type,
                            plan_record.snapshot_build_plan_id,
                        )
                    )
                path_keys[path_key] = entry.entry_plan_id
            if entry.materialization_kind in {"copied_source", "reference_only"}:
                candidate = candidates.get(entry.candidate_id or "")
                evaluation = evaluations.get(entry.candidate_evaluation_id or "")
                selection = selections.get(entry.selection_id or "")
                placement = placements.get(entry.placement_id or "") if entry.placement_id else None
                if candidate is None or evaluation is None or selection is None:
                    issues.append(
                        _issue(
                            "snapshot.plan_source_reference_missing",
                            "Source Entry Plan references missing Candidate/Evaluation/Selection state.",
                            plan_record.record_type,
                            plan_record.snapshot_build_plan_id,
                        )
                    )
                    continue
                endpoint = candidate.source_endpoint
                if (
                    candidate.candidate_evaluation_id != entry.candidate_evaluation_id
                    or selection.candidate_id != entry.candidate_id
                    or selection.candidate_evaluation_id != entry.candidate_evaluation_id
                    or endpoint.core_publication.publication_id != entry.source_publication_id
                    or endpoint.producer_source.producer_module_id != entry.producer_module_id
                    or endpoint.producer_source.projection_contract_version
                    != entry.projection_contract_version
                    or endpoint.source_artifact != entry.source_artifact
                    or (
                        endpoint.source_artifact is not None
                        and endpoint.source_artifact.representation_kind
                        != entry.projection_kind
                    )
                ):
                    issues.append(
                        _issue(
                            "snapshot.plan_source_reference_mismatch",
                            "Source Entry Plan does not freeze the exact selected Candidate endpoint.",
                            plan_record.record_type,
                            plan_record.snapshot_build_plan_id,
                        )
                    )
                if placement is not None and placement.selection_id != selection.selection_id:
                    issues.append(
                        _issue(
                            "snapshot.plan_placement_mismatch",
                            "Source Entry Plan Placement does not belong to its Selection.",
                            plan_record.record_type,
                            plan_record.snapshot_build_plan_id,
                        )
                    )
            elif entry.materialization_kind == "generated_vitrine":
                for reference in entry.input_references:
                    if not _input_reference_exists(state, reference):
                        issues.append(
                            _issue(
                                "snapshot.plan_generated_input_missing",
                                "Generated Entry Plan input reference does not resolve.",
                                plan_record.record_type,
                                plan_record.snapshot_build_plan_id,
                            )
                        )
        if plan_record.predecessor_plan_id is not None:
            plan_predecessor = plans.get(plan_record.predecessor_plan_id)
            if plan_predecessor is None:
                issues.append(
                    _issue(
                        "snapshot.plan_predecessor_missing",
                        "Build Plan predecessor does not exist.",
                        plan_record.record_type,
                        plan_record.snapshot_build_plan_id,
                    )
                )
            elif (
                plan_predecessor.snapshot_build_request_id != plan_record.snapshot_build_request_id
                or plan_predecessor.snapshot_series_id != plan_record.snapshot_series_id
                or plan_predecessor.plan_revision >= plan_record.plan_revision
            ):
                issues.append(
                    _issue(
                        "snapshot.plan_predecessor_mismatch",
                        "Build Plan predecessor belongs to another Request or revision order.",
                        plan_record.record_type,
                        plan_record.snapshot_build_plan_id,
                    )
                )
            plan_successors[plan_record.predecessor_plan_id].append(plan_record.snapshot_build_plan_id)
    for plan_predecessor_id, plan_successor_ids in sorted(plan_successors.items()):
        if len(plan_successor_ids) > 1:
            issues.append(
                _issue(
                    "snapshot.plan_branch",
                    "Build Plan predecessor has multiple successors.",
                    "snapshot_build_plan",
                    plan_predecessor_id,
                )
            )
    plan_predecessors = {
        plan_record.snapshot_build_plan_id: plan_record.predecessor_plan_id for plan_record in state.plans
    }
    for cycle in _cycle_representatives(plan_predecessors):
        issues.append(
            _issue(
                "snapshot.plan_cycle",
                "Build Plan predecessor history contains a cycle.",
                "snapshot_build_plan",
                cycle,
            )
        )

    # Attempts, attempt numbers, and one exact terminal Result.
    attempt_numbers: dict[tuple[str, int], str] = {}
    results_by_attempt: dict[str, list[SnapshotBuildAttemptResult]] = defaultdict(list)
    for attempt_record in state.attempts:
        if attempt_record.snapshot_build_plan_id not in plans:
            issues.append(
                _issue(
                    "snapshot.attempt_plan_missing",
                    "Build Attempt references a missing Plan.",
                    attempt_record.record_type,
                    attempt_record.snapshot_build_attempt_id,
                )
            )
        attempt_number_key = (attempt_record.snapshot_build_plan_id, attempt_record.attempt_number)
        prior_attempt_id = attempt_numbers.get(attempt_number_key)
        if prior_attempt_id is not None:
            issues.append(
                _issue(
                    "snapshot.attempt_number_duplicate",
                    "Build Attempt number is duplicated within a Plan.",
                    attempt_record.record_type,
                    attempt_record.snapshot_build_attempt_id,
                )
            )
        attempt_numbers[attempt_number_key] = attempt_record.snapshot_build_attempt_id
    for attempt_result in state.attempt_results:
        results_by_attempt[attempt_result.snapshot_build_attempt_id].append(attempt_result)
        attempt = attempts.get(attempt_result.snapshot_build_attempt_id)
        plan = plans.get(attempt.snapshot_build_plan_id) if attempt is not None else None
        if attempt is None or plan is None:
            issues.append(
                _issue(
                    "snapshot.result_attempt_missing",
                    "Build Attempt Result references a missing Attempt or Plan.",
                    attempt_result.record_type,
                    attempt_result.snapshot_build_attempt_result_id,
                )
            )
            continue
        expected_entry_ids = tuple(entry.entry_plan_id for entry in plan.entry_plans)
        actual_entry_ids = tuple(outcome.entry_plan_id for outcome in attempt_result.entry_outcomes)
        if set(actual_entry_ids) != set(expected_entry_ids):
            issues.append(
                _issue(
                    "snapshot.result_entry_inventory_incomplete",
                    "Terminal Build Attempt Result must disposition every planned Entry exactly once.",
                    attempt_result.record_type,
                    attempt_result.snapshot_build_attempt_result_id,
                )
            )
        if attempt_result.terminal_outcome in {"sealed", "partial_success_after_seal"}:
            if any(
                outcome.disposition == "failed_blocking"
                for outcome in attempt_result.entry_outcomes
            ) or any(finding.blocking for finding in attempt_result.findings):
                issues.append(
                    _issue(
                        "snapshot.result_blocking_failure_sealed",
                        "Sealed Attempt Result must not retain a blocking Entry or build finding.",
                        attempt_result.record_type,
                        attempt_result.snapshot_build_attempt_result_id,
                    )
                )
        if attempt_result.sealed_snapshot_edition is not None:
            edition = editions.get(
                (
                    attempt_result.sealed_snapshot_edition.snapshot_series_id,
                    attempt_result.sealed_snapshot_edition.edition_number,
                )
            )
            if edition is None or edition.snapshot_series_id != plan.snapshot_series_id:
                issues.append(
                    _issue(
                        "snapshot.result_edition_missing",
                        "Sealed Attempt Result references a missing or mismatched Edition.",
                        attempt_result.record_type,
                        attempt_result.snapshot_build_attempt_result_id,
                    )
                )
        for outcome in attempt_result.entry_outcomes:
            if outcome.materialization_id is not None and outcome.materialization_id not in materializations:
                issues.append(
                    _issue(
                        "snapshot.result_materialization_missing",
                        "Included Entry outcome references a missing Materialization.",
                        attempt_result.record_type,
                        attempt_result.snapshot_build_attempt_result_id,
                    )
                )
            if outcome.omission_id is not None and outcome.omission_id not in omissions:
                issues.append(
                    _issue(
                        "snapshot.result_omission_missing",
                        "Omitted Entry outcome references a missing Omission.",
                        attempt_result.record_type,
                        attempt_result.snapshot_build_attempt_result_id,
                    )
                )
    for attempt_id, attempt_results in sorted(results_by_attempt.items()):
        if len(attempt_results) > 1:
            issues.append(
                _issue(
                    "snapshot.attempt_terminal_conflict",
                    "Build Attempt has more than one terminal Result.",
                    "snapshot_build_attempt",
                    attempt_id,
                )
            )

    # Materialization provenance must explain the frozen #28 record honestly.
    provenance_by_materialization: dict[str, list[SnapshotMaterializationProvenance]] = defaultdict(list)
    for materialization_provenance_record in state.materialization_provenance:
        provenance_by_materialization[materialization_provenance_record.materialization_id].append(materialization_provenance_record)
        materialization = materializations.get(materialization_provenance_record.materialization_id)
        if materialization is None or materialization.snapshot_edition != materialization_provenance_record.snapshot_edition:
            issues.append(
                _issue(
                    "snapshot.materialization_provenance_mismatch",
                    "Materialization provenance does not match a frozen Materialization record.",
                    materialization_provenance_record.record_type,
                    materialization_provenance_record.snapshot_materialization_provenance_id,
                )
            )
            continue
        if materialization.materialization_kind == "copied_source":
            if materialization_provenance_record.source_provider_id is None or materialization_provenance_record.source_provider_version is None:
                issues.append(
                    _issue(
                        "snapshot.materialization_provider_missing",
                        "Copied-source materialization provenance requires an exact source provider.",
                        materialization_provenance_record.record_type,
                        materialization_provenance_record.snapshot_materialization_provenance_id,
                    )
                )
            if materialization_provenance_record.renderer_id is not None or materialization_provenance_record.input_references:
                issues.append(
                    _issue(
                        "snapshot.materialization_provider_renderer_conflict",
                        "Copied-source materialization provenance must not claim renderer inputs.",
                        materialization_provenance_record.record_type,
                        materialization_provenance_record.snapshot_materialization_provenance_id,
                    )
                )
            if materialization_provenance_record.source_stability_result != "verified":
                issues.append(
                    _issue(
                        "snapshot.materialization_stability_unverified",
                        "Copied-source materialization must preserve verified source stability.",
                        materialization_provenance_record.record_type,
                        materialization_provenance_record.snapshot_materialization_provenance_id,
                    )
                )
        elif materialization.materialization_kind == "generated_vitrine":
            if (
                materialization_provenance_record.renderer_id is None
                or materialization_provenance_record.renderer_version is None
                or materialization_provenance_record.renderer_contract_version is None
                or not materialization_provenance_record.input_references
            ):
                issues.append(
                    _issue(
                        "snapshot.materialization_renderer_missing",
                        "Generated materialization provenance requires renderer identity and exact inputs.",
                        materialization_provenance_record.record_type,
                        materialization_provenance_record.snapshot_materialization_provenance_id,
                    )
                )
            if materialization_provenance_record.source_provider_id is not None or materialization_provenance_record.producer_source_digest_claim is not None:
                issues.append(
                    _issue(
                        "snapshot.materialization_generated_source_claim",
                        "Generated materialization provenance must not fabricate producer source claims.",
                        materialization_provenance_record.record_type,
                        materialization_provenance_record.snapshot_materialization_provenance_id,
                    )
                )
    for materialization_id, materialization_provenance_records in sorted(provenance_by_materialization.items()):
        if len(materialization_provenance_records) > 1:
            issues.append(
                _issue(
                    "snapshot.materialization_provenance_duplicate",
                    "Materialization has more than one provenance record.",
                    "snapshot_materialization",
                    materialization_id,
                )
            )

    # Edition build provenance binds the frozen Edition back to Request/Plan/Attempt/Result.
    edition_provenance_seen: dict[tuple[str, int], str] = {}
    for edition_provenance_record in state.edition_build_provenance:
        edition_key = (
            edition_provenance_record.snapshot_edition.snapshot_series_id,
            edition_provenance_record.snapshot_edition.edition_number,
        )
        provenance_edition = editions.get(edition_key)
        provenance_request = requests.get(edition_provenance_record.snapshot_build_request_id)
        provenance_plan = plans.get(edition_provenance_record.snapshot_build_plan_id)
        provenance_attempt = attempts.get(edition_provenance_record.snapshot_build_attempt_id)
        provenance_result = results.get(edition_provenance_record.snapshot_build_attempt_result_id)
        if (
            provenance_edition is None
            or provenance_request is None
            or provenance_plan is None
            or provenance_attempt is None
            or provenance_result is None
        ):
            issues.append(
                _issue(
                    "snapshot.edition_build_provenance_missing",
                    "Edition build provenance references missing workflow state.",
                    edition_provenance_record.record_type,
                    edition_provenance_record.snapshot_edition_build_provenance_id,
                )
            )
            continue
        if (
            provenance_plan.snapshot_build_request_id != provenance_request.snapshot_build_request_id
            or provenance_attempt.snapshot_build_plan_id != provenance_plan.snapshot_build_plan_id
            or provenance_result.snapshot_build_attempt_id != provenance_attempt.snapshot_build_attempt_id
            or provenance_result.sealed_snapshot_edition != edition_provenance_record.snapshot_edition
            or (
                provenance_edition.portfolio_id,
                provenance_edition.profile_binding_id,
                provenance_edition.profile_revision,
                provenance_edition.composition_revision,
                provenance_edition.audience_context_id,
            )
            != (
                edition_provenance_record.portfolio_id,
                edition_provenance_record.profile_binding_id,
                edition_provenance_record.profile_revision,
                edition_provenance_record.composition_revision,
                edition_provenance_record.audience_context_id,
            )
        ):
            issues.append(
                _issue(
                    "snapshot.edition_build_provenance_mismatch",
                    "Edition build provenance does not reproduce the exact successful workflow chain.",
                    edition_provenance_record.record_type,
                    edition_provenance_record.snapshot_edition_build_provenance_id,
                )
            )
        prior_provenance_id = edition_provenance_seen.get(edition_key)
        if prior_provenance_id is not None:
            issues.append(
                _issue(
                    "snapshot.edition_build_provenance_duplicate",
                    "Snapshot Edition has more than one build provenance record.",
                    edition_provenance_record.record_type,
                    edition_provenance_record.snapshot_edition_build_provenance_id,
                )
            )
        edition_provenance_seen[edition_key] = edition_provenance_record.snapshot_edition_build_provenance_id

    # Export artifacts bind exact Entry inventory from one Edition.
    for export_record in state.export_artifacts:
        export_edition_key = (
            export_record.snapshot_edition.snapshot_series_id,
            export_record.snapshot_edition.edition_number,
        )
        if export_edition_key not in editions:
            issues.append(
                _issue(
                    "snapshot.export_edition_missing",
                    "Snapshot Export Artifact references a missing Edition.",
                    export_record.record_type,
                    export_record.snapshot_export_artifact_id,
                )
            )
        edition_entry_ids = {
            entry.snapshot_entry_id
            for entry in state.entries
            if (
                entry.snapshot_edition.snapshot_series_id,
                entry.snapshot_edition.edition_number,
            )
            == export_edition_key
        }
        if set(export_record.included_entry_ids) | set(export_record.excluded_entry_ids) != edition_entry_ids:
            issues.append(
                _issue(
                    "snapshot.export_inventory_mismatch",
                    "Export Artifact must explicitly partition the Edition Entry inventory.",
                    export_record.record_type,
                    export_record.snapshot_export_artifact_id,
                )
            )
        if export_record.predecessor_export_artifact_id is not None:
            export_predecessor = exports.get(export_record.predecessor_export_artifact_id)
            if (
                export_predecessor is None
                or export_predecessor.snapshot_edition != export_record.snapshot_edition
            ):
                issues.append(
                    _issue(
                        "snapshot.export_predecessor_mismatch",
                        "Export Artifact predecessor is missing or belongs to another Edition.",
                        export_record.record_type,
                        export_record.snapshot_export_artifact_id,
                    )
                )

    # Current pointer revisions are explicit, conflict-aware, and must resolve to Editions.
    pointer_groups: dict[str, list[SnapshotCurrentPointerRevision]] = defaultdict(list)
    for pointer_record in state.current_pointers:
        pointer_groups[pointer_record.snapshot_series_id].append(pointer_record)
        if pointer_record.snapshot_series_id not in series_by_id:
            issues.append(
                _issue(
                    "snapshot.pointer_series_missing",
                    "Snapshot Current Pointer references a missing Series.",
                    pointer_record.record_type,
                    f"{pointer_record.snapshot_current_pointer_id}:{pointer_record.pointer_revision}",
                )
            )
        if (pointer_record.snapshot_series_id, pointer_record.edition_number) not in editions:
            issues.append(
                _issue(
                    "snapshot.pointer_edition_missing",
                    "Snapshot Current Pointer references a missing Edition.",
                    pointer_record.record_type,
                    f"{pointer_record.snapshot_current_pointer_id}:{pointer_record.pointer_revision}",
                )
            )
    for pointer_series_id, pointer_records in sorted(pointer_groups.items()):
        by_key = {
            (pointer_record.snapshot_current_pointer_id, pointer_record.pointer_revision): pointer_record for pointer_record in pointer_records
        }
        pointer_successors: dict[tuple[str, int], list[tuple[str, int]]] = defaultdict(list)
        pointer_predecessor_map: dict[str, str | None] = {}
        for pointer_record in pointer_records:
            current_key = (pointer_record.snapshot_current_pointer_id, pointer_record.pointer_revision)
            if pointer_record.predecessor_pointer_revision is not None:
                predecessor_key = (
                    pointer_record.snapshot_current_pointer_id,
                    pointer_record.predecessor_pointer_revision,
                )
                pointer_predecessor = by_key.get(predecessor_key)
                if pointer_predecessor is None:
                    issues.append(
                        _issue(
                            "snapshot.pointer_predecessor_missing",
                            "Snapshot Current Pointer predecessor revision does not exist.",
                            pointer_record.record_type,
                            f"{pointer_record.snapshot_current_pointer_id}:{pointer_record.pointer_revision}",
                        )
                    )
                pointer_successors[predecessor_key].append(current_key)
            pointer_predecessor_map[f"{current_key[0]}:{current_key[1]}"] = (
                None
                if pointer_record.predecessor_pointer_revision is None
                else f"{pointer_record.snapshot_current_pointer_id}:{pointer_record.predecessor_pointer_revision}"
            )
        for pointer_predecessor_key, pointer_successor_keys in sorted(pointer_successors.items()):
            if len(pointer_successor_keys) > 1:
                issues.append(
                    _issue(
                        "snapshot.pointer_branch",
                        "Snapshot Current Pointer revision has multiple successors.",
                        "snapshot_current_pointer_revision",
                        f"{pointer_predecessor_key[0]}:{pointer_predecessor_key[1]}",
                    )
                )
        for pointer_cycle in _cycle_representatives(pointer_predecessor_map):
            issues.append(
                _issue(
                    "snapshot.pointer_cycle",
                    "Snapshot Current Pointer history contains a cycle.",
                    "snapshot_current_pointer_revision",
                    pointer_cycle,
                )
            )
        if len(state.pointer_heads(pointer_series_id)) > 1:
            issues.append(
                _issue(
                    "snapshot.pointer_head_conflict",
                    "Snapshot Series has multiple Current Pointer heads.",
                    "snapshot_current_pointer_revision",
                    pointer_series_id,
                )
            )

    return tuple(issues)


def validate_snapshot_state(state: SnapshotState) -> None:
    issues = collect_snapshot_state_issues(state)
    if issues:
        raise VitrineRecordGraphError(issues)


__all__ = [
    "SnapshotState",
    "collect_snapshot_state_issues",
    "project_snapshot_state",
    "snapshot_plan_fingerprint",
    "validate_snapshot_state",
]
