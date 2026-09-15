"""Validate issue #71 installed-acceptance infrastructure and frozen contract."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tomllib
from pathlib import Path

try:
    from scripts.live_installed_acceptance_contract import (
        ACCEPTANCE_IDENTITY,
        AUDITED_RELEASE_WHEELS,
        CANDIDATE_DISCOVERY_SLICE_READY,
        CI_ENDPOINTS,
        CONCORD_CONTRACT,
        CURATED_SNAPSHOT_SLICE_READY,
        EXPECTED_VITRINE_RUNTIME_DEPENDENCY,
        FIXTURE_PRODUCER_IDS,
        FULL_ACCEPTANCE_READY,
        HEAVY_SCENARIO_FAMILIES,
        LIVE_PRODUCERS,
        QUILLAN_CONTRACT,
        REQUIRED_ACCEPTANCE_FILES,
        SCOREFORM_CONTRACT,
        validate_contract_constants,
    )
except ModuleNotFoundError:  # direct script execution from scripts/
    from live_installed_acceptance_contract import (
        ACCEPTANCE_IDENTITY,
        AUDITED_RELEASE_WHEELS,
        CANDIDATE_DISCOVERY_SLICE_READY,
        CI_ENDPOINTS,
        CONCORD_CONTRACT,
        CURATED_SNAPSHOT_SLICE_READY,
        EXPECTED_VITRINE_RUNTIME_DEPENDENCY,
        FIXTURE_PRODUCER_IDS,
        FULL_ACCEPTANCE_READY,
        HEAVY_SCENARIO_FAMILIES,
        LIVE_PRODUCERS,
        QUILLAN_CONTRACT,
        REQUIRED_ACCEPTANCE_FILES,
        SCOREFORM_CONTRACT,
        validate_contract_constants,
    )

ROOT = Path(__file__).resolve().parents[1]
FOCUSED_TESTS = (
    "tests/test_live_installed_acceptance_contract.py",
    "tests/test_validate_live_installed_acceptance.py",
)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _require_text(path: Path, *markers: str) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{_relative(path)} is missing #71 marker: {marker}")


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _validate_files() -> None:
    missing = tuple(path for path in REQUIRED_ACCEPTANCE_FILES if not (ROOT / path).is_file())
    if missing:
        raise RuntimeError(f"issue #71 required file(s) missing: {missing}")



def _validate_manifest_contract() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    required = (
        "recursive-include docs *.md *.json",
        "recursive-include scripts *.py",
        "recursive-include tests *.py *.json",
    )
    for marker in required:
        if marker not in manifest:
            raise RuntimeError(
                f"MANIFEST.in no longer includes #71 acceptance material: {marker}"
            )

def _validate_frozen_contract() -> None:
    validate_contract_constants()
    if ACCEPTANCE_IDENTITY != "vitrine_live_installed_cross_producer_acceptance_v1":
        raise RuntimeError("issue #71 acceptance identity drifted")
    frozen = {
        spec.distribution_name: (spec.version, spec.filename, spec.sha256)
        for spec in AUDITED_RELEASE_WHEELS
    }
    expected = {
        "pds-core": (
            "0.6.3",
            "pds_core-0.6.3-py3-none-any.whl",
            "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
        ),
        "scoreform": (
            "0.11.0",
            "scoreform-0.11.0-py3-none-any.whl",
            "8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44",
        ),
        "quillan": (
            "0.10.0",
            "quillan-0.10.0-py3-none-any.whl",
            "5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9",
        ),
        "pds-concord": (
            "0.3.0",
            "pds_concord-0.3.0-py3-none-any.whl",
            "dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12",
        ),
    }
    if frozen != expected:
        raise RuntimeError("issue #71 exact release artifact audit drifted")
    if tuple(item.producer_module_id for item in LIVE_PRODUCERS) != (
        "scoreform",
        "quillan",
        "concord",
    ):
        raise RuntimeError("issue #71 live producer set drifted")
    if SCOREFORM_CONTRACT.materialization != "reference_only":
        raise RuntimeError("ScoreForm must remain reference_only")
    if QUILLAN_CONTRACT.materialization != "copied_source":
        raise RuntimeError("Quillan must remain copied_source")
    if CONCORD_CONTRACT.materialization != "copied_source":
        raise RuntimeError("Concord must remain copied_source")
    if FIXTURE_PRODUCER_IDS.intersection(
        item.producer_module_id for item in LIVE_PRODUCERS
    ):
        raise RuntimeError("fixture identity entered live acceptance contract")
    if CI_ENDPOINTS != (("ubuntu-latest", "3.11"), ("windows-latest", "3.14")):
        raise RuntimeError("issue #71 supported endpoint matrix drifted")
    if len(HEAVY_SCENARIO_FAMILIES) != 8:
        raise RuntimeError("issue #71 scenario-family inventory drifted")


def _validate_project_contract() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject project table is missing")
    if project.get("dependencies") != [EXPECTED_VITRINE_RUNTIME_DEPENDENCY]:
        raise RuntimeError("issue #71 must preserve Core-only Vitrine runtime dependency")
    optional = project.get("optional-dependencies", {})
    all_requirements = tuple(project.get("dependencies", ()))
    if isinstance(optional, dict):
        all_requirements += tuple(
            item for values in optional.values() for item in values
        )
    normalized = "\n".join(str(item).casefold() for item in all_requirements)
    for sibling in ("scoreform", "quillan", "pds-concord", "pds-meridian", "pds-portia"):
        if sibling in normalized:
            raise RuntimeError(f"issue #71 added forbidden runtime/dev dependency: {sibling}")

    mypy_files = tuple(data.get("tool", {}).get("mypy", {}).get("files", ()))
    for path in (
        "scripts/live_installed_acceptance_contract.py",
        "scripts/live_installed_acceptance_probe.py",
        "scripts/live_installed_acceptance_support.py",
        "scripts/live_installed_acceptance_portfolio.py",
        "scripts/live_installed_acceptance_scenario.py",
        "scripts/qualify_installed_live_portfolio.py",
        "scripts/validate_live_installed_acceptance.py",
    ):
        if path not in mypy_files:
            raise RuntimeError(f"issue #71 MyPy scope is missing {path}")


def _validate_outer_harness() -> None:
    path = ROOT / "scripts" / "qualify_installed_live_portfolio.py"
    roots = _import_roots(path)
    if {"scoreform", "quillan", "concord"}.intersection(roots):
        raise RuntimeError("outer #71 qualifier must not import producer packages")
    _require_text(
        path,
        "--no-index",
        "PYTHONPATH",
        "venv.EnvBuilder(with_pip=True, clear=True)",
        "live-venv",
        "sealed-verifier-venv",
        "PASS exact release wheel authentication",
        "--preflight-only",
        "--candidate-discovery-only",
        "--portfolio-snapshot-only",
        "live_installed_acceptance_support.py",
        "live_installed_acceptance_portfolio.py",
        "live_installed_acceptance_scenario.py",
    )
    source = path.read_text(encoding="utf-8")
    if "latest" in source.casefold():
        raise RuntimeError("#71 qualifier must not resolve floating latest release artifacts")


def _validate_probe() -> None:
    path = ROOT / "scripts" / "live_installed_acceptance_probe.py"
    _require_text(
        path,
        "scoreform.academic_result_reader",
        "quillan.academic_result_reader",
        "quillan.academic_result_artifacts",
        "concord.academic_result_reader",
        "concord.academic_result_artifacts",
        "build_publication_producer_registry",
        "build_adapter_registry",
        "support_key.producer_module_id",
        "default_workflow_dependencies",
        "sealed-verifier-preflight",
    )
    for fixture_id in FIXTURE_PRODUCER_IDS:
        if fixture_id not in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"probe does not explicitly reject fixture identity {fixture_id}")



def _validate_candidate_scenario() -> None:
    support = ROOT / "scripts" / "live_installed_acceptance_support.py"
    scenario = ROOT / "scripts" / "live_installed_acceptance_scenario.py"
    _require_text(
        support,
        'CONCORD_STANDARD_ID = "synthetic_collab_accept_1"',
        "register_scoreform_academic_work",
        "generate_academic_result_manifest",
        "publish_scoreform_academic_results",
        "register_quillan_academic_work",
        "publish_quillan_academic_results",
        "register_concord_academic_work",
        "publish_concord_academic_results",
        "install_starter_profile",
        "plan_create_portfolio_for_student",
        "link_portfolio_subject",
        "discover_and_evaluate_candidates",
        "build_publication_producer_registry",
        "build_adapter_registry",
        "candidate_source_read",
        "collaborative_artifact",
        "original_student_work",
        "rendered_feedback",
    )
    _require_text(
        scenario,
        "prepare_core_identity_sources",
        "build_scoreform_publication",
        "build_quillan_publication",
        "build_concord_publication",
        "install_improvement_portfolio",
        "discover_live_candidates",
        '"fixture_registry_used": False',
        '"full_acceptance_ready": False',
    )
    combined = support.read_text(encoding="utf-8") + "\n" + scenario.read_text(encoding="utf-8")
    if 'CONCORD_STANDARD_ID = "synthetic:COLLAB.ACCEPT.1"' in combined:
        raise RuntimeError(
            "Slice 2 Concord standard identity must satisfy the Core path-safe identifier contract"
        )
    if "str(error)" in scenario.read_text(encoding="utf-8"):
        raise RuntimeError("Slice 2 scenario must not render raw producer failure text")
    forbidden = (
        "build_development_fixture_producer_registry",
        "build_development_fixture_adapter_registry",
        "fixtures/producer-adapters",
        "fixtures\\producer-adapters",
    )
    for marker in forbidden:
        if marker in combined:
            raise RuntimeError(f"Slice 2 live scenario uses forbidden fixture path/API: {marker}")
    for fixture_id in FIXTURE_PRODUCER_IDS:
        if fixture_id in combined:
            raise RuntimeError(
                f"Slice 2 live scenario contains forbidden fixture identity: {fixture_id}"
            )



def _validate_curated_snapshot_scenario() -> None:
    portfolio = ROOT / "scripts" / "live_installed_acceptance_portfolio.py"
    scenario = ROOT / "scripts" / "live_installed_acceptance_scenario.py"
    _require_text(
        portfolio,
        "select_candidate_directly",
        "place_selection",
        "create_reflection",
        "review_curation_target",
        "create_working_composition",
        'reflection_requirement_id="comparison_reflection"',
        'approval_requirement_id="teacher_review"',
        'producer="scoreform"',
        'native_revision=1',
        'representation_kind="quillan:selected_student_work"',
        'representation_kind="concord:returned_artifact_pdf"',
        'representation_kind="quillan:feedback_pdf"',
        '"reference_only": 1',
        '"copied_source": 3',
        '"generated_vitrine": 1',
        "build_canonical_quillan_artifact_source_context_resolver",
        "build_quillan_artifact_source_providers",
        "build_canonical_concord_artifact_source_context_resolver",
        "build_concord_artifact_source_provider",
        "prepare_current_portfolio_build",
        '("collaborator_review_required",)',
        "acknowledged_obligation_codes=preview.unresolved_obligation_codes",
        "execute_prepared_current_portfolio_build",
        "SnapshotBuildAuthorityDecision",
        "QuillanArtifactAuthorizationDecision",
        "ConcordArtifactAuthorizationDecision",
        "SnapshotMaterializationRecord",
    )
    _require_text(
        scenario,
        "curate_representative_portfolio",
        "build_representative_snapshot",
        '"slice3_curated_snapshot_acceptance"',
        '"Vitrine explicit representative curation"',
        '"Vitrine authorized Snapshot build, seal, verify, and Export"',
    )
    combined = portfolio.read_text(encoding="utf-8") + "\n" + scenario.read_text(
        encoding="utf-8"
    )
    forbidden = (
        "build_development_fixture_producer_registry",
        "build_development_fixture_adapter_registry",
        "highest",
        "best_attempt",
        "latest_attempt",
    )
    for marker in forbidden:
        if marker in combined:
            raise RuntimeError(
                f"Slice 3 curated Snapshot scenario contains forbidden heuristic/fixture marker: {marker}"
            )
    for fixture_id in FIXTURE_PRODUCER_IDS:
        if fixture_id in combined:
            raise RuntimeError(
                f"Slice 3 curated Snapshot scenario contains forbidden fixture identity: {fixture_id}"
            )
    if "str(error)" in scenario.read_text(encoding="utf-8"):
        raise RuntimeError("Slice 3 scenario must not render raw failure text")


def _validate_slice_guard() -> None:
    if not CANDIDATE_DISCOVERY_SLICE_READY:
        raise RuntimeError("Slice 2 Candidate discovery scenario is not enabled")
    if not CURATED_SNAPSHOT_SLICE_READY:
        raise RuntimeError("Slice 3 curated Snapshot scenario is not enabled")
    if FULL_ACCEPTANCE_READY:
        raise RuntimeError(
            "Slice 3 unexpectedly claims full #71 acceptance; negative/drift, "
            "historical, tamper, and producer-independent coverage must land first"
        )


def validate(*, run_focused_tests: bool) -> None:
    _validate_files()
    _validate_manifest_contract()
    _validate_frozen_contract()
    _validate_project_contract()
    _validate_outer_harness()
    _validate_probe()
    _validate_candidate_scenario()
    _validate_curated_snapshot_scenario()
    _validate_slice_guard()
    if run_focused_tests:
        subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS],
            cwd=ROOT,
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Issue #71 validation failed: {error}", file=sys.stderr)
        return 1
    print("PASS issue #71 live installed acceptance Slice 3 validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
