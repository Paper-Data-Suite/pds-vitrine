from __future__ import annotations

import scripts.validate_profile_workflows as validator


def test_profile_workflow_validator_entrypoint_maps_success_without_reexecution(
    monkeypatch, capsys
) -> None:
    calls = 0

    def fake_validate() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(validator, "validate", fake_validate)

    assert validator.main() == 0
    assert calls == 1
    assert "PASS Portfolio Profile workflow validation" in capsys.readouterr().out
