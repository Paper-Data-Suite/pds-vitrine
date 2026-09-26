from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.module_profiles import CORE_ROUTING_CONTRACT_VERSION
from pds_core.pds2 import parse_pds2_payload
from pds_core.route_registrations import (
    resolve_route_registration,
    write_route_registration,
)
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    ModuleRecordRef,
    ModuleWorkRef,
)

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.constants import VITRINE_MODULE_ID
from vitrine.models import (
    CurationTargetRef,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
)
from vitrine.paper_reflection_routes import (
    REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION,
    REFLECTION_RESPONSE_PAGE_RECORD_KIND,
    PaperReflectionRouteValidationError,
    build_reflection_response_page_route,
    build_reflection_response_route_set,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.pds_module import (
    VitrineRegistrationValidationError,
    get_module_profile,
    validate_vitrine_registration,
)


def _issued(tmp_path: Path, *, pages: int = 2):
    setup = build_curation_fixture_workspace(tmp_path)
    result = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated works.",
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
    return setup, issuance, response_pages


def test_reflection_response_route_uses_exact_core_identity(tmp_path: Path) -> None:
    _setup, issuance, pages = _issued(tmp_path, pages=1)
    route = build_reflection_response_page_route(issuance, pages[0])

    assert route.locator.schema == PDS2_SCHEMA
    assert route.locator.work == ModuleWorkRef(
        module_id=VITRINE_MODULE_ID,
        class_id=pages[0].class_id,
        work_id=pages[0].work_id,
    )
    assert route.locator.route_id == pages[0].route_id
    assert route.registration.schema_version == ROUTE_REGISTRATION_SCHEMA_VERSION
    assert route.registration.target == ModuleRecordRef(
        module_id=VITRINE_MODULE_ID,
        record_kind=REFLECTION_RESPONSE_PAGE_RECORD_KIND,
        record_id=pages[0].response_page_id,
        contract_version=REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION,
    )
    assert route.registration.status == "active"
    assert route.registration.module_details["issuance_id"] == issuance.issuance_id
    assert (
        route.registration.module_details["subject_link_id"]
        == issuance.subject_link_id
    )
    assert (
        route.registration.module_details["expected_student_id"]
        == issuance.student_reference.student_id
    )
    assert parse_pds2_payload(route.payload_text) == route.locator
    assert issuance.student_reference.student_id not in route.payload_text
    assert pages[0].response_page_id not in route.payload_text


def test_route_set_preserves_issuance_page_order(tmp_path: Path) -> None:
    _setup, issuance, pages = _issued(tmp_path)
    routes = build_reflection_response_route_set(issuance, pages)
    assert tuple(item.page.response_page_id for item in routes) == issuance.response_page_ids
    assert tuple(item.locator.route_id for item in routes) == tuple(
        page.route_id for page in pages
    )


def test_core_registration_round_trip_resolves_exact_locator(tmp_path: Path) -> None:
    setup, issuance, pages = _issued(tmp_path, pages=1)
    route = build_reflection_response_page_route(issuance, pages[0])
    path = write_route_registration(setup.workspace, route.registration)
    assert path.is_file()

    resolution = resolve_route_registration(setup.workspace, route.locator)
    assert resolution.locator == route.locator
    assert resolution.registration == route.registration
    assert resolution.locator.class_id == pages[0].class_id
    assert resolution.locator.work_id == pages[0].work_id
    assert resolution.locator.route_id == pages[0].route_id


def test_module_profile_declares_exact_core_contract() -> None:
    profile = get_module_profile()
    assert profile.module_id == VITRINE_MODULE_ID
    assert profile.display_name == "Vitrine"
    assert profile.supported_core_routing_contract_versions == frozenset(
        {CORE_ROUTING_CONTRACT_VERSION}
    )
    assert profile.supported_qr_schemas == frozenset({PDS2_SCHEMA})
    assert profile.supported_route_registration_schema_versions == frozenset(
        {ROUTE_REGISTRATION_SCHEMA_VERSION}
    )
    assert profile.dispatchable_route_statuses == frozenset({"active"})
    assert profile.registration_validator is validate_vitrine_registration
    assert callable(profile.route_handler)


def test_module_validator_accepts_exact_reflection_registration(tmp_path: Path) -> None:
    _setup, issuance, pages = _issued(tmp_path, pages=1)
    route = build_reflection_response_page_route(issuance, pages[0])
    validate_vitrine_registration(route.registration)


def test_module_validator_rejects_tampered_expected_student(tmp_path: Path) -> None:
    _setup, issuance, pages = _issued(tmp_path, pages=1)
    route = build_reflection_response_page_route(issuance, pages[0])
    details = dict(route.registration.module_details)
    details["expected_student_id"] = "wrong_student"
    tampered = replace(route.registration, module_details=details)

    with pytest.raises(VitrineRegistrationValidationError):
        validate_vitrine_registration(tampered)


def test_route_builder_rejects_page_reordered_against_issuance(tmp_path: Path) -> None:
    _setup, issuance, pages = _issued(tmp_path)
    reordered = (pages[1], pages[0])
    with pytest.raises(
        PaperReflectionRouteValidationError,
        match="preserve issuance response-page order",
    ):
        build_reflection_response_route_set(issuance, reordered)
