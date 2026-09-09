from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.current_portfolio_menu import run_current_portfolio_build_export_menu


def _dependencies() -> SimpleNamespace:
    return SimpleNamespace(
        snapshot_source_providers=object(),
        snapshot_build_authority_gate=object(),
    )


def _input(values: list[str]):
    pending = iter(values)

    def read(prompt: str) -> str:
        del prompt
        return next(pending)

    return read


def _working(*, disposition: str = "reuse_exact_current") -> SimpleNamespace:
    return SimpleNamespace(
        disposition=disposition,
        unplaced_selection_ids=(),
        audience_rules=(
            SimpleNamespace(
                audience_rule_id="rule_1",
                audience_class="family",
                purpose="showcase",
            ),
        ),
    )


def _preparation(
    *,
    context_disposition: str = "reuse",
    context_matches: tuple[str, ...] = ("context_1",),
    selected_context: str | None = "context_1",
    series_disposition: str = "reuse",
    series_matches: tuple[str, ...] = ("series_1",),
    selected_series: str | None = "series_1",
    unresolved: tuple[str, ...] = (),
    ready: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        audience_context=SimpleNamespace(
            disposition=context_disposition,
            matching_audience_context_ids=context_matches,
            selected_audience_context_id=selected_context,
        ),
        snapshot_series=SimpleNamespace(
            disposition=series_disposition,
            matching_snapshot_series_ids=series_matches,
            selected_snapshot_series_id=selected_series,
        ),
        unresolved_obligation_codes=unresolved,
        ready_for_plan_execution=ready,
    )


def test_stale_working_composition_stops_before_build_preparation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_working_composition",
        lambda *args, **kwargs: _working(disposition="create_successor"),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_current_portfolio_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("prepare")),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.execute_prepared_current_portfolio_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("write")),
    )
    output = StringIO()

    run_current_portfolio_build_export_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_input([]),
        output=output,
        dependencies=_dependencies(),
    )

    text = output.getvalue()
    assert "create_successor" in text
    assert "Return to Working Composition" in text
    assert "Nothing was written" in text


def test_menu_requires_exact_context_series_and_obligation_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = _dependencies()
    calls: list[dict[str, object]] = []
    preparations = iter(
        (
            _preparation(
                context_disposition="requires_choice",
                context_matches=("context_a", "context_b"),
                selected_context=None,
                series_disposition="requires_choice",
                series_matches=(),
                selected_series=None,
            ),
            _preparation(
                selected_context="context_b",
                series_disposition="requires_choice",
                series_matches=("series_a", "series_b"),
                selected_series=None,
                unresolved=("obligation_a",),
                ready=False,
            ),
            _preparation(
                selected_context="context_b",
                selected_series="series_a",
                unresolved=("obligation_a",),
                ready=False,
            ),
            _preparation(
                selected_context="context_b",
                selected_series="series_a",
                unresolved=("obligation_a",),
                ready=True,
            ),
        )
    )
    final_preparation: dict[str, object] = {}
    executed: dict[str, object] = {}

    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_working_composition",
        lambda *args, **kwargs: _working(),
    )

    def fake_prepare(*args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        value = next(preparations)
        final_preparation["value"] = value
        return value

    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_current_portfolio_build",
        fake_prepare,
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.print_current_portfolio_preparation",
        lambda *args, **kwargs: None,
    )

    def fake_execute(*args: object, **kwargs: object) -> object:
        executed["args"] = args
        executed["kwargs"] = kwargs
        return SimpleNamespace(
            snapshot_series_id="series_a",
            edition_number=1,
            snapshot_export_artifact_id="export_1",
            export_disposition="created",
            export_path=tmp_path / "export",
        )

    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.execute_prepared_current_portfolio_build",
        fake_execute,
    )

    output = StringIO()
    run_current_portfolio_build_export_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_input(
            [
                "1",  # Audience Rule
                "2",  # exact Audience Context context_b
                "1",  # exact Snapshot Series series_a
                "ACKNOWLEDGE OBLIGATIONS",
                "BUILD AND EXPORT CURRENT PORTFOLIO",
                "teacher_1",
            ]
        ),
        output=output,
        dependencies=dependencies,
    )

    assert len(calls) == 4
    assert calls[1]["audience_context_id"] == "context_b"
    assert calls[1]["snapshot_series_id"] is None
    assert calls[2]["audience_context_id"] == "context_b"
    assert calls[2]["snapshot_series_id"] == "series_a"
    assert calls[3]["acknowledged_obligation_codes"] == ("obligation_a",)
    assert executed["args"] == (tmp_path, final_preparation["value"])
    kwargs = executed["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["authority_gate"] is dependencies.snapshot_build_authority_gate
    assert kwargs["source_providers"] is dependencies.snapshot_source_providers
    assert kwargs["actor"].actor_id == "teacher_1"
    text = output.getvalue()
    assert "Acknowledging them allows the Snapshot Plan" in text
    assert "Current Edition pointer advanced: no" in text
    assert "not disclosure permission or delivery" in text


def test_menu_declined_final_confirmation_performs_no_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_working_composition",
        lambda *args, **kwargs: _working(),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.prepare_current_portfolio_build",
        lambda *args, **kwargs: _preparation(),
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.print_current_portfolio_preparation",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "vitrine.current_portfolio_menu.execute_prepared_current_portfolio_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("write")),
    )
    output = StringIO()

    run_current_portfolio_build_export_menu(
        root=tmp_path,
        portfolio_id="portfolio_1",
        input_fn=_input(["1", "NO"]),
        output=output,
        dependencies=_dependencies(),
    )

    assert "Build/export cancelled. Nothing was written." in output.getvalue()
