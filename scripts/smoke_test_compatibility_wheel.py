"""Smoke issue #62 compatibility diagnostics from isolated installed wheels."""

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


def _console_path(environment: Path) -> Path:
    return environment / ("Scripts/vitrine.exe" if os.name == "nt" else "bin/vitrine")


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    expected_returncode: int = 0,
) -> tuple[str, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected_returncode:
        raise RuntimeError(
            f"command returned {result.returncode}, expected {expected_returncode}: "
            f"{command!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout, result.stderr


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-compatibility-wheel-smoke-"
    ) as temporary:
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

        import_probe = """
import importlib.util
from vitrine.artifact_diagnostics import diagnose_artifact_applicability
from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
)
from vitrine.publication_diagnostics import COMPATIBILITY_SOURCE_READ_OPERATION
assert CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION == (
    'vitrine_cross_producer_compatibility_diagnostic_v1'
)
assert COMPATIBILITY_SOURCE_READ_OPERATION == 'compatibility_source_read'
assert diagnose_artifact_applicability('scoreform').outcome == 'not_applicable'
assert diagnose_artifact_applicability('quillan').outcome == 'supported'
assert diagnose_artifact_applicability('concord').outcome == 'supported'
assert importlib.util.find_spec('scoreform') is None
assert importlib.util.find_spec('quillan') is None
assert importlib.util.find_spec('concord') is None
"""
        _run([str(python), "-c", import_probe], cwd=work, env=env)

        console = _console_path(environment)
        _run([str(console), "compatibility", "--help"], cwd=work, env=env)

        supported, supported_error = _run(
            [
                str(console),
                "compatibility",
                "contract",
                "--producer",
                "scoreform",
                "--core-publication-schema-version",
                "1",
                "--publication-kind",
                "academic_result_set",
                "--manifest-contract-version",
                "scoreform_academic_result_manifest_v1",
                "--producer-contract-version",
                "scoreform_academic_work_v1",
                "--capability",
                "multiple_attempts",
                "--capability",
                "points",
                "--capability",
                "question_evidence",
            ],
            cwd=work,
            env=env,
        )
        if supported_error:
            raise RuntimeError("supported contract emitted stderr output")
        for marker in (
            "Status: supported",
            "Producer: scoreform",
            "Technical:",
            "compatibility.contract_supported",
        ):
            if marker not in supported:
                raise RuntimeError(
                    f"supported contract output is missing marker: {marker}"
                )

        mismatch, mismatch_error = _run(
            [
                str(console),
                "compatibility",
                "contract",
                "--producer",
                "scoreform",
                "--core-publication-schema-version",
                "1",
                "--publication-kind",
                "academic_result_set",
                "--manifest-contract-version",
                "scoreform_academic_result_manifest_v2",
                "--producer-contract-version",
                "scoreform_academic_work_v1",
                "--capability",
                "multiple_attempts",
                "--capability",
                "points",
                "--capability",
                "question_evidence",
            ],
            cwd=work,
            env=env,
            expected_returncode=1,
        )
        if mismatch_error:
            raise RuntimeError("semantic mismatch emitted stderr output")
        for marker in (
            "Status: unsupported",
            "adapter.unsupported_contract",
            "compatibility.manifest_contract_mismatch",
        ):
            if marker not in mismatch:
                raise RuntimeError(
                    f"semantic mismatch output is missing marker: {marker}"
                )

        readiness, readiness_error = _run(
            [str(console), "compatibility", "producers"],
            cwd=work,
            env=env,
        )
        if readiness_error:
            raise RuntimeError("producer readiness emitted stderr output")
        for producer in ("concord", "quillan", "scoreform"):
            if producer not in readiness:
                raise RuntimeError(
                    f"producer readiness output is missing {producer}"
                )
        if "not_applicable" not in readiness:
            raise RuntimeError(
                "producer readiness did not preserve ScoreForm Artifact N/A"
            )

        if list(work.iterdir()):
            raise RuntimeError(
                "compatibility wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated cross-producer compatibility wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Compatibility wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
