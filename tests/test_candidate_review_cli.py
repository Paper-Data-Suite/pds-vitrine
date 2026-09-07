from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    APPROVAL_REQUIREMENT_ID,
    REFLECTION_REQUIREMENT_ID,
    CurationFixtureWorkspace,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
)
from vitrine import cli
from vitrine.candidate_inbox import CandidateInboxQuery
from vitrine.candidate_review import list_candidate_review_entries
from vitrine.models import (
    CurationAnnotation,
    CurationReviewDecision,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SelectionDecision,
    SelectionProposal,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_context import (
    VitrineWorkflowDependencies,
    default_workflow_dependencies,
)


def _entry_for_candidate(workspace: Path, portfolio_id: str, candidate_id: str) -> str:
    result = list_candidate_review_entries(
        workspace,
        CandidateInboxQuery(portfolio_id=portfolio_id, limit=100),
    )
    return next(item.entry_id for item in result.items if item.candidate_id == candidate_id)


def _candidate_for_section(
    setup: CurationFixtureWorkspace, section_id: str
) -> PortfolioCandidate:
    return next(
        item
        for item in setup.candidate_records_by_source.values()
        if section_id in item.eligible_section_ids
    )


def _dependencies() -> VitrineWorkflowDependencies:
    return replace(
        default_workflow_dependencies(),
        curation_authority_gate=StaticCurationAuthorityGate(),
        development_fixture_mode=True,
    )


def test_candidate_review_cli_is_read_only_and_shows_dual_evaluation_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry_for_candidate(
        setup.workspace, setup.portfolio_id, candidate.candidate_id
    )
    before = load_current_state(setup.workspace).state_revision
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(AssertionError("unexpected prompt")),
    )
    output = io.StringIO()

    assert (
        cli.main(
            [
                "candidate",
                "review",
                entry_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            output=output,
            error=io.StringIO(),
        )
        == 0
    )

    rendered = output.getvalue()
    assert "Candidate Review Entry:" in rendered
    assert "Current review Evaluation:" in rendered
    assert "Curation provenance Evaluation:" in rendered
    assert "Eligible sections:" in rendered
    assert "Undecided Proposals:" in rendered
    assert load_current_state(setup.workspace).state_revision == before


def test_candidate_decide_cli_select_uses_guided_orchestration_without_placement(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry_for_candidate(
        setup.workspace, setup.portfolio_id, candidate.candidate_id
    )
    output = io.StringIO()

    assert (
        cli.main(
            [
                "candidate",
                "decide",
                entry_id,
                "--decision",
                "select",
                "--section-id",
                "baseline",
                "--reason",
                "Exact CLI selection test.",
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=_dependencies(),
            output=output,
            error=io.StringIO(),
        )
        == 0
    )

    records = load_current_records(setup.workspace)
    proposals = tuple(item for item in records if isinstance(item, SelectionProposal))
    decisions = tuple(item for item in records if isinstance(item, SelectionDecision))
    selections = tuple(item for item in records if isinstance(item, PortfolioSelection))
    placements = tuple(item for item in records if isinstance(item, PortfolioPlacement))
    assert proposals[-1].proposal_origin == "direct_selection"
    assert proposals[-1].candidate_id == candidate.candidate_id
    assert proposals[-1].proposed_section_ids == ("baseline",)
    assert decisions[-1].decision == "accepted"
    assert selections[-1].candidate_id == candidate.candidate_id
    assert placements == ()
    assert "Operation: direct_select" in output.getvalue()
    assert "Candidate decision recorded." in output.getvalue()


def test_candidate_decide_cli_decline_creates_rejected_proposal_only(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry_for_candidate(
        setup.workspace, setup.portfolio_id, candidate.candidate_id
    )

    assert (
        cli.main(
            [
                "candidate",
                "decide",
                entry_id,
                "--decision",
                "decline",
                "--section-id",
                "baseline",
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=_dependencies(),
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )

    records = load_current_records(setup.workspace)
    proposals = tuple(item for item in records if isinstance(item, SelectionProposal))
    decisions = tuple(item for item in records if isinstance(item, SelectionDecision))
    assert proposals[-1].proposal_origin == "teacher"
    assert proposals[-1].candidate_id == candidate.candidate_id
    assert decisions[-1].decision == "rejected"
    assert not any(isinstance(item, PortfolioSelection) for item in records)


def test_guided_content_cli_reuses_annotation_reflection_and_review_services(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry_for_candidate(
        setup.workspace, setup.portfolio_id, candidate.candidate_id
    )
    dependencies = _dependencies()

    assert (
        cli.main(
            [
                "candidate",
                "decide",
                entry_id,
                "--decision",
                "select",
                "--section-id",
                "baseline",
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )
    selection = next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, PortfolioSelection)
    )

    assert (
        cli.main(
            [
                "candidate",
                "annotation",
                "add",
                entry_id,
                "--purpose",
                "curator_context",
                "--scope",
                "selection",
                "--target",
                f"selection:{selection.selection_id}",
                "--content",
                "Teacher-authored curation context.",
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )
    annotation = next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, CurationAnnotation)
    )

    assert (
        cli.main(
            [
                "candidate",
                "reflection",
                "add",
                entry_id,
                "--requirement-id",
                REFLECTION_REQUIREMENT_ID,
                "--prompt-id",
                "growth_prompt",
                "--prompt-version",
                "1",
                "--prompt-snapshot",
                "Compare what changed and why.",
                "--scope",
                "portfolio",
                "--target",
                f"portfolio:{setup.portfolio_id}",
                "--content",
                "Teacher-authored reflection fixture.",
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )

    assert (
        cli.main(
            [
                "candidate",
                "curation-review",
                entry_id,
                "--scope",
                "annotation",
                "--target",
                f"annotation:{annotation.annotation_id}:{annotation.annotation_revision}",
                "--decision",
                "approved",
                "--reason",
                "Exact annotation revision reviewed.",
                "--approval-requirement-id",
                APPROVAL_REQUIREMENT_ID,
                "--actor-id",
                "teacher_cli",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )

    records = load_current_records(setup.workspace)
    assert any(isinstance(item, CurationAnnotation) for item in records)
    reflection = next(item for item in records if isinstance(item, PortfolioReflection))
    review = next(item for item in records if isinstance(item, CurationReviewDecision))
    assert reflection.author.actor_id == "teacher_cli"
    assert review.target_references[0].target_revision == annotation.annotation_revision
    assert review.approval_requirement_id == APPROVAL_REQUIREMENT_ID


def test_candidate_review_cli_malformed_target_is_stable_nonzero_failure(
    tmp_path: Path,
) -> None:
    error = io.StringIO()
    status = cli.main(
        [
            "candidate",
            "curation-review",
            "entry_exact",
            "--scope",
            "annotation",
            "--target",
            "not-a-target",
            "--decision",
            "approved",
            "--reason",
            "review",
            "--actor-id",
            "teacher_cli",
            "--workspace-root",
            str(tmp_path),
        ],
        dependencies=_dependencies(),
        output=io.StringIO(),
        error=error,
    )
    assert status == 1
    assert error.getvalue().startswith("candidate_review.invalid_request:")
    assert "Traceback" not in error.getvalue()


def test_slice6_keeps_existing_low_level_cli_commands_parseable() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["candidate", "list", "portfolio_1"]).candidate_command == "list"
    assert (
        parser.parse_args(
            [
                "selection",
                "add",
                "portfolio_1",
                "candidate_1",
                "--section-id",
                "section_1",
                "--actor-id",
                "teacher_1",
            ]
        ).selection_command
        == "add"
    )
    assert (
        parser.parse_args(
            [
                "arrangement",
                "place",
                "portfolio_1",
                "selection_1",
                "--section-id",
                "section_1",
                "--actor-id",
                "teacher_1",
            ]
        ).arrangement_command
        == "place"
    )
