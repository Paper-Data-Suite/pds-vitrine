"""Smoke issue #33 Candidate service imports from isolated installed wheels."""

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
        check=True,
    )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-candidate-wheel-smoke-") as temporary:
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
import importlib.util
from pds_core.publication_compatibility import PublicationProducerRegistry
from vitrine.candidate_services import CandidateDiscoveryRequest, SourceReadAuthorizationDecision
from vitrine.development_candidate_fixtures import build_development_fixture_producer_registry
from vitrine.producer_adapters import build_adapter_registry
registry = build_adapter_registry()
assert tuple(
    adapter.declaration.adapter_id for adapter in registry.adapters
) == ("vitrine_scoreform_live_adapter",)
assert tuple(
    adapter.declaration.support_key.producer_module_id
    for adapter in registry.adapters
) == ("scoreform",)
assert PublicationProducerRegistry(profiles=()).profiles == ()
fixture_profiles = build_development_fixture_producer_registry()
assert len(fixture_profiles.profiles) == 3
for name in ('scoreform', 'quillan', 'concord', 'meridian'):
    assert importlib.util.find_spec(name) is None
assert CandidateDiscoveryRequest is not None
assert SourceReadAuthorizationDecision(outcome='allowed').outcome == 'allowed'
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError("Candidate wheel smoke left current-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Candidate service wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Candidate wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
