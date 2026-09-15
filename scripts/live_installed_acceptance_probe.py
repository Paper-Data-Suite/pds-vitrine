"""Installed-environment preflight for Vitrine issue #71.

The outer qualifier copies this file to a temporary directory outside the source
checkout before execution.  It intentionally performs no Portfolio mutation in
Slice 1; it proves that the exact installed release composition is discoverable,
keeps Vitrine's optional producer boundary intact, and exposes the live adapter
registry without fixtures.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

EXPECTED_VERSIONS = {
    "pds-core": "0.6.3",
    "scoreform": "0.11.0",
    "quillan": "0.10.0",
    "pds-concord": "0.3.0",
}
LIVE_PRODUCER_IDS = ("scoreform", "quillan", "concord")
FIXTURE_IDS = {
    "vitrine_scoreform_fixture",
    "vitrine_quillan_fixture",
    "vitrine_concord_fixture",
}


class InstalledProbeError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InstalledProbeError(message)


def _module_origin(name: str) -> Path:
    module = importlib.import_module(name)
    raw = getattr(module, "__file__", None)
    if not isinstance(raw, str) or not raw:
        raise InstalledProbeError(f"{name} has no installed file origin")
    return Path(raw).resolve()


def _inside_prefix(path: Path) -> bool:
    prefix = Path(sys.prefix).resolve()
    lowered = {part.casefold() for part in path.parts}
    return path.is_relative_to(prefix) and "site-packages" in lowered


def _distribution_versions() -> dict[str, str]:
    return {name: metadata.version(name) for name in EXPECTED_VERSIONS}


def run_live_probe(repository: Path) -> dict[str, Any]:
    _require("PYTHONPATH" not in os.environ, "PYTHONPATH must be absent")
    versions = _distribution_versions()
    _require(versions == EXPECTED_VERSIONS, "installed release versions disagree")
    vitrine_version = metadata.version("pds-vitrine")

    required_modules = (
        "pds_core",
        "scoreform",
        "scoreform.academic_result_reader",
        "quillan",
        "quillan.academic_result_reader",
        "quillan.academic_result_artifacts",
        "concord",
        "concord.academic_result_reader",
        "concord.academic_result_artifacts",
        "vitrine",
        "vitrine.producer_adapters",
        "vitrine.producer_reader_services",
        "vitrine.scoreform_adapter",
        "vitrine.quillan_adapter",
        "vitrine.concord_adapter",
    )
    origins = {name: _module_origin(name) for name in required_modules}
    for name, origin in origins.items():
        _require(_inside_prefix(origin), f"{name} did not import from site-packages")
        _require(
            not origin.is_relative_to(repository),
            f"{name} imported from source checkout",
        )
    for raw in sys.path:
        if not raw:
            continue
        try:
            resolved = Path(raw).resolve()
        except OSError:
            continue
        _require(
            not resolved.is_relative_to(repository),
            "repository root leaked into isolated sys.path",
        )

    from pds_core.publication_compatibility import (
        build_publication_producer_registry,
        discover_publication_producer_profiles,
    )

    from vitrine.producer_adapters import build_adapter_registry
    from vitrine.workflow_context import default_workflow_dependencies

    discovered = discover_publication_producer_profiles()
    discovered_ids = tuple(sorted(profile.module_id for profile in discovered))
    for producer_id in LIVE_PRODUCER_IDS:
        _require(producer_id in discovered_ids, f"missing producer profile: {producer_id}")
    _require(
        not FIXTURE_IDS.intersection(discovered_ids),
        "fixture producer profile discovered in live environment",
    )

    producer_registry = build_publication_producer_registry()
    for producer_id in LIVE_PRODUCER_IDS:
        _require(
            producer_registry.get(producer_id) is not None,
            f"producer registry is missing {producer_id}",
        )

    adapters = build_adapter_registry()
    declarations = tuple(adapter.declaration for adapter in adapters.adapters)
    live_ids = tuple(sorted(item.support_key.producer_module_id for item in declarations))
    _require(live_ids == tuple(sorted(LIVE_PRODUCER_IDS)), "live adapter registry is not exact")
    _require(
        all(item.integration_kind == "live" for item in declarations),
        "ordinary adapter registry contains non-live integration",
    )
    _require(
        not FIXTURE_IDS.intersection(live_ids),
        "fixture adapter entered ordinary registry",
    )

    defaults = default_workflow_dependencies()
    _require(
        defaults.producer_registry.profiles == (),
        "default workflow producer registry must remain fail-closed",
    )
    _require(
        defaults.adapter_registry.adapters == (),
        "default workflow adapter registry must remain fail-closed",
    )
    _require(
        defaults.development_fixture_mode is False,
        "default workflow dependencies enabled fixture mode",
    )

    vitrine_requirements = tuple(metadata.requires("pds-vitrine") or ())
    normalized = tuple(value.casefold().replace(" ", "") for value in vitrine_requirements)
    _require(
        any(value.startswith("pds-core") and ">=0.6.3" in value and "<0.7" in value for value in normalized),
        "Vitrine Core runtime requirement drifted",
    )
    for sibling in ("scoreform", "quillan", "pds-concord", "pds-meridian", "pds-portia"):
        _require(
            not any(sibling in value for value in normalized),
            f"Vitrine gained forbidden sibling runtime dependency: {sibling}",
        )

    return {
        "mode": "live_preflight",
        "vitrine_version": vitrine_version,
        "release_versions": versions,
        "producer_profiles": discovered_ids,
        "live_adapters": live_ids,
        "fixture_identities_present": False,
        "default_workflow_fail_closed": True,
        "installed_origins_verified": len(origins),
    }


def run_sealed_verifier_probe(repository: Path) -> dict[str, Any]:
    _require("PYTHONPATH" not in os.environ, "PYTHONPATH must be absent")
    _require(metadata.version("pds-core") == "0.6.3", "Core version disagrees")
    metadata.version("pds-vitrine")
    for sibling in ("scoreform", "quillan", "pds-concord"):
        try:
            metadata.version(sibling)
        except metadata.PackageNotFoundError:
            continue
        raise InstalledProbeError(f"producer must be absent in sealed verifier: {sibling}")
    for name in ("pds_core", "vitrine", "vitrine.snapshot_custody", "vitrine.storage"):
        origin = _module_origin(name)
        _require(_inside_prefix(origin), f"{name} did not import from site-packages")
        _require(not origin.is_relative_to(repository), f"{name} imported from checkout")
    imported_roots = {name.split(".", 1)[0] for name in sys.modules}
    _require(
        not {"scoreform", "quillan", "concord"}.intersection(imported_roots),
        "producer module imported in Core+Vitrine verifier",
    )
    return {
        "mode": "sealed_verifier_preflight",
        "core_version": metadata.version("pds-core"),
        "vitrine_version": metadata.version("pds-vitrine"),
        "producer_distributions_installed": False,
        "producer_modules_imported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument(
        "--mode",
        required=True,
        choices=("live-preflight", "sealed-verifier-preflight"),
    )
    args = parser.parse_args()
    try:
        repository = args.repository.resolve(strict=True)
        if args.mode == "live-preflight":
            result = run_live_probe(repository)
        else:
            result = run_sealed_verifier_probe(repository)
    except (InstalledProbeError, OSError, metadata.PackageNotFoundError) as error:
        print(f"FAILED installed acceptance preflight: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
