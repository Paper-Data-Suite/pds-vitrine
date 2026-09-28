"""Smoke issue #95 teacher presentation from isolated Core/Vitrine wheels."""

from __future__ import annotations

import argparse
import os
import subprocess
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
            "teacher information architecture installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-teacher-ia-wheel-smoke-"
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
from io import StringIO
from pathlib import Path

from vitrine import portfolio_menu
from vitrine.teacher_presentation import (
    TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
    TeacherPortfolioOverview,
    TeacherSubjectLink,
)

spec = importlib.util.find_spec("vitrine.teacher_presentation")
assert spec is not None and spec.origin is not None
origin = Path(spec.origin).resolve()
assert str(origin).startswith(str(Path(sys.prefix).resolve()))
assert TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION == (
    "vitrine_teacher_information_architecture_v1"
)

view = TeacherPortfolioOverview(
    contract_version=TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
    portfolio_id="portfolio_wheel_exact",
    portfolio_subject_id="subject_wheel_exact",
    title="Improvement Portfolio",
    subject_label="Jordan Rivera",
    profile_binding_id="binding_wheel_exact",
    portfolio_profile_id="profile_wheel_exact",
    profile_revision=1,
    profile_label="Starter Improvement Portfolio",
    purpose_kind="improvement",
    subject_links=(
        TeacherSubjectLink(
            subject_link_id="link_wheel_exact",
            school_year="2026-2027",
            class_id="english12",
            student_id="00107",
            display_name="Jordan Rivera",
            status="confirmed",
            current_resolution="resolvable",
        ),
    ),
    candidate_count=4,
    active_selection_count=2,
    current_composition_revision=1,
    snapshot_series_count=1,
    current_edition_count=1,
)

teacher = StringIO()
technical = StringIO()
portfolio_menu._render_teacher_portfolio_overview(teacher, view)
portfolio_menu._render_portfolio_technical_details(technical, view)

primary = teacher.getvalue()
exact = technical.getvalue()

assert "Jordan Rivera" in primary
assert "Improvement Portfolio" in primary
assert "Starter Improvement Portfolio" in primary
assert "Working Composition: revision 1" in primary
assert "portfolio_wheel_exact" not in primary
assert "binding_wheel_exact" not in primary
assert "profile_wheel_exact" not in primary
assert "link_wheel_exact" not in primary

assert "Technical Details / Provenance" in exact
assert "Portfolio ID: portfolio_wheel_exact" in exact
assert "Portfolio Subject ID: subject_wheel_exact" in exact
assert "Profile Binding ID: binding_wheel_exact" in exact
assert "Profile ID: profile_wheel_exact" in exact
assert "Subject Link ID: link_wheel_exact" in exact
"""
        _run([str(python), "-c", code], cwd=work, env=env)

    print("PASS isolated teacher information architecture wheel smoke test")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    smoke(args.vitrine_wheel, args.core_wheel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
