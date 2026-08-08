"""Exercise versioned Portfolio Profile workflows in a disposable workspace."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioProfileFamily,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileOverlayRequirement,
    ProfileOverlayRequirementChange,
    ProfileOverlayRevisionRef,
    ProfileRevisionRef,
    ProfileSectionDefinition,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    ProfileWorkflowError,
    activate_profile_revision,
    analyze_profile_migration,
    bind_portfolio_profile,
    compose_profile_revision,
    create_profile_family,
    create_profile_overlay,
    create_profile_revision,
    get_portfolio_profile_binding,
    get_profile_requirements,
    list_bindable_profile_revisions,
    migrate_portfolio_profile,
)
from vitrine.storage import (
    catalog_path,
    commit_record_batch,
    load_current_records,
    rebuild_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIGESTS = {
    "improvement-foundational-records-v1.json": "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8",
    "showcase-foundational-records-v1.json": "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360",
}
NOW = datetime(2026, 8, 7, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_profile",
    owning_system="local",
    role_snapshot="teacher",
)


class Ids:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self._counts.get(prefix, 0) + 1
        self._counts[prefix] = value
        return f"{prefix}_{value}"


def _clock() -> datetime:
    return NOW


def _section(section_id: str, order: int, *, reflection: str = "none") -> ProfileSectionDefinition:
    return ProfileSectionDefinition(
        section_id=section_id,
        label=section_id.replace("_", " ").title(),
        purpose=f"Synthetic {section_id} section.",
        order=order,
        obligation="required",
        minimum_placements=1,
        maximum_placements=1,
        allowed_candidate_kinds=("student_work",),
        required_relationship_kinds=("artifact_author",),
        reflection_requirement=reflection,
    )


def _audience() -> ProfileAudienceRule:
    return ProfileAudienceRule(
        audience_rule_id="student_view",
        audience_class="student",
        purpose="Student review.",
        allowed_content_classes=("student_work", "feedback", "reflection"),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=("privacy_review",),
        presentation_class="student_portfolio",
    )


def _family() -> PortfolioProfileFamily:
    return PortfolioProfileFamily(
        profile_family_id="family_growth",
        label="Growth Profiles",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=ACTOR,
    )


def _revision(number: int, *, predecessor: int | None = None, feedback: bool = False, profile_id: str = "profile_growth") -> PortfolioProfileRevision:
    sections = [_section("baseline", 1), _section("current", 2, reflection="required")]
    if feedback:
        sections.append(_section("feedback_context", 3))
    return PortfolioProfileRevision(
        portfolio_profile_id=profile_id,
        profile_revision=number,
        profile_family_id="family_growth",
        predecessor_revision=predecessor,
        label=f"Growth r{number}",
        purpose_kind="improvement",
        applicability=ProfileApplicability(),
        sections=tuple(sections),
        audience_rules=(_audience(),),
        created_at=NOW,
        created_by=ACTOR,
        source_authority_references=("local_instructional_policy",),
    )


def _requirements(number: int, *, feedback: bool = False, profile_id: str = "profile_growth") -> tuple[PortfolioProfileRequirement, ...]:
    values = [
        PortfolioProfileRequirement(
            portfolio_profile_id=profile_id,
            profile_revision=number,
            requirement_id="baseline_required",
            requirement_kind="section",
            obligation="required",
            title="Baseline evidence" if number == 1 else "Baseline work",
            statement="Include one baseline item.",
            scope_kind="section",
            scope_reference="baseline",
            satisfaction_class="section_cardinality",
            authority_references=("local_instructional_policy",),
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile_id,
            profile_revision=number,
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
            profile_revision=number,
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
    if feedback:
        values.append(
            PortfolioProfileRequirement(
                portfolio_profile_id=profile_id,
                profile_revision=number,
                requirement_id="feedback_context_required",
                requirement_kind="section",
                obligation="required",
                title="Feedback context",
                statement="Include feedback context.",
                scope_kind="section",
                scope_reference="feedback_context",
                satisfaction_class="section_cardinality",
                authority_references=("local_instructional_policy",),
            )
        )
    return tuple(values)


def _showcase_family() -> PortfolioProfileFamily:
    return PortfolioProfileFamily(
        profile_family_id="family_showcase",
        label="Synthetic Showcase Profiles",
        purpose_kind="showcase",
        created_at=NOW,
        created_by=ACTOR,
    )


def _showcase_revision() -> PortfolioProfileRevision:
    return PortfolioProfileRevision(
        portfolio_profile_id="profile_showcase",
        profile_revision=1,
        profile_family_id="family_showcase",
        predecessor_revision=None,
        label="Synthetic Showcase",
        purpose_kind="showcase",
        applicability=ProfileApplicability(),
        sections=(
            ProfileSectionDefinition(
                section_id="featured",
                label="Featured Work",
                purpose="Curated showcase work.",
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
                prohibited_content_classes=(
                    "private_teacher_note",
                    "secure_assessment_content",
                ),
                required_review_classes=("privacy_review", "rights_review"),
                presentation_class="public_showcase",
            ),
        ),
        created_at=NOW,
        created_by=ACTOR,
    )


def _showcase_requirements() -> tuple[PortfolioProfileRequirement, ...]:
    return (
        PortfolioProfileRequirement(
            portfolio_profile_id="profile_showcase",
            profile_revision=1,
            requirement_id="featured_required",
            requirement_kind="section",
            obligation="required",
            title="Featured work",
            statement="Include curated featured work.",
            scope_kind="section",
            scope_reference="featured",
            satisfaction_class="section_cardinality",
            authority_references=("local_showcase_policy",),
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id="profile_showcase",
            profile_revision=1,
            requirement_id="public_privacy_review",
            requirement_kind="approval",
            obligation="required",
            title="Public privacy review",
            statement="Public issue requires privacy review.",
            scope_kind="audience",
            scope_reference="public_web",
            satisfaction_class="approval_record",
            authority_references=("local_showcase_policy",),
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id="profile_showcase",
            profile_revision=1,
            requirement_id="public_rights_review",
            requirement_kind="approval",
            obligation="required",
            title="Public rights review",
            statement="Public issue requires rights review.",
            scope_kind="audience",
            scope_reference="public_web",
            satisfaction_class="approval_record",
            authority_references=("local_showcase_policy",),
        ),
    )


def _verify_fixture_digests() -> None:
    fixture_dir = ROOT / "tests" / "fixtures" / "runtime-models"
    for name, expected in FIXTURE_DIGESTS.items():
        actual = hashlib.sha256((fixture_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"foundational fixture digest changed: {name}")


def validate() -> None:
    _verify_fixture_digests()
    ids = Ids()
    with tempfile.TemporaryDirectory(prefix="vitrine-profile-validation-") as temporary:
        workspace = ensure_workspace_root(Path(temporary) / "workspace", create=True)
        subject = PortfolioSubject(
            portfolio_subject_id="subject_profile",
            created_at=NOW,
            created_by=ACTOR,
        )
        portfolio = Portfolio(
            portfolio_id="portfolio_profile",
            portfolio_subject_id=subject.portfolio_subject_id,
            created_at=NOW,
            created_by=ACTOR,
        )
        first = commit_record_batch(workspace, (subject, portfolio), expected_state_revision=None)
        if first.state_revision != 1:
            raise RuntimeError("unexpected bootstrap state revision")

        create_profile_family(workspace, _family(), expected_state_revision=1)
        create_profile_revision(workspace, _revision(1), _requirements(1), expected_state_revision=2)
        if list_bindable_profile_revisions(workspace):
            raise RuntimeError("unactivated Profile Revision became bindable")
        activate_profile_revision(
            workspace,
            ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=1),
            actor=ACTOR,
            reason="Approved local policy.",
            authority_reference="local_instructional_policy",
            expected_state_revision=3,
            clock=_clock,
            id_factory=ids,
        )
        bind_portfolio_profile(
            workspace,
            portfolio.portfolio_id,
            ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=1),
            actor=ACTOR,
            binding_reason="Initial Profile.",
            context=ProfileBindingContext(),
            expected_state_revision=4,
            clock=_clock,
            id_factory=ids,
        )

        create_profile_revision(
            workspace,
            _revision(2, predecessor=1, feedback=True),
            _requirements(2, feedback=True),
            expected_state_revision=5,
        )
        current = get_portfolio_profile_binding(workspace, portfolio.portfolio_id)
        if current is None or current.profile_revision.profile_revision != 1:
            raise RuntimeError("higher Revision changed existing Binding automatically")
        bindable = list_bindable_profile_revisions(workspace)
        if [item.reference.profile_revision for item in bindable] != [1]:
            raise RuntimeError("greatest Revision was inferred as active")

        activate_profile_revision(
            workspace,
            ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
            actor=ACTOR,
            reason="Approved successor policy.",
            authority_reference="local_instructional_policy",
            expected_state_revision=6,
            clock=_clock,
            id_factory=ids,
        )
        analysis = analyze_profile_migration(
            workspace,
            portfolio.portfolio_id,
            ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
            context=ProfileBindingContext(),
        )
        if analysis.requirement_impact.added != ("feedback_context_required",):
            raise RuntimeError("migration impact did not preserve stable Requirement identity")
        migrate_portfolio_profile(
            workspace,
            portfolio.portfolio_id,
            ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),
            actor=ACTOR,
            migration_reason="Adopt successor policy.",
            authority_reference="local_instructional_policy",
            context=ProfileBindingContext(),
            expected_state_revision=7,
            clock=_clock,
            id_factory=ids,
        )
        current = get_portfolio_profile_binding(workspace, portfolio.portfolio_id)
        if current is None or current.profile_revision.profile_revision != 2 or current.predecessor_binding_id is None:
            raise RuntimeError("explicit migration did not create a successor Binding")

        overlay = PortfolioProfileOverlayRevision(
            overlay_id="overlay_growth",
            overlay_revision=1,
            predecessor_overlay_revision=None,
            label="Local growth overlay",
            purpose_kind="improvement",
            created_at=NOW,
            created_by=ACTOR,
            authority_reference="local_instructional_policy",
            component_revisions=(ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),),
            requirement_changes=(
                ProfileOverlayRequirementChange(
                    action="add",
                    requirement=ProfileOverlayRequirement(
                        requirement_id="local_reflection",
                        requirement_kind="reflection",
                        obligation="required",
                        title="Local reflection",
                        statement="Include one local reflection.",
                        scope_kind="portfolio",
                        satisfaction_class="reflection_record",
                        authority_references=("local_instructional_policy",),
                    ),
                ),
            ),
        )
        create_profile_overlay(workspace, overlay, expected_state_revision=8)
        effective = replace(
            _revision(2, predecessor=1, feedback=True, profile_id="profile_growth_local"),
            profile_revision=1,
            predecessor_revision=None,
            label="Local effective growth",
        )
        composed = compose_profile_revision(
            workspace,
            effective,
            (ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),),
            (ProfileOverlayRevisionRef(overlay_id="overlay_growth", overlay_revision=1),),
            actor=ACTOR,
            authority_reference="local_instructional_policy",
            expected_state_revision=9,
            clock=_clock,
            id_factory=ids,
        )
        if "local_reflection" not in composed.requirement_ids:
            raise RuntimeError("overlay requirement was not flattened into effective Profile")
        if not get_profile_requirements(workspace, effective.reference):
            raise RuntimeError("effective Profile is not self-contained")

        weakening = PortfolioProfileOverlayRevision(
            overlay_id="overlay_weakening",
            overlay_revision=1,
            predecessor_overlay_revision=None,
            label="Weakening overlay",
            purpose_kind="improvement",
            created_at=NOW,
            created_by=ACTOR,
            authority_reference="local_instructional_policy",
            component_revisions=(ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),),
            requirement_changes=(
                ProfileOverlayRequirementChange(
                    action="replace",
                    requirement=ProfileOverlayRequirement(
                        requirement_id="baseline_optional_local",
                        requirement_kind="section",
                        obligation="optional",
                        title="Optional baseline",
                        statement="Baseline becomes optional.",
                        scope_kind="section",
                        scope_reference="baseline",
                        satisfaction_class="section_cardinality",
                        replaces_requirement_id="baseline_required",
                    ),
                ),
            ),
        )
        create_profile_overlay(workspace, weakening, expected_state_revision=10)
        try:
            compose_profile_revision(
                workspace,
                replace(effective, portfolio_profile_id="profile_growth_bad"),
                (ProfileRevisionRef(portfolio_profile_id="profile_growth", profile_revision=2),),
                (ProfileOverlayRevisionRef(overlay_id="overlay_weakening", overlay_revision=1),),
                actor=ACTOR,
                authority_reference="local_instructional_policy",
                expected_state_revision=11,
                clock=_clock,
                id_factory=ids,
            )
        except ProfileWorkflowError as error:
            if error.code != "profile_composition_conflict":
                raise
        else:
            raise RuntimeError("weakening overlay was accepted")

        create_profile_family(
            workspace, _showcase_family(), expected_state_revision=11
        )
        create_profile_revision(
            workspace,
            _showcase_revision(),
            _showcase_requirements(),
            expected_state_revision=12,
        )
        showcase_ref = ProfileRevisionRef(
            portfolio_profile_id="profile_showcase", profile_revision=1
        )
        if any(
            item.reference == showcase_ref
            for item in list_bindable_profile_revisions(
                workspace, purpose_kind="showcase"
            )
        ):
            raise RuntimeError("unactivated showcase Profile became bindable")
        activate_profile_revision(
            workspace,
            showcase_ref,
            actor=ACTOR,
            reason="Approve synthetic showcase policy.",
            authority_reference="local_showcase_policy",
            expected_state_revision=13,
            clock=_clock,
            id_factory=ids,
        )
        public_rule = next(
            item
            for item in _showcase_revision().audience_rules
            if item.audience_rule_id == "public_web"
        )
        if set(public_rule.required_review_classes) != {
            "privacy_review",
            "rights_review",
        }:
            raise RuntimeError("showcase public audience lost explicit review policy")
        showcase_portfolio = Portfolio(
            portfolio_id="portfolio_showcase",
            portfolio_subject_id=subject.portfolio_subject_id,
            created_at=NOW,
            created_by=ACTOR,
        )
        commit_record_batch(
            workspace, (showcase_portfolio,), expected_state_revision=14
        )
        bind_portfolio_profile(
            workspace,
            showcase_portfolio.portfolio_id,
            showcase_ref,
            actor=ACTOR,
            binding_reason="Synthetic showcase Binding.",
            context=ProfileBindingContext(),
            expected_state_revision=15,
            clock=_clock,
            id_factory=ids,
        )

        before = load_current_records(workspace)
        rebuild_catalog(workspace)
        catalog_path(workspace).unlink()
        after = load_current_records(workspace)
        if before != after:
            raise RuntimeError("canonical Profile reads depended on derived catalog")


def main() -> int:
    try:
        validate()
        print("PASS Portfolio Profile workflow validation")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Portfolio Profile workflow validation failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
