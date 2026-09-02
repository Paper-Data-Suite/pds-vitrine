"""Validate issue #61 live Concord projection and Artifact-adapter boundaries."""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from vitrine import cli
from vitrine.concord_adapter import (
    CONCORD_LIVE_ADAPTER_CONTRACT_VERSION,
    CONCORD_LIVE_ADAPTER_DECLARATION,
    CONCORD_LIVE_ADAPTER_ID,
    CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
    build_concord_live_adapter,
)
from vitrine.concord_artifact_source import (
    CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)
from vitrine.released_producer_contracts import CONCORD_LIVE_SUPPORT_KEY
from vitrine.workflow_context import default_workflow_dependencies

ROOT = Path(__file__).resolve().parents[1]
_SIBLING_IMPORT_ROOTS = ("concord", "quillan", "scoreform")
_SIBLING_DISTRIBUTIONS = frozenset({"pds-concord", "quillan", "scoreform"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _loaded_siblings() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in sys.modules
            if any(
                name == root or name.startswith(f"{root}.")
                for root in _SIBLING_IMPORT_ROOTS
            )
        )
    )


def _request(*, conditional_capabilities: bool = False) -> ProducerAdapterSupportRequest:
    key = CONCORD_LIVE_SUPPORT_KEY
    capabilities = key.required_capabilities
    if conditional_capabilities:
        capabilities = (
            *capabilities,
            "moderated_scores",
            "standards_ratings",
        )
    return ProducerAdapterSupportRequest(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
        capabilities=capabilities,
    )


def _validate_declaration_registry_and_provider() -> None:
    before = _loaded_siblings()
    adapter = build_concord_live_adapter()
    declaration = adapter.declaration
    _require(
        declaration is CONCORD_LIVE_ADAPTER_DECLARATION,
        "Concord declaration is not authoritative",
    )
    _require(
        declaration.adapter_id == CONCORD_LIVE_ADAPTER_ID,
        "Concord adapter identity changed",
    )
    _require(
        declaration.adapter_contract_version == CONCORD_LIVE_ADAPTER_CONTRACT_VERSION,
        "Concord adapter contract changed",
    )
    _require(
        declaration.candidate_projection_contract_version
        == CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
        "Concord projection contract changed",
    )
    _require(
        declaration.support_key is CONCORD_LIVE_SUPPORT_KEY,
        "Concord support key is not frozen #57 key",
    )
    _require(
        declaration.support_key.required_capabilities == ("criterion_scores",),
        "Concord required capability set changed",
    )
    _require(declaration.integration_kind == "live", "Concord adapter is not live")
    _require(
        declaration.public_reader_id
        == "vitrine_installed_concord_academic_result_reader",
        "Concord reader binding changed",
    )
    _require(
        declaration.reader_contract_version == "vitrine_installed_producer_reader_v1",
        "Concord reader contract changed",
    )
    _require(
        adapter.reader.descriptor.package_identity == "pds-concord",
        "Concord package identity changed",
    )

    ordinary = build_adapter_registry()
    identities = tuple(item.declaration.adapter_id for item in ordinary.adapters)
    _require(
        identities
        == (
            "vitrine_concord_live_adapter",
            "vitrine_scoreform_live_adapter",
        ),
        "ordinary registry does not contain exactly completed live adapters",
    )
    _require(
        ordinary.select_adapter(_request()).declaration.adapter_id
        == "vitrine_concord_live_adapter",
        "exact Concord support did not select live adapter",
    )
    _require(
        ordinary.select_adapter(_request(conditional_capabilities=True)).declaration.adapter_id
        == "vitrine_concord_live_adapter",
        "conditional Concord capabilities did not select the same adapter",
    )
    for invalid in (
        replace(_request(), source_record_kind=None, source_record_contract_version=None),
        replace(_request(), source_record_contract_version="concord_activity_v99"),
        replace(_request(), capabilities=()),
    ):
        try:
            ordinary.select_adapter(invalid)
        except ProducerAdapterError as error:
            _require(
                error.code == "adapter.unsupported_contract",
                "invalid Concord contract failure changed",
            )
        else:
            raise RuntimeError("invalid Concord contract unexpectedly selected an adapter")

    fixtures = build_development_fixture_adapter_registry()
    combined = ProducerProjectionAdapterRegistry(
        adapters=ordinary.adapters + fixtures.adapters
    )
    _require(len(combined.adapters) == 5, "live/fixture registry separation changed")
    _require(
        sum(item.declaration.integration_kind == "live" for item in combined.adapters) == 2,
        "unexpected live adapter count after #61",
    )

    descriptor = CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR
    _require(
        descriptor.support_key
        == (
            "concord",
            "concord:returned_artifact_pdf",
            "vitrine_candidate_projection_v1",
            "collaborative_artifact",
            "concord:returned_artifact_pdf",
        ),
        "Concord Snapshot source-provider support key changed",
    )

    dependencies = default_workflow_dependencies()
    _require(
        dependencies.producer_registry.profiles == (),
        "default workflow unexpectedly discovers producer Profiles",
    )
    _require(
        dependencies.adapter_registry.adapters == (),
        "default workflow unexpectedly enables live adapters",
    )
    _require(
        dependencies.development_fixture_mode is False,
        "default workflow unexpectedly enables fixture mode",
    )
    _require(
        _loaded_siblings() == before,
        "constructing/registering Concord adapter imported a sibling package",
    )


def _validate_cli() -> None:
    before = _loaded_siblings()
    output = io.StringIO()
    error = io.StringIO()
    _require(
        cli.main(["adapters", "list"], output=output, error=error) == 0,
        "adapter list command failed",
    )
    text = output.getvalue()
    for marker in (
        "vitrine_concord_live_adapter",
        "vitrine_scoreform_live_adapter",
    ):
        _require(marker in text, f"live adapter missing from CLI: {marker}")
    _require("fixture" not in text.lower(), "default CLI exposed fixture adapter")
    _require("quillan" not in text.lower(), "Quillan live adapter appeared early")
    _require(not error.getvalue(), "adapter list wrote unexpected stderr")

    shown = io.StringIO()
    _require(
        cli.main(
            ["adapters", "show", "vitrine_concord_live_adapter"],
            output=shown,
        )
        == 0,
        "Concord adapter show command failed",
    )
    shown_text = shown.getvalue()
    for marker in (
        "Integration kind: live",
        "Producer module: concord",
        "concord_academic_result_manifest_v1",
        "vitrine_installed_concord_academic_result_reader",
        "Required capabilities: criterion_scores",
    ):
        _require(marker in shown_text, f"Concord adapter show missing marker {marker!r}")
    _require(
        _loaded_siblings() == before,
        "Concord adapter list/show imported a sibling package",
    )


def _dependency_name(requirement: str) -> str:
    token = requirement.split(";", 1)[0].strip()
    for separator in ("<", ">", "=", "!", "~", "["):
        token = token.split(separator, 1)[0]
    return token.strip().lower().replace("_", "-")


def _validate_dependency_and_source_boundaries() -> None:
    parsed = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = cast(dict[str, Any], parsed["project"])
    dependencies = cast(list[str], project["dependencies"])
    names = {_dependency_name(item) for item in dependencies}
    _require("pds-core" in names, "Vitrine lost Core runtime dependency")
    forbidden = sorted(names & _SIBLING_DISTRIBUTIONS)
    _require(not forbidden, f"Vitrine gained hard sibling dependencies: {forbidden}")

    adapter_source = (ROOT / "vitrine" / "concord_adapter.py").read_text(
        encoding="utf-8"
    )
    for forbidden_source in (
        "json.loads(",
        "json.load(",
        "concord.storage",
        "retained_source_path",
    ):
        _require(
            forbidden_source not in adapter_source,
            f"Concord adapter crossed prohibited boundary: {forbidden_source}",
        )
    for required_source in (
        "score_native_value_type",
        "individual_score_target",
        "group_score_target",
        "artifact_instance",
        "artifact_page",
        "source_locator=None",
    ):
        _require(
            required_source in adapter_source,
            f"Concord adapter missing {required_source}",
        )

    artifact_source = (ROOT / "vitrine" / "concord_artifact_source.py").read_text(
        encoding="utf-8"
    )
    for required_source in (
        'import_module("concord.academic_result_artifacts")',
        "read_authorized_academic_result_artifact",
        "source_snapshot_revision",
        "application/pdf",
        "SnapshotAuthorizedSourceBytesResult",
    ):
        _require(
            required_source in artifact_source,
            f"Concord Artifact provider missing {required_source}",
        )
    for forbidden_source in (
        "concord.storage",
        "retained_source_path",
        "source_relative_path=",
    ):
        _require(
            forbidden_source not in artifact_source,
            f"Concord Artifact provider crossed prohibited boundary: {forbidden_source}",
        )

    tests = (ROOT / "tests" / "test_concord_adapter.py").read_text(encoding="utf-8")
    for marker in (
        "test_projection_emits_one_source_per_score_revision",
        "test_projection_preserves_score_history_without_selecting_current",
        "test_projection_preserves_type_sensitive_scale_and_score_values",
        "test_group_and_individual_targets_remain_distinct",
        "test_non_score_disposition_remains_valueless_and_preserves_reason",
        "test_projection_emits_every_score_evidence_link_independently",
        "test_external_evidence_remains_metadata_only_and_is_not_dereferenced",
        "test_moderation_history_and_public_qualification_are_preserved",
        "test_live_concord_candidate_path_preserves_scores_and_artifact_evidence_without_selection",
    ):
        _require(marker in tests, f"focused Concord projection guard missing {marker}")

    artifact_tests = (
        ROOT / "tests" / "test_concord_artifact_source.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "test_provider_descriptor_is_exact_and_construction_is_concord_lazy",
        "test_non_allowed_artifact_authorization_fails_before_native_io",
        "test_manifest_or_snapshot_context_is_not_artifact_authorization",
        "test_allowed_artifact_authorization_returns_exact_authorized_bytes",
        "test_artifact_page_result_remains_page_bounded",
    ):
        _require(marker in artifact_tests, f"Concord Artifact guard missing {marker}")

    context_tests = (
        ROOT / "tests" / "test_concord_artifact_context.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "test_production_context_resolver_revalidates_selection_core_and_projection",
        "test_selected_concord_artifact_materializes_authorized_pdf_bytes",
    ):
        _require(marker in context_tests, f"Concord context guard missing {marker}")

    qualifier = (
        ROOT / "scripts" / "qualify_installed_producer_readers.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "CONCORD_LIVE_SUPPORT_KEY",
        "get_concord_profile",
        "PASS exact-wheel Concord live projection qualification",
        "score_native_value_type",
    ):
        _require(marker in qualifier, f"exact-wheel Concord qualification missing {marker!r}")

    package = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    for marker in (
        "vitrine/concord_adapter.py",
        "vitrine/concord_artifact_context.py",
        "vitrine/concord_artifact_source.py",
        "scripts/validate_concord_adapter.py",
        "tests/test_concord_adapter.py",
        "tests/test_concord_artifact_context.py",
        "tests/test_concord_artifact_source.py",
    ):
        _require(marker in package, f"Concord package guard missing {marker!r}")

    adapter_smoke = (
        ROOT / "scripts" / "smoke_test_adapter_wheel.py"
    ).read_text(encoding="utf-8")
    candidate_smoke = (
        ROOT / "scripts" / "smoke_test_candidate_wheel.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "vitrine_concord_live_adapter",
        "pds-concord",
    ):
        _require(marker in adapter_smoke, f"adapter wheel smoke missing {marker!r}")
    _require(
        "vitrine_concord_live_adapter" in candidate_smoke,
        "Candidate wheel smoke does not include live Concord",
    )

    artifact_qualifier_path = (
        ROOT / "scripts" / "qualify_concord_artifact_source.py"
    )
    _require(
        artifact_qualifier_path.is_file(),
        "exact-wheel Concord Artifact qualification harness is missing",
    )
    artifact_qualifier = artifact_qualifier_path.read_text(encoding="utf-8")
    for marker in (
        "route_scan_sources",
        "build_concord_artifact_source_provider",
        "SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT",
        "PASS exact-wheel Concord Artifact source qualification",
        "concord_artifact_authorization_denied",
    ):
        _require(
            marker in artifact_qualifier,
            f"exact-wheel Concord Artifact qualification missing {marker!r}",
        )

    parent_qualifier = (
        ROOT / "scripts" / "qualify_installed_producer_readers.py"
    ).read_text(encoding="utf-8")
    _require(
        "qualify_concord_artifact_source.py" in parent_qualifier,
        "installed reader qualification does not invoke Concord Artifact qualification",
    )
    _require(
        "CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR" in adapter_smoke,
        "adapter wheel smoke does not import the Concord Artifact provider",
    )

    contract_path = (
        ROOT / "docs" / "contracts"
        / "live-concord-projection-artifact-adapter-v1.md"
    )
    _require(contract_path.is_file(), "live Concord contract documentation is missing")
    contract = contract_path.read_text(encoding="utf-8")
    for marker in (
        "vitrine_concord_live_adapter_v1",
        "CONCORD_LIVE_SUPPORT_KEY",
        "criterion_scores",
        "standards_ratings",
        "moderated_scores",
        "1 != 1.0 != \"1\" != true",
        "one represented Concord Score revision",
        "one represented Score Evidence Link",
        "concord:returned_artifact_pdf",
        "vitrine_concord_returned_artifact_source_provider",
        "authorized_source_bytes_v1",
        "manifest source-read authorization",
        "Concord Artifact authorization",
        "Snapshot build authority",
        "Candidate != Selection",
        "qualify_concord_artifact_source.py",
    ):
        _require(marker in contract, f"live Concord contract missing {marker!r}")


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_declaration_registry_and_provider()
    _validate_cli()
    _validate_dependency_and_source_boundaries()
    if run_focused_tests:
        focused = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_concord_adapter.py",
                "tests/test_concord_artifact_source.py",
                "tests/test_concord_artifact_context.py",
                "tests/test_adapter_cli.py",
                "-q",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if focused.returncode != 0:
            detail = focused.stderr.strip() or focused.stdout.strip()
            raise RuntimeError(f"Concord focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-focused-tests",
        action="store_true",
        help="Skip focused pytest when an enclosing gate already ran the full suite.",
    )
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS live Concord adapter validation")
        return 0
    except (
        KeyError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        tomllib.TOMLDecodeError,
    ) as error:
        print(f"Live Concord adapter validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
