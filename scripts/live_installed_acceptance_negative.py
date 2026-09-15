"""Installed negative/currentness matrix for Vitrine issue #71 Slice 4A.

Each destructive case runs against a private copy of the accepted synthetic
workspace.  The helper mutates only released-producer state or the exact producer
source bytes whose loss/drift is under test; it never edits canonical Vitrine or
Core records directly.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pds_core.academic_catalog import PublicationCatalogQuery, rebuild_academic_catalog
from pds_core.publication_compatibility import build_publication_producer_registry
from pds_core.routing_models import ModuleWorkRef
from pds_core.standards import load_workspace_standards_library

from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
    discover_and_evaluate_candidates,
)
from vitrine.concord_artifact_context import (
    build_canonical_concord_artifact_source_context_resolver,
)
from vitrine.concord_artifact_source import (
    ConcordArtifactAuthorizationDecision,
    ConcordArtifactAuthorizationRequest,
    build_concord_artifact_source_provider,
)
from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.current_portfolio_execution import (
    CurrentPortfolioExecutionError,
    CurrentPortfolioPlanExecutionResult,
    execute_current_portfolio_build_export,
    execute_prepared_current_portfolio_plan,
)
from vitrine.models import (
    ActorAttribution,
    PortfolioCandidate,
    SnapshotBuildPlan,
    SnapshotEdition,
)
from vitrine.producer_adapters import build_adapter_registry
from vitrine.quillan_artifact_context import (
    build_canonical_quillan_artifact_source_context_resolver,
)
from vitrine.quillan_artifact_source import (
    QuillanArtifactAuthorizationDecision,
    QuillanArtifactAuthorizationRequest,
    build_quillan_artifact_source_providers,
)
from vitrine.snapshot_materialization import SnapshotSourceProviderRegistry
from vitrine.storage import load_current_records, load_current_state

if TYPE_CHECKING:
    from scripts.live_installed_acceptance_portfolio import (
        ExactConcordArtifactGate,
        ExactQuillanArtifactGate,
        ExactSnapshotBuildGate,
        ExactSnapshotSourceReadGate,
    )
    from scripts.live_installed_acceptance_support import (
        CONCORD_ARTIFACT_PAGE_ID,
        CONCORD_CLASS_ID,
        CONCORD_WORK_ID,
        MAIN_STUDENT_ID,
        NOW,
        PURPOSE,
        QUILLAN_CLASS_ID,
        QUILLAN_WORK_ID,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        DeterministicIds,
        LivePortfolioContext,
        ProducerPublication,
    )
else:
    from live_installed_acceptance_portfolio import (
        ExactConcordArtifactGate,
        ExactQuillanArtifactGate,
        ExactSnapshotBuildGate,
        ExactSnapshotSourceReadGate,
    )
    from live_installed_acceptance_support import (
        CONCORD_ARTIFACT_PAGE_ID,
        CONCORD_CLASS_ID,
        CONCORD_WORK_ID,
        MAIN_STUDENT_ID,
        NOW,
        PURPOSE,
        QUILLAN_CLASS_ID,
        QUILLAN_WORK_ID,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        DeterministicIds,
        LivePortfolioContext,
        ProducerPublication,
    )


@dataclass(frozen=True, slots=True)
class NegativeMatrixResult:
    scoreform_old_publication_preserved: bool
    scoreform_stale_reason: str
    quillan_failure_code: str
    quillan_underlying_code: str | None
    concord_failure_code: str
    concord_underlying_code: str | None
    source_authorization_findings: tuple[str, ...]
    artifact_authorization_failure_code: str


def _teacher_actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="issue71_teacher",
        owning_system="local",
        role_snapshot="teacher",
        display_label_snapshot="Synthetic Issue 71 Teacher",
    )


def _clone(source: Path, destination: Path) -> Path:
    if destination.exists():
        raise RuntimeError("negative-matrix clone destination must begin absent")
    shutil.copytree(source, destination)
    return destination


def _publication(
    publications: tuple[ProducerPublication, ...], module_id: str
) -> ProducerPublication:
    matches = tuple(item for item in publications if item.module_id == module_id)
    if len(matches) != 1:
        raise RuntimeError("negative matrix did not resolve one exact producer publication")
    return matches[0]


class _SourceDecisionGate:
    def __init__(self, *, publication_id: str, outcome: str) -> None:
        self.publication_id = publication_id
        self.outcome = outcome
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        exact = (
            request.publication_id == self.publication_id
            and request.operation == "candidate_source_read"
            and request.purpose == PURPOSE
        )
        if not exact:
            return SourceReadAuthorizationDecision(outcome="denied")
        return SourceReadAuthorizationDecision(
            outcome=self.outcome,
            reason_codes=(f"issue_71:source_{self.outcome}",),
        )


def _source_authorization_case(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publication: ProducerPublication,
    outcome: str,
) -> str:
    before = tuple(
        item for item in load_current_records(workspace) if isinstance(item, PortfolioCandidate)
    )
    if before:
        raise RuntimeError("source-authorization case must begin before Candidate persistence")
    rebuild_academic_catalog(workspace)
    gate = _SourceDecisionGate(publication_id=publication.publication_id, outcome=outcome)
    result = discover_and_evaluate_candidates(
        workspace,
        CandidateDiscoveryRequest(
            portfolio_id=portfolio.portfolio_id,
            requesting_actor=_teacher_actor(),
            requested_purpose=PURPOSE,
            catalog_query=PublicationCatalogQuery(
                class_id=publication.class_id,
                module_id=publication.module_id,
                work_id=publication.work_id,
                required_capabilities=("multiple_attempts", "points", "question_evidence"),
                state="current",
                limit=10,
            ),
            expected_state_revision=load_current_state(workspace).state_revision,
        ),
        producer_registry=build_publication_producer_registry(),
        adapter_registry=build_adapter_registry(),
        authorization_gate=gate,
        clock=lambda: NOW,
        id_factory=DeterministicIds(),
    )
    expected_code = f"candidate.authorization_{outcome}"
    if result.proposed_publication_ids != (publication.publication_id,):
        raise RuntimeError("source-authorization case proposed a different publication")
    if tuple(item.code for item in result.findings) != (expected_code,):
        raise RuntimeError("source-authorization case returned the wrong bounded finding")
    if result.evaluation_results or result.committed_state_revision is not None:
        raise RuntimeError("source-authorization failure persisted Candidate state")
    after = tuple(
        item for item in load_current_records(workspace) if isinstance(item, PortfolioCandidate)
    )
    if after:
        raise RuntimeError("source-authorization failure created a Candidate")
    if len(gate.requests) != 1:
        raise RuntimeError("source-authorization gate was not consulted exactly once")
    return expected_code


def _append_scoreform_successor(
    workspace: Path,
    *,
    old_publication_id: str,
) -> str:
    from scoreform.academic_result_manifest_generation import (
        generate_academic_result_manifest,
    )
    from scoreform.academic_result_publication import (
        supersede_scoreform_academic_results,
    )
    from scoreform.page_scoring import ScoredAnswer
    from scoreform.results import ScoreFormRoutedResult, export_scoreform_result_models

    answers = (
        ScoredAnswer(1, "A", True),
        ScoredAnswer(2, "B", True),
        ScoredAnswer(3, "C", True),
    )
    appended = export_scoreform_result_models(
        (
            ScoreFormRoutedResult(
                result_origin="plain_paper_manual",
                class_id=SCOREFORM_CLASS_ID,
                assignment_id=SCOREFORM_WORK_ID,
                student_id=MAIN_STUDENT_ID,
                last_name="Learner",
                first_name="Synthetic",
                period="acceptance",
                page_display="manual",
                score=3,
                total_points=3,
                answers=answers,
                source_file="plain_paper_manual_entry",
            ),
        ),
        workspace_root=workspace,
    )
    if not appended.succeeded or len(appended.appended_attempts) != 1:
        raise RuntimeError("ScoreForm successor attempt was not appended exactly once")
    generated = generate_academic_result_manifest(
        workspace,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
    )
    if generated.revision != 2:
        raise RuntimeError("ScoreForm successor did not allocate producer revision 2")
    result = supersede_scoreform_academic_results(
        workspace,
        SCOREFORM_CLASS_ID,
        SCOREFORM_WORK_ID,
        manifest_revision=generated.revision,
        expected_current_publication_id=old_publication_id,
    )
    successor_id = result.publication.publication_id
    if not isinstance(successor_id, str):
        raise RuntimeError("ScoreForm successor publication ID has the wrong type")
    if (
        successor_id == old_publication_id
        or result.publication.supersedes_publication_id != old_publication_id
    ):
        raise RuntimeError("ScoreForm did not create the exact successor publication")
    return successor_id


def _scoreform_currentness_case(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publication: ProducerPublication,
) -> tuple[bool, str]:
    successor_id = _append_scoreform_successor(
        workspace,
        old_publication_id=publication.publication_id,
    )
    inbox = list_candidate_inbox(
        workspace,
        CandidateInboxQuery(
            portfolio_id=portfolio.portfolio_id,
            producer_module_id="scoreform",
            stale_only=True,
            selected_state="selected",
            limit=20,
        ),
    )
    if inbox.matched_count != 1 or len(inbox.items) != 1:
        raise RuntimeError("ScoreForm selected baseline did not become exactly one stale item")
    item = inbox.items[0]
    reason = "candidate_inbox.publication_superseded"
    if item.stale_state != "stale" or reason not in item.stale_reason_codes:
        raise RuntimeError("ScoreForm stale Candidate did not report publication supersession")
    detail = get_candidate_inbox_detail(workspace, item.entry_id)
    if detail.evaluation is None or detail.evaluation.source_endpoint is None:
        raise RuntimeError("ScoreForm stale Candidate lost its exact persisted evaluation")
    preserved_id = detail.evaluation.source_endpoint.core_publication.publication_id
    preserved = preserved_id == publication.publication_id and preserved_id != successor_id
    if not preserved:
        raise RuntimeError("ScoreForm stale evaluation was retargeted to its successor")
    return preserved, reason


def _build_providers(
    workspace: Path,
    *,
    publications: tuple[ProducerPublication, ...],
    quillan_gate: object,
    concord_gate: object,
) -> SnapshotSourceProviderRegistry:
    source_gate = ExactSnapshotSourceReadGate(
        {item.publication_id for item in publications}
    )
    quillan_resolver = build_canonical_quillan_artifact_source_context_resolver(
        workspace,
        source_read_authorization_gate=source_gate,
    )
    concord_resolver = build_canonical_concord_artifact_source_context_resolver(
        workspace,
        source_read_authorization_gate=source_gate,
    )
    return SnapshotSourceProviderRegistry(
        (
            *build_quillan_artifact_source_providers(
                context_resolver=quillan_resolver,
                authorization_gate=quillan_gate,  # type: ignore[arg-type]
            ),
            build_concord_artifact_source_provider(
                context_resolver=concord_resolver,
                authorization_gate=concord_gate,  # type: ignore[arg-type]
            ),
        )
    )


def _freeze_plan(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
    quillan_gate: object,
    concord_gate: object,
) -> tuple[
    SnapshotSourceProviderRegistry,
    CurrentPortfolioPlanExecutionResult,
    SnapshotBuildPlan,
]:
    providers = _build_providers(
        workspace,
        publications=publications,
        quillan_gate=quillan_gate,
        concord_gate=concord_gate,
    )
    preview = prepare_current_portfolio_build(
        workspace,
        portfolio.portfolio_id,
        audience_rule_id="student_review",
        source_providers=providers,
    )
    if preview.unresolved_obligation_codes != ("collaborator_review_required",):
        raise RuntimeError("negative plan preview obligation inventory drifted")
    preparation = prepare_current_portfolio_build(
        workspace,
        portfolio.portfolio_id,
        audience_rule_id="student_review",
        acknowledged_obligation_codes=preview.unresolved_obligation_codes,
        source_providers=providers,
    )
    if not preparation.ready_for_plan_execution:
        raise RuntimeError("negative case preparation did not become executable")
    plan_execution = execute_prepared_current_portfolio_plan(
        workspace,
        preparation,
        actor=_teacher_actor(),
        source_providers=providers,
    )
    plans = tuple(
        item
        for item in load_current_records(workspace)
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == plan_execution.snapshot_build_plan_id
    )
    if len(plans) != 1:
        raise RuntimeError("negative case immutable Snapshot Plan did not resolve exactly once")
    return providers, plan_execution, plans[0]


def _require_failed_frozen_plan(
    workspace: Path,
    *,
    providers: SnapshotSourceProviderRegistry,
    plan_execution: CurrentPortfolioPlanExecutionResult,
    frozen_plan: SnapshotBuildPlan,
    portfolio: LivePortfolioContext,
    expected_code: str,
    permitted_underlying_codes: frozenset[str],
) -> CurrentPortfolioExecutionError:
    try:
        execute_current_portfolio_build_export(
            workspace,
            plan_execution,
            actor=_teacher_actor(),
            authority_gate=ExactSnapshotBuildGate(portfolio),
            source_providers=providers,
        )
    except CurrentPortfolioExecutionError as error:
        if error.code != expected_code:
            raise RuntimeError(
                "negative Snapshot execution failed with the wrong stable code"
            ) from error
        if error.underlying_code not in permitted_underlying_codes:
            raise RuntimeError(
                "negative Snapshot execution exposed an unexpected underlying code"
            ) from error
        records = load_current_records(workspace)
        plans = tuple(
            item
            for item in records
            if isinstance(item, SnapshotBuildPlan)
            and item.snapshot_build_plan_id == frozen_plan.snapshot_build_plan_id
        )
        if plans != (frozen_plan,):
            raise RuntimeError("failed Snapshot execution rewrote the immutable Plan")
        editions = tuple(item for item in records if isinstance(item, SnapshotEdition))
        if editions:
            raise RuntimeError("failed Snapshot execution produced a sealed Edition")
        return error
    raise RuntimeError("negative Snapshot execution unexpectedly succeeded")


def _quillan_drift_case(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
) -> CurrentPortfolioExecutionError:
    quillan_gate = ExactQuillanArtifactGate()
    concord_gate = ExactConcordArtifactGate()
    providers, plan_execution, frozen_plan = _freeze_plan(
        workspace,
        portfolio=portfolio,
        publications=publications,
        quillan_gate=quillan_gate,
        concord_gate=concord_gate,
    )
    from quillan.work_paths import quillan_work_ref, review_record_path

    review_path = review_record_path(
        workspace,
        quillan_work_ref(QUILLAN_CLASS_ID, QUILLAN_WORK_ID),
        MAIN_STUDENT_ID,
    )
    original = review_path.read_bytes()
    review_path.write_bytes(original + b"\n")
    return _require_failed_frozen_plan(
        workspace,
        providers=providers,
        plan_execution=plan_execution,
        frozen_plan=frozen_plan,
        portfolio=portfolio,
        expected_code="current_portfolio_build.materialization_failed",
        permitted_underlying_codes=frozenset({"snapshot.source_integrity_failed"}),
    )


def _concord_source_removal_case(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
) -> CurrentPortfolioExecutionError:
    quillan_gate = ExactQuillanArtifactGate()
    concord_gate = ExactConcordArtifactGate()
    providers, plan_execution, frozen_plan = _freeze_plan(
        workspace,
        portfolio=portfolio,
        publications=publications,
        quillan_gate=quillan_gate,
        concord_gate=concord_gate,
    )
    from concord.storage import load_current_record_graph

    work = ModuleWorkRef("concord", CONCORD_CLASS_ID, CONCORD_WORK_ID)
    loaded = load_current_record_graph(
        workspace,
        work,
        standards_library=load_workspace_standards_library(workspace),
    )
    references = tuple(
        item
        for item in loaded.graph.scan_references
        if item.artifact_page_id == CONCORD_ARTIFACT_PAGE_ID
    )
    if len(references) != 1:
        raise RuntimeError("Concord exact retained source did not resolve exactly once")
    retained = workspace.joinpath(*references[0].retained_source_relative_path.split("/"))
    if not retained.is_file():
        raise RuntimeError("Concord exact retained source is already unavailable")
    retained.unlink()
    return _require_failed_frozen_plan(
        workspace,
        providers=providers,
        plan_execution=plan_execution,
        frozen_plan=frozen_plan,
        portfolio=portfolio,
        expected_code="current_portfolio_build.materialization_failed",
        permitted_underlying_codes=frozenset(
            {"snapshot.source_integrity_failed", "snapshot.source_unavailable"}
        ),
    )


class _DeniedQuillanArtifactGate:
    def __init__(self) -> None:
        self.requests: list[QuillanArtifactAuthorizationRequest] = []

    def authorize(
        self, request: QuillanArtifactAuthorizationRequest
    ) -> QuillanArtifactAuthorizationDecision:
        self.requests.append(request)
        return QuillanArtifactAuthorizationDecision(
            outcome="denied",
            reason_codes=("issue_71:artifact_denied",),
        )


class _DeniedConcordArtifactGate:
    def __init__(self) -> None:
        self.requests: list[ConcordArtifactAuthorizationRequest] = []

    def authorize(
        self, request: ConcordArtifactAuthorizationRequest
    ) -> ConcordArtifactAuthorizationDecision:
        self.requests.append(request)
        return ConcordArtifactAuthorizationDecision(
            outcome="denied",
            reason_codes=("issue_71:artifact_denied",),
        )


def _artifact_authorization_case(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
) -> CurrentPortfolioExecutionError:
    quillan_gate = _DeniedQuillanArtifactGate()
    concord_gate = _DeniedConcordArtifactGate()
    providers, plan_execution, frozen_plan = _freeze_plan(
        workspace,
        portfolio=portfolio,
        publications=publications,
        quillan_gate=quillan_gate,
        concord_gate=concord_gate,
    )
    error = _require_failed_frozen_plan(
        workspace,
        providers=providers,
        plan_execution=plan_execution,
        frozen_plan=frozen_plan,
        portfolio=portfolio,
        expected_code="current_portfolio_build.producer_artifact_authorization_denied",
        permitted_underlying_codes=frozenset({"snapshot.source_unavailable"}),
    )
    if not quillan_gate.requests and not concord_gate.requests:
        raise RuntimeError("denied Artifact authorization gate was never consulted")
    return error


def run_negative_matrix(
    *,
    authorization_base_workspace: Path,
    curated_workspace: Path,
    work_root: Path,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
) -> NegativeMatrixResult:
    """Run independent Slice 4A failures against exact installed producer state."""

    scoreform = _publication(publications, "scoreform")

    denied_workspace = _clone(
        authorization_base_workspace,
        work_root / "negative-source-denied",
    )
    unresolved_workspace = _clone(
        authorization_base_workspace,
        work_root / "negative-source-unresolved",
    )
    source_findings = (
        _source_authorization_case(
            denied_workspace,
            portfolio=portfolio,
            publication=scoreform,
            outcome="denied",
        ),
        _source_authorization_case(
            unresolved_workspace,
            portfolio=portfolio,
            publication=scoreform,
            outcome="unresolved",
        ),
    )

    scoreform_workspace = _clone(
        curated_workspace,
        work_root / "negative-scoreform-currentness",
    )
    scoreform_preserved, stale_reason = _scoreform_currentness_case(
        scoreform_workspace,
        portfolio=portfolio,
        publication=scoreform,
    )

    quillan_workspace = _clone(
        curated_workspace,
        work_root / "negative-quillan-drift",
    )
    quillan_error = _quillan_drift_case(
        quillan_workspace,
        portfolio=portfolio,
        publications=publications,
    )

    concord_workspace = _clone(
        curated_workspace,
        work_root / "negative-concord-removal",
    )
    concord_error = _concord_source_removal_case(
        concord_workspace,
        portfolio=portfolio,
        publications=publications,
    )

    artifact_workspace = _clone(
        curated_workspace,
        work_root / "negative-artifact-denied",
    )
    artifact_error = _artifact_authorization_case(
        artifact_workspace,
        portfolio=portfolio,
        publications=publications,
    )

    return NegativeMatrixResult(
        scoreform_old_publication_preserved=scoreform_preserved,
        scoreform_stale_reason=stale_reason,
        quillan_failure_code=quillan_error.code,
        quillan_underlying_code=quillan_error.underlying_code,
        concord_failure_code=concord_error.code,
        concord_underlying_code=concord_error.underlying_code,
        source_authorization_findings=source_findings,
        artifact_authorization_failure_code=artifact_error.code,
    )
