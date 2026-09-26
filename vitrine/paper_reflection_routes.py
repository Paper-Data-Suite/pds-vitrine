"""Core PDS2 routing contract for paper-native Reflection response pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from pds_core.pds2 import Pds2PayloadError, parse_pds2_payload, serialize_pds2_payload
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    ModuleRecordRef,
    ModuleWorkRef,
    RouteLocator,
    RouteRegistration,
    RoutingModelError,
)

from vitrine.constants import VITRINE_MODULE_ID
from vitrine.models import ReflectionPromptIssuance, ReflectionResponsePage

REFLECTION_RESPONSE_PAGE_RECORD_KIND: Final[str] = "reflection_response_page"
REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION: Final[str] = "1"

_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "issuance_id",
        "portfolio_id",
        "portfolio_subject_id",
        "subject_link_id",
        "expected_student_id",
        "school_year",
        "reflection_requirement_id",
        "logical_page",
        "total_pages",
    }
)


class PaperReflectionRouteError(ValueError):
    """Base error for Vitrine paper-Reflection route operations."""


class PaperReflectionRouteValidationError(PaperReflectionRouteError):
    """Raised when a paper-Reflection route is malformed or contradictory."""


@dataclass(frozen=True, slots=True)
class ReflectionResponsePageRoute:
    """One exact immutable Vitrine page mapped to one Core PDS2 route."""

    issuance: ReflectionPromptIssuance
    page: ReflectionResponsePage
    locator: RouteLocator
    registration: RouteRegistration
    payload_text: str

    def __post_init__(self) -> None:
        validate_reflection_response_page_route(self)


def reflection_response_page_target(page: object) -> ModuleRecordRef:
    if not isinstance(page, ReflectionResponsePage):
        raise PaperReflectionRouteValidationError(
            "page must be a ReflectionResponsePage."
        )
    return ModuleRecordRef(
        module_id=VITRINE_MODULE_ID,
        record_kind=REFLECTION_RESPONSE_PAGE_RECORD_KIND,
        record_id=page.response_page_id,
        contract_version=REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION,
    )


def reflection_response_page_module_details(
    issuance: object,
    page: object,
) -> dict[str, int | str]:
    issuance, page = _issuance_page(issuance, page)
    return {
        "issuance_id": issuance.issuance_id,
        "portfolio_id": issuance.portfolio_id,
        "portfolio_subject_id": issuance.portfolio_subject_id,
        "subject_link_id": issuance.subject_link_id,
        "expected_student_id": issuance.student_reference.student_id,
        "school_year": issuance.student_reference.school_year,
        "reflection_requirement_id": issuance.reflection_requirement_id,
        "logical_page": page.logical_page_number,
        "total_pages": page.total_pages,
    }


def reflection_response_page_human_fallback(
    issuance: object,
    page: object,
) -> str:
    issuance, page = _issuance_page(issuance, page)
    return (
        f"Vitrine Reflection | class={page.class_id} | work={page.work_id} "
        f"| expected_student={issuance.student_reference.student_id} "
        f"| page={page.logical_page_number}/{page.total_pages} "
        f"| page_id={page.response_page_id}"
    )


def build_reflection_response_page_route(
    issuance: object,
    page: object,
) -> ReflectionResponsePageRoute:
    """Purely construct the exact Core route for one immutable response page."""

    issuance, page = _issuance_page(issuance, page)
    try:
        locator = RouteLocator(
            schema=PDS2_SCHEMA,
            work=ModuleWorkRef(
                module_id=VITRINE_MODULE_ID,
                class_id=page.class_id,
                work_id=page.work_id,
            ),
            route_id=page.route_id,
        )
        registration = RouteRegistration(
            schema_version=ROUTE_REGISTRATION_SCHEMA_VERSION,
            locator=locator,
            target=reflection_response_page_target(page),
            created_at=page.created_at.isoformat(),
            status="active",
            human_fallback=reflection_response_page_human_fallback(issuance, page),
            module_details=reflection_response_page_module_details(issuance, page),
        )
        payload_text = serialize_pds2_payload(locator)
    except (RoutingModelError, Pds2PayloadError) as error:
        raise PaperReflectionRouteValidationError(str(error)) from error

    return ReflectionResponsePageRoute(
        issuance=issuance,
        page=page,
        locator=locator,
        registration=registration,
        payload_text=payload_text,
    )


def build_reflection_response_route_set(
    issuance: object,
    pages: object,
) -> tuple[ReflectionResponsePageRoute, ...]:
    if not isinstance(issuance, ReflectionPromptIssuance):
        raise PaperReflectionRouteValidationError(
            "issuance must be a ReflectionPromptIssuance."
        )
    if not isinstance(pages, (tuple, list)):
        raise PaperReflectionRouteValidationError("pages must be ordered.")
    values = tuple(pages)
    if len(values) != len(issuance.response_page_ids):
        raise PaperReflectionRouteValidationError(
            "Route page count must equal issuance response-page count."
        )
    routes = tuple(
        build_reflection_response_page_route(issuance, page)
        for page in values
    )
    if tuple(route.page.response_page_id for route in routes) != issuance.response_page_ids:
        raise PaperReflectionRouteValidationError(
            "Route pages must preserve issuance response-page order."
        )
    for field_values, label in (
        ((route.locator.route_id for route in routes), "route IDs"),
        ((route.locator for route in routes), "locators"),
        ((route.registration.target for route in routes), "targets"),
    ):
        materialized = tuple(field_values)
        if len(set(materialized)) != len(materialized):
            raise PaperReflectionRouteValidationError(
                f"Route-set {label} must be unique."
            )
    return routes


def validate_reflection_response_page_route(
    route: object,
) -> ReflectionResponsePageRoute:
    if not isinstance(route, ReflectionResponsePageRoute):
        raise PaperReflectionRouteValidationError(
            "route must be a ReflectionResponsePageRoute."
        )
    issuance, page = _issuance_page(route.issuance, route.page)
    expected_index = page.logical_page_number - 1
    if expected_index >= len(issuance.response_page_ids):
        raise PaperReflectionRouteValidationError(
            "Page number exceeds issuance response-page identities."
        )
    if issuance.response_page_ids[expected_index] != page.response_page_id:
        raise PaperReflectionRouteValidationError(
            "Page identity does not match issuance page order."
        )
    if not isinstance(route.locator, RouteLocator):
        raise PaperReflectionRouteValidationError("locator is invalid.")
    if not isinstance(route.registration, RouteRegistration):
        raise PaperReflectionRouteValidationError("registration is invalid.")

    expected_locator = RouteLocator(
        schema=PDS2_SCHEMA,
        work=ModuleWorkRef(
            module_id=VITRINE_MODULE_ID,
            class_id=page.class_id,
            work_id=page.work_id,
        ),
        route_id=page.route_id,
    )
    if route.locator != expected_locator:
        raise PaperReflectionRouteValidationError(
            "Locator does not identify the exact immutable response page route."
        )
    expected_registration = RouteRegistration(
        schema_version=ROUTE_REGISTRATION_SCHEMA_VERSION,
        locator=expected_locator,
        target=reflection_response_page_target(page),
        created_at=page.created_at.isoformat(),
        status="active",
        human_fallback=reflection_response_page_human_fallback(issuance, page),
        module_details=reflection_response_page_module_details(issuance, page),
    )
    if route.registration != expected_registration:
        raise PaperReflectionRouteValidationError(
            "Registration contradicts immutable issuance/page context."
        )
    try:
        canonical = serialize_pds2_payload(expected_locator)
        parsed = parse_pds2_payload(route.payload_text)
    except (RoutingModelError, Pds2PayloadError) as error:
        raise PaperReflectionRouteValidationError(str(error)) from error
    if route.payload_text != canonical or parsed != expected_locator:
        raise PaperReflectionRouteValidationError(
            "PDS2 payload does not round-trip to the exact locator."
        )
    return route


def _issuance_page(
    issuance: object,
    page: object,
) -> tuple[ReflectionPromptIssuance, ReflectionResponsePage]:
    if not isinstance(issuance, ReflectionPromptIssuance):
        raise PaperReflectionRouteValidationError(
            "issuance must be a ReflectionPromptIssuance."
        )
    if not isinstance(page, ReflectionResponsePage):
        raise PaperReflectionRouteValidationError(
            "page must be a ReflectionResponsePage."
        )
    if page.issuance_id != issuance.issuance_id:
        raise PaperReflectionRouteValidationError(
            "page.issuance_id must equal issuance.issuance_id."
        )
    if page.class_id != issuance.student_reference.class_id:
        raise PaperReflectionRouteValidationError(
            "Page class must equal the issuance class-qualified student class."
        )
    if page.total_pages != len(issuance.response_page_ids):
        raise PaperReflectionRouteValidationError(
            "Page total_pages must equal issuance response-page count."
        )
    return issuance, page


__all__ = [
    "PaperReflectionRouteError",
    "PaperReflectionRouteValidationError",
    "REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION",
    "REFLECTION_RESPONSE_PAGE_RECORD_KIND",
    "ReflectionResponsePageRoute",
    "build_reflection_response_page_route",
    "build_reflection_response_route_set",
    "reflection_response_page_human_fallback",
    "reflection_response_page_module_details",
    "reflection_response_page_target",
    "validate_reflection_response_page_route",
]
