from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.improvement_portfolio_fixture_support import (
    PORTFOLIO_ID,
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
from vitrine.attention import VitrineAttentionQuery, evaluate_vitrine_attention_v2
from vitrine.completed_portfolio import project_completed_portfolio_history
from vitrine.models import PortfolioPresentationArtifact, SnapshotCurrentPointerRevision
from vitrine.portfolio_completion import prepare_portfolio_completion
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

    # Issue #104 Slice 4: completion and Attention from the same journey.
    # The sealed Edition and verified Export are technically complete before
    # presentation generation, even with no Current Pointer.
    history_before_presentation = project_completed_portfolio_history(
        load_current_records(setup.workspace), portfolio_id=PORTFOLIO_ID
    )
    assert history_before_presentation.completed_edition_count == 1
    assert len(history_before_presentation.series) == 1
    completed_series = history_before_presentation.series[0]
    assert completed_series.snapshot_series_id == series.snapshot_series_id
    assert completed_series.current_edition_number is None
    assert len(completed_series.editions) == 1
    completed_edition = completed_series.editions[0]
    assert completed_edition.edition_number == sealed.edition.edition_number
    assert completed_edition.composition_revision == setup.composition.composition_revision
    assert completed_edition.is_current is False
    assert len(completed_edition.exports) == 1
    assert (
        completed_edition.exports[0].snapshot_export_artifact_id
        == export_result.export_artifact.snapshot_export_artifact_id
    )
    assert completed_edition.presentations == ()

    completion_before_presentation = prepare_portfolio_completion(
        setup.workspace, PORTFOLIO_ID
    )
    assert completion_before_presentation.state == "complete"
    assert completion_before_presentation.is_complete
    assert completion_before_presentation.student_presentation_missing
    assert completion_before_presentation.required_reason_codes == ()
    assert len(completion_before_presentation.exact_current_editions) == 1
    assert not completion_before_presentation.exact_current_editions[0].is_current

    attention_before_presentation = evaluate_vitrine_attention_v2(
        setup.workspace, VitrineAttentionQuery(portfolio_id=PORTFOLIO_ID)
    )
    assert attention_before_presentation.evaluation == "evaluated"
    before_by_code = {item.code: item for item in attention_before_presentation.summaries}
    assert before_by_code["vitrine_portfolio_complete"].requirement_level == "status"
    assert (
        before_by_code["vitrine_student_presentation_missing"].requirement_level
        == "opportunity"
    )
    assert not any(
        item.requirement_level == "required"
        for item in attention_before_presentation.summaries
    )

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

    # The Presentation is discoverable from the same canonical history and
    # resolves an opportunity; its creation must not invent a Current Pointer.
    history_after_presentation = project_completed_portfolio_history(
        load_current_records(setup.workspace), portfolio_id=PORTFOLIO_ID
    )
    assert len(history_after_presentation.series) == 1
    completed_series_after = history_after_presentation.series[0]
    assert completed_series_after.current_edition_number is None
    assert len(completed_series_after.editions) == 1
    completed_edition_after = completed_series_after.editions[0]
    assert completed_edition_after.is_current is False
    assert len(completed_edition_after.exports) == 1
    assert len(completed_edition_after.presentations) == 1
    assert (
        completed_edition_after.presentations[0].presentation_artifact_id
        == presentation.presentation_artifact_id
    )

    completion_after_presentation = prepare_portfolio_completion(
        setup.workspace, PORTFOLIO_ID
    )
    assert completion_after_presentation.state == "complete"
    assert not completion_after_presentation.student_presentation_missing
    assert (
        completion_after_presentation.exact_current_editions[0].student_presentation_available
    )

    attention_after_presentation = evaluate_vitrine_attention_v2(
        setup.workspace, VitrineAttentionQuery(portfolio_id=PORTFOLIO_ID)
    )
    assert attention_after_presentation.evaluation == "evaluated"
    after_by_code = {item.code: item for item in attention_after_presentation.summaries}
    assert after_by_code["vitrine_portfolio_complete"].requirement_level == "status"
    assert "vitrine_student_presentation_missing" not in after_by_code
    assert not any(
        item.requirement_level == "required"
        for item in attention_after_presentation.summaries
    )

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
