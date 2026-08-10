"""Non-mutating direct CLI diagnostics for producer projection adapters."""

from __future__ import annotations

import argparse
from typing import TextIO

from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.producer_adapters import (
    ProducerProjectionAdapter,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)


def configure_adapter_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "adapters",
        help="Inspect Vitrine producer adapter integration declarations.",
    )
    commands = parser.add_subparsers(dest="adapter_command", required=True)

    list_parser = commands.add_parser("list", help="List registered producer adapters.")
    list_parser.add_argument(
        "--include-development-fixtures",
        action="store_true",
        help="Explicitly include Vitrine development fixture adapters.",
    )

    show_parser = commands.add_parser("show", help="Show one adapter declaration.")
    show_parser.add_argument("adapter_id")
    show_parser.add_argument(
        "--include-development-fixtures",
        action="store_true",
        help="Explicitly include Vitrine development fixture adapters.",
    )


def _registry(include_development_fixtures: bool) -> ProducerProjectionAdapterRegistry:
    ordinary = build_adapter_registry()
    if not include_development_fixtures:
        return ordinary
    fixture = build_development_fixture_adapter_registry()
    return ProducerProjectionAdapterRegistry(adapters=ordinary.adapters + fixture.adapters)


def _find_adapter(
    registry: ProducerProjectionAdapterRegistry, adapter_id: str
) -> ProducerProjectionAdapter | None:
    return next(
        (
            adapter
            for adapter in registry.adapters
            if adapter.declaration.adapter_id == adapter_id
        ),
        None,
    )


def _print_adapter(adapter: ProducerProjectionAdapter, *, output: TextIO) -> None:
    declaration = adapter.declaration
    support = declaration.support_key
    print(f"Adapter ID: {declaration.adapter_id}", file=output)
    print(f"Adapter contract: {declaration.adapter_contract_version}", file=output)
    print(f"Integration kind: {declaration.integration_kind}", file=output)
    print(f"Producer module: {support.producer_module_id}", file=output)
    print(f"Publication kind: {support.publication_kind}", file=output)
    print(f"Manifest contract: {support.manifest_contract_version}", file=output)
    print(f"Reader ID: {declaration.public_reader_id}", file=output)
    print(f"Reader contract: {declaration.reader_contract_version}", file=output)
    print(
        f"Projection contract: {declaration.candidate_projection_contract_version}",
        file=output,
    )
    capabilities = ", ".join(support.required_capabilities) or "<none>"
    print(f"Required capabilities: {capabilities}", file=output)


def run_adapter_command(
    args: argparse.Namespace,
    *,
    output: TextIO,
    error: TextIO,
) -> int:
    include = bool(args.include_development_fixtures)
    registry = _registry(include)
    if args.adapter_command == "list":
        if not registry.adapters:
            print("No live producer adapters are registered.", file=output)
            return 0
        print(
            "adapter_id\tintegration_kind\tproducer_module\tpublication_kind\t"
            "manifest_contract\treader_id\tprojection_contract",
            file=output,
        )
        for adapter in registry.adapters:
            declaration = adapter.declaration
            support = declaration.support_key
            print(
                "\t".join(
                    (
                        declaration.adapter_id,
                        declaration.integration_kind,
                        support.producer_module_id,
                        support.publication_kind,
                        support.manifest_contract_version,
                        declaration.public_reader_id,
                        declaration.candidate_projection_contract_version,
                    )
                ),
                file=output,
            )
        return 0
    if args.adapter_command == "show":
        selected_adapter = _find_adapter(registry, args.adapter_id)
        if selected_adapter is None:
            print("Adapter not found in the selected registry.", file=error)
            return 1
        _print_adapter(selected_adapter, output=output)
        return 0
    raise AssertionError(f"Unhandled adapter command: {args.adapter_command}")


__all__ = ["configure_adapter_parser", "run_adapter_command"]
