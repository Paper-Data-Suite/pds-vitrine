from __future__ import annotations

from pathlib import Path

from scripts.smoke_test_paper_reflection_end_to_end_wheel import (
    _copy_fixture_harness,
)

ROOT = Path(__file__).resolve().parents[1]


def test_paper_reflection_installed_harness_copies_only_test_support(
    tmp_path: Path,
) -> None:
    harness = tmp_path / "harness"
    harness.mkdir()

    _copy_fixture_harness(harness)

    assert (harness / "scripts" / "candidate_fixture_support.py").is_file()
    assert (harness / "scripts" / "curation_fixture_support.py").is_file()
    assert (harness / "fixtures" / "producer-adapters").is_dir()
    assert not (harness / "vitrine").exists()
    assert not (harness / "pds_core").exists()


def test_pip_check_wheel_smokes_install_declared_vitrine_dependencies() -> None:
    offenders: list[str] = []
    for path in sorted((ROOT / "scripts").glob("smoke_test_*_wheel.py")):
        source = path.read_text(encoding="utf-8")
        if '"pip", "check"' in source and '"--no-deps"' in source:
            offenders.append(path.name)

    assert offenders == []
