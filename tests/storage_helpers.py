from __future__ import annotations

from vitrine.models import VitrineRecord, VitrineRecordGraph


def flatten_graph(graph: VitrineRecordGraph) -> tuple[VitrineRecord, ...]:
    return tuple(
        record
        for field_name in graph.__dataclass_fields__
        for record in getattr(graph, field_name)
    )


def improvement_base_graph(graph: VitrineRecordGraph) -> VitrineRecordGraph:
    return VitrineRecordGraph(
        portfolios=graph.portfolios,
        portfolio_subjects=graph.portfolio_subjects,
        subject_links=graph.subject_links,
        profile_families=graph.profile_families,
        profile_revisions=graph.profile_revisions,
        profile_bindings=graph.profile_bindings,
        candidate_evaluations=graph.candidate_evaluations,
        candidates=graph.candidates,
        selections=graph.selections,
        placements=graph.placements,
        arrangements=graph.arrangements,
        compositions=graph.compositions,
        audience_contexts=graph.audience_contexts,
    )


def snapshot_records(graph: VitrineRecordGraph) -> tuple[VitrineRecord, ...]:
    names = (
        "materializations",
        "snapshot_entries",
        "snapshot_omissions",
        "snapshot_manifests",
        "snapshot_seals",
        "snapshot_editions",
    )
    return tuple(record for name in names for record in getattr(graph, name))
