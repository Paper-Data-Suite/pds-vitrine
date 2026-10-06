from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import validate_portfolio_foundation as validator


def test_foundation_audit_ignores_local_virtualenv_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    repository_doc = tmp_path / "README.md"
    repository_doc.write_text("# Repository\n", encoding="utf-8")
    repository_json = tmp_path / "fixture.json"
    repository_json.write_text(json.dumps({"status": "ok"}), encoding="utf-8")

    dependency_root = (
        tmp_path
        / ".venv"
        / "Lib"
        / "site-packages"
        / "example-1.0.dist-info"
        / "licenses"
    )
    dependency_root.mkdir(parents=True)
    (dependency_root / "license.md").write_text(
        "[missing dependency-local target](README.ijg)\n",
        encoding="utf-8",
    )
    (dependency_root / "malformed.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    assert validator.validate_json_and_paths() == 1
    assert validator.validate_no_links_or_fence_errors() == (1, 0)


def test_foundation_audit_ignored_tree_policy_covers_repository_build_artifacts() -> None:
    ignored = validator.IGNORED_REPOSITORY_TREE_NAMES
    assert {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "htmlcov",
        "venv",
    } <= ignored
    assert validator.ignored_repository_path(Path("pkg/__pycache__/module.pyc"))
    assert validator.ignored_repository_path(Path("pds_vitrine.egg-info/PKG-INFO"))
    assert not validator.ignored_repository_path(Path("docs/contracts/example.md"))
