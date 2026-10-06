from __future__ import annotations

import builtins
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    DigestReference,
    PlacementPresentation,
    Portfolio,
    PortfolioPlacement,
    PortfolioPresentationArtifact,
    PortfolioProfileBinding,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileRevisionRef,
    ProfileSectionDefinition,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotEdition,
    SnapshotEditionBuildProvenance,
    SnapshotEditionRef,
    SnapshotEntry,
    SnapshotEntryOutcome,
    SnapshotEntryPlan,
    SnapshotExportArtifact,
    SnapshotExportPlan,
    SnapshotMaterializationProvenance,
    SnapshotMaterializationRecord,
    SnapshotSeal,
    SourceArtifactReference,
    WorkingPortfolioCompositionRevision,
    record_from_dict,
    record_to_dict,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.portfolio_presentation import (
    PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE,
    STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
    prepare_student_portfolio_presentation,
    presentation_artifact_custody_relative_path,
)

NOW = datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE_REF = ProfileRevisionRef(
    portfolio_profile_id="profile_showcase",
    profile_revision=2,
)
EDITION_REF = SnapshotEditionRef(snapshot_series_id="series_1", edition_number=1)
D1 = DigestReference(value="1" * 64)
D2 = DigestReference(value="2" * 64)
D3 = DigestReference(value="3" * 64)


def test_presentation_artifact_is_a_round_trippable_distinct_runtime_record() -> None:
    root = presentation_artifact_custody_relative_path("presentation_artifact_1")
    artifact = PortfolioPresentationArtifact(
        presentation_artifact_id="presentation_artifact_1",
        snapshot_edition=EDITION_REF,
        snapshot_export_artifact_id="export_1",
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        audience_context_id="audience_1",
        presentation_class="student_portfolio",
        presentation_contract_version=STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
        renderer_id="vitrine_student_portfolio_renderer",
        renderer_version="1",
        renderer_contract_version="vitrine_student_portfolio_renderer_v1",
        renderer_configuration_digest=D1,
        relative_path=root,
        presentation_manifest_relative_path=f"{root}/presentation-manifest.json",
        presentation_manifest_digest=D1,
        html_relative_path=f"{root}/index.html",
        html_digest=D2,
        printable_pdf_relative_path=f"{root}/portfolio.pdf",
        printable_pdf_digest=D3,
        package_inventory_digest=D1,
        generated_at=NOW,
        generated_by=ACTOR,
    )

    restored = record_from_dict(record_to_dict(artifact))
    assert restored == artifact
    assert artifact.record_type == "portfolio_presentation_artifact"

    with pytest.raises(VitrineModelValidationError, match="contained"):
        replace(artifact, html_relative_path="other/index.html")


def test_presentation_custody_is_bounded_opaque_and_domain_separated() -> None:
    first = presentation_artifact_custody_relative_path(
        "presentation_" + ("a" * 100)
    )
    second = presentation_artifact_custody_relative_path(
        "presentation_" + ("b" * 100)
    )

    assert first.startswith(PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE + "/vp1_")
    assert first != second
    assert len(first.split("/")[-1]) == 28
    assert "presentation_" not in first


def _source(artifact_id: str) -> SourceArtifactReference:
    return SourceArtifactReference(
        artifact_id=artifact_id,
        artifact_kind="original_student_work",
        representation_kind="document",
        media_type="application/pdf",
        source_locator=None,
        native_revision=1,
        source_digest=D1,
        byte_size=12,
        language="en",
        accessibility_relationship=None,
    )


def _source_entry(
    *,
    entry_plan_id: str,
    position: int,
    ordinal: int,
    placement_id: str,
    selection_id: str,
    candidate_id: str,
    reference_only: bool = False,
) -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id=entry_plan_id,
        plan_position=position,
        section_id="selected_work",
        ordinal=ordinal,
        semantic_role="selected_work",
        materialization_kind="reference_only" if reference_only else "copied_source",
        content_class="assessment_summary" if reference_only else "student_work",
        selection_id=selection_id,
        placement_id=placement_id,
        candidate_id=candidate_id,
        candidate_evaluation_id=f"evaluation_{position}",
        source_publication_id=f"publication_{position}",
        producer_module_id="scoreform" if reference_only else "quillan",
        projection_kind="artifact",
        projection_contract_version="projection_v1",
        source_artifact=_source(f"artifact_{position}"),
        producer_source_digest_claim=D1,
        target_relative_path=None if reference_only else "section-01/01-entry-a.pdf",
        media_type=None if reference_only else "application/pdf",
    )


def _records() -> tuple[object, ...]:
    section = ProfileSectionDefinition(
        section_id="selected_work",
        label="Selected Work",
        purpose="Work the student chose to represent growth and accomplishment.",
        order=1,
        obligation="required",
        minimum_placements=1,
        maximum_placements=5,
        allowed_candidate_kinds=("artifact",),
        required_relationship_kinds=(),
        reflection_requirement="optional",
    )
    audience_rule = ProfileAudienceRule(
        audience_rule_id="student_view",
        audience_class="student",
        purpose="Student portfolio review",
        allowed_content_classes=("student_work", "assessment_summary", "portfolio_index"),
        prohibited_content_classes=(),
        required_review_classes=(),
        presentation_class="student_portfolio",
        retention_policy_reference=None,
    )
    profile = PortfolioProfileRevision(
        portfolio_profile_id="profile_showcase",
        profile_revision=2,
        profile_family_id=None,
        predecessor_revision=1,
        label="Showcase Portfolio",
        purpose_kind="showcase",
        applicability=ProfileApplicability(),
        sections=(section,),
        audience_rules=(audience_rule,),
        created_at=NOW,
        created_by=ACTOR,
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        created_at=NOW,
        created_by=ACTOR,
        title_snapshot="Senior Showcase",
    )
    subject = PortfolioSubject(
        portfolio_subject_id="subject_1",
        created_at=NOW,
        created_by=ACTOR,
        display_name_snapshot="Jordan Lee",
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="binding_1",
        portfolio_id="portfolio_1",
        profile_revision=PROFILE_REF,
        bound_at=NOW,
        bound_by=ACTOR,
    )
    audience = AudienceContext(
        audience_context_id="audience_1",
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        audience_rule_id="student_view",
        audience_class="student",
        purpose="Student portfolio review",
        subject_scope="portfolio_subject",
        allowed_content_classes=("student_work", "assessment_summary", "portfolio_index"),
        prohibited_content_classes=(),
        required_review_classes=(),
        presentation_class="student_portfolio",
        retention_policy_reference=None,
        created_at=NOW,
        created_by=ACTOR,
    )
    placements = (
        PortfolioPlacement(
            placement_id="placement_1",
            portfolio_id="portfolio_1",
            profile_binding_id="binding_1",
            selection_id="selection_1",
            section_id="selected_work",
            presentation=PlacementPresentation(
                display_title="Revised Argument",
                display_caption="A piece that shows how my evidence and reasoning developed.",
            ),
            placed_at=NOW,
            placed_by=ACTOR,
        ),
        PortfolioPlacement(
            placement_id="placement_2",
            portfolio_id="portfolio_1",
            profile_binding_id="binding_1",
            selection_id="selection_2",
            section_id="selected_work",
            presentation=PlacementPresentation(display_title="Benchmark Snapshot"),
            placed_at=NOW,
            placed_by=ACTOR,
        ),
    )
    composition = WorkingPortfolioCompositionRevision(
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        composition_revision=3,
        selection_ids=("selection_1", "selection_2"),
        placement_ids=("placement_1", "placement_2"),
        arrangement_ids=("arrangement_1",),
        created_at=NOW,
        created_by=ACTOR,
    )
    entry_1 = _source_entry(
        entry_plan_id="entry_plan_1",
        position=1,
        ordinal=1,
        placement_id="placement_1",
        selection_id="selection_1",
        candidate_id="candidate_1",
    )
    entry_2 = _source_entry(
        entry_plan_id="entry_plan_2",
        position=2,
        ordinal=2,
        placement_id="placement_2",
        selection_id="selection_2",
        candidate_id="candidate_2",
        reference_only=True,
    )
    export_plan = SnapshotExportPlan(
        export_plan_id="export_plan_1",
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_plan_ids=("entry_plan_1",),
        excluded_entry_plan_ids=("entry_plan_2",),
        configuration_digest=D2,
    )
    plan = SnapshotBuildPlan(
        snapshot_build_plan_id="plan_1",
        snapshot_build_request_id="request_1",
        snapshot_series_id="series_1",
        plan_revision=1,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        composition_revision=3,
        audience_context_id="audience_1",
        entry_plans=(entry_1, entry_2),
        export_plans=(export_plan,),
        required_review_references=(),
        acknowledged_obligation_codes=(),
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        builder_contract_id="snapshot_builder",
        builder_contract_version="1",
        planned_at=NOW,
        planned_by=ACTOR,
        plan_fingerprint="a" * 64,
    )
    result = SnapshotBuildAttemptResult(
        snapshot_build_attempt_result_id="attempt_result_1",
        snapshot_build_attempt_id="attempt_1",
        completed_at=NOW,
        terminal_outcome="sealed",
        entry_outcomes=(
            SnapshotEntryOutcome(
                entry_plan_id="entry_plan_1",
                disposition="included",
                materialization_id="materialization_1",
            ),
            SnapshotEntryOutcome(
                entry_plan_id="entry_plan_2",
                disposition="reference_only",
            ),
        ),
        sealed_snapshot_edition=EDITION_REF,
    )
    provenance = SnapshotEditionBuildProvenance(
        snapshot_edition_build_provenance_id="edition_provenance_1",
        snapshot_edition=EDITION_REF,
        snapshot_build_request_id="request_1",
        snapshot_build_plan_id="plan_1",
        snapshot_build_attempt_id="attempt_1",
        snapshot_build_attempt_result_id="attempt_result_1",
        portfolio_id="portfolio_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        composition_revision=3,
        audience_context_id="audience_1",
        builder_contract_id="snapshot_builder",
        builder_contract_version="1",
        path_policy_id="snapshot_path_v1",
        digest_policy_id="snapshot_digest_v1",
        recorded_at=NOW,
        recorded_by=ACTOR,
    )
    edition = SnapshotEdition(
        snapshot_series_id="series_1",
        edition_number=1,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE_REF,
        composition_revision=3,
        audience_context_id="audience_1",
        manifest_id="manifest_1",
        seal_id="seal_1",
        created_at=NOW,
        created_by=ACTOR,
    )
    seal = SnapshotSeal(
        seal_id="seal_1",
        snapshot_edition=EDITION_REF,
        manifest_id="manifest_1",
        manifest_digest=D1,
        logical_inventory_digest=D2,
        sealed_at=NOW,
        sealed_by=ACTOR,
    )
    materialization_1 = SnapshotMaterializationRecord(
        materialization_id="materialization_1",
        snapshot_edition=EDITION_REF,
        materialization_kind="copied_source",
        candidate_id="candidate_1",
        selection_id="selection_1",
        placement_id="placement_1",
        source_artifact=entry_1.source_artifact,
        source_digest=D1,
        output_digest=D2,
        byte_size=12,
        materialized_at=NOW,
        materialized_by=ACTOR,
    )
    materialization_2 = SnapshotMaterializationRecord(
        materialization_id="materialization_2",
        snapshot_edition=EDITION_REF,
        materialization_kind="reference_only",
        candidate_id="candidate_2",
        selection_id="selection_2",
        placement_id="placement_2",
        source_artifact=entry_2.source_artifact,
        source_digest=None,
        output_digest=None,
        byte_size=None,
        materialized_at=NOW,
        materialized_by=ACTOR,
    )
    materialization_provenance = (
        SnapshotMaterializationProvenance(
            snapshot_materialization_provenance_id="mat_provenance_1",
            materialization_id="materialization_1",
            snapshot_edition=EDITION_REF,
            entry_plan_id="entry_plan_1",
            source_provider_id="quillan_provider",
            source_provider_version="1",
            renderer_id=None,
            renderer_version=None,
            renderer_contract_version=None,
            input_references=(),
            producer_source_digest_claim=D1,
            source_stability_result="verified",
            configuration_digest=None,
            template_digest=None,
            verification_result="verified",
            recorded_at=NOW,
            recorded_by=ACTOR,
        ),
        SnapshotMaterializationProvenance(
            snapshot_materialization_provenance_id="mat_provenance_2",
            materialization_id="materialization_2",
            snapshot_edition=EDITION_REF,
            entry_plan_id="entry_plan_2",
            source_provider_id=None,
            source_provider_version=None,
            renderer_id=None,
            renderer_version=None,
            renderer_contract_version=None,
            input_references=(),
            producer_source_digest_claim=D1,
            source_stability_result="not_applicable",
            configuration_digest=None,
            template_digest=None,
            verification_result="verified",
            recorded_at=NOW,
            recorded_by=ACTOR,
        ),
    )
    snapshot_entry = SnapshotEntry(
        snapshot_entry_id="snapshot_entry_1",
        snapshot_edition=EDITION_REF,
        materialization_id="materialization_1",
        section_id="selected_work",
        ordinal=1,
        relative_path="section-01/01-entry-a.pdf",
        media_type="application/pdf",
        content_class="student_work",
        display_title=None,
        source_placement_id="placement_1",
    )
    export_artifact = SnapshotExportArtifact(
        snapshot_export_artifact_id="export_1",
        snapshot_edition=EDITION_REF,
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_ids=("snapshot_entry_1",),
        excluded_entry_ids=(),
        packager_id="vitrine_directory_packager",
        packager_version="1",
        configuration_digest=D2,
        generated_at=NOW,
        relative_path="snapshots/exports-bounded-v1/vp1_aaaaaaaaaaaaaaaaaaaaaaaa",
        directory_inventory_digest=D3,
        validation_result="verified",
    )
    return (
        portfolio,
        subject,
        binding,
        profile,
        audience,
        *placements,
        composition,
        plan,
        result,
        provenance,
        edition,
        seal,
        materialization_1,
        materialization_2,
        *materialization_provenance,
        snapshot_entry,
        export_artifact,
    )


def test_preparation_uses_exact_sealed_history_and_never_imports_producers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation as module

    records = _records()
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_export_artifact_id="export_1",
            snapshot_series_id="series_1",
            edition_number=1,
        ),
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=44), records),
    )

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".")[0] in {"scoreform", "quillan", "concord", "portia", "meridian"}:
            raise AssertionError(f"presentation preparation imported producer {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    prepared = prepare_student_portfolio_presentation(
        Path("."),
        snapshot_series_id="series_1",
        edition_number=1,
        snapshot_export_artifact_id="export_1",
    )

    assert prepared.student_display_name == "Jordan Lee"
    assert prepared.portfolio_title == "Senior Showcase"
    assert prepared.audience_presentation_class == "student_portfolio"
    assert prepared.presentation_class == "student_portfolio"
    assert prepared.snapshot_manifest_sha256 == D1.value
    assert prepared.snapshot_logical_inventory_sha256 == D2.value
    assert prepared.file_item_count == 1
    assert prepared.reference_only_count == 1
    assert prepared.omitted_count == 0
    assert prepared.sections[0].label == "Selected Work"
    assert prepared.sections[0].presentation_directory_name.startswith("01-selected-work-")

    file_item, reference_item = prepared.sections[0].items
    assert file_item.display_title == "Revised Argument"
    assert file_item.presentation_filename is not None
    assert file_item.presentation_filename.startswith("revised-argument-")
    assert file_item.presentation_filename.endswith(".pdf")
    assert "Jordan" not in file_item.presentation_filename
    assert reference_item.display_title == "Benchmark Snapshot"
    assert reference_item.presentation_filename is None
    assert reference_item.export_file_available is False
    assert "portable file" in (reference_item.presentation_note or "")
    assert len(prepared.preparation_fingerprint) == 64


def test_preparation_rejects_unknown_media_instead_of_inventing_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation as module

    records = tuple(
        replace(item, media_type="application/x-unknown-student-artifact")
        if isinstance(item, SnapshotEntry)
        else item
        for item in _records()
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_export_artifact_id="export_1",
            snapshot_series_id="series_1",
            edition_number=1,
        ),
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=44), records),
    )

    with pytest.raises(module.PortfolioPresentationPreparationError) as caught:
        module.prepare_student_portfolio_presentation(
            Path("."),
            snapshot_series_id="series_1",
            edition_number=1,
            snapshot_export_artifact_id="export_1",
        )

    assert caught.value.code == "portfolio_presentation.unsupported_media"
    assert caught.value.stage == "media"

def test_preparation_rejects_unsupported_presentation_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation as module

    records = tuple(
        replace(item, presentation_class="showcase")
        if isinstance(item, AudienceContext)
        else replace(
            item,
            audience_rules=(
                replace(item.audience_rules[0], presentation_class="showcase"),
            ),
        )
        if isinstance(item, PortfolioProfileRevision)
        else item
        for item in _records()
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_export_artifact_id="export_1",
            snapshot_series_id="series_1",
            edition_number=1,
        ),
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=44), records),
    )

    with pytest.raises(module.PortfolioPresentationPreparationError) as caught:
        module.prepare_student_portfolio_presentation(
            Path("."),
            snapshot_series_id="series_1",
            edition_number=1,
            snapshot_export_artifact_id="export_1",
        )

    assert caught.value.code == (
        "portfolio_presentation.unsupported_presentation_class"
    )
    assert caught.value.stage == "audience"


def test_preparation_requires_portfolio_index_audience_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation as module

    records = tuple(
        replace(
            item,
            allowed_content_classes=("student_work", "assessment_summary"),
        )
        if isinstance(item, AudienceContext)
        else replace(
            item,
            audience_rules=(
                replace(
                    item.audience_rules[0],
                    allowed_content_classes=(
                        "student_work",
                        "assessment_summary",
                    ),
                ),
            ),
        )
        if isinstance(item, PortfolioProfileRevision)
        else item
        for item in _records()
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_export_artifact_id="export_1",
            snapshot_series_id="series_1",
            edition_number=1,
        ),
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=44), records),
    )

    with pytest.raises(module.PortfolioPresentationPreparationError) as caught:
        module.prepare_student_portfolio_presentation(
            Path("."),
            snapshot_series_id="series_1",
            edition_number=1,
            snapshot_export_artifact_id="export_1",
        )

    assert caught.value.code == "portfolio_presentation.portfolio_index_prohibited"
    assert caught.value.stage == "audience"
