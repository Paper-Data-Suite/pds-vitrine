from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import portfolio_menu
from vitrine.models import ActorAttribution
from vitrine.workflow_context import default_workflow_dependencies

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_test",
    owning_system="local",
    role_snapshot="teacher",
)


def _inputs(values: list[str]) -> object:
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_teacher_creation_selects_subject_and_preserves_observed_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    subject = SimpleNamespace(
        portfolio_subject_id="subject_exact",
        display_name="Synthetic learner",
        status="current",
    )
    monkeypatch.setattr(portfolio_menu, "list_subjects", lambda _root: (subject,))
    monkeypatch.setattr(
        portfolio_menu,
        "observe_portfolio_state_revision",
        lambda _root: events.append("observed") or 7,
    )

    def create(_root: Path, **kwargs: object) -> object:
        events.append(kwargs)
        return SimpleNamespace(portfolio=SimpleNamespace(portfolio_id="portfolio_new"))

    monkeypatch.setattr(portfolio_menu, "create_portfolio", create)
    raw_input = _inputs(["1", "1", "Title", "Description", "CREATE", "", "B"])

    portfolio_menu.run_portfolio_menu(
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert events[0] == "observed"
    request = events[1]
    assert isinstance(request, dict)
    assert request["portfolio_subject_id"] == "subject_exact"
    assert request["expected_state_revision"] == 7
    assert request["title_snapshot"] == "Title"
    assert request["description_snapshot"] == "Description"


def test_candidate_number_maps_to_exact_candidate_before_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = SimpleNamespace(
        title_snapshot="Portfolio",
        subject_display_label="Synthetic learner",
        portfolio_subject_id="subject_exact",
    )
    monkeypatch.setattr(
        portfolio_menu, "show_portfolio", lambda _root, _id: SimpleNamespace(summary=summary)
    )
    candidates = tuple(
        SimpleNamespace(
            candidate_id=f"candidate_{index}",
            display_snapshot=f"Candidate {index}",
            condition_state="ready_for_consideration",
            eligible_section_ids=(f"section_{index}",),
        )
        for index in (1, 2)
    )
    monkeypatch.setattr(portfolio_menu, "list_candidate_summaries", lambda *_: candidates)
    endpoint = SimpleNamespace(
        core_publication=SimpleNamespace(publication_id="publication_exact"),
        producer_source=SimpleNamespace(
            producer_module_id="fixture_module", source_record_id="source_exact"
        ),
    )
    monkeypatch.setattr(
        portfolio_menu,
        "show_candidate_detail",
        lambda _root, candidate_id: SimpleNamespace(
            candidate_evaluation_id=f"evaluation_{candidate_id}",
            source_endpoint=endpoint,
            unresolved_condition_codes=(),
        ),
    )
    monkeypatch.setattr(portfolio_menu, "observe_portfolio_state_revision", lambda _root: 12)
    selected: list[str] = []

    def select(_root: Path, **kwargs: object) -> object:
        selected.append(str(kwargs["candidate_id"]))
        return SimpleNamespace(state_revision=13)

    monkeypatch.setattr(portfolio_menu, "select_candidate_directly", select)
    raw_input = _inputs(["3", "", "2", "SELECT", "section_2", "", "B"])

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert selected == ["candidate_2"]
