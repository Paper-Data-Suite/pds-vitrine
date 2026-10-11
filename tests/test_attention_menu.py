from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import attention_menu, menu, portfolio_menu
from vitrine.attention import (
    VITRINE_ATTENTION_V2_CONTRACT_VERSION,
    VitrineAttentionReportV2,
    VitrineAttentionSummaryV2,
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


def _report(portfolio_id: str | None) -> VitrineAttentionReportV2:
    return VitrineAttentionReportV2(
        contract_version=VITRINE_ATTENTION_V2_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=9,
        summaries=(
            VitrineAttentionSummaryV2(
                code="vitrine_selection_unplaced",
                label="Selection needs placement",
                count=1,
                count_unit="selections",
                attention_class="workflow",
                requirement_level="required",
                portfolio_id=portfolio_id,
                reason_codes=("working_composition.selection_unplaced",),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_review",
                    portfolio_id=portfolio_id,
                ),
            ),
            VitrineAttentionSummaryV2(
                code="vitrine_candidate_optional_evidence",
                label="Additional evidence available",
                count=3,
                count_unit="candidates",
                attention_class="workflow",
                requirement_level="opportunity",
                portfolio_id=portfolio_id,
                reason_codes=("candidate_not_required_by_current_portfolio",),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_inbox",
                    portfolio_id=portfolio_id,
                ),
            ),
            VitrineAttentionSummaryV2(
                code="vitrine_portfolio_complete",
                label="Portfolio complete",
                count=1,
                count_unit="portfolios",
                attention_class="status",
                requirement_level="status",
                portfolio_id=portfolio_id,
                reason_codes=(),
                next_action=VitrineNextActionRef(
                    action_id="open_completed_portfolio_editions",
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
        "evaluate_vitrine_attention_v2",
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
    assert "Attention / Next Actions — Current Portfolio" in rendered
    assert "Portfolio status" in rendered
    assert "- Portfolio complete" in rendered
    assert "Needs attention" in rendered
    assert "Selection needs placement: 1 selection" in rendered
    assert "Next step: Review Candidates / Selections" in rendered
    assert "Optional opportunities" in rendered
    assert "Additional evidence available: 3 candidates" in rendered
    assert "Open: Candidate Inbox" in rendered
    assert "Open: Completed Portfolio Editions" in rendered
    assert "Evaluation:" not in rendered
    assert "Observed state revision:" not in rendered
    assert "Code:" not in rendered
    assert "Class:" not in rendered
    assert "Requirement level:" not in rendered
    assert "Reasons:" not in rendered
    assert "Action ID:" not in rendered
    assert "portfolio_exact" not in rendered
    assert "open_candidate_review" not in rendered


@pytest.mark.parametrize(
    ("count_unit", "expected"),
    (
        ("candidates", "1 candidate"),
        ("candidate_entries", "1 candidate entry"),
        ("selection_proposals", "1 selection proposal"),
        ("selections", "1 selection"),
        ("profile_requirements", "1 profile requirement"),
        ("curation_reviews", "1 curation review"),
        ("portfolios", "1 portfolio"),
        ("obligation_codes", "1 obligation"),
        ("snapshot_builds", "1 snapshot build"),
        ("snapshot_findings", "1 snapshot finding"),
        ("snapshot_omissions", "1 snapshot omission"),
        ("snapshot_exports", "1 snapshot export"),
    ),
)
def test_attention_teacher_count_uses_registered_singular_labels(
    count_unit: str,
    expected: str,
) -> None:
    summary = VitrineAttentionSummaryV2(
        code="vitrine_test_count",
        label="Synthetic",
        count=1,
        count_unit=count_unit,
        attention_class="workflow",
        requirement_level="required",
        portfolio_id=None,
        reason_codes=(),
        next_action=None,
    )

    assert attention_menu._teacher_count(summary) == expected


def test_attention_menu_technical_details_preserve_exact_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str | None] = []
    monkeypatch.setattr(
        attention_menu,
        "resolve_workspace_root",
        lambda _root: tmp_path,
    )

    def evaluate(_root: Path, query: object) -> VitrineAttentionReportV2:
        portfolio_id = getattr(query, "portfolio_id")
        calls.append(portfolio_id)
        return _report(portfolio_id)

    monkeypatch.setattr(
        attention_menu,
        "evaluate_vitrine_attention_v2",
        evaluate,
    )
    output = io.StringIO()

    attention_menu.run_attention_menu(
        output=output,
        clear_fn=lambda: None,
        workspace_root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=_inputs(["T", ""]),
    )

    rendered = output.getvalue()
    assert calls == ["portfolio_exact"]
    assert "Technical Details / Provenance" in rendered
    assert "Contract: vitrine_attention_next_actions_v2" in rendered
    assert "Evaluation: evaluated" in rendered
    assert "Observed state revision: 9" in rendered
    assert "Portfolio ID: portfolio_exact" in rendered
    assert "Code: vitrine_selection_unplaced" in rendered
    assert "Class: workflow" in rendered
    assert "Requirement level: required" in rendered
    assert "Requirement level: opportunity" in rendered
    assert "Requirement level: status" in rendered
    assert "Count unit: selections" in rendered
    assert "Reasons: working_composition.selection_unplaced" in rendered
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
        input_fn=_inputs(["6", "Q"]),
        output=output,
        clear_fn=lambda: None,
    )

    assert result == 0
    assert len(routed) == 1
    assert routed[0]["portfolio_id"] is None
    assert routed[0]["input_fn"] is not None
    assert routed[0]["dependencies"] is not None


def test_portfolio_option_nine_routes_exact_portfolio_attention(
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
    raw_input = _inputs(["9", "B"])

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
    assert routed[0]["input_fn"] is raw_input
    assert routed[0]["dependencies"] is not None
    assert routed[0]["actor"] == ACTOR


def test_attention_action_routes_to_owner_workflow_and_recomputes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluations: list[str | None] = []

    monkeypatch.setattr(
        attention_menu,
        "resolve_workspace_root",
        lambda _root: tmp_path,
    )

    def evaluate(_root: Path, query: object) -> VitrineAttentionReportV2:
        portfolio_id = getattr(query, "portfolio_id")
        evaluations.append(portfolio_id)
        return _report(portfolio_id)

    monkeypatch.setattr(
        attention_menu,
        "evaluate_vitrine_attention_v2",
        evaluate,
    )
    routed: list[dict[str, object]] = []
    monkeypatch.setattr(
        attention_menu,
        "run_candidate_review_menu",
        lambda **kwargs: routed.append(kwargs),
    )

    attention_menu.run_attention_menu(
        output=io.StringIO(),
        clear_fn=lambda: None,
        workspace_root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=_inputs(["1", "B"]),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(routed) == 1
    assert routed[0]["portfolio_id"] == "portfolio_exact"
    assert routed[0]["workspace_root"] == tmp_path
    assert routed[0]["actor"] == ACTOR
    assert evaluations == ["portfolio_exact", "portfolio_exact"]


def test_workspace_action_chooses_only_matching_human_readable_portfolio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = (
        SimpleNamespace(
            portfolio_id="portfolio_alpha",
            title_snapshot="Growth Portfolio",
            subject_display_label="Avery",
        ),
        SimpleNamespace(
            portfolio_id="portfolio_beta",
            title_snapshot="Growth Portfolio",
            subject_display_label="Jordan",
        ),
        SimpleNamespace(
            portfolio_id="portfolio_gamma",
            title_snapshot="Other Portfolio",
            subject_display_label="Morgan",
        ),
    )
    monkeypatch.setattr(
        attention_menu,
        "list_portfolios",
        lambda _root: values,
    )

    def evaluate(_root: Path, query: object) -> VitrineAttentionReportV2:
        portfolio_id = getattr(query, "portfolio_id")
        report = _report(portfolio_id)
        if portfolio_id == "portfolio_gamma":
            return VitrineAttentionReportV2(
                contract_version=VITRINE_ATTENTION_V2_CONTRACT_VERSION,
                evaluation="evaluated",
                observed_state_revision=9,
                summaries=tuple(
                    item
                    for item in report.summaries
                    if item.next_action is not None
                    and item.next_action.action_id != "open_candidate_review"
                ),
                notices=(),
            )
        return report

    monkeypatch.setattr(
        attention_menu,
        "evaluate_vitrine_attention_v2",
        evaluate,
    )
    output = io.StringIO()
    selected = attention_menu._select_workspace_portfolio_for_action(
        root=tmp_path,
        action=attention_menu._MenuActionChoice(
            action_id="open_candidate_review",
            portfolio_id=None,
            label="Review Candidates / Selections",
        ),
        input_fn=_inputs(["2"]),
        output=output,
        clear_fn=lambda: None,
    )

    rendered = output.getvalue()
    assert selected == "portfolio_beta"
    assert "Avery — Growth Portfolio" in rendered
    assert "Jordan — Growth Portfolio" in rendered
    assert "Morgan" not in rendered
    assert "portfolio_alpha" not in rendered
    assert "portfolio_beta" not in rendered
    assert "portfolio_gamma" not in rendered


def test_completed_portfolio_action_can_continue_to_updated_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed_calls: list[dict[str, object]] = []
    build_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        attention_menu,
        "run_completed_portfolio_menu",
        lambda **kwargs: (
            completed_calls.append(kwargs)
            or attention_menu.BUILD_UPDATED_EDITION
        ),
    )
    monkeypatch.setattr(
        attention_menu,
        "run_current_portfolio_build_export_menu",
        lambda **kwargs: build_calls.append(kwargs),
    )

    attention_menu._run_owner_action(
        root=tmp_path,
        action=attention_menu._MenuActionChoice(
            action_id="open_completed_portfolio_editions",
            portfolio_id="portfolio_exact",
            label="Completed Portfolio Editions",
        ),
        portfolio_id="portfolio_exact",
        input_fn=_inputs([]),
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(completed_calls) == 1
    assert len(build_calls) == 1
    assert build_calls[0]["portfolio_id"] == "portfolio_exact"
