from __future__ import annotations

from scripts.improvement_portfolio_fixture_support import IMPROVEMENT_ROOT


def test_runtime_manifests_are_explicit_development_fixtures() -> None:
    for name in ("baseline-manifest.json", "later-manifest.json"):
        payload = (IMPROVEMENT_ROOT / "runtime" / name).read_text(encoding="utf-8")
        assert '"integration_kind":"development_fixture"' in payload
        assert '"producer_module_id":"vitrine_quillan_fixture"' in payload
        assert "pds-quillan" not in payload

