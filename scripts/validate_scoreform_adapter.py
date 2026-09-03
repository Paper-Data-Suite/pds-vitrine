"""Validate issue #59 live ScoreForm projection-adapter boundaries."""

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
from vitrine.released_producer_contracts import SCOREFORM_LIVE_SUPPORT_KEY
from vitrine.scoreform_adapter import (
    SCOREFORM_LIVE_ADAPTER_DECLARATION,
    build_scoreform_live_adapter,
)
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
    key = SCOREFORM_LIVE_SUPPORT_KEY
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


def _validate_declaration_and_registry() -> None:
    before = _loaded_siblings()
    adapter = build_scoreform_live_adapter()
    declaration = adapter.declaration
    _require(declaration is SCOREFORM_LIVE_ADAPTER_DECLARATION, "ScoreForm declaration is not authoritative")
    _require(declaration.adapter_id == "vitrine_scoreform_live_adapter", "ScoreForm adapter identity changed")
    _require(declaration.adapter_contract_version == "vitrine_scoreform_live_adapter_v1", "ScoreForm adapter contract changed")
    _require(declaration.support_key is SCOREFORM_LIVE_SUPPORT_KEY, "ScoreForm support key is not frozen #57 key")
    _require(declaration.integration_kind == "live", "ScoreForm adapter is not live")
    _require(declaration.public_reader_id == "vitrine_installed_scoreform_academic_result_reader", "ScoreForm reader binding changed")
    _require(declaration.reader_contract_version == "vitrine_installed_producer_reader_v1", "ScoreForm reader contract changed")
    _require(adapter.reader.descriptor.package_identity == "scoreform", "ScoreForm package identity changed")

    ordinary = build_adapter_registry()
    _require(
        tuple(item.declaration.adapter_id for item in ordinary.adapters)
        == (
            "vitrine_concord_live_adapter",
            "vitrine_quillan_live_adapter",
            "vitrine_scoreform_live_adapter",
        ),
        "ordinary registry does not contain completed live adapters",
    )
    _require(ordinary.select_adapter(_request()).declaration.adapter_id == "vitrine_scoreform_live_adapter", "exact ScoreForm support did not select live adapter")
    try:
        ordinary.select_adapter(replace(_request(), manifest_contract_version="scoreform_unknown_manifest_v1"))
    except ProducerAdapterError as error:
        _require(error.code == "adapter.unsupported_contract", "wrong ScoreForm contract failure changed")
    else:
        raise RuntimeError("wrong ScoreForm contract unexpectedly selected an adapter")

    fixtures = build_development_fixture_adapter_registry()
    combined = ProducerProjectionAdapterRegistry(adapters=ordinary.adapters + fixtures.adapters)
    _require(len(combined.adapters) == 6, "live/fixture registry separation changed")
    _require(
        sum(item.declaration.integration_kind == "live" for item in combined.adapters) == 3,
        "unexpected live adapter count after #60",
    )
    _require(
        {item.declaration.support_key.producer_module_id for item in ordinary.adapters}
        == {"concord", "quillan", "scoreform"},
        "ordinary live producer set changed unexpectedly",
    )

    dependencies = default_workflow_dependencies()
    _require(dependencies.producer_registry.profiles == (), "default workflow unexpectedly discovers producer Profiles")
    _require(dependencies.adapter_registry.adapters == (), "default workflow unexpectedly enables live adapter")
    _require(dependencies.development_fixture_mode is False, "default workflow unexpectedly enables fixture mode")
    _require(_loaded_siblings() == before, "constructing/registering ScoreForm adapter imported sibling package")


def _validate_cli() -> None:
    before = _loaded_siblings()
    output = io.StringIO()
    error = io.StringIO()
    _require(cli.main(["adapters", "list"], output=output, error=error) == 0, "adapter list command failed")
    text = output.getvalue()
    _require("vitrine_scoreform_live_adapter" in text, "live ScoreForm missing from CLI")
    _require("fixture" not in text.lower(), "default CLI exposed fixture adapter")
    _require("vitrine_quillan_live_adapter" in text, "live Quillan missing from CLI")
    _require("vitrine_concord_live_adapter" in text, "live Concord missing from CLI")
    _require(not error.getvalue(), "adapter list wrote unexpected stderr")
    shown = io.StringIO()
    _require(cli.main(["adapters", "show", "vitrine_scoreform_live_adapter"], output=shown) == 0, "adapter show command failed")
    shown_text = shown.getvalue()
    for marker in ("Integration kind: live", "Producer module: scoreform", "scoreform_academic_result_manifest_v1", "vitrine_installed_scoreform_academic_result_reader"):
        _require(marker in shown_text, f"adapter show missing marker {marker!r}")
    _require(_loaded_siblings() == before, "adapter list/show imported sibling package")


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

    source = (ROOT / "vitrine" / "scoreform_adapter.py").read_text(encoding="utf-8")
    for forbidden_source in ("json.loads(", "json.load(", "assignment.json", "results.csv", 'key="selected_answer"', 'key="retained_source_path"', "source_locator=scan.retained_source_path"):
        _require(forbidden_source not in source, f"ScoreForm adapter crossed prohibited boundary: {forbidden_source}")
    for required_source in ("scoreform_attempt_projection_identity", "selected_answer_presence", "response_correctness", "question_standard_alignments", "scan_review_failure_id", "pds2_source_sha256", "source_locator=None", "source_digest=None"):
        _require(required_source in source, f"ScoreForm adapter missing {required_source}")

    tests = (ROOT / "tests" / "test_scoreform_adapter.py").read_text(encoding="utf-8")
    for marker in (
        "test_projection_emits_exactly_one_source_per_represented_attempt",
        "test_multiple_attempts_survive_without_selection_or_ranking_semantics",
        "test_response_states_presence_and_correctness_remain_distinct",
        "test_selected_answer_content_is_never_projected",
        "test_assignment_question_and_standard_alignment_metadata_is_preserved_without_ratings",
        "test_pds2_provenance_survives_but_retained_path_never_becomes_access",
        "test_plain_paper_provenance_fabricates_no_scan_or_review_metadata",
        "test_scan_review_provenance_preserves_only_bounded_failure_reference",
        "test_attempt_identity_is_unchanged_by_score_timestamp_or_response_content",
        "test_attempt_relationship_artifact_and_privacy_contract_are_exact",
        "test_live_scoreform_candidate_path_evaluates_every_attempt_without_selection",
    ):
        _require(marker in tests, f"focused ScoreForm guard missing {marker}")

    qualifier = (ROOT / "scripts" / "qualify_installed_producer_readers.py").read_text(encoding="utf-8")
    for marker in (
        "get_publication_producer_profile",
        "PASS exact-wheel ScoreForm live projection qualification",
        "len(batch.projected_sources) != 3",
        "qualification-private.pdf",
    ):
        _require(marker in qualifier, f"exact-wheel ScoreForm qualification missing {marker!r}")


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_declaration_and_registry()
    _validate_cli()
    _validate_dependency_and_source_boundaries()
    if run_focused_tests:
        focused = subprocess.run([sys.executable, "-m", "pytest", "tests/test_scoreform_adapter.py", "tests/test_adapter_cli.py", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
        if focused.returncode != 0:
            detail = focused.stderr.strip() or focused.stdout.strip()
            raise RuntimeError(f"ScoreForm focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true", help="Skip focused pytest when an enclosing gate already ran the full suite.")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS live ScoreForm adapter validation")
        return 0
    except (KeyError, OSError, RuntimeError, subprocess.SubprocessError, tomllib.TOMLDecodeError) as error:
        print(f"Live ScoreForm adapter validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
