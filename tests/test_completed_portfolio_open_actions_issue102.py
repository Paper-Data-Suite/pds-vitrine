"""Issue #102 Slice 3: teacher local-use actions from completed history."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vitrine import completed_portfolio_menu as menu
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
)
from vitrine.models import ProfileRevisionRef
from vitrine.portfolio_output_opening import PortfolioOutputOpenError

NOW = datetime(2026, 10, 6, 22, 0, tzinfo=timezone.utc)
PROFILE = ProfileRevisionRef(portfolio_profile_id="profile_1", profile_revision=2)


def _presentation(identity: str, when: datetime) -> CompletedPortfolioPresentation:
    return CompletedPortfolioPresentation(
        presentation_artifact_id=identity,
        snapshot_export_artifact_id="export_1",
        presentation_class="student_portfolio",
        presentation_contract_version="vitrine_student_portfolio_presentation_v1",
        renderer_id="vitrine_student_portfolio_renderer",
        renderer_version="1",
        renderer_contract_version="vitrine_student_portfolio_renderer_v1",
        relative_path=f"presentations/{identity}",
        html_relative_path=f"presentations/{identity}/portfolio.html",
        printable_pdf_relative_path=f"presentations/{identity}/portfolio.pdf",
        generated_at=when,
        predecessor_presentation_artifact_id=None,
    )


def _history(
    *,
    presentations: tuple[CompletedPortfolioPresentation, ...] | None = None,
) -> CompletedPortfolioHistory:
    export = CompletedPortfolioExport(
        snapshot_export_artifact_id="export_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        relative_path="exports/export_1",
        generated_at=NOW - timedelta(days=2),
        predecessor_export_artifact_id=None,
    )
    if presentations is None:
        presentations = (_presentation("presentation_secret_1", NOW - timedelta(days=1)),)
    edition = CompletedPortfolioEdition(
        snapshot_series_id="series_1",
        edition_number=2,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=2,
        audience_context_id="audience_1",
        created_at=NOW - timedelta(days=3),
        predecessor_edition=1,
        is_current=True,
        exports=(export,),
        presentations=presentations,
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
        created_at=NOW - timedelta(days=5),
        predecessor_series_id=None,
        current_edition_number=2,
        editions=(edition,),
    )
    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        series=(series,),
    )


def _inputs(*values: str):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _install_menu_context(
    monkeypatch: pytest.MonkeyPatch,
    history: CompletedPortfolioHistory,
) -> None:
    monkeypatch.setattr(menu, "_load_history", lambda *_args: history)
    monkeypatch.setattr(
        menu,
        "_portfolio_label",
        lambda *_args: "Jordan — Improvement Portfolio",
    )


def test_detail_offers_safe_local_actions_before_history_and_provenance() -> None:
    series = _history().series[0]
    edition = series.editions[0]
    output = io.StringIO()

    actions = menu._render_edition_detail(
        output,
        edition=edition,
        series=series,
        series_label="Student Review",
        portfolio_label="Jordan — Improvement Portfolio",
    )

    assert actions == (
        "view_student_portfolio",
        "print_portfolio",
        "open_portfolio_folder",
        "open_technical_export",
        "verify_portfolio",
        "artifact_history",
        "technical_details",
    )
    rendered = output.getvalue()
    assert "1. View Student Portfolio" in rendered
    assert "2. Print Portfolio" in rendered
    assert "3. Open Portfolio Folder" in rendered
    assert "4. Open Technical Export Folder" in rendered
    assert "5. Verify Portfolio Now" in rendered
    assert "6. Export / Presentation History" in rendered
    assert "7. Technical Details / Provenance" in rendered
    assert "presentation_secret_1" not in rendered
    assert "export_1" not in rendered


def test_view_action_uses_exact_canonical_presentation_without_id_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = _history()
    _install_menu_context(monkeypatch, history)
    opened: list[str] = []
    monkeypatch.setattr(
        menu,
        "open_student_portfolio_html",
        lambda _root, *, presentation_artifact_id: opened.append(
            presentation_artifact_id
        ),
    )
    output = io.StringIO()

    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "1", "", "B", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    assert opened == ["presentation_secret_1"]
    rendered = output.getvalue()
    assert "Student Portfolio opened." in rendered
    assert "presentation_secret_1" not in rendered
    assert "delivered" not in rendered.casefold()
    assert "shared" not in rendered.casefold()


def test_print_action_opens_pdf_but_does_not_claim_printing_occurred(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_menu_context(monkeypatch, _history())
    opened: list[str] = []
    monkeypatch.setattr(
        menu,
        "open_printable_student_portfolio",
        lambda _root, *, presentation_artifact_id: opened.append(
            presentation_artifact_id
        ),
    )
    output = io.StringIO()

    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "2", "", "B", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    assert opened == ["presentation_secret_1"]
    rendered = output.getvalue()
    assert "Printable Portfolio opened." in rendered
    assert "Use your PDF application's Print command" in rendered
    assert "Portfolio printed" not in rendered


def test_open_technical_export_uses_exact_canonical_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_menu_context(monkeypatch, _history())
    opened: list[str] = []
    monkeypatch.setattr(
        menu,
        "open_technical_export_folder",
        lambda _root, *, snapshot_export_artifact_id: opened.append(
            snapshot_export_artifact_id
        ),
    )

    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "4", "", "B", "B"),
        output=io.StringIO(),
        clear_fn=lambda: None,
    )

    assert opened == ["export_1"]


def test_multiple_presentations_are_chosen_by_human_label_not_opaque_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = _history(
        presentations=(
            _presentation("presentation_private_alpha", NOW - timedelta(days=2)),
            _presentation("presentation_private_beta", NOW - timedelta(days=1)),
        )
    )
    _install_menu_context(monkeypatch, history)
    opened: list[str] = []
    monkeypatch.setattr(
        menu,
        "open_student_portfolio_html",
        lambda _root, *, presentation_artifact_id: opened.append(
            presentation_artifact_id
        ),
    )
    output = io.StringIO()

    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "1", "2", "", "B", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    assert opened == ["presentation_private_beta"]
    rendered = output.getvalue()
    assert "Choose Student Portfolio" in rendered
    assert "presentation_private_alpha" not in rendered
    assert "presentation_private_beta" not in rendered


def test_verification_or_open_failure_is_fail_soft_and_hides_private_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_menu_context(monkeypatch, _history())

    def fail(*_args: object, **_kwargs: object):
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "C:/private/student/path/portfolio.html changed",
            stage="presentation_verification",
        )

    monkeypatch.setattr(menu, "open_student_portfolio_html", fail)
    output = io.StringIO()

    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_inputs("1", "1", "", "B", "B"),
        output=output,
        clear_fn=lambda: None,
    )

    rendered = output.getvalue()
    assert "no longer matches its verified saved state" in rendered
    assert "Nothing was changed automatically." in rendered
    assert "Technical Details / Provenance" in rendered
    assert "C:/private/student/path" not in rendered
