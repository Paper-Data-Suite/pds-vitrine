"""Exercise Vitrine canonical persistence in a disposable Core workspace."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine.models import VitrineRecord, VitrineRecordGraph, graph_from_json_bytes
from vitrine.storage import (
    VitrineStorageConflictError,
    audit_canonical_storage,
    catalog_path,
    commit_record_batch,
    load_current_record_graph,
    load_state_revision,
    query_catalog_records,
    rebuild_catalog,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "runtime-models"
    / "improvement-foundational-records-v1.json"
)
SNAPSHOT_COLLECTIONS = (
    "materializations",
    "snapshot_entries",
    "snapshot_omissions",
    "snapshot_manifests",
    "snapshot_seals",
    "snapshot_editions",
)


def _flatten(graph: VitrineRecordGraph) -> tuple[VitrineRecord, ...]:
    return tuple(
        record
        for field_name in graph.__dataclass_fields__
        for record in getattr(graph, field_name)
    )


def _base_graph(graph: VitrineRecordGraph) -> VitrineRecordGraph:
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


def validate() -> None:
    graph = graph_from_json_bytes(FIXTURE.read_bytes())
    base = _base_graph(graph)
    snapshot_records = tuple(
        record for name in SNAPSHOT_COLLECTIONS for record in getattr(graph, name)
    )

    with tempfile.TemporaryDirectory(prefix="vitrine-storage-validation-") as temporary:
        workspace = ensure_workspace_root(Path(temporary) / "workspace", create=True)
        first = commit_record_batch(
            workspace,
            _flatten(base),
            expected_state_revision=None,
        )
        if first.state_revision != 1 or first.no_op:
            raise RuntimeError("bootstrap did not publish state revision 1")

        second = commit_record_batch(
            workspace,
            snapshot_records,
            expected_state_revision=1,
        )
        if second.state_revision != 2 or second.no_op:
            raise RuntimeError("advancing commit did not publish state revision 2")

        replay = commit_record_batch(
            workspace,
            snapshot_records,
            expected_state_revision=2,
        )
        if not replay.no_op or replay.state_revision != 2:
            raise RuntimeError("exact replay was not a state-preserving no-op")

        try:
            commit_record_batch(
                workspace,
                snapshot_records,
                expected_state_revision=1,
            )
        except VitrineStorageConflictError:
            pass
        else:
            raise RuntimeError("stale expected state did not conflict")

        _, _, historical = load_state_revision(workspace, 1)
        if historical != base:
            raise RuntimeError("historical state revision did not reconstruct exactly")
        current = load_current_record_graph(workspace)
        if current.state_revision != 2 or current.graph != graph:
            raise RuntimeError("current canonical graph did not reconstruct exactly")
        if audit_canonical_storage(workspace):
            raise RuntimeError("canonical audit returned findings for valid storage")

        rebuilt = rebuild_catalog(workspace)
        rows = query_catalog_records(workspace, state="current")
        if not rebuilt.is_file() or len(rows) != len(_flatten(graph)):
            raise RuntimeError("derived catalog did not index the complete current graph")
        catalog_path(workspace).unlink()
        if load_current_record_graph(workspace).graph != graph:
            raise RuntimeError("canonical reads depended on the derived catalog")


def main() -> int:
    try:
        validate()
        print("PASS canonical Vitrine storage validation")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Canonical storage validation failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
