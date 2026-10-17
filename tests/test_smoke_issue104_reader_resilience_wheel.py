"""Host-side tests for #104 disposable installed-wheel resilience acceptance."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.issue104_installed_reader_probe as probe
import scripts.smoke_test_issue104_reader_resilience_wheel as smoke
from scripts.issue104_synthetic_producer_wheels import (
    FUTURE_VERSION,
    PRODUCERS,
    create_synthetic_producer_wheel,
)


def test_synthetic_future_wheels_have_real_metadata_and_core_entrypoints(
    tmp_path: Path,
) -> None:
    assert FUTURE_VERSION == "99.123.456"
    assert set(PRODUCERS) == {"scoreform", "quillan", "concord"}
    for module, (distribution, manifest, _, contract, _) in PRODUCERS.items():
        wheel = create_synthetic_producer_wheel(tmp_path, module)
        assert wheel.name.endswith("-py3-none-any.whl")
        with zipfile.ZipFile(wheel) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            entries = next(item for item in names if item.endswith("/entry_points.txt"))
            points = archive.read(entries).decode("utf-8")
            assert f"{module} = {module}.pds_publication:" in points
            profile = archive.read(f"{module}/pds_publication.py").decode("utf-8")
            assert distribution in profile
            assert manifest in profile
            assert contract in profile
            assert f"{module}/academic_result_reader.py" in names
            assert any(item.endswith("/RECORD") for item in names)
            assert not any("tests/" in item or "fixtures/" in item for item in names)


def test_synthetic_wheel_builder_rejects_unknown_producer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported synthetic producer"):
        create_synthetic_producer_wheel(tmp_path, "other")


def test_probe_requires_valid_scenario_report(monkeypatch: pytest.MonkeyPatch,
                                              tmp_path: Path) -> None:
    captured: list[tuple[list[str], dict[str, str]]] = []

    def stub_run(command: list[str], *, cwd: Path,
                 environment: dict[str, str]) -> str:
        captured.append((command, environment))
        return json.dumps({"mode": "unsupported", "module": "scoreform",
                           "failure": "reader.incompatible"})

    monkeypatch.setattr(smoke, "_run", stub_run)
    result = smoke._probe(Path("python"), mode="unsupported", module="scoreform",
                          cwd=tmp_path, environment={})
    assert result["failure"] == "reader.incompatible"
    command, env = captured[0]
    assert command[1:3] == ["-I", "-B"]
    assert env["PDS_ISSUE104_SCENARIO"] == "unsupported"
    assert env["PDS_ISSUE104_TARGET"] == "scoreform"


def test_probe_fails_closed_on_mismatched_target(monkeypatch: pytest.MonkeyPatch,
                                                  tmp_path: Path) -> None:
    monkeypatch.setattr(
        smoke, "_run", lambda command, *, cwd, environment: json.dumps(
            {"mode": "missing", "module": "concord"}
        ),
    )
    with pytest.raises(RuntimeError, match="target module"):
        smoke._probe(Path("python"), mode="missing", module="quillan",
                     cwd=tmp_path, environment={})


def test_issue117_issue104_installed_probe_uses_current_core_066() -> None:
    """The installed-only #104 probe must qualify the active Core, not 0.6.5."""
    import tomllib

    from scripts import verify_core_wheel

    root = Path(probe.__file__).resolve().parents[1]
    source = (root / "scripts/issue104_installed_reader_probe.py").read_text(
        encoding="utf-8"
    )
    core_version = verify_core_wheel.EXPECTED_CORE_VERSION
    assert core_version == "0.6.6"
    assert (
        f'assert metadata.version("pds-core") == "{core_version}"'
        in source
    )
    assert 'assert metadata.version("pds-core") == "0.6.5"' not in source
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == [
        f"pds-core>={core_version},<0.7"
    ]


def test_issue104_installed_smoke_is_registered_for_complete_validation() -> None:
    import scripts.validate_repository as repository

    commands = dict(repository.VALIDATOR_COMMANDS)
    assert commands["issue #104 improvement / reader resilience"] == (
        "scripts/validate_issue104_acceptance.py", "--skip-focused-tests"
    )
    source = (repository.ROOT if hasattr(repository, "ROOT") else
              Path(repository.__file__).resolve().parents[1])
    text = (source / "scripts/validate_repository.py").read_text(encoding="utf-8")
    assert '"scripts/smoke_test_issue104_reader_resilience_wheel.py"' in text
    assert '"issue #104 installed reader resilience"' in text
    for rel in ("scripts/check_package.py", "pyproject.toml"):
        contents = (source / rel).read_text(encoding="utf-8")
        for filename in (
            "issue104_synthetic_producer_wheels.py",
            "issue104_installed_reader_probe.py",
            "smoke_test_issue104_reader_resilience_wheel.py",
        ):
            assert filename in contents
    assert '"tests/test_smoke_issue104_reader_resilience_wheel.py"' in (
        source / "scripts/check_package.py"
    ).read_text(encoding="utf-8")


def _issue104_scoreform_stub(number: int, source_id: str) -> SimpleNamespace:
    """One ordered-or-reordered projected attempt without installed producers."""

    values = {
        "attempt_number": number,
        "question_standard_alignments": (
            "1:RL.CR.9-10.1", "2:W.AW.9-10.1"
        ),
        "response_states": (
            ("1:selected", "2:blank")
            if number == 1
            else ("1:selected", "2:selected")
        ),
        "selected_answer_presence": (
            ("1:present", "2:absent")
            if number == 1
            else ("1:present", "2:present")
        ),
        "response_correctness": (
            ("1:true", "2:false")
            if number == 1
            else ("1:true", "2:true")
        ),
    }
    return SimpleNamespace(
        producer_source=SimpleNamespace(source_record_id=source_id),
        display_snapshot=SimpleNamespace(
            fields=tuple(
                SimpleNamespace(key=key, value=value)
                for key, value in values.items()
            )
        ),
    )


def test_issue104_scoreform_attempts_ignore_opaque_source_sort_order() -> None:
    first = _issue104_scoreform_stub(1, "source_z")
    second = _issue104_scoreform_stub(2, "source_a")
    # ProducerProjectionBatch sorts by opaque source identity, not attempt number.
    probe._verify_scoreform_attempts((first, second))
    probe._verify_scoreform_attempts((second, first))
    with pytest.raises(AssertionError):
        probe._verify_scoreform_attempts((first, first))
