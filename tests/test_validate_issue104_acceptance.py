"""Focused contract and mutation tests for the #104 umbrella validator."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_issue104_acceptance as acceptance


def test_issue104_static_acceptance_and_source_inventory() -> None:
    acceptance.validate(run_focused_tests=False, run_synthetic_journey=False)
    assert "tests/test_quillan_adapter.py" in acceptance.FOCUSED_TESTS
    assert "tests/test_portfolio_presentation_end_to_end_issue101.py" in (
        acceptance.FOCUSED_TESTS
    )


def test_issue104_runtime_policy_guard_blocks_release_equality() -> None:
    source = (
        acceptance.ROOT / "vitrine/producer_reader_compatibility.py"
    ).read_text(encoding="utf-8")
    modified = source.replace(
        "if installed_distribution_version in legacy:",
        "if installed_distribution_version == audit.release_version:",
        1,
    )
    assert modified != source
    with pytest.raises(RuntimeError, match="exact-release|semantic compatibility"):
        acceptance._validate_version_policy_source(modified)


def test_issue104_runtime_policy_guard_blocks_semver_ordering() -> None:
    source = (
        acceptance.ROOT / "vitrine/producer_reader_compatibility.py"
    ).read_text(encoding="utf-8")
    modified = source.replace(
        "if installed_distribution_version in legacy:",
        'if installed_distribution_version >= "0.13.0":',
        1,
    )
    assert modified != source
    with pytest.raises(RuntimeError, match="semantic compatibility"):
        acceptance._validate_version_policy_source(modified)


def test_issue104_reader_service_guard_blocks_wheel_identity() -> None:
    source = (acceptance.ROOT / "vitrine/producer_reader_services.py").read_text(
        encoding="utf-8"
    )
    modified = source.replace(
        "def read(self, value: bytes) -> object:",
        (
            "def read(self, value: bytes) -> object:\n"
            "        _ = self.audit.release_version"
        ),
        1,
    )
    assert modified != source
    with pytest.raises(RuntimeError, match="exact-wheel release"):
        acceptance._validate_reader_service_source(modified)


def test_issue104_runner_composes_existing_journeys_without_inlining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(acceptance, "_run_command", calls.append)
    acceptance.validate()
    assert len(calls) == 2
    assert calls[0][1:] == ("scripts/validate_improvement_portfolio.py",)
    assert calls[1][1:4] == ("-m", "pytest", "-q")
    assert calls[1][4:] == acceptance.FOCUSED_TESTS


def test_issue104_skip_flags_run_static_guards_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbid_subprocess(arguments: tuple[str, ...]) -> None:
        raise AssertionError(f"Unexpected acceptance subprocess: {arguments}")

    monkeypatch.setattr(acceptance, "_run_command", forbid_subprocess)
    assert acceptance.main(
        ["--skip-focused-tests", "--skip-synthetic-journey"]
    ) == 0
    assert "PASS Issue #104" in capsys.readouterr().out


def test_issue104_invalid_contract_policy_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="exactly one function"):
        acceptance._validate_version_policy_source("def other():\n    pass\n")


def test_issue104_acceptance_source_is_checkout_scoped() -> None:
    assert acceptance.ROOT == Path(__file__).resolve().parents[1]
