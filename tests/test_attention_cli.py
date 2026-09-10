from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import attention_cli, cli
from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionQuery,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
)


def _report(portfolio_id: str | None) -> VitrineAttentionReport:
    return VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=12,
        summaries=(
            VitrineAttentionSummary(
                code="vitrine_candidate_review_pending",
                label="Candidate review pending",
                count=2,
                count_unit="candidates",
                attention_class="workflow",
                portfolio_id=portfolio_id,
                reason_codes=(),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_inbox",
                    portfolio_id=portfolio_id,
                ),
            ),
        ),
        notices=(),
    )


def test_direct_attention_cli_is_noninteractive_and_emits_stable_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, VitrineAttentionQuery]] = []
    monkeypatch.setattr(
        attention_cli,
        "show_workspace",
        lambda _root: SimpleNamespace(root=tmp_path),
    )

    def evaluate(root: Path, query: VitrineAttentionQuery) -> VitrineAttentionReport:
        calls.append((root, query))
        return _report(query.portfolio_id)

    monkeypatch.setattr(attention_cli, "evaluate_vitrine_attention", evaluate)
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(
            AssertionError("direct attention command prompted for input")
        ),
    )
    output = io.StringIO()

    result = cli.main(
        [
            "attention",
            "list",
            "--portfolio-id",
            "portfolio_exact",
            "--workspace-root",
            str(tmp_path),
        ],
        output=output,
    )

    assert result == 0
    assert calls == [
        (tmp_path, VitrineAttentionQuery(portfolio_id="portfolio_exact"))
    ]
    rendered = output.getvalue()
    assert "vitrine_candidate_review_pending" in rendered
    assert "action=open_candidate_inbox" in rendered
    assert "portfolio=portfolio_exact" in rendered


def test_unavailable_attention_cli_returns_nonzero_but_reports_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        attention_cli,
        "show_workspace",
        lambda _root: SimpleNamespace(root=tmp_path),
    )
    unavailable = VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="unavailable",
        observed_state_revision=None,
        summaries=(),
        notices=(),
    )
    monkeypatch.setattr(
        attention_cli,
        "evaluate_vitrine_attention",
        lambda _root, _query: unavailable,
    )
    output = io.StringIO()

    result = cli.main(
        ["attention", "list", "--workspace-root", str(tmp_path)],
        output=output,
    )

    assert result == 1
    assert "Evaluation: unavailable" in output.getvalue()
    assert VITRINE_ATTENTION_CONTRACT_VERSION in output.getvalue()
