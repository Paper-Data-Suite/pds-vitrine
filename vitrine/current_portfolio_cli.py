"""Direct CLI surface for Build and Export Current Portfolio."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TextIO

from vitrine.current_portfolio_build import (
    CurrentPortfolioBuildPreparation,
    prepare_current_portfolio_build,
)
from vitrine.current_portfolio_execution import (
    CurrentPortfolioBuildExportResult,
    execute_prepared_current_portfolio_build,
)
from vitrine.current_portfolio_surface import print_current_portfolio_preparation
from vitrine.models import ActorAttribution
from vitrine.workflow_context import VitrineWorkflowDependencies


class CurrentPortfolioCliError(RuntimeError):
    """Stable task-surface validation failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-root", type=Path)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("portfolio_id")
    parser.add_argument("--audience-rule-id", required=True)
    parser.add_argument("--audience-context-id")
    parser.add_argument("--snapshot-series-id")
    parser.add_argument(
        "--acknowledge-obligation",
        action="append",
        default=[],
        metavar="CODE",
        help=(
            "Acknowledge one exact unresolved Composition obligation. Repeat for "
            "the exact reviewed set."
        ),
    )
    _workspace(parser)


def configure_current_portfolio_build_export_parsers(
    portfolios: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    task = portfolios.add_parser(
        "build-export",
        help="Prepare or execute Build and Export Current Portfolio.",
    )
    commands = task.add_subparsers(
        dest="portfolio_build_export_command",
        required=True,
    )

    prepare = commands.add_parser(
        "prepare",
        help="Prepare the exact current Portfolio build/export read-only.",
    )
    _common(prepare)

    execute = commands.add_parser(
        "execute",
        help="Execute one exact reviewed Current Portfolio preparation.",
    )
    _common(execute)
    execute.add_argument("--preparation-fingerprint", required=True)
    execute.add_argument("--expected-state-revision", type=int, required=True)
    execute.add_argument("--actor-id", required=True)
    execute.add_argument(
        "--actor-kind",
        default="authorized_adult",
        choices=("authorized_adult", "system", "external_actor"),
    )
    execute.add_argument("--owning-system", default="local")
    execute.add_argument("--role", default="teacher")


def _prepare(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
) -> CurrentPortfolioBuildPreparation:
    return prepare_current_portfolio_build(
        args.workspace_root,
        args.portfolio_id,
        audience_rule_id=args.audience_rule_id,
        audience_context_id=args.audience_context_id,
        snapshot_series_id=args.snapshot_series_id,
        acknowledged_obligation_codes=tuple(args.acknowledge_obligation),
        source_providers=dependencies.snapshot_source_providers,
    )


def _actor(args: argparse.Namespace) -> ActorAttribution:
    return ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )


def _print_result(result: CurrentPortfolioBuildExportResult, output: TextIO) -> None:
    print("Build and Export Current Portfolio completed.", file=output)
    print(f"Preparation fingerprint: {result.preparation_fingerprint}", file=output)
    print(f"Final Vitrine state revision: {result.state_revision}", file=output)
    print(f"Audience Context: {result.audience_context_id}", file=output)
    print(f"Snapshot Series: {result.snapshot_series_id}", file=output)
    print(f"Snapshot Build Request: {result.snapshot_build_request_id}", file=output)
    print(f"Snapshot Build Plan: {result.snapshot_build_plan_id}", file=output)
    print(f"Snapshot Build Attempt: {result.snapshot_build_attempt_id}", file=output)
    print(f"Attempt outcome: {result.attempt_terminal_outcome}", file=output)
    print(f"Snapshot Edition: {result.edition_number}", file=output)
    print(
        f"Edition Manifest SHA-256: {result.edition_manifest_sha256}",
        file=output,
    )
    print(
        "Edition logical inventory SHA-256: "
        f"{result.edition_logical_inventory_sha256}",
        file=output,
    )
    print(
        f"Snapshot Export Artifact: {result.snapshot_export_artifact_id}",
        file=output,
    )
    print(f"Export disposition: {result.export_disposition}", file=output)
    print(
        "Export directory inventory SHA-256: "
        f"{result.export_directory_inventory_sha256}",
        file=output,
    )
    print(f"Export path: {result.export_path}", file=output)
    print("Current Edition pointer advanced: no", file=output)
    print("Export creation is not disclosure permission or delivery.", file=output)


def run_current_portfolio_build_export_command(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    """Run the direct task surface using the shared preparation/execution boundary."""

    preparation = _prepare(args, dependencies=dependencies)
    print_current_portfolio_preparation(preparation, output=output)
    if args.portfolio_build_export_command == "prepare":
        return 0

    if preparation.observed_state_revision != args.expected_state_revision:
        raise CurrentPortfolioCliError(
            "current_portfolio_build.expected_state_mismatch",
            "Prepared Vitrine state revision differs from --expected-state-revision.",
        )
    if preparation.preparation_fingerprint != args.preparation_fingerprint:
        raise CurrentPortfolioCliError(
            "current_portfolio_build.preparation_fingerprint_mismatch",
            "Current preparation differs from the exact reviewed fingerprint.",
        )
    if not preparation.ready_for_plan_execution:
        raise CurrentPortfolioCliError(
            "current_portfolio_build.preparation_blocked",
            "Current Portfolio preparation has blocking reasons; "
            "no write was attempted.",
        )

    result = execute_prepared_current_portfolio_build(
        args.workspace_root,
        preparation,
        actor=_actor(args),
        authority_gate=dependencies.snapshot_build_authority_gate,
        source_providers=dependencies.snapshot_source_providers,
    )
    _print_result(result, output)
    return 0


__all__ = [
    "CurrentPortfolioCliError",
    "configure_current_portfolio_build_export_parsers",
    "run_current_portfolio_build_export_command",
]
