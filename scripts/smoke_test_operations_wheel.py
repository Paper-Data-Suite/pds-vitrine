"""Smoke issue #70 Core operations integration from isolated wheels."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_script(environment: Path, name: str) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / f"{name}.exe"
    return environment / "bin" / name


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "(no child output)"
        raise RuntimeError(
            "operations installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-operations-wheel-smoke-"
    ) as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        implicit_workspace = root / "implicit-workspace"
        explicit_workspace = root / "explicit-workspace"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        vitrine_script = _venv_script(environment, "vitrine")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PDS_WORKSPACE_ROOT"] = str(implicit_workspace)

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
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
                str(vitrine_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        version_output = _run([str(vitrine_script), "--version"], cwd=work, env=env)
        if "0.2.0" not in version_output:
            raise RuntimeError(
                "installed vitrine console script returned wrong version"
            )

        code = r'''\
import importlib.metadata
import importlib.util
import sys
from pathlib import Path

from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    MODULE_OPERATIONS_ENTRY_POINT_GROUP,
    ModuleOperationsRequest,
    invoke_module_attention,
    invoke_module_readiness,
)
from pds_core.provider_diagnostics import (
    diagnose_core_providers,
    inspect_core_provider_entry_points,
)
from pds_core.workspace import ensure_workspace_root

implicit_workspace = Path(sys.argv[1])
explicit_workspace = Path(sys.argv[2])

assert importlib.metadata.version("pds-core") == "0.6.3"
assert importlib.metadata.version("pds-vitrine") == "0.2.0"
assert MODULE_OPERATIONS_CONTRACT_VERSION == "1"
assert MODULE_OPERATIONS_ENTRY_POINT_GROUP == "paper_data_suite.module_operations"
assert not implicit_workspace.exists()
assert not explicit_workspace.exists()

metadata_rows = tuple(
    item
    for item in inspect_core_provider_entry_points(provider_kind="module_operations")
    if item.entry_point_name == "vitrine"
)
assert len(metadata_rows) == 1
metadata_row = metadata_rows[0]
assert metadata_row.entry_point_group == "paper_data_suite.module_operations"
assert metadata_row.entry_point_target == (
    "vitrine.pds_operations:get_module_operations_profile"
)
assert metadata_row.distribution_name == "pds-vitrine"
assert not implicit_workspace.exists()
assert not explicit_workspace.exists()

diagnostics = tuple(
    item
    for item in diagnose_core_providers(provider_kind="module_operations")
    if item.metadata.entry_point_name == "vitrine"
)
assert len(diagnostics) == 1
diagnostic = diagnostics[0]
assert diagnostic.stage == "valid"
assert diagnostic.code == "provider.valid"
assert diagnostic.declared_identity == "vitrine"
assert diagnostic.profile_validation == "passed"
assert diagnostic.core_compatibility == "passed"
assert diagnostic.registry_conflict is False
assert diagnostic.validated_profile is not None
profile = diagnostic.validated_profile
assert profile.module_id == "vitrine"
assert profile.supported_core_operations_contract_versions == frozenset({"1"})
assert profile.readiness_provider is not None
assert profile.attention_provider is not None
assert not implicit_workspace.exists()
assert not explicit_workspace.exists()

no_workspace = invoke_module_readiness(profile, ModuleOperationsRequest())
assert no_workspace.code == "module_operations.evaluation_unavailable"
assert no_workspace.report is not None
assert no_workspace.report.evaluation == "unavailable"
assert no_workspace.report.ready is None
assert tuple(item.code for item in no_workspace.report.notices) == (
    "vitrine_readiness_workspace_required",
)
assert not implicit_workspace.exists()
assert not explicit_workspace.exists()

class_scope = invoke_module_attention(
    profile,
    ModuleOperationsRequest(
        workspace_root=explicit_workspace,
        active_school_year="2026-2027",
        class_id="english-10",
    ),
)
assert class_scope.code == "module_operations.evaluation_unavailable"
assert class_scope.report is not None
assert class_scope.report.evaluation == "unavailable"
assert class_scope.report.summaries == ()
assert tuple(item.code for item in class_scope.report.notices) == (
    "vitrine_attention_class_scope_unsupported",
)
assert not implicit_workspace.exists()
assert not explicit_workspace.exists()

workspace = ensure_workspace_root(explicit_workspace, create=True)
before = tuple(sorted(path.relative_to(workspace) for path in workspace.rglob("*")))
ready = invoke_module_readiness(
    profile,
    ModuleOperationsRequest(
        workspace_root=workspace,
        active_school_year="2026-2027",
        class_id="english-10",
    ),
)
assert ready.code == "module_operations.evaluated"
assert ready.report is not None
assert ready.report.evaluation == "evaluated"
assert ready.report.ready is True
assert ready.report.notices == ()
assert not (workspace / "vitrine").exists()
assert (
    tuple(sorted(path.relative_to(workspace) for path in workspace.rglob("*")))
    == before
)

attention = invoke_module_attention(
    profile,
    ModuleOperationsRequest(workspace_root=workspace),
)
assert attention.code == "module_operations.evaluation_unavailable"
assert attention.report is not None
assert attention.report.evaluation == "unavailable"
assert attention.report.summaries == ()
assert tuple(item.code for item in attention.report.notices) == (
    "vitrine_attention_unavailable",
)
assert not (workspace / "vitrine").exists()
assert (
    tuple(sorted(path.relative_to(workspace) for path in workspace.rglob("*")))
    == before
)

(workspace / "vitrine").mkdir()
namespace_before = tuple(
    sorted(path.relative_to(workspace) for path in workspace.rglob("*"))
)
blocked = invoke_module_readiness(
    profile,
    ModuleOperationsRequest(workspace_root=workspace),
)
assert blocked.code == "module_operations.evaluated"
assert blocked.report is not None
assert blocked.report.evaluation == "evaluated"
assert blocked.report.ready is False
assert tuple(item.code for item in blocked.report.notices) == (
    "vitrine_readiness_storage_blocked",
)
assert (
    tuple(sorted(path.relative_to(workspace) for path in workspace.rglob("*")))
    == namespace_before
)

console = tuple(
    item
    for item in importlib.metadata.entry_points(group="console_scripts")
    if item.name == "vitrine"
)
assert len(console) == 1
assert console[0].value == "vitrine.cli:main"

for name in (
    "scoreform",
    "quillan",
    "concord",
    "portia",
    "meridian",
    "paper_data_suite",
):
    assert importlib.util.find_spec(name) is None
'''
        _run(
            [
                str(python),
                "-c",
                code,
                str(implicit_workspace),
                str(explicit_workspace),
            ],
            cwd=work,
            env=env,
        )
        if list(work.iterdir()):
            raise RuntimeError("operations wheel smoke left working-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Vitrine module-operations wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Vitrine operations wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
