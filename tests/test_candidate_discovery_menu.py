from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import portfolio_menu
from vitrine.candidate_discovery_presentation import (
    CandidateDiscoveryModuleParticipation,
    CandidateDiscoverySummary,
)
from vitrine.candidate_services import (
    CandidateDiscoveryFinding,
    CandidateDiscoveryResult,
)
from vitrine.models import ActorAttribution
from vitrine.workflow_context import default_workflow_dependencies

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_discovery",
    owning_system="local",
    role_snapshot="teacher",
)


def _inputs(values: list[str]) -> object:
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _overview() -> SimpleNamespace:
    return SimpleNamespace(
        portfolio_id="portfolio_exact",
        portfolio_subject_id="subject_exact",
        title="Improvement Portfolio",
        subject_label="Jordan Rivera",
        profile_binding_id="binding_exact",
        portfolio_profile_id="profile_exact",
        profile_revision=1,
        profile_label="Starter Improvement Portfolio",
        purpose_kind="improvement",
        subject_links=(),
        candidate_count=0,
        active_selection_count=0,
        current_composition_revision=None,
        snapshot_series_count=0,
        current_edition_count=0,
    )


def test_discovery_preflight_is_instructional_and_contextual() -> None:
    output = io.StringIO()

    portfolio_menu._render_discovery_preflight(output, _overview())

    rendered = output.getvalue()
    assert "Discover Portfolio Evidence" in rendered
    assert "Portfolio: Improvement Portfolio" in rendered
    assert "Student: Jordan Rivera" in rendered
    assert "Profile: Starter Improvement Portfolio — revision 1" in rendered
    assert "search current published evidence" in rendered
    assert "evaluate it against the Portfolio's bound Profile" in rendered
    assert "Discovery does not:" in rendered
    assert "select work for the Portfolio" in rendered
    assert "place evidence into a Portfolio section" in rendered
    assert "approve evidence" in rendered
    assert "build a Portfolio Edition" in rendered
    assert "query configured Candidate sources" not in rendered


def test_discovery_summary_uses_teacher_language_and_preserves_boundaries() -> None:
    output = io.StringIO()
    summary = CandidateDiscoverySummary(
        contract_version="vitrine_candidate_discovery_presentation_v1",
        publications_considered=3,
        evidence_items_evaluated=8,
        new_candidates=5,
        already_known_candidates=2,
        ineligible_evidence=1,
        unresolved_evidence=0,
        source_problem_count=1,
        module_participation=(
            CandidateDiscoveryModuleParticipation(
                label="ScoreForm",
                evidence_items=2,
            ),
            CandidateDiscoveryModuleParticipation(
                label="Quillan",
                evidence_items=6,
            ),
        ),
    )

    portfolio_menu._render_discovery_summary(output, summary)

    rendered = output.getvalue()
    assert "Candidate discovery complete." in rendered
    assert "Publications considered: 3" in rendered
    assert "Evidence evaluated: 8" in rendered
    assert "New Candidates: 5" in rendered
    assert "Already known: 2" in rendered
    assert "Not eligible: 1" in rendered
    assert "Needs review / unresolved: 0" in rendered
    assert "Source / discovery problems: 1" in rendered
    assert "ScoreForm: 2 evidence items" in rendered
    assert "Quillan: 6 evidence items" in rendered
    assert "No work was selected or placed in a Portfolio section." in rendered
    assert "Next: Review Candidates" in rendered


def test_discovery_technical_details_are_explicit_not_primary() -> None:
    discovery = CandidateDiscoveryResult(
        proposed_publication_ids=("publication_exact",),
        findings=(
            CandidateDiscoveryFinding(
                code="candidate.reader_failed",
                stage="producer_read",
                proposed_publication_id="publication_exact",
                diagnostic_codes=("reader_digest_mismatch",),
            ),
        ),
        evaluation_results=(),
        committed_state_revision=None,
    )
    output = io.StringIO()

    portfolio_menu._render_discovery_technical_details(output, discovery)

    rendered = output.getvalue()
    assert "Candidate Discovery Technical Details / Provenance" in rendered
    assert "candidate.reader_failed" in rendered
    assert "producer_read" in rendered
    assert "publication_exact" in rendered
    assert "reader_digest_mismatch" in rendered


def test_guided_discovery_runs_after_preflight_and_summarizes_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        portfolio_menu,
        "build_teacher_portfolio_overview",
        lambda *_args: _overview(),
    )
    monkeypatch.setattr(
        portfolio_menu,
        "_require_observed_revision",
        lambda _root: 11,
    )
    result = CandidateDiscoveryResult(
        proposed_publication_ids=("publication_exact",),
        findings=(),
        evaluation_results=(),
        committed_state_revision=None,
    )
    calls: list[object] = []

    def discover(_root: Path, request, **_kwargs):
        calls.append(request)
        return result

    monkeypatch.setattr(
        portfolio_menu,
        "discover_and_evaluate_candidates",
        discover,
    )
    output = io.StringIO()

    portfolio_menu._candidate_discovery_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=_inputs(["DISCOVER", "", "", "", "", "", ""]),  # type: ignore[arg-type]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(calls) == 1
    request = calls[0]
    assert request.portfolio_id == "portfolio_exact"
    assert request.requested_purpose == "teacher_review"
    assert request.expected_state_revision == 11
    rendered = output.getvalue()
    assert rendered.index("Discover Portfolio Evidence") < rendered.index(
        "Candidate discovery complete."
    )
    assert "Publications considered: 1" in rendered
    assert "No work was selected or placed in a Portfolio section." in rendered


def test_guided_discovery_cancel_does_not_call_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        portfolio_menu,
        "build_teacher_portfolio_overview",
        lambda *_args: _overview(),
    )
    calls: list[object] = []
    monkeypatch.setattr(
        portfolio_menu,
        "discover_and_evaluate_candidates",
        lambda *_args, **_kwargs: calls.append((_args, _kwargs)),
    )

    portfolio_menu._candidate_discovery_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=_inputs([""]),  # type: ignore[arg-type]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls == []
