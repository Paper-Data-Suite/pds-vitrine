"""Smoke issue #96 Candidate evidence contracts from isolated Core/Vitrine wheels."""

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
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "(no child output)"
        raise RuntimeError(
            "Candidate evidence review installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-candidate-evidence-wheel-smoke-"
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

        code = r"""
import importlib.util
import sys
from pathlib import Path

from vitrine.candidate_discovery_presentation import (
    CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION,
)
from vitrine.candidate_evidence_artifact_preview import (
    CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
    acquire_candidate_evidence_artifact_preview,
)
from vitrine.candidate_evidence_presentation import (
    CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
    build_candidate_evidence_presentation,
)
from vitrine.candidate_evidence_preview import (
    CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
    prepare_candidate_evidence_preview,
)
from vitrine.candidate_evidence_preview_menu import run_candidate_evidence_preview

for module_name in (
    "vitrine.candidate_discovery_presentation",
    "vitrine.candidate_evidence_presentation",
    "vitrine.candidate_evidence_preview",
    "vitrine.candidate_evidence_artifact_preview",
    "vitrine.candidate_evidence_preview_menu",
):
    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin is not None
    origin = Path(spec.origin).resolve()
    assert origin.is_relative_to(Path(sys.prefix).resolve())

assert CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION == (
    "vitrine_candidate_discovery_presentation_v1"
)
assert CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION == (
    "vitrine_candidate_evidence_presentation_v1"
)
assert CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION == (
    "vitrine_candidate_evidence_preview_v1"
)
assert CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION == (
    "vitrine_candidate_evidence_artifact_preview_v1"
)

for value in (
    build_candidate_evidence_presentation,
    prepare_candidate_evidence_preview,
    acquire_candidate_evidence_artifact_preview,
    run_candidate_evidence_preview,
):
    assert callable(value)

for distribution in ("scoreform", "quillan", "pds-concord"):
    assert importlib.util.find_spec(distribution.replace("pds-", "")) is None

imported_roots = {name.split(".", 1)[0] for name in sys.modules}
assert not {"scoreform", "quillan", "concord"}.intersection(imported_roots)
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "Candidate evidence review wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Candidate evidence review wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Candidate evidence review wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
