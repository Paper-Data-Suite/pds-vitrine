"""Smoke Issue #99 routing/profile contract from isolated Core/Vitrine wheels."""

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
            "paper Reflection installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-paper-reflection-wheel-smoke-"
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

        code = r"""
import importlib.metadata
import importlib.util

from pds_core.module_profiles import (
    CORE_ROUTING_CONTRACT_VERSION,
    discover_module_profiles,
)

profiles = {profile.module_id: profile for profile in discover_module_profiles()}
assert "vitrine" in profiles
profile = profiles["vitrine"]
assert CORE_ROUTING_CONTRACT_VERSION in profile.supported_core_routing_contract_versions
assert "PDS2" in profile.supported_qr_schemas
assert "1" in profile.supported_route_registration_schema_versions
assert "active" in profile.dispatchable_route_statuses
assert callable(profile.route_handler)
assert callable(profile.registration_validator)

metadata = importlib.metadata.metadata("pds-vitrine")
requirements = tuple(metadata.get_all("Requires-Dist", ()))
normalized = tuple(value.replace(" ", "").lower() for value in requirements)
assert any("pds-core<0.7,>=0.6.3" in value for value in normalized)
assert any(value.startswith("qrcode[pil]") or value.startswith("qrcode") for value in normalized)
assert any(value.startswith("reportlab") for value in normalized)

for forbidden in ("pds-scoreform", "pds-quillan", "pds-concord", "pds-portia", "pds-meridian"):
    assert not any(forbidden in value for value in normalized)

for module_name in (
    "vitrine.pds_module",
    "vitrine.paper_reflection_services",
    "vitrine.paper_reflection_printing",
    "vitrine.paper_reflection_evidence",
    "vitrine.paper_reflection_authorship",
    "vitrine.manual_reflection_services",
    "vitrine.paper_reflection_materialization",
    "vitrine.paper_reflection_workflow",
    "vitrine.paper_reflection_review",
):
    assert importlib.util.find_spec(module_name) is not None

for sibling in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(sibling) is None
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "paper Reflection wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated paper Reflection routing/profile wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Paper Reflection wheel smoke failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
