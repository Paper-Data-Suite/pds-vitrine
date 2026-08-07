from dataclasses import replace

from tests.runtime_fixture_factory import make_improvement_graph, make_showcase_graph
from vitrine.models import collect_record_graph_issues, validate_record_graph


def test_improvement_and_showcase_graphs_validate() -> None:
    validate_record_graph(make_improvement_graph())
    validate_record_graph(make_showcase_graph())


def test_missing_subject_is_reported_with_stable_code() -> None:
    graph = make_improvement_graph()
    invalid = replace(graph, portfolio_subjects=())
    codes = {issue.code for issue in collect_record_graph_issues(invalid)}
    assert "portfolio.subject_missing" in codes


def test_candidate_context_mismatch_is_reported() -> None:
    graph = make_improvement_graph()
    candidate = graph.candidates[0]
    invalid_candidate = replace(candidate, portfolio_id="another_portfolio")
    invalid = replace(graph, candidates=(invalid_candidate, graph.candidates[1]))
    codes = {issue.code for issue in collect_record_graph_issues(invalid)}
    assert "candidate.evaluation_context_mismatch" in codes


def test_duplicate_snapshot_path_is_reported() -> None:
    graph = make_showcase_graph()
    duplicate = replace(
        graph.snapshot_entries[1],
        relative_path=graph.snapshot_entries[0].relative_path,
    )
    invalid = replace(graph, snapshot_entries=(graph.snapshot_entries[0], duplicate))
    codes = {issue.code for issue in collect_record_graph_issues(invalid)}
    assert "snapshot.entry_path_duplicate" in codes


def test_snapshot_entry_materialization_edition_mismatch_is_reported() -> None:
    graph = make_showcase_graph()
    entry = graph.snapshot_entries[0]
    other_ref = replace(entry.snapshot_edition, edition_number=2)
    invalid_entry = replace(entry, snapshot_edition=other_ref)
    invalid = replace(
        graph,
        snapshot_entries=(invalid_entry, *graph.snapshot_entries[1:]),
    )
    codes = {issue.code for issue in collect_record_graph_issues(invalid)}
    assert "snapshot.entry_materialization_mismatch" in codes
