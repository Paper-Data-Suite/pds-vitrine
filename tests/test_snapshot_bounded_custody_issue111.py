from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import vitrine.snapshot_distribution as distribution_module
from tests.test_snapshot_services import (
    ACTOR,
    _execution_plan,
    _ExecutionAuthority,
    _ExecutionRenderer,
    _ExecutionSourceProvider,
    _prepare,
    fixed_clock,
)
from vitrine.path_policy import CUSTODY_TOKEN_MAX_LENGTH
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    acquire_snapshot_series_lock,
    bounded_snapshot_attempt_staging_root,
    bounded_snapshot_edition_root,
    bounded_snapshot_export_path,
    bounded_snapshot_exports_root,
    bounded_snapshot_locks_root,
    bounded_snapshot_series_lock_path,
    bounded_snapshot_staging_root,
    create_snapshot_staging,
    inspect_snapshot_series_lock,
    legacy_snapshot_attempt_staging_root,
    legacy_snapshot_export_path,
    legacy_snapshot_series_lock_path,
    load_snapshot_staging,
    snapshot_attempt_staging_root,
    snapshot_edition_root,
    snapshot_export_path_from_relative,
)
from vitrine.snapshot_distribution import (
    create_snapshot_directory_export,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_services import (
    execute_snapshot_build_attempt,
    seal_snapshot_build_attempt,
)


def test_long_snapshot_identities_have_fixed_bounded_custody_components(
    tmp_path: Path,
) -> None:
    series_id = "snapshot_series_" + ("s" * 10_000)
    attempt_id = "snapshot_attempt_" + ("a" * 10_000)
    export_id = "snapshot_export_" + ("e" * 10_000)

    staging = bounded_snapshot_attempt_staging_root(tmp_path, attempt_id)
    edition = bounded_snapshot_edition_root(tmp_path, series_id, 123456789)
    lock = bounded_snapshot_series_lock_path(tmp_path, series_id)
    export = bounded_snapshot_export_path(
        tmp_path,
        snapshot_series_id=series_id,
        edition_number=123456789,
        snapshot_export_artifact_id=export_id,
    )

    assert len(staging.name) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(edition.name) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(lock.stem) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(export.name) == CUSTODY_TOKEN_MAX_LENGTH
    assert series_id not in edition.as_posix()
    assert attempt_id not in staging.as_posix()
    assert export_id not in export.as_posix()


def test_new_staging_is_bounded_while_legacy_staging_reopens_in_place(
    tmp_path: Path,
) -> None:
    long_attempt = "snapshot_attempt_" + ("a" * 2_000)
    staging = create_snapshot_staging(tmp_path, long_attempt)

    assert staging.root == bounded_snapshot_attempt_staging_root(
        tmp_path,
        long_attempt,
    )
    assert staging.root.parent == bounded_snapshot_staging_root(tmp_path)
    assert load_snapshot_staging(tmp_path, long_attempt).root == staging.root

    legacy_attempt = "snapshot_attempt_legacy_fixture"
    legacy = legacy_snapshot_attempt_staging_root(tmp_path, legacy_attempt)
    (legacy / "content").mkdir(parents=True)
    (legacy / "internal").mkdir()
    reopened = load_snapshot_staging(tmp_path, legacy_attempt)

    assert reopened.root == legacy
    assert snapshot_attempt_staging_root(tmp_path, legacy_attempt) == legacy
    assert not bounded_snapshot_attempt_staging_root(
        tmp_path,
        legacy_attempt,
    ).exists()


def test_new_lock_is_bounded_and_legacy_lock_remains_readable(
    tmp_path: Path,
) -> None:
    series_id = "snapshot_series_" + ("s" * 2_000)
    inspection = acquire_snapshot_series_lock(
        tmp_path,
        snapshot_series_id=series_id,
        snapshot_build_attempt_id="snapshot_attempt_bounded_lock",
        snapshot_build_plan_id="snapshot_plan_bounded_lock",
        acquired_at=fixed_clock(),
    )
    bounded = bounded_snapshot_series_lock_path(tmp_path, series_id)

    assert bounded.is_file()
    assert bounded.parent == bounded_snapshot_locks_root(tmp_path)
    assert inspection.relative_path.startswith(".locks-bounded-v1/")

    legacy_series = "snapshot_series_legacy_lock"
    acquire_snapshot_series_lock(
        tmp_path,
        snapshot_series_id=legacy_series,
        snapshot_build_attempt_id="snapshot_attempt_legacy_lock",
        snapshot_build_plan_id="snapshot_plan_legacy_lock",
        acquired_at=fixed_clock(),
    )
    new_path = bounded_snapshot_series_lock_path(tmp_path, legacy_series)
    legacy_path = legacy_snapshot_series_lock_path(tmp_path, legacy_series)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(new_path), str(legacy_path))

    inspected = inspect_snapshot_series_lock(
        tmp_path,
        snapshot_series_id=legacy_series,
    )
    assert inspected.snapshot_series_id == legacy_series
    assert inspected.relative_path == f".locks/{legacy_series}.json"


def test_dual_staging_custody_fails_closed(tmp_path: Path) -> None:
    attempt_id = "snapshot_attempt_dual"
    legacy = legacy_snapshot_attempt_staging_root(tmp_path, attempt_id)
    bounded = bounded_snapshot_attempt_staging_root(tmp_path, attempt_id)
    legacy.mkdir(parents=True)
    bounded.mkdir(parents=True)

    with pytest.raises(SnapshotCustodyError) as captured:
        snapshot_attempt_staging_root(tmp_path, attempt_id)

    assert captured.value.code == "snapshot.custody_conflict"


def _seal_distribution_fixture(tmp_path: Path):
    (
        setup,
        composition,
        inventory,
        _,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
    ) = _prepare(tmp_path)
    plan, attempt, render_config = _execution_plan(
        setup,
        composition,
        inventory,
        baseline_selection,
        later_selection,
        baseline_placement,
        later_placement,
        include_generated=True,
        permitted_first_omission="source_unavailable",
    )
    copied_entries = tuple(
        item
        for item in plan.entry_plans
        if item.materialization_kind == "copied_source"
    )
    source_root = (tmp_path / "distribution_sources").resolve()
    second_artifact = copied_entries[1].source_artifact
    assert second_artifact is not None
    assert second_artifact.source_locator is not None
    second_target = source_root.joinpath(*second_artifact.source_locator.split("/"))
    second_target.parent.mkdir(parents=True, exist_ok=True)
    second_target.write_bytes(b"distribution-ready copied source\n")
    provider = _ExecutionSourceProvider(source_root, copied_entries[0])
    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_ExecutionAuthority(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
        renderers=SnapshotRendererRegistry((_ExecutionRenderer(render_config),)),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return setup, plan, sealed


def test_sealed_edition_and_new_export_use_bounded_custody(
    tmp_path: Path,
) -> None:
    setup, plan, sealed = _seal_distribution_fixture(tmp_path)

    assert sealed.edition_path == bounded_snapshot_edition_root(
        setup.workspace,
        sealed.edition.snapshot_series_id,
        sealed.edition.edition_number,
    )
    assert snapshot_edition_root(
        setup.workspace,
        sealed.edition.snapshot_series_id,
        sealed.edition.edition_number,
    ) == sealed.edition_path

    export = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="snapshot_export_bounded_issue111",
    )
    expected = bounded_snapshot_export_path(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
    )

    assert export.export_path == expected
    assert export.export_path.parent == bounded_snapshot_exports_root(setup.workspace)
    assert export.export_artifact.relative_path.startswith(
        "snapshots/exports-bounded-v1/"
    )
    assert (
        snapshot_export_path_from_relative(
            setup.workspace,
            export.export_artifact.relative_path,
        )
        == export.export_path
    )
    verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
        verified_at=fixed_clock(),
    )


def test_historical_export_relative_path_is_verified_without_current_writer_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, plan, sealed = _seal_distribution_fixture(tmp_path)
    original_writer = distribution_module.bounded_snapshot_export_path

    def legacy_writer(
        root: str | Path,
        *,
        snapshot_series_id: str,
        edition_number: int,
        snapshot_export_artifact_id: str,
    ) -> Path:
        return legacy_snapshot_export_path(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
        )

    with monkeypatch.context() as context:
        context.setattr(
            distribution_module,
            "bounded_snapshot_export_path",
            legacy_writer,
        )
        export = create_snapshot_directory_export(
            setup.workspace,
            snapshot_series_id=sealed.edition.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            export_plan_id=plan.export_plans[0].export_plan_id,
            expected_state_revision=setup.state_revision,
            generated_at=fixed_clock(),
            artifact_id="snapshot_export_historical_issue111",
        )

    assert export.export_artifact.relative_path.startswith("snapshots/exports/")
    assert not export.export_artifact.relative_path.startswith(
        "snapshots/exports-bounded-v1/"
    )
    assert original_writer(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
    ) != export.export_path

    verified = verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=export.export_artifact.snapshot_export_artifact_id,
        verified_at=fixed_clock(),
    )
    assert (
        verified.snapshot_export_artifact_id
        == export.export_artifact.snapshot_export_artifact_id
    )
