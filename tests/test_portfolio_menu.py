from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.menu_navigation import QuitPDS, ReturnToMainMenu

from vitrine import portfolio_menu
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


@pytest.mark.parametrize("raw", ("not-a-number", "0", "-1", "3"))
def test_numbered_choice_rejects_out_of_range_values(raw: str) -> None:
    assert portfolio_menu._numbered_choice(raw, ("first", "second")) is None


def test_numbered_choice_preserves_back_navigation() -> None:
    assert portfolio_menu._numbered_choice("B", ("first",)) is not None


@pytest.mark.parametrize(("raw", "error"), (("M", ReturnToMainMenu), ("Q", QuitPDS)))
def test_numbered_choice_preserves_core_unwind_navigation(
    raw: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        portfolio_menu._numbered_choice(raw, ("first",))


def test_numbered_choice_maps_one_based_value() -> None:
    assert portfolio_menu._numbered_choice("2", ("first", "second")) == "second"


def test_teacher_creation_selects_subject_and_preserves_observed_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    subject = SimpleNamespace(
        portfolio_subject_id="subject_exact",
        display_name="Synthetic learner",
        status="current",
    )
    monkeypatch.setattr(portfolio_menu, "list_subjects", lambda _root: (subject,))
    monkeypatch.setattr(
        portfolio_menu,
        "observe_portfolio_state_revision",
        lambda _root: events.append("observed") or 7,
    )

    def create(_root: Path, **kwargs: object) -> object:
        events.append(kwargs)
        return SimpleNamespace(portfolio=SimpleNamespace(portfolio_id="portfolio_new"))

    monkeypatch.setattr(portfolio_menu, "create_portfolio", create)
    raw_input = _inputs(["1", "1", "Title", "Description", "CREATE", "", "B"])

    portfolio_menu.run_portfolio_menu(
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert events[0] == "observed"
    request = events[1]
    assert isinstance(request, dict)
    assert request["portfolio_subject_id"] == "subject_exact"
    assert request["expected_state_revision"] == 7
    assert request["title_snapshot"] == "Title"
    assert request["description_snapshot"] == "Description"


def test_candidate_number_maps_to_exact_candidate_before_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = SimpleNamespace(
        portfolio_id="portfolio_exact",
        title_snapshot="Portfolio",
        subject_display_label="Synthetic learner",
        portfolio_subject_id="subject_exact",
        profile_binding_id=None,
        candidate_count=0,
        active_selection_count=0,
        current_composition_revision=None,
        snapshot_series_count=0,
    )
    monkeypatch.setattr(
        portfolio_menu,
        "show_portfolio",
        lambda _root, _id: SimpleNamespace(summary=summary),
    )
    candidates = tuple(
        SimpleNamespace(
            candidate_id=f"candidate_{index}",
            display_snapshot=f"Candidate {index}",
            condition_state="ready_for_consideration",
            eligible_section_ids=(f"section_{index}",),
        )
        for index in (1, 2)
    )
    monkeypatch.setattr(
        portfolio_menu, "list_candidate_summaries", lambda *_: candidates
    )
    monkeypatch.setattr(
        portfolio_menu,
        "list_candidate_inbox",
        lambda *_args, **_kwargs: SimpleNamespace(items=()),
    )
    endpoint = SimpleNamespace(
        core_publication=SimpleNamespace(publication_id="publication_exact"),
        producer_source=SimpleNamespace(
            producer_module_id="fixture_module",
            source_record_kind="attempt",
            source_record_id="source_exact",
            native_revision=4,
        ),
        source_artifact=SimpleNamespace(
            artifact_id="artifact_exact",
            artifact_kind="document",
            representation_kind="text",
        ),
        subject_relationship_assertions=(),
    )
    monkeypatch.setattr(
        portfolio_menu,
        "show_candidate_detail",
        lambda _root, candidate_id: SimpleNamespace(
            candidate_id=candidate_id,
            candidate_evaluation_id=f"evaluation_{candidate_id}",
            profile_binding_id="binding_exact",
            display_snapshot="Candidate detail",
            source_endpoint=endpoint,
            condition_state="ready_for_consideration",
            evaluation_reason_codes=("profile_rule_match",),
            unresolved_condition_codes=(),
            availability_observations=(),
            eligible_section_ids=("section_2",),
        ),
    )
    monkeypatch.setattr(
        portfolio_menu, "observe_portfolio_state_revision", lambda _root: 12
    )
    selected: list[str] = []

    def select(_root: Path, **kwargs: object) -> object:
        selected.append(str(kwargs["candidate_id"]))
        return SimpleNamespace(state_revision=13)

    monkeypatch.setattr(portfolio_menu, "select_candidate_directly", select)
    raw_input = _inputs(["3", "", "2", "SELECT", "section_2", "", "B"])

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert selected == ["candidate_2"]


def test_portfolio_subject_route_uses_exact_subject_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = SimpleNamespace(
        portfolio_id="portfolio_exact",
        title_snapshot="Portfolio",
        subject_display_label="Synthetic learner",
        portfolio_subject_id="subject_exact",
        profile_binding_id=None,
        candidate_count=0,
        active_selection_count=0,
        current_composition_revision=None,
        snapshot_series_count=0,
    )
    monkeypatch.setattr(
        portfolio_menu, "show_portfolio", lambda *_: SimpleNamespace(summary=summary)
    )
    routed: list[object] = []
    monkeypatch.setattr(
        portfolio_menu,
        "run_subject_menu",
        lambda **kwargs: routed.append(kwargs),
    )
    raw_input = _inputs(["1", "", "B"])

    portfolio_menu._portfolio_context(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert routed[0]["portfolio_subject_id"] == "subject_exact"
    assert routed[0]["workspace_root"] == tmp_path


def test_existing_profile_binding_is_inspectable_without_automatic_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = SimpleNamespace(portfolio_profile_id="profile", profile_revision=1)
    binding = SimpleNamespace(
        profile_binding_id="binding_current", profile_revision=reference
    )
    revision = SimpleNamespace(
        label="Current Profile",
        purpose_kind="growth",
        sections=(SimpleNamespace(section_id="reflection"),),
    )
    monkeypatch.setattr(
        portfolio_menu, "get_portfolio_profile_binding", lambda *_: binding
    )
    monkeypatch.setattr(portfolio_menu, "get_profile_revision", lambda *_: revision)
    migrated: list[object] = []
    monkeypatch.setattr(
        portfolio_menu,
        "migrate_portfolio_profile",
        lambda *args, **kwargs: migrated.append((args, kwargs)),
    )

    portfolio_menu._profile_binding_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=_inputs(["1"]),  # type: ignore[arg-type]
        output=io.StringIO(),
        actor=ACTOR,
    )

    assert migrated == []


def test_profile_migration_preserves_exact_observed_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = SimpleNamespace(portfolio_profile_id="profile", profile_revision=1)
    target = SimpleNamespace(portfolio_profile_id="profile", profile_revision=2)
    monkeypatch.setattr(
        portfolio_menu,
        "get_portfolio_profile_binding",
        lambda *_: SimpleNamespace(
            profile_binding_id="binding_current", profile_revision=current
        ),
    )
    monkeypatch.setattr(portfolio_menu, "observe_profile_state_revision", lambda _: 17)
    monkeypatch.setattr(
        portfolio_menu,
        "list_bindable_profile_revisions",
        lambda _: (
            SimpleNamespace(label="Current", reference=current),
            SimpleNamespace(label="Target", reference=target),
        ),
    )
    impact = SimpleNamespace(added=(), removed=(), replaced=(), materially_changed=())
    monkeypatch.setattr(
        portfolio_menu,
        "analyze_profile_migration",
        lambda *_args, **_kwargs: SimpleNamespace(
            requirement_impact=impact,
            affected_section_ids=(),
            potentially_affected_selection_count=0,
            blocked=False,
        ),
    )
    migrated: list[object] = []
    monkeypatch.setattr(
        portfolio_menu,
        "migrate_portfolio_profile",
        lambda *args, **kwargs: migrated.append((args, kwargs)),
    )
    raw_input = _inputs(
        ["2", "2", "", "", "", "", "", "MIGRATE", "reason", "authority"]
    )

    portfolio_menu._profile_binding_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        actor=ACTOR,
    )

    assert migrated[0][1]["expected_state_revision"] == 17
    assert migrated[0][0][2] is target


@pytest.mark.parametrize("error", (EOFError, KeyboardInterrupt))
def test_read_maps_terminal_interrupts_to_core_quit(error: type[BaseException]) -> None:
    def interrupted(_prompt: str) -> str:
        raise error

    assert portfolio_menu._read(interrupted, "Choice: ") == "Q"


def test_teacher_decision_uses_exact_proposal_and_observed_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(portfolio_menu, "list_active_selections", lambda *_: ())
    monkeypatch.setattr(
        portfolio_menu, "observe_portfolio_state_revision", lambda _: 23
    )
    decided: list[dict[str, object]] = []
    monkeypatch.setattr(
        portfolio_menu,
        "decide_selection_proposal",
        lambda _root, **kwargs: decided.append(kwargs),
    )
    raw_input = _inputs(["1", "proposal_exact", "accepted", "DECIDE", "reason"])

    portfolio_menu._curation_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert decided[0]["selection_proposal_id"] == "proposal_exact"
    assert decided[0]["decision"] == "accepted"
    assert decided[0]["expected_state_revision"] == 23


@pytest.mark.parametrize(
    ("action", "confirmation", "service_name"),
    (
        ("3", "WITHDRAW", "withdraw_selection"),
        ("4", "INVALIDATE", "invalidate_selection"),
    ),
)
def test_teacher_selection_lifecycle_maps_exact_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    confirmation: str,
    service_name: str,
) -> None:
    selection = SimpleNamespace(
        selection_id="selection_exact", candidate_id="candidate_exact"
    )
    monkeypatch.setattr(
        portfolio_menu, "list_active_selections", lambda *_: (selection,)
    )
    monkeypatch.setattr(
        portfolio_menu, "observe_portfolio_state_revision", lambda _: 29
    )
    monkeypatch.setattr(
        portfolio_menu,
        "show_candidate_detail",
        lambda *_: SimpleNamespace(eligible_section_ids=()),
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        portfolio_menu,
        service_name,
        lambda _root, **kwargs: calls.append(kwargs),
    )
    raw_input = _inputs([action, "1", "teacher reason", confirmation])

    portfolio_menu._curation_workflow(
        root=tmp_path,
        portfolio_id="portfolio_exact",
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls[0]["selection_id"] == "selection_exact"
    assert calls[0]["expected_state_revision"] == 29
    assert calls[0]["expected_pointer_revisions"] == {}


def test_portfolio_menu_surfaces_controlled_errors_and_clears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        portfolio_menu,
        "list_portfolios",
        lambda _root: (_ for _ in ()).throw(ValueError("controlled failure")),
    )
    output = io.StringIO()
    clears: list[None] = []
    raw_input = _inputs(["3", "", "B"])

    portfolio_menu.run_portfolio_menu(
        input_fn=lambda prompt: raw_input(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: clears.append(None),
        dependencies=default_workflow_dependencies(),
        workspace_root=tmp_path,
        actor=ACTOR,
    )

    assert "Portfolio workflow problem" in output.getvalue()
    assert "controlled failure" in output.getvalue()
    assert "Traceback" not in output.getvalue()
    assert len(clears) >= 3
