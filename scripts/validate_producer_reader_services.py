"""Validate issue #58 installed producer-reader and authorization services."""

from __future__ import annotations

import inspect
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

from vitrine.producer_adapters import build_adapter_registry
from vitrine.producer_reader_services import (
    INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
    PRODUCER_READER_SERVICE_CONTRACT_VERSION,
    build_audited_installed_producer_readers,
    read_authorized_producer_manifest,
)
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)
from vitrine.workflow_context import default_workflow_dependencies

_SIBLING_IMPORT_ROOTS = ("concord", "quillan", "scoreform")
_SIBLING_DISTRIBUTIONS = frozenset({"pds-concord", "quillan", "scoreform"})

_EXPECTED_READERS: dict[str, tuple[str, str, str]] = {
    "scoreform": (
        "scoreform",
        "scoreform.academic_result_reader",
        "read_academic_result_manifest",
    ),
    "quillan": (
        "quillan",
        "quillan.academic_result_reader",
        "read_academic_result_manifest",
    ),
    "concord": (
        "pds-concord",
        "concord.academic_result_reader",
        "read_academic_result_manifest",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _dependency_name(requirement: str) -> str:
    token = requirement.split(";", 1)[0].strip()
    for separator in ("<", ">", "=", "!", "~", "["):
        token = token.split(separator, 1)[0]
    return token.strip().lower().replace("_", "-")


def _validate_contracts() -> None:
    _require(
        PRODUCER_READER_SERVICE_CONTRACT_VERSION
        == "vitrine_producer_reader_service_v1",
        "unexpected producer-reader service contract version",
    )
    _require(
        INSTALLED_PRODUCER_READER_CONTRACT_VERSION
        == "vitrine_installed_producer_reader_v1",
        "unexpected installed producer-reader contract version",
    )


def _validate_audited_reader_bindings() -> None:
    before = {
        name
        for name in sys.modules
        if any(
            name == root or name.startswith(f"{root}.")
            for root in _SIBLING_IMPORT_ROOTS
        )
    }
    readers = build_audited_installed_producer_readers()
    after = {
        name
        for name in sys.modules
        if any(
            name == root or name.startswith(f"{root}.")
            for root in _SIBLING_IMPORT_ROOTS
        )
    }
    _require(
        after == before,
        "building audited installed readers eagerly imported a sibling producer",
    )
    _require(
        tuple(reader.audit.producer_module_id for reader in readers)
        == ("concord", "quillan", "scoreform"),
        "audited installed reader order changed",
    )
    for reader in readers:
        module_id = reader.audit.producer_module_id
        expected_distribution, expected_module, expected_symbol = _EXPECTED_READERS[
            module_id
        ]
        authoritative = RELEASED_PRODUCER_CONTRACT_BY_MODULE[module_id]
        _require(
            reader.audit is authoritative,
            f"{module_id} reader is not bound to the authoritative #57 audit record",
        )
        _require(
            reader.audit.distribution_name == expected_distribution,
            f"{module_id} distribution identity changed",
        )
        _require(
            reader.audit.public_reader_module == expected_module,
            f"{module_id} public reader module changed",
        )
        _require(
            reader.audit.public_reader_symbol == expected_symbol,
            f"{module_id} public reader symbol changed",
        )
        _require(
            reader.descriptor.integration_kind == "live",
            f"{module_id} installed reader is not marked live",
        )
        _require(
            reader.descriptor.reader_contract_version
            == INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
            f"{module_id} installed reader contract version changed",
        )


def _validate_fail_closed_defaults() -> None:
    ordinary = build_adapter_registry()
    _require(
        tuple(item.declaration.adapter_id for item in ordinary.adapters)
        == (
            "vitrine_concord_live_adapter",
            "vitrine_quillan_live_adapter",
            "vitrine_scoreform_live_adapter",
        ),
        "ordinary registry must contain exactly the completed live adapters",
    )
    expected_readers = {
        "concord": "vitrine_installed_concord_academic_result_reader",
        "quillan": "vitrine_installed_quillan_academic_result_reader",
        "scoreform": "vitrine_installed_scoreform_academic_result_reader",
    }
    actual_readers = {
        item.declaration.support_key.producer_module_id:
        item.reader.descriptor.public_reader_id
        for item in ordinary.adapters
    }
    _require(
        actual_readers == expected_readers,
        "completed live adapters are not bound to the #58 installed readers",
    )
    dependencies = default_workflow_dependencies()
    _require(
        dependencies.producer_registry.profiles == (),
        "default workflow dependencies must not discover producer Profiles",
    )
    _require(
        dependencies.adapter_registry.adapters == (),
        "default workflow dependencies must not enable live adapters",
    )
    _require(
        dependencies.development_fixture_mode is False,
        "default workflow dependencies unexpectedly enable fixture mode",
    )


def _validate_trust_order() -> None:
    source = inspect.getsource(read_authorized_producer_manifest)
    authorization = source.find("authorize_source_read(")
    verification = source.find("read_verified_publication_manifest_bytes(")
    invocation = source.find("reader.read(")
    _require(
        -1 not in (authorization, verification, invocation),
        "shared authorized-read service is missing a required trust stage",
    )
    _require(
        authorization < verification < invocation,
        "shared authorized-read trust order changed",
    )


def _validate_candidate_integration(root: Path) -> None:
    text = (root / "vitrine" / "candidate_services.py").read_text(encoding="utf-8")
    _require(
        "read_authorized_producer_manifest" in text,
        "Candidate services no longer consume the shared authorized-read service",
    )
    _require(
        "def _authorize_read_and_parse_manifest(" in text,
        "Candidate shared authorized-read compatibility mapper is missing",
    )


def _validate_dependency_boundary(root: Path) -> None:
    parsed = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = cast(dict[str, Any], parsed["project"])
    dependencies = cast(list[str], project["dependencies"])
    names = {_dependency_name(item) for item in dependencies}
    _require("pds-core" in names, "Vitrine lost its required Core dependency")
    forbidden = sorted(names & _SIBLING_DISTRIBUTIONS)
    _require(
        not forbidden,
        f"Vitrine gained hard sibling producer dependencies: {forbidden}",
    )


def _validate_docs(root: Path) -> None:
    qualifier = root / "scripts" / "qualify_installed_producer_readers.py"
    _require(
        qualifier.is_file(),
        "exact-wheel installed reader qualification harness is missing",
    )
    contract = (
        root / "docs" / "contracts" / "installed-producer-reader-services-v1.md"
    ).read_text(encoding="utf-8")
    handoff = (
        root / "docs" / "contracts" / "live-producer-integration-handoff-v1.md"
    ).read_text(encoding="utf-8")
    for marker in (
        "vitrine_installed_producer_reader_v1",
        "read_authorized_producer_manifest",
        "build_installed_producer_registry",
        "reader.unavailable",
        "reader.incompatible",
        "source-read authorization",
        "Artifact authorization",
        "#59",
        "#60",
        "#61",
        "#62",
        "qualify_installed_producer_readers.py",
    ):
        _require(marker in contract, f"#58 contract missing marker {marker!r}")
    _require(
        "Issue #58 is implemented" in handoff,
        "live producer handoff does not record the implemented #58 boundary",
    )


def validate(root: Path) -> None:
    _validate_contracts()
    _validate_audited_reader_bindings()
    _validate_fail_closed_defaults()
    _validate_trust_order()
    _validate_candidate_integration(root)
    _validate_dependency_boundary(root)
    _validate_docs(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        validate(root)
    except (KeyError, OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"Producer reader service validation failed: {error}", file=sys.stderr)
        return 1
    print("PASS producer reader service validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
