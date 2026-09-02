"""Run the complete reusable Vitrine repository validation sequence."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

VALIDATOR_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("runtime models", ("scripts/validate_runtime_models.py",)),
    ("canonical storage", ("scripts/validate_canonical_storage.py",)),
    ("Subject workflows", ("scripts/validate_subject_workflows.py",)),
    ("Profile workflows", ("scripts/validate_profile_workflows.py",)),
    ("producer adapters", ("scripts/validate_producer_adapters.py",)),
    (
        "released producer contracts",
        ("scripts/validate_released_producer_contracts.py",),
    ),
    (
        "producer reader services",
        ("scripts/validate_producer_reader_services.py",),
    ),
    (
        "live ScoreForm adapter",
        ("scripts/validate_scoreform_adapter.py", "--skip-focused-tests"),
    ),
    (
        "Candidate discovery",
        ("scripts/validate_candidate_discovery.py", "--skip-focused-tests"),
    ),
    (
        "curation workflows",
        ("scripts/validate_curation_workflows.py", "--skip-focused-tests"),
    ),
    ("Snapshot workflows", ("scripts/validate_snapshot_workflows.py",)),
    ("improvement Portfolio", ("scripts/validate_improvement_portfolio.py",)),
    ("interface workflows", ("scripts/validate_interface_workflows.py",)),
    ("showcase Portfolio", ("scripts/validate_showcase_portfolio.py",)),
    ("release contract", ("scripts/validate_release_contract.py",)),
)


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    """One completed repository-validation command timing."""

    phase: str
    elapsed_seconds: float


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    phase: str,
    timings: list[PhaseTiming],
) -> None:
    print("+", " ".join(command), flush=True)
    started = perf_counter()
    try:
        subprocess.run(command, cwd=cwd, env=env, check=True)
    finally:
        elapsed = perf_counter() - started
        timings.append(PhaseTiming(phase=phase, elapsed_seconds=elapsed))
        print(f"TIMING {phase}: {elapsed:.3f}s", flush=True)


def _print_timing_summary(timings: list[PhaseTiming], total_seconds: float) -> None:
    """Print a stable human-readable timing summary."""
    print("", flush=True)
    print("Validation timing summary:", flush=True)
    for timing in timings:
        print(f"  {timing.phase}: {timing.elapsed_seconds:.3f}s", flush=True)
    print(f"  TOTAL: {total_seconds:.3f}s", flush=True)


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


def _static_cache_paths(
    temp: Path,
    *,
    reuse_static_caches: bool,
) -> tuple[Path, Path]:
    if not reuse_static_caches:
        return temp / "ruff-cache", temp / "mypy-cache"

    configured = os.environ.get("PDS_VITRINE_STATIC_CACHE_DIR")
    persistent_root = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".cache" / "pds-vitrine" / "static-analysis"
    )
    version = f"py{sys.version_info.major}{sys.version_info.minor}"
    version_root = persistent_root / version
    return version_root / "ruff", version_root / "mypy"


def validate(
    core_wheel: Path,
    *,
    allow_dirty: bool,
    reuse_static_caches: bool = False,
) -> None:
    root = Path(__file__).resolve().parents[1]
    initial_status = _git_status(root)
    if initial_status and not allow_dirty:
        raise RuntimeError("repository must be clean; use --allow-dirty during development")

    timings: list[PhaseTiming] = []
    validation_started = perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="vitrine-validation-") as temporary:
            temp = Path(temporary)
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            ruff_cache, mypy_cache = _static_cache_paths(
                temp,
                reuse_static_caches=reuse_static_caches,
            )
            env["RUFF_CACHE_DIR"] = str(ruff_cache)
            env["MYPY_CACHE_DIR"] = str(mypy_cache)
            _run(
                [sys.executable, "scripts/verify_core_wheel.py", str(core_wheel)],
                cwd=root,
                env=env,
                phase="core wheel verification",
                timings=timings,
            )
            _run(
                [sys.executable, "scripts/verify_core_wheel.py", "--installed"],
                cwd=root,
                env=env,
                phase="installed Core verification",
                timings=timings,
            )
            _run(
                [sys.executable, "-m", "pip", "check"],
                cwd=root,
                env=env,
                phase="pip check",
                timings=timings,
            )
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
                phase="pytest",
                timings=timings,
            )
            _run(
                [sys.executable, "-m", "ruff", "check", "."],
                cwd=root,
                env=env,
                phase="ruff",
                timings=timings,
            )
            _run(
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--cache-dir",
                    env["MYPY_CACHE_DIR"],
                ],
                cwd=root,
                env=env,
                phase="mypy",
                timings=timings,
            )
            for label, command in VALIDATOR_COMMANDS:
                _run(
                    [sys.executable, *command],
                    cwd=root,
                    env=env,
                    phase=f"validator: {label}",
                    timings=timings,
                )
            _run(
                [sys.executable, "scripts/check_documentation.py"],
                cwd=root,
                env=env,
                phase="documentation",
                timings=timings,
            )
            _run(
                [sys.executable, "scripts/validate_representative_portfolios.py"],
                cwd=root,
                env=env,
                phase="representative Portfolios",
                timings=timings,
            )
            _run(
                [sys.executable, "scripts/validate_portfolio_foundation.py"],
                cwd=root,
                env=env,
                phase="portfolio foundation",
                timings=timings,
            )
            build_source = _copy_build_source(root, temp / "source")
            dist = temp / "dist"
            _run(
                [sys.executable, "-m", "build", "--outdir", str(dist)],
                cwd=build_source,
                env=env,
                phase="package build",
                timings=timings,
            )
            artifacts = [str(path) for path in sorted(dist.iterdir())]
            _run(
                [sys.executable, "-m", "twine", "check", *artifacts],
                cwd=root,
                env=env,
                phase="twine check",
                timings=timings,
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
                phase="package content",
                timings=timings,
            )
            wheel_smokes = (
                ("base", "scripts/smoke_test_wheel.py"),
                ("adapter", "scripts/smoke_test_adapter_wheel.py"),
                ("Candidate", "scripts/smoke_test_candidate_wheel.py"),
                ("curation", "scripts/smoke_test_curation_wheel.py"),
                ("Snapshot", "scripts/smoke_test_snapshot_wheel.py"),
            )
            for label, script in wheel_smokes:
                _run(
                    [sys.executable, script, str(wheels[0]), str(core_wheel)],
                    cwd=root,
                    env=env,
                    phase=f"installed-wheel smoke: {label}",
                    timings=timings,
                )
            _run(
                [
                    sys.executable,
                    "scripts/smoke_test_end_to_end_wheel.py",
                    str(wheels[0]),
                    str(core_wheel),
                ],
                cwd=root,
                env=env,
                phase="installed-wheel acceptance: end-to-end",
                timings=timings,
            )
            _run(
                ["git", "diff", "--check"],
                cwd=root,
                env=env,
                phase="git diff check",
                timings=timings,
            )
        final_status = _git_status(root)
        if allow_dirty:
            if final_status != initial_status:
                raise RuntimeError("validation changed the working tree")
        elif final_status:
            raise RuntimeError("validation left repository residue")
    finally:
        _print_timing_summary(timings, perf_counter() - validation_started)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-wheel", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--reuse-static-caches",
        action="store_true",
        help="reuse persistent Ruff/Mypy caches for local complete validation",
    )
    args = parser.parse_args(argv)
    try:
        validate(
            args.core_wheel,
            allow_dirty=args.allow_dirty,
            reuse_static_caches=args.reuse_static_caches,
        )
        print("PASS complete repository validation")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Repository validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
