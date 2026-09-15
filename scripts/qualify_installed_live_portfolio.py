"""Authoritative exact-wheel installed qualification for Vitrine issue #71.

Slice-specific modes remain available for focused diagnosis. With no slice flag,
the harness composes the accepted destructive negative matrix with a separate
healthy seal/export/custody run and a Core+Vitrine-only historical verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.live_installed_acceptance_contract import (
        AUDITED_RELEASE_WHEELS,
        CANDIDATE_DISCOVERY_SLICE_READY,
        CURATED_SNAPSHOT_SLICE_READY,
        CUSTODY_VERIFIER_SLICE_READY,
        FULL_ACCEPTANCE_READY,
        NEGATIVE_MATRIX_SLICE_READY,
        WheelSpec,
        validate_contract_constants,
    )
else:
    from live_installed_acceptance_contract import (
        AUDITED_RELEASE_WHEELS,
        CANDIDATE_DISCOVERY_SLICE_READY,
        CURATED_SNAPSHOT_SLICE_READY,
        CUSTODY_VERIFIER_SLICE_READY,
        FULL_ACCEPTANCE_READY,
        NEGATIVE_MATRIX_SLICE_READY,
        WheelSpec,
        validate_contract_constants,
    )


class LiveInstalledQualificationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _authenticate(path: Path, spec: WheelSpec) -> Path:
    resolved = path.resolve(strict=True)
    if resolved.name != spec.filename:
        raise LiveInstalledQualificationError(
            f"expected {spec.filename}, found {resolved.name}"
        )
    actual = _sha256(resolved)
    if actual != spec.sha256:
        raise LiveInstalledQualificationError(
            f"SHA-256 mismatch for {spec.filename}: {actual}"
        )
    return resolved


def _resolve_release_wheels(wheel_dir: Path) -> tuple[Path, ...]:
    root = wheel_dir.resolve(strict=True)
    if not root.is_dir():
        raise LiveInstalledQualificationError("wheel-dir must be a directory")
    return tuple(_authenticate(root / spec.filename, spec) for spec in AUDITED_RELEASE_WHEELS)


def _distribution_version_from_wheel_filename(path: Path) -> tuple[str, str]:
    name = path.name
    if not name.endswith(".whl"):
        raise LiveInstalledQualificationError("Vitrine artifact must be a wheel")
    parts = name[:-4].split("-")
    if len(parts) < 2:
        raise LiveInstalledQualificationError("Vitrine wheel filename is malformed")
    distribution = parts[0].replace("_", "-")
    version = parts[1]
    return distribution, version


def _authenticate_vitrine_wheel(path: Path) -> tuple[Path, str]:
    resolved = path.resolve(strict=True)
    distribution, version = _distribution_version_from_wheel_filename(resolved)
    if distribution != "pds-vitrine":
        raise LiveInstalledQualificationError(
            f"candidate wheel is not pds-vitrine: {resolved.name}"
        )
    if version != "0.2.0":
        raise LiveInstalledQualificationError(
            f"issue #71 must not promote Vitrine version; found {version}"
        )
    return resolved, _sha256(resolved)


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    printable = " ".join(command)
    print(f"+ {printable}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _install_exact(
    python: Path,
    wheels: tuple[Path, ...],
    *,
    wheelhouse: Path,
    cwd: Path,
    env: dict[str, str],
) -> None:
    # Producer wheels have ordinary third-party runtime dependencies.  Resolve
    # those only from the caller-prepared local wheelhouse while installing the
    # four audited PDS wheels by exact authenticated path.
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            *(str(path) for path in wheels),
        ],
        cwd=cwd,
        env=env,
    )
    _run([str(python), "-m", "pip", "check"], cwd=cwd, env=env)


def _copy_runner_file(repository: Path, destination: Path, filename: str) -> Path:
    source = repository / "scripts" / filename
    if not source.is_file():
        raise LiveInstalledQualificationError(f"installed acceptance runner is missing: {filename}")
    target = destination / source.name
    shutil.copy2(source, target)
    return target


def _run_preflights(
    *,
    repository: Path,
    work_root: Path,
    vitrine_wheel: Path,
    release_wheels: tuple[Path, ...],
) -> tuple[Path, Path, Path]:
    env = _clean_env()
    runner_root = work_root / "runner"
    runner_root.mkdir()
    probe = _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_probe.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_support.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_portfolio.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_negative.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_custody.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_verifier.py"
    )
    _copy_runner_file(
        repository, runner_root, "live_installed_acceptance_scenario.py"
    )

    live_venv = work_root / "live-venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(live_venv)
    live_python = _venv_python(live_venv)
    _install_exact(
        live_python,
        (*release_wheels, vitrine_wheel),
        wheelhouse=release_wheels[0].parent,
        cwd=runner_root,
        env=env,
    )
    _run(
        [
            str(live_python),
            str(probe),
            "--repository",
            str(repository),
            "--mode",
            "live-preflight",
        ],
        cwd=runner_root,
        env=env,
    )

    verifier_venv = work_root / "sealed-verifier-venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(verifier_venv)
    verifier_python = _venv_python(verifier_venv)
    _install_exact(
        verifier_python,
        (release_wheels[0], vitrine_wheel),
        wheelhouse=release_wheels[0].parent,
        cwd=runner_root,
        env=env,
    )
    _run(
        [
            str(verifier_python),
            str(probe),
            "--repository",
            str(repository),
            "--mode",
            "sealed-verifier-preflight",
        ],
        cwd=runner_root,
        env=env,
    )
    return live_python, verifier_python, runner_root


def _run_candidate_discovery_slice(
    *,
    live_python: Path,
    runner_root: Path,
    repository: Path,
    work_root: Path,
) -> None:
    scenario = runner_root / "live_installed_acceptance_scenario.py"
    _run(
        [
            str(live_python),
            str(scenario),
            "--workspace",
            str(work_root / "live-workspace"),
            "--repository",
            str(repository),
            "--work-root",
            str(work_root / "scenario-work"),
        ],
        cwd=runner_root,
        env=_clean_env(),
    )



def _run_curated_snapshot_slice(
    *,
    live_python: Path,
    runner_root: Path,
    repository: Path,
    work_root: Path,
) -> None:
    scenario = runner_root / "live_installed_acceptance_scenario.py"
    _run(
        [
            str(live_python),
            str(scenario),
            "--workspace",
            str(work_root / "live-workspace"),
            "--repository",
            str(repository),
            "--work-root",
            str(work_root / "scenario-work"),
            "--portfolio-snapshot",
        ],
        cwd=runner_root,
        env=_clean_env(),
    )

def _run_negative_matrix_slice(
    *,
    live_python: Path,
    runner_root: Path,
    repository: Path,
    work_root: Path,
) -> None:
    scenario = runner_root / "live_installed_acceptance_scenario.py"
    _run(
        [
            str(live_python),
            str(scenario),
            "--workspace",
            str(work_root / "live-workspace"),
            "--repository",
            str(repository),
            "--work-root",
            str(work_root / "scenario-work"),
            "--negative-matrix",
        ],
        cwd=runner_root,
        env=_clean_env(),
    )


def _run_custody_verifier_slice(
    *,
    live_python: Path,
    verifier_python: Path,
    runner_root: Path,
    repository: Path,
    work_root: Path,
) -> None:
    scenario = runner_root / "live_installed_acceptance_scenario.py"
    scenario_work = work_root / "scenario-work"
    _run(
        [
            str(live_python),
            str(scenario),
            "--workspace",
            str(work_root / "live-workspace"),
            "--repository",
            str(repository),
            "--work-root",
            str(scenario_work),
            "--custody-verifier",
        ],
        cwd=runner_root,
        env=_clean_env(),
    )
    verifier = runner_root / "live_installed_acceptance_verifier.py"
    _run(
        [
            str(verifier_python),
            str(verifier),
            "--workspace",
            str(scenario_work / "sealed-verifier-workspace"),
            "--request",
            str(scenario_work / "sealed-verifier-request.json"),
        ],
        cwd=runner_root,
        env=_clean_env(),
    )


def qualify(
    *,
    repository: Path,
    vitrine_wheel: Path,
    wheel_dir: Path,
    preflight_only: bool,
    candidate_discovery_only: bool,
    portfolio_snapshot_only: bool,
    negative_matrix_only: bool,
    custody_verifier_only: bool,
) -> None:
    validate_contract_constants()
    repository = repository.resolve(strict=True)
    candidate, candidate_sha256 = _authenticate_vitrine_wheel(vitrine_wheel)
    release_wheels = _resolve_release_wheels(wheel_dir)
    print("PASS exact release wheel authentication", flush=True)
    print(f"PASS candidate Vitrine wheel authentication sha256={candidate_sha256}", flush=True)

    with tempfile.TemporaryDirectory(prefix="vitrine-live-installed-71-") as raw:
        work_root = Path(raw).resolve()
        if work_root.is_relative_to(repository):
            raise LiveInstalledQualificationError(
                "temporary qualification root must be outside repository"
            )
        live_python, verifier_python, runner_root = _run_preflights(
            repository=repository,
            work_root=work_root,
            vitrine_wheel=candidate,
            release_wheels=release_wheels,
        )
        if candidate_discovery_only:
            if not CANDIDATE_DISCOVERY_SLICE_READY:
                raise LiveInstalledQualificationError(
                    "Slice 2 Candidate discovery scenario is not enabled"
                )
            _run_candidate_discovery_slice(
                live_python=live_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root,
            )
        elif portfolio_snapshot_only:
            if not CURATED_SNAPSHOT_SLICE_READY:
                raise LiveInstalledQualificationError(
                    "Slice 3 curated Snapshot scenario is not enabled"
                )
            _run_curated_snapshot_slice(
                live_python=live_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root,
            )
        elif negative_matrix_only:
            if not NEGATIVE_MATRIX_SLICE_READY:
                raise LiveInstalledQualificationError(
                    "Slice 4A negative matrix scenario is not enabled"
                )
            _run_negative_matrix_slice(
                live_python=live_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root,
            )
        elif custody_verifier_only:
            if not CUSTODY_VERIFIER_SLICE_READY:
                raise LiveInstalledQualificationError(
                    "Slice 4B custody/verifier scenario is not enabled"
                )
            _run_custody_verifier_slice(
                live_python=live_python,
                verifier_python=verifier_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root,
            )
        elif not preflight_only:
            if not FULL_ACCEPTANCE_READY:
                raise LiveInstalledQualificationError(
                    "full issue #71 acceptance is not enabled"
                )
            _run_negative_matrix_slice(
                live_python=live_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root / "full-negative",
            )
            _run_custody_verifier_slice(
                live_python=live_python,
                verifier_python=verifier_python,
                runner_root=runner_root,
                repository=repository,
                work_root=work_root / "full-custody",
            )

    print("PASS installed exact-wheel isolation preflight", flush=True)
    print("PASS producer-independent verifier isolation preflight", flush=True)
    if preflight_only:
        print("PASS issue #71 Slice 1 acceptance infrastructure preflight", flush=True)
        return
    if candidate_discovery_only:
        print(
            "PASS issue #71 Slice 2 native producer and live Candidate acceptance",
            flush=True,
        )
        return
    if portfolio_snapshot_only:
        print(
            "PASS issue #71 Slice 3 explicit curation and authorized Snapshot acceptance",
            flush=True,
        )
        return
    if negative_matrix_only:
        print(
            "PASS issue #71 Slice 4A currentness, drift, removal, and authorization acceptance",
            flush=True,
        )
        return
    if custody_verifier_only:
        print(
            "PASS issue #71 Slice 4B custody, tamper, historical, and producer-independent verification acceptance",
            flush=True,
        )
        return
    if not FULL_ACCEPTANCE_READY:
        raise LiveInstalledQualificationError(
            "full issue #71 acceptance is not enabled"
        )
    print(
        "PASS issue #71 full live installed cross-producer acceptance",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--vitrine-wheel", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--candidate-discovery-only", action="store_true")
    mode.add_argument("--portfolio-snapshot-only", action="store_true")
    mode.add_argument("--negative-matrix-only", action="store_true")
    mode.add_argument("--custody-verifier-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        qualify(
            repository=args.repository,
            vitrine_wheel=args.vitrine_wheel,
            wheel_dir=args.wheel_dir,
            preflight_only=args.preflight_only,
            candidate_discovery_only=args.candidate_discovery_only,
            portfolio_snapshot_only=args.portfolio_snapshot_only,
            negative_matrix_only=args.negative_matrix_only,
            custody_verifier_only=args.custody_verifier_only,
        )
        return 0
    except (
        LiveInstalledQualificationError,
        OSError,
        subprocess.CalledProcessError,
        metadata.PackageNotFoundError,
    ) as error:
        print(f"Live installed qualification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
