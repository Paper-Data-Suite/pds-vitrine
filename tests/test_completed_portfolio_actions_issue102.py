"""Issue #102 Slice 4: verification and historical Presentation services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from vitrine import completed_portfolio_actions as actions
from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
)
from vitrine.models import ActorAttribution, ProfileRevisionRef
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
)

NOW = datetime(2026, 10, 6, 23, 0, tzinfo=timezone.utc)
PROFILE = ProfileRevisionRef(portfolio_profile_id="profile_1", profile_revision=2)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="local",
    role_snapshot="teacher",
)


def _export(identity: str = "export_1") -> CompletedPortfolioExport:
    return CompletedPortfolioExport(
        snapshot_export_artifact_id=identity,
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        relative_path=f"exports/{identity}",
        generated_at=NOW - timedelta(days=2),
        predecessor_export_artifact_id=None,
    )


def _presentation(identity: str = "presentation_1") -> CompletedPortfolioPresentation:
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
        generated_at=NOW - timedelta(days=1),
        predecessor_presentation_artifact_id=None,
    )


def _history(
    *,
    presentation_class: str = "student_portfolio",
    presentations: tuple[CompletedPortfolioPresentation, ...] = (),
    exports: tuple[CompletedPortfolioExport, ...] = (_export(),),
) -> CompletedPortfolioHistory:
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
        is_current=False,
        exports=exports,
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
        presentation_class=presentation_class,
        created_at=NOW - timedelta(days=4),
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


def _install_history(
    monkeypatch: pytest.MonkeyPatch,
    history: CompletedPortfolioHistory,
) -> None:
    monkeypatch.setattr(
        actions,
        "load_current_records_with_state",
        lambda *_args: (SimpleNamespace(state_revision=31), ()),
    )
    monkeypatch.setattr(
        actions,
        "project_completed_portfolio_history",
        lambda _records, *, portfolio_id: history,
    )


def test_verify_completed_edition_verifies_all_recorded_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = _history(
        presentations=(_presentation("presentation_1"), _presentation("presentation_2")),
        exports=(_export("export_1"), _export("export_2")),
    )
    _install_history(monkeypatch, history)
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        actions,
        "verify_snapshot_edition",
        lambda _root, **kwargs: calls.append(("edition", kwargs)),
    )
    monkeypatch.setattr(
        actions,
        "verify_snapshot_export",
        lambda _root, **kwargs: calls.append(("export", kwargs)),
    )
    monkeypatch.setattr(
        actions,
        "verify_portfolio_presentation",
        lambda _root, **kwargs: calls.append(("presentation", kwargs)),
    )

    result = actions.verify_completed_portfolio_edition(
        ".",
        portfolio_id="portfolio_1",
        snapshot_series_id="series_1",
        edition_number=2,
    )

    assert result.verified_export_count == 2
    assert result.verified_student_presentation_count == 2
    assert calls[0][0] == "edition"
    assert [item[0] for item in calls].count("export") == 2
    assert [item[0] for item in calls].count("presentation") == 2


def test_verification_failure_is_wrapped_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_history(monkeypatch, _history(presentations=(_presentation(),)))
    monkeypatch.setattr(actions, "verify_snapshot_edition", lambda *_a, **_k: None)
    monkeypatch.setattr(actions, "verify_snapshot_export", lambda *_a, **_k: None)

    def fail(*_args: object, **_kwargs: object):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "changed",
            stage="verification",
        )

    monkeypatch.setattr(actions, "verify_portfolio_presentation", fail)
    built: list[object] = []
    monkeypatch.setattr(
        actions,
        "build_student_portfolio_presentation",
        lambda *_args, **_kwargs: built.append(object()),
    )

    with pytest.raises(actions.CompletedPortfolioActionError) as caught:
        actions.verify_completed_portfolio_edition(
            ".",
            portfolio_id="portfolio_1",
            snapshot_series_id="series_1",
            edition_number=2,
        )

    assert caught.value.code == "completed_portfolio_action.verification_failed"
    assert caught.value.underlying_code == (
        "portfolio_presentation_verification.file_mismatch"
    )
    assert built == []


def test_existing_presentation_is_not_treated_as_create_or_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_history(monkeypatch, _history(presentations=(_presentation(),)))
    built: list[object] = []
    monkeypatch.setattr(
        actions,
        "build_student_portfolio_presentation",
        lambda *_args, **_kwargs: built.append(object()),
    )

    with pytest.raises(actions.CompletedPortfolioActionError) as caught:
        actions.create_historical_student_portfolio_presentation(
            ".",
            portfolio_id="portfolio_1",
            snapshot_series_id="series_1",
            edition_number=2,
            snapshot_export_artifact_id="export_1",
            generated_by=ACTOR,
        )

    assert caught.value.code == "completed_portfolio_action.presentation_exists"
    assert built == []


def test_historical_creation_reuses_exact_issue101_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_history(monkeypatch, _history())
    verified: list[tuple[str, object]] = []
    monkeypatch.setattr(
        actions,
        "verify_snapshot_edition",
        lambda _root, **kwargs: verified.append(("edition", kwargs)),
    )
    monkeypatch.setattr(
        actions,
        "verify_snapshot_export",
        lambda _root, **kwargs: verified.append(("export", kwargs)),
    )
    expected = SimpleNamespace(disposition="created", presentation_artifact_id="p1")
    calls: list[dict[str, object]] = []

    def build(_root: object, **kwargs: object):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(actions, "build_student_portfolio_presentation", build)

    result = actions.create_historical_student_portfolio_presentation(
        ".",
        portfolio_id="portfolio_1",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        generated_by=ACTOR,
    )

    assert result is expected
    assert calls == [
        {
            "snapshot_series_id": "series_1",
            "edition_number": 2,
            "snapshot_export_artifact_id": "export_1",
            "generated_by": ACTOR,
        }
    ]
    assert [item[0] for item in verified] == ["edition", "export"]


def test_unsupported_presentation_class_is_not_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = _history(presentation_class="showcase")
    _install_history(monkeypatch, history)
    series = history.series[0]
    edition = series.editions[0]
    assert not actions.historical_student_presentation_available(series, edition)

    with pytest.raises(actions.CompletedPortfolioActionError) as caught:
        actions.create_historical_student_portfolio_presentation(
            ".",
            portfolio_id="portfolio_1",
            snapshot_series_id="series_1",
            edition_number=2,
            snapshot_export_artifact_id="export_1",
            generated_by=ACTOR,
        )
    assert caught.value.code == "completed_portfolio_action.presentation_unavailable"
