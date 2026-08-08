from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioProfileFamily,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
)
from vitrine.storage import commit_record_batch

NOW = datetime(2026, 8, 7, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_profile",
    owning_system="local",
    role_snapshot="teacher",
)


@dataclass
class DeterministicIds:
    counters: dict[str, int]

    def __init__(self) -> None:
        self.counters = {}

    def __call__(self, prefix: str) -> str:
        value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = value
        return f"{prefix}_{value}"


def fixed_clock() -> datetime:
    return NOW


def make_profile_workspace(tmp_path: Path) -> Path:
    workspace = ensure_workspace_root(tmp_path / "workspace", create=True)
    subject = PortfolioSubject(
        portfolio_subject_id="subject_profile",
        created_at=NOW,
        created_by=ACTOR,
        display_name_snapshot="Synthetic Student",
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_profile",
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=NOW,
        created_by=ACTOR,
        title_snapshot="Synthetic Portfolio",
    )
    commit_record_batch(workspace, (subject, portfolio), expected_state_revision=None)
    return workspace


def improvement_family() -> PortfolioProfileFamily:
    return PortfolioProfileFamily(
        profile_family_id="family_improvement",
        label="Improvement Profiles",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=ACTOR,
        description="Synthetic improvement Profile family.",
    )


def improvement_revision(revision: int, *, predecessor: int | None = None, include_feedback: bool = False, profile_id: str = "profile_growth") -> PortfolioProfileRevision:
    sections = [
        ProfileSectionDefinition(
            section_id="baseline",
            label="Baseline",
            purpose="Starting evidence.",
            order=1,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("artifact_author",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="current",
            label="Current",
            purpose="Later evidence.",
            order=2,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("artifact_author",),
            reflection_requirement="required",
        ),
    ]
    if include_feedback:
        sections.append(
            ProfileSectionDefinition(
                section_id="feedback_context",
                label="Feedback Context",
                purpose="Feedback used during revision.",
                order=3,
                obligation="required",
                minimum_placements=1,
                maximum_placements=1,
                allowed_candidate_kinds=("feedback",),
                required_relationship_kinds=(),
                reflection_requirement="none",
            )
        )
    audience = ProfileAudienceRule(
        audience_rule_id="student_view",
        audience_class="student",
        purpose="Student review.",
        allowed_content_classes=("student_work", "feedback", "reflection"),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=("privacy_review",),
        presentation_class="student_portfolio",
    )
    return PortfolioProfileRevision(
        portfolio_profile_id=profile_id,
        profile_revision=revision,
        profile_family_id="family_improvement",
        predecessor_revision=predecessor,
        label=f"Growth Profile r{revision}",
        purpose_kind="improvement",
        applicability=ProfileApplicability(),
        sections=tuple(sections),
        audience_rules=(audience,),
        created_at=NOW,
        created_by=ACTOR,
        source_authority_references=("local_instructional_policy",),
    )


def improvement_requirements(revision: int, *, include_feedback: bool = False, title_change: bool = False, profile_id: str = "profile_growth") -> tuple[PortfolioProfileRequirement, ...]:
    values = [
        PortfolioProfileRequirement(
            portfolio_profile_id=profile_id,
            profile_revision=revision,
            requirement_id="baseline_required",
            requirement_kind="section",
            obligation="required",
            title="Baseline evidence" if not title_change else "Baseline work",
            statement="Include one baseline item.",
            scope_kind="section",
            scope_reference="baseline",
            satisfaction_class="section_cardinality",
            authority_references=("local_instructional_policy",),
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile_id,
            profile_revision=revision,
            requirement_id="current_required",
            requirement_kind="section",
            obligation="required",
            title="Current evidence",
            statement="Include one current item.",
            scope_kind="section",
            scope_reference="current",
            satisfaction_class="section_cardinality",
            authority_references=("local_instructional_policy",),
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile_id,
            profile_revision=revision,
            requirement_id="teacher_review",
            requirement_kind="approval",
            obligation="required",
            title="Teacher review",
            statement="Teacher review is required before issue.",
            scope_kind="portfolio",
            satisfaction_class="approval_record",
            authority_references=("local_instructional_policy",),
        ),
    ]
    if include_feedback:
        values.append(
            PortfolioProfileRequirement(
                portfolio_profile_id=profile_id,
                profile_revision=revision,
                requirement_id="feedback_context_required",
                requirement_kind="section",
                obligation="required",
                title="Feedback context",
                statement="Include one feedback context item.",
                scope_kind="section",
                scope_reference="feedback_context",
                satisfaction_class="section_cardinality",
                authority_references=("local_instructional_policy",),
            )
        )
    return tuple(values)


def showcase_family() -> PortfolioProfileFamily:
    return PortfolioProfileFamily(
        profile_family_id="family_showcase",
        label="Showcase Profiles",
        purpose_kind="showcase",
        created_at=NOW,
        created_by=ACTOR,
    )


def showcase_revision() -> PortfolioProfileRevision:
    return PortfolioProfileRevision(
        portfolio_profile_id="profile_showcase_local",
        profile_revision=1,
        profile_family_id="family_showcase",
        predecessor_revision=None,
        label="Local Showcase",
        purpose_kind="showcase",
        applicability=ProfileApplicability(),
        sections=(
            ProfileSectionDefinition(
                section_id="featured",
                label="Featured Work",
                purpose="Curated work.",
                order=1,
                obligation="required",
                minimum_placements=1,
                maximum_placements=None,
                allowed_candidate_kinds=("student_work",),
                required_relationship_kinds=("artifact_author",),
                reflection_requirement="optional",
            ),
        ),
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="school_exhibition",
                audience_class="institutional_reviewer",
                purpose="School exhibition.",
                allowed_content_classes=("student_work",),
                prohibited_content_classes=("private_teacher_note",),
                required_review_classes=("privacy_review",),
                presentation_class="showcase",
            ),
            ProfileAudienceRule(
                audience_rule_id="public_web",
                audience_class="public",
                purpose="Public showcase.",
                allowed_content_classes=("student_work",),
                prohibited_content_classes=("private_teacher_note", "secure_assessment_content"),
                required_review_classes=("privacy_review", "rights_review"),
                presentation_class="public_showcase",
            ),
        ),
        created_at=NOW,
        created_by=ACTOR,
    )


def showcase_requirements() -> tuple[PortfolioProfileRequirement, ...]:
    return (
        PortfolioProfileRequirement(
            portfolio_profile_id="profile_showcase_local",
            profile_revision=1,
            requirement_id="featured_required",
            requirement_kind="section",
            obligation="required",
            title="Featured work",
            statement="Include curated featured work.",
            scope_kind="section",
            scope_reference="featured",
            satisfaction_class="section_cardinality",
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id="profile_showcase_local",
            profile_revision=1,
            requirement_id="public_privacy_review",
            requirement_kind="approval",
            obligation="required",
            title="Public privacy review",
            statement="Public issue requires privacy review.",
            scope_kind="audience",
            scope_reference="public_web",
            satisfaction_class="approval_record",
        ),
    )
