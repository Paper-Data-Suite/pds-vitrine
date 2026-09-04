"""Validate issue #62 cross-producer compatibility diagnostic contracts."""

from __future__ import annotations

import sys
from pathlib import Path

from vitrine.artifact_diagnostics import diagnose_artifact_applicability
from vitrine.cli import build_parser
from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
    DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS,
    explain_live_adapter_support,
)
from vitrine.producer_adapters import (
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    build_adapter_registry,
)
from vitrine.released_producer_contracts import LIVE_PRODUCER_SUPPORT_KEYS

_EXPECTED_LIVE_ADAPTER_IDS = (
    "vitrine_concord_live_adapter",
    "vitrine_quillan_live_adapter",
    "vitrine_scoreform_live_adapter",
)
_EXPECTED_PRODUCER_IDS = ("concord", "quillan", "scoreform")
_EXPECTED_FIXTURE_IDS = frozenset(
    {
        "vitrine_concord_fixture",
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
    }
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _request_from_key(
    key: ProducerAdapterSupportKey,
) -> ProducerAdapterSupportRequest:
    return ProducerAdapterSupportRequest(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
        capabilities=key.required_capabilities,
    )


def _validate_contract_support() -> None:
    _require(
        CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
        == "vitrine_cross_producer_compatibility_diagnostic_v1",
        "cross-producer diagnostic contract version changed",
    )
    _require(
        DEVELOPMENT_FIXTURE_PRODUCER_MODULE_IDS == _EXPECTED_FIXTURE_IDS,
        "development fixture producer identities changed",
    )

    registry = build_adapter_registry()
    adapter_ids = tuple(item.declaration.adapter_id for item in registry.adapters)
    _require(
        adapter_ids == _EXPECTED_LIVE_ADAPTER_IDS,
        f"ordinary live adapter registry changed: {adapter_ids!r}",
    )

    keys = tuple(LIVE_PRODUCER_SUPPORT_KEYS)
    producers = tuple(key.producer_module_id for key in keys)
    _require(
        producers == _EXPECTED_PRODUCER_IDS,
        f"live support-key producer ordering changed: {producers!r}",
    )
    for key in keys:
        request = _request_from_key(key)
        diagnostic = explain_live_adapter_support(request, registry=registry)
        _require(
            diagnostic.outcome == "supported",
            f"exact {key.producer_module_id} support request is not supported",
        )
        _require(
            diagnostic.code == "compatibility.contract_supported",
            f"exact {key.producer_module_id} support code changed",
        )
        _require(
            diagnostic.reason_codes == ("compatibility.contract_supported",),
            f"exact {key.producer_module_id} support reasons changed",
        )

    scoreform = next(
        key for key in keys if key.producer_module_id == "scoreform"
    )
    future_manifest = ProducerAdapterSupportRequest(
        producer_module_id=scoreform.producer_module_id,
        core_publication_schema_version=(
            scoreform.core_publication_schema_version
        ),
        publication_kind=scoreform.publication_kind,
        manifest_contract_version="scoreform_academic_result_manifest_v2",
        producer_contract_version=scoreform.producer_contract_version,
        source_record_kind=scoreform.source_record_kind,
        source_record_contract_version=scoreform.source_record_contract_version,
        capabilities=scoreform.required_capabilities,
    )
    mismatch = explain_live_adapter_support(future_manifest, registry=registry)
    _require(
        mismatch.code == "adapter.unsupported_contract",
        "semantic mismatch no longer preserves adapter.unsupported_contract",
    )
    _require(
        "compatibility.manifest_contract_mismatch" in mismatch.reason_codes,
        "manifest mismatch explanation is missing",
    )

    fixture_request = ProducerAdapterSupportRequest(
        producer_module_id="vitrine_scoreform_fixture",
        core_publication_schema_version=scoreform.core_publication_schema_version,
        publication_kind=scoreform.publication_kind,
        manifest_contract_version=scoreform.manifest_contract_version,
        producer_contract_version=scoreform.producer_contract_version,
        source_record_kind=scoreform.source_record_kind,
        source_record_contract_version=scoreform.source_record_contract_version,
        capabilities=scoreform.required_capabilities,
    )
    fixture = explain_live_adapter_support(fixture_request, registry=registry)
    _require(
        fixture.code == "adapter.fixture_not_enabled",
        "fixture identity no longer preserves adapter.fixture_not_enabled",
    )
    _require(
        fixture.scope == "fixture_boundary",
        "fixture identity is not diagnosed at the fixture boundary",
    )


def _validate_artifact_applicability() -> None:
    scoreform = diagnose_artifact_applicability("scoreform")
    _require(
        scoreform.outcome == "not_applicable",
        "ScoreForm Artifact readiness must remain not_applicable",
    )
    _require(
        scoreform.code == "compatibility.artifact_api_not_applicable",
        "ScoreForm Artifact applicability code changed",
    )

    for producer in ("quillan", "concord"):
        diagnostic = diagnose_artifact_applicability(producer)
        _require(
            diagnostic.outcome == "supported",
            f"{producer} Artifact applicability is not supported",
        )
        _require(
            diagnostic.code == "compatibility.artifact_api_ready",
            f"{producer} Artifact applicability code changed",
        )


def _validate_cli_parser() -> None:
    parser = build_parser()
    producer_args = parser.parse_args(["compatibility", "producers"])
    _require(
        producer_args.command == "compatibility"
        and producer_args.compatibility_command == "producers",
        "compatibility producers CLI parser changed",
    )

    contract_args = parser.parse_args(
        [
            "compatibility",
            "contract",
            "--producer",
            "scoreform",
            "--core-publication-schema-version",
            "1",
            "--publication-kind",
            "academic_result_set",
            "--manifest-contract-version",
            "scoreform_academic_result_manifest_v1",
            "--producer-contract-version",
            "scoreform_academic_work_v1",
            "--capability",
            "multiple_attempts",
            "--capability",
            "points",
            "--capability",
            "question_evidence",
        ]
    )
    _require(
        contract_args.compatibility_command == "contract",
        "compatibility contract CLI parser changed",
    )

    publication_args = parser.parse_args(
        ["compatibility", "publication", "publication_validation"]
    )
    _require(
        publication_args.compatibility_command == "publication",
        "compatibility publication CLI parser changed",
    )


def _validate_documentation(root: Path) -> None:
    required = {
        "docs/contracts/cross-producer-compatibility-diagnostics-v1.md": (
            "vitrine_cross_producer_compatibility_diagnostic_v1",
            "Package version is not semantic compatibility",
            "adapter.unsupported_contract",
            "source_read.authorization_denied",
            "snapshot.source_integrity_failed",
        ),
        "docs/development/cross-producer-compatibility-diagnostics.md": (
            "vitrine compatibility producers",
            "vitrine compatibility contract",
            "vitrine compatibility publication",
            "--verify-read",
            "fail-closed",
        ),
        "docs/validation/issue-62-cross-producer-compatibility-validation.md": (
            "Core 0.6.3",
            "ScoreForm 0.11.0",
            "Quillan 0.10.0",
            "Concord 0.3.0",
            "qualify_installed_producer_readers.py",
        ),
    }
    for relative, markers in required.items():
        path = root / relative
        _require(path.is_file(), f"missing issue #62 document: {relative}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            _require(
                marker in text,
                f"{relative} is missing required marker {marker!r}",
            )


def validate(root: Path) -> None:
    _validate_contract_support()
    _validate_artifact_applicability()
    _validate_cli_parser()
    _validate_documentation(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        validate(root)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Compatibility diagnostic validation failed: {error}", file=sys.stderr)
        return 1
    print("PASS cross-producer compatibility diagnostic validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
