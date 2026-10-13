"""Issue #104: run stable reader-contract acceptance from an installed Vitrine wheel.

A disposable environment installs the supplied Core/Vitrine wheels and three
SYNTHETIC future producer wheels. These synthetic producers are not release
qualification evidence for actual ScoreForm, Quillan, or Concord distributions.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.issue104_synthetic_producer_wheels import (
    FUTURE_VERSION,
    PRODUCERS,
    create_synthetic_producer_wheel,
)

PROBE = ROOT / "scripts/issue104_installed_reader_probe.py"


def _python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _require_wheel(path: Path, description: str) -> Path:
    checked = path.expanduser().resolve()
    if not checked.is_file() or checked.suffix != ".whl":
        raise RuntimeError(f"{description} must be an existing wheel")
    return checked


def _run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> str:
    completed = subprocess.run(
        command, cwd=cwd, env=environment,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Installed #104 command failed ({completed.returncode}): "
            f"{command[0]} / {command[1:3]}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def _probe(
    python: Path, *, mode: str, module: str | None,
    cwd: Path, environment: dict[str, str],
) -> dict[str, object]:
    env = dict(environment)
    env["PDS_ISSUE104_SCENARIO"] = mode
    if module is None:
        env.pop("PDS_ISSUE104_TARGET", None)
    else:
        env["PDS_ISSUE104_TARGET"] = module
    args = [str(python), "-I", "-B", str(PROBE), "--mode", mode]
    if module is not None:
        args.extend(("--module", module))
    response = _run(args, cwd=cwd, environment=env)
    try:
        report = json.loads(response)
    except (ValueError, TypeError) as error:
        raise RuntimeError("Installed #104 probe returned invalid JSON") from error
    if not isinstance(report, dict) or report.get("mode") != mode:
        raise RuntimeError("Installed #104 probe did not confirm the intended mode")
    if module is not None and report.get("module") != module:
        raise RuntimeError("Installed #104 probe did not confirm target module")
    return cast(dict[str, object], report)


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    """Qualify installed runtime compatibility without a source checkout import."""

    vitrine = _require_wheel(vitrine_wheel, "Vitrine")
    core = _require_wheel(core_wheel, "Core")
    if not PROBE.is_file():
        raise RuntimeError("Issue #104 installed reader probe is missing")
    with tempfile.TemporaryDirectory(prefix="vitrine-issue104-installed-") as raw:
        root = Path(raw)
        environment = root / "venv"
        work = root / "work"
        wheelhouse = root / "synthetic_wheels"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _python(environment)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env.pop("PDS_ISSUE104_SCENARIO", None)
        env.pop("PDS_ISSUE104_TARGET", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        fake_wheels = [
            create_synthetic_producer_wheel(wheelhouse, module)
            for module in PRODUCERS
        ]
        _run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps",
             str(core), str(vitrine), *(str(path) for path in fake_wheels)],
            cwd=work, environment=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, environment=env)
        supported = _probe(
            python, mode="supported", module=None, cwd=work, environment=env
        )
        if supported.get("synthetic_version") != FUTURE_VERSION:
            raise RuntimeError("Synthetic installed future version was not verified")
        if supported.get("projected_sources") != {
            "scoreform": 2, "quillan": 3, "concord": 1
        }:
            raise RuntimeError("Installed live projections did not produce expected sources")
        for failure in ("unsupported", "missing"):
            for module in PRODUCERS:
                rejected = _probe(
                    python, mode=failure, module=module,
                    cwd=work, environment=env,
                )
                if rejected.get("failure") != "reader.incompatible":
                    raise RuntimeError("Installed reader accepted incompatible metadata")
        historical = _probe(
            python, mode="historical", module=None, cwd=work, environment=env
        )
        if historical.get("exact_fallback_cases") != 6:
            raise RuntimeError("Bounded historical fallback inventory changed")
        if any(work.iterdir()):
            raise RuntimeError("Installed #104 acceptance left working-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Issue #104 installed-wheel acceptance failed: {error}", file=sys.stderr)
        return 1
    print(
        "PASS Issue #104 isolated installed Vitrine/Core wheels: "
        "3 synthetic future producer packages, 6 projected sources, "
        "6 fail-closed metadata cases, bounded historical fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
