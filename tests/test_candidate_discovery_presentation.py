from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_discovery_presentation import (
    CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION,
    build_candidate_discovery_summary,
)
from vitrine.candidate_services import (
    CandidateDiscoveryFinding,
    CandidateDiscoveryRequest,
    CandidateDiscoveryResult,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)


def _run(setup: object, module_id: str) -> CandidateDiscoveryResult:
    return discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id,
                state="current",
                limit=20,
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )


def test_scoreform_summary_counts_exact_discovery_result(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    result = _run(setup, "vitrine_scoreform_fixture")

    summary = build_candidate_discovery_summary(result)

    assert (
        summary.contract_version
        == CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION
    )
    assert summary.publications_considered == 1
    assert summary.evidence_items_evaluated == 2
    assert summary.new_candidates == 2
    assert summary.already_known_candidates == 0
    assert summary.ineligible_evidence == 0
    assert summary.unresolved_evidence == 0
    assert summary.source_problem_count == 0
    assert tuple(
        (item.label, item.evidence_items)
        for item in summary.module_participation
    ) == (("ScoreForm", 2),)


def test_summary_distinguishes_already_known_without_minting_new_meaning(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    created = _run(setup, "vitrine_scoreform_fixture")
    existing = replace(
        created,
        evaluation_results=tuple(
            replace(item, disposition="existing")
            for item in created.evaluation_results
        ),
        committed_state_revision=None,
    )

    summary = build_candidate_discovery_summary(existing)

    assert summary.new_candidates == 0
    assert summary.already_known_candidates == 2
    assert summary.evidence_items_evaluated == 2


def test_summary_counts_ineligible_evidence_without_candidate(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    result = _run(setup, "vitrine_scoreform_fixture")

    summary = build_candidate_discovery_summary(result)

    assert summary.evidence_items_evaluated == 2
    assert summary.new_candidates == 0
    assert summary.already_known_candidates == 0
    assert summary.ineligible_evidence == 2
    assert summary.unresolved_evidence == 0


def test_summary_counts_findings_as_discovery_problems_without_exposing_codes() -> None:
    result = CandidateDiscoveryResult(
        proposed_publication_ids=(),
        findings=(
            CandidateDiscoveryFinding(
                code="candidate.no_matching_publication",
                stage="catalog",
            ),
        ),
        evaluation_results=(),
        committed_state_revision=None,
    )

    summary = build_candidate_discovery_summary(result)

    assert summary.publications_considered == 0
    assert summary.evidence_items_evaluated == 0
    assert summary.source_problem_count == 1
    assert summary.module_participation == ()
