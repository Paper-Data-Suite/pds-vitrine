from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.route_registrations import (
    load_route_registration,
    write_route_registration,
)
from pds_core.routes import route_registration_path

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.models import (
    CurationTargetRef,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
)
from vitrine.paper_reflection_printing import (
    PaperReflectionPrintContextError,
    PaperReflectionPrintRouteError,
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
    validate_reflection_print_plan,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance


def _issued(tmp_path: Path, *, pages: int = 2):
    setup = build_curation_fixture_workspace(tmp_path)
    result = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated works without assuming improvement.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        issued_by=ACTOR,
        page_count=pages,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item for item in result.records if isinstance(item, ReflectionPromptIssuance)
    )
    response_pages = tuple(
        item for item in result.records if isinstance(item, ReflectionResponsePage)
    )
    return setup, result.state_revision, issuance, response_pages


def test_print_plan_reloads_exact_durable_issuance_and_page_order(
    tmp_path: Path,
) -> None:
    setup, revision, issuance, pages = _issued(tmp_path)

    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )

    assert plan.workspace_root == setup.workspace.resolve()
    assert plan.state_revision == revision
    assert plan.issuance == issuance
    assert plan.pages == pages
    assert tuple(page.response_page_id for page in plan.pages) == (
        issuance.response_page_ids
    )
    assert plan.issuance.prompt_snapshot == (
        "Compare the curated works without assuming improvement."
    )
    assert plan.issuance.target_references == (
        CurationTargetRef(
            target_kind="portfolio",
            target_id=setup.portfolio_id,
        ),
    )
    assert plan.issuance.student_reference.student_id
    assert tuple(route.payload_text for route in plan.routes)
    assert all(
        issuance.student_reference.student_id not in route.payload_text
        for route in plan.routes
    )


def test_print_plan_is_nonmutating_for_core_routes(tmp_path: Path) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)

    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )

    assert all(
        not route_registration_path(setup.workspace, route.locator).exists()
        for route in plan.routes
    )


def test_print_plan_rejects_stale_state_revision(tmp_path: Path) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)

    with pytest.raises(
        PaperReflectionPrintContextError,
        match="state changed",
    ):
        prepare_reflection_print_plan(
            setup.workspace,
            issuance_id=issuance.issuance_id,
            expected_state_revision=revision - 1,
        )


def test_print_plan_validation_rejects_reordered_pages(tmp_path: Path) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )
    tampered = object.__new__(type(plan))
    object.__setattr__(tampered, "workspace_root", plan.workspace_root)
    object.__setattr__(tampered, "state_revision", plan.state_revision)
    object.__setattr__(tampered, "issuance", plan.issuance)
    object.__setattr__(tampered, "pages", tuple(reversed(plan.pages)))
    object.__setattr__(tampered, "routes", plan.routes)

    with pytest.raises(
        PaperReflectionPrintContextError,
        match="page order",
    ):
        validate_reflection_print_plan(tampered)


def test_route_persistence_creates_and_verifies_complete_set(
    tmp_path: Path,
) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )

    result = persist_reflection_print_route_registrations(plan)

    assert len(result.registration_paths) == len(plan.routes)
    assert result.created_paths == result.registration_paths
    assert result.reused_paths == ()
    for route, path in zip(plan.routes, result.registration_paths, strict=True):
        assert path.is_file()
        assert load_route_registration(setup.workspace, route.locator) == (
            route.registration
        )


def test_exact_route_persistence_replay_is_idempotent(tmp_path: Path) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )
    first = persist_reflection_print_route_registrations(plan)
    second = persist_reflection_print_route_registrations(plan)

    assert first.created_paths == first.registration_paths
    assert second.created_paths == ()
    assert second.reused_paths == second.registration_paths


def test_contradictory_existing_route_blocks_entire_missing_set_before_write(
    tmp_path: Path,
) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path)
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )
    assert len(plan.routes) == 2

    second = plan.routes[1]
    tampered_registration = replace(
        second.registration,
        human_fallback="Vitrine Reflection | contradictory existing route",
    )
    write_route_registration(setup.workspace, tampered_registration)

    first_path = route_registration_path(
        setup.workspace,
        plan.routes[0].locator,
    )
    assert not first_path.exists()

    with pytest.raises(PaperReflectionPrintRouteError, match="contradicts"):
        persist_reflection_print_route_registrations(plan)

    assert not first_path.exists()
