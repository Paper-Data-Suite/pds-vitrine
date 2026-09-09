from __future__ import annotations

from types import SimpleNamespace

from vitrine.current_portfolio_surface import current_portfolio_preparation_lines


def _preparation() -> SimpleNamespace:
    artifact = SimpleNamespace(
        artifact_id="artifact_1",
        artifact_kind="original_student_work",
        representation_kind="student_work",
    )
    item = SimpleNamespace(
        plan_position=1,
        section_label="Growth",
        position_in_section=1,
        placement_id="placement_1",
        selection_id="selection_1",
        candidate_id="candidate_1",
        candidate_evaluation_id="evaluation_1",
        source_publication_id="publication_1",
        producer_module_id="quillan",
        projection_kind="student_work",
        projection_contract_version="quillan_projection_v1",
        source_artifact=artifact,
        source_current_use_state="historical",
        content_class="student_work",
        materialization_kind="copied_source",
        provider_disposition="exact_provider",
        provider_id="quillan_provider",
        provider_version="1",
        target_relative_path="growth/item_1.txt",
        media_type="text/plain",
        export_file=True,
        permitted_omission_reason=None,
        explanation="Exact authorized producer Artifact bytes.",
    )
    reflection = SimpleNamespace(
        plan_position=2,
        reflection_id="reflection_1",
        reflection_revision=2,
        section_label="Growth",
        section_id="growth",
        reflection_requirement_id="reflection_requirement_1",
        prompt_id="prompt_1",
        prompt_version="1",
        content_mode="inline_text",
        content_format="plain_text",
        language="en",
        renderer_id="vitrine_portfolio_reflection",
        renderer_version="1",
        renderer_contract_version="vitrine_portfolio_reflection_renderer_v1",
        target_relative_path="growth/reflection_1.txt",
        media_type="text/plain",
        export_file=True,
        supported=True,
        explanation="Exact frozen Reflection revision.",
    )
    return SimpleNamespace(
        contract_version="vitrine_build_export_current_portfolio_v1",
        preparation_fingerprint="a" * 64,
        observed_state_revision=17,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision_id="profile_1",
        profile_revision_number=3,
        current_composition_revision=4,
        current_composition_pointer_revision=2,
        working_composition_disposition="reuse_exact_current",
        selected_audience_rule=SimpleNamespace(
            audience_rule_id="audience_rule_1",
            audience_class="family",
            purpose="showcase",
            allowed_content_classes=("student_work", "reflection"),
            prohibited_content_classes=("feedback",),
            required_review_classes=("teacher_review",),
            presentation_class="portfolio",
            retention_policy_reference="policy_1",
        ),
        audience_context=SimpleNamespace(
            disposition="reuse",
            matching_audience_context_ids=("audience_context_1",),
            selected_audience_context_id="audience_context_1",
        ),
        snapshot_series=SimpleNamespace(
            disposition="reuse",
            matching_snapshot_series_ids=("snapshot_series_1",),
            selected_snapshot_series_id="snapshot_series_1",
            resolution_deferred_for_audience_context=False,
        ),
        required_reviews=(
            SimpleNamespace(
                review_class="teacher_review",
                satisfied=True,
                profile_requirement_ids=("requirement_1",),
                satisfying_review_decision_ids=("review_1",),
            ),
        ),
        missing_required_review_classes=(),
        unresolved_obligation_codes=("follow_up_needed",),
        acknowledged_obligation_codes=("follow_up_needed",),
        planned_items=(item,),
        generated_reflections=(reflection,),
        directory_export=SimpleNamespace(
            export_plan_id="export_plan_1",
            export_format="directory_package",
            export_contract_version="snapshot_directory_export_v1",
            included_entry_plan_ids=("entry_1", "entry_2"),
            excluded_entry_plan_ids=("entry_3",),
            configuration_sha256="b" * 64,
        ),
        warnings=("historical_source",),
        blocking_reasons=(),
    )


def test_shared_preparation_view_exposes_exact_policy_and_distinctions() -> None:
    text = "\n".join(current_portfolio_preparation_lines(_preparation()))

    assert "vitrine_build_export_current_portfolio_v1" in text
    assert "Audience Rule" in text
    assert "Audience Context" in text
    assert "Snapshot Series" in text
    assert "Required Reviews" in text
    assert "follow_up_needed" in text
    assert "historical" in text
    assert "copied_source" in text
    assert "quillan_provider / 1" in text
    assert "Reflection reflection_1:2" in text
    assert "Directory Export Plan" in text
    assert "Excluded Entry Plans: entry_3" in text
    assert "not recipient or disclosure authority" in text
    assert "Export creation is not delivery or sending." in text
