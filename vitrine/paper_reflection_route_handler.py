"""Non-mutating Core route resolver for Vitrine Reflection response pages."""

from __future__ import annotations

from pds_core.routing_models import RouteResolution
from pds_core.scan_retention import RetainedSourceScan

from vitrine.models import ReflectionPromptIssuance, ReflectionResponsePage
from vitrine.paper_reflection_routes import (
    build_reflection_response_page_route,
    reflection_response_page_target,
)
from vitrine.pds_module import validate_vitrine_registration
from vitrine.storage import VitrineStorageError, load_current_records


class VitrineReflectionRouteContextError(RuntimeError):
    """Raised when a resolved Reflection route contradicts canonical Vitrine state."""


def handle_vitrine_reflection_response_page_route(
    resolution: RouteResolution,
    retained_source: RetainedSourceScan,
    source_page_number: int,
    /,
) -> ReflectionResponsePage:
    """Resolve one route to its immutable page without mutating Vitrine state.

    This slice deliberately stops before retained-paper evidence capture. The
    retained source is type-checked here so the installed Core handler contract
    is real, while later #99 slices will create evidence from that source.
    """

    if not isinstance(resolution, RouteResolution):
        raise VitrineReflectionRouteContextError(
            "resolution must be a RouteResolution."
        )
    if not isinstance(retained_source, RetainedSourceScan):
        raise VitrineReflectionRouteContextError(
            "retained_source must be a RetainedSourceScan."
        )
    if (
        isinstance(source_page_number, bool)
        or not isinstance(source_page_number, int)
        or source_page_number < 1
    ):
        raise VitrineReflectionRouteContextError(
            "source_page_number must be a positive non-Boolean integer."
        )
    try:
        validate_vitrine_registration(resolution.registration)
        workspace_root = resolution.class_root.parent.parent
        records = load_current_records(workspace_root)
    except (ValueError, VitrineStorageError) as error:
        raise VitrineReflectionRouteContextError(
            "Resolved Vitrine route cannot be validated against canonical state."
        ) from error

    target = resolution.registration.target
    pages = tuple(
        item
        for item in records
        if isinstance(item, ReflectionResponsePage)
        and item.response_page_id == target.record_id
    )
    if len(pages) != 1:
        raise VitrineReflectionRouteContextError(
            "Registered Reflection response page is missing or ambiguous."
        )
    page = pages[0]
    issuances = tuple(
        item
        for item in records
        if isinstance(item, ReflectionPromptIssuance)
        and item.issuance_id == page.issuance_id
    )
    if len(issuances) != 1:
        raise VitrineReflectionRouteContextError(
            "Response page issuance is missing or ambiguous."
        )
    expected = build_reflection_response_page_route(issuances[0], page)
    if (
        resolution.locator != expected.locator
        or resolution.registration != expected.registration
        or target != reflection_response_page_target(page)
    ):
        raise VitrineReflectionRouteContextError(
            "Resolved Core route contradicts immutable Vitrine page context."
        )
    return page


__all__ = [
    "VitrineReflectionRouteContextError",
    "handle_vitrine_reflection_response_page_route",
]
