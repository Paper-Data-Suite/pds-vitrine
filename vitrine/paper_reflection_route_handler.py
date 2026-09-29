"""Core route handler for Vitrine Reflection returned-paper evidence."""

from __future__ import annotations

from pds_core.routing_models import RouteResolution
from pds_core.scan_retention import RetainedSourceScan

from vitrine.models import ReflectionReturnedPaperEvidence
from vitrine.paper_reflection_evidence import capture_returned_paper_evidence


def handle_vitrine_reflection_response_page_route(
    resolution: RouteResolution,
    retained_source: RetainedSourceScan,
    source_page_number: int,
    /,
) -> ReflectionReturnedPaperEvidence:
    """Capture one routed Core-retained page as immutable Vitrine evidence."""

    return capture_returned_paper_evidence(
        resolution,
        retained_source,
        source_page_number,
    )


__all__ = ["handle_vitrine_reflection_response_page_route"]
