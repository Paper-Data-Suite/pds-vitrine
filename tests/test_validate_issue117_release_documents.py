"""Issue #117 Slice 3: current release documentation contract and negative tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts import validate_issue117_release_documents as documents


def _copy_candidate(tmp_path: Path) -> Path:
    for relative in (
        *documents.DOCUMENTS,
        "README.md",
        "docs/README.md",
        "CHANGELOG.md",
        "MANIFEST.in",
        "pyproject.toml",
        "vitrine/_version.py",
        "scripts/check_package.py",
        "scripts/validate_repository.py",
    ):
        source = documents.ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return tmp_path


def test_release_candidate_documents_are_valid() -> None:
    assert documents.validate() == ()


def test_missing_candidate_matrix_fails_closed(tmp_path: Path) -> None:
    root = _copy_candidate(tmp_path)
    path = root / "docs/v0.4.0-release-compatibility.md"
    content = path.read_text(encoding="utf-8")
    assert "Pending authentication" in content
    path.write_text(
        content.replace("Pending authentication", "UNKNOWN"), encoding="utf-8"
    )
    assert any("Pending authentication" in item for item in documents.validate(root))


def test_false_publication_verdict_is_rejected(tmp_path: Path) -> None:
    root = _copy_candidate(tmp_path)
    path = root / "docs/v0.4.0-release-audit.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\nFinal release verdict: **RELEASED — VERIFIED**\n",
        encoding="utf-8",
    )
    assert (
        "candidate audit claims a final verified publication"
        in documents.validate(root)
    )


def test_core_only_runtime_dependency_remains_required(tmp_path: Path) -> None:
    root = _copy_candidate(tmp_path)
    path = root / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    assert '"pds-core>=0.6.6,<0.7"' in content
    path.write_text(
        content.replace(
            '"pds-core>=0.6.6,<0.7"',
            '"pds-core>=0.6.6,<0.7", "scoreform==0.13.0"',
            1,
        ),
        encoding="utf-8",
    )
    assert (
        "current Core-only dependency requirement drifted"
        in documents.validate(root)
    )


def test_current_document_inventory_cannot_shrink(tmp_path: Path) -> None:
    root = _copy_candidate(tmp_path)
    (root / "docs/v0.4.0-release-checklist.md").unlink()
    assert any(
        "v0.4.0 document missing" in item for item in documents.validate(root)
    )
