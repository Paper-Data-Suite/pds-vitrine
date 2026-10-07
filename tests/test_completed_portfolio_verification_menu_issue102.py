"""Issue #102 Slice 4: completed verification and historical Presentation menu."""

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
    CompletedPortfolioSeries,
)
from vitrine.completed_portfolio_actions import CompletedPortfolioActionError
from vitrine.models import ActorAttribution, ProfileRevisionRef

NOW = datetime(2026, 10, 6, 23, 0, tzinfo=timezone.utc)
PROFILE = ProfileRevisionRef(portfolio_profile_id="profile_1", profile_revision=2)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="local",
    role_snapshot="teacher",
)


def _history(*, presentation_class: str = "student_portfolio") -> CompletedPortfolioHistory:
    export = CompletedPortfolioExport(
        snapshot_export_artifact_id="export_private_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        relative_path="exports/private",
        generated_at=NOW - timedelta(days=1),
        predecessor_export_artifact_id=None,
    )
    edition = CompletedPortfolioEdition(
        snapshot_series_id="series_private_1",
        edition_number=2,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=2,
        audience_context_id="audience_1",
        created_at=NOW - timedelta(days=2),
        predecessor_edition=1,
        is_current=False,
        exports=(export,),
        presentations=(),
    )
    series = CompletedPortfolioSeries(
        snapshot_series_id="series_private_1",
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        snapshot_purpose="improvement",
        audience_context_id="audience_1",
        audience_class="student",
        audience_purpose="Student Review",
        presentation_class=presentation_class,
        created_at=NOW - timedelta(days=3),
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


def _inputs(*values: str):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_historical_student_presentation_action_is_offered_without_ids() -> None:
    history = _history()
    series = history.series[0]
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
        "open_technical_export",
        "verify_portfolio",
        "create_student_presentation",
        "artifact_history",
        "technical_details",
    )
    rendered = output.getvalue()
    assert "Verify Portfolio Now" in rendered
    assert "Create Student Portfolio Presentation" in rendered
    assert "Student Portfolio: not created yet" in rendered
    assert "series_private_1" not in rendered
    assert "export_private_1" not in rendered


def test_unsupported_class_explains_unavailability_and_does_not_offer_create() -> None:
    history = _history(presentation_class="showcase")
    series = history.series[0]
    edition = series.editions[0]
    output = io.StringIO()

    actions = menu._render_edition_detail(
        output,
        edition=edition,
        series=series,
        series_label="Showcase",
        portfolio_label="Jordan — Portfolio",
    )

    assert "create_student_presentation" not in actions
    assert "not available for this presentation class" in output.getvalue()


def test_verify_action_reports_verified_now_without_technical_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _history().series[0].editions[0]
    monkeypatch.setattr(
        menu,
        "verify_completed_portfolio_edition",
        lambda *_args, **_kwargs: SimpleNamespace(
            verified_export_count=1,
            verified_student_presentation_count=0,
        ),
    )
    output = io.StringIO()

    menu._run_verify_action(
        root=tmp_path,
        portfolio_id="portfolio_1",
        edition=edition,
        output=output,
        clear_fn=lambda: None,
        input_fn=_inputs(""),
    )

    rendered = output.getvalue()
    assert "Portfolio verification passed." in rendered
    assert "Edition: verified" in rendered
    assert "Technical Export: verified" in rendered
    assert "Student Portfolio: none recorded" in rendered
    assert "export_private_1" not in rendered


def test_verification_failure_is_bounded_and_hides_private_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _history().series[0].editions[0]

    def fail(*_args: object, **_kwargs: object):
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.verification_failed",
            "C:/private/custody/changed",
            stage="verification",
        )

    monkeypatch.setattr(menu, "verify_completed_portfolio_edition", fail)
    output = io.StringIO()

    menu._run_verify_action(
        root=tmp_path,
        portfolio_id="portfolio_1",
        edition=edition,
        output=output,
        clear_fn=lambda: None,
        input_fn=_inputs(""),
    )

    rendered = output.getvalue()
    assert "no longer matches its verified saved state" in rendered
    assert "Nothing was changed automatically." in rendered
    assert "C:/private/custody" not in rendered


def test_create_action_uses_exact_export_actor_and_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _history().series[0].editions[0]
    calls: list[dict[str, object]] = []

    def create(_root: Path, **kwargs: object):
        calls.append(kwargs)
        return SimpleNamespace(disposition="created")

    monkeypatch.setattr(
        menu,
        "create_historical_student_portfolio_presentation",
        create,
    )
    output = io.StringIO()

    menu._run_create_presentation_action(
        root=tmp_path,
        portfolio_id="portfolio_1",
        edition=edition,
        actor=ACTOR,
        input_fn=_inputs("CREATE PRESENTATION", ""),
        output=output,
        clear_fn=lambda: None,
    )

    assert calls == [
        {
            "portfolio_id": "portfolio_1",
            "snapshot_series_id": "series_private_1",
            "edition_number": 2,
            "snapshot_export_artifact_id": "export_private_1",
            "generated_by": ACTOR,
        }
    ]
    rendered = output.getvalue()
    assert "Student Portfolio Presentation is available and verified." in rendered
    assert "current Working Composition was not reread" in rendered
    assert "export_private_1" not in rendered
