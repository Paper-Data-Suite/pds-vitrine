from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine import working_composition_menu
from vitrine.models import ActorAttribution
from vitrine.workflow_context import default_workflow_dependencies

ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_test",
    owning_system="local",
    role_snapshot="teacher",
)


def _inputs(values: list[str]) -> object:
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _empty_view() -> SimpleNamespace:
    return SimpleNamespace(composition=None, inventory=None, pointer_revision=None)


def _preparation(
    *,
    unresolved: tuple[str, ...] = (),
    disposition: str = "create_initial",
) -> SimpleNamespace:
    placement = SimpleNamespace(
        placement_id="placement_exact",
        selection_id="selection_exact",
        candidate_id="candidate_exact",
        candidate_display_snapshot="Exact Work",
        candidate_condition_state="ready_for_consideration",
        unresolved_condition_codes=(),
        section_id="baseline",
        display_title=None,
        display_caption=None,
    )
    section = SimpleNamespace(
        section_id="baseline",
        label="Baseline",
        purpose="Exact baseline section.",
        order=1,
        obligation="required",
        minimum_placements=1,
        maximum_placements=1,
        active_placement_count=1,
        current_arrangement_id="arrangement_exact",
        current_arrangement_revision=2,
        current_arrangement_pointer_revision=2,
        placements=(placement,),
    )
    requirement = SimpleNamespace(
        requirement_id="baseline_rule",
        title="Baseline evidence",
        statement="Machine-readable baseline cardinality.",
        requirement_kind="section",
        obligation="required",
        scope_kind="section",
        scope_reference="baseline",
        satisfaction_class="placement_cardinality",
        status="satisfied_current_curation",
        related_to_frozen_inventory=True,
        associated_unresolved_obligation_codes=(),
    )
    source = SimpleNamespace(
        selection_id="selection_exact",
        candidate_id="candidate_exact",
        publication_id="publication_exact",
        series_head_publication_id="publication_exact",
        observed_series_state="current",
        observed_withdrawal_state="not_withdrawn",
        current_use_state="current",
    )
    audience = SimpleNamespace(
        audience_rule_id="student_review",
        audience_class="student",
        purpose="Student review policy metadata.",
        allowed_content_classes=("student_work",),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=(),
        presentation_class="student_portfolio",
        retention_policy_reference=None,
    )
    payload = SimpleNamespace(
        selection_ids=("selection_exact",),
        placement_ids=("placement_exact",),
        arrangement_ids=("arrangement_exact",),
        included_rationale_ids=(),
        included_curation_revisions=(),
        applicable_review_decision_ids=(),
        related_profile_requirement_ids=("baseline_rule",),
        unresolved_obligation_codes=unresolved,
        coherence_state=(
            "coherent_with_unresolved_obligations" if unresolved else "coherent"
        ),
    )
    return SimpleNamespace(
        contract_version="vitrine_guided_working_composition_v1",
        observed_state_revision=7,
        portfolio_id="portfolio_exact",
        portfolio_subject_id="subject_exact",
        profile_binding_id="binding_exact",
        profile_revision_id="profile_exact",
        profile_revision_number=1,
        observed_composition_pointer_revision=None,
        current_composition_revision=None,
        predicted_composition_revision=1,
        predecessor_composition_revision=None,
        predicted_composition_pointer_revision=1,
        disposition=disposition,
        payload=payload,
        sections=(section,),
        selections=(),
        unplaced_selection_ids=(),
        requirements=(requirement,),
        source_observations=(source,),
        reviews=(),
        audience_rules=(audience,),
        requested_composition_note=None,
        composition_note_will_persist=disposition != "reuse_exact_current",
        preparation_fingerprint="a" * 64,
    )


def test_guided_menu_prepares_read_only_and_renders_exact_section_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared: list[tuple[Path, str, str | None]] = []
    preparation = _preparation()
    monkeypatch.setattr(working_composition_menu, "show_composition", lambda *_: _empty_view())

    def prepare(root: Path, portfolio_id: str, *, composition_note: str | None = None) -> object:
        prepared.append((root, portfolio_id, composition_note))
        return preparation

    monkeypatch.setattr(working_composition_menu, "prepare_working_composition", prepare)
    output = io.StringIO()
    raw_input = _inputs(["1", "", "1", "", "B", "B"])

    working_composition_menu.run_working_composition_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert prepared == [(tmp_path, "portfolio_exact", None)]
    text = output.getvalue()
    assert "1. Baseline (baseline)" in text
    assert "Placement placement_exact; Selection selection_exact" in text
    assert "Exact Work" in text


def test_guided_menu_freezes_the_exact_reviewed_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation(unresolved=("approval_required",))
    monkeypatch.setattr(working_composition_menu, "show_composition", lambda *_: _empty_view())
    monkeypatch.setattr(
        working_composition_menu,
        "prepare_working_composition",
        lambda *_args, **_kwargs: preparation,
    )
    frozen: list[object] = []

    def freeze(
        _root: Path,
        exact_preparation: object,
        *,
        created_by: ActorAttribution,
        authority_gate: object,
    ) -> SimpleNamespace:
        frozen.append((exact_preparation, created_by, authority_gate))
        return SimpleNamespace(state_revision=8, disposition="created", records=())

    monkeypatch.setattr(
        working_composition_menu,
        "freeze_prepared_working_composition",
        freeze,
    )
    output = io.StringIO()
    raw_input = _inputs(["1", "", "7", "FREEZE COMPOSITION", "", "B"])
    dependencies = default_workflow_dependencies()

    working_composition_menu.run_working_composition_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=dependencies,
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert len(frozen) == 1
    assert frozen[0][0] is preparation
    assert frozen[0][1] == ACTOR
    assert frozen[0][2] is dependencies.curation_authority_gate
    text = output.getvalue()
    assert "retain the unresolved obligations" in text
    assert "Freezing does not clear, waive, satisfy, or authorize them." in text


def test_guided_menu_requires_exact_freeze_phrase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation()
    monkeypatch.setattr(working_composition_menu, "show_composition", lambda *_: _empty_view())
    monkeypatch.setattr(
        working_composition_menu,
        "prepare_working_composition",
        lambda *_args, **_kwargs: preparation,
    )
    frozen: list[object] = []
    monkeypatch.setattr(
        working_composition_menu,
        "freeze_prepared_working_composition",
        lambda *args, **kwargs: frozen.append((args, kwargs)),
    )
    raw_input = _inputs(["1", "", "7", "FREEZE", "", "B", "B"])

    working_composition_menu.run_working_composition_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert frozen == []


def test_guided_menu_shows_audience_constraints_without_creating_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation()
    monkeypatch.setattr(working_composition_menu, "show_composition", lambda *_: _empty_view())
    monkeypatch.setattr(
        working_composition_menu,
        "prepare_working_composition",
        lambda *_args, **_kwargs: preparation,
    )
    output = io.StringIO()
    raw_input = _inputs(["1", "", "5", "", "B", "B"])

    working_composition_menu.run_working_composition_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    text = output.getvalue()
    assert "student (student_review)" in text
    assert "does not create an Audience Context" in text
    assert "does not authorize disclosure or build a Snapshot" in text


def test_guided_menu_reads_exact_historical_composition_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[int | None] = []
    composition = SimpleNamespace(
        composition_revision=2,
        profile_binding_id="binding_exact",
        profile_revision=SimpleNamespace(
            portfolio_profile_id="profile_exact", profile_revision=1
        ),
        predecessor_composition_revision=1,
        created_by=ACTOR,
        created_at=SimpleNamespace(isoformat=lambda: "2026-09-07T00:00:00+00:00"),
        composition_note=None,
        selection_ids=(),
        placement_ids=(),
        arrangement_ids=(),
    )
    inventory = SimpleNamespace(
        coherence_state="coherent",
        unresolved_obligation_codes=(),
        included_rationale_ids=(),
        included_curation_revisions=(),
        applicable_review_decision_ids=(),
        related_profile_requirement_ids=(),
    )

    def show(_root: Path, _portfolio_id: str, revision: int | None = None) -> SimpleNamespace:
        requested.append(revision)
        if revision is None:
            return _empty_view()
        return SimpleNamespace(composition=composition, inventory=inventory, pointer_revision=3)

    monkeypatch.setattr(working_composition_menu, "show_composition", show)
    output = io.StringIO()
    raw_input = _inputs(["3", "2", "", "B"])

    working_composition_menu.run_working_composition_menu(
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert 2 in requested
    assert "Working Composition revision 2" in output.getvalue()
    assert "Revision: 2" in output.getvalue()
