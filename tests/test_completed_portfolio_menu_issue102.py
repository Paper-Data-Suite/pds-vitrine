"""Issue #102 Slice 2: canonical teacher-facing completed history."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import completed_portfolio_menu as menu
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioHistoryError,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
)
from vitrine.models import ProfileRevisionRef

NOW = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_internal_only", profile_revision=2
)


def _export(identity: str, when: datetime) -> CompletedPortfolioExport:
    return CompletedPortfolioExport(
        snapshot_export_artifact_id=identity,
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        relative_path=f"exports/{identity}",
        generated_at=when,
        predecessor_export_artifact_id=None,
    )


def _presentation(
    identity: str, export_id: str, when: datetime
) -> CompletedPortfolioPresentation:
    return CompletedPortfolioPresentation(
        presentation_artifact_id=identity,
        snapshot_export_artifact_id=export_id,
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


def _edition(
    series: str,
    number: int,
    *,
    current: bool,
    with_artifacts: bool = False,
) -> CompletedPortfolioEdition:
    export = _export("export_private_123", NOW - timedelta(days=4))
    presentation = _presentation(
        "presentation_private_456",
        export.snapshot_export_artifact_id,
        NOW - timedelta(days=3),
    )
    return CompletedPortfolioEdition(
        snapshot_series_id=series,
        edition_number=number,
        portfolio_id="portfolio_private_111",
        portfolio_subject_id="subject_private_222",
        profile_binding_id="binding_private_333",
        profile_revision=PROFILE,
        composition_revision=number,
        audience_context_id="audience_private_444",
        created_at=NOW - timedelta(days=number),
        predecessor_edition=number - 1 if number > 1 else None,
        is_current=current,
        exports=(export,) if with_artifacts else (),
        presentations=(presentation,) if with_artifacts else (),
    )


def _history(*, duplicates: bool = False) -> CompletedPortfolioHistory:
    first = CompletedPortfolioSeries(
        snapshot_series_id="series_internal_a",
        portfolio_id="portfolio_private_111",
        portfolio_subject_id="subject_private_222",
        snapshot_purpose="improvement",
        audience_context_id="audience_private_444",
        audience_class="student",
        audience_purpose="Student Review",
        presentation_class="student_portfolio",
        created_at=NOW - timedelta(days=10),
        predecessor_series_id=None,
        current_edition_number=1,
        editions=(
            _edition("series_internal_a", 2, current=False),
            _edition("series_internal_a", 1, current=True, with_artifacts=True),
        ),
    )
    second = CompletedPortfolioSeries(
        snapshot_series_id="series_internal_b",
        portfolio_id="portfolio_private_111",
        portfolio_subject_id="subject_private_222",
        snapshot_purpose="family_review",
        audience_context_id="audience_family_hidden",
        audience_class="family",
        audience_purpose="Student Review" if duplicates else "Family Review",
        presentation_class="student_portfolio",
        created_at=NOW - timedelta(days=5),
        predecessor_series_id=None,
        current_edition_number=None,
        editions=(_edition("series_internal_b", 1, current=False),),
    )
    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id="portfolio_private_111",
        portfolio_subject_id="subject_private_222",
        series=(first, second),
    )


def _inputs(*responses: str):
    values = iter(responses)
    return lambda _prompt: next(values)


def test_list_groups_series_and_preserves_exact_current_pointer_semantics() -> None:
    output = io.StringIO()
    choices = menu._render_list(output, _history(), "Jordan — Improvement Portfolio")
    text = output.getvalue()
    assert choices == (
        ("series_internal_a", 2),
        ("series_internal_a", 1),
        ("series_internal_b", 1),
    )
    assert "Student Review" in text
    assert "Family Review" in text
    assert "Jordan — Improvement Portfolio" in text
    assert text.count("Current: yes") == 1
    assert text.count("Current: no") == 2
    assert "Edition 2" in text and "Edition 1" in text
    assert "recorded (verification required)" in text
    for private in (
        "series_internal_",
        "portfolio_private_",
        "presentation_private_",
        "export_private_",
        "audience_private_",
    ):
        assert private not in text


def test_colliding_human_labels_are_disambiguated_without_opaque_ids() -> None:
    output = io.StringIO()
    menu._render_list(output, _history(duplicates=True), "Improvement Portfolio")
    text = output.getvalue()
    assert "Student Review (Series 1)" in text
    assert "Student Review (Series 2)" in text
    assert "series_internal" not in text


def test_edition_details_offer_safe_local_actions_but_defer_explicit_verify() -> None:
    series = _history().series[0]
    edition = series.editions[1]
    output = io.StringIO()
    menu._render_edition_detail(
        output,
        edition=edition,
        series=series,
        series_label="Student Review",
        portfolio_label="Jordan — Improvement Portfolio",
    )
    text = output.getvalue()
    assert "Export / Presentation History" in text
    assert "Technical Details / Provenance" in text
    assert "Current: yes" in text
    assert "View Student Portfolio" in text
    assert "Print Portfolio" in text
    assert "Open Portfolio Folder" in text
    assert "Open Technical Export Folder" in text
    assert "Verify Portfolio Now" in text
    assert "presentation_private_456" not in text


def test_history_is_human_readable_and_provenance_is_opt_in() -> None:
    series = _history().series[0]
    edition = series.editions[1]
    ordinary = io.StringIO()
    technical = io.StringIO()
    menu._render_artifact_history(ordinary, edition)
    menu._render_technical(technical, edition=edition, series=series)
    assert "Directory Package" in ordinary.getvalue()
    assert "Student Portfolio" in ordinary.getvalue()
    assert "export_private_123" not in ordinary.getvalue()
    assert "presentation_private_456" not in ordinary.getvalue()
    assert "export_private_123" in technical.getvalue()
    assert "presentation_private_456" in technical.getvalue()
    assert "portfolio.html" in technical.getvalue()
    assert "portfolio.pdf" in technical.getvalue()


def test_selected_edition_reloads_canonical_history_before_each_detail_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    reloads: list[str] = []

    def history(_root: Path, portfolio_id: str) -> CompletedPortfolioHistory:
        reloads.append(portfolio_id)
        return _history()

    monkeypatch.setattr(menu, "_load_history", history)
    monkeypatch.setattr(
        menu, "_portfolio_label", lambda *_: "Jordan — Improvement Portfolio"
    )
    output = io.StringIO()
    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_private_111",
        input_fn=_inputs("2", "7", "", "8", "", "B", "B"),
        output=output,
        clear_fn=lambda: None,
    )
    assert len(reloads) >= 4
    assert "Export / Presentation History" in output.getvalue()
    assert "Technical Details / Provenance" in output.getvalue()
    assert "export_private_123" in output.getvalue()


def test_history_errors_do_not_dump_private_paths_or_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object) -> CompletedPortfolioHistory:
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.canonical_history_inconsistent",
            "private retained scan path should never be printed",
        )

    monkeypatch.setattr(menu, "_load_history", broken)
    output = io.StringIO()
    menu.run_completed_portfolio_menu(
        root=tmp_path,
        portfolio_id="portfolio_private_111",
        input_fn=_inputs(""),
        output=output,
        clear_fn=lambda: None,
    )
    rendered = output.getvalue()
    assert "completed_portfolio.canonical_history_inconsistent" in rendered
    assert "private retained scan path" not in rendered
    assert "Traceback" not in rendered


def test_canonical_history_service_reads_once_and_never_scans_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Path] = []

    def load(root: Path):
        seen.append(root)
        return SimpleNamespace(state_revision=10), ()

    monkeypatch.setattr(menu, "load_current_records_with_state", load)
    monkeypatch.setattr(
        menu,
        "project_completed_portfolio_history",
        lambda records, *, portfolio_id: _history(),
    )
    result = menu._load_history(tmp_path, "portfolio_private_111")
    assert result.completed_edition_count == 3
    assert seen == [tmp_path]


def test_portfolio_context_routes_completed_history_without_opaque_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vitrine import portfolio_menu
    from vitrine.workflow_context import default_workflow_dependencies

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
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        portfolio_menu,
        "run_completed_portfolio_menu",
        lambda **kwargs: calls.append(kwargs),
    )
    output = io.StringIO()
    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_private_111",
        input_fn=_inputs("8", "B"),
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=None,
    )
    assert len(calls) == 1
    assert calls[0]["portfolio_id"] == "portfolio_private_111"
    assert calls[0]["root"] == tmp_path
    assert calls[0]["actor"] is None
    assert "8. Completed Portfolio Editions" in output.getvalue()
    assert "9. Attention / Next Actions" in output.getvalue()


def test_overview_shows_completed_separately_from_current() -> None:
    from vitrine import portfolio_menu

    view = SimpleNamespace(
        title="Improvement Portfolio",
        subject_label="Jordan",
        purpose_kind="improvement",
        profile_label="Improvement",
        profile_revision=2,
        subject_links=(),
        candidate_count=0,
        active_selection_count=0,
        current_composition_revision=2,
        current_edition_count=1,
        completed_edition_count=3,
    )
    output = io.StringIO()
    portfolio_menu._render_teacher_portfolio_overview(output, view)
    assert "Current Portfolio Editions: 1" in output.getvalue()
    assert "Completed Portfolio Editions: 3" in output.getvalue()
