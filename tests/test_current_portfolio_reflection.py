from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.current_portfolio_reflection import (
    CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
    CurrentPortfolioReflectionRenderer,
    current_portfolio_reflection_bytes,
    current_portfolio_reflection_configuration_digest,
    current_portfolio_reflection_output_digest,
)
from vitrine.models import (
    ActorAttribution,
    CurationRevisionRef,
    CurationTargetRef,
    PortfolioReflection,
    ProfileRevisionRef,
    SnapshotEntryPlan,
    SnapshotInputReference,
)
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotRenderRequest,
)
from vitrine.working_composition import (
    WorkingCompositionAudienceSummary,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
    WorkingCompositionRequirementSummary,
    WorkingCompositionSectionSummary,
)

NOW = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="core_student",
    actor_id="opaque_subject_actor",
    owning_system="vitrine",
    role_snapshot="student",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_1",
    profile_revision=1,
)
RULE = WorkingCompositionAudienceSummary(
    audience_rule_id="rule_1",
    audience_class="external_reviewer",
    purpose="Portfolio review",
    allowed_content_classes=("reflection",),
    prohibited_content_classes=(),
    required_review_classes=(),
    presentation_class="showcase",
    retention_policy_reference=None,
)


def _reflection(
    revision: int = 1,
    *,
    content: str = "Exact frozen reflection.\r\nSecond line.",
    content_mode: str = "inline_text",
    content_format: str = "plain_text",
    requirement_id: str = "reflection_requirement",
) -> PortfolioReflection:
    return PortfolioReflection(
        reflection_id="reflection_1",
        reflection_revision=revision,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        reflection_requirement_id=requirement_id,
        prompt_id="reflection_prompt",
        prompt_version=str(revision),
        prompt_snapshot="What changed in this exact work?",
        author=ACTOR,
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id="portfolio_1",
            ),
        ),
        content_mode=content_mode,
        language="en",
        content_format=content_format,
        content=content,
        created_at=NOW,
        predecessor_reflection_revision=None if revision == 1 else revision - 1,
    )


def _entry(reflection: PortfolioReflection) -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id="entry_reflection",
        plan_position=1,
        section_id="reflection",
        ordinal=1,
        semantic_role="reflection",
        materialization_kind="generated_vitrine",
        content_class="reflection",
        target_relative_path="section-01/01-reflection.txt",
        media_type=CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
        renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
        renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
        renderer_contract_version=(
            CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        ),
        renderer_configuration_digest=(
            current_portfolio_reflection_configuration_digest()
        ),
        input_references=(
            SnapshotInputReference(
                record_type="portfolio_reflection",
                record_id=reflection.reflection_id,
                record_revision=reflection.reflection_revision,
            ),
        ),
    )


def _section(section_id: str = "reflection", order: int = 1):
    return WorkingCompositionSectionSummary(
        section_id=section_id,
        label="Reflection",
        purpose="Exact reflection",
        order=order,
        obligation="required",
        minimum_placements=0,
        maximum_placements=0,
        active_placement_count=0,
        current_arrangement_id=None,
        current_arrangement_revision=None,
        current_arrangement_pointer_revision=None,
        placements=(),
    )


def _requirement(
    requirement_id: str = "reflection_requirement",
    *,
    scope_kind: str = "section",
    scope_reference: str | None = "reflection",
) -> WorkingCompositionRequirementSummary:
    return WorkingCompositionRequirementSummary(
        requirement_id=requirement_id,
        title="Reflection",
        statement="Provide exact reflection.",
        requirement_kind="reflection",
        obligation="required",
        scope_kind=scope_kind,
        scope_reference=scope_reference,
        satisfaction_class="reflection_presence",
        status="satisfied_current_curation",
        related_to_frozen_inventory=True,
        associated_unresolved_obligation_codes=(),
    )


def _working(
    reflections: tuple[PortfolioReflection, ...],
    *,
    requirements: tuple[WorkingCompositionRequirementSummary, ...] | None = None,
    included_curation_revisions: tuple[CurationRevisionRef, ...] | None = None,
) -> WorkingCompositionPreparation:
    frozen = (
        tuple(
            CurationRevisionRef(
                record_kind="reflection",
                record_id=item.reflection_id,
                revision=item.reflection_revision,
            )
            for item in reflections
        )
        if included_curation_revisions is None
        else included_curation_revisions
    )
    requirement_values = (
        (_requirement(),) if requirements is None else requirements
    )
    return WorkingCompositionPreparation(
        contract_version="vitrine_guided_working_composition_v1",
        observed_state_revision=7,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision_id="profile_1",
        profile_revision_number=1,
        observed_composition_pointer_revision=1,
        current_composition_revision=1,
        predicted_composition_revision=1,
        predecessor_composition_revision=None,
        predicted_composition_pointer_revision=1,
        disposition="reuse_exact_current",
        payload=WorkingCompositionPayloadPreview(
            selection_ids=(),
            placement_ids=(),
            arrangement_ids=(),
            included_rationale_ids=(),
            included_curation_revisions=frozen,
            applicable_review_decision_ids=(),
            related_profile_requirement_ids=tuple(
                item.requirement_id for item in requirement_values
            ),
            unresolved_obligation_codes=(),
            coherence_state="coherent",
        ),
        sections=(_section(),),
        selections=(),
        unplaced_selection_ids=(),
        requirements=requirement_values,
        source_observations=(),
        reviews=(),
        audience_rules=(RULE,),
        requested_composition_note=None,
        composition_note_will_persist=False,
        preparation_fingerprint="a" * 64,
    )


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    working: WorkingCompositionPreparation,
    records: tuple[object, ...],
) -> None:
    import vitrine.current_portfolio_build as module

    monkeypatch.setattr(
        module,
        "prepare_working_composition",
        lambda *_args, **_kwargs: working,
    )
    current = type(
        "Current",
        (),
        {"state_revision": working.observed_state_revision},
    )()
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (current, records),
    )


def test_renderer_preserves_exact_frozen_content_bytes() -> None:
    reflection = _reflection()
    payload = current_portfolio_reflection_bytes(reflection)

    assert payload == b"Exact frozen reflection.\r\nSecond line."
    assert current_portfolio_reflection_output_digest(reflection).value == (
        hashlib.sha256(payload).hexdigest()
    )


def test_renderer_follows_exact_revision_not_later_successor() -> None:
    first = _reflection(1, content="Revision one")
    second = _reflection(2, content="Revision two")
    renderer = CurrentPortfolioReflectionRenderer((first, second))

    result = renderer.render(
        SnapshotRenderRequest(
            snapshot_build_plan_id="plan_1",
            snapshot_build_attempt_id="attempt_1",
            entry_plan=_entry(first),
        )
    )

    assert result.content == b"Revision one"
    assert result.language == "en"
    assert result.configuration_digest == (
        current_portfolio_reflection_configuration_digest()
    )
    assert result.template_digest is None


def test_external_reference_reflection_is_not_dereferenced() -> None:
    reflection = _reflection(
        content="https://example.invalid/private-reflection",
        content_mode="external_reference",
    )
    renderer = CurrentPortfolioReflectionRenderer((reflection,))

    with pytest.raises(SnapshotMaterializationError) as captured:
        renderer.render(
            SnapshotRenderRequest(
                snapshot_build_plan_id="plan_1",
                snapshot_build_attempt_id="attempt_1",
                entry_plan=_entry(reflection),
            )
        )

    assert captured.value.code == "snapshot.render_failed"


def test_preparation_adds_exact_generated_reflection_and_export_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reflection = _reflection()
    working = _working((reflection,))
    _patch(monkeypatch, working, (reflection,))

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    assert prepared.planned_items == ()
    assert len(prepared.generated_reflections) == 1
    generated = prepared.generated_reflections[0]
    assert generated.materialization_kind == "generated_vitrine"
    assert generated.content_class == "reflection"
    assert generated.reflection_id == reflection.reflection_id
    assert generated.reflection_revision == 1
    assert generated.supported is True
    assert generated.export_file is True
    assert generated.output_byte_size == len(reflection.content.encode("utf-8"))
    assert generated.output_sha256 == (
        current_portfolio_reflection_output_digest(reflection).value
    )
    assert generated.entry_plan is not None
    assert generated.entry_plan.input_references[0].record_revision == 1
    assert prepared.snapshot_entry_plans == (generated.entry_plan,)
    assert prepared.directory_export.included_entry_plan_ids == (
        generated.entry_plan_id,
    )
    assert prepared.blocking_reasons == ()


def test_unsupported_reflection_blocks_without_reinterpretation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reflection = _reflection(content_mode="structured_response")
    working = _working((reflection,))
    _patch(monkeypatch, working, (reflection,))

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    generated = prepared.generated_reflections[0]
    assert generated.supported is False
    assert generated.entry_plan is None
    assert generated.export_file is False
    assert "unsupported_reflection_rendering" in prepared.blocking_reasons


def test_audience_prohibited_reflection_blocks_instead_of_fabricating_omission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reflection = _reflection()
    working = _working((reflection,))
    prohibited = replace(
        RULE,
        allowed_content_classes=(),
        prohibited_content_classes=("reflection",),
    )
    working = replace(working, audience_rules=(prohibited,))
    _patch(monkeypatch, working, (reflection,))

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    generated = prepared.generated_reflections[0]
    assert generated.entry_plan is None
    assert generated.export_file is False
    assert "reflection_audience_prohibited" in prepared.blocking_reasons


def test_frozen_reflection_change_changes_plan_and_preparation_fingerprints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _reflection(content="First exact content")
    working = _working((first,))
    _patch(monkeypatch, working, (first,))
    prepared_first = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    changed = _reflection(content="Second exact content")
    _patch(monkeypatch, working, (changed,))
    prepared_second = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    assert prepared_first.generated_reflections[0].entry_plan_id != (
        prepared_second.generated_reflections[0].entry_plan_id
    )
    assert prepared_first.preparation_fingerprint != (
        prepared_second.preparation_fingerprint
    )


def test_non_section_scoped_reflection_requirement_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reflection = _reflection()
    working = _working(
        (reflection,),
        requirements=(
            _requirement(scope_kind="portfolio", scope_reference=None),
        ),
    )
    _patch(monkeypatch, working, (reflection,))

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    assert len(prepared.generated_reflections) == 1
    generated = prepared.generated_reflections[0]
    assert generated.section_id is None
    assert generated.position_in_section is None
    assert generated.entry_plan is None
    assert generated.export_file is False
    assert generated.supported is False
    assert "unsupported_reflection_placement" in prepared.blocking_reasons
    assert "will not invent" in generated.explanation


def test_annotation_inventory_reference_does_not_become_generated_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working = _working(
        (),
        included_curation_revisions=(
            CurationRevisionRef(
                record_kind="annotation",
                record_id="annotation_1",
                revision=1,
            ),
        ),
    )
    _patch(monkeypatch, working, ())

    prepared = prepare_current_portfolio_build(
        ".",
        "portfolio_1",
        audience_rule_id="rule_1",
    )

    assert prepared.generated_reflections == ()
    assert prepared.snapshot_entry_plans == ()
