"""Issue #117: static/current official-wheel identity and byte-level negatives."""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import validate_issue117_release_wheels as wheels


def _wheel(
    directory: Path,
    spec: wheels.QualifiedWheel,
    *,
    version: str | None = None,
) -> Path:
    path = directory / spec.filename
    dist_info = spec.distribution.replace("-", "_") + f"-{spec.version}.dist-info"
    with zipfile.ZipFile(path, "w") as output:
        output.writestr(
            f"{dist_info}/METADATA",
            "Metadata-Version: 2.3\n"
            f"Name: {spec.distribution}\n"
            f"Version: {version or spec.version}\n"
            "Requires-Python: >=3.11\n",
        )
        output.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\n")
    return path


def test_current_release_input_matrix_matches_existing_audits() -> None:
    assert wheels.validate_inventory() == ()
    actual = tuple(
        (item.distribution, item.version) for item in wheels.EXPECTED_WHEELS
    )
    assert actual == (
        ("pds-core", "0.6.5"),
        ("scoreform", "0.13.0"),
        ("quillan", "0.10.6"),
        ("pds-concord", "0.3.2"),
    )


def test_stale_concord_version_does_not_pass_current_audit() -> None:
    specs = tuple(
        replace(spec, version="0.3.1") if spec.distribution == "pds-concord" else spec
        for spec in wheels.EXPECTED_WHEELS
    )
    assert any(
        "release wheel audit drift" in item
        for item in wheels.validate_inventory(specs)
    )


def test_no_local_wheels_is_not_reported_as_authenticated(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="missing official release wheel"):
        wheels.authenticate_wheelhouse(tmp_path)


def test_exact_byte_digest_and_metadata_are_both_required(tmp_path: Path) -> None:
    spec = wheels.EXPECTED_WHEELS[0]
    path = _wheel(tmp_path, spec)
    local = replace(spec, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    assert wheels.authenticate_wheel(path, local) == local.sha256
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        wheels.authenticate_wheel(path, local)


def test_wrong_version_in_wheel_metadata_fails_closed(tmp_path: Path) -> None:
    spec = wheels.EXPECTED_WHEELS[1]
    path = _wheel(tmp_path, spec, version="9.9.9")
    local = replace(spec, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(RuntimeError, match="metadata version mismatch"):
        wheels.authenticate_wheel(path, local)


def test_wrong_distribution_in_metadata_fails_closed(tmp_path: Path) -> None:
    spec = wheels.EXPECTED_WHEELS[2]
    path = tmp_path / spec.filename
    with zipfile.ZipFile(path, "w") as output:
        output.writestr(
            "quillan-0.10.6.dist-info/METADATA",
            "Metadata-Version: 2.3\nName: unrelated\nVersion: 0.10.6\n"
            "Requires-Python: >=3.11\n",
        )
    local = replace(spec, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(RuntimeError, match="distribution mismatch"):
        wheels.authenticate_wheel(path, local)


def test_bad_zip_fails_even_if_digest_matches(tmp_path: Path) -> None:
    spec = wheels.EXPECTED_WHEELS[3]
    path = tmp_path / spec.filename
    path.write_bytes(b"not a zip")
    local = replace(spec, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(RuntimeError, match="not a readable wheel"):
        wheels.authenticate_wheel(path, local)


def test_url_targets_the_exact_tag_and_asset() -> None:
    for spec in wheels.EXPECTED_WHEELS:
        assert spec.url.endswith(f"/releases/download/v{spec.version}/{spec.filename}")
        assert spec.url.startswith("https://github.com/Paper-Data-Suite/")
