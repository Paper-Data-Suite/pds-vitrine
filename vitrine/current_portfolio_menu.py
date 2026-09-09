"""Teacher menu for Build and Export Current Portfolio."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TextIO, TypeVar

from vitrine.current_portfolio_build import (
    CurrentPortfolioBuildPreparation,
    prepare_current_portfolio_build,
)
from vitrine.current_portfolio_execution import (
    CurrentPortfolioBuildExportResult,
    CurrentPortfolioExecutionError,
    execute_prepared_current_portfolio_build,
)
from vitrine.current_portfolio_surface import print_current_portfolio_preparation
from vitrine.menu_types import InputFunction
from vitrine.models import ActorAttribution
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.working_composition import prepare_working_composition

T = TypeVar("T")


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "B"


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _choose(
    values: tuple[T, ...],
    *,
    input_fn: InputFunction,
    output: TextIO,
    label: str,
    render: Callable[[T], str],
) -> T | None:
    if not values:
        return None
    for index, value in enumerate(values, 1):
        _write(output, f"{index}. {render(value)}")
    raw = _read(input_fn, f"{label} number (B to cancel): ")
    if raw.upper() == "B":
        return None
    if not raw.isdecimal():
        _write(output, f"That {label} number is not available.")
        return None
    index = int(raw)
    if index < 1 or index > len(values):
        _write(output, f"That {label} number is not available.")
        return None
    return values[index - 1]


def _actor(input_fn: InputFunction) -> ActorAttribution | None:
    actor_id = _read(input_fn, "Teacher/actor ID (B to cancel): ")
    if actor_id.upper() == "B" or not actor_id:
        return None
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id=actor_id,
        owning_system="local",
        role_snapshot="teacher",
    )


def _prepare(
    *,
    root: Path,
    portfolio_id: str,
    audience_rule_id: str,
    audience_context_id: str | None,
    snapshot_series_id: str | None,
    acknowledged_obligation_codes: tuple[str, ...],
    dependencies: VitrineWorkflowDependencies,
) -> CurrentPortfolioBuildPreparation:
    return prepare_current_portfolio_build(
        root,
        portfolio_id,
        audience_rule_id=audience_rule_id,
        audience_context_id=audience_context_id,
        snapshot_series_id=snapshot_series_id,
        acknowledged_obligation_codes=acknowledged_obligation_codes,
        source_providers=dependencies.snapshot_source_providers,
    )


def _resolve_exact_choices(
    preparation: CurrentPortfolioBuildPreparation,
    *,
    root: Path,
    portfolio_id: str,
    audience_rule_id: str,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
) -> CurrentPortfolioBuildPreparation | None:
    audience_context_id = preparation.audience_context.selected_audience_context_id
    snapshot_series_id = preparation.snapshot_series.selected_snapshot_series_id

    if preparation.audience_context.disposition == "requires_choice":
        _write(
            output,
            "",
            "More than one exact Audience Context matches. Choose one explicitly.",
        )
        selected = _choose(
            preparation.audience_context.matching_audience_context_ids,
            input_fn=input_fn,
            output=output,
            label="Audience Context",
            render=lambda value: value,
        )
        if selected is None:
            return None
        audience_context_id = selected
        preparation = _prepare(
            root=root,
            portfolio_id=portfolio_id,
            audience_rule_id=audience_rule_id,
            audience_context_id=audience_context_id,
            snapshot_series_id=None,
            acknowledged_obligation_codes=(),
            dependencies=dependencies,
        )

    if preparation.snapshot_series.disposition == "requires_choice":
        _write(
            output,
            "",
            "More than one exact Snapshot Series matches. Choose one explicitly.",
        )
        selected_series = _choose(
            preparation.snapshot_series.matching_snapshot_series_ids,
            input_fn=input_fn,
            output=output,
            label="Snapshot Series",
            render=lambda value: value,
        )
        if selected_series is None:
            return None
        snapshot_series_id = selected_series
        preparation = _prepare(
            root=root,
            portfolio_id=portfolio_id,
            audience_rule_id=audience_rule_id,
            audience_context_id=audience_context_id,
            snapshot_series_id=snapshot_series_id,
            acknowledged_obligation_codes=(),
            dependencies=dependencies,
        )
    return preparation


def _acknowledge_obligations(
    preparation: CurrentPortfolioBuildPreparation,
    *,
    root: Path,
    portfolio_id: str,
    audience_rule_id: str,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
) -> CurrentPortfolioBuildPreparation | None:
    unresolved = preparation.unresolved_obligation_codes
    if not unresolved:
        return preparation
    _write(output, "", "These Composition obligations remain unresolved:")
    for code in unresolved:
        _write(output, f"- {code}")
    _write(
        output,
        "",
        "Acknowledging them allows the Snapshot Plan to preserve that state.",
        "It does not satisfy, clear, approve, or authorize disclosure.",
    )
    if (
        _read(
            input_fn,
            "Type ACKNOWLEDGE OBLIGATIONS to continue: ",
        )
        != "ACKNOWLEDGE OBLIGATIONS"
    ):
        _write(output, "Obligations were not acknowledged. Nothing was written.")
        return None
    return _prepare(
        root=root,
        portfolio_id=portfolio_id,
        audience_rule_id=audience_rule_id,
        audience_context_id=preparation.audience_context.selected_audience_context_id,
        snapshot_series_id=preparation.snapshot_series.selected_snapshot_series_id,
        acknowledged_obligation_codes=unresolved,
        dependencies=dependencies,
    )


def _print_result(result: CurrentPortfolioBuildExportResult, output: TextIO) -> None:
    _write(
        output,
        "",
        "Build and Export Current Portfolio completed.",
        f"Snapshot Series: {result.snapshot_series_id}",
        f"Snapshot Edition: {result.edition_number}",
        f"Snapshot Export Artifact: {result.snapshot_export_artifact_id}",
        f"Export disposition: {result.export_disposition}",
        f"Export path: {result.export_path}",
        "Current Edition pointer advanced: no",
        "Export creation is not disclosure permission or delivery.",
    )


def _print_execution_error(
    error: CurrentPortfolioExecutionError, output: TextIO
) -> None:
    _write(
        output,
        "",
        f"Build/export stopped: {error.code}",
        f"Stage: {error.stage}",
    )
    if error.underlying_code is not None:
        _write(output, f"Underlying Snapshot code: {error.underlying_code}")
    if error.underlying_stage is not None:
        _write(output, f"Underlying Snapshot stage: {error.underlying_stage}")
    if error.snapshot_build_attempt_id is not None:
        _write(output, f"Durable Attempt: {error.snapshot_build_attempt_id}")
    if error.edition_number is not None:
        _write(output, f"Durable Edition number: {error.edition_number}")
    if error.snapshot_export_artifact_id is not None:
        _write(output, f"Durable Export Artifact: {error.snapshot_export_artifact_id}")
    if error.next_safe_action is not None:
        _write(output, f"Next safe action: {error.next_safe_action}")
    _write(output, "No successor source or current Edition was inferred.")


def run_current_portfolio_build_export_menu(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None = None,
) -> None:
    """Prepare, explicitly confirm, and execute the first-party Current Portfolio."""

    try:
        working = prepare_working_composition(root, portfolio_id)
        if working.disposition != "reuse_exact_current":
            _write(
                output,
                "Build and Export Current Portfolio",
                "",
                "The exact current Working Composition is not ready for building.",
                f"Working Composition disposition: {working.disposition}",
                "Return to Working Composition, freeze the exact current curation,",
                "then prepare this build again. Nothing was written.",
            )
            return
        if working.unplaced_selection_ids:
            _write(
                output,
                "Build and Export Current Portfolio",
                "",
                "Active Selections remain unplaced:",
                *tuple(f"- {item}" for item in working.unplaced_selection_ids),
                "Place, replace, or withdraw them and freeze Working Composition.",
                "Nothing was written.",
            )
            return
        if not working.audience_rules:
            _write(output, "No Audience Rules are available in the bound Profile.")
            return

        _write(
            output,
            "Build and Export Current Portfolio",
            "",
            "Choose one exact Audience Rule from the bound Profile Revision.",
            "The Audience Rule constrains content; it does not identify a recipient.",
        )
        rule = _choose(
            working.audience_rules,
            input_fn=input_fn,
            output=output,
            label="Audience Rule",
            render=lambda value: (
                f"{value.audience_rule_id} — {value.audience_class} / {value.purpose}"
            ),
        )
        if rule is None:
            return

        preparation = _prepare(
            root=root,
            portfolio_id=portfolio_id,
            audience_rule_id=rule.audience_rule_id,
            audience_context_id=None,
            snapshot_series_id=None,
            acknowledged_obligation_codes=(),
            dependencies=dependencies,
        )
        resolved_preparation = _resolve_exact_choices(
            preparation,
            root=root,
            portfolio_id=portfolio_id,
            audience_rule_id=rule.audience_rule_id,
            input_fn=input_fn,
            output=output,
            dependencies=dependencies,
        )
        if resolved_preparation is None:
            return
        acknowledged_preparation = _acknowledge_obligations(
            resolved_preparation,
            root=root,
            portfolio_id=portfolio_id,
            audience_rule_id=rule.audience_rule_id,
            input_fn=input_fn,
            output=output,
            dependencies=dependencies,
        )
        if acknowledged_preparation is None:
            return
        preparation = acknowledged_preparation

        _write(output, "")
        print_current_portfolio_preparation(preparation, output=output)
        if not preparation.ready_for_plan_execution:
            _write(
                output,
                "",
                "This preparation is blocked. Nothing was written.",
                "Correct Working Composition, Review, source, or Reflection state",
                "shown above, then prepare again.",
            )
            return

        _write(
            output,
            "",
            "Final confirmation",
            "This will create/reuse canonical Snapshot workflow records, acquire",
            "only authorized planned bytes, seal an immutable Edition, verify it,",
            "and create/verify a local directory Export.",
            "It will not advance the current Edition pointer or deliver the Export.",
        )
        if (
            _read(
                input_fn,
                "Type BUILD AND EXPORT CURRENT PORTFOLIO to continue: ",
            )
            != "BUILD AND EXPORT CURRENT PORTFOLIO"
        ):
            _write(output, "Build/export cancelled. Nothing was written.")
            return
        mutation_actor = actor or _actor(input_fn)
        if mutation_actor is None:
            _write(output, "Build/export cancelled. No actor was supplied.")
            return

        result = execute_prepared_current_portfolio_build(
            root,
            preparation,
            actor=mutation_actor,
            authority_gate=dependencies.snapshot_build_authority_gate,
            source_providers=dependencies.snapshot_source_providers,
        )
        _print_result(result, output)
    except CurrentPortfolioExecutionError as error:
        _print_execution_error(error, output)
    except RuntimeError as error:
        code = getattr(error, "code", error.__class__.__name__)
        _write(output, f"Build/export preparation stopped: {code}", str(error))


__all__ = ["run_current_portfolio_build_export_menu"]
