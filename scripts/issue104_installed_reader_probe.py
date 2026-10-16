"""Child-side installed-only #104 reader-contract and projection acceptance.

Executed by an isolated interpreter with -I, from outside the source checkout.
Producer wheels are disposable synthetic contracts, not official producer builds.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import cast

from pds_core.publication_compatibility import (
    PublicationProducerProfile,
    discover_publication_producer_profiles,
    lookup_publication_reader_support,
)
from pds_core.publication_records import PublicationKind

from vitrine.producer_adapters import (
    ProducerAdapterSupportRequest,
    ProducerReaderError,
    ProjectedProducerSource,
    build_adapter_registry,
)
from vitrine.producer_reader_compatibility import (
    VITRINE_LEGACY_EXACT_PRODUCER_RELEASES,
    InstalledProducerReaderCompatibilityError,
    resolve_installed_producer_reader_compatibility,
)
from vitrine.producer_reader_services import build_audited_installed_producer_reader
from vitrine.released_producer_contracts import RELEASED_PRODUCER_CONTRACT_BY_MODULE

FUTURE_VERSION = "99.123.456"
MANIFEST_BYTES = b"issue104:synthetic_public_manifest"
EXPECTED_CONTRACTS = {
    "scoreform": "scoreform_academic_result_reader_v1",
    "quillan": "quillan_academic_result_reader_v1",
    "concord": "concord_academic_result_reader_v1",
}
EXPECTED_COUNTS = {"scoreform": 2, "quillan": 3, "concord": 1}


def _assert_wheel_import(module_name: str) -> None:
    imported = importlib.import_module(module_name)
    module_path = getattr(imported, "__file__", None)
    if not isinstance(module_path, str):
        raise RuntimeError(f"Installed module has no file path: {module_name}")
    root = Path(module_path).resolve()
    assert root.is_file()
    assert root.is_relative_to(Path(sys.prefix).resolve()), (
        module_name, root, sys.prefix
    )


def _request(producer_module: str) -> ProducerAdapterSupportRequest:
    key = RELEASED_PRODUCER_CONTRACT_BY_MODULE[producer_module].support_key
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


def _installed_context() -> tuple[PublicationProducerProfile, ...]:
    assert metadata.version("pds-core") == "0.6.6"
    assert metadata.version("pds-vitrine")
    for module in ("pds_core", "vitrine", *EXPECTED_CONTRACTS):
        _assert_wheel_import(module)
    profiles = discover_publication_producer_profiles()
    assert {profile.module_id for profile in profiles} == set(EXPECTED_CONTRACTS)
    for module in EXPECTED_CONTRACTS:
        audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[module]
        assert metadata.version(audit.distribution_name) == FUTURE_VERSION
        assert FUTURE_VERSION != audit.release_version
        assert FUTURE_VERSION not in VITRINE_LEGACY_EXACT_PRODUCER_RELEASES[module]
    return profiles


def _require_field(source: ProjectedProducerSource, key: str) -> object:
    fields = source.display_snapshot.fields
    matches = tuple(item.value for item in fields if item.key == key)
    assert len(matches) == 1, key
    return matches[0]


def _verify_scoreform_attempts(
    sources: tuple[ProjectedProducerSource, ...],
) -> None:
    """Assert exact attempt evidence, independent of opaque identity ordering."""

    attempts = {_require_field(source, "attempt_number"): source for source in sources}
    assert len(sources) == 2
    assert set(attempts) == {1, 2}
    assert len({source.producer_source.source_record_id for source in sources}) == 2

    for source in attempts.values():
        assert _require_field(source, "question_standard_alignments") == (
            "1:RL.CR.9-10.1",
            "2:W.AW.9-10.1",
        )
    assert _require_field(attempts[1], "response_states") == (
        "1:selected", "2:blank"
    )
    assert _require_field(attempts[2], "response_states") == (
        "1:selected", "2:selected"
    )
    assert _require_field(attempts[1], "selected_answer_presence") == (
        "1:present", "2:absent"
    )
    assert _require_field(attempts[2], "selected_answer_presence") == (
        "1:present", "2:present"
    )
    assert _require_field(attempts[1], "response_correctness") == (
        "1:true", "2:false"
    )
    assert _require_field(attempts[2], "response_correctness") == (
        "1:true", "2:true"
    )


def _supported() -> dict[str, object]:
    profiles = _installed_context()
    registry = build_adapter_registry()
    counts: dict[str, int] = {}
    for module, contract in EXPECTED_CONTRACTS.items():
        audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[module]
        key = audit.support_key
        profile = next(profile for profile in profiles if profile.module_id == module)
        metadata_support = lookup_publication_reader_support(
            profile, cast(PublicationKind, key.publication_kind), key.manifest_contract_version
        )
        assert metadata_support is not None
        assert metadata_support.reader_contract_version == contract
        assert metadata_support.distribution_name == audit.distribution_name
        compatible = resolve_installed_producer_reader_compatibility(
            audit, installed_distribution_version=FUTURE_VERSION
        )
        assert compatible.compatibility_basis == "declared_reader_contract"
        assert compatible.reader_contract_version == contract
        assert compatible.installed_distribution_version == FUTURE_VERSION
        reader = build_audited_installed_producer_reader(module)
        model = reader.read(MANIFEST_BYTES)
        assert isinstance(model, importlib.import_module(
            f"{module}.academic_result_manifest"
        ).AcademicResultManifest)
        adapter = registry.select_adapter(_request(module))
        assert adapter.declaration.reader_contract_version == contract
        assert adapter.declaration.integration_kind == "live"
        projected = adapter.project(model)
        assert projected.adapter_id == adapter.declaration.adapter_id
        assert projected.reader_contract_version == contract
        assert len(projected.projected_sources) == EXPECTED_COUNTS[module], module
        assert all(source.producer_source.producer_module_id == module
                   for source in projected.projected_sources)
        assert "PRIVATE_A" not in repr(projected)
        assert "PRIVATE_B" not in repr(projected)
        assert "PRIVATE_C" not in repr(projected)
        if module == "scoreform":
            _verify_scoreform_attempts(projected.projected_sources)
        elif module == "quillan":
            kinds = tuple(item.projection_kind for item in projected.projected_sources)
            assert any("review_summary" in kind for kind in kinds)
            assert sum("feedback" in kind for kind in kinds) == 2
            assert _require_field(projected.projected_sources[0],
                                  "review_state") == "ratings_complete"
        elif module == "concord":
            assert _require_field(projected.projected_sources[0],
                                  "score_native_value") == "proficient"
            assert _require_field(projected.projected_sources[0],
                                  "score_native_value_type") == "string"
        counts[module] = len(projected.projected_sources)
    return {"mode": "supported", "synthetic_version": FUTURE_VERSION,
            "projected_sources": counts, "installed_vitrine": metadata.version("pds-vitrine")}


def _rejected(mode: str, module: str) -> dict[str, object]:
    _installed_context()
    reader = build_audited_installed_producer_reader(module)
    try:
        reader.read(MANIFEST_BYTES)
    except ProducerReaderError as error:
        assert error.code == "reader.incompatible", (mode, module, error.code)
        assert error.stage == "reader_contract", (mode, module, error.stage)
    else:
        raise AssertionError(f"Unsupported future metadata was accepted: {mode}/{module}")
    # Confirm other installed producers remain compatible while one is invalid.
    for other in EXPECTED_CONTRACTS:
        if other != module:
            build_audited_installed_producer_reader(other).read(MANIFEST_BYTES)
    return {"mode": mode, "module": module, "failure": "reader.incompatible"}


def _historical() -> dict[str, object]:
    _installed_context()
    count = 0
    for module, versions in VITRINE_LEGACY_EXACT_PRODUCER_RELEASES.items():
        audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[module]
        for exact in versions:
            legacy = resolve_installed_producer_reader_compatibility(
                audit, installed_distribution_version=exact, profiles=()
            )
            assert legacy.compatibility_basis == "legacy_exact_release"
            count += 1
        try:
            resolve_installed_producer_reader_compatibility(
                audit, installed_distribution_version="99.123.455", profiles=()
            )
        except InstalledProducerReaderCompatibilityError as error:
            assert error.code == "reader.incompatible"
        else:
            raise AssertionError("Unlisted synthetic adjacent release was accepted")
    return {"mode": "historical", "exact_fallback_cases": count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("supported", "unsupported", "missing", "historical"),
                        required=True)
    parser.add_argument("--module", choices=tuple(EXPECTED_CONTRACTS))
    args = parser.parse_args(argv)
    assert os.environ.get("PDS_ISSUE104_SCENARIO", "supported") == args.mode or (
        args.mode == "historical" and os.environ.get("PDS_ISSUE104_SCENARIO") == "historical"
    )
    if args.mode in ("unsupported", "missing"):
        assert args.module is not None
        assert os.environ.get("PDS_ISSUE104_TARGET") == args.module
        result = _rejected(args.mode, args.module)
    elif args.mode == "historical":
        result = _historical()
    else:
        assert args.module is None
        result = _supported()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
