"""Issue #117 installed-release acceptance: fail-closed package/probe tests."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts import qualify_issue117_installed_release as qualification
from scripts.validate_issue117_release_wheels import EXPECTED_WHEELS


def _candidate(
    path: Path, *, version: str = "0.4.0", name: str = "pds-vitrine"
) -> None:
    metadata = (
        f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n"
        "Requires-Python: >=3.11\n"
        "Requires-Dist: pds-core<0.7,>=0.6.5\n\n"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("pds_vitrine-0.4.0.dist-info/METADATA", metadata)
        archive.writestr("vitrine/__init__.py", "__version__ = '0.4.0'\n")


def test_issue117_installed_source_contract_is_current() -> None:
    assert qualification.validate_source() == ()
    assert len(qualification.HELPERS) == 3


def test_issue117_reuses_exact_current_release_audits() -> None:
    assert qualification.VERSIONS == {
        "pds-vitrine": "0.4.0",
        "pds-core": "0.6.5",
        "scoreform": "0.13.0",
        "quillan": "0.10.6",
        "pds-concord": "0.3.2",
    }
    assert {item.distribution for item in EXPECTED_WHEELS} == {
        "pds-core", "scoreform", "quillan", "pds-concord"
    }


def test_issue117_candidate_wheel_metadata_and_digest(tmp_path: Path) -> None:
    candidate = tmp_path / qualification.CANDIDATE_FILENAME
    _candidate(candidate)
    assert len(qualification.validate_candidate_wheel(candidate)) == 64


def test_issue117_missing_or_renamed_candidate_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / qualification.CANDIDATE_FILENAME
    with pytest.raises(RuntimeError, match="missing Vitrine"):
        qualification.validate_candidate_wheel(missing)
    wrong = tmp_path / "pds_vitrine-0.3.0-py3-none-any.whl"
    _candidate(wrong)
    with pytest.raises(RuntimeError, match="wrong Vitrine wheel filename"):
        qualification.validate_candidate_wheel(wrong)


def test_issue117_mismatched_candidate_metadata_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / qualification.CANDIDATE_FILENAME
    _candidate(candidate, version="0.3.0")
    with pytest.raises(RuntimeError, match="embedded version"):
        qualification.validate_candidate_wheel(candidate)
    _candidate(candidate, name="other-vitrine")
    with pytest.raises(RuntimeError, match="distribution mismatch"):
        qualification.validate_candidate_wheel(candidate)


def test_issue117_invalid_candidate_zip_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / qualification.CANDIDATE_FILENAME
    candidate.write_bytes(b"this is not a wheel")
    with pytest.raises(RuntimeError, match="not a valid ZIP"):
        qualification.validate_candidate_wheel(candidate)


def test_issue117_python_isolation_is_mandatory() -> None:
    preflight = qualification.INSTALLED_PREFLIGHT
    assert "sys.flags.isolated != 1" in preflight
    assert "is_relative_to(site_root)" in preflight
    assert 'dist.read_text("direct_url.json")' in preflight
    assert "editable" in preflight
    assert qualification.VERSIONS["pds-vitrine"] == "0.4.0"
    env = qualification._isolated_env()
    for name in ("PYTHONPATH", "PYTHONHOME", "PDS_WORKSPACE_ROOT"):
        assert name not in env


def test_issue117_source_contract_detects_missing_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = qualification.validate_source
    # Source gate must check presence of each established probe, not only
    # accept a file name or rely on static source imports from the checkout.
    root = tmp_path
    (root / "scripts").mkdir()
    monkeypatch.setattr(
        "scripts.qualify_issue117_installed_release.validate_inventory",
        lambda *, root: (),
    )
    findings = original(root)
    assert any(
        "missing established official-producer probe" in item for item in findings
    )


def test_issue117_static_cli_does_not_perform_an_install() -> None:
    assert qualification.main(["--check-source"]) == 0


@pytest.mark.parametrize(
    "arguments",
    (
        ("scripts/qualify_issue117_installed_release.py", "--check-source"),
        ("-m", "scripts.qualify_issue117_installed_release", "--check-source"),
    ),
)
def test_issue117_source_gate_supports_both_invocation_forms(
    arguments: tuple[str, ...],
) -> None:
    """The repository validator uses the direct-file invocation form."""
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=qualification.ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS #117 installed acceptance static source/probe contract" in result.stdout
