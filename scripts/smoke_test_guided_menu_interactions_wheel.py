"""Smoke Issue #98 guided interactions from isolated Core/Vitrine wheels."""

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
            "guided-menu interaction installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-guided-menu-interactions-wheel-smoke-"
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
from io import StringIO

from vitrine.menu_interactions import (
    GUIDED_MENU_INTERACTION_CONTRACT_VERSION,
    confirm_exact_phrase,
    resolve_required_choice,
)

assert (
    GUIDED_MENU_INTERACTION_CONTRACT_VERSION
    == "vitrine_guided_menu_interaction_v1"
)

zero = resolve_required_choice(())
assert zero.disposition == "unavailable"
assert zero.selected is None

exact = object()
one = resolve_required_choice((exact,))
assert one.disposition == "carried_forward"
assert one.selected is exact

first = object()
second = object()
many = resolve_required_choice((first, second))
assert many.disposition == "requires_choice"
assert many.choices == (first, second)

output = StringIO()
responses = iter(("WRONG", "confirm action"))
clears = []
reviews = []

def render_review():
    reviews.append("review")
    print("Current Review", file=output)

assert confirm_exact_phrase(
    expected_phrase="CONFIRM ACTION",
    input_fn=lambda _prompt: next(responses),
    output=output,
    clear_fn=lambda: clears.append("clear"),
    render_review=render_review,
)
assert clears == ["clear", "clear"]
assert reviews == ["review", "review"]
assert "Confirmation not accepted." in output.getvalue()

for module_name in (
    "vitrine.menu",
    "vitrine.portfolio_menu",
    "vitrine.portfolio_setup_menu",
    "vitrine.candidate_review_menu",
    "vitrine.working_composition_menu",
    "vitrine.current_portfolio_menu",
    "vitrine.profile_menu",
    "vitrine.subject_menu",
):
    assert importlib.util.find_spec(module_name) is not None

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "guided-menu interaction wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated guided-menu interaction wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Guided-menu interaction wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
