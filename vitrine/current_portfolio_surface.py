"""Shared teacher-facing presentation for Current Portfolio build preparation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TextIO

from vitrine.current_portfolio_build import CurrentPortfolioBuildPreparation


def _joined(values: Iterable[str]) -> str:
    items = tuple(values)
    return ", ".join(items) if items else "(none)"


def current_portfolio_preparation_lines(
    preparation: CurrentPortfolioBuildPreparation,
) -> tuple[str, ...]:
    """Render the exact reviewed first-party policy without adding semantics."""

    rule = preparation.selected_audience_rule
    context = preparation.audience_context
    series = preparation.snapshot_series
    lines: list[str] = [
        "Build and Export Current Portfolio",
        "",
        f"Contract: {preparation.contract_version}",
        f"Preparation fingerprint: {preparation.preparation_fingerprint}",
        f"Observed Vitrine state revision: {preparation.observed_state_revision}",
        f"Portfolio: {preparation.portfolio_id}",
        f"Portfolio Subject: {preparation.portfolio_subject_id}",
        f"Profile Binding: {preparation.profile_binding_id}",
        (
            "Profile Revision: "
            f"{preparation.profile_revision_id}:"
            f"{preparation.profile_revision_number}"
        ),
        (
            "Current Working Composition: "
            f"{preparation.current_composition_revision or '(none)'}"
        ),
        (
            "Composition pointer revision: "
            f"{preparation.current_composition_pointer_revision or '(none)'}"
        ),
        (
            "Working Composition disposition: "
            f"{preparation.working_composition_disposition}"
        ),
        "",
        "Audience Rule",
        f"  Rule ID: {rule.audience_rule_id}",
        f"  Audience class: {rule.audience_class}",
        f"  Purpose: {rule.purpose}",
        f"  Allowed content classes: {_joined(rule.allowed_content_classes)}",
        f"  Prohibited content classes: {_joined(rule.prohibited_content_classes)}",
        f"  Required review classes: {_joined(rule.required_review_classes)}",
        f"  Presentation class: {rule.presentation_class}",
        (
            "  Retention policy: "
            f"{rule.retention_policy_reference or '(none)'}"
        ),
        "  This rule constrains content; it is not recipient or disclosure authority.",
        "",
        "Audience Context",
        f"  Disposition: {context.disposition}",
        (
            "  Exact matches: "
            f"{_joined(context.matching_audience_context_ids)}"
        ),
        (
            "  Selected Context: "
            f"{context.selected_audience_context_id or '(none)'}"
        ),
        "",
        "Snapshot Series",
        f"  Disposition: {series.disposition}",
        f"  Exact matches: {_joined(series.matching_snapshot_series_ids)}",
        (
            "  Selected Series: "
            f"{series.selected_snapshot_series_id or '(none)'}"
        ),
    ]
    if series.resolution_deferred_for_audience_context:
        lines.append("  Series resolution is deferred until exact Context choice.")

    lines.extend(("", "Required Reviews"))
    if preparation.required_reviews:
        for review in preparation.required_reviews:
            lines.extend(
                (
                    f"  {review.review_class}: "
                    f"{'satisfied' if review.satisfied else 'missing'}",
                    (
                        "    Profile requirements: "
                        f"{_joined(review.profile_requirement_ids)}"
                    ),
                    (
                        "    Exact satisfying Reviews: "
                        f"{_joined(review.satisfying_review_decision_ids)}"
                    ),
                )
            )
    else:
        lines.append("  (none required)")
    lines.append(
        "  Missing required review classes: "
        f"{_joined(preparation.missing_required_review_classes)}"
    )

    lines.extend(("", "Unresolved Composition Obligations"))
    lines.append(f"  Unresolved: {_joined(preparation.unresolved_obligation_codes)}")
    lines.append(
        "  Acknowledged for this Plan: "
        f"{_joined(preparation.acknowledged_obligation_codes)}"
    )
    lines.append(
        "  Acknowledgement preserves unresolved state; it does not satisfy it."
    )

    lines.extend(("", "Source-backed items"))
    if not preparation.planned_items:
        lines.append("  (none)")
    for plan in preparation.planned_items:
        artifact = plan.source_artifact
        artifact_id = artifact.artifact_id if artifact is not None else "(none)"
        artifact_kind = artifact.artifact_kind if artifact is not None else "(none)"
        representation = (
            artifact.representation_kind if artifact is not None else "(none)"
        )
        lines.extend(
            (
                (
                    f"  {plan.plan_position}. {plan.section_label} / "
                    f"position {plan.position_in_section}"
                ),
                (
                    f"    Placement {plan.placement_id}; Selection "
                    f"{plan.selection_id}; Candidate {plan.candidate_id}"
                ),
                f"    Candidate Evaluation: {plan.candidate_evaluation_id}",
                f"    Core Publication: {plan.source_publication_id}",
                (
                    f"    Producer/projection: {plan.producer_module_id} / "
                    f"{plan.projection_kind} / "
                    f"{plan.projection_contract_version}"
                ),
                (
                    f"    Artifact: {artifact_id} / {artifact_kind} / "
                    f"{representation}"
                ),
                f"    Source current-use state: {plan.source_current_use_state}",
                f"    Content class: {plan.content_class}",
                f"    Materialization: {plan.materialization_kind}",
                f"    Provider disposition: {plan.provider_disposition}",
                (
                    "    Provider: "
                    f"{plan.provider_id or '(none)'} / "
                    f"{plan.provider_version or '(none)'}"
                ),
                f"    Target path: {plan.target_relative_path or '(none)'}",
                f"    Media type: {plan.media_type or '(none/deferred)'}",
                f"    Export file: {'yes' if plan.export_file else 'no'}",
                (
                    "    Permitted omission: "
                    f"{plan.permitted_omission_reason or '(none)'}"
                ),
                f"    Policy: {plan.explanation}",
            )
        )

    lines.extend(("", "Generated Vitrine Reflections"))
    if not preparation.generated_reflections:
        lines.append("  (none)")
    for refl in preparation.generated_reflections:
        lines.extend(
            (
                (
                    f"  {refl.plan_position}. Reflection {refl.reflection_id}:"
                    f"{refl.reflection_revision}"
                ),
                (
                    "    Section: "
                    f"{refl.section_label or refl.section_id or '(unsupported)'}"
                ),
                f"    Requirement: {refl.reflection_requirement_id}",
                f"    Prompt: {refl.prompt_id}:{refl.prompt_version}",
                f"    Content mode/format: {refl.content_mode}/{refl.content_format}",
                f"    Language: {refl.language}",
                (
                    f"    Renderer: {refl.renderer_id}/{refl.renderer_version}/"
                    f"{refl.renderer_contract_version}"
                ),
                f"    Target path: {refl.target_relative_path or '(none)'}",
                f"    Media type: {refl.media_type or '(none)'}",
                f"    Export file: {'yes' if refl.export_file else 'no'}",
                f"    Supported: {'yes' if refl.supported else 'no'}",
                f"    Policy: {refl.explanation}",
            )
        )

    export = preparation.directory_export
    lines.extend(
        (
            "",
            "Directory Export Plan",
            f"  Export Plan ID: {export.export_plan_id}",
            f"  Format: {export.export_format}",
            f"  Contract: {export.export_contract_version}",
            (
                "  Included Entry Plans: "
                f"{_joined(export.included_entry_plan_ids)}"
            ),
            (
                "  Excluded Entry Plans: "
                f"{_joined(export.excluded_entry_plan_ids)}"
            ),
            f"  Configuration SHA-256: {export.configuration_sha256}",
            "",
            f"Warnings: {_joined(preparation.warnings)}",
            f"Blocking reasons: {_joined(preparation.blocking_reasons)}",
            "",
            "Verification is not disclosure permission.",
            "Export creation is not delivery or sending.",
        )
    )
    return tuple(lines)


def print_current_portfolio_preparation(
    preparation: CurrentPortfolioBuildPreparation,
    *,
    output: TextIO,
) -> None:
    for line in current_portfolio_preparation_lines(preparation):
        print(line, file=output)


__all__ = [
    "current_portfolio_preparation_lines",
    "print_current_portfolio_preparation",
]
