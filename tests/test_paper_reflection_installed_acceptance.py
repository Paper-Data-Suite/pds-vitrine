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


def test_legacy_core_only_wheel_smokes_preserve_no_deps_isolation() -> None:
    names = (
        "smoke_test_adapter_wheel.py",
        "smoke_test_attention_next_actions_wheel.py",
        "smoke_test_candidate_evidence_review_wheel.py",
        "smoke_test_candidate_inbox_wheel.py",
        "smoke_test_candidate_review_selection_wheel.py",
        "smoke_test_candidate_wheel.py",
        "smoke_test_compatibility_wheel.py",
        "smoke_test_curation_wheel.py",
        "smoke_test_current_portfolio_build_export_wheel.py",
        "smoke_test_end_to_end_wheel.py",
        "smoke_test_guided_menu_interactions_wheel.py",
        "smoke_test_operations_wheel.py",
        "smoke_test_portfolio_setup_wheel.py",
        "smoke_test_selection_placement_guidance_wheel.py",
        "smoke_test_snapshot_wheel.py",
        "smoke_test_starter_profiles_wheel.py",
        "smoke_test_teacher_information_architecture_wheel.py",
        "smoke_test_working_composition_wheel.py",
    )
    for name in names:
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert '"--no-deps"' in source
