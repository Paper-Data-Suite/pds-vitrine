from __future__ import annotations

from types import SimpleNamespace

import pytest

from vitrine import workflow_views


def test_candidate_summaries_default_to_active_profile_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = SimpleNamespace(
        candidate_id="candidate_current",
        profile_binding_id="binding_current",
        display_snapshot="Current",
        condition_state="ready_for_consideration",
        eligible_section_ids=("section",),
        portfolio_id="portfolio",
    )
    historical = SimpleNamespace(
        candidate_id="candidate_historical",
        profile_binding_id="binding_old",
        display_snapshot="Historical",
        condition_state="ready_for_consideration",
        eligible_section_ids=("section",),
        portfolio_id="portfolio",
    )
    profile_state = SimpleNamespace(
        active_binding=lambda _portfolio_id: SimpleNamespace(
            profile_binding_id="binding_current"
        )
    )
    curation_state = SimpleNamespace(
        candidates=(historical, current), active_selections=lambda **_kwargs: ()
    )
    monkeypatch.setattr(workflow_views, "_records", lambda _root: ())
    monkeypatch.setattr(
        workflow_views, "project_profile_state", lambda _records: profile_state
    )
    monkeypatch.setattr(
        workflow_views, "project_curation_state", lambda _records: curation_state
    )

    summaries = workflow_views.list_candidate_summaries("unused", "portfolio")

    assert tuple(item.candidate_id for item in summaries) == ("candidate_current",)


def test_exact_historical_composition_uses_its_own_binding_pointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = SimpleNamespace(
        portfolio_id="portfolio",
        profile_binding_id="binding_old",
        composition_revision=1,
        composition_inventory_id="inventory_old",
    )
    current = SimpleNamespace(
        portfolio_id="portfolio",
        profile_binding_id="binding_current",
        composition_revision=2,
        composition_inventory_id="inventory_current",
    )
    calls: list[str] = []

    def pointers(_portfolio_id: str, binding_id: str) -> tuple[object, ...]:
        calls.append(binding_id)
        revision = 4 if binding_id == "binding_old" else 9
        return (SimpleNamespace(pointer_revision=revision),)

    curation_state = SimpleNamespace(
        compositions=(historical, current),
        composition_inventories=(),
        composition_pointer_heads=pointers,
    )
    monkeypatch.setattr(workflow_views, "_records", lambda _root: ())
    monkeypatch.setattr(
        workflow_views, "project_curation_state", lambda _records: curation_state
    )

    view = workflow_views.show_composition("unused", "portfolio", revision=1)

    assert view.composition is historical
    assert view.pointer_revision == 4
    assert calls == ["binding_old"]
