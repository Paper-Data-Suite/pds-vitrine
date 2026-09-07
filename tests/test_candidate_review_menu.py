from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import candidate_review_menu
from vitrine.models import ActorAttribution
from vitrine.workflow_context import default_workflow_dependencies

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_menu",
    owning_system="local",
    role_snapshot="teacher",
)


def _inputs(values: list[str]) -> object:
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _item(
    *,
    candidate_id: str | None = "candidate_exact",
    selected_state: str = "unselected",
) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="entry_exact",
        candidate_id=candidate_id,
        current_evaluation_id="evaluation_current",
        portfolio_id="portfolio_exact",
        portfolio_label="Portfolio",
        portfolio_subject_id="subject_exact",
        subject_label="Student",
        profile_binding_id="binding_exact",
        portfolio_profile_id="profile_exact",
        profile_revision=1,
        profile_label="Improvement",
        profile_purpose="improvement",
        source_display_label="Synthetic evidence",
        evaluation_outcome="eligible" if candidate_id is not None else "ineligible",
        candidate_condition=(
            "ready_for_consideration" if candidate_id is not None else None
        ),
        stale_state="current",
        stale_reason_codes=(),
        attention_needed=False,
        attention_reason_codes=(),
        selected_state=selected_state,
    )


def _section(section_id: str, label: str) -> SimpleNamespace:
    return SimpleNamespace(
        section_id=section_id,
        label=label,
        obligation="optional",
        minimum_placements=0,
        maximum_placements=None,
        active_placement_count=0,
        arrangement_pointer_revision=4,
        arrangement_pointer_conflict=False,
        relevant_profile_requirement_ids=(),
    )


def _detail(
    *,
    item: SimpleNamespace | None = None,
    active: bool = False,
) -> SimpleNamespace:
    value = item or _item(selected_state="selected" if active else "unselected")
    selection = SimpleNamespace(
        selection_id="selection_exact",
        candidate_evaluation_id="evaluation_origin",
        lifecycle_state="activated",
        proposal_ids=("proposal_exact",),
        decision_ids=("decision_exact",),
        unresolved_condition_codes=(),
        active_placement_ids=("placement_exact",) if active else (),
        historical_placement_ids=(),
    )
    placement = SimpleNamespace(
        placement_id="placement_exact",
        selection_id="selection_exact",
        section_id="section_one",
        section_label="Section One",
        lifecycle_state="activated",
    )
    return SimpleNamespace(
        inbox_detail=SimpleNamespace(item=value),
        selectable=value.candidate_id is not None,
        current_review_evaluation_id="evaluation_current",
        curation_provenance_evaluation_id=(
            "evaluation_origin" if value.candidate_id is not None else None
        ),
        current_evaluation_differs_from_curation_provenance=(
            value.candidate_id is not None
        ),
        source=None,
        sections=(
            _section("section_one", "Section One"),
            _section("section_two", "Section Two"),
        ) if value.candidate_id is not None else (),
        proposals=(),
        selections=(selection,) if active else (),
        placements=(placement,) if active else (),
        annotations=(),
        reflections=(),
        reviews=(),
        profile_requirements=(),
    )


def test_guided_menu_fresh_select_uses_numbered_section_and_shared_orchestration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _item()
    detail = _detail(item=item)
    monkeypatch.setattr(
        candidate_review_menu,
        "list_candidate_review_entries",
        lambda *_args, **_kwargs: SimpleNamespace(items=(item,)),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda *_args, **_kwargs: detail,
    )
    planned: list[dict[str, object]] = []

    def plan(_root: Path, **kwargs: object) -> object:
        planned.append(kwargs)
        return SimpleNamespace(
            contract_version="vitrine_guided_candidate_review_v1",
            observed_state_revision=11,
            portfolio_id="portfolio_exact",
            candidate_id="candidate_exact",
            current_review_evaluation_id="evaluation_current",
            curation_provenance_evaluation_id="evaluation_origin",
            candidate_condition="ready_for_consideration",
            stale_state="current",
            stale_reason_codes=(),
            decision="select",
            selection_proposal_id=None,
            proposed_section_ids=kwargs["proposed_section_ids"],
            intended_profile_requirement_ids=(),
            condition_acknowledgement_required=False,
            confirmation_phrase="SELECT CANDIDATE",
        )

    monkeypatch.setattr(candidate_review_menu, "plan_candidate_decision", plan)
    executed: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_candidate_decision",
        lambda *_args, **_kwargs: (
            executed.append(_args[1]),
            SimpleNamespace(state_revision=12),
        )[1],
    )
    raw_input = _inputs(
        ["5", "1", "1", "2", "", "SELECT CANDIDATE", "", "B"]
    )
    output = io.StringIO()

    candidate_review_menu.run_candidate_review_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert planned[0]["entry_id"] == "entry_exact"
    assert planned[0]["decision"] == "select"
    assert planned[0]["proposed_section_ids"] == ("section_two",)
    assert len(executed) == 1
    assert "No Placement was created implicitly." in output.getvalue()


def test_guided_menu_evaluation_only_entry_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _item(candidate_id=None)
    detail = _detail(item=item)
    monkeypatch.setattr(
        candidate_review_menu,
        "list_candidate_review_entries",
        lambda *_args, **_kwargs: SimpleNamespace(items=(item,)),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda *_args, **_kwargs: detail,
    )
    planned: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "plan_candidate_decision",
        lambda *_args, **_kwargs: planned.append((_args, _kwargs)),
    )
    raw_input = _inputs(["4", "1", "", "", "B"])
    output = io.StringIO()

    candidate_review_menu.run_candidate_review_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert planned == []
    assert "reviewable but not selectable" in output.getvalue()


def test_active_selection_placement_uses_exact_numbered_section_and_pointer_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _item(selected_state="selected")
    detail = _detail(item=item, active=True)
    monkeypatch.setattr(
        candidate_review_menu,
        "list_candidate_review_entries",
        lambda *_args, **_kwargs: SimpleNamespace(items=(item,)),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda *_args, **_kwargs: detail,
    )
    planned: list[dict[str, object]] = []

    def plan(_root: Path, **kwargs: object) -> object:
        planned.append(kwargs)
        return SimpleNamespace(
            selection_id="selection_exact",
            section_id=kwargs["section_id"],
            section_label="Section Two",
            active_placement_count=0,
            maximum_placements=None,
            expected_arrangement_pointer_revision=4,
            observed_state_revision=21,
            confirmation_phrase="PLACE SELECTION",
        )

    monkeypatch.setattr(candidate_review_menu, "plan_selection_placement", plan)
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_selection_placement",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=22),
    )
    raw_input = _inputs(["3", "1", "1", "1", "2", "PLACE SELECTION", "", "B"])

    candidate_review_menu.run_candidate_review_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert planned[0]["selection_id"] == "selection_exact"
    assert planned[0]["section_id"] == "section_two"


def test_replacement_requires_explicit_same_section_disposition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail(active=True)
    successor_item = _item(candidate_id="candidate_successor")
    successor_item.entry_id = "entry_successor"
    successor_detail = _detail(item=successor_item)
    successor_detail.sections = (_section("section_one", "Section One"),)
    monkeypatch.setattr(
        candidate_review_menu,
        "_successor_entries",
        lambda *_args, **_kwargs: (successor_item,),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda _root, entry_id: (
            successor_detail if entry_id == "entry_successor" else detail
        ),
    )
    planned: list[dict[str, object]] = []

    def plan(_root: Path, **kwargs: object) -> object:
        planned.append(kwargs)
        return SimpleNamespace(
            selection_id="selection_exact",
            candidate_id="candidate_exact",
            successor_candidate_id="candidate_successor",
            successor_current_review_evaluation_id="evaluation_current",
            successor_curation_provenance_evaluation_id="evaluation_origin",
            successor_candidate_condition="ready_for_consideration",
            successor_stale_state="current",
            proposed_section_ids=kwargs["proposed_section_ids"],
            placement_dispositions=(
                SimpleNamespace(
                    placement_id="placement_exact",
                    source_section_id="section_one",
                    target_section_id="section_one",
                ),
            ),
            arrangement_pointers=(
                SimpleNamespace(section_id="section_one", pointer_revision=4),
            ),
            reason=kwargs["reason"],
            observed_state_revision=31,
            confirmation_phrase="REPLACE SELECTION",
        )

    monkeypatch.setattr(candidate_review_menu, "plan_selection_replacement", plan)
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_selection_replacement",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=32),
    )
    raw_input = _inputs(
        ["1", "1", "1", "2", "replace reason", "REPLACE SELECTION"]
    )

    candidate_review_menu._replacement_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
        clear_fn=lambda: None,
    )

    assert planned[0]["placement_dispositions"] == {
        "placement_exact": "section_one"
    }
    assert planned[0]["proposed_section_ids"] == ("section_one",)


def test_annotation_reflection_and_review_flows_use_shared_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail(active=True)
    detail.profile_requirements = (
        SimpleNamespace(
            requirement_id="reflection_exact",
            requirement_kind="reflection",
            title="Reflection",
        ),
        SimpleNamespace(
            requirement_id="approval_exact",
            requirement_kind="approval",
            title="Approval",
        ),
    )
    calls: list[str] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "plan_annotation_creation",
        lambda *_args, **kwargs: SimpleNamespace(
            action="create",
            purpose=kwargs["purpose"],
            target_scope=kwargs["target_scope"],
            target_references=kwargs["target_references"],
            observed_state_revision=41,
            confirmation_phrase="SAVE ANNOTATION",
        ),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_annotation_action",
        lambda *_args, **_kwargs: (
            calls.append("annotation"),
            SimpleNamespace(state_revision=42),
        )[1],
    )
    annotation_input = _inputs(["1", "1", "1", "1", "note", "SAVE ANNOTATION"])
    candidate_review_menu._annotation_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: annotation_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    monkeypatch.setattr(
        candidate_review_menu,
        "plan_reflection_creation",
        lambda *_args, **kwargs: SimpleNamespace(
            action="create",
            reflection_requirement_id=kwargs["reflection_requirement_id"],
            prompt_id=kwargs["prompt_id"],
            prompt_version=kwargs["prompt_version"],
            target_scope=kwargs["target_scope"],
            target_references=kwargs["target_references"],
            observed_state_revision=43,
            confirmation_phrase="SAVE REFLECTION",
        ),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_reflection_action",
        lambda *_args, **_kwargs: (
            calls.append("reflection"),
            SimpleNamespace(state_revision=44),
        )[1],
    )
    reflection_input = _inputs(
        ["1", "1", "1", "1", "prompt", "v1", "Prompt", "text", "SAVE REFLECTION"]
    )
    candidate_review_menu._reflection_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: reflection_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    detail.annotations = (
        SimpleNamespace(
            annotation_id="annotation_exact",
            annotation_revision=1,
            purpose="curator_context",
        ),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "plan_curation_review",
        lambda *_args, **kwargs: SimpleNamespace(
            decision=kwargs["decision"],
            approval_requirement_id=kwargs["approval_requirement_id"],
            reason=kwargs["reason"],
            target_references=kwargs["target_references"],
            observed_state_revision=45,
            confirmation_phrase="RECORD REVIEW",
        ),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_curation_review",
        lambda *_args, **_kwargs: (
            calls.append("review"),
            SimpleNamespace(state_revision=46),
        )[1],
    )
    review_input = _inputs(["1", "1", "1", "", "reason", "RECORD REVIEW"])
    candidate_review_menu._review_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: review_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls == ["annotation", "reflection", "review"]
