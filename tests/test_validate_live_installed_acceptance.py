from __future__ import annotations

from pathlib import Path

from scripts import validate_live_installed_acceptance as validator


def test_issue_71_static_validator_passes_without_heavy_wheels() -> None:
    validator.validate(run_focused_tests=False)


def test_issue_71_required_files_are_repository_relative() -> None:
    root = Path(validator.ROOT)
    for relative in validator.REQUIRED_ACCEPTANCE_FILES:
        path = root / relative
        assert path.is_file()
        assert path.resolve().is_relative_to(root.resolve())


def test_slice_2_installed_scenario_files_are_present() -> None:
    root = Path(validator.ROOT)
    for relative in (
        "scripts/live_installed_acceptance_support.py",
        "scripts/live_installed_acceptance_scenario.py",
    ):
        assert (root / relative).is_file()


def test_slice_2_scenario_static_contract_passes() -> None:
    validator._validate_candidate_scenario()


def test_slice_2_scenario_uses_shared_vitrine_release_candidate_version() -> None:
    scenario = (
        Path(validator.ROOT) / "scripts" / "live_installed_acceptance_scenario.py"
    ).read_text(encoding="utf-8")
    assert '"pds-vitrine": EXPECTED_VITRINE_VERSION' in scenario
    assert '"pds-vitrine": "0.2.0"' not in scenario


def test_slice_2_concord_standard_identity_is_path_safe() -> None:
    support = (Path(validator.ROOT) / "scripts" / "live_installed_acceptance_support.py").read_text(
        encoding="utf-8"
    )
    assert 'CONCORD_STANDARD_ID = "synthetic_collab_accept_1"' in support
    assert 'CONCORD_STANDARD_ID = "synthetic:COLLAB.ACCEPT.1"' not in support



def test_slice_3_curated_snapshot_file_is_present() -> None:
    root = Path(validator.ROOT)
    assert (root / "scripts/live_installed_acceptance_portfolio.py").is_file()


def test_slice_3_curated_snapshot_static_contract_passes() -> None:
    validator._validate_curated_snapshot_scenario()


def test_slice_4a_negative_matrix_file_is_present() -> None:
    root = Path(validator.ROOT)
    assert (root / "scripts/live_installed_acceptance_negative.py").is_file()


def test_slice_4a_negative_matrix_static_contract_passes() -> None:
    validator._validate_negative_matrix_scenario()


def test_slice_4b_custody_verifier_files_are_present() -> None:
    root = Path(validator.ROOT)
    for relative in (
        "scripts/live_installed_acceptance_custody.py",
        "scripts/live_installed_acceptance_verifier.py",
    ):
        assert (root / relative).is_file()


def test_slice_4b_custody_verifier_static_contract_passes() -> None:
    validator._validate_custody_verifier_scenario()


def test_issue_71_final_ci_wiring_static_contract_passes() -> None:
    validator._validate_ci_wiring()
