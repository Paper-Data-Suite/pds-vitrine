"""Smoke packaged starter Profiles from isolated Core and Vitrine wheels."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _workspace_code() -> str:
    return r"""
from pathlib import Path
import sys
from pds_core.workspace import ensure_workspace_root

workspace = Path(sys.argv[1])
ensure_workspace_root(workspace)
"""


def _state_revision_code() -> str:
    return r"""
from pathlib import Path
import sys
from vitrine.profile_services import observe_profile_state_revision

workspace = Path(sys.argv[1])
print("none" if observe_profile_state_revision(workspace) is None else "present")
"""


def _verify_installed_code() -> str:
    return r"""
from pathlib import Path
import sys

from vitrine.profile_services import (
    list_bindable_profile_revisions,
    list_profile_families,
    list_profile_revisions,
    load_profile_state,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_records

workspace = Path(sys.argv[1])
expected_revision = int(sys.argv[2])
current = observe_profile_state_revision(workspace)
assert current == expected_revision

families = list_profile_families(workspace)
assert any(
    item.profile_family_id == "vitrine_starter_improvement_family"
    for item in families
)
revisions = list_profile_revisions(
    workspace,
    portfolio_profile_id="vitrine_starter_improvement",
)
assert len(revisions) == 1
assert revisions[0].reference.profile_revision == 1
assert revisions[0].lifecycle_status == "activated"
assert revisions[0].requirement_count == 4

bindable = list_bindable_profile_revisions(workspace)
assert any(
    item.reference.portfolio_profile_id == "vitrine_starter_improvement"
    and item.reference.profile_revision == 1
    for item in bindable
)
state, state_revision = load_profile_state(workspace)
assert state_revision == expected_revision
assert state.portfolios == ()
assert state.bindings == ()
activation_events = tuple(
    item
    for item in state.lifecycle_events
    if item.profile_revision.portfolio_profile_id == "vitrine_starter_improvement"
    and item.profile_revision.profile_revision == 1
    and item.event_kind == "activated"
)
assert len(activation_events) == 1

allowed_record_types = {
    "portfolio_profile_family",
    "portfolio_profile_revision",
    "portfolio_profile_requirement",
    "portfolio_profile_lifecycle_event",
}
records = load_current_records(workspace)
assert records
assert {item.record_type for item in records}.issubset(allowed_record_types)
"""


def _dependency_isolation_code() -> str:
    return r"""
from importlib import metadata

for distribution in ("scoreform", "pds-scoreform", "quillan", "pds-quillan", "pds-concord"):
    try:
        metadata.version(distribution)
    except metadata.PackageNotFoundError:
        continue
    raise AssertionError(f"unexpected sibling producer distribution installed: {distribution}")
"""


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="vitrine-starter-wheel-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        workspace = root / "workspace"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PDS_WORKSPACE_ROOT"] = str(root / "default-workspace")

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
        _run(
            [str(python), "-c", _dependency_isolation_code()],
            cwd=work,
            env=env,
        )

        package_path = _run(
            [
                str(python),
                "-c",
                "import json,vitrine; print(json.dumps(vitrine.__path__[0]))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package_path.stdout))
        if not installed.is_dir() or repository in installed.parents:
            raise RuntimeError("starter smoke did not import the isolated installed wheel")
        installed_before = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }

        command = [str(python), "-m", "vitrine", "profile", "starter"]
        listed = _run([*command, "list"], cwd=work, env=env)
        if (
            "improvement_portfolio_v1" not in listed.stdout
            or "showcase_portfolio_v1" not in listed.stdout
        ):
            raise RuntimeError("installed starter list omitted a frozen starter")
        shown = _run(
            [*command, "show", "improvement_portfolio_v1"],
            cwd=work,
            env=env,
        )
        if "Profile: vitrine_starter_improvement@1" not in shown.stdout:
            raise RuntimeError("installed starter show did not expose the exact Revision")
        for starter_id in (
            "improvement_portfolio_v1",
            "showcase_portfolio_v1",
        ):
            validated = _run(
                [*command, "validate", starter_id],
                cwd=work,
                env=env,
            )
            if f"PASS starter Profile: {starter_id}" not in validated.stdout:
                raise RuntimeError("installed starter validate did not report PASS")

        _run(
            [str(python), "-c", _workspace_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        before_plan = _run(
            [str(python), "-c", _state_revision_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        if before_plan.stdout.strip() != "none":
            raise RuntimeError("fresh Core workspace unexpectedly has Vitrine state")
        plan = _run(
            [
                *command,
                "plan",
                "improvement_portfolio_v1",
                "--workspace-root",
                str(workspace),
            ],
            cwd=work,
            env=env,
        )
        if "Lifecycle disposition: activate_new" not in plan.stdout:
            raise RuntimeError("fresh starter plan did not propose explicit activation")
        after_plan = _run(
            [str(python), "-c", _state_revision_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        if after_plan.stdout.strip() != "none":
            raise RuntimeError("starter plan mutated canonical Vitrine state")

        install_args = [
            *command,
            "install",
            "improvement_portfolio_v1",
            "--actor-id",
            "teacher_starter_smoke",
            "--authority-reference",
            "installed_wheel_smoke",
            "--reason",
            "Explicit installed-wheel starter acceptance.",
            "--confirm",
            "--workspace-root",
            str(workspace),
        ]
        first_install = _run(install_args, cwd=work, env=env)
        if "State revision:" not in first_install.stdout:
            raise RuntimeError("confirmed starter install did not commit canonical state")
        revision_text = next(
            line.split(":", 1)[1].strip()
            for line in first_install.stdout.splitlines()
            if line.startswith("State revision:")
        )
        installed_revision = int(revision_text)
        _run(
            [
                str(python),
                "-c",
                _verify_installed_code(),
                str(workspace),
                str(installed_revision),
            ],
            cwd=work,
            env=env,
        )

        second_install = _run(install_args, cwd=work, env=env)
        if "No change: exact starter definition is already active" not in second_install.stdout:
            raise RuntimeError("second exact starter install was not idempotent")
        _run(
            [
                str(python),
                "-c",
                _verify_installed_code(),
                str(workspace),
                str(installed_revision),
            ],
            cwd=work,
            env=env,
        )

        installed_after = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }
        if installed_after != installed_before:
            raise RuntimeError("starter workflows modified installed package files")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS installed starter Profile wheel smoke")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Starter Profile wheel smoke failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
