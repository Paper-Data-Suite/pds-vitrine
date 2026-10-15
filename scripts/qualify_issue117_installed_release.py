"""Issue #117: qualify a noneditable Vitrine wheel with authentic producer wheels.

The outer command validates five wheel inputs and executes copied qualification
probes in a disposable environment.  All runtime imports resolve to installed
wheels; the repository checkout is NEVER on the probe's import path.

This is release-CANDIDATE acceptance, not v0.4.0 publication evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from email.parser import BytesParser
from pathlib import Path

# Only the outer driver needs checkout-side qualification helpers. Executing
# this file directly puts scripts/ (not the repository root) on sys.path.
# The installed-wheel child probes still execute with -I and no PYTHONPATH;
# this adjustment is not inherited by their independent Python processes.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_issue117_release_wheels import (  # noqa: E402
    EXPECTED_WHEELS,
    authenticate_wheelhouse,
    validate_inventory,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_FILENAME = "pds_vitrine-0.4.0-py3-none-any.whl"
HELPERS = (
    "qualify_installed_producer_readers.py",
    "qualify_concord_artifact_source.py",
    "qualify_quillan_artifact_source.py",
)
VERSIONS = {
    "pds-vitrine": "0.4.0",
    "pds-core": "0.6.5",
    "scoreform": "0.13.0",
    "quillan": "0.10.6",
    "pds-concord": "0.3.2",
}

# Executed with -I -B by the NEW virtualenv Python, not the checkout interpreter.
# No source path is placed on sys.path, and every package must live in sys.prefix.
INSTALLED_PREFLIGHT = r'''
import importlib
import importlib.metadata as metadata
import json
import pathlib
import sys

expected = json.loads(sys.argv[1])
site_root = pathlib.Path(sys.prefix).resolve()
if sys.flags.isolated != 1:
    raise RuntimeError("release probe must execute with Python -I")
for distribution, version in expected.items():
    actual = metadata.version(distribution)
    if actual != version:
        raise RuntimeError(f"{distribution}: expected {version}, installed {actual}")
    dist = metadata.distribution(distribution)
    dist_path = pathlib.Path(str(dist._path)).resolve()
    if not dist_path.is_relative_to(site_root):
        raise RuntimeError(
            f"{distribution}: metadata outside isolated env: {dist_path}"
        )
    direct_url = dist.read_text("direct_url.json")
    if direct_url and json.loads(direct_url).get("dir_info", {}).get("editable"):
        raise RuntimeError(f"{distribution}: editable distribution is forbidden")
for module in ("vitrine", "pds_core", "scoreform", "quillan", "concord"):
    package = importlib.import_module(module)
    file = getattr(package, "__file__", None)
    if not file or not pathlib.Path(file).resolve().is_relative_to(site_root):
        raise RuntimeError(f"{module}: runtime import came from checkout: {file}")
if importlib.import_module("vitrine").__version__ != "0.4.0":
    raise RuntimeError("Vitrine public version mismatch")
print("PASS #117 isolated noneditable source/metadata provenance and five versions")
'''


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_candidate_wheel(path: Path) -> str:
    """Reject missing, wrong, corrupt, or mislabeled v0.4.0 candidate wheels."""
    if path.name != CANDIDATE_FILENAME:
        raise RuntimeError(f"wrong Vitrine wheel filename: {path.name}")
    if not path.is_file():
        raise RuntimeError(f"missing Vitrine candidate wheel: {path}")
    digest = _sha256(path)
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"corrupt Vitrine wheel member: {bad}")
            names = [
                member
                for member in archive.namelist()
                if len(member.split("/")) == 2
                and member.endswith(".dist-info/METADATA")
            ]
            if len(names) != 1:
                raise RuntimeError("Vitrine wheel must contain one METADATA record")
            metadata = BytesParser().parsebytes(archive.read(names[0]))
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Vitrine wheel is not a valid ZIP archive") from exc
    if metadata.get("Name", "").casefold().replace("_", "-") != "pds-vitrine":
        raise RuntimeError("Vitrine wheel metadata distribution mismatch")
    if metadata.get("Version") != "0.4.0":
        raise RuntimeError("Vitrine wheel embedded version is not 0.4.0")
    if metadata.get("Requires-Python") != ">=3.11":
        raise RuntimeError("Vitrine wheel Python floor changed")
    dependencies = metadata.get_all("Requires-Dist", ())
    core = {"pds-core<0.7,>=0.6.5", "pds-core>=0.6.5,<0.7"}
    if not any(d.replace(" ", "") in core for d in dependencies):
        raise RuntimeError("Vitrine candidate lacks required Core dependency")
    for dependency in dependencies:
        if "extra ==" not in dependency and "extra==" not in dependency:
            siblings = ("scoreform", "quillan", "concord", "meridian", "portia")
            if any(name in dependency.casefold() for name in siblings):
                raise RuntimeError(
                    "Vitrine candidate has unconditional sibling dependency"
                )
    return digest


def validate_source(root: Path = ROOT) -> tuple[str, ...]:
    """Static, wheel-free gate used by repository validation and focused tests."""
    findings = list(validate_inventory(root=root))
    for helper in HELPERS:
        path = root / "scripts" / helper
        if not path.is_file():
            findings.append(f"missing established official-producer probe: {helper}")
            continue
        content = path.read_text(encoding="utf-8")
        if helper == HELPERS[0]:
            for marker in (
                "def _inside_qualification(",
                "def _scoreform_bytes(",
                "def _quillan_bytes(",
                '"--build-concord-fixture"',
                '"--inside"',
            ):
                if marker not in content:
                    findings.append(f"official-producer qualifier missing {marker}")
    if tuple(VERSIONS.items()) != (
        ("pds-vitrine", "0.4.0"),
        *((spec.distribution, spec.version) for spec in EXPECTED_WHEELS),
    ):
        findings.append("installed version matrix diverged from authenticated inputs")
    return tuple(findings)


def _run(command: list[str], *, work: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command, cwd=work, env=env, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            "Issue #117 installed command failed "
            f"({result.returncode}): {command[:3]!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def _isolated_python(environment: Path) -> Path:
    return environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )


def _isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "PDS_WORKSPACE_ROOT"):
        env.pop(name, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def qualify(vitrine_wheel: Path, wheel_dir: Path) -> None:
    findings = validate_source()
    if findings:
        raise RuntimeError("source gate failed: " + "; ".join(findings))
    candidate = vitrine_wheel.expanduser().resolve()
    wheelhouse = wheel_dir.expanduser().resolve()
    digest = validate_candidate_wheel(candidate)
    # Reuse the existing exact published input-wheel authenticators from Slice 4.
    verified = authenticate_wheelhouse(wheelhouse)
    for item in verified:
        print("PASS release input", item, flush=True)
    print("PASS candidate Vitrine wheel SHA-256", digest, flush=True)

    from scripts.qualify_installed_producer_readers import (
        _quillan_bytes,
        _scoreform_bytes,
    )

    with tempfile.TemporaryDirectory(prefix="vitrine-issue117-installed-") as raw:
        temporary = Path(raw)
        isolated = temporary / "venv"
        work = temporary / "work"
        probes = temporary / "probes"
        fixtures = temporary / "fixtures"
        work.mkdir()
        probes.mkdir()
        fixtures.mkdir()
        for helper in HELPERS:
            shutil.copyfile(ROOT / "scripts" / helper, probes / helper)
        (fixtures / "scoreform.json").write_bytes(_scoreform_bytes())
        (fixtures / "quillan.json").write_bytes(_quillan_bytes())

        venv.EnvBuilder(with_pip=True, clear=True).create(isolated)
        python = _isolated_python(isolated)
        env = _isolated_env()
        # Installing all five wheel INPUTS together allows legitimate transitive
        # dependencies to resolve without adding sibling dependencies to Vitrine.
        _run(
            [
                str(python), "-m", "pip", "install",
                "--disable-pip-version-check", "--no-input",
                *[str(wheelhouse / spec.filename) for spec in EXPECTED_WHEELS],
                str(candidate),
            ],
            work=work, env=env,
        )
        _run([str(python), "-m", "pip", "check"], work=work, env=env)
        print(
            _run(
                [str(python), "-I", "-B", "-c", INSTALLED_PREFLIGHT,
                 json.dumps(VERSIONS, sort_keys=True)],
                work=work, env=env,
            ).strip(), flush=True,
        )
        console = _run(
            [str(python), "-I", "-B", "-m", "vitrine", "--version"],
            work=work, env=env,
        )
        if "0.4.0" not in console:
            raise RuntimeError("installed Vitrine CLI did not report 0.4.0")
        print("PASS isolated Vitrine CLI", console.strip(), flush=True)

        common = [str(python), "-I", "-B"]
        qualifier = str(probes / HELPERS[0])
        print(
            _run(
                [*common, qualifier, "--build-concord-fixture",
                 str(fixtures / "concord.json")],
                work=work, env=env,
            ).strip(), flush=True,
        )
        print(
            _run(
                [*common, qualifier, "--inside", "--fixture-dir", str(fixtures)],
                work=work, env=env,
            ).strip(), flush=True,
        )
        for helper in HELPERS[1:]:
            print(
                _run([*common, str(probes / helper)], work=work, env=env).strip(),
                flush=True,
            )
        if tuple(work.iterdir()):
            raise RuntimeError(
                "installed qualification left residue in working directory"
            )
    print(
        "PASS #117 noneditable Vitrine + four authentic releases installed acceptance"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--vitrine-wheel", type=Path)
    parser.add_argument("--wheel-dir", type=Path)
    args = parser.parse_args(argv)
    findings = validate_source()
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    if args.check_source:
        if args.vitrine_wheel or args.wheel_dir:
            parser.error("--check-source cannot be combined with wheel paths")
        print("PASS #117 installed acceptance static source/probe contract")
        return 0
    if args.vitrine_wheel is None or args.wheel_dir is None:
        parser.error("both --vitrine-wheel and --wheel-dir are required")
    try:
        qualify(args.vitrine_wheel, args.wheel_dir)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Issue #117 installed acceptance failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
