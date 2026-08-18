"""Inspect built Vitrine distributions for metadata and content boundaries."""

from __future__ import annotations

import argparse
import email
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ALLOWED_RUNTIME_FILES = {
    "vitrine/__init__.py",
    "vitrine/__main__.py",
    "vitrine/_version.py",
    "vitrine/adapter_cli.py",
    "vitrine/audience_services.py",
    "vitrine/cli.py",
    "vitrine/candidate_services.py",
    "vitrine/constants.py",
    "vitrine/curation_services.py",
    "vitrine/curation_state.py",
    "vitrine/snapshot_state.py",
    "vitrine/snapshot_custody.py",
    "vitrine/snapshot_distribution.py",
    "vitrine/snapshot_materialization.py",
    "vitrine/snapshot_planning.py",
    "vitrine/snapshot_sealing.py",
    "vitrine/snapshot_services.py",
    "vitrine/development_adapters.py",
    "vitrine/development_candidate_fixtures.py",
    "vitrine/menu.py",
    "vitrine/identity_state.py",
    "vitrine/profile_state.py",
    "vitrine/profile_services.py",
    "vitrine/profile_cli.py",
    "vitrine/profile_menu.py",
    "vitrine/menu_types.py",
    "vitrine/portfolio_menu.py",
    "vitrine/portfolio_services.py",
    "vitrine/producer_adapters.py",
    "vitrine/subject_cli.py",
    "vitrine/subject_menu.py",
    "vitrine/subject_services.py",
    "vitrine/models/__init__.py",
    "vitrine/models/audiences.py",
    "vitrine/models/candidates.py",
    "vitrine/models/common.py",
    "vitrine/models/conversion.py",
    "vitrine/models/curation.py",
    "vitrine/models/curation_workflow.py",
    "vitrine/models/errors.py",
    "vitrine/models/graph.py",
    "vitrine/models/identity.py",
    "vitrine/models/profiles.py",
    "vitrine/models/serialization.py",
    "vitrine/models/snapshot_workflow.py",
    "vitrine/models/snapshots.py",
    "vitrine/models/sources.py",
    "vitrine/record_registry.py",
    "vitrine/storage/__init__.py",
    "vitrine/storage/catalog.py",
    "vitrine/storage/diagnostics.py",
    "vitrine/storage/errors.py",
    "vitrine/storage/models.py",
    "vitrine/storage/paths.py",
    "vitrine/storage/serialization.py",
    "vitrine/storage/store.py",
    "vitrine/py.typed",
    "vitrine/workflow_cli.py",
    "vitrine/workflow_context.py",
    "vitrine/workflow_views.py",
    "vitrine/workspace.py",
}
REQUIRED_SDIST_FILES = {
    "CHANGELOG.md",
    "MANIFEST.in",
    "RELEASE_NOTES_v0.2.0.md",
    "README.md",
    "Security.md",
    "docs/release_checklist.md",
    "docs/v0.2.0-release-audit.md",
    "docs/v0.2.0-release-compatibility.md",
    "docs/contracts/foundational-runtime-models-v1.md",
    "docs/contracts/canonical-storage-v1.md",
    "docs/contracts/portfolio-subject-workflows-v1.md",
    "docs/contracts/portfolio-profile-workflows-v1.md",
    "docs/contracts/producer-projection-adapters-v1.md",
    "docs/contracts/candidate-discovery-evaluation-v1.md",
    "docs/contracts/curation-workflows-v1.md",
    "docs/contracts/snapshot-build-workflows-v1.md",
    "docs/development/runtime-models.md",
    "docs/development/canonical-storage.md",
    "docs/development/portfolio-subject-workflows.md",
    "docs/development/portfolio-profile-workflows.md",
    "docs/development/producer-adapters.md",
    "docs/development/candidate-discovery.md",
    "docs/development/curation-workflows.md",
    "docs/development/snapshot-build-workflows.md",
    "docs/development/improvement-portfolio-vertical-slice.md",
    "docs/development/interface-workflows.md",
    "docs/development/showcase-portfolio-vertical-slice.md",
    "docs/development/installed-end-to-end-acceptance.md",
    "fixtures/producer-adapters/README.md",
    "fixtures/producer-adapters/scoreform/manifest.json",
    "fixtures/producer-adapters/quillan/manifest.json",
    "fixtures/producer-adapters/concord/manifest.json",
    "fixtures/installed-acceptance/scoreform-manifest.json",
    "fixtures/installed-acceptance/source-root/artifacts/baseline-argument.txt",
    "fixtures/installed-acceptance/source-root/artifacts/revised-argument.txt",
    "fixtures/installed-acceptance/source-root/artifacts/revised-feedback.txt",
    "fixtures/installed-acceptance/source-root/artifacts/polished-literary-analysis.txt",
    "fixtures/installed-acceptance/source-root/artifacts/group-artifact.txt",
    "fixtures/snapshot-workflows/README.md",
    "fixtures/snapshot-workflows/fixture-index.json",
    "fixtures/snapshot-workflows/source-root/artifacts/selected-analysis.txt",
    "fixtures/snapshot-workflows/source-root/artifacts/approved-paragraph.txt",
    "fixtures/snapshot-workflows/source-root/artifacts/student-feedback.md",
    "fixtures/snapshot-workflows/structured/scoreform-attempt-1.json",
    "fixtures/snapshot-workflows/expected/scoreform-attempt-1.md",
    "fixtures/snapshot-workflows/expected/reflection.md",
    "pyproject.toml",
    "run_tests.ps1",
    "scripts/check_documentation.py",
    "scripts/check_package.py",
    "scripts/smoke_test_wheel.py",
    "scripts/smoke_test_adapter_wheel.py",
    "scripts/smoke_test_candidate_wheel.py",
    "scripts/smoke_test_curation_wheel.py",
    "scripts/smoke_test_snapshot_wheel.py",
    "scripts/smoke_test_end_to_end_wheel.py",
    "scripts/verify_installed_end_to_end.py",
    "scripts/verify_installed_end_to_end_reload.py",
    "scripts/validate_portfolio_foundation.py",
    "scripts/validate_repository.py",
    "scripts/validate_release_contract.py",
    "scripts/validate_representative_portfolios.py",
    "scripts/validate_runtime_models.py",
    "scripts/validate_canonical_storage.py",
    "scripts/validate_subject_workflows.py",
    "scripts/validate_profile_workflows.py",
    "scripts/validate_producer_adapters.py",
    "scripts/validate_candidate_discovery.py",
    "scripts/validate_curation_workflows.py",
    "scripts/validate_snapshot_workflows.py",
    "scripts/validate_improvement_portfolio.py",
    "scripts/validate_interface_workflows.py",
    "scripts/validate_showcase_portfolio.py",
    "scripts/candidate_fixture_support.py",
    "scripts/curation_fixture_support.py",
    "scripts/snapshot_fixture_support.py",
    "scripts/improvement_portfolio_fixture_support.py",
    "scripts/showcase_portfolio_fixture_support.py",
    "scripts/verify_core_wheel.py",
    "tests/fixtures/runtime-models/improvement-foundational-records-v1.json",
    "tests/fixtures/runtime-models/showcase-foundational-records-v1.json",
    "tests/runtime_fixture_factory.py",
    "tests/test_cli.py",
    "tests/test_adapter_cli.py",
    "tests/test_runtime_graph.py",
    "tests/test_runtime_models.py",
    "tests/test_runtime_serialization.py",
    "tests/test_validate_runtime_models.py",
    "tests/storage_helpers.py",
    "tests/test_storage_models.py",
    "tests/test_storage_paths.py",
    "tests/test_storage_commits.py",
    "tests/test_storage_reads.py",
    "tests/test_storage_serialization.py",
    "tests/test_storage_catalog.py",
    "tests/test_storage_diagnostics.py",
    "tests/subject_helpers.py",
    "tests/test_subject_identity_models.py",
    "tests/test_subject_services.py",
    "tests/test_subject_cli.py",
    "tests/test_subject_menu.py",
    "tests/test_validate_subject_workflows.py",
    "tests/profile_helpers.py",
    "tests/test_profile_models.py",
    "tests/test_profile_services.py",
    "tests/test_profile_cli.py",
    "tests/test_profile_menu.py",
    "tests/test_validate_profile_workflows.py",
    "tests/test_producer_adapters.py",
    "tests/test_validate_producer_adapters.py",
    "tests/test_candidate_services.py",
    "tests/test_candidate_discovery.py",
    "tests/test_validate_candidate_discovery.py",
    "tests/test_curation_models.py",
    "tests/test_curation_state.py",
    "tests/test_curation_services.py",
    "tests/test_curation_workflows.py",
    "tests/test_validate_curation_workflows.py",
    "tests/test_snapshot_workflow_models.py",
    "tests/test_snapshot_state.py",
    "tests/test_snapshot_persistence_wiring.py",
    "tests/test_snapshot_custody.py",
    "tests/test_snapshot_materialization.py",
    "tests/test_snapshot_sealing.py",
    "tests/test_snapshot_services.py",
    "tests/test_validate_snapshot_workflows.py",
    "tests/test_improvement_portfolio_vertical_slice.py",
    "tests/test_portfolio_menu.py",
    "tests/test_portfolio_services.py",
    "tests/test_workflow_cli.py",
    "tests/test_workflow_views.py",
    "tests/test_validate_improvement_portfolio.py",
    "tests/test_showcase_portfolio_vertical_slice.py",
    "tests/test_validate_showcase_portfolio.py",
    "tests/test_installed_end_to_end_acceptance.py",
    "tests/test_validate_release_contract.py",
    "fixtures/representative-portfolios/improvement/runtime/baseline-manifest.json",
    "fixtures/representative-portfolios/improvement/runtime/later-manifest.json",
    "fixtures/representative-portfolios/showcase/runtime/polished-manifest.json",
    "fixtures/representative-portfolios/showcase/runtime/concord-manifest.json",
    "vitrine/py.typed",
}


def _metadata_findings(metadata_bytes: bytes) -> list[str]:
    findings: list[str] = []
    metadata = email.message_from_bytes(metadata_bytes)
    if metadata.get("Name") != "pds-vitrine":
        findings.append(f"unexpected distribution name: {metadata.get('Name')}")
    if metadata.get("Version") != "0.2.0":
        findings.append(f"unexpected version: {metadata.get('Version')}")
    if metadata.get("Requires-Python") != ">=3.11":
        findings.append(
            f"unexpected Requires-Python: {metadata.get('Requires-Python')}"
        )
    requirements = metadata.get_all("Requires-Dist", [])
    normalized = [item.replace(" ", "") for item in requirements]
    if not any("pds-core<0.7,>=0.6" in item for item in normalized):
        findings.append(f"missing Core dependency range: {requirements}")
    sibling_names = (
        "pds-scoreform",
        "pds-quillan",
        "pds-concord",
        "pds-portia",
        "pds-meridian",
    )
    if any(any(name in item.lower() for name in sibling_names) for item in requirements):
        findings.append(f"forbidden producer runtime dependency: {requirements}")
    return findings


def _unsafe_path(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)


def validate_wheel(path: Path) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            return [f"corrupt wheel member: {corrupt_member}"]
        names = set(archive.namelist())
        dist_info_roots = {
            PurePosixPath(name).parts[0]
            for name in names
            if PurePosixPath(name).parts
            and PurePosixPath(name).parts[0].endswith(".dist-info")
        }
        if len(dist_info_roots) != 1:
            findings.append(
                f"expected exactly one dist-info directory: {sorted(dist_info_roots)}"
            )
        allowed_metadata_root = next(iter(dist_info_roots), None)
        runtime = {name for name in names if name.startswith("vitrine/")}
        unexpected = sorted(runtime - ALLOWED_RUNTIME_FILES)
        missing = sorted(ALLOWED_RUNTIME_FILES - runtime)
        if unexpected:
            findings.append(f"unexpected runtime files: {unexpected}")
        if missing:
            findings.append(f"missing runtime files: {missing}")
        forbidden_prefixes = (
            ".github/",
            "docs/",
            "fixtures/",
            "scripts/",
            "tests/",
        )
        for name in sorted(names):
            if name.startswith(forbidden_prefixes):
                findings.append(f"forbidden wheel content: {name}")
            if "__pycache__/" in name or name.endswith((".pyc", ".pyo")):
                findings.append(f"forbidden wheel cache content: {name}")
            if _unsafe_path(name):
                findings.append(f"unsafe wheel path: {name}")
            is_runtime = name in ALLOWED_RUNTIME_FILES
            is_metadata = (
                allowed_metadata_root is not None
                and name.startswith(f"{allowed_metadata_root}/")
            )
            if not is_runtime and not is_metadata:
                findings.append(f"unexpected top-level wheel content: {name}")
        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        entry_names = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(metadata_names) != 1:
            findings.append("expected exactly one METADATA file")
        else:
            findings.extend(_metadata_findings(archive.read(metadata_names[0])))
        if len(entry_names) != 1:
            findings.append("expected exactly one entry_points.txt")
        else:
            entries = archive.read(entry_names[0]).decode("utf-8")
            if "vitrine = vitrine.cli:main" not in entries:
                findings.append("missing vitrine console entry point")
            if "paper_data_suite.modules" in entries:
                findings.append("routing entry point must not be declared")
            if "paper_data_suite.publication_producers" in entries:
                findings.append("publication-producer entry point must not be declared")
    return findings


def validate_sdist(path: Path) -> list[str]:
    findings: list[str] = []
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if _unsafe_path(member.name):
                findings.append(f"unsafe sdist path: {member.name}")
            if member.issym() or member.islnk():
                findings.append(f"sdist link member is not allowed: {member.name}")
        file_names = [member.name for member in members if member.isfile()]
        roots = {PurePosixPath(name).parts[0] for name in file_names if name}
        if len(roots) != 1:
            findings.append(f"sdist must have one root directory: {sorted(roots)}")
            return findings
        root_name = next(iter(roots))
        relative_names = {
            PurePosixPath(name).relative_to(root_name).as_posix()
            for name in file_names
        }
        for name in file_names:
            if "/.git/" in f"/{name}/" or "__pycache__/" in name:
                findings.append(f"forbidden sdist content: {name}")
        missing = sorted(REQUIRED_SDIST_FILES - relative_names)
        if missing:
            findings.append(f"missing required sdist files: {missing}")
        try:
            metadata_member = archive.getmember(f"{root_name}/PKG-INFO")
        except KeyError:
            findings.append("sdist PKG-INFO is missing")
        else:
            metadata_handle = archive.extractfile(metadata_member)
            if metadata_handle is None:
                findings.append("sdist PKG-INFO is unreadable")
            else:
                findings.extend(_metadata_findings(metadata_handle.read()))
    return findings


def validate_artifact(path: Path) -> list[str]:
    if path.suffix == ".whl":
        return validate_wheel(path)
    if path.name.endswith(".tar.gz"):
        return validate_sdist(path)
    return [f"unsupported distribution artifact: {path}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args(argv)
    findings: list[str] = []
    for artifact in args.artifacts:
        findings.extend(
            f"{artifact}: {finding}" for finding in validate_artifact(artifact)
        )
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS distribution content validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
