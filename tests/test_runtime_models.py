from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    Portfolio,
    PortfolioProfileBinding,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    VitrineModelValidationError,
)

NOW = datetime(2026, 8, 6, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
)


def test_portfolio_and_subject_are_distinct_immutable_records() -> None:
    subject = PortfolioSubject(
        portfolio_subject_id="subject_1", created_at=NOW, created_by=ACTOR
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_1",
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=NOW,
        created_by=ACTOR,
    )
    assert portfolio.portfolio_id != subject.portfolio_subject_id
    with pytest.raises(FrozenInstanceError):
        portfolio.portfolio_id = "changed"  # type: ignore[misc]


def test_class_qualified_identity_keeps_equal_student_ids_distinct() -> None:
    first = ClassQualifiedStudentRef(
        class_id="english10_p2", student_id="student_1", school_year="2026-2027"
    )
    second = ClassQualifiedStudentRef(
        class_id="science10_p4", student_id="student_1", school_year="2026-2027"
    )
    assert first != second


def test_school_year_uses_core_contract() -> None:
    with pytest.raises(VitrineModelValidationError):
        ClassQualifiedStudentRef(
            class_id="english10_p2", student_id="student_1", school_year="2026"
        )


def test_profile_sections_require_explicit_unique_order() -> None:
    section = ProfileSectionDefinition(
        section_id="baseline",
        label="Baseline",
        purpose="Initial work.",
        order=1,
        obligation="required",
        minimum_placements=1,
        maximum_placements=1,
        allowed_candidate_kinds=("original_student_work",),
        required_relationship_kinds=(),
        reflection_requirement="none",
    )
    audience = ProfileAudienceRule(
        audience_rule_id="student_view",
        audience_class="student",
        purpose="Student review.",
        allowed_content_classes=("student_work",),
        prohibited_content_classes=("private_note",),
        required_review_classes=(),
        presentation_class="student_portfolio",
    )
    profile = PortfolioProfileRevision(
        portfolio_profile_id="profile_1",
        profile_revision=1,
        profile_family_id=None,
        predecessor_revision=None,
        label="Profile",
        purpose_kind="improvement",
        applicability=ProfileApplicability(),
        sections=(section,),
        audience_rules=(audience,),
        created_at=NOW,
        created_by=ACTOR,
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="binding_1",
        portfolio_id="portfolio_1",
        profile_revision=profile.reference,
        bound_at=NOW,
        bound_by=ACTOR,
    )
    assert binding.profile_revision.profile_revision == 1


def test_prohibited_profile_section_requires_explicit_zero_maximum() -> None:
    with pytest.raises(VitrineModelValidationError, match="both placement"):
        ProfileSectionDefinition(
            section_id="excluded",
            label="Excluded",
            purpose="Not available in this Profile.",
            order=1,
            obligation="prohibited",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=(),
            required_relationship_kinds=(),
            reflection_requirement="none",
        )
