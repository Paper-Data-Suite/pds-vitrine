from __future__ import annotations

from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.current_portfolio_execution import (
    CurrentPortfolioBuildExportResult,
    CurrentPortfolioExecutionError,
    execute_prepared_current_portfolio_build,
    resume_current_portfolio_presentation,
)
from vitrine.models import ActorAttribution
from vitrine.portfolio_presentation_services import (
    PortfolioPresentationBuildError,
    PortfolioPresentationBuildResult,
)
from vitrine.snapshot_materialization import SnapshotSourceProviderRegistry

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)


def _snapshot_result() -> CurrentPortfolioBuildExportResult:
    return CurrentPortfolioBuildExportResult(
        contract_version="vitrine_build_export_current_portfolio_v1",
        preparation_fingerprint="a" * 64,
        state_revision=20,
        audience_context_id="audience_1",
        snapshot_series_id="series_1",
        snapshot_build_request_id="request_1",
        snapshot_build_plan_id="plan_1",
        snapshot_build_attempt_id="attempt_1",
        attempt_number=1,
        attempt_terminal_outcome="sealed",
        edition_number=2,
        edition_manifest_sha256="b" * 64,
        edition_logical_inventory_sha256="c" * 64,
        snapshot_export_artifact_id="export_1",
        export_disposition="created",
        export_directory_inventory_sha256="d" * 64,
        export_path=Path("exports/exact"),
    )


def _presentation_result() -> PortfolioPresentationBuildResult:
    return PortfolioPresentationBuildResult(
        state_revision=21,
        presentation_artifact_id="presentation_1",
        disposition="created",
        relative_path="presentations-bounded-v1/vp1_0123456789abcdef01234567",
        html_relative_path=(
            "presentations-bounded-v1/vp1_0123456789abcdef01234567/portfolio.html"
        ),
        printable_pdf_relative_path=(
            "presentations-bounded-v1/vp1_0123456789abcdef01234567/portfolio.pdf"
        ),
        presentation_manifest_sha256="e" * 64,
        package_inventory_sha256="f" * 64,
        verified_file_paths=("portfolio.html", "portfolio.pdf"),
    )


def test_prepared_student_portfolio_build_continues_through_presentation_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    preparation = SimpleNamespace(
        selected_audience_rule=SimpleNamespace(
            presentation_class="student_portfolio"
        )
    )
    plan = SimpleNamespace()
    registry = SnapshotSourceProviderRegistry()
    monkeypatch.setattr(
        module,
        "execute_prepared_current_portfolio_plan",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        module,
        "execute_current_portfolio_build_export",
        lambda *_args, **_kwargs: _snapshot_result(),
    )
    calls: list[tuple[str, int, str]] = []

    def build(*_args, **kwargs):
        calls.append(
            (
                kwargs["snapshot_series_id"],
                kwargs["edition_number"],
                kwargs["snapshot_export_artifact_id"],
            )
        )
        assert kwargs["generated_by"] is ACTOR
        return _presentation_result()

    monkeypatch.setattr(module, "build_student_portfolio_presentation", build)

    result = execute_prepared_current_portfolio_build(
        ".",
        preparation,  # type: ignore[arg-type]
        actor=ACTOR,
        authority_gate=SimpleNamespace(),
        source_providers=registry,
    )

    assert calls == [("series_1", 2, "export_1")]
    assert result.state_revision == 21
    assert result.presentation_disposition == "created"
    assert result.presentation_artifact_id == "presentation_1"
    assert result.presentation_verified is True
    assert result.current_pointer_advanced is False


def test_presentation_failure_reports_durable_snapshot_export_resume_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    preparation = SimpleNamespace(
        selected_audience_rule=SimpleNamespace(
            presentation_class="student_portfolio"
        )
    )
    monkeypatch.setattr(
        module,
        "execute_prepared_current_portfolio_plan",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        module,
        "execute_current_portfolio_build_export",
        lambda *_args, **_kwargs: _snapshot_result(),
    )

    def fail(*_args, **_kwargs):
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.package_failed",
            "synthetic presentation failure",
            stage="package",
            underlying_code="portfolio_presentation_package.render_failed",
            underlying_stage="pdf",
            presentation_artifact_id="presentation_1",
            next_safe_action="resume_presentation_existing_edition",
        )

    monkeypatch.setattr(module, "build_student_portfolio_presentation", fail)

    with pytest.raises(CurrentPortfolioExecutionError) as caught:
        execute_prepared_current_portfolio_build(
            ".",
            preparation,  # type: ignore[arg-type]
            actor=ACTOR,
            authority_gate=SimpleNamespace(),
        )

    assert caught.value.code == "current_portfolio_build.presentation_failed"
    assert caught.value.edition_number == 2
    assert caught.value.snapshot_export_artifact_id == "export_1"
    assert "export_verification" in caught.value.completed_stages
    assert caught.value.next_safe_action == "resume_presentation_existing_edition"


def test_non_student_presentation_class_is_explicitly_unsupported_without_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    preparation = SimpleNamespace(
        selected_audience_rule=SimpleNamespace(presentation_class="showcase")
    )
    monkeypatch.setattr(
        module,
        "execute_prepared_current_portfolio_plan",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        module,
        "execute_current_portfolio_build_export",
        lambda *_args, **_kwargs: _snapshot_result(),
    )
    monkeypatch.setattr(
        module,
        "build_student_portfolio_presentation",
        lambda *_args, **_kwargs: pytest.fail("showcase must not use student renderer"),
    )

    result = execute_prepared_current_portfolio_build(
        ".",
        preparation,  # type: ignore[arg-type]
        actor=ACTOR,
        authority_gate=SimpleNamespace(),
    )

    assert result.presentation_disposition == "unsupported"
    assert result.presentation_artifact_id is None
    assert result.presentation_verified is False


def test_resume_presentation_uses_only_exact_durable_edition_and_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.current_portfolio_execution as module

    expected = _presentation_result()
    calls: list[tuple[str, int, str]] = []

    def resume(*_args, **kwargs):
        calls.append(
            (
                kwargs["snapshot_series_id"],
                kwargs["edition_number"],
                kwargs["snapshot_export_artifact_id"],
            )
        )
        assert kwargs["generated_by"] is ACTOR
        return expected

    monkeypatch.setattr(module, "resume_student_portfolio_presentation", resume)

    result = resume_current_portfolio_presentation(
        ".",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        actor=ACTOR,
    )

    assert result is expected
    assert calls == [("series_1", 2, "export_1")]

def test_teacher_completion_summary_leads_with_student_portfolio_availability() -> None:
    from vitrine.current_portfolio_menu import _print_result

    result = replace(
        _snapshot_result(),
        state_revision=21,
        presentation_disposition="created",
        presentation_artifact_id="presentation_1",
        presentation_relative_path=(
            "presentations-bounded-v1/vp1_0123456789abcdef01234567"
        ),
        presentation_html_relative_path=(
            "presentations-bounded-v1/vp1_0123456789abcdef01234567/portfolio.html"
        ),
        presentation_pdf_relative_path=(
            "presentations-bounded-v1/vp1_0123456789abcdef01234567/portfolio.pdf"
        ),
        presentation_verified=True,
    )
    output = StringIO()

    _print_result(result, output)

    text = output.getvalue()
    assert "Student Portfolio:" in text
    assert "Digital Portfolio: available" in text
    assert "Printable Portfolio: available" in text
    assert "Student files: available" in text
    assert "Technical custody package:" in text
    assert "preserved and verified" in text
    assert "has not been delivered or sent" in text
    assert "SHA-256" not in text
    assert "presentation_1" not in text
