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
    selection = SimpleNamespace(
        selection_id="selection_exact",
        candidate_id="candidate_exact",
        candidate_display_snapshot="Exact Work",
        candidate_condition_state="ready_for_consideration",
        unresolved_condition_codes=(),
        placement_ids=("placement_exact",),
        section_ids=("baseline",),
        is_placed=True,
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
        selections=(selection,),
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
    assert "1. Baseline — Required" in text
    assert "Exact Work" in text
    assert "Placement placement_exact" not in text
    assert "Selection selection_exact" not in text
    assert "arrangement_exact" not in text


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
    assert "- Student" in text
    assert "student_review" not in text
    assert "does not create an Audience Context" in text
    assert "does not authorize disclosure or build a Snapshot" in text


def test_preparation_technical_details_preserve_exact_provenance() -> None:
    output = io.StringIO()

    working_composition_menu._render_preparation_technical_details(
        output,
        _preparation(),
    )

    text = output.getvalue()
    assert "Working Composition Technical Details / Provenance" in text
    assert "Portfolio ID: portfolio_exact" in text
    assert "Profile Binding ID: binding_exact" in text
    assert "Selection IDs: selection_exact" in text
    assert "Placement IDs: placement_exact" in text
    assert "Arrangement IDs: arrangement_exact" in text
    assert "Baseline (baseline)" in text
    assert "Placement placement_exact; Selection selection_exact" in text
    assert "Baseline evidence (baseline_rule)" in text
    assert "Publication publication_exact" in text
    assert "student (student_review)" in text


def test_frozen_composition_default_hides_exact_identity_but_technical_preserves_it() -> None:
    composition = SimpleNamespace(
        composition_revision=2,
        profile_binding_id="binding_exact",
        profile_revision=SimpleNamespace(
            portfolio_profile_id="profile_exact",
            profile_revision=1,
        ),
        predecessor_composition_revision=1,
        created_by=ACTOR,
        created_at=SimpleNamespace(
            isoformat=lambda: "2026-09-07T00:00:00+00:00"
        ),
        composition_note="Teacher note",
        selection_ids=("selection_exact",),
        placement_ids=("placement_exact",),
        arrangement_ids=("arrangement_exact",),
    )
    inventory = SimpleNamespace(
        coherence_state="coherent",
        unresolved_obligation_codes=(),
        included_rationale_ids=("rationale_exact",),
        included_curation_revisions=(),
        applicable_review_decision_ids=("review_exact",),
        related_profile_requirement_ids=("baseline_rule",),
    )
    view = SimpleNamespace(
        composition=composition,
        inventory=inventory,
        pointer_revision=3,
    )

    default = io.StringIO()
    working_composition_menu._render_composition_view(
        default,
        view,
        heading="Current frozen Working Composition",
    )
    rendered = default.getvalue()
    assert "Revision: 2" in rendered
    assert "Selections included: 1" in rendered
    assert "Coherence: Coherent" in rendered
    assert "binding_exact" not in rendered
    assert "selection_exact" not in rendered
    assert "placement_exact" not in rendered
    assert "arrangement_exact" not in rendered
    assert "review_exact" not in rendered
    assert "baseline_rule" not in rendered

    technical = io.StringIO()
    working_composition_menu._render_composition_technical_details(
        technical,
        view,
        heading="Current frozen Working Composition",
    )
    exact = technical.getvalue()
    assert "Technical Details / Provenance" in exact
    assert "Profile Binding: binding_exact" in exact
    assert "Selection IDs: selection_exact" in exact
    assert "Placement IDs: placement_exact" in exact
    assert "Arrangement IDs: arrangement_exact" in exact
    assert "Composition pointer revision: 3" in exact
    assert "Applicable Review Decision IDs: review_exact" in exact
    assert "Related Profile Requirement IDs: baseline_rule" in exact


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
    rendered = output.getvalue()
    assert "Working Composition revision 2" in rendered
    assert "Revision: 2" in rendered
    assert "Profile Binding:" not in rendered
