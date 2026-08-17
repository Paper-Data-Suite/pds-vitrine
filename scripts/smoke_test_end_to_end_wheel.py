"""Run the installed end-to-end acceptance in one isolated wheel environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast


class InstalledAcceptanceHarnessError(RuntimeError):
    """Host-side installed-acceptance orchestration failure."""


PROHIBITED_REPORT_MARKERS = (
    "PRIVATE_",
    "collaborator-syn-001",
    "collaborator-syn-002",
    "recipient authorization",
    "consent obtained",
)


def require_report_safe(report: dict[str, object]) -> None:
    """Reject private/disclosure markers from the public acceptance report."""

    rendered = json.dumps(report, sort_keys=True)
    marker = next((value for value in PROHIBITED_REPORT_MARKERS if value in rendered), None)
    if marker is not None:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance report contains a prohibited privacy/authorization marker"
        )


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    """Content identity for one ordinary file, symlink, or missing tracked path."""

    relative_path: str
    kind: str
    byte_size: int | None
    sha256: str | None
    link_target: str | None = None


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one ordinary file."""

    if not path.is_file() or path.is_symlink():
        raise InstalledAcceptanceHarnessError(
            f"expected an ordinary file for hashing: {path}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_entry(root: Path, relative: Path) -> InventoryEntry:
    path = root / relative
    text = relative.as_posix()
    if path.is_symlink():
        target = os.readlink(path)
        return InventoryEntry(
            relative_path=text,
            kind="symlink",
            byte_size=len(target.encode("utf-8")),
            sha256=hashlib.sha256(target.encode("utf-8")).hexdigest(),
            link_target=target,
        )
    if not path.exists():
        return InventoryEntry(
            relative_path=text,
            kind="missing",
            byte_size=None,
            sha256=None,
        )
    if not path.is_file():
        raise InstalledAcceptanceHarnessError(
            f"inventory path is not an ordinary file: {path}"
        )
    return InventoryEntry(
        relative_path=text,
        kind="file",
        byte_size=path.stat().st_size,
        sha256=sha256_file(path),
    )


def inventory_tree(root: Path) -> tuple[InventoryEntry, ...]:
    """Inventory every file/link under one package or fixture root by content."""

    resolved = root.resolve()
    if not resolved.is_dir():
        raise InstalledAcceptanceHarnessError(
            f"inventory root is not a directory: {resolved}"
        )
    relatives = tuple(
        sorted(
            (
                path.relative_to(resolved)
                for path in resolved.rglob("*")
                if path.is_file() or path.is_symlink()
            ),
            key=lambda item: item.as_posix(),
        )
    )
    return tuple(_inventory_entry(resolved, relative) for relative in relatives)


def _git_text(
    repository: Path,
    arguments: list[str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise InstalledAcceptanceHarnessError(
            "git command failed while inventorying the source checkout: "
            f"{arguments[0]}"
        ) from error


def _git_bytes(
    repository: Path,
    arguments: list[str],
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            capture_output=True,
            text=False,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise InstalledAcceptanceHarnessError(
            "git command failed while inventorying the source checkout: "
            f"{arguments[0]}"
        ) from error


def inventory_git_tracked(repository: Path) -> tuple[InventoryEntry, ...]:
    """Inventory the exact tracked-file set without relying on mtimes."""

    resolved = repository.resolve()
    result = _git_bytes(resolved, ["ls-files", "-z"])
    relatives = tuple(
        sorted(
            (
                Path(value.decode("utf-8"))
                for value in result.stdout.split(b"\0")
                if value
            ),
            key=lambda item: item.as_posix(),
        )
    )
    return tuple(_inventory_entry(resolved, relative) for relative in relatives)


def inventory_git_visible(repository: Path) -> tuple[InventoryEntry, ...]:
    """Inventory tracked plus untracked nonignored checkout files by content."""

    resolved = repository.resolve()
    result = _git_bytes(
        resolved,
        ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    )
    relatives = tuple(
        sorted(
            (
                Path(value.decode("utf-8"))
                for value in result.stdout.split(b"\0")
                if value
            ),
            key=lambda item: item.as_posix(),
        )
    )
    return tuple(_inventory_entry(resolved, relative) for relative in relatives)


def git_status(repository: Path) -> str:
    """Return an exact porcelain snapshot including untracked files."""

    result = _git_text(
        repository.resolve(),
        ["status", "--porcelain", "--untracked-files=all"],
    )
    return result.stdout


def build_isolated_environment(
    base: Mapping[str, str],
    *,
    workspace: Path,
) -> dict[str, str]:
    """Construct the subprocess environment used by installed acceptance."""

    env = dict(base)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PDS_WORKSPACE_ROOT"] = str(workspace.resolve())
    return env


def build_probe_command(
    python: Path,
    verifier: Path,
    *,
    repository: Path,
    fixture_root: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
    boundary_only: bool = False,
    discovery_only: bool = False,
    curation_only: bool = False,
    snapshot_only: bool = False,
) -> list[str]:
    """Build the isolated probe command without repository-root import leakage."""

    selected_modes = sum((boundary_only, discovery_only, curation_only, snapshot_only))
    if selected_modes > 1:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance mode flags are mutually exclusive"
        )
    if boundary_only:
        mode = "--boundary-only"
    elif discovery_only:
        mode = "--discovery-only"
    elif curation_only:
        mode = "--curation-only"
    elif snapshot_only:
        mode = "--snapshot-only"
    else:
        mode = "--end-to-end"
    return [
        str(python),
        "-I",
        "-B",
        str(verifier.resolve()),
        "--repository",
        str(repository.resolve()),
        "--fixture-root",
        str(fixture_root.resolve()),
        "--workspace",
        str(workspace.resolve()),
        "--vitrine-wheel-sha256",
        vitrine_wheel_sha256,
        "--core-wheel-sha256",
        core_wheel_sha256,
        mode,
    ]


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        stdout = (error.stdout or "").strip()
        stderr = (error.stderr or "").strip()
        detail = stderr or stdout or f"exit status {error.returncode}"
        raise InstalledAcceptanceHarnessError(
            f"installed acceptance command failed: {detail}"
        ) from error
    except OSError as error:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance command could not be started"
        ) from error


def _json_report(result: subprocess.CompletedProcess[str], label: str) -> dict[str, object]:
    try:
        raw_report = cast(object, json.loads(result.stdout))
    except json.JSONDecodeError as error:
        raise InstalledAcceptanceHarnessError(
            f"{label} did not return one JSON report"
        ) from error
    if not isinstance(raw_report, dict):
        raise InstalledAcceptanceHarnessError(f"{label} report must be one JSON object")
    return cast(dict[str, object], raw_report)


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _installed_package_root(
    python: Path,
    module_name: str,
    *,
    cwd: Path,
    env: dict[str, str],
) -> Path:
    distribution_name = {
        "vitrine": "pds-vitrine",
        "pds_core": "pds-core",
    }.get(module_name)
    if distribution_name is None:
        raise InstalledAcceptanceHarnessError(
            f"unsupported installed package root lookup: {module_name}"
        )
    code = (
        "import importlib.metadata,json; "
        f"d=importlib.metadata.distribution({distribution_name!r}); "
        f"p=d.locate_file({module_name!r}); "
        "print(json.dumps(str(p)))"
    )
    result = _run([str(python), "-I", "-B", "-c", code], cwd=cwd, env=env)
    try:
        raw_path = cast(object, json.loads(result.stdout))
        if not isinstance(raw_path, str):
            raise TypeError("installed package root JSON must be a string")
        path = Path(raw_path).resolve(strict=True)
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
        raise InstalledAcceptanceHarnessError(
            f"could not resolve installed package root for {module_name}"
        ) from error
    if not path.is_dir():
        raise InstalledAcceptanceHarnessError(
            f"installed package root is not a directory for {module_name}"
        )
    return path


def _require_wheel(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.suffix != ".whl":
        raise InstalledAcceptanceHarnessError(
            f"{label} must be an existing .whl file"
        )
    return resolved


def smoke(
    vitrine_wheel: Path,
    core_wheel: Path,
    *,
    boundary_only: bool = False,
    discovery_only: bool = False,
    curation_only: bool = False,
    snapshot_only: bool = False,
) -> dict[str, object]:
    """Run installed isolation through the implemented acceptance stage."""

    repository = Path(__file__).resolve().parents[1]
    verifier = repository / "scripts" / "verify_installed_end_to_end.py"
    reload_verifier = repository / "scripts" / "verify_installed_end_to_end_reload.py"
    fixture_root = repository / "fixtures"
    if not verifier.is_file():
        raise InstalledAcceptanceHarnessError(
            "installed acceptance verifier is missing from the source checkout"
        )
    if not reload_verifier.is_file():
        raise InstalledAcceptanceHarnessError(
            "historical reload verifier is missing from the source checkout"
        )
    if not fixture_root.is_dir():
        raise InstalledAcceptanceHarnessError(
            "installed acceptance fixture root is missing from the source checkout"
        )
    vitrine = _require_wheel(vitrine_wheel, "Vitrine wheel")
    core = _require_wheel(core_wheel, "Core wheel")
    source_before = inventory_git_visible(repository)
    status_before = git_status(repository)
    fixtures_before = inventory_tree(fixture_root)
    vitrine_digest = sha256_file(vitrine)
    core_digest = sha256_file(core)

    with tempfile.TemporaryDirectory(prefix="vitrine-installed-e2e-") as raw:
        root = Path(raw)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        workspace = root / "workspace"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = build_isolated_environment(os.environ, workspace=workspace)
        _run(
            [str(python), "-m", "pip", "install", str(core)],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(vitrine),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        vitrine_root = _installed_package_root(
            python, "vitrine", cwd=work, env=env
        )
        core_root = _installed_package_root(
            python, "pds_core", cwd=work, env=env
        )
        vitrine_before = inventory_tree(vitrine_root)
        core_before = inventory_tree(core_root)

        _run(
            [str(python), "-I", "-B", "-m", "vitrine", "--help"],
            cwd=work,
            env=env,
        )
        if workspace.exists():
            raise InstalledAcceptanceHarnessError(
                "installed Vitrine help/read-only inspection created workspace state"
            )
        if inventory_tree(vitrine_root) != vitrine_before:
            raise InstalledAcceptanceHarnessError(
                "installed Vitrine help/read-only inspection changed package content"
            )
        if inventory_tree(core_root) != core_before:
            raise InstalledAcceptanceHarnessError(
                "installed Vitrine help/read-only inspection changed Core package content"
            )

        command = build_probe_command(
            python,
            verifier,
            repository=repository,
            fixture_root=fixture_root,
            workspace=workspace,
            vitrine_wheel_sha256=vitrine_digest,
            core_wheel_sha256=core_digest,
            boundary_only=boundary_only,
            discovery_only=discovery_only,
            curation_only=curation_only,
            snapshot_only=snapshot_only,
        )
        result = _run(command, cwd=work, env=env)
        report = _json_report(result, "installed verifier")
        final_mode = not any((boundary_only, discovery_only, curation_only, snapshot_only))
        if final_mode:
            expectations = report.pop("historical_reload_expectations", None)
            if not isinstance(expectations, dict):
                raise InstalledAcceptanceHarnessError(
                    "primary installed verifier omitted bounded historical expectations"
                )
            expectations_path = root / "historical-reload-expectations.json"
            expectations_path.write_text(
                json.dumps(expectations, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
                newline="\n",
            )
            reload_result = _run(
                [
                    str(python),
                    "-I",
                    "-B",
                    str(reload_verifier.resolve()),
                    "--workspace",
                    str(workspace.resolve()),
                    "--expectations",
                    str(expectations_path.resolve()),
                ],
                cwd=work,
                env=env,
            )
            report["historical_reload"] = _json_report(
                reload_result, "historical reload verifier"
            )
            report["mode"] = "end_to_end"
            report["stages"] = [
                "installed_provenance",
                "fixture_boundary",
                "workspace_identity",
                "profile_setup",
                "core_publication",
                "candidate_discovery",
                "improvement_curation",
                "showcase_curation",
                "improvement_snapshot",
                "showcase_snapshot",
                "source_drift",
                "historical_reload",
                "write_isolation",
            ]
        if boundary_only:
            if workspace.exists():
                raise InstalledAcceptanceHarnessError(
                    "boundary-only installed probe unexpectedly created workspace state"
                )
        elif not (workspace / ".pds" / "workspace.json").is_file():
            raise InstalledAcceptanceHarnessError(
                "installed acceptance probe did not create a Core workspace"
            )

        if inventory_tree(vitrine_root) != vitrine_before:
            raise InstalledAcceptanceHarnessError(
                "installed Vitrine package content changed during acceptance"
            )
        if inventory_tree(core_root) != core_before:
            raise InstalledAcceptanceHarnessError(
                "installed Core package content changed during acceptance"
            )
        if inventory_tree(fixture_root) != fixtures_before:
            raise InstalledAcceptanceHarnessError(
                "installed acceptance changed committed fixture inputs"
            )
        if tuple(work.iterdir()):
            raise InstalledAcceptanceHarnessError(
                "installed acceptance current directory contains residue"
            )
        if final_mode:
            report["write_isolation"] = {
                "installed_vitrine_unchanged": True,
                "installed_core_unchanged": True,
                "fixture_tree_unchanged": True,
                "current_directory_clean": True,
                "help_read_only_side_effect_free": True,
            }
        require_report_safe(report)

    if inventory_git_visible(repository) != source_before:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance changed tracked source-checkout content"
        )
    if git_status(repository) != status_before:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance changed source-checkout status"
        )
    if inventory_tree(fixture_root) != fixtures_before:
        raise InstalledAcceptanceHarnessError(
            "installed acceptance changed fixture content after environment cleanup"
        )
    if not any((boundary_only, discovery_only, curation_only, snapshot_only)):
        isolation = report.get("write_isolation")
        if not isinstance(isolation, dict):
            raise InstalledAcceptanceHarnessError("write-isolation report is absent")
        isolation["source_checkout_unchanged"] = True
        isolation["source_checkout_status_unchanged"] = True
        isolation["fixture_tree_unchanged_after_cleanup"] = True
    require_report_safe(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--boundary-only", action="store_true")
    mode.add_argument("--discovery-only", action="store_true")
    mode.add_argument("--curation-only", action="store_true")
    mode.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = smoke(
            args.vitrine_wheel,
            args.core_wheel,
            boundary_only=args.boundary_only,
            discovery_only=args.discovery_only,
            curation_only=args.curation_only,
            snapshot_only=args.snapshot_only,
        )
    except InstalledAcceptanceHarnessError as error:
        print(f"Installed E2E acceptance failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.boundary_only:
        label = "boundary"
    elif args.discovery_only:
        label = "discovery"
    elif args.curation_only:
        label = "curation"
    elif args.snapshot_only:
        label = "snapshot"
    else:
        label = "end-to-end"
    print(f"PASS installed E2E {label} acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
