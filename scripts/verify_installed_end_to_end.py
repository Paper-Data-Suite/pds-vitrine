"""Verify installed Vitrine acceptance in an isolated interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module, metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from vitrine.snapshot_materialization import (
    SnapshotRendererRegistry as _SnapshotRendererRegistryBase,
)
from vitrine.snapshot_materialization import (
    SnapshotSourceProviderRegistry as _SnapshotSourceProviderRegistryBase,
)

if TYPE_CHECKING:
    from pds_core.publication_records import PublicationCapability

    from vitrine.producer_adapters import ProducerAdapterSupportRequest


STAGES = (
    "installed_provenance",
    "fixture_boundary",
    "workspace_identity",
    "profile_setup",
    "core_publication",
    "candidate_discovery",
    "improvement_curation",
    "showcase_curation",
    "improvement_snapshot",
    "showcase_snapshot",
    "source_drift",
    "historical_reload",
    "write_isolation",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_T = TypeVar("_T")

BASELINE_CLASS_ID = "class-ela10-syn"
BASELINE_SCHOOL_YEAR = "2023-2024"
LATER_CLASS_ID = "class-ela11-syn"
LATER_SCHOOL_YEAR = "2024-2025"
SHOWCASE_CLASS_ID = "class-ela12-syn"
SHOWCASE_SCHOOL_YEAR = "2025-2026"
STUDENT_ID = "student-syn-001"
NOW = datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc)


class InstalledEndToEndAcceptanceError(RuntimeError):
    """Bounded acceptance failure with one stable stage."""

    def __init__(self, stage: str, message: str) -> None:
        if stage not in STAGES:
            raise ValueError("stage must be a known installed-acceptance stage")
        if not message or "\n" in message or "\r" in message:
            raise ValueError("message must be nonempty single-line text")
        self.stage = stage
        self.message = message
        super().__init__(f"{stage}: {message}")


def _require(condition: bool, stage: str, message: str) -> None:
    if not condition:
        raise InstalledEndToEndAcceptanceError(stage, message)


def _stage(stage: str, operation: Callable[[], _T]) -> _T:
    try:
        return operation()
    except InstalledEndToEndAcceptanceError:
        raise
    except Exception as error:
        raise InstalledEndToEndAcceptanceError(
            stage,
            f"operation failed ({type(error).__name__})",
        ) from error


def _sha256(value: str, label: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise InstalledEndToEndAcceptanceError(
            "installed_provenance", f"{label} is not a lowercase SHA-256 digest"
        )
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _module_origin(name: str) -> Path:
    module = import_module(name)
    raw = getattr(module, "__file__", None)
    if not isinstance(raw, str) or not raw:
        raise InstalledEndToEndAcceptanceError(
            "installed_provenance", f"{name} has no installed file origin"
        )
    return Path(raw).resolve()


def _installed_origin(path: Path, repository: Path) -> bool:
    prefix = Path(sys.prefix).resolve()
    lowered = {part.casefold() for part in path.parts}
    return (
        path.is_relative_to(prefix)
        and "site-packages" in lowered
        and not path.is_relative_to(repository)
    )


def _distribution_missing(name: str) -> bool:
    try:
        metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return True
    return False


def _installed_provenance(
    repository: Path,
    workspace: Path,
    *,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    stage = "installed_provenance"
    _require("PYTHONPATH" not in os.environ, stage, "PYTHONPATH must be cleared")
    configured_workspace = os.environ.get("PDS_WORKSPACE_ROOT")
    _require(
        configured_workspace is not None
        and Path(configured_workspace).resolve() == workspace,
        stage,
        "PDS_WORKSPACE_ROOT does not match the acceptance workspace",
    )
    _require(not workspace.exists(), stage, "workspace existed before explicit setup")

    vitrine_distribution = metadata.distribution("pds-vitrine")
    core_distribution = metadata.distribution("pds-core")
    _require(
        core_distribution.version == "0.6.3",
        stage,
        "installed Core version is not 0.6.3",
    )
    requirements = tuple(metadata.requires("pds-vitrine") or ())
    core_requirements = tuple(
        value
        for value in requirements
        if value.lower().replace("_", "-").startswith("pds-core")
    )
    normalized_core = tuple(
        value.lower().replace(" ", "") for value in core_requirements
    )
    _require(
        len(normalized_core) == 1
        and ">=0.6" in normalized_core[0]
        and "<0.7" in normalized_core[0],
        stage,
        "Vitrine Core dependency metadata does not preserve >=0.6,<0.7",
    )
    sibling_requirement_markers = (
        "scoreform",
        "quillan",
        "pds-concord",
        "pds-meridian",
        "pds-portia",
    )
    _require(
        not any(
            marker in requirement.lower()
            for requirement in requirements
            for marker in sibling_requirement_markers
        ),
        stage,
        "Vitrine metadata contains a sibling runtime dependency",
    )

    required_modules = (
        "vitrine",
        "vitrine.candidate_services",
        "vitrine.curation_services",
        "vitrine.development_adapters",
        "vitrine.development_candidate_fixtures",
        "vitrine.portfolio_services",
        "vitrine.producer_adapters",
        "vitrine.profile_services",
        "vitrine.snapshot_services",
        "vitrine.subject_services",
        "vitrine.workflow_context",
        "vitrine.storage",
        "pds_core",
        "pds_core.academic_catalog",
        "pds_core.publication_compatibility",
        "pds_core.publication_storage",
        "pds_core.registry_services",
    )
    origins = {name: _module_origin(name) for name in required_modules}
    for name, origin in origins.items():
        _require(
            _installed_origin(origin, repository),
            stage,
            f"{name} did not import from isolated site-packages",
        )

    for raw in sys.path:
        if not raw:
            continue
        try:
            resolved = Path(raw).resolve()
        except OSError:
            continue
        _require(
            not resolved.is_relative_to(repository),
            stage,
            "repository path leaked into isolated interpreter search path",
        )

    sibling_distributions = (
        "scoreform",
        "quillan",
        "pds-concord",
        "pds-meridian",
        "pds-portia",
    )
    _require(
        all(_distribution_missing(name) for name in sibling_distributions),
        stage,
        "a sibling producer or consumer distribution is installed",
    )
    sibling_modules = {"scoreform", "quillan", "concord", "meridian", "portia"}
    _require(
        not sibling_modules.intersection(
            {name.split(".", 1)[0] for name in sys.modules}
        ),
        stage,
        "a sibling producer or consumer module was implicitly imported",
    )

    publication_entries = tuple(
        entry
        for entry in vitrine_distribution.entry_points
        if entry.group == "paper_data_suite.publication_producers"
    )
    _require(
        not publication_entries,
        stage,
        "Vitrine must not advertise itself as a publication producer",
    )
    _require(not workspace.exists(), stage, "provenance checks created workspace state")
    return {
        "vitrine_version": vitrine_distribution.version,
        "core_version": core_distribution.version,
        "vitrine_wheel_sha256": _sha256(
            vitrine_wheel_sha256, "Vitrine wheel digest"
        ),
        "core_wheel_sha256": _sha256(core_wheel_sha256, "Core wheel digest"),
        "module_origins": {name: str(path) for name, path in origins.items()},
        "sibling_distributions_installed": False,
        "publication_producer_entry_points": 0,
    }


def _live_support_requests() -> dict[str, ProducerAdapterSupportRequest]:
    from vitrine.producer_adapters import ProducerAdapterSupportRequest

    return {
        "scoreform": ProducerAdapterSupportRequest(
            producer_module_id="scoreform",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="scoreform_academic_result_manifest_v1",
            producer_contract_version="scoreform_academic_work_v1",
            source_record_kind=None,
            source_record_contract_version=None,
            capabilities=("points", "question_evidence", "multiple_attempts"),
        ),
        "quillan": ProducerAdapterSupportRequest(
            producer_module_id="quillan",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="quillan_academic_result_manifest_v1",
            producer_contract_version="quillan_academic_work_v1",
            source_record_kind=None,
            source_record_contract_version=None,
            capabilities=("standards_ratings",),
        ),
        "concord": ProducerAdapterSupportRequest(
            producer_module_id="concord",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="concord_academic_result_manifest_v1",
            producer_contract_version="concord_academic_work_v1",
            source_record_kind="activity",
            source_record_contract_version="concord_activity_v1",
            capabilities=(
                "criterion_scores",
                "moderated_scores",
                "standards_ratings",
            ),
        ),
    }


def _fixture_boundary(workspace: Path) -> dict[str, object]:
    stage = "fixture_boundary"
    from pds_core.publication_compatibility import (
        discover_publication_producer_profiles,
    )

    from vitrine.development_adapters import (
        build_development_fixture_adapter_registry,
    )
    from vitrine.development_candidate_fixtures import (
        build_development_fixture_producer_registry,
    )
    from vitrine.producer_adapters import (
        ProducerAdapterError,
        ProducerAdapterUnsupportedError,
        build_adapter_registry,
    )
    from vitrine.workflow_context import default_workflow_dependencies

    discovered = discover_publication_producer_profiles()
    discovered_ids = tuple(profile.module_id for profile in discovered)
    _require(
        not any(value.startswith("vitrine_") for value in discovered_ids),
        stage,
        "Core producer discovery exposed a Vitrine development fixture",
    )

    defaults = default_workflow_dependencies()
    _require(
        defaults.producer_registry.profiles == (),
        stage,
        "default workflow producer registry is not fail-closed",
    )
    _require(
        defaults.adapter_registry.adapters == (),
        stage,
        "default workflow adapter registry is not fail-closed",
    )
    _require(
        defaults.development_fixture_mode is False,
        stage,
        "default workflow dependencies enabled fixture mode",
    )
    _require(
        type(defaults.snapshot_planning_provider).__name__
        == "UnconfiguredSnapshotPlanningProvider",
        stage,
        "default Snapshot planning provider is configured implicitly",
    )

    fixture_profiles = build_development_fixture_producer_registry()
    fixture_profile_ids = tuple(
        profile.module_id for profile in fixture_profiles.profiles
    )
    expected_profiles = (
        "vitrine_concord_fixture",
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
    )
    _require(
        fixture_profile_ids == expected_profiles,
        stage,
        "explicit fixture producer registry identity drifted",
    )
    fixture_adapters = build_development_fixture_adapter_registry()
    _require(
        len(fixture_adapters.adapters) == 3
        and all(
            adapter.declaration.integration_kind == "development_fixture"
            for adapter in fixture_adapters.adapters
        ),
        stage,
        "explicit fixture adapter registry is not exactly development-only",
    )
    try:
        build_adapter_registry(adapters=fixture_adapters.adapters)
    except ProducerAdapterError as error:
        _require(
            error.code == "adapter.fixture_not_enabled",
            stage,
            "ordinary registry rejected fixtures for the wrong reason",
        )
    else:
        raise InstalledEndToEndAcceptanceError(
            stage, "ordinary adapter registry accepted development fixtures"
        )

    live_requests = _live_support_requests()
    for producer, request in live_requests.items():
        try:
            fixture_adapters.select_adapter(request)
        except ProducerAdapterUnsupportedError as error:
            _require(
                error.code == "adapter.unsupported_contract",
                stage,
                f"{producer} live-like request failed with an unstable code",
            )
        else:
            raise InstalledEndToEndAcceptanceError(
                stage,
                f"{producer} live-like contract incorrectly matched a fixture adapter",
            )

    _require(
        not workspace.exists(),
        stage,
        "fixture boundary checks created workspace state",
    )
    return {
        "core_discovered_profile_ids": discovered_ids,
        "fixture_profile_ids": fixture_profile_ids,
        "fixture_adapter_ids": tuple(
            adapter.declaration.adapter_id for adapter in fixture_adapters.adapters
        ),
        "live_contract_non_masquerading": tuple(sorted(live_requests)),
        "default_workflow_fail_closed": True,
    }


@dataclass
class _AcceptanceIds:
    counters: dict[str, int]

    def __init__(self) -> None:
        self.counters = {}

    def __call__(self, prefix: str) -> str:
        number = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = number
        return f"{prefix}_installed_{number}"


def _fixed_clock() -> datetime:
    return NOW


def _state_revision(workspace: Path) -> int:
    from vitrine.storage import load_current_state

    return load_current_state(workspace).state_revision


def _write_class_context(
    workspace: Path,
    *,
    class_id: str,
    school_year: str,
    period: str,
) -> None:
    from pds_core.class_metadata import (
        create_class_metadata,
        write_class_metadata_for_class,
    )
    from pds_core.classes import write_class_roster
    from pds_core.rosters import ROSTER_REQUIRED_COLUMNS, validate_roster_rows

    write_class_metadata_for_class(
        workspace,
        create_class_metadata(
            class_id,
            school_year,
            created_at=NOW,
            module_details={},
        ),
    )
    roster = validate_roster_rows(
        ROSTER_REQUIRED_COLUMNS,
        (
            {
                "class_id": class_id,
                "student_id": STUDENT_ID,
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": period,
            },
            {
                "class_id": class_id,
                "student_id": f"confuser_{period}",
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": period,
            },
        ),
    )
    write_class_roster(workspace, roster)


def _actor() -> Any:
    from vitrine.models import ActorAttribution

    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="installed_acceptance_teacher",
        owning_system="vitrine",
        role_snapshot="teacher",
    )


def _student_actor() -> Any:
    from vitrine.models import ActorAttribution

    return ActorAttribution(
        actor_kind="core_student",
        actor_id=STUDENT_ID,
        owning_system="pds-core",
        role_snapshot="student",
    )


def _initialize_subject_and_portfolios(
    workspace: Path,
    ids: _AcceptanceIds,
) -> dict[str, str]:
    stage = "workspace_identity"
    from pds_core.workspace import ensure_workspace_root

    from vitrine.models import ClassQualifiedStudentRef
    from vitrine.portfolio_services import create_portfolio
    from vitrine.subject_services import (
        IdentityDecisionContext,
        create_portfolio_subject,
        link_portfolio_subject,
        resolve_subject_reference,
    )

    ensure_workspace_root(workspace, create=True)
    _write_class_context(
        workspace,
        class_id=BASELINE_CLASS_ID,
        school_year=BASELINE_SCHOOL_YEAR,
        period="2",
    )
    _write_class_context(
        workspace,
        class_id=LATER_CLASS_ID,
        school_year=LATER_SCHOOL_YEAR,
        period="4",
    )
    _write_class_context(
        workspace,
        class_id=SHOWCASE_CLASS_ID,
        school_year=SHOWCASE_SCHOOL_YEAR,
        period="1",
    )
    actor = _actor()
    context = IdentityDecisionContext(
        actor=actor,
        authority_source="installed_acceptance_roster",
        basis_type="direct_teacher_knowledge",
        basis_summary="Synthetic installed acceptance exact roster identity.",
    )
    baseline_ref = ClassQualifiedStudentRef(
        class_id=BASELINE_CLASS_ID,
        student_id=STUDENT_ID,
        school_year=BASELINE_SCHOOL_YEAR,
    )
    created = create_portfolio_subject(
        workspace,
        baseline_ref,
        context=context,
        expected_state_revision=None,
        clock=_fixed_clock,
        id_factory=ids,
    )
    _require(len(created.subject_ids) == 1, stage, "Subject creation was not exact")
    subject_id = created.subject_ids[0]
    later_ref = ClassQualifiedStudentRef(
        class_id=LATER_CLASS_ID,
        student_id=STUDENT_ID,
        school_year=LATER_SCHOOL_YEAR,
    )
    showcase_ref = ClassQualifiedStudentRef(
        class_id=SHOWCASE_CLASS_ID,
        student_id=STUDENT_ID,
        school_year=SHOWCASE_SCHOOL_YEAR,
    )
    for reference in (later_ref, showcase_ref):
        link_portfolio_subject(
            workspace,
            subject_id,
            reference,
            context=context,
            expected_state_revision=_state_revision(workspace),
            clock=_fixed_clock,
            id_factory=ids,
        )
    for reference in (baseline_ref, later_ref, showcase_ref):
        resolution = resolve_subject_reference(workspace, reference)
        _require(
            resolution.status == "resolved"
            and resolution.subject_ids == (subject_id,),
            stage,
            "class-qualified Subject reference did not resolve exactly",
        )
    improvement = create_portfolio(
        workspace,
        portfolio_subject_id=subject_id,
        created_by=actor,
        expected_state_revision=_state_revision(workspace),
        title_snapshot="Installed Improvement Portfolio",
        description_snapshot="Installed acceptance improvement workflow.",
        clock=_fixed_clock,
        id_factory=ids,
    ).portfolio
    showcase = create_portfolio(
        workspace,
        portfolio_subject_id=subject_id,
        created_by=actor,
        expected_state_revision=_state_revision(workspace),
        title_snapshot="Installed Showcase Portfolio",
        description_snapshot="Installed acceptance showcase workflow.",
        clock=_fixed_clock,
        id_factory=ids,
    ).portfolio
    _require(
        improvement.portfolio_subject_id == subject_id
        and showcase.portfolio_subject_id == subject_id
        and improvement.portfolio_id != showcase.portfolio_id,
        stage,
        "two distinct Portfolios were not created for one exact Subject",
    )
    return {
        "subject_id": subject_id,
        "improvement_portfolio_id": improvement.portfolio_id,
        "showcase_portfolio_id": showcase.portfolio_id,
    }


def _improvement_profile_records(actor: Any) -> tuple[Any, Any, tuple[Any, ...]]:
    from vitrine.models import (
        PortfolioProfileFamily,
        PortfolioProfileRequirement,
        PortfolioProfileRevision,
        ProfileApplicability,
        ProfileAudienceRule,
        ProfileSectionDefinition,
    )

    family = PortfolioProfileFamily(
        profile_family_id="installed_improvement_family",
        label="Installed Improvement Profile Family",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=actor,
    )
    sections = (
        ProfileSectionDefinition(
            section_id="baseline",
            label="Baseline",
            purpose="Exact baseline student work.",
            order=1,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="later_work",
            label="Later Work and Feedback",
            purpose="Exact later student work and student-facing feedback.",
            order=2,
            obligation="required",
            minimum_placements=2,
            maximum_placements=2,
            allowed_candidate_kinds=("student_work", "feedback"),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="reflection",
            label="Reflection",
            purpose="Student-authored comparison of exact Selections.",
            order=3,
            obligation="required",
            minimum_placements=0,
            maximum_placements=0,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=(),
            reflection_requirement="required",
        ),
        ProfileSectionDefinition(
            section_id="assessment_context",
            label="Assessment Context",
            purpose="Optional exact assessment-attempt context.",
            order=4,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("assessment_summary",),
            required_relationship_kinds=("attempt_subject",),
            reflection_requirement="none",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id="installed_improvement_profile",
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Installed Improvement Profile",
        purpose_kind="improvement",
        applicability=ProfileApplicability(
            school_years=(BASELINE_SCHOOL_YEAR, LATER_SCHOOL_YEAR)
        ),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="installed_improvement_student",
                audience_class="student",
                purpose="Synthetic student-facing improvement review.",
                allowed_content_classes=(
                    "student_work",
                    "feedback",
                    "reflection",
                    "assessment_summary",
                ),
                prohibited_content_classes=("private_teacher_note",),
                required_review_classes=(),
                presentation_class="student_portfolio",
            ),
        ),
        created_at=NOW,
        created_by=actor,
        source_authority_references=("installed_acceptance_policy",),
        known_limitations=("Synthetic acceptance does not calculate improvement.",),
    )
    requirements: list[Any] = []
    for section in sections:
        if section.section_id == "reflection":
            requirements.append(
                PortfolioProfileRequirement(
                    portfolio_profile_id=revision.portfolio_profile_id,
                    profile_revision=revision.profile_revision,
                    requirement_id="installed_improvement_reflection",
                    requirement_kind="reflection",
                    obligation="required",
                    title="Student comparison reflection",
                    statement="Include one student-authored comparison reflection.",
                    scope_kind="section",
                    scope_reference="reflection",
                    satisfaction_class="reflection_presence",
                    authority_references=("installed_acceptance_policy",),
                )
            )
        else:
            requirements.append(
                PortfolioProfileRequirement(
                    portfolio_profile_id=revision.portfolio_profile_id,
                    profile_revision=revision.profile_revision,
                    requirement_id=f"installed_{section.section_id}_requirement",
                    requirement_kind="section",
                    obligation=section.obligation,
                    title=f"{section.label} requirement",
                    statement="Preserve the exact installed acceptance section contract.",
                    scope_kind="section",
                    scope_reference=section.section_id,
                    satisfaction_class=(
                        "candidate_eligibility"
                        if section.section_id == "assessment_context"
                        else "placement_cardinality"
                    ),
                    authority_references=("installed_acceptance_policy",),
                )
            )
    return family, revision, tuple(requirements)


def _showcase_profile_records(actor: Any) -> tuple[Any, Any, tuple[Any, ...]]:
    from vitrine.models import (
        PortfolioProfileFamily,
        PortfolioProfileRequirement,
        PortfolioProfileRevision,
        ProfileApplicability,
        ProfileAudienceRule,
        ProfileSectionDefinition,
    )

    family = PortfolioProfileFamily(
        profile_family_id="installed_showcase_family",
        label="Installed Showcase Profile Family",
        purpose_kind="showcase",
        created_at=NOW,
        created_by=actor,
    )
    sections = (
        ProfileSectionDefinition(
            section_id="featured_work",
            label="Featured Work",
            purpose="Polished individual student work.",
            order=1,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("submission_subject",),
            reflection_requirement="none",
        ),
        ProfileSectionDefinition(
            section_id="collaboration",
            label="Collaboration",
            purpose="Collaborative evidence with documented contribution.",
            order=2,
            obligation="required",
            minimum_placements=1,
            maximum_placements=1,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("documented_contributor",),
            reflection_requirement="none",
        ),
    )
    revision = PortfolioProfileRevision(
        portfolio_profile_id="installed_showcase_profile",
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Installed Showcase Profile",
        purpose_kind="showcase",
        applicability=ProfileApplicability(school_years=(SHOWCASE_SCHOOL_YEAR,)),
        sections=sections,
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="installed_showcase_external",
                audience_class="external_reviewer",
                purpose="Synthetic minimum-necessary showcase review.",
                allowed_content_classes=(
                    "student_work",
                    "audience_safe_attribution",
                    "curation_rationale",
                    "portfolio_index",
                ),
                prohibited_content_classes=(
                    "private_teacher_note",
                    "raw_collaborator_data",
                    "secure_assessment_content",
                    "restricted_internal",
                ),
                required_review_classes=("privacy_review",),
                presentation_class="showcase",
            ),
        ),
        created_at=NOW,
        created_by=actor,
        source_authority_references=("installed_acceptance_policy",),
        known_limitations=("Curation review is not disclosure authorization.",),
    )
    requirements = tuple(
        PortfolioProfileRequirement(
            portfolio_profile_id=revision.portfolio_profile_id,
            profile_revision=revision.profile_revision,
            requirement_id=f"installed_{section.section_id}_requirement",
            requirement_kind="section",
            obligation="required",
            title=f"{section.label} requirement",
            statement="Preserve the exact installed acceptance section contract.",
            scope_kind="section",
            scope_reference=section.section_id,
            satisfaction_class="placement_cardinality",
            authority_references=("installed_acceptance_policy",),
        )
        for section in sections
    ) + (
        PortfolioProfileRequirement(
            portfolio_profile_id=revision.portfolio_profile_id,
            profile_revision=revision.profile_revision,
            requirement_id="installed_showcase_collaborator_review",
            requirement_kind="approval",
            obligation="required",
            title="Showcase collaborator treatment review",
            statement=(
                "Review the exact collaborative curation and minimum-necessary "
                "presentation before freezing the showcase Composition."
            ),
            scope_kind="portfolio",
            satisfaction_class="curation_review",
            authority_references=("installed_acceptance_policy",),
        ),
    )
    return family, revision, requirements


def _initialize_profiles(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
) -> dict[str, str]:
    stage = "profile_setup"
    from vitrine.profile_services import (
        ProfileBindingContext,
        activate_profile_revision,
        bind_portfolio_profile,
        create_profile_family,
        create_profile_revision,
        get_portfolio_profile_binding,
    )

    actor = _actor()
    improvement_family, improvement_revision, improvement_requirements = (
        _improvement_profile_records(actor)
    )
    showcase_family, showcase_revision, showcase_requirements = (
        _showcase_profile_records(actor)
    )
    for family, revision, requirements in (
        (improvement_family, improvement_revision, improvement_requirements),
        (showcase_family, showcase_revision, showcase_requirements),
    ):
        create_profile_family(
            workspace,
            family,
            expected_state_revision=_state_revision(workspace),
        )
        create_profile_revision(
            workspace,
            revision,
            requirements,
            expected_state_revision=_state_revision(workspace),
        )
        activate_profile_revision(
            workspace,
            revision.reference,
            actor=actor,
            reason="Activate exact installed acceptance Profile Revision.",
            authority_reference="installed_acceptance_policy",
            expected_state_revision=_state_revision(workspace),
            clock=_fixed_clock,
            id_factory=ids,
        )
    bind_portfolio_profile(
        workspace,
        identities["improvement_portfolio_id"],
        improvement_revision.reference,
        actor=actor,
        binding_reason="Bind exact installed improvement Profile Revision.",
        context=ProfileBindingContext(school_year=LATER_SCHOOL_YEAR),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    bind_portfolio_profile(
        workspace,
        identities["showcase_portfolio_id"],
        showcase_revision.reference,
        actor=actor,
        binding_reason="Bind exact installed showcase Profile Revision.",
        context=ProfileBindingContext(school_year=SHOWCASE_SCHOOL_YEAR),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    improvement_binding = get_portfolio_profile_binding(
        workspace, identities["improvement_portfolio_id"]
    )
    showcase_binding = get_portfolio_profile_binding(
        workspace, identities["showcase_portfolio_id"]
    )
    _require(
        improvement_binding is not None
        and improvement_binding.profile_revision == improvement_revision.reference,
        stage,
        "improvement Portfolio did not bind the exact Profile Revision",
    )
    _require(
        showcase_binding is not None
        and showcase_binding.profile_revision == showcase_revision.reference,
        stage,
        "showcase Portfolio did not bind the exact Profile Revision",
    )
    return {
        "improvement_profile_binding_id": cast(Any, improvement_binding).profile_binding_id,
        "showcase_profile_binding_id": cast(Any, showcase_binding).profile_binding_id,
        "improvement_profile_id": improvement_revision.portfolio_profile_id,
        "showcase_profile_id": showcase_revision.portfolio_profile_id,
    }


def _fixture_file(fixture_root: Path, relative: str) -> Path:
    root = fixture_root.resolve(strict=True)
    path = (root / Path(relative)).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise InstalledEndToEndAcceptanceError(
            "core_publication", "fixture input is not an ordinary file inside fixture root"
        )
    return path


def _publish_fixture(
    workspace: Path,
    *,
    class_id: str,
    module_id: str,
    work_id: str,
    producer_contract_version: str,
    manifest_contract_version: str,
    fixture_path: Path,
    source_record: Any | None,
    capabilities: tuple[PublicationCapability, ...],
    record_set_id: str,
) -> dict[str, object]:
    from pds_core.publication_storage import verify_publication_manifest
    from pds_core.registry_services import (
        AcademicWorkRegistrationRequest,
        PublicationManifestRequest,
        get_canonical_publication_record,
        publish_manifest_revision,
        register_academic_work,
    )
    from pds_core.routes import module_work_dir
    from pds_core.routing_models import ModuleWorkRef

    work = ModuleWorkRef(module_id, class_id, work_id)
    work_root = module_work_dir(workspace, work)
    work_root.mkdir(parents=True, exist_ok=True)
    registration = register_academic_work(
        workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version=producer_contract_version,
            title=f"Installed synthetic {work_id}",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=() if source_record is None else (source_record,),
        ),
    ).registration
    target = work_root / "exports" / "manifests" / record_set_id / "1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = fixture_path.read_bytes()
    target.write_bytes(source_bytes)
    publication = publish_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work,
            source_record=source_record,
            publication_kind="academic_result_set",
            capabilities=capabilities,
            record_set_id=record_set_id,
            record_set_revision=1,
            manifest_contract_version=manifest_contract_version,
            manifest_path=target.relative_to(workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    canonical = get_canonical_publication_record(workspace, publication.publication_id)
    verified = verify_publication_manifest(workspace, canonical)
    _require(
        canonical == publication
        and canonical.academic_work_registration_revision
        == registration.registration_revision,
        "core_publication",
        "canonical Publication/registration identity disagreed after publication",
    )
    _require(
        verified == target,
        "core_publication",
        "Core manifest verification did not resolve the exact staged manifest",
    )
    _require(
        target.read_bytes() == source_bytes,
        "core_publication",
        "staged manifest bytes differ from committed fixture input",
    )
    return {
        "publication_id": publication.publication_id,
        "module_id": module_id,
        "class_id": class_id,
        "work_id": work_id,
        "manifest_sha256": _sha256_bytes(source_bytes),
        "manifest_relative_path": target.relative_to(workspace).as_posix(),
        "registration_revision": registration.registration_revision,
    }


def _publish_acceptance_sources(
    workspace: Path,
    fixture_root: Path,
) -> dict[str, dict[str, object]]:
    stage = "core_publication"
    from pds_core.academic_catalog import (
        PublicationCatalogQuery,
        query_publication_catalog,
        rebuild_academic_catalog,
    )
    from pds_core.routing_models import ModuleRecordRef

    published: dict[str, dict[str, object]] = {}
    published["scoreform"] = _publish_fixture(
        workspace,
        class_id=LATER_CLASS_ID,
        module_id="vitrine_scoreform_fixture",
        work_id="argument_assessment",
        producer_contract_version="vitrine_fixture_scoreform_academic_work_v1",
        manifest_contract_version="vitrine_fixture_scoreform_manifest_v1",
        fixture_path=_fixture_file(
            fixture_root, "installed-acceptance/scoreform-manifest.json"
        ),
        source_record=None,
        capabilities=("multiple_attempts", "points", "question_evidence"),
        record_set_id="installed_scoreform_results",
    )
    published["baseline"] = _publish_fixture(
        workspace,
        class_id=BASELINE_CLASS_ID,
        module_id="vitrine_quillan_fixture",
        work_id="baseline_argument",
        producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
        manifest_contract_version="vitrine_fixture_quillan_manifest_v1",
        fixture_path=_fixture_file(
            fixture_root,
            "representative-portfolios/improvement/runtime/baseline-manifest.json",
        ),
        source_record=ModuleRecordRef(
            "vitrine_quillan_fixture",
            "submission",
            "submission_baseline_syn_001",
            "vitrine_fixture_quillan_submission_v1",
        ),
        capabilities=(),
        record_set_id="installed_baseline",
    )
    published["later"] = _publish_fixture(
        workspace,
        class_id=LATER_CLASS_ID,
        module_id="vitrine_quillan_fixture",
        work_id="revised_argument",
        producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
        manifest_contract_version="vitrine_fixture_quillan_manifest_v1",
        fixture_path=_fixture_file(
            fixture_root,
            "representative-portfolios/improvement/runtime/later-manifest.json",
        ),
        source_record=ModuleRecordRef(
            "vitrine_quillan_fixture",
            "submission",
            "submission_revised_syn_001",
            "vitrine_fixture_quillan_submission_v1",
        ),
        capabilities=(),
        record_set_id="installed_later",
    )
    published["polished"] = _publish_fixture(
        workspace,
        class_id=SHOWCASE_CLASS_ID,
        module_id="vitrine_quillan_fixture",
        work_id="literary_analysis",
        producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
        manifest_contract_version="vitrine_fixture_quillan_manifest_v1",
        fixture_path=_fixture_file(
            fixture_root,
            "representative-portfolios/showcase/runtime/polished-manifest.json",
        ),
        source_record=ModuleRecordRef(
            "vitrine_quillan_fixture",
            "submission",
            "submission_showcase_polished",
            "vitrine_fixture_quillan_submission_v1",
        ),
        capabilities=(),
        record_set_id="installed_polished",
    )
    published["concord"] = _publish_fixture(
        workspace,
        class_id=SHOWCASE_CLASS_ID,
        module_id="vitrine_concord_fixture",
        work_id="concord_activity",
        producer_contract_version="vitrine_fixture_concord_academic_work_v1",
        manifest_contract_version="vitrine_fixture_concord_manifest_v1",
        fixture_path=_fixture_file(
            fixture_root,
            "representative-portfolios/showcase/runtime/concord-manifest.json",
        ),
        source_record=ModuleRecordRef(
            "vitrine_concord_fixture",
            "artifact_instance",
            "concord-artifact-syn-001",
            "vitrine_fixture_concord_artifact_v1",
        ),
        capabilities=("criterion_scores",),
        record_set_id="installed_concord",
    )
    rebuild_academic_catalog(workspace)
    rows = query_publication_catalog(
        workspace,
        PublicationCatalogQuery(state="current", limit=20),
    )
    ids = {row.publication_id for row in rows}
    expected = {
        cast(str, item["publication_id"]) for item in published.values()
    }
    _require(
        expected <= ids,
        stage,
        "Core catalog did not expose every installed acceptance Publication",
    )
    return published


class _SourceReadGate:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def authorize(self, request: Any) -> Any:
        from vitrine.candidate_services import SourceReadAuthorizationDecision

        self.requests.append(request)
        return SourceReadAuthorizationDecision(
            outcome="allowed",
            reason_codes=("installed_acceptance_authorized",),
        )


def _discover(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    portfolio_id: str,
    purpose: str,
    class_id: str,
    module_id: str,
    dependencies: Any,
) -> Any:
    from pds_core.academic_catalog import PublicationCatalogQuery

    from vitrine.candidate_services import (
        CandidateDiscoveryRequest,
        discover_and_evaluate_candidates,
    )
    return discover_and_evaluate_candidates(
        workspace,
        CandidateDiscoveryRequest(
            portfolio_id=portfolio_id,
            requesting_actor=_actor(),
            requested_purpose=purpose,
            catalog_query=PublicationCatalogQuery(
                class_id=class_id,
                module_id=module_id,
                state="current",
                limit=10,
            ),
            expected_state_revision=_state_revision(workspace),
        ),
        producer_registry=dependencies.producer_registry,
        adapter_registry=dependencies.adapter_registry,
        authorization_gate=dependencies.source_read_authorization_gate,
        clock=_fixed_clock,
        id_factory=ids,
    )


def _field_map(result: Any) -> dict[str, object]:
    return {field.key: field.value for field in result.projected_source.display_snapshot.fields}


def _candidate_discovery(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
    dependencies: Any,
) -> dict[str, object]:
    stage = "candidate_discovery"
    from vitrine.models import (
        CandidateEvaluation,
        PortfolioCandidate,
        PortfolioSelection,
    )
    from vitrine.storage import load_current_records

    gate = dependencies.source_read_authorization_gate
    _require(
        isinstance(gate, _SourceReadGate),
        stage,
        "installed workflow dependencies lost the explicit source-read gate",
    )
    improvement_results = (
        *_discover(
            workspace,
            ids,
            portfolio_id=identities["improvement_portfolio_id"],
            purpose="improvement",
            class_id=BASELINE_CLASS_ID,
            module_id="vitrine_quillan_fixture",
            dependencies=dependencies,
        ).evaluation_results,
        *_discover(
            workspace,
            ids,
            portfolio_id=identities["improvement_portfolio_id"],
            purpose="improvement",
            class_id=LATER_CLASS_ID,
            module_id="vitrine_quillan_fixture",
            dependencies=dependencies,
        ).evaluation_results,
        *_discover(
            workspace,
            ids,
            portfolio_id=identities["improvement_portfolio_id"],
            purpose="improvement",
            class_id=LATER_CLASS_ID,
            module_id="vitrine_scoreform_fixture",
            dependencies=dependencies,
        ).evaluation_results,
    )
    showcase_results = (
        *_discover(
            workspace,
            ids,
            portfolio_id=identities["showcase_portfolio_id"],
            purpose="showcase",
            class_id=SHOWCASE_CLASS_ID,
            module_id="vitrine_quillan_fixture",
            dependencies=dependencies,
        ).evaluation_results,
        *_discover(
            workspace,
            ids,
            portfolio_id=identities["showcase_portfolio_id"],
            purpose="showcase",
            class_id=SHOWCASE_CLASS_ID,
            module_id="vitrine_concord_fixture",
            dependencies=dependencies,
        ).evaluation_results,
    )
    _require(
        all(item.candidate is not None for item in improvement_results),
        stage,
        "an expected improvement projection did not produce a Candidate",
    )
    improvement_ids = tuple(
        item.projected_source.producer_source.source_record_id
        for item in improvement_results
    )
    _require(
        set(improvement_ids)
        == {
            "baseline_argument",
            "revised_argument",
            "revised_feedback",
            "argument_assessment_attempt_1",
            "argument_assessment_attempt_2",
        },
        stage,
        "improvement Candidate source inventory is not exact",
    )
    scoreform = tuple(
        item
        for item in improvement_results
        if item.projected_source.projection_kind == "scoreform_fixture:attempt_summary"
    )
    _require(len(scoreform) == 2, stage, "ScoreForm attempt inventory is not exact")
    native_revisions = tuple(
        item.projected_source.producer_source.native_revision for item in scoreform
    )
    _require(
        native_revisions == (1, 2),
        stage,
        "ScoreForm native attempt revisions were reordered or collapsed",
    )
    fields = tuple(_field_map(item) for item in scoreform)
    _require(
        tuple(item["points_earned"] for item in fields) == (7, 9)
        and fields[0]["response_states"]
        == ("1:selected", "2:blank", "3:ambiguous")
        and fields[1]["response_states"]
        == ("1:selected", "2:selected", "3:selected"),
        stage,
        "ScoreForm attempt/response semantics were not preserved",
    )
    scoreform_rendered = repr(scoreform)
    for marker in (
        "PRIVATE_ANSWER_KEY",
        "PRIVATE_DETECTOR",
        "PRIVATE_ROUTE",
        "PRIVATE_SCAN_REVIEW_NOTE",
        "proficiency",
        "mastery",
        "Grade",
        "official",
    ):
        _require(
            marker not in scoreform_rendered,
            stage,
            "ScoreForm Candidate projection leaked or inferred prohibited semantics",
        )

    polished = tuple(
        item
        for item in showcase_results
        if item.projected_source.producer_source.source_record_id
        == "polished_literary_analysis"
    )
    _require(
        len(polished) == 1 and polished[0].candidate is not None,
        stage,
        "polished showcase Candidate is absent",
    )
    concord_artifacts = tuple(
        item
        for item in showcase_results
        if item.projected_source.projection_kind == "concord_fixture:artifact"
    )
    _require(
        len(concord_artifacts) == 1 and concord_artifacts[0].candidate is not None,
        stage,
        "Concord collaborative Artifact Candidate is absent",
    )
    artifact = concord_artifacts[0]
    relationships = artifact.projected_source.source_relationships
    student_kinds = {
        item.relationship_kind
        for item in relationships
        if item.source_subject_kind == "core_student"
        and item.source_subject_id == STUDENT_ID
    }
    _require(
        {"group_member", "artifact_subject", "documented_contributor"}
        <= student_kinds
        and "artifact_author" not in student_kinds,
        stage,
        "Concord student relationships collapsed membership/subject/contribution/authorship",
    )
    group_kinds = {
        item.relationship_kind
        for item in relationships
        if item.source_subject_kind == "concord_group"
    }
    _require(
        {"artifact_author", "artifact_subject", "represented_group"} <= group_kinds,
        stage,
        "Concord Group authorship/subject/representation semantics were not preserved",
    )
    candidate = artifact.candidate
    _require(
        candidate.condition_state == "collaborator_review_required"
        and candidate.eligible_section_ids == ("collaboration",),
        stage,
        "Concord collaborative Candidate condition/eligibility is not exact",
    )
    score_results = tuple(
        item
        for item in showcase_results
        if item.projected_source.projection_kind == "concord_fixture:score_summary"
    )
    _require(
        len(score_results) == 2
        and all(item.candidate is None for item in score_results)
        and all(item.evaluation.outcome == "unresolved" for item in score_results),
        stage,
        "Concord Group Score projection incorrectly created an individual Candidate",
    )
    for score in score_results:
        score_fields = _field_map(score)
        _require(
            score_fields["target_kind"] == "concord_group"
            and score.projected_source.source_relationships[0].relationship_kind
            == "group_score_target",
            stage,
            "Concord Group Score target was substituted",
        )
    deferred = next(
        item for item in score_results if _field_map(item)["disposition"] == "deferred"
    )
    _require(
        "native_value" not in _field_map(deferred),
        stage,
        "deferred Concord non-score acquired a value",
    )

    records = load_current_records(workspace)
    evaluations = tuple(item for item in records if isinstance(item, CandidateEvaluation))
    candidates = tuple(item for item in records if isinstance(item, PortfolioCandidate))
    selections = tuple(item for item in records if isinstance(item, PortfolioSelection))
    _require(
        not selections,
        stage,
        "Candidate discovery silently created Selection state",
    )
    _require(
        len(evaluations) == len(improvement_results) + len(showcase_results),
        stage,
        "persisted Candidate Evaluation inventory differs from discovery results",
    )
    _require(
        len(candidates)
        == len([item for item in improvement_results if item.candidate is not None])
        + len([item for item in showcase_results if item.candidate is not None]),
        stage,
        "persisted Candidate inventory differs from discovery results",
    )
    _require(
        len(gate.requests) == 5,
        stage,
        "source-read authorization was not requested once per canonical Publication",
    )
    return {
        "improvement_projection_count": len(improvement_results),
        "showcase_projection_count": len(showcase_results),
        "candidate_count": len(candidates),
        "evaluation_count": len(evaluations),
        "selection_count": 0,
        "source_read_authorization_requests": len(gate.requests),
        "improvement_source_record_ids": tuple(sorted(improvement_ids)),
        "scoreform_attempt_native_revisions": native_revisions,
        "scoreform_attempt_points": tuple(item["points_earned"] for item in fields),
        "concord_student_relationships": tuple(sorted(student_kinds)),
        "concord_group_relationships": tuple(sorted(group_kinds)),
        "concord_score_projection_count": len(score_results),
    }


class _CurationGate:
    """Explicit acceptance-only curation authority with condition acknowledgement."""

    def __init__(self) -> None:
        self.requests: list[Any] = []

    def authorize(self, request: Any) -> Any:
        from vitrine.curation_services import CurationAuthorityDecision

        self.requests.append(request)
        condition = request.candidate_condition_state
        acknowledged = (
            (condition,)
            if condition is not None and condition != "ready_for_consideration"
            else ()
        )
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="installed_acceptance_curation_authority",
            reason_codes=("installed_acceptance",),
            acknowledged_condition_codes=acknowledged,
        )


def _candidate_by_source(
    workspace: Path,
    *,
    portfolio_id: str,
    source_record_id: str,
    stage: str,
) -> Any:
    from vitrine.models import PortfolioCandidate
    from vitrine.storage import load_current_records

    matches = tuple(
        item
        for item in load_current_records(workspace)
        if isinstance(item, PortfolioCandidate)
        and item.portfolio_id == portfolio_id
        and item.source_endpoint.producer_source.source_record_id == source_record_id
    )
    if len(matches) != 1:
        raise InstalledEndToEndAcceptanceError(
            stage,
            "exact Candidate source identity did not resolve uniquely",
        )
    return matches[0]


def _arrangement_pointer_revision(
    workspace: Path,
    *,
    portfolio_id: str,
    profile_binding_id: str,
    section_id: str,
    stage: str,
) -> int | None:
    from vitrine.curation_state import project_curation_state
    from vitrine.storage import load_current_records

    state = project_curation_state(load_current_records(workspace))
    heads = state.arrangement_pointer_heads(
        portfolio_id, profile_binding_id, section_id
    )
    if not heads:
        return None
    if len(heads) != 1:
        raise InstalledEndToEndAcceptanceError(
            stage,
            "section Arrangement pointer is conflicted",
        )
    return heads[0].pointer_revision


def _select_with_proposal(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    portfolio_id: str,
    candidate: Any,
    section_id: str,
    requirement_id: str,
    gate: _CurationGate,
) -> Any:
    from vitrine.curation_services import (
        decide_selection_proposal,
        propose_candidate_selection,
    )
    from vitrine.models import PortfolioSelection, SelectionProposal

    proposed = propose_candidate_selection(
        workspace,
        portfolio_id=portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=_student_actor(),
        proposal_origin="student",
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=(requirement_id,),
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        rationale_text="Installed acceptance explicit student curation proposal.",
        clock=_fixed_clock,
        id_factory=ids,
    )
    proposal = next(
        item for item in proposed.records if isinstance(item, SelectionProposal)
    )
    decided = decide_selection_proposal(
        workspace,
        portfolio_id=portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="accepted",
        decided_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        rationale_text="Installed acceptance accepts this exact Candidate only.",
        clock=_fixed_clock,
        id_factory=ids,
    )
    return next(
        item for item in decided.records if isinstance(item, PortfolioSelection)
    )


def _select_directly(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    portfolio_id: str,
    candidate: Any,
    section_id: str,
    requirement_id: str,
    gate: _CurationGate,
) -> Any:
    from vitrine.curation_services import select_candidate_directly
    from vitrine.models import PortfolioSelection

    selected = select_candidate_directly(
        workspace,
        portfolio_id=portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=_actor(),
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=(requirement_id,),
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        rationale_text="Installed acceptance explicit teacher direct Selection.",
        clock=_fixed_clock,
        id_factory=ids,
    )
    return next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )


def _place_curation_selection(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    portfolio_id: str,
    profile_binding_id: str,
    selection: Any,
    section_id: str,
    gate: _CurationGate,
    stage: str,
) -> Any:
    from vitrine.curation_services import place_selection
    from vitrine.models import PortfolioPlacement

    placed = place_selection(
        workspace,
        portfolio_id=portfolio_id,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=_student_actor(),
        expected_state_revision=_state_revision(workspace),
        expected_arrangement_pointer_revision=_arrangement_pointer_revision(
            workspace,
            portfolio_id=portfolio_id,
            profile_binding_id=profile_binding_id,
            section_id=section_id,
            stage=stage,
        ),
        authority_gate=gate,
        clock=_fixed_clock,
        id_factory=ids,
    )
    return next(
        item for item in placed.records if isinstance(item, PortfolioPlacement)
    )


def _improvement_curation(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
    profiles: dict[str, str],
    dependencies: Any,
) -> dict[str, object]:
    stage = "improvement_curation"
    from vitrine.audience_services import create_audience_context
    from vitrine.curation_services import (
        create_reflection,
        create_working_composition,
    )
    from vitrine.curation_state import project_curation_state
    from vitrine.models import (
        CurationTargetRef,
        PortfolioReflection,
        PortfolioSelection,
        WorkingPortfolioCompositionInventory,
        WorkingPortfolioCompositionRevision,
    )
    from vitrine.storage import load_current_records

    portfolio_id = identities["improvement_portfolio_id"]
    binding_id = profiles["improvement_profile_binding_id"]
    gate = dependencies.curation_authority_gate
    _require(
        isinstance(gate, _CurationGate),
        stage,
        "installed workflow dependencies lost the explicit curation gate",
    )
    authority_requests_before = len(gate.requests)
    baseline = _candidate_by_source(
        workspace, portfolio_id=portfolio_id, source_record_id="baseline_argument", stage=stage
    )
    later = _candidate_by_source(
        workspace, portfolio_id=portfolio_id, source_record_id="revised_argument", stage=stage
    )
    feedback = _candidate_by_source(
        workspace, portfolio_id=portfolio_id, source_record_id="revised_feedback", stage=stage
    )
    scoreform_1 = _candidate_by_source(
        workspace,
        portfolio_id=portfolio_id,
        source_record_id="argument_assessment_attempt_1",
        stage=stage,
    )
    scoreform_2 = _candidate_by_source(
        workspace,
        portfolio_id=portfolio_id,
        source_record_id="argument_assessment_attempt_2",
        stage=stage,
    )
    selections = (
        _select_with_proposal(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            candidate=baseline,
            section_id="baseline",
            requirement_id="installed_baseline_requirement",
            gate=gate,
        ),
        _select_with_proposal(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            candidate=later,
            section_id="later_work",
            requirement_id="installed_later_work_requirement",
            gate=gate,
        ),
        _select_with_proposal(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            candidate=feedback,
            section_id="later_work",
            requirement_id="installed_later_work_requirement",
            gate=gate,
        ),
    )
    placements = (
        _place_curation_selection(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            profile_binding_id=binding_id,
            selection=selections[0],
            section_id="baseline",
            gate=gate,
            stage=stage,
        ),
        _place_curation_selection(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            profile_binding_id=binding_id,
            selection=selections[1],
            section_id="later_work",
            gate=gate,
            stage=stage,
        ),
        _place_curation_selection(
            workspace,
            ids,
            portfolio_id=portfolio_id,
            profile_binding_id=binding_id,
            selection=selections[2],
            section_id="later_work",
            gate=gate,
            stage=stage,
        ),
    )
    reflected = create_reflection(
        workspace,
        portfolio_id=portfolio_id,
        reflection_requirement_id="installed_improvement_reflection",
        prompt_id="installed_compare_baseline_later",
        prompt_version="1",
        prompt_snapshot="Compare the exact baseline and later writing and explain what changed.",
        author=_student_actor(),
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[0].selection_id,
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[1].selection_id,
                semantic_role="later",
            ),
        ),
        content=(
            "I made the later claim more specific and connected each quoted detail "
            "to my reasoning. This comparison refers only to my exact selected work."
        ),
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        clock=_fixed_clock,
        id_factory=ids,
    )
    reflection = next(
        item for item in reflected.records if isinstance(item, PortfolioReflection)
    )
    composed = create_working_composition(
        workspace,
        portfolio_id=portfolio_id,
        created_by=_student_actor(),
        expected_state_revision=_state_revision(workspace),
        expected_composition_pointer_revision=None,
        authority_gate=gate,
        composition_note="Freeze exact installed improvement curation state.",
        clock=_fixed_clock,
        id_factory=ids,
    )
    composition = next(
        item
        for item in composed.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in composed.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    audience = create_audience_context(
        workspace,
        portfolio_id=portfolio_id,
        audience_rule_id="installed_improvement_student",
        created_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    ).context

    state = project_curation_state(load_current_records(workspace))
    active = state.active_selections(
        portfolio_id=portfolio_id, profile_binding_id=binding_id
    )
    _require(
        {item.selection_id for item in active}
        == {item.selection_id for item in selections},
        stage,
        "improvement active Selection inventory is not exact",
    )
    selected_candidates = {item.candidate_id for item in active}
    _require(
        scoreform_1.candidate_id not in selected_candidates
        and scoreform_2.candidate_id not in selected_candidates,
        stage,
        "ScoreForm attempts were implicitly selected by improvement policy",
    )
    _require(
        tuple(composition.selection_ids) == tuple(item.selection_id for item in selections),
        stage,
        "improvement Composition Selection inventory is not exact",
    )
    _require(
        tuple(composition.placement_ids) == tuple(item.placement_id for item in placements),
        stage,
        "improvement Composition Placement inventory is not exact",
    )
    _require(
        inventory.unresolved_obligation_codes == (),
        stage,
        "improvement Composition has unresolved obligations",
    )
    _require(
        any(
            ref.record_kind == "reflection"
            and ref.record_id == reflection.reflection_id
            and ref.revision == reflection.reflection_revision
            for ref in inventory.included_curation_revisions
        ),
        stage,
        "improvement Composition did not freeze exact Reflection revision",
    )
    _require(
        audience.profile_binding_id == binding_id
        and audience.profile_revision == composition.profile_revision,
        stage,
        "improvement Audience Context is not bound to exact Profile revision",
    )
    _require(
        all(isinstance(item, PortfolioSelection) for item in selections),
        stage,
        "improvement Selection records are invalid",
    )
    return {
        "selection_ids": tuple(item.selection_id for item in selections),
        "placement_ids": tuple(item.placement_id for item in placements),
        "reflection_id": reflection.reflection_id,
        "reflection_revision": reflection.reflection_revision,
        "composition_revision": composition.composition_revision,
        "composition_selection_count": len(composition.selection_ids),
        "composition_placement_count": len(composition.placement_ids),
        "unresolved_obligation_codes": inventory.unresolved_obligation_codes,
        "audience_context_id": audience.audience_context_id,
        "scoreform_attempts_selected": False,
        "authority_request_count": len(gate.requests) - authority_requests_before,
    }


def _showcase_curation(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
    profiles: dict[str, str],
    dependencies: Any,
) -> dict[str, object]:
    stage = "showcase_curation"
    from vitrine.audience_services import create_audience_context
    from vitrine.curation_services import (
        create_annotation,
        create_working_composition,
        review_curation_target,
    )
    from vitrine.curation_state import project_curation_state
    from vitrine.models import (
        CurationAnnotation,
        CurationReviewDecision,
        CurationTargetRef,
        WorkingPortfolioCompositionInventory,
        WorkingPortfolioCompositionRevision,
    )
    from vitrine.storage import load_current_records

    portfolio_id = identities["showcase_portfolio_id"]
    binding_id = profiles["showcase_profile_binding_id"]
    gate = dependencies.curation_authority_gate
    _require(
        isinstance(gate, _CurationGate),
        stage,
        "installed workflow dependencies lost the explicit curation gate",
    )
    authority_requests_before = len(gate.requests)
    polished = _candidate_by_source(
        workspace,
        portfolio_id=portfolio_id,
        source_record_id="polished_literary_analysis",
        stage=stage,
    )
    collaborative = _candidate_by_source(
        workspace,
        portfolio_id=portfolio_id,
        source_record_id="concord-artifact-syn-001",
        stage=stage,
    )
    polished_selection = _select_directly(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        candidate=polished,
        section_id="featured_work",
        requirement_id="installed_featured_work_requirement",
        gate=gate,
    )
    collaborative_selection = _select_directly(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        candidate=collaborative,
        section_id="collaboration",
        requirement_id="installed_collaboration_requirement",
        gate=gate,
    )
    polished_placement = _place_curation_selection(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        profile_binding_id=binding_id,
        selection=polished_selection,
        section_id="featured_work",
        gate=gate,
        stage=stage,
    )
    collaborative_placement = _place_curation_selection(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        profile_binding_id=binding_id,
        selection=collaborative_selection,
        section_id="collaboration",
        gate=gate,
        stage=stage,
    )
    attribution_result = create_annotation(
        workspace,
        portfolio_id=portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=collaborative_selection.selection_id,
                semantic_role="collaborative_artifact",
            ),
        ),
        author=_actor(),
        content=(
            "Audience-safe attribution: Created by the synthetic group. The Portfolio "
            "Subject contributed the methods paragraph and chart explanation. "
            "Collaborator display names are intentionally omitted."
        ),
        intended_presentation_class="showcase",
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        clock=_fixed_clock,
        id_factory=ids,
    )
    attribution = next(
        item for item in attribution_result.records if isinstance(item, CurationAnnotation)
    )
    rationale_result = create_annotation(
        workspace,
        portfolio_id=portfolio_id,
        purpose="comparison_note",
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=polished_selection.selection_id,
                semantic_role="individual_work",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=collaborative_selection.selection_id,
                semantic_role="collaborative_artifact",
            ),
        ),
        author=_student_actor(),
        content=(
            "The individual analysis demonstrates close reading. The collaborative "
            "artifact demonstrates my documented contribution to shared work."
        ),
        intended_presentation_class="showcase",
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        clock=_fixed_clock,
        id_factory=ids,
    )
    rationale = next(
        item for item in rationale_result.records if isinstance(item, CurationAnnotation)
    )
    reviewed = review_curation_target(
        workspace,
        portfolio_id=portfolio_id,
        target_scope="showcase_collaborator_treatment",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=collaborative_selection.selection_id,
                semantic_role="reviewed_artifact",
            ),
            CurationTargetRef(
                target_kind="annotation",
                target_id=attribution.annotation_id,
                target_revision=attribution.annotation_revision,
                semantic_role="audience_safe_attribution",
            ),
        ),
        decision="approved",
        reviewed_by=_actor(),
        reason=(
            "Exact synthetic bytes and attribution omit collaborator display names, "
            "preserve collective Group authorship, and preserve the documented "
            "Portfolio Subject contribution. This curation review is not disclosure "
            "authorization."
        ),
        approval_requirement_id="installed_showcase_collaborator_review",
        expected_state_revision=_state_revision(workspace),
        authority_gate=gate,
        clock=_fixed_clock,
        id_factory=ids,
    )
    review = next(
        item
        for item in reviewed.records
        if isinstance(item, CurationReviewDecision)
    )
    composed = create_working_composition(
        workspace,
        portfolio_id=portfolio_id,
        created_by=_student_actor(),
        expected_state_revision=_state_revision(workspace),
        expected_composition_pointer_revision=None,
        authority_gate=gate,
        composition_note="Freeze exact installed showcase curation state.",
        clock=_fixed_clock,
        id_factory=ids,
    )
    composition = next(
        item
        for item in composed.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in composed.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    audience = create_audience_context(
        workspace,
        portfolio_id=portfolio_id,
        audience_rule_id="installed_showcase_external",
        created_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    ).context

    state = project_curation_state(load_current_records(workspace))
    active = state.active_selections(
        portfolio_id=portfolio_id, profile_binding_id=binding_id
    )
    _require(
        {item.selection_id for item in active}
        == {polished_selection.selection_id, collaborative_selection.selection_id},
        stage,
        "showcase active Selection inventory is not exact",
    )
    _require(
        collaborative.condition_state == "collaborator_review_required",
        stage,
        "showcase collaborative Candidate condition was lost",
    )
    _require(
        inventory.unresolved_obligation_codes
        == ("collaborator_review_required",),
        stage,
        "showcase Composition did not retain the exact acknowledged Candidate condition",
    )
    _require(
        review.approval_requirement_id == "installed_showcase_collaborator_review"
        and review.decision == "approved",
        stage,
        "showcase collaborator review is not exact",
    )
    _require(
        attribution.annotation_id != rationale.annotation_id
        and attribution.author.actor_kind == "authorized_adult"
        and rationale.author.actor_kind == "core_student",
        stage,
        "showcase attribution/rationale authorship was collapsed",
    )
    _require(
        tuple(composition.selection_ids)
        == (polished_selection.selection_id, collaborative_selection.selection_id),
        stage,
        "showcase Composition Selection inventory is not exact",
    )
    _require(
        tuple(composition.placement_ids)
        == (polished_placement.placement_id, collaborative_placement.placement_id),
        stage,
        "showcase Composition Placement inventory is not exact",
    )
    _require(
        audience.profile_binding_id == binding_id
        and audience.profile_revision == composition.profile_revision
        and audience.audience_class == "external_reviewer",
        stage,
        "showcase Audience Context is not exact",
    )
    _require(
        "raw_collaborator_data" in audience.prohibited_content_classes
        and "private_teacher_note" in audience.prohibited_content_classes,
        stage,
        "showcase Audience Context lost prohibited content classes",
    )
    return {
        "selection_ids": (
            polished_selection.selection_id,
            collaborative_selection.selection_id,
        ),
        "placement_ids": (
            polished_placement.placement_id,
            collaborative_placement.placement_id,
        ),
        "attribution_annotation_id": attribution.annotation_id,
        "rationale_annotation_id": rationale.annotation_id,
        "collaborator_review_id": review.curation_review_decision_id,
        "collaborator_review_decision": review.decision,
        "composition_revision": composition.composition_revision,
        "unresolved_obligation_codes": inventory.unresolved_obligation_codes,
        "audience_context_id": audience.audience_context_id,
        "audience_class": audience.audience_class,
        "collaborative_condition": collaborative.condition_state,
        "authority_request_count": len(gate.requests) - authority_requests_before,
    }


SNAPSHOT_EXPORT_CONFIGURATION = (
    b'{"export_format":"directory_package","internal_manifest":false}\n'
)
REFLECTION_RENDERER_CONFIGURATION = (
    b'{"format":"markdown","renderer":"installed_reflection"}\n'
)
REFLECTION_RENDERER_TEMPLATE = b"# Student Reflection\n\n{content}\n"
SHOWCASE_ATTRIBUTION_CONFIGURATION = (
    b'{"format":"text","renderer":"installed_showcase_attribution"}\n'
)
SHOWCASE_ATTRIBUTION_TEMPLATE = b"{content}\n"
SHOWCASE_RATIONALE_CONFIGURATION = (
    b'{"format":"markdown","renderer":"installed_showcase_rationale"}\n'
)
SHOWCASE_RATIONALE_TEMPLATE = b"# Showcase Rationale\n\n{content}\n"
SHOWCASE_INDEX_CONFIGURATION = (
    b'{"format":"markdown","renderer":"installed_showcase_index"}\n'
)
SHOWCASE_INDEX_TEMPLATE = (
    b"# Showcase Portfolio Index\n\n"
    b"This synthetic external-review package contains only explicitly curated entries.\n"
)


def _snapshot_digest(value: bytes) -> Any:
    from vitrine.models import DigestReference

    return DigestReference(value=hashlib.sha256(value).hexdigest())


@dataclass
class _InstalledSnapshotSourceProvider:
    descriptor: Any
    source_root: Path
    allowed: dict[tuple[str, str], str]

    def resolve(self, request: Any) -> Any:
        from vitrine.snapshot_materialization import (
            SnapshotMaterializationError,
            SnapshotSourceResult,
        )

        artifact = request.entry_plan.source_artifact
        publication_id = request.entry_plan.source_publication_id
        if artifact is None or publication_id is None:
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Installed source request lacks exact planned source identity.",
                stage="installed_source_resolution",
            )
        key = (publication_id, artifact.artifact_id)
        expected = self.allowed.get(key)
        if (
            expected is None
            or artifact.source_locator is None
            or artifact.source_locator != expected
        ):
            raise SnapshotMaterializationError(
                "snapshot.source_unavailable",
                "Installed source provider refuses an unplanned source locator.",
                stage="installed_source_resolution",
            )
        return SnapshotSourceResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=publication_id,
            source_artifact_id=artifact.artifact_id,
            source_root=self.source_root,
            source_relative_path=expected,
        )

    def confirm_stability(self, request: Any, result: Any) -> bool:
        artifact = request.entry_plan.source_artifact
        return (
            artifact is not None
            and result.source_publication_id == request.entry_plan.source_publication_id
            and result.source_artifact_id == artifact.artifact_id
        )


@dataclass
class _InstalledSnapshotRenderer:
    descriptor: Any
    expected_inputs: tuple[Any, ...]
    content: bytes
    media_type: str
    configuration: bytes
    template: bytes

    def render(self, request: Any) -> Any:
        from vitrine.snapshot_materialization import (
            SnapshotMaterializationError,
            SnapshotRenderResult,
        )

        if request.entry_plan.input_references != self.expected_inputs:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Installed renderer received inputs other than the exact frozen references.",
                stage="installed_render",
            )
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=self.content,
            media_type=self.media_type,
            configuration_digest=_snapshot_digest(self.configuration),
            template_digest=_snapshot_digest(self.template),
            language="en",
        )


class _InstalledSnapshotAuthorityGate:
    def authorize(self, request: Any) -> Any:
        from vitrine.snapshot_materialization import SnapshotBuildAuthorityDecision

        if request.operation != "build_snapshot":
            return SnapshotBuildAuthorityDecision(outcome="denied")
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="installed_acceptance_snapshot_build_authority",
        )


class _DeferredSnapshotSourceRegistry(_SnapshotSourceProviderRegistryBase):
    """One stable real registry slot configured with exact per-stage providers."""

    def __init__(self) -> None:
        super().__init__()
        self._delegate = _SnapshotSourceProviderRegistryBase()

    def configure(self, registry: _SnapshotSourceProviderRegistryBase) -> None:
        self._delegate = registry

    def select(self, entry_plan: Any) -> Any:
        return self._delegate.select(entry_plan)


class _DeferredSnapshotRendererRegistry(_SnapshotRendererRegistryBase):
    """One stable real registry slot configured with exact per-stage renderers."""

    def __init__(self) -> None:
        super().__init__()
        self._delegate = _SnapshotRendererRegistryBase()

    def configure(self, registry: _SnapshotRendererRegistryBase) -> None:
        self._delegate = registry

    def select(self, entry_plan: Any) -> Any:
        return self._delegate.select(entry_plan)


def _build_installed_workflow_dependencies() -> Any:
    """Construct the one explicit dependency context shared by the installed flow."""

    from vitrine.development_adapters import build_development_fixture_adapter_registry
    from vitrine.development_candidate_fixtures import (
        build_development_fixture_producer_registry,
    )
    from vitrine.snapshot_planning import UnconfiguredSnapshotPlanningProvider
    from vitrine.workflow_context import VitrineWorkflowDependencies

    return VitrineWorkflowDependencies(
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=_SourceReadGate(),
        curation_authority_gate=_CurationGate(),
        snapshot_build_authority_gate=_InstalledSnapshotAuthorityGate(),
        snapshot_source_providers=cast(Any, _DeferredSnapshotSourceRegistry()),
        snapshot_renderers=cast(Any, _DeferredSnapshotRendererRegistry()),
        snapshot_planning_provider=UnconfiguredSnapshotPlanningProvider(),
        development_fixture_mode=True,
    )


def _dependency_report(dependencies: Any) -> dict[str, object]:
    return {
        "context_type": type(dependencies).__name__,
        "development_fixture_mode": dependencies.development_fixture_mode,
        "producer_profile_ids": tuple(
            item.module_id for item in dependencies.producer_registry.profiles
        ),
        "adapter_count": len(dependencies.adapter_registry.adapters),
        "source_read_gate": type(dependencies.source_read_authorization_gate).__name__,
        "curation_authority_gate": type(dependencies.curation_authority_gate).__name__,
        "snapshot_build_authority_gate": type(
            dependencies.snapshot_build_authority_gate
        ).__name__,
        "snapshot_source_registry": type(
            dependencies.snapshot_source_providers
        ).__name__,
        "snapshot_renderer_registry": type(dependencies.snapshot_renderers).__name__,
        "snapshot_planning_provider": type(
            dependencies.snapshot_planning_provider
        ).__name__,
    }


def _snapshot_source_root(fixture_root: Path, workspace: Path) -> Path:
    stage = "improvement_snapshot"
    source = _fixture_file(
        fixture_root,
        "installed-acceptance/source-root/artifacts/baseline-argument.txt",
    ).parent.parent
    expected = {
        "artifacts/baseline-argument.txt",
        "artifacts/revised-argument.txt",
        "artifacts/revised-feedback.txt",
        "artifacts/polished-literary-analysis.txt",
        "artifacts/group-artifact.txt",
    }
    actual = {
        item.relative_to(source).as_posix()
        for item in source.rglob("*")
        if item.is_file()
    }
    _require(actual == expected, stage, "installed Snapshot source fixture inventory is not exact")
    target = workspace.parent / "producer-source"
    _require(not target.exists(), stage, "temporary producer source root already exists")
    shutil.copytree(source, target)
    _require(
        {item.relative_to(target).as_posix() for item in target.rglob("*") if item.is_file()}
        == expected,
        stage,
        "temporary producer source staging inventory is not exact",
    )
    return target.resolve(strict=True)


def _selected_snapshot_bundle(
    workspace: Path,
    *,
    portfolio_id: str,
    source_record_id: str,
    stage: str,
) -> tuple[Any, Any, Any]:
    from vitrine.models import (
        PortfolioCandidate,
        PortfolioPlacement,
        PortfolioSelection,
    )
    from vitrine.storage import load_current_records

    records = load_current_records(workspace)
    candidates = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and item.portfolio_id == portfolio_id
        and item.source_endpoint.producer_source.source_record_id == source_record_id
    )
    _require(len(candidates) == 1, stage, "exact Snapshot Candidate did not resolve")
    candidate = candidates[0]
    selections = tuple(
        item
        for item in records
        if isinstance(item, PortfolioSelection)
        and item.portfolio_id == portfolio_id
        and item.candidate_id == candidate.candidate_id
    )
    _require(len(selections) == 1, stage, "exact Snapshot Selection did not resolve")
    selection = selections[0]
    placements = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPlacement)
        and item.portfolio_id == portfolio_id
        and item.selection_id == selection.selection_id
    )
    _require(len(placements) == 1, stage, "exact Snapshot Placement did not resolve")
    return candidate, selection, placements[0]


def _copied_snapshot_entry(
    workspace: Path,
    *,
    portfolio_id: str,
    source_record_id: str,
    entry_plan_id: str,
    position: int,
    section_id: str,
    ordinal: int,
    semantic_role: str,
    content_class: str,
    target_relative_path: str,
    stage: str,
    required_review_ids: tuple[str, ...] = (),
) -> Any:
    from vitrine.models import SnapshotEntryPlan

    candidate, selection, placement = _selected_snapshot_bundle(
        workspace,
        portfolio_id=portfolio_id,
        source_record_id=source_record_id,
        stage=stage,
    )
    artifact = candidate.source_endpoint.source_artifact
    _require(
        artifact is not None and artifact.source_locator is not None,
        stage,
        "copied Snapshot Candidate lacks an exact source Artifact locator",
    )
    assert artifact is not None
    return SnapshotEntryPlan(
        entry_plan_id=entry_plan_id,
        plan_position=position,
        section_id=section_id,
        ordinal=ordinal,
        semantic_role=semantic_role,
        materialization_kind="copied_source",
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target_relative_path,
        media_type=artifact.media_type,
        required_review_ids=required_review_ids,
    )


def _snapshot_provider_registry(
    entries: tuple[Any, ...], source_root: Path, *, stage: str
) -> Any:
    from vitrine.snapshot_materialization import (
        SnapshotSourceProviderDescriptor,
        SnapshotSourceProviderRegistry,
    )

    grouped: dict[tuple[str, str, str, str, str], dict[tuple[str, str], str]] = {}
    for entry in entries:
        if entry.materialization_kind != "copied_source":
            continue
        artifact = entry.source_artifact
        if (
            artifact is None
            or artifact.source_locator is None
            or entry.source_publication_id is None
            or entry.producer_module_id is None
            or entry.projection_kind is None
            or entry.projection_contract_version is None
        ):
            raise InstalledEndToEndAcceptanceError(
                stage,
                "copied Snapshot Entry Plan lacks exact provider support identity",
            )
        support = (
            entry.producer_module_id,
            entry.projection_kind,
            entry.projection_contract_version,
            artifact.artifact_kind,
            artifact.representation_kind,
        )
        grouped.setdefault(support, {})[(entry.source_publication_id, artifact.artifact_id)] = (
            artifact.source_locator
        )
    providers = tuple(
        _InstalledSnapshotSourceProvider(
            descriptor=SnapshotSourceProviderDescriptor(
                provider_id=f"installed_snapshot_source_provider_{index}",
                provider_version="1",
                producer_module_id=support[0],
                projection_kind=support[1],
                projection_contract_version=support[2],
                artifact_kind=support[3],
                representation_kind=support[4],
            ),
            source_root=source_root,
            allowed=allowed,
        )
        for index, (support, allowed) in enumerate(sorted(grouped.items()), start=1)
    )
    return SnapshotSourceProviderRegistry(providers)


def _improvement_snapshot_entries(
    workspace: Path, portfolio_id: str
) -> tuple[tuple[Any, ...], Any]:
    stage = "improvement_snapshot"
    from vitrine.models import (
        PortfolioReflection,
        SnapshotEntryPlan,
        SnapshotInputReference,
    )
    from vitrine.snapshot_materialization import (
        SnapshotRendererDescriptor,
        SnapshotRendererRegistry,
    )
    from vitrine.storage import load_current_records

    records = load_current_records(workspace)
    reflections = tuple(
        item
        for item in records
        if isinstance(item, PortfolioReflection) and item.portfolio_id == portfolio_id
    )
    _require(len(reflections) == 1, stage, "exact improvement Reflection did not resolve")
    reflection = reflections[0]
    composition_revision = 1
    reflection_inputs = (
        SnapshotInputReference(
            record_type="portfolio_reflection",
            record_id=reflection.reflection_id,
            record_revision=reflection.reflection_revision,
        ),
        SnapshotInputReference(
            record_type="working_portfolio_composition_revision",
            record_id=portfolio_id,
            record_revision=composition_revision,
        ),
    )
    entries = (
        _copied_snapshot_entry(
            workspace,
            portfolio_id=portfolio_id,
            source_record_id="baseline_argument",
            entry_plan_id="installed_imp_baseline_entry",
            position=1,
            section_id="baseline",
            ordinal=1,
            semantic_role="baseline_work",
            content_class="student_work",
            target_relative_path="baseline/argument.txt",
            stage=stage,
        ),
        _copied_snapshot_entry(
            workspace,
            portfolio_id=portfolio_id,
            source_record_id="revised_argument",
            entry_plan_id="installed_imp_later_entry",
            position=2,
            section_id="later_work",
            ordinal=1,
            semantic_role="later_work",
            content_class="student_work",
            target_relative_path="later/argument.txt",
            stage=stage,
        ),
        _copied_snapshot_entry(
            workspace,
            portfolio_id=portfolio_id,
            source_record_id="revised_feedback",
            entry_plan_id="installed_imp_feedback_entry",
            position=3,
            section_id="later_work",
            ordinal=2,
            semantic_role="student_feedback",
            content_class="feedback",
            target_relative_path="later/student-feedback.txt",
            stage=stage,
        ),
        SnapshotEntryPlan(
            entry_plan_id="installed_imp_reflection_entry",
            plan_position=4,
            section_id="reflection",
            ordinal=1,
            semantic_role="student_reflection",
            materialization_kind="generated_vitrine",
            content_class="reflection",
            target_relative_path="reflection/student-comparison.md",
            media_type="text/markdown",
            renderer_id="installed_reflection_renderer",
            renderer_version="1",
            renderer_contract_version="installed_reflection_renderer_v1",
            renderer_configuration_digest=_snapshot_digest(
                REFLECTION_RENDERER_CONFIGURATION
            ),
            renderer_template_digest=_snapshot_digest(REFLECTION_RENDERER_TEMPLATE),
            input_references=reflection_inputs,
        ),
    )
    renderer = _InstalledSnapshotRenderer(
        descriptor=SnapshotRendererDescriptor(
            renderer_id="installed_reflection_renderer",
            renderer_version="1",
            renderer_contract_version="installed_reflection_renderer_v1",
        ),
        expected_inputs=reflection_inputs,
        content=("# Student Reflection\n\n" + reflection.content + "\n").encode("utf-8"),
        media_type="text/markdown",
        configuration=REFLECTION_RENDERER_CONFIGURATION,
        template=REFLECTION_RENDERER_TEMPLATE,
    )
    return entries, SnapshotRendererRegistry((renderer,))


def _showcase_snapshot_entries(
    workspace: Path,
    portfolio_id: str,
) -> tuple[tuple[Any, ...], Any, str]:
    stage = "showcase_snapshot"
    from vitrine.models import (
        CurationAnnotation,
        CurationReviewDecision,
        SnapshotEntryPlan,
        SnapshotInputReference,
    )
    from vitrine.snapshot_materialization import (
        SnapshotRendererDescriptor,
        SnapshotRendererRegistry,
    )
    from vitrine.storage import load_current_records

    records = load_current_records(workspace)
    attribution = tuple(
        item
        for item in records
        if isinstance(item, CurationAnnotation)
        and item.portfolio_id == portfolio_id
        and item.purpose == "curator_context"
    )
    rationale = tuple(
        item
        for item in records
        if isinstance(item, CurationAnnotation)
        and item.portfolio_id == portfolio_id
        and item.purpose == "comparison_note"
    )
    reviews = tuple(
        item
        for item in records
        if isinstance(item, CurationReviewDecision)
        and item.portfolio_id == portfolio_id
        and item.approval_requirement_id == "installed_showcase_collaborator_review"
    )
    _require(len(attribution) == 1, stage, "exact showcase attribution did not resolve")
    _require(len(rationale) == 1, stage, "exact showcase rationale did not resolve")
    _require(
        len(reviews) == 1 and reviews[0].decision == "approved",
        stage,
        "exact showcase collaborator review did not resolve",
    )
    review_id = reviews[0].curation_review_decision_id
    composition_ref = SnapshotInputReference(
        record_type="working_portfolio_composition_revision",
        record_id=portfolio_id,
        record_revision=1,
    )
    attribution_ref = SnapshotInputReference(
        record_type="curation_annotation",
        record_id=attribution[0].annotation_id,
        record_revision=attribution[0].annotation_revision,
    )
    rationale_ref = SnapshotInputReference(
        record_type="curation_annotation",
        record_id=rationale[0].annotation_id,
        record_revision=rationale[0].annotation_revision,
    )
    attribution_inputs = (attribution_ref, composition_ref)
    rationale_inputs = (rationale_ref, composition_ref)
    index_inputs = (composition_ref,)
    entries = (
        _copied_snapshot_entry(
            workspace,
            portfolio_id=portfolio_id,
            source_record_id="polished_literary_analysis",
            entry_plan_id="installed_show_polished_entry",
            position=1,
            section_id="featured_work",
            ordinal=1,
            semantic_role="individual_work",
            content_class="student_work",
            target_relative_path="01-polished-literary-analysis.txt",
            stage=stage,
        ),
        _copied_snapshot_entry(
            workspace,
            portfolio_id=portfolio_id,
            source_record_id="concord-artifact-syn-001",
            entry_plan_id="installed_show_group_entry",
            position=2,
            section_id="collaboration",
            ordinal=1,
            semantic_role="collaborative_artifact",
            content_class="student_work",
            target_relative_path="02-group-water-quality-recommendation.txt",
            stage=stage,
            required_review_ids=(review_id,),
        ),
        SnapshotEntryPlan(
            entry_plan_id="installed_show_attribution_entry",
            plan_position=3,
            section_id="collaboration",
            ordinal=2,
            semantic_role="audience_safe_attribution",
            materialization_kind="generated_vitrine",
            content_class="audience_safe_attribution",
            target_relative_path="03-audience-safe-attribution.txt",
            media_type="text/plain",
            renderer_id="installed_showcase_attribution_renderer",
            renderer_version="1",
            renderer_contract_version="installed_showcase_text_renderer_v1",
            renderer_configuration_digest=_snapshot_digest(
                SHOWCASE_ATTRIBUTION_CONFIGURATION
            ),
            renderer_template_digest=_snapshot_digest(SHOWCASE_ATTRIBUTION_TEMPLATE),
            input_references=attribution_inputs,
            required_review_ids=(review_id,),
        ),
        SnapshotEntryPlan(
            entry_plan_id="installed_show_rationale_entry",
            plan_position=4,
            section_id="collaboration",
            ordinal=3,
            semantic_role="curation_rationale",
            materialization_kind="generated_vitrine",
            content_class="curation_rationale",
            target_relative_path="04-curation-rationale.md",
            media_type="text/markdown",
            renderer_id="installed_showcase_rationale_renderer",
            renderer_version="1",
            renderer_contract_version="installed_showcase_text_renderer_v1",
            renderer_configuration_digest=_snapshot_digest(
                SHOWCASE_RATIONALE_CONFIGURATION
            ),
            renderer_template_digest=_snapshot_digest(SHOWCASE_RATIONALE_TEMPLATE),
            input_references=rationale_inputs,
        ),
        SnapshotEntryPlan(
            entry_plan_id="installed_show_index_entry",
            plan_position=5,
            section_id="collaboration",
            ordinal=4,
            semantic_role="portfolio_index",
            materialization_kind="generated_vitrine",
            content_class="portfolio_index",
            target_relative_path="05-index.md",
            media_type="text/markdown",
            renderer_id="installed_showcase_index_renderer",
            renderer_version="1",
            renderer_contract_version="installed_showcase_text_renderer_v1",
            renderer_configuration_digest=_snapshot_digest(
                SHOWCASE_INDEX_CONFIGURATION
            ),
            renderer_template_digest=_snapshot_digest(SHOWCASE_INDEX_TEMPLATE),
            input_references=index_inputs,
        ),
    )
    renderers = SnapshotRendererRegistry(
        (
            _InstalledSnapshotRenderer(
                descriptor=SnapshotRendererDescriptor(
                    renderer_id="installed_showcase_attribution_renderer",
                    renderer_version="1",
                    renderer_contract_version="installed_showcase_text_renderer_v1",
                ),
                expected_inputs=attribution_inputs,
                content=(attribution[0].content + "\n").encode("utf-8"),
                media_type="text/plain",
                configuration=SHOWCASE_ATTRIBUTION_CONFIGURATION,
                template=SHOWCASE_ATTRIBUTION_TEMPLATE,
            ),
            _InstalledSnapshotRenderer(
                descriptor=SnapshotRendererDescriptor(
                    renderer_id="installed_showcase_rationale_renderer",
                    renderer_version="1",
                    renderer_contract_version="installed_showcase_text_renderer_v1",
                ),
                expected_inputs=rationale_inputs,
                content=("# Showcase Rationale\n\n" + rationale[0].content + "\n").encode(
                    "utf-8"
                ),
                media_type="text/markdown",
                configuration=SHOWCASE_RATIONALE_CONFIGURATION,
                template=SHOWCASE_RATIONALE_TEMPLATE,
            ),
            _InstalledSnapshotRenderer(
                descriptor=SnapshotRendererDescriptor(
                    renderer_id="installed_showcase_index_renderer",
                    renderer_version="1",
                    renderer_contract_version="installed_showcase_text_renderer_v1",
                ),
                expected_inputs=index_inputs,
                content=SHOWCASE_INDEX_TEMPLATE,
                media_type="text/markdown",
                configuration=SHOWCASE_INDEX_CONFIGURATION,
                template=SHOWCASE_INDEX_TEMPLATE,
            ),
        )
    )
    return entries, renderers, review_id


def _snapshot_file_inventory(root: Path) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (
            item.relative_to(root).as_posix(),
            item.stat().st_size,
            hashlib.sha256(item.read_bytes()).hexdigest(),
        )
        for item in sorted(path for path in root.rglob("*") if path.is_file())
    )


def _execute_snapshot_pipeline(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    portfolio_id: str,
    audience_context_id: str,
    purpose: str,
    entries: tuple[Any, ...],
    source_root: Path,
    dependencies: Any,
    acknowledged_codes: tuple[str, ...],
    stage: str,
) -> dict[str, object]:
    from vitrine.models import (
        SnapshotBuildPlan,
        SnapshotBuildRequest,
        SnapshotEdition,
        SnapshotEntry,
        SnapshotExportPlan,
        SnapshotOmission,
        SnapshotSeries,
        WorkingPortfolioCompositionInventory,
        WorkingPortfolioCompositionRevision,
    )
    from vitrine.snapshot_custody import snapshot_staging_root
    from vitrine.snapshot_distribution import (
        advance_snapshot_current_pointer,
        create_snapshot_directory_export,
        inspect_snapshot_custody,
        verify_snapshot_edition,
        verify_snapshot_export,
    )
    from vitrine.snapshot_services import (
        create_snapshot_series,
        execute_snapshot_build_attempt,
        plan_snapshot_build,
        request_snapshot_build,
        seal_snapshot_build_attempt,
        start_snapshot_build_attempt,
    )
    from vitrine.storage import load_current_records

    records = load_current_records(workspace)
    compositions = tuple(
        item
        for item in records
        if isinstance(item, WorkingPortfolioCompositionRevision)
        and item.portfolio_id == portfolio_id
        and item.composition_revision == 1
    )
    inventories = tuple(
        item
        for item in records
        if isinstance(item, WorkingPortfolioCompositionInventory)
        and item.portfolio_id == portfolio_id
        and item.composition_revision == 1
    )
    _require(
        len(compositions) == 1 and len(inventories) == 1,
        stage,
        "exact frozen Composition did not resolve for Snapshot",
    )
    _require(
        tuple(inventories[0].unresolved_obligation_codes) == acknowledged_codes,
        stage,
        "Snapshot acknowledgement codes differ from frozen Composition obligations",
    )
    created = create_snapshot_series(
        workspace,
        portfolio_id=portfolio_id,
        audience_context_id=audience_context_id,
        snapshot_purpose=purpose,
        created_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    series = next(item for item in created.records if isinstance(item, SnapshotSeries))
    requested = request_snapshot_build(
        workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=1,
        requested_by=_student_actor(),
        idempotency_key=f"installed-{purpose}-snapshot-v1",
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    request = next(
        item for item in requested.records if isinstance(item, SnapshotBuildRequest)
    )
    export_plan = SnapshotExportPlan(
        export_plan_id=ids("snapshot_export_plan"),
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=_snapshot_digest(SNAPSHOT_EXPORT_CONFIGURATION),
    )
    planned = plan_snapshot_build(
        workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export_plan,),
        planned_by=_actor(),
        acknowledged_obligation_codes=acknowledged_codes,
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
    _require(
        plan.acknowledged_obligation_codes == acknowledged_codes,
        stage,
        "Snapshot Build Plan did not freeze exact obligation acknowledgements",
    )
    started = start_snapshot_build_attempt(
        workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    execution = execute_snapshot_build_attempt(
        workspace,
        snapshot_build_attempt_id=started.attempt.snapshot_build_attempt_id,
        expected_state_revision=_state_revision(workspace),
        authority_gate=dependencies.snapshot_build_authority_gate,
        source_providers=dependencies.snapshot_source_providers,
        renderers=dependencies.snapshot_renderers,
        clock=_fixed_clock,
        id_factory=ids,
    )
    _require(
        tuple(item.disposition for item in execution.entries)
        == ("prepared_bytes",) * len(entries),
        stage,
        "every planned installed Snapshot Entry did not prepare exact bytes",
    )
    sealed = seal_snapshot_build_attempt(
        workspace,
        execution=execution,
        expected_state_revision=_state_revision(workspace),
        sealed_by=_actor(),
        clock=_fixed_clock,
        id_factory=ids,
    )
    _require(sealed.edition_path is not None, stage, "sealed Snapshot Edition path is absent")
    assert sealed.edition_path is not None
    edition_verification = verify_snapshot_edition(
        workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=_fixed_clock(),
    )
    _require(
        edition_verification.manifest_digest == sealed.seal.manifest_digest
        and edition_verification.logical_inventory_digest
        == sealed.seal.logical_inventory_digest,
        stage,
        "sealed Snapshot Edition digests did not reproduce",
    )
    exported = create_snapshot_directory_export(
        workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=export_plan.export_plan_id,
        expected_state_revision=_state_revision(workspace),
        generated_at=_fixed_clock(),
        artifact_id=ids("snapshot_export"),
    )
    export_verification = verify_snapshot_export(
        workspace,
        snapshot_export_artifact_id=exported.export_artifact.snapshot_export_artifact_id,
        verified_at=_fixed_clock(),
    )
    _require(
        export_verification.directory_inventory_digest
        == exported.export_artifact.directory_inventory_digest,
        stage,
        "Snapshot directory Export digest did not reproduce",
    )
    pointer = advance_snapshot_current_pointer(
        workspace,
        snapshot_series_id=series.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        expected_state_revision=_state_revision(workspace),
        expected_pointer_revision=None,
        expected_current_edition=None,
        pointed_by=_actor(),
        authority_reference="installed_acceptance_snapshot_pointer_authority",
        reason="Promote the verified installed acceptance Edition explicitly.",
        pointed_at=_fixed_clock(),
        pointer_id=ids("snapshot_current_pointer"),
    )
    _require(
        pointer.pointer.edition_number == sealed.edition.edition_number,
        stage,
        "explicit current-Edition pointer targets the wrong Edition",
    )
    final_records = load_current_records(workspace)
    edition_entries = tuple(
        item
        for item in final_records
        if isinstance(item, SnapshotEntry)
        and item.snapshot_edition == sealed.edition.reference
    )
    _require(
        len(edition_entries) == len(entries),
        stage,
        "sealed Snapshot Entry inventory is not exact",
    )
    _require(
        not any(isinstance(item, SnapshotOmission) for item in final_records),
        stage,
        "successful installed Snapshot unexpectedly persisted an Omission",
    )
    _require(
        len(
            tuple(
                item
                for item in final_records
                if isinstance(item, SnapshotEdition)
                and item.snapshot_series_id == series.snapshot_series_id
            )
        )
        == 1,
        stage,
        "installed Snapshot Series did not seal exactly one Edition",
    )
    custody_errors = tuple(
        item
        for item in inspect_snapshot_custody(workspace).findings
        if item.severity == "error"
    )
    _require(not custody_errors, stage, "Snapshot custody inspection reported an error")
    staging = snapshot_staging_root(workspace)
    _require(
        not staging.exists() or not any(staging.iterdir()),
        stage,
        "successful installed Snapshot left staging residue",
    )
    edition_inventory = _snapshot_file_inventory(sealed.edition_path)
    export_inventory = _snapshot_file_inventory(exported.export_path)
    _require(
        len(export_inventory) == len(entries),
        stage,
        "Snapshot Export byte inventory is not exact",
    )
    return {
        "snapshot_series_id": series.snapshot_series_id,
        "build_request_id": request.snapshot_build_request_id,
        "build_plan_id": plan.snapshot_build_plan_id,
        "build_plan_fingerprint": plan.plan_fingerprint,
        "build_attempt_id": started.attempt.snapshot_build_attempt_id,
        "edition_number": sealed.edition.edition_number,
        "manifest_sha256": sealed.seal.manifest_digest.value,
        "logical_inventory_sha256": sealed.seal.logical_inventory_digest.value,
        "export_artifact_id": exported.export_artifact.snapshot_export_artifact_id,
        "export_inventory_sha256": exported.export_artifact.directory_inventory_digest.value,
        "current_pointer_revision": pointer.pointer.pointer_revision,
        "entry_count": len(edition_entries),
        "edition_file_count": len(edition_inventory),
        "export_file_count": len(export_inventory),
        "acknowledged_obligation_codes": acknowledged_codes,
        "seal_id": sealed.seal.seal_id,
        "_edition_path": str(sealed.edition_path),
        "_export_path": str(exported.export_path),
        "_edition_inventory": edition_inventory,
        "_export_inventory": export_inventory,
    }


def _seal_unpromoted_successor_edition(
    workspace: Path,
    ids: _AcceptanceIds,
    *,
    primary: dict[str, object],
    entries: tuple[Any, ...],
    dependencies: Any,
    acknowledged_codes: tuple[str, ...],
    stage: str,
) -> dict[str, object]:
    """Seal Edition 2 while deliberately retaining the pointer at Edition 1."""

    from vitrine.models import (
        SnapshotBuildPlan,
        SnapshotBuildRequest,
        SnapshotExportPlan,
    )
    from vitrine.snapshot_distribution import verify_snapshot_edition
    from vitrine.snapshot_services import (
        execute_snapshot_build_attempt,
        plan_snapshot_build,
        request_snapshot_build,
        seal_snapshot_build_attempt,
        start_snapshot_build_attempt,
    )
    from vitrine.workflow_views import show_snapshot_series

    series_id = primary.get("snapshot_series_id")
    _require(isinstance(series_id, str), stage, "primary Snapshot Series identity is absent")
    assert isinstance(series_id, str)
    request_result = request_snapshot_build(
        workspace,
        snapshot_series_id=series_id,
        composition_revision=1,
        requested_by=_student_actor(),
        idempotency_key="installed-improvement-unpromoted-successor-v1",
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    request = next(
        item for item in request_result.records if isinstance(item, SnapshotBuildRequest)
    )
    export_plan = SnapshotExportPlan(
        export_plan_id=ids("snapshot_export_plan"),
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=_snapshot_digest(SNAPSHOT_EXPORT_CONFIGURATION),
    )
    plan_result = plan_snapshot_build(
        workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export_plan,),
        planned_by=_actor(),
        acknowledged_obligation_codes=acknowledged_codes,
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    plan = next(item for item in plan_result.records if isinstance(item, SnapshotBuildPlan))
    started = start_snapshot_build_attempt(
        workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=_actor(),
        expected_state_revision=_state_revision(workspace),
        clock=_fixed_clock,
        id_factory=ids,
    )
    execution = execute_snapshot_build_attempt(
        workspace,
        snapshot_build_attempt_id=started.attempt.snapshot_build_attempt_id,
        expected_state_revision=_state_revision(workspace),
        authority_gate=dependencies.snapshot_build_authority_gate,
        source_providers=dependencies.snapshot_source_providers,
        renderers=dependencies.snapshot_renderers,
        clock=_fixed_clock,
        id_factory=ids,
    )
    sealed = seal_snapshot_build_attempt(
        workspace,
        execution=execution,
        expected_state_revision=_state_revision(workspace),
        sealed_by=_actor(),
        clock=_fixed_clock,
        id_factory=ids,
    )
    _require(
        sealed.edition_path is not None and sealed.edition.edition_number == 2,
        stage,
        "unpromoted successor did not seal as Edition 2",
    )
    assert sealed.edition_path is not None
    verified = verify_snapshot_edition(
        workspace,
        snapshot_series_id=series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=_fixed_clock(),
    )
    _require(
        verified.manifest_digest == sealed.seal.manifest_digest
        and verified.logical_inventory_digest == sealed.seal.logical_inventory_digest,
        stage,
        "unpromoted successor Edition digests did not reproduce",
    )
    view = show_snapshot_series(workspace, series_id)
    _require(
        view.current_edition is not None
        and view.current_edition.edition_number == 1
        and max(item.edition_number for item in view.editions) == 2,
        stage,
        "current Edition view was not controlled by the explicit pointer",
    )
    return {
        "snapshot_series_id": series_id,
        "edition_number": sealed.edition.edition_number,
        "manifest_sha256": sealed.seal.manifest_digest.value,
        "logical_inventory_sha256": sealed.seal.logical_inventory_digest.value,
        "_edition_path": str(sealed.edition_path),
        "_edition_inventory": _snapshot_file_inventory(sealed.edition_path),
    }


def _snapshot_public_report(report: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


def _canonical_record_inventory(workspace: Path) -> dict[str, tuple[str, ...]]:
    from vitrine.models.serialization import record_to_canonical_json_bytes
    from vitrine.storage import load_current_records

    grouped: dict[str, list[str]] = {}
    for record in load_current_records(workspace):
        grouped.setdefault(record.record_type, []).append(
            hashlib.sha256(record_to_canonical_json_bytes(record)).hexdigest()
        )
    return {
        record_type: tuple(sorted(digests))
        for record_type, digests in sorted(grouped.items())
    }


def _selection_identity_inventory(workspace: Path) -> tuple[str, ...]:
    from vitrine.models import PortfolioCandidate, PortfolioSelection
    from vitrine.models.serialization import record_to_canonical_json_bytes
    from vitrine.storage import load_current_records

    records = load_current_records(workspace)
    selected = tuple(
        item
        for item in records
        if isinstance(item, (PortfolioCandidate, PortfolioSelection))
    )
    return tuple(
        sorted(
            hashlib.sha256(record_to_canonical_json_bytes(item)).hexdigest()
            for item in selected
        )
    )


def _historical_reload_expectations(
    workspace: Path,
    snapshots: tuple[dict[str, object], dict[str, object]],
) -> dict[str, object]:
    inventory = _canonical_record_inventory(workspace)
    json_inventory = {key: list(value) for key, value in inventory.items()}
    improvement = snapshots[0]
    successor_raw = improvement.get("_unpromoted_successor")
    _require(
        isinstance(successor_raw, dict),
        "historical_reload",
        "unpromoted improvement successor is absent from reload expectations",
    )
    assert isinstance(successor_raw, dict)
    successor = cast(dict[str, object], successor_raw)
    series_id = improvement.get("snapshot_series_id")
    pointed_edition = improvement.get("current_pointer_edition_number")
    greatest_edition = improvement.get("greatest_edition_number")
    successor_manifest = successor.get("manifest_sha256")
    successor_inventory = successor.get("logical_inventory_sha256")
    _require(
        isinstance(series_id, str)
        and isinstance(pointed_edition, int)
        and not isinstance(pointed_edition, bool)
        and isinstance(greatest_edition, int)
        and not isinstance(greatest_edition, bool)
        and pointed_edition < greatest_edition
        and isinstance(successor_manifest, str)
        and _SHA256.fullmatch(successor_manifest) is not None
        and isinstance(successor_inventory, str)
        and _SHA256.fullmatch(successor_inventory) is not None,
        "historical_reload",
        "pointer-vs-greatest reload expectation is incomplete",
    )
    assert isinstance(series_id, str)
    assert isinstance(pointed_edition, int) and not isinstance(pointed_edition, bool)
    assert isinstance(greatest_edition, int) and not isinstance(greatest_edition, bool)
    assert isinstance(successor_manifest, str)
    assert isinstance(successor_inventory, str)
    pointer_probe: dict[str, object] = {
        "snapshot_series_id": series_id,
        "pointed_edition_number": pointed_edition,
        "greatest_edition_number": greatest_edition,
        "successor_manifest_sha256": successor_manifest,
        "successor_logical_inventory_sha256": successor_inventory,
    }
    return {
        "workspace_state_revision": _state_revision(workspace),
        "record_inventory": json_inventory,
        "record_inventory_sha256": _sha256_bytes(
            json.dumps(
                json_inventory,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ),
        "snapshots": [
            {
                key: value
                for key, value in _snapshot_public_report(snapshot).items()
                if key
                in {
                    "snapshot_series_id",
                    "build_request_id",
                    "build_plan_id",
                    "build_plan_fingerprint",
                    "build_attempt_id",
                    "edition_number",
                    "seal_id",
                    "manifest_sha256",
                    "logical_inventory_sha256",
                    "export_artifact_id",
                    "export_inventory_sha256",
                    "current_pointer_revision",
                }
            }
            for snapshot in snapshots
        ],
        "pointer_probe": pointer_probe,
    }


def _source_drift(
    workspace: Path,
    source_root: Path,
    snapshots: tuple[dict[str, object], dict[str, object]],
) -> dict[str, object]:
    stage = "source_drift"
    from vitrine.snapshot_distribution import (
        verify_snapshot_edition,
        verify_snapshot_export,
    )

    before_revision = _state_revision(workspace)
    before_selection_inventory = _selection_identity_inventory(workspace)
    files = tuple(sorted(item for item in source_root.rglob("*") if item.is_file()))
    _require(
        len(files) == 5,
        stage,
        "staged producer source inventory is not exact before drift",
    )
    files[0].write_bytes(
        b"DRIFTED PRODUCER SOURCE -- SEALED SNAPSHOTS MUST IGNORE THIS\n"
    )
    files[-1].unlink()

    improvement_successor = snapshots[0].get("_unpromoted_successor")
    _require(
        isinstance(improvement_successor, dict),
        stage,
        "unpromoted improvement successor Edition is absent",
    )
    assert isinstance(improvement_successor, dict)
    edition_targets = (snapshots[0], improvement_successor, snapshots[1])

    def verify_editions() -> None:
        for target in edition_targets:
            series_id = target.get("snapshot_series_id")
            edition_number = target.get("edition_number")
            _require(
                isinstance(series_id, str) and isinstance(edition_number, int),
                stage,
                "Snapshot Edition identity is incomplete before source-drift verification",
            )
            assert isinstance(series_id, str)
            assert isinstance(edition_number, int)
            verified = verify_snapshot_edition(
                workspace,
                snapshot_series_id=series_id,
                edition_number=edition_number,
                verified_at=_fixed_clock(),
            )
            _require(
                verified.manifest_digest.value == target.get("manifest_sha256")
                and verified.logical_inventory_digest.value
                == target.get("logical_inventory_sha256"),
                stage,
                "sealed Edition digest changed after staged producer-source drift",
            )
            edition_path = target.get("_edition_path")
            _require(
                isinstance(edition_path, str),
                stage,
                "sealed Edition custody path is absent",
            )
            assert isinstance(edition_path, str)
            _require(
                _snapshot_file_inventory(Path(edition_path))
                == target.get("_edition_inventory"),
                stage,
                "sealed Edition byte inventory changed after source drift",
            )

    def verify_exports() -> None:
        for snapshot in snapshots:
            export_id = snapshot.get("export_artifact_id")
            _require(
                isinstance(export_id, str),
                stage,
                "Snapshot Export identity is incomplete before source-drift verification",
            )
            assert isinstance(export_id, str)
            export_verified = verify_snapshot_export(
                workspace,
                snapshot_export_artifact_id=export_id,
                verified_at=_fixed_clock(),
            )
            _require(
                export_verified.directory_inventory_digest.value
                == snapshot.get("export_inventory_sha256"),
                stage,
                "Export digest changed after staged producer-source drift",
            )
            export_path = snapshot.get("_export_path")
            _require(
                isinstance(export_path, str),
                stage,
                "Snapshot Export custody path is absent",
            )
            assert isinstance(export_path, str)
            _require(
                _snapshot_file_inventory(Path(export_path))
                == snapshot.get("_export_inventory"),
                stage,
                "Export byte inventory changed after source drift",
            )

    verify_editions()
    verify_exports()

    shutil.rmtree(source_root)
    _require(not source_root.exists(), stage, "staged producer source root was not removed")

    verify_editions()
    verify_exports()

    _require(
        _state_revision(workspace) == before_revision,
        stage,
        "source drift or verification mutated canonical Vitrine state",
    )
    _require(
        _selection_identity_inventory(workspace) == before_selection_inventory,
        stage,
        "source drift retargeted Candidate or Selection identity",
    )
    return {
        "staged_files_before_drift": len(files),
        "staged_files_mutated": 1,
        "staged_files_deleted_before_root_removal": 1,
        "source_root_removed": True,
        "editions_reverified": len(edition_targets),
        "exports_reverified": len(snapshots),
        "sealed_byte_inventories_unchanged": True,
        "candidate_selection_identity_unchanged": True,
        "workspace_state_revision_unchanged": True,
    }


def _improvement_snapshot(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
    curation: dict[str, object],
    source_root: Path,
    dependencies: Any,
) -> dict[str, object]:
    stage = "improvement_snapshot"
    portfolio_id = identities["improvement_portfolio_id"]
    entries, renderers = _improvement_snapshot_entries(workspace, portfolio_id)
    source_registry = dependencies.snapshot_source_providers
    renderer_registry = dependencies.snapshot_renderers
    _require(
        isinstance(source_registry, _SnapshotSourceProviderRegistryBase)
        and isinstance(renderer_registry, _SnapshotRendererRegistryBase)
        and isinstance(source_registry, _DeferredSnapshotSourceRegistry)
        and isinstance(renderer_registry, _DeferredSnapshotRendererRegistry),
        stage,
        "installed workflow dependencies lost real Snapshot registry slots",
    )
    source_registry.configure(
        _snapshot_provider_registry(entries, source_root, stage=stage)
    )
    renderer_registry.configure(renderers)
    _require(
        not any(
            getattr(item, "content_class", None) == "assessment_summary"
            for item in entries
        ),
        stage,
        "unselected ScoreForm attempts leaked into improvement Snapshot planning",
    )
    audience_id = curation.get("audience_context_id")
    _require(
        isinstance(audience_id, str),
        stage,
        "improvement Audience Context identity is absent",
    )
    assert isinstance(audience_id, str)
    report = _execute_snapshot_pipeline(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        audience_context_id=audience_id,
        purpose="improvement",
        entries=entries,
        source_root=source_root,
        dependencies=dependencies,
        acknowledged_codes=(),
        stage=stage,
    )
    successor = _seal_unpromoted_successor_edition(
        workspace,
        ids,
        primary=report,
        entries=entries,
        dependencies=dependencies,
        acknowledged_codes=(),
        stage=stage,
    )
    report["current_pointer_edition_number"] = report["edition_number"]
    report["greatest_edition_number"] = successor["edition_number"]
    report["current_pointer_precedes_greatest"] = True
    report["_unpromoted_successor"] = successor
    return report


def _showcase_snapshot(
    workspace: Path,
    ids: _AcceptanceIds,
    identities: dict[str, str],
    curation: dict[str, object],
    source_root: Path,
    dependencies: Any,
) -> dict[str, object]:
    stage = "showcase_snapshot"
    portfolio_id = identities["showcase_portfolio_id"]
    entries, renderers, review_id = _showcase_snapshot_entries(workspace, portfolio_id)
    source_registry = dependencies.snapshot_source_providers
    renderer_registry = dependencies.snapshot_renderers
    _require(
        isinstance(source_registry, _SnapshotSourceProviderRegistryBase)
        and isinstance(renderer_registry, _SnapshotRendererRegistryBase)
        and isinstance(source_registry, _DeferredSnapshotSourceRegistry)
        and isinstance(renderer_registry, _DeferredSnapshotRendererRegistry),
        stage,
        "installed workflow dependencies lost real Snapshot registry slots",
    )
    source_registry.configure(
        _snapshot_provider_registry(entries, source_root, stage=stage)
    )
    renderer_registry.configure(renderers)
    audience_id = curation.get("audience_context_id")
    _require(
        isinstance(audience_id, str),
        stage,
        "showcase Audience Context identity is absent",
    )
    assert isinstance(audience_id, str)
    report = _execute_snapshot_pipeline(
        workspace,
        ids,
        portfolio_id=portfolio_id,
        audience_context_id=audience_id,
        purpose="showcase",
        entries=entries,
        source_root=source_root,
        dependencies=dependencies,
        acknowledged_codes=("collaborator_review_required",),
        stage=stage,
    )
    from vitrine.models import SnapshotBuildRequest
    from vitrine.storage import load_current_records

    requests = tuple(
        item
        for item in load_current_records(workspace)
        if isinstance(item, SnapshotBuildRequest)
        and item.snapshot_series_id == report["snapshot_series_id"]
    )
    _require(
        len(requests) == 1 and review_id in requests[0].curation_review_decision_ids,
        stage,
        "showcase Snapshot Build Request did not freeze the exact collaborator review",
    )
    forbidden = (
        b"collaborator-syn-001",
        b"collaborator-syn-002",
        b"PRIVATE_",
        b"secure_assessment",
        b"recipient authorization",
        b"consent obtained",
    )
    export_id = report["export_artifact_id"]
    from vitrine.snapshot_distribution import verify_snapshot_export
    # Re-verification here is intentional: the generated report identity must resolve
    # before privacy checks inspect the canonical export path in Slice 5.
    _require(isinstance(export_id, str), stage, "showcase Export identity is absent")
    assert isinstance(export_id, str)
    verify_snapshot_export(
        workspace,
        snapshot_export_artifact_id=export_id,
        verified_at=_fixed_clock(),
    )
    # Source fixture bytes and generated presentation text are all known here;
    # reject prohibited disclosure/authorization markers before historical drift tests.
    source_bytes = b"\n".join(
        item.read_bytes()
        for item in sorted(
            path for path in source_root.rglob("*") if path.is_file()
        )
    )
    _require(
        not any(marker in source_bytes for marker in forbidden),
        stage,
        "showcase staged source fixture contains prohibited disclosure markers",
    )
    export_path_raw = report.get("_export_path")
    _require(
        isinstance(export_path_raw, str),
        stage,
        "showcase Export custody path is absent",
    )
    assert isinstance(export_path_raw, str)
    export_path = Path(export_path_raw).resolve(strict=True)
    export_files = tuple(
        sorted(item for item in export_path.rglob("*") if item.is_file())
    )
    _require(
        len(export_files) == len(entries),
        stage,
        "showcase Export privacy scan did not resolve the exact file inventory",
    )
    _require(
        not any(
            marker in path.read_bytes()
            for path in export_files
            for marker in forbidden
        ),
        stage,
        "showcase Export contains prohibited privacy or authorization content",
    )
    _require(
        not (export_path / "internal" / "manifest.json").exists(),
        stage,
        "showcase directory Export leaked the internal Snapshot manifest",
    )
    report["audience_safe_export_verified"] = True
    return report

def run_boundary_probe(
    *,
    repository: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    """Run installed provenance and fixture/live contract-boundary acceptance."""

    resolved_repository = repository.resolve(strict=True)
    resolved_workspace = workspace.resolve()
    provenance = _stage(
        "installed_provenance",
        lambda: _installed_provenance(
            resolved_repository,
            resolved_workspace,
            vitrine_wheel_sha256=vitrine_wheel_sha256,
            core_wheel_sha256=core_wheel_sha256,
        ),
    )
    boundary = _stage(
        "fixture_boundary", lambda: _fixture_boundary(resolved_workspace)
    )
    return {
        "acceptance_contract": "vitrine_installed_end_to_end_acceptance_v1",
        "mode": "boundary_only",
        "stages": STAGES[:2],
        "installed_provenance": provenance,
        "fixture_boundary": boundary,
        "workspace_side_effects": False,
    }


def run_discovery_probe(
    *,
    repository: Path,
    fixture_root: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    """Run installed isolation through Core publication and Candidate discovery."""

    resolved_repository = repository.resolve(strict=True)
    resolved_fixture_root = fixture_root.resolve(strict=True)
    resolved_workspace = workspace.resolve()
    _require(
        resolved_fixture_root.is_dir(),
        "core_publication",
        "fixture root is not a directory",
    )
    provenance = _stage(
        "installed_provenance",
        lambda: _installed_provenance(
            resolved_repository,
            resolved_workspace,
            vitrine_wheel_sha256=vitrine_wheel_sha256,
            core_wheel_sha256=core_wheel_sha256,
        ),
    )
    boundary = _stage(
        "fixture_boundary", lambda: _fixture_boundary(resolved_workspace)
    )
    dependencies = _stage(
        "fixture_boundary", _build_installed_workflow_dependencies
    )
    ids = _AcceptanceIds()
    identities = _stage(
        "workspace_identity",
        lambda: _initialize_subject_and_portfolios(resolved_workspace, ids),
    )
    profiles = _stage(
        "profile_setup",
        lambda: _initialize_profiles(resolved_workspace, ids, identities),
    )
    publications = _stage(
        "core_publication",
        lambda: _publish_acceptance_sources(
            resolved_workspace, resolved_fixture_root
        ),
    )
    discovery = _stage(
        "candidate_discovery",
        lambda: _candidate_discovery(
            resolved_workspace, ids, identities, dependencies
        ),
    )
    return {
        "acceptance_contract": "vitrine_installed_end_to_end_acceptance_v1",
        "mode": "discovery_only",
        "stages": STAGES[:6],
        "installed_provenance": provenance,
        "fixture_boundary": boundary,
        "workflow_dependencies": _dependency_report(dependencies),
        "workspace_identity": identities,
        "profile_setup": profiles,
        "core_publication": publications,
        "candidate_discovery": discovery,
        "workspace_state_revision": _state_revision(resolved_workspace),
    }


def run_curation_probe(
    *,
    repository: Path,
    fixture_root: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    """Run installed acceptance through explicit curation and frozen audience state."""

    resolved_repository = repository.resolve(strict=True)
    resolved_fixture_root = fixture_root.resolve(strict=True)
    resolved_workspace = workspace.resolve()
    _require(
        resolved_fixture_root.is_dir(),
        "core_publication",
        "fixture root is not a directory",
    )
    provenance = _stage(
        "installed_provenance",
        lambda: _installed_provenance(
            resolved_repository,
            resolved_workspace,
            vitrine_wheel_sha256=vitrine_wheel_sha256,
            core_wheel_sha256=core_wheel_sha256,
        ),
    )
    boundary = _stage(
        "fixture_boundary", lambda: _fixture_boundary(resolved_workspace)
    )
    dependencies = _stage(
        "fixture_boundary", _build_installed_workflow_dependencies
    )
    ids = _AcceptanceIds()
    identities = _stage(
        "workspace_identity",
        lambda: _initialize_subject_and_portfolios(resolved_workspace, ids),
    )
    profiles = _stage(
        "profile_setup",
        lambda: _initialize_profiles(resolved_workspace, ids, identities),
    )
    publications = _stage(
        "core_publication",
        lambda: _publish_acceptance_sources(
            resolved_workspace, resolved_fixture_root
        ),
    )
    discovery = _stage(
        "candidate_discovery",
        lambda: _candidate_discovery(
            resolved_workspace, ids, identities, dependencies
        ),
    )
    improvement = _stage(
        "improvement_curation",
        lambda: _improvement_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    showcase = _stage(
        "showcase_curation",
        lambda: _showcase_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    _require(
        improvement["audience_context_id"] != showcase["audience_context_id"],
        "showcase_curation",
        "improvement and showcase Audience Contexts collapsed",
    )
    return {
        "acceptance_contract": "vitrine_installed_end_to_end_acceptance_v1",
        "mode": "curation_only",
        "stages": STAGES[:8],
        "installed_provenance": provenance,
        "fixture_boundary": boundary,
        "workflow_dependencies": _dependency_report(dependencies),
        "workspace_identity": identities,
        "profile_setup": profiles,
        "core_publication": publications,
        "candidate_discovery": discovery,
        "improvement_curation": improvement,
        "showcase_curation": showcase,
        "workspace_state_revision": _state_revision(resolved_workspace),
    }



def run_snapshot_probe(
    *,
    repository: Path,
    fixture_root: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    """Run installed acceptance through both immutable Snapshot issuance pipelines."""

    resolved_repository = repository.resolve(strict=True)
    resolved_fixture_root = fixture_root.resolve(strict=True)
    resolved_workspace = workspace.resolve()
    _require(
        resolved_fixture_root.is_dir(),
        "core_publication",
        "fixture root is not a directory",
    )
    provenance = _stage(
        "installed_provenance",
        lambda: _installed_provenance(
            resolved_repository,
            resolved_workspace,
            vitrine_wheel_sha256=vitrine_wheel_sha256,
            core_wheel_sha256=core_wheel_sha256,
        ),
    )
    boundary = _stage(
        "fixture_boundary", lambda: _fixture_boundary(resolved_workspace)
    )
    dependencies = _stage(
        "fixture_boundary", _build_installed_workflow_dependencies
    )
    ids = _AcceptanceIds()
    identities = _stage(
        "workspace_identity",
        lambda: _initialize_subject_and_portfolios(resolved_workspace, ids),
    )
    profiles = _stage(
        "profile_setup",
        lambda: _initialize_profiles(resolved_workspace, ids, identities),
    )
    publications = _stage(
        "core_publication",
        lambda: _publish_acceptance_sources(
            resolved_workspace, resolved_fixture_root
        ),
    )
    discovery = _stage(
        "candidate_discovery",
        lambda: _candidate_discovery(
            resolved_workspace, ids, identities, dependencies
        ),
    )
    improvement = _stage(
        "improvement_curation",
        lambda: _improvement_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    showcase = _stage(
        "showcase_curation",
        lambda: _showcase_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    source_root = _stage(
        "improvement_snapshot",
        lambda: _snapshot_source_root(resolved_fixture_root, resolved_workspace),
    )
    improvement_snapshot = _stage(
        "improvement_snapshot",
        lambda: _improvement_snapshot(
            resolved_workspace, ids, identities, improvement, source_root, dependencies
        ),
    )
    showcase_snapshot = _stage(
        "showcase_snapshot",
        lambda: _showcase_snapshot(
            resolved_workspace, ids, identities, showcase, source_root, dependencies
        ),
    )
    _require(
        improvement_snapshot["snapshot_series_id"]
        != showcase_snapshot["snapshot_series_id"],
        "showcase_snapshot",
        "improvement and showcase Snapshot Series identities collapsed",
    )
    _require(
        improvement_snapshot["export_artifact_id"]
        != showcase_snapshot["export_artifact_id"],
        "showcase_snapshot",
        "improvement and showcase Export identities collapsed",
    )
    return {
        "acceptance_contract": "vitrine_installed_end_to_end_acceptance_v1",
        "mode": "snapshot_only",
        "stages": STAGES[:10],
        "installed_provenance": provenance,
        "fixture_boundary": boundary,
        "workflow_dependencies": _dependency_report(dependencies),
        "workspace_identity": identities,
        "profile_setup": profiles,
        "core_publication": publications,
        "candidate_discovery": discovery,
        "improvement_curation": improvement,
        "showcase_curation": showcase,
        "improvement_snapshot": _snapshot_public_report(improvement_snapshot),
        "showcase_snapshot": _snapshot_public_report(showcase_snapshot),
        "staged_source_root_name": source_root.name,
        "workspace_state_revision": _state_revision(resolved_workspace),
    }


def run_end_to_end_probe(
    *,
    repository: Path,
    fixture_root: Path,
    workspace: Path,
    vitrine_wheel_sha256: str,
    core_wheel_sha256: str,
) -> dict[str, object]:
    """Run the primary installed process through source drift and reload handoff."""

    resolved_repository = repository.resolve(strict=True)
    resolved_fixture_root = fixture_root.resolve(strict=True)
    resolved_workspace = workspace.resolve()
    _require(
        resolved_fixture_root.is_dir(),
        "core_publication",
        "fixture root is not a directory",
    )
    provenance = _stage(
        "installed_provenance",
        lambda: _installed_provenance(
            resolved_repository,
            resolved_workspace,
            vitrine_wheel_sha256=vitrine_wheel_sha256,
            core_wheel_sha256=core_wheel_sha256,
        ),
    )
    boundary = _stage(
        "fixture_boundary", lambda: _fixture_boundary(resolved_workspace)
    )
    dependencies = _stage(
        "fixture_boundary", _build_installed_workflow_dependencies
    )
    ids = _AcceptanceIds()
    identities = _stage(
        "workspace_identity",
        lambda: _initialize_subject_and_portfolios(resolved_workspace, ids),
    )
    profiles = _stage(
        "profile_setup",
        lambda: _initialize_profiles(resolved_workspace, ids, identities),
    )
    publications = _stage(
        "core_publication",
        lambda: _publish_acceptance_sources(
            resolved_workspace, resolved_fixture_root
        ),
    )
    discovery = _stage(
        "candidate_discovery",
        lambda: _candidate_discovery(
            resolved_workspace, ids, identities, dependencies
        ),
    )
    improvement = _stage(
        "improvement_curation",
        lambda: _improvement_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    showcase = _stage(
        "showcase_curation",
        lambda: _showcase_curation(
            resolved_workspace, ids, identities, profiles, dependencies
        ),
    )
    source_root = _stage(
        "improvement_snapshot",
        lambda: _snapshot_source_root(resolved_fixture_root, resolved_workspace),
    )
    improvement_snapshot = _stage(
        "improvement_snapshot",
        lambda: _improvement_snapshot(
            resolved_workspace, ids, identities, improvement, source_root, dependencies
        ),
    )
    showcase_snapshot = _stage(
        "showcase_snapshot",
        lambda: _showcase_snapshot(
            resolved_workspace, ids, identities, showcase, source_root, dependencies
        ),
    )
    snapshots = (improvement_snapshot, showcase_snapshot)
    drift = _stage(
        "source_drift",
        lambda: _source_drift(resolved_workspace, source_root, snapshots),
    )
    expectations = _historical_reload_expectations(resolved_workspace, snapshots)
    return {
        "acceptance_contract": "vitrine_installed_end_to_end_acceptance_v1",
        "mode": "end_to_end_primary",
        "stages": STAGES[:11],
        "installed_provenance": provenance,
        "fixture_boundary": boundary,
        "workflow_dependencies": _dependency_report(dependencies),
        "workspace_identity": identities,
        "profile_setup": profiles,
        "core_publication": publications,
        "candidate_discovery": discovery,
        "improvement_curation": improvement,
        "showcase_curation": showcase,
        "improvement_snapshot": _snapshot_public_report(improvement_snapshot),
        "showcase_snapshot": _snapshot_public_report(showcase_snapshot),
        "source_drift": drift,
        "historical_reload_expectations": expectations,
        "workspace_state_revision": _state_revision(resolved_workspace),
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--vitrine-wheel-sha256", required=True)
    parser.add_argument("--core-wheel-sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--boundary-only", action="store_true")
    mode.add_argument("--discovery-only", action="store_true")
    mode.add_argument("--curation-only", action="store_true")
    mode.add_argument("--snapshot-only", action="store_true")
    mode.add_argument("--end-to-end", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.boundary_only:
            report = run_boundary_probe(
                repository=args.repository,
                workspace=args.workspace,
                vitrine_wheel_sha256=args.vitrine_wheel_sha256,
                core_wheel_sha256=args.core_wheel_sha256,
            )
        else:
            if args.fixture_root is None:
                raise InstalledEndToEndAcceptanceError(
                    "core_publication",
                    "installed acceptance beyond the boundary requires --fixture-root",
                )
            if args.discovery_only:
                report = run_discovery_probe(
                    repository=args.repository,
                    fixture_root=args.fixture_root,
                    workspace=args.workspace,
                    vitrine_wheel_sha256=args.vitrine_wheel_sha256,
                    core_wheel_sha256=args.core_wheel_sha256,
                )
            elif args.curation_only:
                report = run_curation_probe(
                    repository=args.repository,
                    fixture_root=args.fixture_root,
                    workspace=args.workspace,
                    vitrine_wheel_sha256=args.vitrine_wheel_sha256,
                    core_wheel_sha256=args.core_wheel_sha256,
                )
            elif args.snapshot_only:
                report = run_snapshot_probe(
                    repository=args.repository,
                    fixture_root=args.fixture_root,
                    workspace=args.workspace,
                    vitrine_wheel_sha256=args.vitrine_wheel_sha256,
                    core_wheel_sha256=args.core_wheel_sha256,
                )
            else:
                report = run_end_to_end_probe(
                    repository=args.repository,
                    fixture_root=args.fixture_root,
                    workspace=args.workspace,
                    vitrine_wheel_sha256=args.vitrine_wheel_sha256,
                    core_wheel_sha256=args.core_wheel_sha256,
                )
    except InstalledEndToEndAcceptanceError as error:
        print(f"{error.stage}: {error.message}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
