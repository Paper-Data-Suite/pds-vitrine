from __future__ import annotations

import io
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine import cli
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.storage import load_current_state


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
        producer_registry=(build_development_fixture_producer_registry()),
        adapter_registry=(build_development_fixture_adapter_registry()),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()


def test_candidate_inbox_parser_supports_workspace_list_and_show() -> None:
    parser = cli.build_parser()

    listing = parser.parse_args(
        [
            "candidate",
            "inbox",
            "--portfolio-id",
            "portfolio_fixture",
            "--attention-only",
            "--stale-only",
            "--selected-state",
            "unselected",
            "--outcome",
            "eligible",
            "--condition",
            "ready_for_consideration",
            "--module-id",
            "vitrine_scoreform_fixture",
            "--limit",
            "25",
        ]
    )
    assert listing.command == "candidate"
    assert listing.candidate_command == "inbox"
    assert listing.candidate_inbox_command is None
    assert listing.portfolio_id == "portfolio_fixture"
    assert listing.attention_only is True
    assert listing.stale_only is True
    assert listing.outcome == ["eligible"]
    assert listing.condition == ["ready_for_consideration"]

    detail = parser.parse_args(
        [
            "candidate",
            "inbox",
            "show",
            "candidate:candidate_fixture",
        ]
    )
    assert detail.candidate_inbox_command == "show"
    assert detail.entry_id == "candidate:candidate_fixture"


def test_candidate_inbox_cli_lists_teacher_facing_rows_read_only(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    before = load_current_state(setup.workspace).state_revision
    output = io.StringIO()
    error = io.StringIO()

    status = cli.main(
        [
            "candidate",
            "inbox",
            "--portfolio-id",
            setup.portfolio_id,
            "--outcome",
            "eligible",
            "--workspace-root",
            str(setup.workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 0
    rendered = output.getvalue()
    assert "Candidate Inbox: 2 matching" in rendered
    assert "candidate:" in rendered
    assert "Eligible" in rendered
    assert "Ready For Consideration" in rendered
    assert "Current" in rendered
    assert "Not selected" in rendered
    assert "vitrine_scoreform_fixture" not in error.getvalue()
    assert error.getvalue() == ""
    assert load_current_state(setup.workspace).state_revision == before


def test_candidate_inbox_cli_show_drills_into_exact_provenance(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    listing = io.StringIO()
    assert (
        cli.main(
            [
                "candidate",
                "inbox",
                "--limit",
                "1",
                "--workspace-root",
                str(setup.workspace),
            ],
            output=listing,
            error=io.StringIO(),
        )
        == 0
    )
    row = next(
        line
        for line in listing.getvalue().splitlines()
        if line.startswith("candidate:")
    )
    entry_id = row.split("\t", 1)[0]
    before = load_current_state(setup.workspace).state_revision

    output = io.StringIO()
    error = io.StringIO()
    status = cli.main(
        [
            "candidate",
            "inbox",
            "show",
            entry_id,
            "--workspace-root",
            str(setup.workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 0
    rendered = output.getvalue()
    assert f"Candidate Inbox Entry: {entry_id}" in rendered
    assert "Core Publication:" in rendered
    assert "Producer module: vitrine_scoreform_fixture" in rendered
    assert "Producer source:" in rendered
    assert "Artifact:" in rendered
    assert "Subject relationships:" in rendered
    assert "Profile Binding:" in rendered
    assert "Evaluator contract:" in rendered
    assert "Current-pointer history: 1:" in rendered
    assert error.getvalue() == ""
    assert load_current_state(setup.workspace).state_revision == before


def test_candidate_inbox_cli_ineligible_rows_are_evaluation_only(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover(setup)
    output = io.StringIO()
    error = io.StringIO()

    status = cli.main(
        [
            "candidate",
            "inbox",
            "--outcome",
            "ineligible",
            "--workspace-root",
            str(setup.workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 0
    rendered = output.getvalue()
    assert "Candidate Inbox: 2 matching" in rendered
    assert "evaluation:" in rendered
    assert "Ineligible" in rendered
    assert "candidate:" not in "\n".join(
        line for line in rendered.splitlines() if line.startswith("evaluation:")
    )
    assert error.getvalue() == ""


def test_candidate_inbox_cli_invalid_detail_is_stable_failure(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    output = io.StringIO()
    error = io.StringIO()

    status = cli.main(
        [
            "candidate",
            "inbox",
            "show",
            "candidate:missing",
            "--workspace-root",
            str(setup.workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 1
    assert output.getvalue() == ""
    assert error.getvalue().startswith("candidate_inbox.entry_not_found:")
    assert "Traceback" not in error.getvalue()


def test_candidate_inbox_cli_evaluated_since_is_explicit_boundary(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    output = io.StringIO()

    status = cli.main(
        [
            "candidate",
            "inbox",
            "--evaluated-since",
            fixed_clock().isoformat(),
            "--workspace-root",
            str(setup.workspace),
        ],
        output=output,
        error=io.StringIO(),
    )

    assert status == 0
    assert "Candidate Inbox: 2 matching" in output.getvalue()
