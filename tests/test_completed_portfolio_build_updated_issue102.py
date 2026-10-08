"""Issue #102 Slice 5: Build Updated Edition and post-build continuation."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import completed_portfolio_menu, current_portfolio_menu, portfolio_menu
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioSeries,
)
from vitrine.models import ProfileRevisionRef
from vitrine.portfolio_output_opening import PortfolioOutputOpenError
from vitrine.workflow_context import default_workflow_dependencies

NOW = datetime(2026, 10, 6, 23, 30, tzinfo=timezone.utc)
PROFILE = ProfileRevisionRef(portfolio_profile_id="profile_1", profile_revision=2)


def _inputs(*values: str):
    pending = iter(values)
    return lambda _prompt: next(pending)


def _history() -> CompletedPortfolioHistory:
    export = CompletedPortfolioExport(
        snapshot_export_artifact_id="export_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        relative_path="exports/export_1",
        generated_at=NOW,
        predecessor_export_artifact_id=None,
    )
    edition = CompletedPortfolioEdition(
        snapshot_series_id="series_1",
        edition_number=2,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=2,
        audience_context_id="audience_1",
        created_at=NOW,
        predecessor_edition=1,
        is_current=False,
        exports=(export,),
        presentations=(),
    )
    series = CompletedPortfolioSeries(
        snapshot_series_id="series_1",
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        snapshot_purpose="improvement",
        audience_context_id="audience_1",
        audience_class="student",
        audience_purpose="Student Review",
        presentation_class="student_portfolio",
        created_at=NOW,
        predecessor_series_id=None,
        current_edition_number=None,
        editions=(edition,),
    )
    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        series=(series,),
    )


def _presentation_result() -> SimpleNamespace:
    return SimpleNamespace(
        snapshot_series_id="series_exact",
        edition_number=3,
        snapshot_export_artifact_id="export_exact",
        export_disposition="created",
        export_path=Path("vitrine/snapshots/exports-bounded-v1/export_exact"),
        presentation_disposition="created",
        presentation_artifact_id="presentation_exact",
        presentation_relative_path="presentations-bounded-v1/presentation_exact",
        presentation_html_relative_path=(
            "presentations-bounded-v1/presentation_exact/portfolio.html"
        ),
        presentation_pdf_relative_path=(
            "presentations-bounded-v1/presentation_exact/portfolio.pdf"
        ),
        presentation_verified=True,
        current_pointer_advanced=False,
    )


def test_completed_detail_offers_build_updated() -> None:
    history = _history()
    actions = completed_portfolio_menu._edition_actions(
        history.series[0],
        history.series[0].editions[0],
    )

    assert (
        completed_portfolio_menu.BUILD_UPDATED_EDITION,
        "Build Updated Edition",
    ) in actions


def test_completed_menu_returns_build_updated_routing_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = _history()
    monkeypatch.setattr(
        completed_portfolio_menu,
        "_load_history",
        lambda *_args: history,
    )
    monkeypatch.setattr(
        completed_portfolio_menu,
        "_portfolio_label",
        lambda *_args: "Jordan — Improvement Portfolio",
    )

    result = completed_portfolio_menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "4"),
        output=io.StringIO(),
        clear_fn=lambda: None,
    )

    assert result == completed_portfolio_menu.BUILD_UPDATED_EDITION


def test_portfolio_context_routes_build_updated_to_existing_current_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        portfolio_menu,
        "show_portfolio",
        lambda *_args: SimpleNamespace(
            summary=SimpleNamespace(
                title_snapshot="Improvement Portfolio",
                subject_display_label="Jordan",
            )
        ),
    )
    monkeypatch.setattr(
        portfolio_menu,
        "run_completed_portfolio_menu",
        lambda **_kwargs: completed_portfolio_menu.BUILD_UPDATED_EDITION,
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        portfolio_menu,
        "run_current_portfolio_build_export_menu",
        lambda **kwargs: calls.append(kwargs),
    )
    dependencies = default_workflow_dependencies()
    actor = SimpleNamespace(actor_id="teacher_exact")

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("8", "B"),
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=dependencies,
        actor=actor,  # type: ignore[arg-type]
    )

    assert len(calls) == 1
    assert calls[0]["root"] == tmp_path
    assert calls[0]["portfolio_id"] == "portfolio_1"
    assert calls[0]["dependencies"] is dependencies
    assert calls[0]["actor"] is actor
    assert "snapshot_series_id" not in calls[0]
    assert "edition_number" not in calls[0]


@pytest.mark.parametrize(
    ("choice", "operation_name"),
    (
        ("1", "open_student_portfolio_html"),
        ("2", "open_printable_student_portfolio"),
        ("3", "open_student_portfolio_folder"),
    ),
)
def test_post_build_actions_reuse_exact_durable_open_services(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    choice: str,
    operation_name: str,
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        current_portfolio_menu,
        operation_name,
        lambda root, *, presentation_artifact_id: calls.append(
            (Path(root), presentation_artifact_id)
        ),
    )
    output = io.StringIO()

    current_portfolio_menu._run_post_build_continuation(
        root=tmp_path,
        result=_presentation_result(),  # type: ignore[arg-type]
        input_fn=_inputs(choice, "", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    assert calls == [(tmp_path, "presentation_exact")]
    rendered = output.getvalue()
    assert "View Student Portfolio" in rendered
    assert "Print Portfolio" in rendered
    assert "Open Portfolio Folder" in rendered
    assert "presentation_exact" not in rendered


def test_post_build_print_never_claims_physical_printing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        current_portfolio_menu,
        "open_printable_student_portfolio",
        lambda *_args, **_kwargs: None,
    )
    output = io.StringIO()

    current_portfolio_menu._run_post_build_continuation(
        root=tmp_path,
        result=_presentation_result(),  # type: ignore[arg-type]
        input_fn=_inputs("2", "", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    rendered = output.getvalue()
    assert "Use your PDF application's Print command" in rendered
    assert "Portfolio printed" not in rendered


def test_post_build_open_failure_is_fail_soft_and_hides_private_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object):
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "C:/private/custody/changed",
            stage="presentation_verification",
        )

    monkeypatch.setattr(
        current_portfolio_menu,
        "open_student_portfolio_html",
        fail,
    )
    output = io.StringIO()

    current_portfolio_menu._run_post_build_continuation(
        root=tmp_path,
        result=_presentation_result(),  # type: ignore[arg-type]
        input_fn=_inputs("1", "", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    rendered = output.getvalue()
    assert "no longer matches its verified saved state" in rendered
    assert "Nothing was changed automatically." in rendered
    assert "C:/private/custody" not in rendered


def test_post_build_without_student_presentation_has_no_fake_open_actions(
    tmp_path: Path,
) -> None:
    result = _presentation_result()
    result.presentation_disposition = "unsupported"
    result.presentation_artifact_id = None
    result.presentation_relative_path = None
    result.presentation_html_relative_path = None
    result.presentation_pdf_relative_path = None
    result.presentation_verified = False
    output = io.StringIO()

    current_portfolio_menu._run_post_build_continuation(
        root=tmp_path,
        result=result,  # type: ignore[arg-type]
        input_fn=_inputs(""),
        output=output,
        clear_fn=lambda: None,
    )

    rendered = output.getvalue()
    assert "View Student Portfolio" not in rendered
    assert "Print Portfolio" not in rendered
    assert "Open Portfolio Folder" not in rendered
