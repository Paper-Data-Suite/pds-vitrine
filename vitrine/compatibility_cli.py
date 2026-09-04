"""Direct, read-only CLI presentation for cross-producer compatibility diagnostics."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import TextIO, cast

from pds_core.publication_compatibility import PublicationProducerRegistry
from pds_core.workspace import WorkspaceRootError

from vitrine.compatibility_diagnostics import (
    CrossProducerCompatibilityDiagnostic,
    ProducerIntegrationReadiness,
    diagnose_installed_producer_readiness,
    explain_live_adapter_support,
)
from vitrine.producer_adapters import (
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterRegistry,
)
from vitrine.producer_reader_services import (
    SourceReadAuthorizationGate as SharedSourceReadAuthorizationGate,
)
from vitrine.publication_diagnostics import (
    PublicationCompatibilityDiagnostics,
    PublicationReadProbeDiagnostics,
    diagnose_publication_compatibility,
    diagnose_publication_read_probe,
)
from vitrine.workflow_context import (
    VitrineWorkflowDependencies,
    default_workflow_dependencies,
)
from vitrine.workspace import show_workspace


def configure_compatibility_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Configure read-only compatibility commands without resolving a workspace."""

    parser = subparsers.add_parser(
        "compatibility",
        help="Explain live producer compatibility and unsupported-contract diagnostics.",
    )
    commands = parser.add_subparsers(dest="compatibility_command", required=True)

    commands.add_parser(
        "producers",
        help="Inspect installed readiness for the audited live producer integrations.",
    )

    contract = commands.add_parser(
        "contract",
        help="Explain one explicit semantic producer support request without workspace I/O.",
    )
    contract.add_argument("--producer", required=True)
    contract.add_argument("--core-publication-schema-version", required=True)
    contract.add_argument("--publication-kind", required=True)
    contract.add_argument("--manifest-contract-version", required=True)
    contract.add_argument("--producer-contract-version")
    contract.add_argument("--source-record-kind")
    contract.add_argument("--source-record-contract-version")
    contract.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Core Publication capability; repeat for multiple capabilities.",
    )

    publication = commands.add_parser(
        "publication",
        help="Diagnose one explicit canonical Core Publication without mutation.",
    )
    publication.add_argument("publication_id")
    publication.add_argument("--workspace-root", type=Path)
    publication.add_argument(
        "--verify-read",
        action="store_true",
        help=(
            "After metadata compatibility succeeds, request source authorization, "
            "verify the manifest, invoke the audited public reader, and run pure "
            "projection."
        ),
    )
    publication.add_argument("--portfolio-id")
    publication.add_argument("--portfolio-subject-id")
    publication.add_argument("--purpose")


def _field_map(
    diagnostic: CrossProducerCompatibilityDiagnostic,
) -> dict[str, str]:
    return dict(diagnostic.safe_fields)


def _print_diagnostic(
    diagnostic: CrossProducerCompatibilityDiagnostic,
    *,
    output: TextIO,
) -> None:
    """Render one already-sanitized diagnostic without consulting source state."""

    print(f"Status: {diagnostic.outcome}", file=output)
    if diagnostic.producer_module_id is not None:
        print(f"Producer: {diagnostic.producer_module_id}", file=output)
    if diagnostic.publication_id is not None:
        print(f"Publication: {diagnostic.publication_id}", file=output)
    if diagnostic.adapter_id is not None:
        print(f"Adapter: {diagnostic.adapter_id}", file=output)
    print(f"Stage: {diagnostic.stage}", file=output)
    print("Why:", file=output)
    print(diagnostic.summary, file=output)
    print("Technical:", file=output)
    print(diagnostic.code, file=output)
    if diagnostic.reason_codes:
        print(f"Reasons: {', '.join(diagnostic.reason_codes)}", file=output)

    fields = _field_map(diagnostic)
    actual_expected = tuple(
        (key, value)
        for key, value in diagnostic.safe_fields
        if key.startswith("actual_") or key.startswith("expected_")
    )
    if actual_expected:
        print("Contract details:", file=output)
        for key, value in actual_expected:
            print(f"{key}: {value}", file=output)

    if fields.get("protected_source_inspected") == "no":
        print("Protected source inspected: no", file=output)
    if fields.get("artifact_bytes_acquired") == "no":
        print("Artifact bytes acquired: no", file=output)

    print("Next action:", file=output)
    print(diagnostic.next_action, file=output)


def _stage_outcome(
    report: ProducerIntegrationReadiness,
    stage: str,
) -> str:
    match = next((item for item in report.checks if item.stage == stage), None)
    return "not_checked" if match is None else match.outcome


def _print_producer_readiness(
    reports: tuple[ProducerIntegrationReadiness, ...],
    *,
    output: TextIO,
) -> None:
    print(
        "producer\tstatus\tadapter\tcore_profile\treader_distribution\t"
        "reader_api\tartifact_api\ttechnical",
        file=output,
    )
    for report in sorted(reports, key=lambda item: item.producer_module_id):
        print(
            "\t".join(
                (
                    report.producer_module_id,
                    report.overall.outcome,
                    _stage_outcome(report, "adapter_registry"),
                    _stage_outcome(report, "core_profile"),
                    _stage_outcome(report, "reader_distribution"),
                    _stage_outcome(report, "reader_api"),
                    _stage_outcome(report, "artifact_api"),
                    report.overall.code,
                )
            ),
            file=output,
        )


def _print_publication_report(
    report: PublicationCompatibilityDiagnostics | PublicationReadProbeDiagnostics,
    *,
    output: TextIO,
) -> None:
    _print_diagnostic(report.overall, output=output)
    print("Checks:", file=output)
    for check in report.checks:
        print(f"{check.stage}\t{check.outcome}\t{check.code}", file=output)
        fields = _field_map(check)
        if fields.get("protected_source_inspected") == "no":
            print("Protected source inspected: no", file=output)
    if isinstance(report, PublicationReadProbeDiagnostics):
        if report.projected_source_count is not None:
            print(f"Projected source count: {report.projected_source_count}", file=output)


def _safe_failure(error: BaseException, *, output: TextIO) -> int:
    """Never print arbitrary exception text from producer/integration failures."""

    code = getattr(error, "code", "compatibility.failed")
    if (
        not isinstance(code, str)
        or re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", code) is None
    ):
        code = "compatibility.failed"
    print(
        f"{code}: Compatibility diagnostics could not be completed safely.",
        file=output,
    )
    return 1


def _contract_request(args: argparse.Namespace) -> ProducerAdapterSupportRequest:
    return ProducerAdapterSupportRequest(
        producer_module_id=args.producer,
        core_publication_schema_version=args.core_publication_schema_version,
        publication_kind=args.publication_kind,
        manifest_contract_version=args.manifest_contract_version,
        producer_contract_version=args.producer_contract_version,
        source_record_kind=args.source_record_kind,
        source_record_contract_version=args.source_record_contract_version,
        capabilities=tuple(args.capability),
    )


def _explicit_registries(
    dependencies: VitrineWorkflowDependencies | None,
) -> tuple[
    PublicationProducerRegistry | None,
    ProducerProjectionAdapterRegistry | None,
]:
    if dependencies is None:
        return None, None
    return dependencies.producer_registry, dependencies.adapter_registry


def _run_producers(
    *,
    dependencies: VitrineWorkflowDependencies | None,
    output: TextIO,
    error: TextIO,
) -> int:
    try:
        if dependencies is None:
            reports = diagnose_installed_producer_readiness()
        else:
            reports = diagnose_installed_producer_readiness(
                adapter_registry=dependencies.adapter_registry,
                producer_registry=dependencies.producer_registry,
            )
    except WorkspaceRootError:
        raise
    except Exception as exc:
        return _safe_failure(exc, output=error)
    _print_producer_readiness(reports, output=output)
    # Producer packages are optional dependencies. The observational readiness
    # listing succeeds even when one or more integrations are unavailable.
    return 0


def _run_contract(
    args: argparse.Namespace,
    *,
    output: TextIO,
    error: TextIO,
) -> int:
    try:
        diagnostic = explain_live_adapter_support(_contract_request(args))
    except WorkspaceRootError:
        raise
    except Exception as exc:
        return _safe_failure(exc, output=error)
    _print_diagnostic(diagnostic, output=output)
    return 0 if diagnostic.outcome == "supported" else 1


def _publication_context_error(args: argparse.Namespace) -> str | None:
    if not args.verify_read:
        return None
    missing = tuple(
        name
        for name, value in (
            ("--portfolio-id", args.portfolio_id),
            ("--portfolio-subject-id", args.portfolio_subject_id),
            ("--purpose", args.purpose),
        )
        if value is None
    )
    if not missing:
        return None
    return "--verify-read requires " + ", ".join(missing)


def _run_publication(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies | None,
    output: TextIO,
    error: TextIO,
) -> int:
    context_error = _publication_context_error(args)
    if context_error is not None:
        print(f"compatibility.invalid_request: {context_error}", file=error)
        return 1

    # Workspace inspection is read-only. It resolves the explicit/saved/default
    # Core root without creating or saving anything.
    workspace_root = show_workspace(args.workspace_root).root
    producer_registry, adapter_registry = _explicit_registries(dependencies)
    report: PublicationCompatibilityDiagnostics | PublicationReadProbeDiagnostics
    try:
        if args.verify_read:
            effective_dependencies = dependencies or default_workflow_dependencies()
            assert args.portfolio_id is not None
            assert args.portfolio_subject_id is not None
            assert args.purpose is not None
            report = diagnose_publication_read_probe(
                workspace_root,
                args.publication_id,
                portfolio_id=args.portfolio_id,
                portfolio_subject_id=args.portfolio_subject_id,
                purpose=args.purpose,
                authorization_gate=cast(
                    SharedSourceReadAuthorizationGate,
                    effective_dependencies.source_read_authorization_gate,
                ),
                producer_registry=producer_registry,
                adapter_registry=adapter_registry,
            )
        else:
            report = diagnose_publication_compatibility(
                workspace_root,
                args.publication_id,
                producer_registry=producer_registry,
                adapter_registry=adapter_registry,
            )
    except WorkspaceRootError:
        raise
    except Exception as exc:
        return _safe_failure(exc, output=error)

    _print_publication_report(report, output=output)
    return 0 if report.ready else 1


def run_compatibility_command(
    args: argparse.Namespace,
    *,
    output: TextIO,
    error: TextIO,
    dependencies: VitrineWorkflowDependencies | None = None,
) -> int:
    """Run one compatibility diagnostic command without mutating Vitrine/Core state."""

    if args.compatibility_command == "producers":
        return _run_producers(
            dependencies=dependencies,
            output=output,
            error=error,
        )
    if args.compatibility_command == "contract":
        return _run_contract(args, output=output, error=error)
    if args.compatibility_command == "publication":
        return _run_publication(
            args,
            dependencies=dependencies,
            output=output,
            error=error,
        )
    raise AssertionError(
        f"Unhandled compatibility command: {args.compatibility_command}"
    )


__all__ = ["configure_compatibility_parser", "run_compatibility_command"]
