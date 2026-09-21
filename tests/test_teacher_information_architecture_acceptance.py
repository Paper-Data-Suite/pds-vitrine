from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ACCEPTANCE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {
    "A_portfolio_overview_teacher_readable": {
        "tests/test_teacher_presentation.py": (
            "test_default_portfolio_overview_prioritizes_teacher_context",
            "test_portfolio_technical_details_preserve_exact_provenance",
        ),
    },
    "B_explicit_subject_navigation": {
        "tests/test_portfolio_menu.py": (
            "test_overview_subject_details_require_explicit_action",
            "test_portfolio_subject_route_uses_exact_subject_id",
        ),
    },
    "C_provenance_preserved_secondary": {
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_technical_details_preserve_bounded_provenance",
        ),
        "tests/test_candidate_review_menu.py": (
            "test_guided_review_detail_is_teacher_first_with_explicit_technical_view",
        ),
        "tests/test_working_composition_menu.py": (
            "test_preparation_technical_details_preserve_exact_provenance",
            "test_frozen_composition_default_hides_exact_identity_but_technical_preserves_it",
        ),
        "tests/test_current_portfolio_menu.py": (
            "test_success_result_is_teacher_first_and_technical_preserves_ids",
        ),
        "tests/test_attention_menu.py": (
            "test_attention_menu_technical_details_preserve_exact_projection",
        ),
    },
    "D_candidate_default_hierarchy": {
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_lists_and_inspects_read_only",
            "test_candidate_inbox_menu_technical_details_preserve_bounded_provenance",
        ),
    },
    "E_candidate_review_decision_first": {
        "tests/test_candidate_review_menu.py": (
            "test_guided_review_detail_is_teacher_first_with_explicit_technical_view",
            "test_guided_menu_fresh_select_uses_numbered_section_and_shared_orchestration",
        ),
    },
    "F_working_composition_meaning_first": {
        "tests/test_working_composition_menu.py": (
            "test_guided_menu_prepares_read_only_and_renders_exact_section_order",
            "test_preparation_technical_details_preserve_exact_provenance",
        ),
    },
    "G_attention_teacher_language": {
        "tests/test_attention_menu.py": (
            "test_attention_menu_renders_bounded_next_action_without_mutation",
            "test_attention_menu_technical_details_preserve_exact_projection",
        ),
    },
    "H_display_values_not_authority": {
        "tests/test_portfolio_menu.py": (
            "test_duplicate_portfolio_labels_use_exact_id_only_for_disambiguation",
            "test_portfolio_subject_route_uses_exact_subject_id",
            "test_profile_migration_preserves_exact_observed_revision",
        ),
        "tests/test_candidate_inbox_acceptance.py": (
            "test_selection_provenance_does_not_retarget_when_pointer_advances",
        ),
        "tests/test_candidate_current_evaluation.py": (
            "test_explicit_pointer_successor_follows_evaluation_lineage",
        ),
        "tests/test_current_portfolio_execution.py": (
            "test_revalidation_uses_exact_prepared_choices_and_provider_registry",
        ),
        "tests/test_profile_services.py": (
            "test_showcase_profile_is_explicit_policy_not_authorization",
        ),
    },
    "I_details_are_observational": {
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_lists_and_inspects_read_only",
            "test_candidate_inbox_menu_technical_details_preserve_bounded_provenance",
        ),
        "tests/test_candidate_review_actions.py": (
            "test_action_plan_requires_explicit_fresh_section_intent_and_is_read_only",
        ),
        "tests/test_working_composition_menu.py": (
            "test_guided_menu_prepares_read_only_and_renders_exact_section_order",
        ),
        "tests/test_attention_menu.py": (
            "test_attention_menu_technical_details_preserve_exact_projection",
        ),
    },
    "J_privacy_boundaries": {
        "tests/test_candidate_inbox.py": (
            "test_suppressed_head_is_removed_before_counts_and_filters",
            "test_suppressed_entry_cannot_be_retrieved_by_detail",
        ),
        "tests/test_candidate_review.py": (
            "test_suppressed_evaluation_remains_absent_from_guided_review_list",
        ),
    },
}


def _test_functions(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def test_issue95_acceptance_matrix_points_to_real_behavior_tests() -> None:
    referenced: set[tuple[str, str]] = set()
    assert set(ACCEPTANCE_MATRIX) == {
        "A_portfolio_overview_teacher_readable",
        "B_explicit_subject_navigation",
        "C_provenance_preserved_secondary",
        "D_candidate_default_hierarchy",
        "E_candidate_review_decision_first",
        "F_working_composition_meaning_first",
        "G_attention_teacher_language",
        "H_display_values_not_authority",
        "I_details_are_observational",
        "J_privacy_boundaries",
    }

    for group, files in ACCEPTANCE_MATRIX.items():
        assert files, f"acceptance group {group} has no behavior tests"
        for relative, expected_tests in files.items():
            path = ROOT / relative
            assert path.is_file(), f"missing acceptance test file: {relative}"
            available = _test_functions(path)
            for test_name in expected_tests:
                assert test_name in available, (
                    f"acceptance group {group} lost behavior test "
                    f"{relative}::{test_name}"
                )
                referenced.add((relative, test_name))

    assert len(referenced) >= 20
