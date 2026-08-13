"""Smoke issue #35 Snapshot imports from isolated installed wheels."""

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


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-snapshot-wheel-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
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
        code = """
import importlib.util
from vitrine.models import (
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotExportArtifact,
    SnapshotSeries,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_services import (
    SnapshotWorkflowError,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    seal_snapshot_build_attempt,
)
from vitrine.snapshot_state import SnapshotState, project_snapshot_state

for name in ('scoreform', 'quillan', 'concord', 'portia', 'meridian'):
    assert importlib.util.find_spec(name) is None
assert SnapshotState is not None
assert project_snapshot_state(()) is not None
assert SnapshotSeries is not None
assert SnapshotBuildRequest is not None
assert SnapshotBuildPlan is not None
assert SnapshotBuildAttempt is not None
assert SnapshotExportArtifact is not None
assert SnapshotCurrentPointerRevision is not None
assert SnapshotBuildAuthorityDecision(outcome='denied').outcome == 'denied'
assert SnapshotSourceProviderRegistry() is not None
assert SnapshotRendererRegistry() is not None
assert SnapshotWorkflowError is not None
assert SnapshotDistributionError is not None
assert create_snapshot_series is not None
assert execute_snapshot_build_attempt is not None
assert seal_snapshot_build_attempt is not None
assert inspect_snapshot_custody is not None
assert verify_snapshot_edition is not None
assert verify_snapshot_export is not None
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError("Snapshot wheel smoke left current-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Snapshot workflow wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Snapshot wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
