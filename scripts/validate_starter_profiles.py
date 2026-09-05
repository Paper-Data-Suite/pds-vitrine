"""Validate the frozen optional starter Portfolio Profile contract."""

from __future__ import annotations

import sys
from pathlib import Path

from vitrine.candidate_services import CANDIDATE_KIND_BY_ARTIFACT_KIND
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.starter_profiles import (
    STARTER_PORTFOLIO_PROFILE_IDS,
    STARTER_PROFILE_CANDIDATE_KINDS_V1,
    STARTER_PROFILE_CATALOG_CONTRACT_VERSION,
    STARTER_PROFILE_FAMILY_IDS,
    STARTER_PROFILE_IDS,
    STARTER_PROFILE_PACK_CONTRACT_VERSION,
    STARTER_PROFILE_PURPOSES,
    get_starter_profile_pack,
    list_starter_profile_packs,
    validate_starter_profile_pack,
)

EXPECTED = {
    "improvement_portfolio_v1": (
        "improvement",
        "vitrine_starter_improvement_family",
        "vitrine_starter_improvement",
        ("baseline", "later_evidence", "supporting_feedback", "reflection"),
        (
            "baseline_cardinality",
            "later_evidence_cardinality",
            "comparison_reflection",
            "teacher_review",
        ),
    ),
    "showcase_portfolio_v1": (
        "showcase",
        "vitrine_starter_showcase_family",
        "vitrine_starter_showcase",
        ("featured_work", "supporting_evidence", "reflection"),
        (
            "featured_work_cardinality",
            "showcase_reflection",
            "privacy_review",
            "rights_review",
            "accessibility_treatment",
            "collaborative_work_treatment",
            "final_curator_approval",
        ),
    ),
}
EXPECTED_SECTION_POLICY: dict[
    tuple[str, str],
    tuple[str, int, int | None, str, tuple[str, ...]],
] = {
    ("improvement_portfolio_v1", "baseline"): (
        "required",
        1,
        1,
        "none",
        ("assessment_summary", "student_work"),
    ),
    ("improvement_portfolio_v1", "later_evidence"): (
        "required",
        1,
        3,
        "none",
        ("assessment_summary", "student_work"),
    ),
    ("improvement_portfolio_v1", "supporting_feedback"): (
        "optional",
        0,
        2,
        "none",
        ("feedback",),
    ),
    ("improvement_portfolio_v1", "reflection"): (
        "required",
        0,
        0,
        "required",
        ("student_work",),
    ),
    ("showcase_portfolio_v1", "featured_work"): (
        "required",
        1,
        3,
        "none",
        ("student_work",),
    ),
    ("showcase_portfolio_v1", "supporting_evidence"): (
        "optional",
        0,
        3,
        "none",
        ("assessment_summary", "feedback"),
    ),
    ("showcase_portfolio_v1", "reflection"): (
        "required",
        0,
        0,
        "required",
        ("student_work",),
    ),
}

FORBIDDEN_DEPENDENCY_MARKERS = (
    "scoreform",
    "quillan",
    "pds-concord",
    "pds_concord",
)
FORBIDDEN_IMPORT_ROOTS = ("scoreform", "quillan", "concord")


def _fail(findings: list[str], message: str) -> None:
    findings.append(message)


def _validate_package_dependencies(root: Path, findings: list[str]) -> None:
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    start_marker = "dependencies = ["
    start = pyproject.find(start_marker)
    end = pyproject.find("]", start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0:
        _fail(findings, "pyproject.toml project dependency block could not be located.")
        return
    dependency_block = pyproject[start:end].casefold()
    if "pds-core>=0.6,<0.7" not in dependency_block:
        _fail(findings, "pyproject.toml is missing the expected Core dependency range.")
    for marker in FORBIDDEN_DEPENDENCY_MARKERS:
        if marker in dependency_block:
            _fail(
                findings,
                f"starter support must not add a hard sibling dependency: {marker}",
            )


def _validate_import_isolation(findings: list[str]) -> None:
    for module_name in FORBIDDEN_IMPORT_ROOTS:
        if module_name in sys.modules:
            _fail(
                findings,
                f"starter validation imported optional sibling package {module_name!r}.",
            )


def _validate_pack(starter_id: str, findings: list[str]) -> None:
    validation = validate_starter_profile_pack(starter_id)
    if not validation.valid:
        _fail(
            findings,
            f"{starter_id}: packaged validation failed: {validation.issue_codes!r}",
        )
        return

    pack = get_starter_profile_pack(starter_id)
    purpose, family_id, profile_id, section_ids, requirement_ids = EXPECTED[starter_id]

    if pack.contract_version != STARTER_PROFILE_PACK_CONTRACT_VERSION:
        _fail(findings, f"{starter_id}: unexpected pack contract version.")
    if pack.purpose_kind != purpose:
        _fail(findings, f"{starter_id}: unexpected purpose kind.")
    if pack.family.profile_family_id != family_id:
        _fail(findings, f"{starter_id}: unexpected Family identity.")
    if pack.revision.portfolio_profile_id != profile_id:
        _fail(findings, f"{starter_id}: unexpected Profile series identity.")
    if pack.revision.profile_revision != 1:
        _fail(findings, f"{starter_id}: initial Profile Revision must be 1.")
    if pack.revision.predecessor_revision is not None:
        _fail(findings, f"{starter_id}: initial Profile Revision must have no predecessor.")
    if pack.family.purpose_kind != purpose or pack.revision.purpose_kind != purpose:
        _fail(findings, f"{starter_id}: Family/Revision purpose mismatch.")
    if pack.revision.profile_family_id != family_id:
        _fail(findings, f"{starter_id}: Revision does not identify the frozen Family.")

    author = pack.family.created_by
    if (
        author.actor_kind != "system"
        or author.actor_id != "vitrine_starter_profile_catalog"
        or author.owning_system != "vitrine"
        or author.display_label_snapshot != "Vitrine starter Profile catalog"
        or author.role_snapshot != "starter_profile_author"
        or pack.family.created_at.isoformat() != "2026-09-04T00:00:00+00:00"
        or pack.revision.created_by != author
        or pack.revision.created_at != pack.family.created_at
    ):
        _fail(findings, f"{starter_id}: authored provenance is not deterministic.")
    if STARTER_PROFILE_CATALOG_CONTRACT_VERSION not in (
        pack.revision.source_authority_references
    ):
        _fail(findings, f"{starter_id}: starter catalog authority reference is absent.")
    if not pack.revision.known_limitations:
        _fail(findings, f"{starter_id}: known limitations must be explicit.")

    applicability = pack.revision.applicability
    if any(
        (
            applicability.jurisdiction,
            applicability.institution_id,
            applicability.program_id,
            applicability.school_years,
            applicability.cohorts,
            applicability.grade_bands,
            applicability.content_areas,
            applicability.pathway,
            applicability.effective_from,
            applicability.effective_through,
            applicability.authority_reference,
        )
    ):
        _fail(findings, f"{starter_id}: general starter applicability must remain broad.")

    actual_sections = tuple(section.section_id for section in pack.revision.sections)
    if actual_sections != section_ids:
        _fail(
            findings,
            f"{starter_id}: unexpected section order/identity: {actual_sections!r}",
        )
    actual_orders = tuple(section.order for section in pack.revision.sections)
    expected_orders = tuple(range(1, len(pack.revision.sections) + 1))
    if actual_orders != expected_orders:
        _fail(findings, f"{starter_id}: section order is not explicit and contiguous.")

    runtime_candidate_kinds = frozenset(CANDIDATE_KIND_BY_ARTIFACT_KIND.values())
    for section in pack.revision.sections:
        expected_policy = EXPECTED_SECTION_POLICY[(starter_id, section.section_id)]
        actual_policy = (
            section.obligation,
            section.minimum_placements,
            section.maximum_placements,
            section.reflection_requirement,
            section.allowed_candidate_kinds,
        )
        if actual_policy != expected_policy:
            _fail(
                findings,
                f"{starter_id}:{section.section_id}: section policy changed: "
                f"{actual_policy!r}",
            )
        unsupported = set(section.allowed_candidate_kinds).difference(
            STARTER_PROFILE_CANDIDATE_KINDS_V1
        )
        if unsupported:
            _fail(
                findings,
                f"{starter_id}:{section.section_id}: unsupported starter Candidate kinds "
                f"{sorted(unsupported)!r}.",
            )
        unknown_runtime = set(section.allowed_candidate_kinds).difference(
            runtime_candidate_kinds
        )
        if unknown_runtime:
            _fail(
                findings,
                f"{starter_id}:{section.section_id}: Candidate kinds are outside the "
                f"current Vitrine evaluator vocabulary: {sorted(unknown_runtime)!r}.",
            )

    actual_requirements = tuple(item.requirement_id for item in pack.requirements)
    if actual_requirements != requirement_ids:
        _fail(
            findings,
            f"{starter_id}: unexpected Requirement identity/order: "
            f"{actual_requirements!r}",
        )
    section_id_set = set(actual_sections)
    for requirement in pack.requirements:
        if requirement.profile_reference != pack.revision.reference:
            _fail(
                findings,
                f"{starter_id}:{requirement.requirement_id}: Requirement does not "
                "identify the exact starter Revision.",
            )
        if requirement.scope_kind == "section":
            if requirement.scope_reference not in section_id_set:
                _fail(
                    findings,
                    f"{starter_id}:{requirement.requirement_id}: section scope does "
                    "not resolve.",
                )
        if requirement.replaces_requirement_id is not None:
            _fail(
                findings,
                f"{starter_id}:{requirement.requirement_id}: initial Requirement "
                "must not replace predecessor policy.",
            )

    family_only_state = project_profile_state((pack.family,))
    if (
        family_only_state.revisions
        or family_only_state.requirements
        or family_only_state.lifecycle_events
    ):
        _fail(
            findings,
            f"{starter_id}: purpose/Family projection injected hidden Profile policy.",
        )

    aggregate_issues = collect_profile_state_issues(
        project_profile_state((pack.family, pack.revision, *pack.requirements))
    )
    if aggregate_issues:
        _fail(
            findings,
            f"{starter_id}: ordinary Profile aggregate validation failed: "
            f"{aggregate_issues[0].code}",
        )

    if starter_id == "improvement_portfolio_v1":
        text = " ".join(
            (
                pack.description,
                *pack.revision.known_limitations,
                *(section.purpose for section in pack.revision.sections),
            )
        ).casefold()
        if "does not determine whether improvement occurred" not in text:
            _fail(findings, "Improvement starter must disclaim inferred improvement.")
        for forbidden in ("highest score", "latest attempt", "best rating"):
            if forbidden in " ".join(section.purpose.casefold() for section in pack.revision.sections):
                _fail(
                    findings,
                    f"Improvement section policy must not encode automatic {forbidden!r} selection.",
                )

    if starter_id == "showcase_portfolio_v1":
        audience_classes = {rule.audience_class for rule in pack.revision.audience_rules}
        review_classes = {
            review
            for rule in pack.revision.audience_rules
            for review in rule.required_review_classes
        }
        if "external_reviewer" not in audience_classes:
            _fail(findings, "Showcase starter must define a bounded external-review audience.")
        if not {"privacy_review", "rights_review", "accessibility_review"}.issubset(
            review_classes
        ):
            _fail(
                findings,
                "Showcase audience must preserve privacy, rights, and accessibility review.",
            )
        limitation_text = " ".join(pack.revision.known_limitations).casefold()
        if "does not grant permission to disclose student work" not in limitation_text:
            _fail(findings, "Showcase starter must disclaim disclosure authorization.")


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    if STARTER_PROFILE_CATALOG_CONTRACT_VERSION != "vitrine_starter_profile_catalog_v1":
        _fail(findings, "unexpected starter catalog contract version")
    if STARTER_PROFILE_PACK_CONTRACT_VERSION != "vitrine_starter_profile_pack_v1":
        _fail(findings, "unexpected starter pack contract version")
    if STARTER_PROFILE_IDS != (
        "improvement_portfolio_v1",
        "showcase_portfolio_v1",
    ):
        _fail(findings, "starter IDs/order changed")
    if STARTER_PROFILE_FAMILY_IDS != (
        "vitrine_starter_improvement_family",
        "vitrine_starter_showcase_family",
    ):
        _fail(findings, "starter Family IDs changed")
    if STARTER_PORTFOLIO_PROFILE_IDS != (
        "vitrine_starter_improvement",
        "vitrine_starter_showcase",
    ):
        _fail(findings, "starter Profile series IDs changed")
    if STARTER_PROFILE_PURPOSES != ("improvement", "showcase"):
        _fail(findings, "starter purpose order changed")

    summaries = list_starter_profile_packs()
    summary_ids = tuple(item.starter_profile_id for item in summaries)
    if summary_ids != STARTER_PROFILE_IDS:
        _fail(findings, f"catalog order differs from frozen starter IDs: {summary_ids!r}")
    if len(set(summary_ids)) != len(summary_ids):
        _fail(findings, "starter catalog contains duplicate IDs")

    for starter_id in STARTER_PROFILE_IDS:
        _validate_pack(starter_id, findings)

    _validate_package_dependencies(root, findings)
    _validate_import_isolation(findings)
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = validate(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS starter Profile validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
