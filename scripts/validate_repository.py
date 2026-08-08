"""Run the complete reusable Vitrine repository validation sequence."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _git_status(root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _copy_build_source(root: Path, destination: Path) -> Path:
    """Copy the working source into a disposable build tree."""
    ignored_names = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "htmlcov",
        "pds_vitrine.egg-info",
        "venv",
    }

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in ignored_names
            or name == "__pycache__"
            or name.endswith(".egg-info")
            or name.endswith((".pyc", ".pyo"))
        }

    shutil.copytree(root, destination, ignore=ignore)
    return destination


def validate(core_wheel: Path, *, allow_dirty: bool) -> None:
    root = Path(__file__).resolve().parents[1]
    initial_status = _git_status(root)
    if initial_status and not allow_dirty:
        raise RuntimeError("repository must be clean; use --allow-dirty during development")
    with tempfile.TemporaryDirectory(prefix="vitrine-validation-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RUFF_CACHE_DIR"] = str(temp / "ruff-cache")
        env["MYPY_CACHE_DIR"] = str(temp / "mypy-cache")
        _run(
            [sys.executable, "scripts/verify_core_wheel.py", str(core_wheel)],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/verify_core_wheel.py", "--installed"],
            cwd=root,
            env=env,
        )
        _run([sys.executable, "-m", "pip", "check"], cwd=root, env=env)
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--basetemp",
                str(temp / "pytest"),
                "-o",
                f"cache_dir={temp / 'pytest-cache'}",
            ],
            cwd=root,
            env=env,
        )
        _run([sys.executable, "-m", "ruff", "check", "."], cwd=root, env=env)
        _run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--cache-dir",
                str(temp / "mypy-cache"),
            ],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/validate_runtime_models.py"],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/validate_canonical_storage.py"],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/validate_subject_workflows.py"],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/validate_profile_workflows.py"],
            cwd=root,
            env=env,
        )
        _run([sys.executable, "scripts/check_documentation.py"], cwd=root, env=env)
        _run(
            [sys.executable, "scripts/validate_representative_portfolios.py"],
            cwd=root,
            env=env,
        )
        _run(
            [sys.executable, "scripts/validate_portfolio_foundation.py"],
            cwd=root,
            env=env,
        )
        build_source = _copy_build_source(root, temp / "source")
        dist = temp / "dist"
        _run(
            [sys.executable, "-m", "build", "--outdir", str(dist)],
            cwd=build_source,
            env=env,
        )
        artifacts = [str(path) for path in sorted(dist.iterdir())]
        _run(
            [sys.executable, "-m", "twine", "check", *artifacts],
            cwd=root,
            env=env,
        )
        wheels = list(dist.glob("*.whl"))
        source_distributions = list(dist.glob("*.tar.gz"))
        if len(wheels) != 1 or len(source_distributions) != 1:
            raise RuntimeError(
                "expected exactly one Vitrine wheel and one source distribution"
            )
        _run(
            [
                sys.executable,
                "scripts/check_package.py",
                str(wheels[0]),
                str(source_distributions[0]),
            ],
            cwd=root,
            env=env,
        )
        _run(
            [
                sys.executable,
                "scripts/smoke_test_wheel.py",
                str(wheels[0]),
                str(core_wheel),
            ],
            cwd=root,
            env=env,
        )
        _run(["git", "diff", "--check"], cwd=root, env=env)
    final_status = _git_status(root)
    if allow_dirty:
        if final_status != initial_status:
            raise RuntimeError("validation changed the working tree")
    elif final_status:
        raise RuntimeError("validation left repository residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-wheel", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(args.core_wheel, allow_dirty=args.allow_dirty)
        print("PASS complete repository validation")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Repository validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
