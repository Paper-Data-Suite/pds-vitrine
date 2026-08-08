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
    "vitrine/cli.py",
    "vitrine/constants.py",
    "vitrine/menu.py",
    "vitrine/identity_state.py",
    "vitrine/profile_state.py",
    "vitrine/profile_services.py",
    "vitrine/profile_cli.py",
    "vitrine/profile_menu.py",
    "vitrine/menu_types.py",
    "vitrine/subject_cli.py",
    "vitrine/subject_menu.py",
    "vitrine/subject_services.py",
    "vitrine/models/__init__.py",
    "vitrine/models/audiences.py",
    "vitrine/models/candidates.py",
    "vitrine/models/common.py",
    "vitrine/models/conversion.py",
    "vitrine/models/curation.py",
    "vitrine/models/errors.py",
    "vitrine/models/graph.py",
    "vitrine/models/identity.py",
    "vitrine/models/profiles.py",
    "vitrine/models/serialization.py",
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
    "vitrine/workspace.py",
}
REQUIRED_SDIST_FILES = {
    "CHANGELOG.md",
    "MANIFEST.in",
    "README.md",
    "Security.md",
    "docs/contracts/foundational-runtime-models-v1.md",
    "docs/contracts/canonical-storage-v1.md",
    "docs/contracts/portfolio-subject-workflows-v1.md",
    "docs/contracts/portfolio-profile-workflows-v1.md",
    "docs/development/runtime-models.md",
    "docs/development/canonical-storage.md",
    "docs/development/portfolio-subject-workflows.md",
    "docs/development/portfolio-profile-workflows.md",
    "pyproject.toml",
    "run_tests.ps1",
    "scripts/check_documentation.py",
    "scripts/check_package.py",
    "scripts/smoke_test_wheel.py",
    "scripts/validate_portfolio_foundation.py",
    "scripts/validate_repository.py",
    "scripts/validate_representative_portfolios.py",
    "scripts/validate_runtime_models.py",
    "scripts/validate_canonical_storage.py",
    "scripts/validate_subject_workflows.py",
    "scripts/validate_profile_workflows.py",
    "scripts/verify_core_wheel.py",
    "tests/fixtures/runtime-models/improvement-foundational-records-v1.json",
    "tests/fixtures/runtime-models/showcase-foundational-records-v1.json",
    "tests/runtime_fixture_factory.py",
    "tests/test_cli.py",
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
    "vitrine/py.typed",
}


def _metadata_findings(metadata_bytes: bytes) -> list[str]:
    findings: list[str] = []
    metadata = email.message_from_bytes(metadata_bytes)
    if metadata.get("Name") != "pds-vitrine":
        findings.append(f"unexpected distribution name: {metadata.get('Name')}")
    if metadata.get("Version") != "0.2.0.dev0":
        findings.append(f"unexpected version: {metadata.get('Version')}")
    if metadata.get("Requires-Python") != ">=3.11":
        findings.append(
            f"unexpected Requires-Python: {metadata.get('Requires-Python')}"
        )
    requirements = metadata.get_all("Requires-Dist", [])
    normalized = [item.replace(" ", "") for item in requirements]
    if not any("pds-core<0.7,>=0.6" in item for item in normalized):
        findings.append(f"missing Core dependency range: {requirements}")
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
    print(f"PASS distribution content: {len(args.artifacts)} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
