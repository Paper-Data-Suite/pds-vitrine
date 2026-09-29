"""Installed Core routing profile for Vitrine paper-native Reflection pages."""

from __future__ import annotations

import re
from typing import Final

from pds_core.identifiers import validate_identifier
from pds_core.module_profiles import (
    CORE_ROUTING_CONTRACT_VERSION,
    ModuleProfile,
    validate_module_profile,
)
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    RouteRegistration,
    validate_route_registration,
)

from vitrine.constants import VITRINE_MODULE_ID
from vitrine.paper_reflection_routes import (
    REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION,
    REFLECTION_RESPONSE_PAGE_RECORD_KIND,
)

VITRINE_DISPLAY_NAME: Final[str] = "Vitrine"
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
_FALLBACK: Final[re.Pattern[str]] = re.compile(
    r"Vitrine Reflection \| class=([^ |]+) \| work=([^ |]+) "
    r"\| expected_student=([^ |]+) \| page=([0-9]+)/([0-9]+) "
    r"\| page_id=([^ |]+)"
)


class VitrineRegistrationValidationError(ValueError):
    """Raised when a Vitrine route registration violates its module contract."""


def validate_vitrine_registration(registration: RouteRegistration, /) -> None:
    """Validate one Vitrine Reflection response-page registration."""

    try:
        if not isinstance(registration, RouteRegistration):
            raise ValueError("registration must be a RouteRegistration.")
        validate_route_registration(registration)
        if registration.schema_version != ROUTE_REGISTRATION_SCHEMA_VERSION:
            raise ValueError("registration schema_version must be '1'.")
        locator = registration.locator
        if locator.schema != PDS2_SCHEMA:
            raise ValueError("locator schema must be 'PDS2'.")
        if locator.module_id != VITRINE_MODULE_ID:
            raise ValueError("locator module_id must be 'vitrine'.")
        if registration.status != "active":
            raise ValueError("registration status must be 'active'.")

        target = registration.target
        if target.module_id != VITRINE_MODULE_ID:
            raise ValueError("target module_id must be 'vitrine'.")
        if target.record_kind != REFLECTION_RESPONSE_PAGE_RECORD_KIND:
            raise ValueError(
                "target record_kind must be 'reflection_response_page'."
            )
        if target.contract_version != REFLECTION_RESPONSE_PAGE_CONTRACT_VERSION:
            raise ValueError("target contract_version must be '1'.")
        validate_identifier(target.record_id, "response_page_id")

        details = registration.module_details
        if frozenset(details) != _DETAIL_KEYS:
            raise ValueError("module_details keys do not match the Vitrine contract.")
        for key in (
            "issuance_id",
            "portfolio_id",
            "portfolio_subject_id",
            "subject_link_id",
            "expected_student_id",
            "school_year",
            "reflection_requirement_id",
        ):
            value = details[key]
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string.")
            validate_identifier(value, key)
        logical_page = _positive_integer(details["logical_page"], "logical_page")
        total_pages = _positive_integer(details["total_pages"], "total_pages")
        if logical_page > total_pages:
            raise ValueError("logical_page must not exceed total_pages.")

        match = _FALLBACK.fullmatch(registration.human_fallback)
        if match is None:
            raise ValueError(
                "human_fallback does not use Vitrine's exact Reflection grammar."
            )
        class_id, work_id, student_id, logical, total, page_id = match.groups()
        validate_identifier(class_id, "fallback class_id")
        validate_identifier(work_id, "fallback work_id")
        validate_identifier(student_id, "fallback expected_student_id")
        validate_identifier(page_id, "fallback response_page_id")
        if class_id != locator.class_id:
            raise ValueError("fallback class does not match locator class.")
        if work_id != locator.work_id:
            raise ValueError("fallback work does not match locator work.")
        if student_id != details["expected_student_id"]:
            raise ValueError(
                "fallback expected student does not match module_details."
            )
        if page_id != target.record_id:
            raise ValueError("fallback page_id does not match target.")
        if logical != str(logical_page) or total != str(total_pages):
            raise ValueError(
                "fallback page meaning does not match module_details."
            )
    except VitrineRegistrationValidationError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError) as error:
        raise VitrineRegistrationValidationError(
            f"Invalid Vitrine route registration: {error}"
        ) from error


def _positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive non-Boolean integer.")
    return value


def get_module_profile() -> ModuleProfile:
    """Return Vitrine's validated Core routing profile."""

    from vitrine.paper_reflection_route_handler import (
        handle_vitrine_reflection_response_page_route,
    )

    return validate_module_profile(
        ModuleProfile(
            module_id=VITRINE_MODULE_ID,
            display_name=VITRINE_DISPLAY_NAME,
            supported_core_routing_contract_versions=frozenset(
                {CORE_ROUTING_CONTRACT_VERSION}
            ),
            supported_qr_schemas=frozenset({PDS2_SCHEMA}),
            supported_route_registration_schema_versions=frozenset(
                {ROUTE_REGISTRATION_SCHEMA_VERSION}
            ),
            dispatchable_route_statuses=frozenset({"active"}),
            route_handler=handle_vitrine_reflection_response_page_route,
            registration_validator=validate_vitrine_registration,
        )
    )


__all__ = [
    "VitrineRegistrationValidationError",
    "get_module_profile",
    "validate_vitrine_registration",
]
