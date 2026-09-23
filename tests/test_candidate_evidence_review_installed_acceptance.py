from __future__ import annotations

import ast
from pathlib import Path

import scripts.validate_candidate_evidence_review as validator

ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.add(node.module)
    return values


def test_issue96_installed_runner_uses_exact_public_preview_boundaries() -> None:
    path = ROOT / "scripts/live_installed_candidate_evidence_review.py"
    source = path.read_text(encoding="utf-8")
    assert '"pds-core": "0.6.3"' in source
    assert '"scoreform": "0.11.0"' in source
    assert '"quillan": "0.10.1"' in source
    assert '"pds-concord": "0.3.0"' in source
    assert "prepare_candidate_evidence_preview_context" in source
    assert "acquire_candidate_evidence_artifact_preview" in source
    assert "build_candidate_evidence_presentation" in source
    assert "vitrine_scoreform_fixture" not in source
    assert "vitrine_quillan_fixture" not in source
    assert "vitrine_concord_fixture" not in source
    assert "snapshot_plan_id" not in source
    assert "snapshot_attempt_id" not in source
    assert "review.json" not in source


def test_issue96_outer_qualifier_remains_producer_import_free() -> None:
    path = ROOT / "scripts/qualify_installed_live_portfolio.py"
    roots = {value.split(".", 1)[0] for value in _imports(path)}
    assert not {"scoreform", "quillan", "concord"}.intersection(roots)
    source = path.read_text(encoding="utf-8")
    assert "--candidate-evidence-review-only" in source
    assert 'version="0.10.1"' in source
    assert (
        'sha256="5311cccc03a012a7d319827e30b5a989901a9e77693171a8861e4e58409764ad"'
        in source
    )
    assert "PASS issue #96 installed Candidate evidence review acceptance" in source


def test_issue96_installed_smoke_is_core_vitrine_only() -> None:
    source = (
        ROOT / "scripts/smoke_test_candidate_evidence_review_wheel.py"
    ).read_text(encoding="utf-8")
    assert '"--no-deps"' in source
    assert "vitrine_candidate_evidence_preview_v1" in source
    assert "vitrine_candidate_evidence_artifact_preview_v1" in source
    assert "scoreform" in source
    assert "quillan" in source
    assert "concord" in source


def test_issue96_validator_freezes_installed_acceptance_wiring() -> None:
    validator.validate(run_focused_tests=False)
