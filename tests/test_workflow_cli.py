from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import pytest

from vitrine import cli
from vitrine.models import SelectionDecision, SelectionProposal
from vitrine.storage import load_current_records
from vitrine.workflow_context import default_workflow_dependencies


def test_workflow_parser_construction_is_side_effect_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    parser = cli.build_parser()
    assert list(tmp_path.iterdir()) == []
    assert parser.parse_args(["portfolio", "list"]).command == "portfolio"
    assert (
        parser.parse_args(["candidate", "list", "portfolio_1"]).command == "candidate"
    )
    assert (
        parser.parse_args(["snapshot", "verify", "series_1", "--edition", "1"]).command
        == "snapshot"
    )


def test_direct_workflow_commands_never_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(AssertionError("unexpected prompt")),
    )
    output = io.StringIO()
    assert (
        cli.main(
            ["portfolio", "list", "--workspace-root", str(tmp_path / "workspace")],
            output=output,
        )
        == 0
    )


def test_default_workflow_dependencies_fail_closed_and_hide_fixtures() -> None:
    dependencies = default_workflow_dependencies()
    assert dependencies.development_fixture_mode is False
    assert dependencies.producer_registry.profiles == ()
    assert dependencies.adapter_registry.adapters == ()
    with pytest.raises(ValueError, match="not configured"):
        dependencies.snapshot_planning_provider.propose(
            Path("unused"),
            object(),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "decision",
    ("accepted", "rejected", "changes_requested", "withdrawn", "expired"),
)
def test_selection_parser_uses_exact_service_decisions(decision: str) -> None:
    args = cli.build_parser().parse_args(
        [
            "selection",
            "decide",
            "portfolio_1",
            "proposal_1",
            "--decision",
            decision,
            "--actor-id",
            "teacher_1",
        ]
    )
    assert args.decision == decision


def test_missing_plan_file_is_a_stable_cli_failure(tmp_path: Path) -> None:
    error = io.StringIO()
    status = cli.main(
        [
            "snapshot",
            "plan",
            "request_1",
            "--from-plan-json",
            str(tmp_path / "missing.json"),
            "--actor-id",
            "teacher_1",
            "--workspace-root",
            str(tmp_path),
        ],
        error=error,
    )
    assert status == 1
    assert error.getvalue().startswith("snapshot_plan_file_unreadable:")
    assert "Traceback" not in error.getvalue()


def test_direct_cli_executes_every_nonaccepted_selection_decision(
    tmp_path: Path,
) -> None:
    from scripts.curation_fixture_support import StaticCurationAuthorityGate
    from scripts.improvement_portfolio_fixture_support import (
        PORTFOLIO_ID,
        build_improvement_portfolio_fixture,
    )

    built = build_improvement_portfolio_fixture(tmp_path, complete_curation=False)
    workspace, _evaluations, candidates = built
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=StaticCurationAuthorityGate(),
        development_fixture_mode=True,
    )
    baseline_candidate = next(
        item for item in candidates if "baseline" in item.eligible_section_ids
    )
    for decision in ("rejected", "changes_requested", "withdrawn", "expired"):
        before_ids = {
            item.selection_proposal_id
            for item in load_current_records(workspace)
            if isinstance(item, SelectionProposal)
        }
        assert (
            cli.main(
                [
                    "selection",
                    "propose",
                    PORTFOLIO_ID,
                    baseline_candidate.candidate_id,
                    "--section-id",
                    "baseline",
                    "--actor-id",
                    "teacher_cli",
                    "--workspace-root",
                    str(workspace),
                ],
                dependencies=dependencies,
                output=io.StringIO(),
                error=io.StringIO(),
            )
            == 0
        )
        proposal = next(
            item
            for item in load_current_records(workspace)
            if isinstance(item, SelectionProposal)
            and item.selection_proposal_id not in before_ids
        )
        assert (
            cli.main(
                [
                    "selection",
                    "decide",
                    PORTFOLIO_ID,
                    proposal.selection_proposal_id,
                    "--decision",
                    decision,
                    "--actor-id",
                    "teacher_cli",
                    "--workspace-root",
                    str(workspace),
                ],
                dependencies=dependencies,
                output=io.StringIO(),
                error=io.StringIO(),
            )
            == 0
        )
        assert any(
            isinstance(item, SelectionDecision)
            and item.selection_proposal_id == proposal.selection_proposal_id
            and item.decision == decision
            for item in load_current_records(workspace)
        )
