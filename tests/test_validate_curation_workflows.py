from __future__ import annotations

import scripts.validate_curation_workflows as validator


def test_curation_workflow_validator_locks_foundation_hashes() -> None:
    assert {path.name for path in validator.LOCKED_FIXTURES} == {
        "improvement-foundational-records-v1.json",
        "showcase-foundational-records-v1.json",
    }
    for path, expected in validator.LOCKED_FIXTURES.items():
        assert validator._sha256(path) == expected
