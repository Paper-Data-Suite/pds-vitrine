from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.validate_showcase_portfolio import validate

ROOT = Path(__file__).resolve().parents[1]


def test_showcase_runtime_manifests_are_explicit_development_fixtures() -> None:
    runtime = ROOT / "fixtures" / "representative-portfolios" / "showcase" / "runtime"
    for path in (runtime / "polished-manifest.json", runtime / "concord-manifest.json"):
        body = path.read_text(encoding="utf-8")
        assert '"integration_kind":"development_fixture"' in body
        assert '"producer_module_id":"vitrine_' in body


def test_complete_showcase_validator_proves_exact_reproducible_export() -> None:
    report = validate()
    assert report.subject_id == "portfolio-subject-syn-001"
    assert report.candidate_ids == ("candidate-show-polished", "candidate-show-group")
    assert len(report.selection_ids) == len(report.placement_ids) == 2
    assert report.edition_identity[1] == 1
    assert tuple(item[0] for item in report.entry_inventory) == (
        "01-polished-literary-analysis.txt",
        "02-group-water-quality-recommendation.txt",
        "03-audience-safe-attribution.txt",
        "04-curation-rationale.md",
        "05-index.md",
    )
    assert len(report.manifest_sha256) == len(report.logical_inventory_sha256) == 64
    assert len(report.export_inventory_sha256) == 64


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
