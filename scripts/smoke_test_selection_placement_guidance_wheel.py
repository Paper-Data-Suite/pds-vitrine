"""Smoke Issue #97 guidance from isolated installed Core/Vitrine wheels."""

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
            "Selection/Placement guidance installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-selection-placement-guidance-wheel-smoke-"
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
from dataclasses import fields

from vitrine.candidate_review import list_candidate_review_section_guidance
from vitrine.selection_placement_guidance import (
    SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION,
    SelectionPlacementGuidance,
    SelectionPlacementSectionGuidance,
    profile_requirement_ids_for_sections,
    project_selection_placement_guidance,
)

assert (
    SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION
    == "vitrine_selection_placement_guidance_v1"
)
assert callable(project_selection_placement_guidance)
assert callable(profile_requirement_ids_for_sections)
assert callable(list_candidate_review_section_guidance)

guidance_fields = {field.name for field in fields(SelectionPlacementGuidance)}
assert {
    "operation",
    "releasing_placement_ids",
    "semantic_eligible_section_ids",
    "sections",
}.issubset(guidance_fields)

section_fields = {
    field.name for field in fields(SelectionPlacementSectionGuidance)
}
assert {
    "semantic_candidate_eligible",
    "placement_bearing",
    "released_placement_count",
    "remaining_capacity",
    "arrangement_pointer_state",
    "current_actionable",
    "unavailability_reason_codes",
    "relevant_profile_requirement_ids",
}.issubset(section_fields)

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "Selection/Placement guidance wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Selection/Placement guidance wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Selection/Placement guidance wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
