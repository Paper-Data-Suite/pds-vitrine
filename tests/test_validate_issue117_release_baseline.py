"""Issue #117 baseline and frozen historical-release mutation tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import validate_issue117_release_baseline as baseline


def _isolated_baseline(tmp_path: Path) -> Path:
    for relative in (
        *baseline.FROZEN_PATHS,
        "pyproject.toml",
        "vitrine/_version.py",
        baseline.SNAPSHOT_PATH,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(baseline.ROOT / relative, target)
    return tmp_path


def test_issue117_baseline_is_currently_valid() -> None:
    assert baseline.validate() == ()


def test_issue117_frozen_v030_release_evidence_fails_on_drift(tmp_path: Path) -> None:
    root = _isolated_baseline(tmp_path)
    target = root / "docs/v0.3.0-release-audit.md"
    target.write_bytes(target.read_bytes() + b"\nchanged\n")
    assert any(
        "historical release evidence modified" in item
        for item in baseline.validate(root)
    )


def test_issue117_frozen_release_inventory_cannot_shrink(tmp_path: Path) -> None:
    root = _isolated_baseline(tmp_path)
    manifest = root / baseline.SNAPSHOT_PATH
    record = json.loads(manifest.read_text(encoding="utf-8"))
    record["historical_sha256"].pop(baseline.FROZEN_PATHS[0])
    manifest.write_text(json.dumps(record), encoding="utf-8")
    assert "historical release file inventory was changed" in baseline.validate(root)


def test_issue117_core_floor_and_optional_producers_remain_separate(
    tmp_path: Path,
) -> None:
    root = _isolated_baseline(tmp_path)
    project = root / "pyproject.toml"
    content = project.read_text(encoding="utf-8")
    assert '"pds-core>=0.6.6,<0.7"' in content
    project.write_text(
        content.replace(
            '"pds-core>=0.6.6,<0.7"',
            '"pds-core>=0.6.6,<0.7", "pds-vitrine==0.4.0"',
            1,
        ),
        encoding="utf-8",
    )
    assert any(
        "forbidden unconditional sibling dependency" in item
        for item in baseline.validate(root)
    )


def test_issue117_source_version_can_be_promoted_without_falsifying_history(
    tmp_path: Path,
) -> None:
    root = _isolated_baseline(tmp_path)
    source = root / "vitrine/_version.py"
    content = source.read_text(encoding="utf-8")
    assert '__version__ = "0.4.0"' in content
    # Reverting the *surrogate* source version still preserves the audit.
    source.write_text(content.replace('"0.4.0"', '"0.3.0"'), encoding="utf-8")
    assert baseline.validate(root) == ()
