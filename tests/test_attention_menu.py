from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import attention_menu, menu, portfolio_menu
from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
)
from vitrine.models import ActorAttribution
from vitrine.workflow_context import default_workflow_dependencies

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_attention",
    owning_system="local",
    role_snapshot="teacher",
)


def _inputs(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _report(portfolio_id: str | None) -> VitrineAttentionReport:
    return VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=9,
        summaries=(
            VitrineAttentionSummary(
                code="vitrine_selection_unplaced",
                label="Selection needs placement",
                count=1,
                count_unit="selections",
                attention_class="workflow",
                portfolio_id=portfolio_id,
                reason_codes=(),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_review",
                    portfolio_id=portfolio_id,
                ),
            ),
        ),
        notices=(),
    )


def test_attention_menu_renders_bounded_next_action_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        attention_menu,
        "resolve_workspace_root",
        lambda _root: tmp_path,
    )
    monkeypatch.setattr(
        attention_menu,
        "evaluate_vitrine_attention",
        lambda _root, query: _report(query.portfolio_id),
    )
    output = io.StringIO()

    attention_menu.run_attention_menu(
        output=output,
        clear_fn=lambda: None,
        workspace_root=tmp_path,
        portfolio_id="portfolio_exact",
    )

    rendered = output.getvalue()
    assert "Selection needs placement: 1 selections" in rendered
    assert "Next action: Review Candidates / Selections" in rendered
    assert "Action ID: open_candidate_review" in rendered


def test_main_menu_option_six_routes_workspace_attention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed: list[dict[str, object]] = []
    monkeypatch.setattr(
        menu,
        "run_attention_menu",
        lambda **kwargs: routed.append(kwargs),
    )
    output = io.StringIO()

    result = menu.run_menu(
        input_fn=_inputs(["6", "", "Q"]),
        output=output,
        clear_fn=lambda: None,
    )

    assert result == 0
    assert len(routed) == 1
    assert routed[0]["portfolio_id"] is None


def test_portfolio_option_seven_routes_exact_portfolio_attention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = SimpleNamespace(
        portfolio_id="portfolio_exact",
        title_snapshot="Portfolio",
        subject_display_label="Synthetic learner",
        portfolio_subject_id="subject_exact",
        profile_binding_id=None,
        candidate_count=0,
        active_selection_count=0,
        current_composition_revision=None,
        snapshot_series_count=0,
    )
    monkeypatch.setattr(
        portfolio_menu,
        "show_portfolio",
        lambda *_args: SimpleNamespace(summary=summary),
    )
    routed: list[dict[str, object]] = []
    monkeypatch.setattr(
        portfolio_menu,
        "run_attention_menu",
        lambda **kwargs: routed.append(kwargs),
    )
    raw_input = _inputs(["7", "", "B"])

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=raw_input,
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(routed) == 1
    assert routed[0]["workspace_root"] == tmp_path
    assert routed[0]["portfolio_id"] == "portfolio_exact"
