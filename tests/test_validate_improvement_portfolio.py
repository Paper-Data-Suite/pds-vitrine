from __future__ import annotations

from scripts.improvement_portfolio_fixture_support import IMPROVEMENT_ROOT
from scripts.validate_improvement_portfolio import EXPECTED_ENTRY_PATHS


def test_runtime_manifests_are_explicit_development_fixtures() -> None:
    for name in ("baseline-manifest.json", "later-manifest.json"):
        payload = (IMPROVEMENT_ROOT / "runtime" / name).read_text(encoding="utf-8")
        assert '"integration_kind":"development_fixture"' in payload
        assert '"producer_module_id":"vitrine_quillan_fixture"' in payload
        assert "pds-quillan" not in payload


def test_improvement_validator_locks_exact_entry_inventory_without_running_slice() -> None:
    assert EXPECTED_ENTRY_PATHS == (
        "baseline/argument.txt",
        "later/argument.txt",
        "later/student-feedback.txt",
        "reflection/student-comparison.md",
    )

