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
        eligible_section_ids=(
            ("section_one", "section_two")
            if candidate_id is not None
            else ()
        ),
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
    profile_sections = (
        SimpleNamespace(section_id="section_one", label="Section One"),
        SimpleNamespace(section_id="section_two", label="Section Two"),
    )
    return SimpleNamespace(
        inbox_detail=SimpleNamespace(
            item=value,
            profile_revision=SimpleNamespace(sections=profile_sections),
        ),
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


def test_guided_review_detail_is_teacher_first_with_explicit_technical_view() -> None:
    detail = _detail()
    output = io.StringIO()

    candidate_review_menu._render_detail(output, detail)

    rendered = output.getvalue()
    assert "Candidate Review" in rendered
    assert "Synthetic evidence" in rendered
    assert "Student: Student" in rendered
    assert "Portfolio: Portfolio" in rendered
    assert "Portfolio fit" in rendered
    assert "Matches: Section One, Section Two" in rendered
    assert "Matched Profile section context" in rendered
    assert "guarantee current Placement validity." in rendered
    assert "Section One — Optional; 0 placed; no maximum" in rendered
    assert "Entry ID: entry_exact" not in rendered
    assert "Candidate ID: candidate_exact" not in rendered
    assert "Profile Binding: binding_exact" not in rendered
    assert "evaluation_current" not in rendered
    assert "arrangement pointer" not in rendered

    technical = io.StringIO()
    candidate_review_menu._render_technical_detail(technical, detail)
    exact = technical.getvalue()
    assert "Candidate Review Technical Details / Provenance" in exact
    assert "Entry ID: entry_exact" in exact
    assert "Candidate ID: candidate_exact" in exact
    assert "Profile Binding: binding_exact" in exact
    assert "Current review Evaluation: evaluation_current" in exact
    assert "arrangement pointer 4" in exact


def test_guided_review_list_humanizes_state_tokens() -> None:
    rendered = candidate_review_menu._item_line(_item())

    assert "Synthetic evidence" in rendered
    assert "Ready For Consideration" in rendered
    assert "Not selected" in rendered
    assert "ready_for_consideration" not in rendered


def test_ready_to_consider_category_requires_unselected_candidate() -> None:
    query = candidate_review_menu._query_for_category("portfolio_exact", "2")

    assert query.portfolio_id == "portfolio_exact"
    assert query.candidate_conditions == ("ready_for_consideration",)
    assert query.selected_state == "unselected"


def test_selection_categories_remain_distinct() -> None:
    ready = candidate_review_menu._query_for_category("portfolio_exact", "2")
    selected = candidate_review_menu._query_for_category("portfolio_exact", "3")

    assert ready.selected_state == "unselected"
    assert selected.selected_state == "selected"
    assert ready.selected_state != selected.selected_state


def test_guided_review_list_uses_instructional_detail_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail()
    monkeypatch.setattr(
        candidate_review_menu,
        "build_teacher_candidate_detail",
        lambda _detail: SimpleNamespace(
            evidence_label="Feedback — Argument Paragraph (PDF)"
        ),
    )

    rendered = candidate_review_menu._item_line(_item(), detail=detail)

    assert "Feedback — Argument Paragraph (PDF)" in rendered
    assert "Synthetic evidence" not in rendered
    assert "Ready For Consideration" in rendered


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
        ["5", "1", "1", "2", "", "select candidate", "", "B"]
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



def test_single_active_selection_is_carried_forward_without_prompt() -> None:
    detail = _detail(active=True)
    output = io.StringIO()

    def unexpected_input(_prompt: str) -> str:
        pytest.fail("a one-item Active Selection chooser must not prompt")

    selected = candidate_review_menu._choose_active_selection(
        unexpected_input,
        output,
        detail,
    )

    assert selected is detail.selections[0]
    assert "Using the active Selection for this evidence" in output.getvalue()
    assert "Active Selection number:" not in output.getvalue()


def test_candidate_decision_confirmation_mismatch_is_explicit_and_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail()
    plan = SimpleNamespace(
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
        proposed_section_ids=("section_one",),
        intended_profile_requirement_ids=(),
        condition_acknowledgement_required=False,
        confirmation_phrase="SELECT CANDIDATE",
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "plan_candidate_decision",
        lambda *_args, **_kwargs: plan,
    )
    executed: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_candidate_decision",
        lambda *_args, **_kwargs: (
            executed.append(_args[1]),
            SimpleNamespace(state_revision=12),
        )[1],
    )
    raw_input = _inputs(["1", "", "SELECT", "select candidate"])
    output = io.StringIO()
    clear_calls: list[str] = []

    candidate_review_menu._decision_flow(
        root=tmp_path,
        detail=detail,
        decision="select",
        selection_proposal_id=None,
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: clear_calls.append("clear"),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(executed) == 1
    assert "Confirmation not accepted." in output.getvalue()
    assert output.getvalue().count("Final Candidate Decision Review") == 2
    assert len(clear_calls) >= 4



def test_post_selection_next_action_reloads_state_and_routes_to_separate_placement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail()
    refreshed = _detail(active=True)
    refreshed.selections[0].active_placement_ids = ()
    refreshed.placements = ()
    refreshed.sections = (_section("section_one", "Baseline Evidence"),)
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda _root, entry_id: (
            refreshed
            if entry_id == detail.inbox_detail.item.entry_id
            else pytest.fail("unexpected Candidate entry")
        ),
    )
    placement_calls: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "_placement_flow",
        lambda **kwargs: placement_calls.append(kwargs["detail"]),
    )
    output = io.StringIO()

    result = candidate_review_menu._post_selection_next_action(
        root=tmp_path,
        entry_id=detail.inbox_detail.item.entry_id,
        state_revision=12,
        input_fn=lambda _prompt: "1",
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert result is True
    assert placement_calls == [refreshed]
    assert "1. Place now in Baseline Evidence" in output.getvalue()
    assert "Selection and Placement remain separate explicit actions." in output.getvalue()


def test_post_selection_next_action_does_not_create_placement_without_choice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refreshed = _detail(active=True)
    refreshed.selections[0].active_placement_ids = ()
    refreshed.placements = ()
    refreshed.sections = (_section("section_one", "Baseline Evidence"),)
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda *_args, **_kwargs: refreshed,
    )
    placement_calls: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "_placement_flow",
        lambda **kwargs: placement_calls.append(kwargs["detail"]),
    )

    result = candidate_review_menu._post_selection_next_action(
        root=tmp_path,
        entry_id="entry_exact",
        state_revision=12,
        input_fn=lambda _prompt: "",
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert result is False
    assert placement_calls == []


def test_post_selection_refresh_failure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_refresh(*_args: object, **_kwargs: object) -> object:
        raise candidate_review_menu.CandidateReviewError(
            "candidate_review.state_changed",
            "current Candidate state changed",
        )

    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        fail_refresh,
    )
    output = io.StringIO()
    placement_calls: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "_placement_flow",
        lambda **kwargs: placement_calls.append(kwargs["detail"]),
    )

    result = candidate_review_menu._post_selection_next_action(
        root=tmp_path,
        entry_id="entry_exact",
        state_revision=12,
        input_fn=lambda _prompt: pytest.fail("refresh failure must not prompt"),
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert result is True
    assert placement_calls == []
    assert "could not be refreshed for Placement" in output.getvalue()
    assert "candidate_review.state_changed" in output.getvalue()



def test_post_selection_candidate_inbox_refresh_failure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_refresh(*_args: object, **_kwargs: object) -> object:
        raise candidate_review_menu.CandidateInboxError(
            "candidate_inbox.state_invalid",
            "Canonical Vitrine state is unavailable.",
        )

    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        fail_refresh,
    )
    output = io.StringIO()
    placement_calls: list[object] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "_placement_flow",
        lambda **kwargs: placement_calls.append(kwargs["detail"]),
    )

    result = candidate_review_menu._post_selection_next_action(
        root=tmp_path,
        entry_id="entry_exact",
        state_revision=12,
        input_fn=lambda _prompt: pytest.fail("refresh failure must not prompt"),
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert result is True
    assert placement_calls == []
    assert "could not be refreshed for Placement" in output.getvalue()
    assert "candidate_inbox.state_invalid" in output.getvalue()



def test_withdrawal_uses_shared_confirmation_and_success_redraw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail(active=True)
    detail.selections[0].active_placement_ids = ()
    detail.placements = ()
    monkeypatch.setattr(
        candidate_review_menu,
        "plan_selection_withdrawal",
        lambda *_args, **kwargs: SimpleNamespace(
            selection_id=kwargs["selection_id"],
            candidate_id="candidate_exact",
            selection_evaluation_id="evaluation_origin",
            active_placement_ids=(),
            affected_section_ids=(),
            reason=kwargs["reason"],
            observed_state_revision=51,
            arrangement_pointers=(),
            confirmation_phrase="WITHDRAW SELECTION",
        ),
    )
    calls: list[str] = []
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_selection_withdrawal",
        lambda *_args, **_kwargs: (
            calls.append("withdrawal"),
            SimpleNamespace(state_revision=52),
        )[1],
    )
    output = io.StringIO()
    clear_calls: list[str] = []
    raw_input = _inputs(["teacher reason", "withdraw selection"])

    candidate_review_menu._withdrawal_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: clear_calls.append("clear"),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls == ["withdrawal"]
    assert "Selection withdrawn." in output.getvalue()
    assert len(clear_calls) >= 3


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
    raw_input = _inputs(["3", "1", "1", "PLACE SELECTION", "", "B"])

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
    monkeypatch.setattr(
        candidate_review_menu,
        "list_candidate_review_section_guidance",
        lambda *_args, **_kwargs: successor_detail.sections,
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
        ["1", "1", "2", "replace reason", "REPLACE SELECTION"]
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
    annotation_input = _inputs(["1", "1", "1", "1", "note", "save annotation"])
    candidate_review_menu._annotation_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: annotation_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
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
        ["1", "1", "1", "1", "prompt", "v1", "Prompt", "text", "save reflection"]
    )
    candidate_review_menu._reflection_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: reflection_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
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
    review_input = _inputs(["1", "1", "1", "", "reason", "record review"])
    candidate_review_menu._review_flow(
        root=tmp_path,
        detail=detail,
        input_fn=lambda prompt: review_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls == ["annotation", "reflection", "review"]
