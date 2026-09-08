from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
)
from vitrine import cli
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_context import default_workflow_dependencies
from vitrine.workflow_views import show_composition
from vitrine.working_composition import prepare_working_composition


def test_working_composition_cli_parsers_add_prepared_path_and_preserve_low_level() -> None:
    parser = cli.build_parser()

    prepared = parser.parse_args(
        [
            "composition",
            "prepare",
            "portfolio_1",
        ]
    )
    assert prepared.composition_command == "prepare"

    frozen = parser.parse_args(
        [
            "composition",
            "freeze",
            "portfolio_1",
            "--preparation-fingerprint",
            "0" * 64,
            "--expected-state-revision",
            "1",
            "--expected-composition-pointer-revision",
            "none",
            "--actor-id",
            "teacher_1",
        ]
    )
    assert frozen.composition_command == "freeze"
    assert frozen.expected_composition_pointer_revision == "none"

    legacy = parser.parse_args(
        [
            "composition",
            "build",
            "portfolio_1",
            "--actor-id",
            "teacher_1",
        ]
    )
    assert legacy.composition_command == "build"


def test_composition_prepare_cli_is_read_only_and_prints_exact_review_token(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    before_state = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)
    output = io.StringIO()

    assert (
        cli.main(
            [
                "composition",
                "prepare",
                setup.portfolio_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            output=output,
            error=io.StringIO(),
        )
        == 0
    )

    after_state = load_current_state(setup.workspace).state_revision
    after_records = load_current_records(setup.workspace)
    text = output.getvalue()
    assert after_state == before_state
    assert after_records == before_records
    assert "Contract: vitrine_guided_working_composition_v1" in text
    assert f"Observed state revision: {before_state}" in text
    assert "Observed Composition pointer revision: none" in text
    assert "Disposition: create_initial" in text
    assert "Preparation fingerprint: " in text
    assert "Working Composition != Audience Context != Snapshot" in text


def test_composition_freeze_cli_uses_exact_reviewed_preparation(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    gate = StaticCurationAuthorityGate()
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=gate,
        development_fixture_mode=True,
    )
    output = io.StringIO()

    assert (
        cli.main(
            [
                "composition",
                "freeze",
                setup.portfolio_id,
                "--preparation-fingerprint",
                preparation.preparation_fingerprint,
                "--expected-state-revision",
                str(preparation.observed_state_revision),
                "--expected-composition-pointer-revision",
                "none",
                "--actor-id",
                ACTOR.actor_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=output,
            error=io.StringIO(),
        )
        == 0
    )

    view = show_composition(setup.workspace, setup.portfolio_id)
    assert view.composition is not None
    assert view.composition.composition_revision == 1
    assert len(gate.requests) == 1
    assert gate.requests[0].operation == "compose_portfolio"
    assert "Disposition: created" in output.getvalue()
    assert (
        f"Preparation fingerprint: {preparation.preparation_fingerprint}"
        in output.getvalue()
    )


def test_composition_freeze_cli_rejects_fingerprint_without_authority_or_write(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    gate = StaticCurationAuthorityGate()
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=gate,
        development_fixture_mode=True,
    )
    before_revision = load_current_state(setup.workspace).state_revision
    error = io.StringIO()

    assert (
        cli.main(
            [
                "composition",
                "freeze",
                setup.portfolio_id,
                "--preparation-fingerprint",
                "0" * 64,
                "--expected-state-revision",
                str(preparation.observed_state_revision),
                "--expected-composition-pointer-revision",
                "none",
                "--actor-id",
                ACTOR.actor_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=error,
        )
        == 1
    )

    assert load_current_state(setup.workspace).state_revision == before_revision
    assert show_composition(setup.workspace, setup.portfolio_id).composition is None
    assert gate.requests == []
    assert error.getvalue().startswith("working_composition.preparation_mismatch:")


def test_composition_freeze_cli_rejects_pointer_expectation_without_inference(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    gate = StaticCurationAuthorityGate()
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=gate,
        development_fixture_mode=True,
    )
    before_revision = load_current_state(setup.workspace).state_revision
    error = io.StringIO()

    assert (
        cli.main(
            [
                "composition",
                "freeze",
                setup.portfolio_id,
                "--preparation-fingerprint",
                preparation.preparation_fingerprint,
                "--expected-state-revision",
                str(preparation.observed_state_revision),
                "--expected-composition-pointer-revision",
                "1",
                "--actor-id",
                ACTOR.actor_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=error,
        )
        == 1
    )

    assert load_current_state(setup.workspace).state_revision == before_revision
    assert gate.requests == []
    assert error.getvalue().startswith(
        "working_composition.composition_pointer_changed:"
    )
