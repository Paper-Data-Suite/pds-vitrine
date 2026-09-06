from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_inbox_menu import run_candidate_inbox_menu
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.menu import run_menu
from vitrine.storage import load_current_state


def scripted_input(values: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


def _discover(setup: object) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="vitrine_scoreform_fixture",
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
    assert result.findings == ()


def test_main_menu_exposes_candidate_inbox_as_option_five(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    output = io.StringIO()
    result = run_menu(
        input_fn=scripted_input(["5", "b", "q"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert result == 0
    assert "5. Candidate Inbox" in output.getvalue()


def test_candidate_inbox_menu_lists_and_inspects_read_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    before = load_current_state(setup.workspace).state_revision
    output = io.StringIO()
    run_candidate_inbox_menu(
        input_fn=scripted_input(["1", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    rendered = output.getvalue()
    assert "2 matching entries" in rendered
    assert "Candidate Inbox Detail" in rendered
    assert "Core Publication:" in rendered
    assert "Producer module: vitrine_scoreform_fixture" in rendered
    assert "Profile Binding:" in rendered
    assert "Evaluator contract:" in rendered
    assert "Current-pointer history: 1:" in rendered
    assert "does not discover, select, place, replace," in rendered
    assert "Type PROPOSE" not in rendered
    assert "Type SELECT" not in rendered
    assert "Type DISCOVER" not in rendered
    assert load_current_state(setup.workspace).state_revision == before


def test_candidate_inbox_menu_attention_filter_is_read_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path, link_student=False)
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    before = load_current_state(setup.workspace).state_revision
    output = io.StringIO()
    run_candidate_inbox_menu(
        input_fn=scripted_input(["f", "3", "b", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    rendered = output.getvalue()
    assert "Attention only (on)" in rendered
    assert "ATTENTION" in rendered
    assert load_current_state(setup.workspace).state_revision == before


def test_candidate_inbox_menu_negative_filter_keeps_evaluation_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    output = io.StringIO()
    run_candidate_inbox_menu(
        input_fn=scripted_input(["f", "2", "ineligible", "b", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    rendered = output.getvalue()
    assert "Outcome=ineligible" in rendered
    assert "2 matching entries" in rendered
    assert "Ineligible" in rendered


def test_candidate_inbox_menu_invalid_filter_is_bounded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    output = io.StringIO()
    run_candidate_inbox_menu(
        input_fn=scripted_input(["f", "2", "suppressed", "b", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    rendered = output.getvalue()
    assert "candidate_inbox.invalid_query:" in rendered
    assert "Traceback" not in rendered
