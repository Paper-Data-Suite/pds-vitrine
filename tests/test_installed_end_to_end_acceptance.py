from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from pds_core.publication_compatibility import discover_publication_producer_profiles

from scripts.smoke_test_end_to_end_wheel import (
    InstalledAcceptanceHarnessError,
    InventoryEntry,
    _require_wheel,
    build_isolated_environment,
    build_probe_command,
    inventory_git_tracked,
    inventory_git_visible,
    inventory_tree,
    require_report_safe,
)
from scripts.verify_installed_end_to_end import (
    STAGES,
    InstalledEndToEndAcceptanceError,
    _actor,
    _build_installed_workflow_dependencies,
    _DeferredSnapshotRendererRegistry,
    _DeferredSnapshotSourceRegistry,
    _dependency_report,
    _fixture_file,
    _installed_origin,
    _live_support_requests,
    _showcase_profile_records,
    _snapshot_source_root,
)
from scripts.verify_installed_end_to_end_reload import (
    HistoricalReloadError,
    _expect_pointer_probe,
    _expect_snapshot_rows,
    _load_expectations,
)
from vitrine.development_adapters import (
    SCOREFORM_FIXTURE_SUPPORT_REQUEST,
    ScoreFormFixtureReader,
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.producer_adapters import ProducerAdapterUnsupportedError
from vitrine.snapshot_materialization import (
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.workflow_context import default_workflow_dependencies


def test_inventory_tree_detects_content_addition_and_deletion(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    first = root / "first.txt"
    second = root / "second.txt"
    first.write_text("alpha\n", encoding="utf-8")
    second.write_text("beta\n", encoding="utf-8")

    baseline = inventory_tree(root)
    assert all(isinstance(item, InventoryEntry) for item in baseline)

    first.write_text("changed\n", encoding="utf-8")
    assert inventory_tree(root) != baseline

    first.write_text("alpha\n", encoding="utf-8")
    extra = root / "extra.txt"
    extra.write_text("new\n", encoding="utf-8")
    assert inventory_tree(root) != baseline

    extra.unlink()
    second.unlink()
    assert inventory_tree(root) != baseline


def test_inventory_git_tracked_detects_exact_tracked_content_change(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "tracked.txt"],
        cwd=repository,
        check=True,
        capture_output=True,
    )

    baseline = inventory_git_tracked(repository)
    tracked.write_text("after\n", encoding="utf-8")
    assert inventory_git_tracked(repository) != baseline


def test_isolated_environment_clears_pythonpath_and_sets_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    base = {
        "PYTHONPATH": "should-not-survive",
        "OTHER": "retained",
    }

    env = build_isolated_environment(base, workspace=workspace)

    assert "PYTHONPATH" not in env
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PDS_WORKSPACE_ROOT"] == str(workspace.resolve())
    assert env["OTHER"] == "retained"
    assert base["PYTHONPATH"] == "should-not-survive"


def test_probe_command_uses_isolated_mode_and_explicit_paths(tmp_path: Path) -> None:
    python = tmp_path / "python"
    verifier = tmp_path / "verify.py"
    repository = tmp_path / "repo"
    fixture_root = repository / "fixtures"
    workspace = tmp_path / "workspace"
    digest = "a" * 64

    command = build_probe_command(
        python,
        verifier,
        repository=repository,
        fixture_root=fixture_root,
        workspace=workspace,
        vitrine_wheel_sha256=digest,
        core_wheel_sha256=digest,
    )

    assert command[:4] == [str(python), "-I", "-B", str(verifier.resolve())]
    assert "--repository" in command
    assert str(repository.resolve()) in command
    assert "--fixture-root" in command
    assert str(fixture_root.resolve()) in command
    assert "--workspace" in command
    assert str(workspace.resolve()) in command
    assert command[-1] == "--end-to-end"

    curation = build_probe_command(
        python,
        verifier,
        repository=repository,
        fixture_root=fixture_root,
        workspace=workspace,
        vitrine_wheel_sha256=digest,
        core_wheel_sha256=digest,
        curation_only=True,
    )
    assert curation[-1] == "--curation-only"

    snapshot = build_probe_command(
        python,
        verifier,
        repository=repository,
        fixture_root=fixture_root,
        workspace=workspace,
        vitrine_wheel_sha256=digest,
        core_wheel_sha256=digest,
        snapshot_only=True,
    )
    assert snapshot[-1] == "--snapshot-only"

    discovery = build_probe_command(
        python,
        verifier,
        repository=repository,
        fixture_root=fixture_root,
        workspace=workspace,
        vitrine_wheel_sha256=digest,
        core_wheel_sha256=digest,
        discovery_only=True,
    )
    assert discovery[-1] == "--discovery-only"

    boundary = build_probe_command(
        python,
        verifier,
        repository=repository,
        fixture_root=fixture_root,
        workspace=workspace,
        vitrine_wheel_sha256=digest,
        core_wheel_sha256=digest,
        boundary_only=True,
    )
    assert boundary[-1] == "--boundary-only"


def test_installed_origin_rejects_source_checkout_path(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    package = repository / "vitrine" / "__init__.py"
    package.parent.mkdir(parents=True)
    package.write_text("", encoding="utf-8")

    assert not _installed_origin(package.resolve(), repository.resolve())


def test_fixture_registries_are_explicit_and_default_context_is_fail_closed() -> None:
    defaults = default_workflow_dependencies()
    assert defaults.producer_registry.profiles == ()
    assert defaults.adapter_registry.adapters == ()
    assert defaults.development_fixture_mode is False
    assert type(defaults.snapshot_planning_provider).__name__ == (
        "UnconfiguredSnapshotPlanningProvider"
    )

    fixture_profiles = build_development_fixture_producer_registry()
    assert tuple(item.module_id for item in fixture_profiles.profiles) == (
        "vitrine_concord_fixture",
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
    )
    fixture_adapters = build_development_fixture_adapter_registry()
    assert len(fixture_adapters.adapters) == 3
    assert all(
        item.declaration.integration_kind == "development_fixture"
        for item in fixture_adapters.adapters
    )


@pytest.mark.parametrize("producer", ("scoreform", "quillan", "concord"))
def test_live_like_contracts_cannot_match_fixture_adapters(producer: str) -> None:
    registry = build_development_fixture_adapter_registry()
    request = _live_support_requests()[producer]

    with pytest.raises(ProducerAdapterUnsupportedError) as captured:
        registry.select_adapter(request)

    assert captured.value.code == "adapter.unsupported_contract"


def test_acceptance_error_is_bounded_single_line() -> None:
    error = InstalledEndToEndAcceptanceError(
        "fixture_boundary", "stable bounded failure"
    )
    assert error.stage == "fixture_boundary"
    assert str(error) == "fixture_boundary: stable bounded failure"

    with pytest.raises(ValueError):
        InstalledEndToEndAcceptanceError("fixture_boundary", "bad\nmessage")


def test_environment_builder_does_not_mutate_process_environment(
    tmp_path: Path,
) -> None:
    before = dict(os.environ)
    build_isolated_environment(os.environ, workspace=tmp_path / "workspace")
    assert dict(os.environ) == before


def test_fixture_file_requires_contained_ordinary_file(tmp_path: Path) -> None:
    root = tmp_path / "fixtures"
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")

    assert _fixture_file(root, "manifest.json") == manifest.resolve()

    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    with pytest.raises(InstalledEndToEndAcceptanceError) as captured:
        _fixture_file(root, "../outside.json")
    assert captured.value.stage == "core_publication"


def test_installed_acceptance_scoreform_fixture_uses_shared_subject_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "fixtures" / "installed-acceptance" / "scoreform-manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))

    assert value["assignment"]["class_id"] == "class-ela11-syn"
    assert value["assignment"]["student_id"] == "student-syn-001"
    assert [item["attempt_number"] for item in value["attempts"]] == [1, 2]
    assert [item["points_earned"] for item in value["attempts"]] == [7, 9]
    assert value["fixture_contract"] == "vitrine_fixture_scoreform_manifest_v1"


def test_installed_acceptance_scoreform_projection_kind_matches_fixture_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "fixtures" / "installed-acceptance" / "scoreform-manifest.json"
    registry = build_development_fixture_adapter_registry()
    adapter = registry.select_adapter(SCOREFORM_FIXTURE_SUPPORT_REQUEST)
    public_model = ScoreFormFixtureReader().read(path.read_bytes())
    batch = adapter.project(public_model)

    assert tuple(item.projection_kind for item in batch.projected_sources) == (
        "scoreform_fixture:attempt_summary",
        "scoreform_fixture:attempt_summary",
    )
    assert tuple(
        item.producer_source.source_record_id for item in batch.projected_sources
    ) == (
        "argument_assessment_attempt_1",
        "argument_assessment_attempt_2",
    )
    assert tuple(
        item.producer_source.native_revision for item in batch.projected_sources
    ) == (1, 2)


def test_installed_acceptance_stage_order_freezes_curation_before_snapshot() -> None:
    assert STAGES == (
        "installed_provenance",
        "fixture_boundary",
        "workspace_identity",
        "profile_setup",
        "core_publication",
        "candidate_discovery",
        "improvement_curation",
        "showcase_curation",
        "improvement_snapshot",
        "showcase_snapshot",
        "source_drift",
        "historical_reload",
        "write_isolation",
    )


def test_showcase_profile_requires_exact_collaborator_review() -> None:
    _, revision, requirements = _showcase_profile_records(_actor())
    approval = tuple(
        item
        for item in requirements
        if item.requirement_id == "installed_showcase_collaborator_review"
    )

    assert len(approval) == 1
    assert approval[0].requirement_kind == "approval"
    assert approval[0].obligation == "required"
    assert approval[0].satisfaction_class == "curation_review"
    assert revision.audience_rules[0].required_review_classes == ("privacy_review",)


def test_installed_snapshot_source_fixture_is_exact_and_staged_outside_workspace(
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / "fixtures"
    source = fixture_root / "installed-acceptance" / "source-root" / "artifacts"
    source.mkdir(parents=True)
    names = (
        "baseline-argument.txt",
        "revised-argument.txt",
        "revised-feedback.txt",
        "polished-literary-analysis.txt",
        "group-artifact.txt",
    )
    for name in names:
        (source / name).write_text(f"{name}\n", encoding="utf-8")
    workspace = tmp_path / "workspace"

    staged = _snapshot_source_root(fixture_root, workspace)

    assert staged == (tmp_path / "producer-source").resolve()
    assert not staged.is_relative_to(workspace.resolve())
    assert {
        item.relative_to(staged).as_posix()
        for item in staged.rglob("*")
        if item.is_file()
    } == {f"artifacts/{name}" for name in names}


def test_probe_command_rejects_multiple_explicit_modes(tmp_path: Path) -> None:
    digest = "a" * 64
    with pytest.raises(InstalledAcceptanceHarnessError):
        build_probe_command(
            tmp_path / "python",
            tmp_path / "verify.py",
            repository=tmp_path / "repo",
            fixture_root=tmp_path / "repo" / "fixtures",
            workspace=tmp_path / "workspace",
            vitrine_wheel_sha256=digest,
            core_wheel_sha256=digest,
            discovery_only=True,
            curation_only=True,
        )



def test_inventory_git_visible_detects_untracked_content_change(tmp_path: Path) -> None:
    repository = tmp_path / "repo-visible"
    repository.mkdir()
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True, capture_output=True)
    untracked = repository / "acceptance.py"
    untracked.write_text("before\n", encoding="utf-8")

    baseline = inventory_git_visible(repository)
    untracked.write_text("after\n", encoding="utf-8")

    assert inventory_git_visible(repository) != baseline


def test_historical_reload_expectations_reject_unbounded_payload(tmp_path: Path) -> None:
    path = tmp_path / "expectations.json"
    path.write_text(
        json.dumps(
            {
                "workspace_state_revision": 1,
                "record_inventory": {},
                "record_inventory_sha256": "a" * 64,
                "snapshots": [],
                "pointer_probe": {
                    "snapshot_series_id": "series_test",
                    "pointed_edition_number": 1,
                    "greatest_edition_number": 2,
                    "successor_manifest_sha256": "b" * 64,
                    "successor_logical_inventory_sha256": "c" * 64,
                },
                "raw_payload": {"student_name": "must-not-cross-process-boundary"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HistoricalReloadError):
        _load_expectations(path)



def test_invalid_wheel_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InstalledAcceptanceHarnessError):
        _require_wheel(tmp_path / "missing.whl", "Vitrine wheel")

    not_wheel = tmp_path / "not-a-wheel.txt"
    not_wheel.write_text("not a wheel\n", encoding="utf-8")
    with pytest.raises(InstalledAcceptanceHarnessError):
        _require_wheel(not_wheel, "Core wheel")


def test_core_discovery_does_not_expose_vitrine_fixture_profiles() -> None:
    discovered = discover_publication_producer_profiles()
    module_ids = {item.module_id for item in discovered}

    assert "vitrine_scoreform_fixture" not in module_ids
    assert "vitrine_quillan_fixture" not in module_ids
    assert "vitrine_concord_fixture" not in module_ids


def test_installed_workflow_dependencies_are_one_explicit_fixture_context() -> None:
    dependencies = _build_installed_workflow_dependencies()
    report = _dependency_report(dependencies)

    assert report == {
        "context_type": "VitrineWorkflowDependencies",
        "development_fixture_mode": True,
        "producer_profile_ids": (
            "vitrine_concord_fixture",
            "vitrine_quillan_fixture",
            "vitrine_scoreform_fixture",
        ),
        "adapter_count": 3,
        "source_read_gate": "_SourceReadGate",
        "curation_authority_gate": "_CurationGate",
        "snapshot_build_authority_gate": "_InstalledSnapshotAuthorityGate",
        "snapshot_source_registry": "_DeferredSnapshotSourceRegistry",
        "snapshot_renderer_registry": "_DeferredSnapshotRendererRegistry",
        "snapshot_planning_provider": "UnconfiguredSnapshotPlanningProvider",
    }
    assert type(dependencies.source_read_authorization_gate).__name__ == "_SourceReadGate"
    assert type(dependencies.curation_authority_gate).__name__ == "_CurationGate"
    assert type(dependencies.snapshot_build_authority_gate).__name__ == (
        "_InstalledSnapshotAuthorityGate"
    )
    assert isinstance(
        dependencies.snapshot_source_providers, _DeferredSnapshotSourceRegistry
    )
    assert isinstance(
        dependencies.snapshot_source_providers, SnapshotSourceProviderRegistry
    )
    assert isinstance(
        dependencies.snapshot_renderers, _DeferredSnapshotRendererRegistry
    )
    assert isinstance(dependencies.snapshot_renderers, SnapshotRendererRegistry)


def test_public_acceptance_report_rejects_prohibited_markers() -> None:
    require_report_safe({"status": "safe", "count": 2})

    with pytest.raises(InstalledAcceptanceHarnessError):
        require_report_safe({"leak": "PRIVATE_TEACHER_NOTE"})
    with pytest.raises(InstalledAcceptanceHarnessError):
        require_report_safe({"leak": "collaborator-syn-001"})


def test_pointer_expectation_requires_pointed_edition_below_greatest() -> None:
    safe = {
        "snapshot_series_id": "series_test",
        "pointed_edition_number": 1,
        "greatest_edition_number": 2,
        "successor_manifest_sha256": "a" * 64,
        "successor_logical_inventory_sha256": "b" * 64,
    }
    assert _expect_pointer_probe(safe) == safe

    invalid = dict(safe)
    invalid["pointed_edition_number"] = 2
    with pytest.raises(HistoricalReloadError):
        _expect_pointer_probe(invalid)


def test_historical_snapshot_expectation_schema_is_exact() -> None:
    row = {
        "snapshot_series_id": "series_test",
        "build_request_id": "request_test",
        "build_plan_id": "plan_test",
        "build_plan_fingerprint": "a" * 64,
        "build_attempt_id": "attempt_test",
        "edition_number": 1,
        "seal_id": "seal_test",
        "manifest_sha256": "b" * 64,
        "logical_inventory_sha256": "c" * 64,
        "export_artifact_id": "export_test",
        "export_inventory_sha256": "d" * 64,
        "current_pointer_revision": 1,
    }
    rows = _expect_snapshot_rows([row, dict(row, snapshot_series_id="series_two")])
    assert rows[0]["build_plan_fingerprint"] == "a" * 64
    assert rows[0]["manifest_sha256"] == "b" * 64
    assert rows[0]["current_pointer_revision"] == 1

    malformed = dict(row)
    malformed["unexpected"] = "not-bounded"
    with pytest.raises(HistoricalReloadError):
        _expect_snapshot_rows([row, malformed])


def test_inventory_tree_detects_installed_package_mutation(tmp_path: Path) -> None:
    package = tmp_path / "site-packages" / "vitrine"
    package.mkdir(parents=True)
    module = package / "module.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    baseline = inventory_tree(package)

    module.write_text("VALUE = 2\n", encoding="utf-8")
    assert inventory_tree(package) != baseline

def test_repository_gate_wires_installed_end_to_end_once() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts" / "validate_repository.py").read_text(encoding="utf-8")

    assert text.count('"scripts/smoke_test_end_to_end_wheel.py"') == 1
    assert text.count('phase="installed-wheel acceptance: end-to-end"') == 1

