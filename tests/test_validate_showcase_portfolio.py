from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import scripts.validate_showcase_portfolio as validator

ROOT = Path(__file__).resolve().parents[1]


def test_showcase_runtime_manifests_are_explicit_development_fixtures() -> None:
    runtime = ROOT / "fixtures" / "representative-portfolios" / "showcase" / "runtime"
    for path in (runtime / "polished-manifest.json", runtime / "concord-manifest.json"):
        body = path.read_text(encoding="utf-8")
        assert '"integration_kind":"development_fixture"' in body
        assert '"producer_module_id":"vitrine_' in body


def test_showcase_validator_entrypoint_maps_success_without_reexecuting_slice(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        lambda: SimpleNamespace(edition_identity=("series-test", 1)),
    )

    assert validator.main() == 0
    assert "PASS executable showcase Portfolio" in capsys.readouterr().out


def test_frozen_foundational_fixture_hashes_are_unchanged() -> None:
    expected = {
        "improvement-foundational-records-v1.json": "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8",
        "showcase-foundational-records-v1.json": "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360",
    }
    root = ROOT / "tests" / "fixtures" / "runtime-models"
    assert {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in expected
    } == expected
