"""Validate issue #60 live Quillan projection and Artifact-adapter boundaries."""

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
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)
from vitrine.quillan_adapter import (
    QUILLAN_LIVE_ADAPTER_CONTRACT_VERSION,
    QUILLAN_LIVE_ADAPTER_DECLARATION,
    QUILLAN_LIVE_ADAPTER_ID,
    build_quillan_live_adapter,
)
from vitrine.quillan_artifact_source import (
    QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
    QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
    QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY,
    QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY,
)
from vitrine.released_producer_contracts import QUILLAN_LIVE_SUPPORT_KEY
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


def _request() -> ProducerAdapterSupportRequest:
    key = QUILLAN_LIVE_SUPPORT_KEY
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


def _validate_declaration_registry_and_providers() -> None:
    before = _loaded_siblings()
    adapter = build_quillan_live_adapter()
    declaration = adapter.declaration
    _require(
        declaration is QUILLAN_LIVE_ADAPTER_DECLARATION,
        "Quillan declaration is not authoritative",
    )
    _require(
        declaration.adapter_id == QUILLAN_LIVE_ADAPTER_ID,
        "Quillan adapter identity changed",
    )
    _require(
        declaration.adapter_contract_version == QUILLAN_LIVE_ADAPTER_CONTRACT_VERSION,
        "Quillan adapter contract changed",
    )
    _require(
        declaration.candidate_projection_contract_version
        == QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
        "Quillan projection contract changed",
    )
    _require(
        declaration.support_key is QUILLAN_LIVE_SUPPORT_KEY,
        "Quillan support key is not frozen #57 key",
    )
    _require(
        declaration.support_key.source_record_kind is None
        and declaration.support_key.source_record_contract_version is None,
        "Quillan live key incorrectly gained a Publication source record",
    )
    _require(
        declaration.support_key.required_capabilities == ("standards_ratings",),
        "Quillan required capability set changed",
    )
    _require(declaration.integration_kind == "live", "Quillan adapter is not live")
    _require(
        declaration.public_reader_id
        == "vitrine_installed_quillan_academic_result_reader",
        "Quillan reader binding changed",
    )
    _require(
        declaration.reader_contract_version == "vitrine_installed_producer_reader_v1",
        "Quillan reader contract changed",
    )
    _require(
        adapter.reader.descriptor.package_identity == "quillan",
        "Quillan package identity changed",
    )

    ordinary = build_adapter_registry()
    identities = tuple(item.declaration.adapter_id for item in ordinary.adapters)
    _require(
        identities
        == (
            "vitrine_concord_live_adapter",
            "vitrine_quillan_live_adapter",
            "vitrine_scoreform_live_adapter",
        ),
        "ordinary registry does not contain exactly the three completed live adapters",
    )
    _require(
        ordinary.select_adapter(_request()).declaration.adapter_id
        == QUILLAN_LIVE_ADAPTER_ID,
        "exact Quillan support did not select live adapter",
    )
    for invalid in (
        replace(_request(), manifest_contract_version="quillan_unknown_manifest_v1"),
        replace(
            _request(),
            source_record_kind="assignment",
            source_record_contract_version="2",
        ),
        replace(_request(), capabilities=()),
    ):
        try:
            ordinary.select_adapter(invalid)
        except ProducerAdapterError as error:
            _require(
                error.code == "adapter.unsupported_contract",
                "invalid Quillan contract failure changed",
            )
        else:
            raise RuntimeError(
                "invalid Quillan contract unexpectedly selected an adapter"
            )

    fixtures = build_development_fixture_adapter_registry()
    combined = ProducerProjectionAdapterRegistry(
        adapters=ordinary.adapters + fixtures.adapters
    )
    _require(len(combined.adapters) == 6, "live/fixture registry separation changed")
    _require(
        sum(
            item.declaration.integration_kind == "live"
            for item in combined.adapters
        )
        == 3,
        "unexpected completed live adapter count after #60",
    )
    _require(
        {item.declaration.support_key.producer_module_id for item in ordinary.adapters}
        == {"concord", "quillan", "scoreform"},
        "ordinary live producer set changed unexpectedly",
    )

    descriptors = (
        QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
        QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
        QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
    )
    _require(
        tuple(item.support_key for item in descriptors)
        == (
            QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_SUPPORT_KEY,
            QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_SUPPORT_KEY,
            QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_SUPPORT_KEY,
        ),
        "Quillan Snapshot source-provider support keys changed",
    )
    _require(
        QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR.concrete_media_types
        == QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
        "Quillan deferred student-work media allowlist changed",
    )
    _require(
        QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR.concrete_media_types == (),
        "Quillan PDF provider unexpectedly advertises deferred media",
    )
    _require(
        QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR.concrete_media_types == (),
        "Quillan Markdown provider unexpectedly advertises deferred media",
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
        "constructing/registering Quillan adapter imported a sibling package",
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
        "vitrine_quillan_live_adapter",
        "vitrine_scoreform_live_adapter",
    ):
        _require(marker in text, f"live adapter missing from CLI: {marker}")
    _require("fixture" not in text.lower(), "default CLI exposed fixture adapter")
    _require(not error.getvalue(), "adapter list wrote unexpected stderr")

    shown = io.StringIO()
    _require(
        cli.main(
            ["adapters", "show", QUILLAN_LIVE_ADAPTER_ID],
            output=shown,
        )
        == 0,
        "Quillan adapter show command failed",
    )
    shown_text = shown.getvalue()
    for marker in (
        "Integration kind: live",
        "Producer module: quillan",
        "quillan_academic_result_manifest_v1",
        "vitrine_installed_quillan_academic_result_reader",
        "Required capabilities: standards_ratings",
    ):
        _require(
            marker in shown_text,
            f"Quillan adapter show missing marker {marker!r}",
        )
    _require(
        _loaded_siblings() == before,
        "Quillan adapter list/show imported a sibling package",
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

    adapter_source = (ROOT / "vitrine" / "quillan_adapter.py").read_text(
        encoding="utf-8"
    )
    for forbidden_source in (
        'import_module("quillan.academic_result_artifacts")',
        "json.loads(",
        "json.load(",
        "assignment.json",
        "submission.json",
        "review.json",
        "student_prompt",
    ):
        _require(
            forbidden_source not in adapter_source,
            f"Quillan adapter crossed prohibited boundary: {forbidden_source}",
        )
    for required_source in (
        "review_payload_json_base64_chunks",
        "routed_evidence_sha256",
        "pds2_response_pages",
        "QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND",
        "feedback_pdf",
        "feedback_markdown",
        "source_locator=None",
        "source_digest=None",
        "byte_size=None",
    ):
        _require(
            required_source in adapter_source,
            f"Quillan adapter missing {required_source}",
        )

    artifact_source = (
        ROOT / "vitrine" / "quillan_artifact_source.py"
    ).read_text(encoding="utf-8")
    for required_source in (
        'import_module("quillan.academic_result_artifacts")',
        "read_authorized_academic_result_artifacts",
        "student_work",
        "feedback_pdf",
        "feedback_markdown",
        "SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT",
        "SnapshotAuthorizedSourceBytesResult",
    ):
        _require(
            required_source in artifact_source,
            f"Quillan Artifact provider missing {required_source}",
        )
    for forbidden_source in (
        ".read_bytes(",
        "source_relative_path=",
        "routed_evidence_path(",
        "feedback_pdf_path(",
        "feedback_markdown_path(",
    ):
        _require(
            forbidden_source not in artifact_source,
            (
                "Quillan Artifact provider crossed prohibited boundary: "
                f"{forbidden_source}"
            ),
        )

    context_source = (
        ROOT / "vitrine" / "quillan_artifact_context.py"
    ).read_text(encoding="utf-8")
    for required_source in (
        "load_current_records_with_state",
        "get_canonical_publication_record",
        "get_canonical_publication_withdrawal",
        "load_academic_work_registration_revision",
        "read_authorized_producer_manifest",
        "build_quillan_live_adapter",
        'getattr(publication, "source_record", None) is not None',
        'getattr(registration_source, "contract_version", None) != "2"',
    ):
        _require(
            required_source in context_source,
            f"Quillan canonical context missing {required_source}",
        )
    _require(
        "from quillan" not in context_source and "import quillan" not in context_source,
        "Quillan canonical context gained a direct producer import",
    )

    adapter_tests = (ROOT / "tests" / "test_quillan_adapter.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "test_live_declaration_uses_frozen_quillan_contract_and_installed_reader",
        "test_projection_emits_one_logical_review_summary_per_student_result",
        "test_projection_preserves_review_requirements_scale_and_null_semantics",
        "test_projection_preserves_published_text_and_feedback_without_truncation",
        "test_selected_pds2_evidence_projects_independently_in_public_order",
        (
            "test_feedback_capabilities_are_distinct_exact_representations_"
            "without_existence_claim"
        ),
        "test_plain_paper_result_remains_distinct_without_fabricated_digital_work",
        "test_projection_does_not_normalize_native_ratings_into_consumer_judgments",
    ):
        _require(
            marker in adapter_tests,
            f"focused Quillan projection guard missing {marker}",
        )

    artifact_tests = (
        ROOT / "tests" / "test_quillan_artifact_source.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "test_provider_family_has_three_exact_support_keys_and_construction_is_lazy",
        "test_allowed_student_work_selects_exact_evidence_from_producer_tuple",
        "test_non_allowed_decision_fails_before_producer_native_io",
        "test_plain_paper_plan_cannot_fabricate_student_work_capability",
        "test_producer_historical_integrity_failure_maps_to_snapshot_integrity",
        "test_vitrine_never_reopens_returned_quillan_relative_path",
    ):
        _require(marker in artifact_tests, f"Quillan Artifact guard missing {marker}")

    context_tests = (
        ROOT / "tests" / "test_quillan_artifact_context.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "test_production_context_revalidates_selection_core_and_selected_evidence",
        "test_context_refuses_withdrawn_publication_before_manifest_read",
        "test_context_rejects_registration_source_contract_drift",
        "test_selected_quillan_evidence_materializes_authorized_exact_bytes",
    ):
        _require(marker in context_tests, f"Quillan context guard missing {marker}")

    qualifier = (ROOT / "scripts" / "qualify_installed_producer_readers.py").read_text(encoding="utf-8")
    for marker in (
        "QUILLAN_LIVE_SUPPORT_KEY",
        "PASS exact-wheel Quillan live projection qualification",
        "qualify_quillan_artifact_source.py",
    ):
        _require(marker in qualifier, f"exact-wheel Quillan qualification missing {marker!r}")

    artifact_qualifier = ROOT / "scripts" / "qualify_quillan_artifact_source.py"
    _require(artifact_qualifier.is_file(), "exact-wheel Quillan Artifact qualifier is missing")
    artifact_text = artifact_qualifier.read_text(encoding="utf-8")
    for marker in (
        "build_quillan_artifact_source_provider",
        "SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT",
        "PASS exact-wheel Quillan Artifact source qualification",
        "quillan_artifact_authorization_denied",
    ):
        _require(marker in artifact_text, f"Quillan Artifact qualification missing {marker!r}")

    package = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    for marker in (
        "vitrine/quillan_adapter.py",
        "vitrine/quillan_contract.py",
        "vitrine/quillan_artifact_context.py",
        "vitrine/quillan_artifact_source.py",
        "scripts/validate_quillan_adapter.py",
        "scripts/qualify_quillan_artifact_source.py",
    ):
        _require(marker in package, f"Quillan package guard missing {marker!r}")

    adapter_smoke = (ROOT / "scripts" / "smoke_test_adapter_wheel.py").read_text(encoding="utf-8")
    candidate_smoke = (ROOT / "scripts" / "smoke_test_candidate_wheel.py").read_text(encoding="utf-8")
    for marker in ("vitrine_quillan_live_adapter", "QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR"):
        _require(marker in adapter_smoke, f"adapter wheel smoke missing {marker!r}")
    _require("vitrine_quillan_live_adapter" in candidate_smoke, "Candidate wheel smoke does not include live Quillan")


def _validate_documentation_handoff() -> None:
    contract_path = (
        ROOT
        / "docs"
        / "contracts"
        / "live-quillan-projection-artifact-adapter-v1.md"
    )
    _require(contract_path.is_file(), "final Quillan operational contract is missing")
    contract = contract_path.read_text(encoding="utf-8")
    for marker in (
        "QUILLAN_LIVE_SUPPORT_KEY",
        "source_record_kind              = None",
        "vitrine_installed_quillan_academic_result_reader",
        "absent != withheld != included",
        "authorized_source_bytes_deferred_media_v1",
        "vitrine_quillan_authorized_artifact_source_provider",
        "Candidate != Selection",
        "Concord + Quillan + ScoreForm",
        "qualify_installed_producer_readers.py",
    ):
        _require(marker in contract, f"final Quillan contract missing {marker!r}")

    handoff = (
        ROOT / "docs" / "contracts" / "live-producer-integration-handoff-v1.md"
    ).read_text(encoding="utf-8")
    _require(
        "Concord + Quillan + ScoreForm" in handoff,
        "#57 handoff still lacks the completed three-live-adapter registry",
    )
    _require(
        "live-quillan-projection-artifact-adapter-v1.md" in handoff,
        "#57 handoff does not point to the final Quillan operational contract",
    )

    reader_contract = (
        ROOT / "docs" / "contracts" / "installed-producer-reader-services-v1.md"
    ).read_text(encoding="utf-8")
    _require(
        "Concord, Quillan, and ScoreForm" in reader_contract,
        "#58 reader handoff still describes an incomplete live registry",
    )
    _require(
        "live-quillan-projection-artifact-adapter-v1.md" in reader_contract,
        "#58 reader handoff does not point to the final Quillan contract",
    )

    scoreform_contract = (
        ROOT / "docs" / "contracts" / "live-scoreform-projection-adapter-v1.md"
    ).read_text(encoding="utf-8")
    concord_contract = (
        ROOT / "docs" / "contracts" / "live-concord-projection-artifact-adapter-v1.md"
    ).read_text(encoding="utf-8")
    for name, text in (
        ("#59", scoreform_contract),
        ("#61", concord_contract),
    ):
        _require(
            "vitrine_quillan_live_adapter" in text,
            f"{name} handoff still omits the live Quillan adapter",
        )

    report_path = (
        ROOT / "docs" / "validation" / "issue-60-live-quillan-adapter-validation.md"
    )
    _require(report_path.is_file(), "issue #60 validation report is missing")
    report = report_path.read_text(encoding="utf-8")
    for marker in (
        "Final repository validation:",
        "PASS exact-wheel Quillan live projection qualification",
        "PASS exact-wheel Quillan Artifact source qualification",
        "Concord + Quillan + ScoreForm",
    ):
        _require(marker in report, f"issue #60 validation report missing {marker!r}")

    package = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    for marker in (
        "docs/contracts/live-quillan-projection-artifact-adapter-v1.md",
        "docs/validation/issue-60-live-quillan-adapter-validation.md",
    ):
        _require(marker in package, f"Quillan final package guard missing {marker!r}")


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_declaration_registry_and_providers()
    _validate_cli()
    _validate_dependency_and_source_boundaries()
    _validate_documentation_handoff()
    if run_focused_tests:
        focused = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_quillan_adapter.py",
                "tests/test_quillan_artifact_source.py",
                "tests/test_quillan_artifact_context.py",
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
            raise RuntimeError(f"Quillan focused validation failed: {detail}")


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
        print("PASS live Quillan adapter validation")
        return 0
    except (
        KeyError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        tomllib.TOMLDecodeError,
    ) as error:
        print(f"Live Quillan adapter validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
