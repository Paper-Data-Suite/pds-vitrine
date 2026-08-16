"""Shared dependency context for direct and teacher-facing workflows."""

from __future__ import annotations

from dataclasses import dataclass

from pds_core.publication_compatibility import PublicationProducerRegistry

from vitrine.candidate_services import (
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationGate,
    SourceReadAuthorizationRequest,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityGate,
    CurationAuthorityRequest,
)
from vitrine.producer_adapters import ProducerProjectionAdapterRegistry
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityGate,
    SnapshotBuildAuthorityRequest,
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_planning import (
    SnapshotPlanningProvider,
    UnconfiguredSnapshotPlanningProvider,
)


class _UnresolvedSourceGate:
    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        return SourceReadAuthorizationDecision(
            outcome="unresolved", reason_codes=("integration_unconfigured",)
        )


class _UnresolvedCurationGate:
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        return CurationAuthorityDecision(
            outcome="unresolved", reason_codes=("integration_unconfigured",)
        )


class _UnresolvedSnapshotGate:
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome="unresolved", reason_codes=("integration_unconfigured",)
        )


@dataclass(frozen=True, slots=True)
class VitrineWorkflowDependencies:
    """One explicit provider set shared by every presentation surface."""

    producer_registry: PublicationProducerRegistry
    adapter_registry: ProducerProjectionAdapterRegistry
    source_read_authorization_gate: SourceReadAuthorizationGate
    curation_authority_gate: CurationAuthorityGate
    snapshot_build_authority_gate: SnapshotBuildAuthorityGate
    snapshot_source_providers: SnapshotSourceProviderRegistry
    snapshot_renderers: SnapshotRendererRegistry
    snapshot_planning_provider: SnapshotPlanningProvider = (
        UnconfiguredSnapshotPlanningProvider()
    )
    development_fixture_mode: bool = False


def default_workflow_dependencies() -> VitrineWorkflowDependencies:
    """Return a fail-closed production context with no implicit integrations."""
    return VitrineWorkflowDependencies(
        producer_registry=PublicationProducerRegistry(profiles=()),
        adapter_registry=ProducerProjectionAdapterRegistry(),
        source_read_authorization_gate=_UnresolvedSourceGate(),
        curation_authority_gate=_UnresolvedCurationGate(),
        snapshot_build_authority_gate=_UnresolvedSnapshotGate(),
        snapshot_source_providers=SnapshotSourceProviderRegistry(),
        snapshot_renderers=SnapshotRendererRegistry(),
        snapshot_planning_provider=UnconfiguredSnapshotPlanningProvider(),
    )


__all__ = ["VitrineWorkflowDependencies", "default_workflow_dependencies"]
