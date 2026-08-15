from __future__ import annotations

import sys
from pathlib import Path

from scripts import validate_repository


def test_isolated_static_cache_paths_use_validation_temp(tmp_path: Path) -> None:
    ruff, mypy = validate_repository._static_cache_paths(
        tmp_path,
        reuse_static_caches=False,
    )
    assert ruff == tmp_path / "ruff-cache"
    assert mypy == tmp_path / "mypy-cache"


def test_reusable_static_cache_paths_use_configured_persistent_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    persistent = tmp_path / "persistent"
    monkeypatch.setenv("PDS_VITRINE_STATIC_CACHE_DIR", str(persistent))

    ruff, mypy = validate_repository._static_cache_paths(
        tmp_path / "validation",
        reuse_static_caches=True,
    )

    version = f"py{sys.version_info.major}{sys.version_info.minor}"
    assert ruff == persistent / version / "ruff"
    assert mypy == persistent / version / "mypy"


def test_main_forwards_reusable_static_cache_flag(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_validate(
        core_wheel: Path,
        *,
        allow_dirty: bool,
        reuse_static_caches: bool = False,
    ) -> None:
        captured["core_wheel"] = core_wheel
        captured["allow_dirty"] = allow_dirty
        captured["reuse_static_caches"] = reuse_static_caches

    monkeypatch.setattr(validate_repository, "validate", fake_validate)
    wheel = tmp_path / "core.whl"

    result = validate_repository.main(
        [
            "--core-wheel",
            str(wheel),
            "--allow-dirty",
            "--reuse-static-caches",
        ]
    )

    assert result == 0
    assert captured == {
        "core_wheel": wheel,
        "allow_dirty": True,
        "reuse_static_caches": True,
    }
