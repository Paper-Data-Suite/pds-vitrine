"""Issue #104: compose fixture-backed improvement and reader-contract acceptance.

This is a source-checkout acceptance gate, NOT installed-wheel qualification.
The exact-wheel release audit remains a separate, reproducible qualification.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A single suite covers all three producer public-model projections and the
# future Quillan reader through persisted Candidate/Selection/Placement. The
# representative fixture-backed journey and presentation stay explicitly named.
FOCUSED_TESTS: tuple[str, ...] = (
    "tests/test_issue103_reader_contract_compatibility.py",
    "tests/test_quillan_adapter.py",
    "tests/test_scoreform_adapter.py",
    "tests/test_concord_adapter.py",
    "tests/test_portfolio_completion_issue103.py",
    "tests/test_attention_completion_issue103.py",
    "tests/test_completed_portfolio_history_issue102.py",
    "tests/test_candidate_evidence_review_acceptance.py",
    "tests/test_portfolio_presentation_end_to_end_issue101.py",
    "tests/test_validate_issue104_acceptance.py",
)

REQUIRED_TEST_FUNCTIONS: dict[str, tuple[str, ...]] = {
    "tests/test_issue103_reader_contract_compatibility.py": (
        "test_issue104_future_producer_release_calls_public_reader",
        "test_issue104_future_producer_contract_failure_is_closed",
        "test_issue104_pre_metadata_fallback_is_exact",
    ),
    "tests/test_quillan_adapter.py": (
        "test_issue104_future_quillan_reader_projects_public_candidate_evidence",
        "test_issue104_future_quillan_canonical_candidate_and_guided_curation",
    ),
    "tests/test_scoreform_adapter.py": (
        "test_multiple_attempts_survive_without_selection_or_ranking_semantics",
        "test_response_states_presence_and_correctness_remain_distinct",
        (
            "test_assignment_question_and_standard_alignment_metadata_is_"
            "preserved_without_ratings"
        ),
    ),
    "tests/test_concord_adapter.py": (
        "test_projection_preserves_criterion_scale_and_activity_context",
        (
            "test_score_projection_is_pure_summary_without_source_locator_"
            "or_grade_semantics"
        ),
    ),
    "tests/test_portfolio_completion_issue103.py": (
        "test_issue104_combined_recovery_and_integrity_keep_completed_history_visible",
        "test_issue104_operational_blockers_override_update_ready",
    ),
    "tests/test_attention_completion_issue103.py": (
        "test_issue104_attention_preserves_completion_and_teacher_next_action",
        "test_v2_evaluator_reports_complete_and_optional_extra_evidence",
    ),
    "tests/test_completed_portfolio_history_issue102.py": (
        "test_current_status_comes_only_from_exact_pointer_not_newest_edition",
    ),
    "tests/test_portfolio_presentation_end_to_end_issue101.py": (
        (
            "test_representative_improvement_portfolio_becomes_verified_"
            "student_presentation"
        ),
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    matching = tuple(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    _require(len(matching) == 1, f"Expected exactly one function {name!r}")
    return matching[0]


def _validate_version_policy_source(source: str) -> None:
    """Guard the semantic resolver: only exact *legacy* release membership.

    This is an architectural regression guard, not a replacement for runtime
    version/metadata parametrized tests. Any new semantic resolver requires a
    deliberate update to this bounded guard and its test suite.
    """

    tree = ast.parse(source)
    resolver = _function_node(tree, "resolve_installed_producer_reader_compatibility")
    allowed_legacy_checks = 0
    for node in ast.walk(resolver):
        if isinstance(node, ast.Attribute) and node.attr in {
            "release_version",
            "wheel_sha256",
            "wheel_filename",
        }:
            raise RuntimeError(
                "Runtime reader compatibility references exact-release audit identity"
            )
        if not isinstance(node, ast.Compare):
            continue
        version_used = any(
            isinstance(item, ast.Name) and item.id == "installed_distribution_version"
            for item in ast.walk(node)
        )
        if not version_used:
            continue
        exact_legacy = (
            len(node.ops) == 1
            and isinstance(node.ops[0], ast.In)
            and isinstance(node.left, ast.Name)
            and node.left.id == "installed_distribution_version"
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Name)
            and node.comparators[0].id == "legacy"
        )
        if not exact_legacy:
            raise RuntimeError(
                "Installed distribution version is being used for semantic "
                "compatibility outside the bounded exact-legacy fallback"
            )
        allowed_legacy_checks += 1
    _require(
        allowed_legacy_checks == 1,
        "Reader compatibility must retain one bounded exact-legacy check",
    )
    calls = {
        node.func.id
        for node in ast.walk(resolver)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    _require(
        "lookup_publication_reader_support" in calls,
        "Runtime semantic reader lookup no longer uses Core metadata",
    )


def _validate_reader_service_source(source: str) -> None:
    tree = ast.parse(source)
    readers = tuple(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef)
        and item.name == "InstalledProducerManifestReader"
    )
    _require(len(readers) == 1, "Installed producer reader boundary is missing")
    read = tuple(
        item
        for item in readers[0].body
        if isinstance(item, ast.FunctionDef) and item.name == "read"
    )
    _require(len(read) == 1, "Installed reader's public read operation is missing")
    attributes = {
        item.attr for item in ast.walk(read[0]) if isinstance(item, ast.Attribute)
    }
    _require(
        not (attributes & {"release_version", "wheel_sha256", "wheel_filename"}),
        "Installed public reader compares exact-wheel release audit properties",
    )
    calls = {
        item.func.id
        for item in ast.walk(read[0])
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
    }
    _require(
        "resolve_installed_producer_reader_compatibility" in calls,
        "Installed public reader bypasses the semantic compatibility boundary",
    )


def _validate_contracts_and_inventory() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    _require(
        project["project"]["dependencies"] == ["pds-core>=0.6.5,<0.7"],
        "Base installation must depend only on Core >=0.6.5,<0.7",
    )
    _validate_version_policy_source(
        (ROOT / "vitrine/producer_reader_compatibility.py").read_text(
            encoding="utf-8"
        )
    )
    _validate_reader_service_source(
        (ROOT / "vitrine/producer_reader_services.py").read_text(encoding="utf-8")
    )
    for relative in FOCUSED_TESTS:
        _require((ROOT / relative).is_file(), f"Missing #104 test {relative}")
    for relative, functions in REQUIRED_TEST_FUNCTIONS.items():
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        for name in functions:
            _require(name in names, f"Missing #104 acceptance case: {relative}:{name}")
    _require(
        (ROOT / "scripts/validate_improvement_portfolio.py").is_file(),
        "The primary synthetic Improvement Portfolio journey is unavailable",
    )


def _run_command(arguments: tuple[str, ...]) -> None:
    print("+", " ".join(arguments), flush=True)
    subprocess.run(arguments, cwd=ROOT, check=True)


def validate(
    *,
    run_focused_tests: bool = True,
    run_synthetic_journey: bool = True,
) -> None:
    """Run source-only acceptance without modifying the repository or corpus."""

    _validate_contracts_and_inventory()
    if run_synthetic_journey:
        _run_command((sys.executable, "scripts/validate_improvement_portfolio.py"))
    if run_focused_tests:
        _run_command((sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    parser.add_argument("--skip-synthetic-journey", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(
            run_focused_tests=not args.skip_focused_tests,
            run_synthetic_journey=not args.skip_synthetic_journey,
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
        SyntaxError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Issue #104 acceptance failed: {error}", file=sys.stderr)
        return 1
    print("PASS Issue #104 fixture journey and stable reader-contract acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
