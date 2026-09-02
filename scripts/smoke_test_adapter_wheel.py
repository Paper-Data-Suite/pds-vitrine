"""Smoke the issue #32 adapter boundary from isolated installed wheels."""

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
    return environment / (
        "Scripts/vitrine.exe" if os.name == "nt" else "bin/vitrine"
    )


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-adapter-wheel-smoke-") as temporary:
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
        code = """
from vitrine.concord_artifact_source import (
    CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.producer_adapters import build_adapter_registry
assert CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.producer_module_id == "concord"
assert (
    CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR.representation_kind
    == "concord:returned_artifact_pdf"
)
ordinary = build_adapter_registry()
assert tuple(item.declaration.adapter_id for item in ordinary.adapters) == (
    'vitrine_concord_live_adapter',
    'vitrine_scoreform_live_adapter',
)
assert all(item.declaration.integration_kind == 'live' for item in ordinary.adapters)
assert {
    item.declaration.support_key.producer_module_id:
    item.reader.descriptor.package_identity
    for item in ordinary.adapters
} == {
    'concord': 'pds-concord',
    'scoreform': 'scoreform',
}
fixture = build_development_fixture_adapter_registry()
assert len(fixture.adapters) == 3
assert all(item.declaration.integration_kind == 'development_fixture' for item in fixture.adapters)
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        console = _console_path(environment)
        _run([str(console), "adapters", "--help"], cwd=work, env=env)
        ordinary_output = _run([str(console), "adapters", "list"], cwd=work, env=env)
        for adapter_id in (
            "vitrine_concord_live_adapter",
            "vitrine_scoreform_live_adapter",
        ):
            if adapter_id not in ordinary_output:
                raise RuntimeError(f"default adapter CLI is missing {adapter_id}")
        if "fixture" in ordinary_output.lower():
            raise RuntimeError("default adapter CLI exposed development fixtures")
        for adapter_id, producer in (
            ("vitrine_concord_live_adapter", "concord"),
            ("vitrine_scoreform_live_adapter", "scoreform"),
        ):
            show_output = _run(
                [str(console), "adapters", "show", adapter_id],
                cwd=work,
                env=env,
            )
            if "Integration kind: live" not in show_output:
                raise RuntimeError(f"{adapter_id} show diagnostics are missing")
            if f"Producer module: {producer}" not in show_output:
                raise RuntimeError(f"{adapter_id} show producer identity is missing")
        fixture_output = _run(
            [str(console), "adapters", "list", "--include-development-fixtures"],
            cwd=work,
            env=env,
        )
        for adapter_id in (
            "vitrine_scoreform_fixture_adapter",
            "vitrine_quillan_fixture_adapter",
            "vitrine_concord_fixture_adapter",
        ):
            if adapter_id not in fixture_output:
                raise RuntimeError(f"missing explicit fixture adapter listing: {adapter_id}")
        installed = _run(
            [
                str(python),
                "-c",
                "import importlib.util; "
                "assert importlib.util.find_spec('scoreform') is None; "
                "assert importlib.util.find_spec('quillan') is None; "
                "assert importlib.util.find_spec('concord') is None",
            ],
            cwd=work,
            env=env,
        )
        if installed:
            raise RuntimeError("unexpected adapter dependency smoke output")
        if list(work.iterdir()):
            raise RuntimeError("adapter wheel smoke left current-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated producer-adapter wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Adapter wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
