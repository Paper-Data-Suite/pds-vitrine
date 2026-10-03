"""Installed-wheel acceptance for Issue #111 bounded Vitrine paths."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
            "Issue #111 installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    # Authenticate the exact published Core 0.6.4 artifact before creating
    # the isolated environment.
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
    )

    with tempfile.TemporaryDirectory(prefix="vitrine-issue111-wheel-") as temporary:
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
        _run(
            [str(python), "-m", "pip", "check"],
            cwd=work,
            env=env,
        )

        code = r"""
import hashlib
import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.scan_retention import retain_source_scan
from pds_core.scan_routes import (
    RETAINED_SOURCE_FILENAME_MAX_LENGTH,
    SOURCE_SCAN_ID_MAX_LENGTH,
)
from vitrine.paper_reflection_materialization import (
    PaperReflectionMaterialization,
    read_paper_reflection_materialization_bytes,
)
from vitrine.path_policy import (
    CUSTODY_TOKEN_MAX_LENGTH,
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    build_bounded_presentation_directory_name,
    build_bounded_presentation_filename,
)
from vitrine.snapshot_custody import (
    acquire_snapshot_series_lock,
    bounded_snapshot_attempt_staging_root,
    bounded_snapshot_edition_root,
    bounded_snapshot_export_path,
    create_snapshot_staging,
    inspect_snapshot_series_lock,
    release_snapshot_series_lock,
)

assert importlib.metadata.version("pds-core") == "0.6.4"
assert importlib.metadata.version("pds-vitrine") == "0.3.0"

requirements = tuple(
    value.replace(" ", "").lower()
    for value in importlib.metadata.metadata("pds-vitrine").get_all(
        "Requires-Dist", ()
    )
)
assert any("pds-core<0.7,>=0.6.3" in value for value in requirements)

long_attempt = "snapshot_attempt_" + ("a" * 4096)
long_series = "snapshot_series_" + ("s" * 4096)
long_export = "snapshot_export_" + ("e" * 4096)

with TemporaryDirectory(prefix="issue111-case-", dir=".") as case:
    case_root = Path(case).resolve()
    workspace = case_root / "workspace"
    workspace.mkdir()

    staging = create_snapshot_staging(workspace, long_attempt)
    assert staging.root == bounded_snapshot_attempt_staging_root(
        workspace,
        long_attempt,
    )
    assert len(staging.root.name) == CUSTODY_TOKEN_MAX_LENGTH

    edition = bounded_snapshot_edition_root(workspace, long_series, 1)
    export = bounded_snapshot_export_path(
        workspace,
        snapshot_series_id=long_series,
        edition_number=1,
        snapshot_export_artifact_id=long_export,
    )
    assert len(edition.name) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(export.name) == CUSTODY_TOKEN_MAX_LENGTH

    lock = acquire_snapshot_series_lock(
        workspace,
        snapshot_series_id=long_series,
        snapshot_build_attempt_id=long_attempt,
        snapshot_build_plan_id="snapshot_plan_issue111",
        acquired_at=datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc),
    )
    assert inspect_snapshot_series_lock(
        workspace,
        snapshot_series_id=long_series,
    ) == lock
    release_snapshot_series_lock(
        workspace,
        snapshot_series_id=long_series,
        snapshot_build_attempt_id=long_attempt,
        expected_sha256=lock.sha256,
    )

    filename = build_bounded_presentation_filename(
        "My Portfolio Evidence " * 1000,
        semantic_domain="installed-issue111-entry",
        semantic_identity={"entry_id": "entry_" + ("x" * 10000)},
        extension=".pdf",
    )
    directory = build_bounded_presentation_directory_name(
        "Writing Growth " * 1000,
        semantic_domain="installed-issue111-section",
        semantic_identity={"section_id": "section_" + ("y" * 10000)},
        ordinal=1,
    )
    assert len(filename.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH
    assert len(directory.encode("utf-8")) <= PRESENTATION_DIRECTORY_MAX_LENGTH
    assert filename.endswith(".pdf")

    payload = b"%PDF-Core-0.6.4-Issue-111\n"
    incoming = case_root / (("student-reflection-" * 9) + ".pdf")
    assert len(incoming.name.encode("utf-8")) < 255
    incoming.write_bytes(payload)
    retained = retain_source_scan(
        workspace,
        incoming,
        intake_timestamp=datetime(2026, 10, 2, 20, 5, tzinfo=timezone.utc),
    )
    assert retained.source_filename == incoming.name
    assert len(retained.retained_source_path.name) <= RETAINED_SOURCE_FILENAME_MAX_LENGTH
    assert len(retained.source_scan_id) <= SOURCE_SCAN_ID_MAX_LENGTH
    assert retained.retained_source_path.read_bytes() == payload

    materialization = PaperReflectionMaterialization(
        reflection_id="reflection_issue111_installed",
        reflection_revision=1,
        paper_finalization_id="paper_finalization_issue111_installed",
        returned_paper_evidence_id="paper_evidence_issue111_installed",
        source_scan_id=retained.source_scan_id,
        source_page_number=1,
        retained_source_relative_path=retained.retained_source_relative_path,
        source_sha256=retained.source_sha256,
        media_type="application/pdf",
    )
    assert (
        read_paper_reflection_materialization_bytes(workspace, materialization)
        == payload
    )
"""
        _run([str(python), "-c", code], cwd=work, env=env)

        if list(work.iterdir()):
            raise RuntimeError(
                "Issue #111 wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS Issue #111 Core 0.6.4 installed-wheel acceptance")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Issue #111 wheel smoke failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
