"""Install Core and Vitrine wheels in isolation and smoke the baseline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _run(command: list[str], *, cwd: Path, env: dict[str, str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _console_path(python: Path) -> Path:
    code = "import json,sysconfig; print(json.dumps(sysconfig.get_path('scripts')))"
    result = subprocess.run(
        [str(python), "-c", code],
        text=True,
        capture_output=True,
        check=True,
    )
    scripts = Path(json.loads(result.stdout))
    return scripts / ("vitrine.exe" if os.name == "nt" else "vitrine")


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    source_before = {path: path.stat().st_mtime_ns for path in repository.rglob("*") if path.is_file() and ".git" not in path.parts}
    with tempfile.TemporaryDirectory(prefix="vitrine-wheel-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        workspace = root / "workspace"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PDS_WORKSPACE_ROOT"] = str(root / "environment-workspace")
        _run([str(python), "-m", "pip", "install", str(core_wheel.resolve())], cwd=work, env=env)
        _run([str(python), "-m", "pip", "install", "--no-deps", str(vitrine_wheel.resolve())], cwd=work, env=env)
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
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
        if not installed.is_dir():
            raise RuntimeError("installed package path is missing")
        installed_before = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }
        console = _console_path(python)
        _run([str(console), "--version"], cwd=work, env=env)
        _run([str(console), "--help"], cwd=work, env=env)
        _run([str(python), "-m", "vitrine", "--version"], cwd=work, env=env)
        _run([str(python), "-m", "vitrine", "--help"], cwd=work, env=env)
        _run([str(console), "menu"], cwd=work, env=env, input_text="Q\n")
        _run([str(console), "workspace", "show", "--workspace-root", str(workspace)], cwd=work, env=env)
        if workspace.exists():
            raise RuntimeError("workspace show created the workspace")
        _run([str(console), "workspace", "validate", "--workspace-root", str(workspace)], cwd=work, env=env)
        if not (workspace / ".pds" / "workspace.json").is_file():
            raise RuntimeError("workspace validate did not create Core metadata")
        _run(
            [str(console), "workspace", "show", "--workspace-root", str(workspace)],
            cwd=work,
            env=env,
        )
        installed_after = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }
        if installed_before != installed_after:
            raise RuntimeError("Vitrine commands modified the installed package")
        residue = [path for path in work.iterdir()]
        if residue:
            raise RuntimeError(f"smoke current directory contains residue: {residue}")
    source_after = {path: path.stat().st_mtime_ns for path in repository.rglob("*") if path.is_file() and ".git" not in path.parts}
    if source_before != source_after:
        raise RuntimeError("installed-wheel smoke test modified the source checkout")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated installed-wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Wheel smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
