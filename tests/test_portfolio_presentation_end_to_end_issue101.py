from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.improvement_portfolio_fixture_support import (
    TEACHER,
    ImprovementPortfolioFixture,
    build_improvement_portfolio_fixture,
    fixed_clock,
)
from scripts.validate_improvement_portfolio import (
    _assert_curation,
    _assert_materialization,
    _start_pipeline,
)
from scripts.validate_snapshot_workflows import (
    _FixtureAuthorityGate,
    _provider_registry,
    _ReflectionFixtureRenderer,
)
from vitrine.models import PortfolioPresentationArtifact, SnapshotCurrentPointerRevision
from vitrine.portfolio_presentation_services import (
    build_student_portfolio_presentation,
)
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
    verify_portfolio_presentation,
)
from vitrine.snapshot_distribution import (
    create_snapshot_directory_export,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import SnapshotRendererRegistry
from vitrine.snapshot_services import (
    execute_snapshot_build_attempt,
    seal_snapshot_build_attempt,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.storage.paths import safe_vitrine_descendant


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def test_representative_improvement_portfolio_becomes_verified_student_presentation(
    tmp_path: Path,
) -> None:
    built = build_improvement_portfolio_fixture(tmp_path)
    assert isinstance(built, ImprovementPortfolioFixture)
    setup = built
    _assert_curation(setup)

    series, _request, plan, attempt = _start_pipeline(setup)
    execution = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_FixtureAuthorityGate(),
        source_providers=_provider_registry(plan.entry_plans, setup.source_root),
        renderers=SnapshotRendererRegistry(
            (_ReflectionFixtureRenderer(reflection=setup.reflection),)
        ),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    _assert_materialization(setup, execution)
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=execution,
        expected_state_revision=setup.state_revision,
        sealed_by=TEACHER,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert sealed.edition_path is not None
    verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    export_result = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="export-artifact-issue101-e2e",
    )
    verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=(
            export_result.export_artifact.snapshot_export_artifact_id
        ),
        verified_at=fixed_clock(),
    )
    technical_before = _file_bytes(export_result.export_path)

    presentation = build_student_portfolio_presentation(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        snapshot_export_artifact_id=(
            export_result.export_artifact.snapshot_export_artifact_id
        ),
        generated_by=TEACHER,
        clock=fixed_clock,
    )
    assert presentation.disposition == "created"
    assert presentation.verified_file_paths

    html_path = safe_vitrine_descendant(
        setup.workspace, presentation.html_relative_path
    )
    pdf_path = safe_vitrine_descendant(
        setup.workspace, presentation.printable_pdf_relative_path
    )
    html = html_path.read_text(encoding="utf-8")
    assert "Synthetic Improvement Portfolio" in html
    assert setup.reflection.content is not None
    assert setup.reflection.content in html
    labels = ("Baseline", "Later Work and Feedback", "Reflection")
    positions = tuple(html.index(label) for label in labels)
    assert positions == tuple(sorted(positions))
    assert pdf_path.read_bytes().startswith(b"%PDF-")

    verified = verify_portfolio_presentation(
        setup.workspace,
        presentation_artifact_id=presentation.presentation_artifact_id,
    )
    assert verified.presentation_artifact_id == presentation.presentation_artifact_id
    assert verified.snapshot_series_id == series.snapshot_series_id
    assert verified.edition_number == sealed.edition.edition_number

    records = load_current_records(setup.workspace)
    artifacts = tuple(
        item for item in records if isinstance(item, PortfolioPresentationArtifact)
    )
    assert len(artifacts) == 1
    assert artifacts[0].presentation_artifact_id == presentation.presentation_artifact_id
    assert not any(isinstance(item, SnapshotCurrentPointerRevision) for item in records)

    state_before_retry = load_current_state(setup.workspace).state_revision
    repeated = build_student_portfolio_presentation(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        snapshot_export_artifact_id=(
            export_result.export_artifact.snapshot_export_artifact_id
        ),
        generated_by=TEACHER,
        clock=fixed_clock,
    )
    assert repeated.disposition == "existing"
    assert repeated.presentation_artifact_id == presentation.presentation_artifact_id
    assert load_current_state(setup.workspace).state_revision == state_before_retry

    shutil.rmtree(setup.source_root)
    verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=(
            export_result.export_artifact.snapshot_export_artifact_id
        ),
        verified_at=fixed_clock(),
    )
    verify_portfolio_presentation(
        setup.workspace,
        presentation_artifact_id=presentation.presentation_artifact_id,
    )
    assert _file_bytes(export_result.export_path) == technical_before

    original_html = html_path.read_bytes()
    html_path.write_bytes(original_html + b"\n")
    with pytest.raises(PortfolioPresentationVerificationError):
        verify_portfolio_presentation(
            setup.workspace,
            presentation_artifact_id=presentation.presentation_artifact_id,
        )
    html_path.write_bytes(original_html)
    verify_portfolio_presentation(
        setup.workspace,
        presentation_artifact_id=presentation.presentation_artifact_id,
    )
