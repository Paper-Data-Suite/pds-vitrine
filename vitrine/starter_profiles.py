"""Packaged starter Portfolio Profile definitions and explicit installation.

Starter packs are optional convenience content. Catalog loading, listing,
validation, and install planning are read-only. Installation is a separate,
explicit, guarded canonical-state mutation.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Final, cast

from vitrine.models import (
    ActorAttribution,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    VitrineRecord,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.profile_state import collect_profile_state_issues, project_profile_state

if TYPE_CHECKING:
    from vitrine.storage import VitrineStorageCommitResult

StarterInstallClock = Callable[[], datetime]
StarterInstallIdFactory = Callable[[str], str]

STARTER_PROFILE_CATALOG_CONTRACT_VERSION: Final[str] = (
    "vitrine_starter_profile_catalog_v1"
)
STARTER_PROFILE_PACK_CONTRACT_VERSION: Final[str] = "vitrine_starter_profile_pack_v1"
STARTER_PROFILE_RESOURCE_PACKAGE: Final[str] = "vitrine.starter_profile_data"
STARTER_PROFILE_IDS: Final[tuple[str, str]] = (
    "improvement_portfolio_v1",
    "showcase_portfolio_v1",
)
STARTER_PROFILE_FAMILY_IDS: Final[tuple[str, str]] = (
    "vitrine_starter_improvement_family",
    "vitrine_starter_showcase_family",
)
STARTER_PORTFOLIO_PROFILE_IDS: Final[tuple[str, str]] = (
    "vitrine_starter_improvement",
    "vitrine_starter_showcase",
)
STARTER_PROFILE_PURPOSES: Final[tuple[str, str]] = ("improvement", "showcase")

# These are the canonical Candidate kinds consumed by current Profile-section
# eligibility. They are deliberately producer-neutral and are cross-checked in
# focused tests against the current Candidate evaluator mapping.
STARTER_PROFILE_CANDIDATE_KINDS_V1: Final[frozenset[str]] = frozenset(
    {"assessment_summary", "feedback", "student_work"}
)


class StarterProfileError(ValueError):
    """Stable starter catalog, pack, planning, or installation failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class StarterProfileCatalogEntry:
    starter_profile_id: str
    resource_name: str
    label: str
    purpose_kind: str
    profile_family_id: str
    portfolio_profile_id: str
    profile_revision: int


@dataclass(frozen=True, slots=True)
class StarterProfilePack:
    contract_version: str
    starter_profile_id: str
    label: str
    description: str
    purpose_kind: str
    family: PortfolioProfileFamily
    revision: PortfolioProfileRevision
    requirements: tuple[PortfolioProfileRequirement, ...]

    @property
    def section_count(self) -> int:
        return len(self.revision.sections)

    @property
    def requirement_count(self) -> int:
        return len(self.requirements)


@dataclass(frozen=True, slots=True)
class StarterProfileSummary:
    starter_profile_id: str
    label: str
    purpose_kind: str
    profile_family_id: str
    portfolio_profile_id: str
    profile_revision: int
    section_count: int
    requirement_count: int


STARTER_PROFILE_COMPONENT_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"create", "reuse_exact", "conflict"}
)
STARTER_PROFILE_LIFECYCLE_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        "activate_new",
        "already_active",
        "activate_existing_exact",
        "lifecycle_conflict",
    }
)


@dataclass(frozen=True, slots=True)
class StarterProfileInstallComponentDisposition:
    component_kind: str
    component_id: str
    disposition: str
    detail_code: str | None = None


@dataclass(frozen=True, slots=True)
class StarterProfileInstallPlan:
    starter_profile_id: str
    label: str
    purpose_kind: str
    profile_family_id: str
    portfolio_profile_id: str
    profile_revision: int
    observed_state_revision: int | None
    observed_lifecycle_status: str
    lifecycle_disposition: str
    components: tuple[StarterProfileInstallComponentDisposition, ...]

    @property
    def created_record_count(self) -> int:
        return sum(item.disposition == "create" for item in self.components)

    @property
    def reused_record_count(self) -> int:
        return sum(item.disposition == "reuse_exact" for item in self.components)

    @property
    def conflict_record_count(self) -> int:
        return sum(item.disposition == "conflict" for item in self.components)

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_record_count > 0 or (
            self.lifecycle_disposition == "lifecycle_conflict"
        )

    @property
    def activation_required(self) -> bool:
        return self.lifecycle_disposition in {
            "activate_new",
            "activate_existing_exact",
        }

    @property
    def would_change(self) -> bool:
        return not self.has_conflicts and (
            self.created_record_count > 0 or self.activation_required
        )


@dataclass(frozen=True, slots=True)
class StarterProfileInstallResult:
    plan: StarterProfileInstallPlan
    activation_event_id: str | None
    committed_component_ids: tuple[str, ...]
    commit: VitrineStorageCommitResult | None

    @property
    def no_op(self) -> bool:
        return self.commit is None

    @property
    def resulting_state_revision(self) -> int | None:
        if self.commit is None:
            return self.plan.observed_state_revision
        return self.commit.state_revision


@dataclass(frozen=True, slots=True)
class StarterProfileValidationResult:
    starter_profile_id: str
    valid: bool
    issue_codes: tuple[str, ...]


def _resource_text(resource_name: str) -> str:
    try:
        return (
            resources.files(STARTER_PROFILE_RESOURCE_PACKAGE)
            .joinpath(resource_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as error:
        raise StarterProfileError(
            "starter_profile_invalid",
            "Packaged starter Profile resource could not be loaded.",
        ) from error


def _json_object(resource_name: str) -> dict[str, object]:
    try:
        value = json.loads(_resource_text(resource_name))
    except json.JSONDecodeError as error:
        raise StarterProfileError(
            "starter_profile_invalid",
            "Packaged starter Profile resource is not valid JSON.",
        ) from error
    if not isinstance(value, dict):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Packaged starter Profile resource must contain one JSON object.",
        )
    return cast(dict[str, object], value)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be a nonempty string.",
        )
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _required_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be an integer.",
        )
    return value


def _required_mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be an object.",
        )
    return cast(dict[str, object], value)


def _mapping_sequence(value: object, field_name: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be an array.",
        )
    result: list[dict[str, object]] = []
    for item in value:
        result.append(_required_mapping(item, field_name))
    return tuple(result)


def _string_sequence(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be an array.",
        )
    return tuple(_required_string(item, field_name) for item in value)


def _aware_datetime(value: object, field_name: str) -> datetime:
    text = _required_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} is not an ISO datetime.",
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile field {field_name!r} must be timezone-aware.",
        )
    return parsed


def _actor(value: object) -> ActorAttribution:
    data = _required_mapping(value, "created_by")
    return ActorAttribution(
        actor_kind=_required_string(data.get("actor_kind"), "actor_kind"),
        actor_id=_required_string(data.get("actor_id"), "actor_id"),
        owning_system=_required_string(data.get("owning_system"), "owning_system"),
        display_label_snapshot=_optional_string(
            data.get("display_label_snapshot"), "display_label_snapshot"
        ),
        role_snapshot=_optional_string(data.get("role_snapshot"), "role_snapshot"),
    )


def _applicability(value: object) -> ProfileApplicability:
    data = _required_mapping(value, "applicability")
    return ProfileApplicability(
        jurisdiction=_optional_string(data.get("jurisdiction"), "jurisdiction"),
        institution_id=_optional_string(data.get("institution_id"), "institution_id"),
        program_id=_optional_string(data.get("program_id"), "program_id"),
        school_years=_string_sequence(data.get("school_years", []), "school_years"),
        cohorts=_string_sequence(data.get("cohorts", []), "cohorts"),
        grade_bands=_string_sequence(data.get("grade_bands", []), "grade_bands"),
        content_areas=_string_sequence(
            data.get("content_areas", []), "content_areas"
        ),
        pathway=_optional_string(data.get("pathway"), "pathway"),
        authority_reference=_optional_string(
            data.get("authority_reference"), "authority_reference"
        ),
    )


def _section(value: dict[str, object]) -> ProfileSectionDefinition:
    maximum_raw = value.get("maximum_placements")
    maximum: int | None = (
        None
        if maximum_raw is None
        else _required_int(maximum_raw, "maximum_placements")
    )
    return ProfileSectionDefinition(
        section_id=_required_string(value.get("section_id"), "section_id"),
        label=_required_string(value.get("label"), "label"),
        purpose=_required_string(value.get("purpose"), "purpose"),
        order=_required_int(value.get("order"), "order"),
        obligation=_required_string(value.get("obligation"), "obligation"),
        minimum_placements=_required_int(
            value.get("minimum_placements"), "minimum_placements"
        ),
        maximum_placements=maximum,
        allowed_candidate_kinds=_string_sequence(
            value.get("allowed_candidate_kinds", []), "allowed_candidate_kinds"
        ),
        required_relationship_kinds=_string_sequence(
            value.get("required_relationship_kinds", []),
            "required_relationship_kinds",
        ),
        reflection_requirement=_required_string(
            value.get("reflection_requirement"), "reflection_requirement"
        ),
    )


def _audience_rule(value: dict[str, object]) -> ProfileAudienceRule:
    return ProfileAudienceRule(
        audience_rule_id=_required_string(
            value.get("audience_rule_id"), "audience_rule_id"
        ),
        audience_class=_required_string(value.get("audience_class"), "audience_class"),
        purpose=_required_string(value.get("purpose"), "purpose"),
        allowed_content_classes=_string_sequence(
            value.get("allowed_content_classes", []), "allowed_content_classes"
        ),
        prohibited_content_classes=_string_sequence(
            value.get("prohibited_content_classes", []), "prohibited_content_classes"
        ),
        required_review_classes=_string_sequence(
            value.get("required_review_classes", []), "required_review_classes"
        ),
        presentation_class=_required_string(
            value.get("presentation_class"), "presentation_class"
        ),
        retention_policy_reference=_optional_string(
            value.get("retention_policy_reference"), "retention_policy_reference"
        ),
    )


def _family(value: object) -> PortfolioProfileFamily:
    data = _required_mapping(value, "family")
    return PortfolioProfileFamily(
        profile_family_id=_required_string(
            data.get("profile_family_id"), "profile_family_id"
        ),
        label=_required_string(data.get("label"), "label"),
        purpose_kind=_required_string(data.get("purpose_kind"), "purpose_kind"),
        created_at=_aware_datetime(data.get("created_at"), "created_at"),
        created_by=_actor(data.get("created_by")),
        description=_optional_string(data.get("description"), "description"),
    )


def _revision(value: object) -> PortfolioProfileRevision:
    data = _required_mapping(value, "revision")
    predecessor_raw = data.get("predecessor_revision")
    predecessor: int | None = (
        None
        if predecessor_raw is None
        else _required_int(predecessor_raw, "predecessor_revision")
    )
    return PortfolioProfileRevision(
        portfolio_profile_id=_required_string(
            data.get("portfolio_profile_id"), "portfolio_profile_id"
        ),
        profile_revision=_required_int(
            data.get("profile_revision"), "profile_revision"
        ),
        profile_family_id=_optional_string(
            data.get("profile_family_id"), "profile_family_id"
        ),
        predecessor_revision=predecessor,
        label=_required_string(data.get("label"), "label"),
        purpose_kind=_required_string(data.get("purpose_kind"), "purpose_kind"),
        applicability=_applicability(data.get("applicability")),
        sections=tuple(
            _section(item)
            for item in _mapping_sequence(data.get("sections"), "sections")
        ),
        audience_rules=tuple(
            _audience_rule(item)
            for item in _mapping_sequence(
                data.get("audience_rules", []), "audience_rules"
            )
        ),
        created_at=_aware_datetime(data.get("created_at"), "created_at"),
        created_by=_actor(data.get("created_by")),
        source_authority_references=_string_sequence(
            data.get("source_authority_references", []),
            "source_authority_references",
        ),
        known_limitations=_string_sequence(
            data.get("known_limitations", []), "known_limitations"
        ),
    )


def _requirement(value: dict[str, object]) -> PortfolioProfileRequirement:
    return PortfolioProfileRequirement(
        portfolio_profile_id=_required_string(
            value.get("portfolio_profile_id"), "portfolio_profile_id"
        ),
        profile_revision=_required_int(
            value.get("profile_revision"), "profile_revision"
        ),
        requirement_id=_required_string(value.get("requirement_id"), "requirement_id"),
        requirement_kind=_required_string(
            value.get("requirement_kind"), "requirement_kind"
        ),
        obligation=_required_string(value.get("obligation"), "obligation"),
        title=_required_string(value.get("title"), "title"),
        statement=_required_string(value.get("statement"), "statement"),
        scope_kind=_required_string(value.get("scope_kind"), "scope_kind"),
        satisfaction_class=_required_string(
            value.get("satisfaction_class"), "satisfaction_class"
        ),
        authority_references=_string_sequence(
            value.get("authority_references", []), "authority_references"
        ),
        scope_reference=_optional_string(
            value.get("scope_reference"), "scope_reference"
        ),
        replaces_requirement_id=_optional_string(
            value.get("replaces_requirement_id"), "replaces_requirement_id"
        ),
    )


def _load_catalog_entries() -> tuple[StarterProfileCatalogEntry, ...]:
    data = _json_object("catalog.json")
    if data.get("contract_version") != STARTER_PROFILE_CATALOG_CONTRACT_VERSION:
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile catalog contract version is unsupported.",
        )
    entries = tuple(
        StarterProfileCatalogEntry(
            starter_profile_id=_required_string(
                item.get("starter_profile_id"), "starter_profile_id"
            ),
            resource_name=_required_string(item.get("resource_name"), "resource_name"),
            label=_required_string(item.get("label"), "label"),
            purpose_kind=_required_string(item.get("purpose_kind"), "purpose_kind"),
            profile_family_id=_required_string(
                item.get("profile_family_id"), "profile_family_id"
            ),
            portfolio_profile_id=_required_string(
                item.get("portfolio_profile_id"), "portfolio_profile_id"
            ),
            profile_revision=_required_int(
                item.get("profile_revision"), "profile_revision"
            ),
        )
        for item in _mapping_sequence(data.get("starters"), "starters")
    )
    ids = tuple(item.starter_profile_id for item in entries)
    family_ids = tuple(item.profile_family_id for item in entries)
    profile_ids = tuple(item.portfolio_profile_id for item in entries)
    purposes = tuple(item.purpose_kind for item in entries)
    revisions = tuple(item.profile_revision for item in entries)
    resources_used = tuple(item.resource_name for item in entries)
    if (
        ids != STARTER_PROFILE_IDS
        or family_ids != STARTER_PROFILE_FAMILY_IDS
        or profile_ids != STARTER_PORTFOLIO_PROFILE_IDS
        or purposes != STARTER_PROFILE_PURPOSES
        or revisions != (1, 1)
        or len(set(resources_used)) != len(resources_used)
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile catalog identities or ordering are invalid.",
        )
    return entries


def _decode_pack(
    entry: StarterProfileCatalogEntry, data: dict[str, object]
) -> StarterProfilePack:
    try:
        family = _family(data.get("family"))
        revision = _revision(data.get("revision"))
        requirements = tuple(
            _requirement(item)
            for item in _mapping_sequence(data.get("requirements"), "requirements")
        )
    except VitrineModelValidationError as error:
        raise StarterProfileError("starter_profile_invalid", str(error)) from error
    pack = StarterProfilePack(
        contract_version=_required_string(
            data.get("contract_version"), "contract_version"
        ),
        starter_profile_id=_required_string(
            data.get("starter_profile_id"), "starter_profile_id"
        ),
        label=_required_string(data.get("label"), "label"),
        description=_required_string(data.get("description"), "description"),
        purpose_kind=_required_string(data.get("purpose_kind"), "purpose_kind"),
        family=family,
        revision=revision,
        requirements=requirements,
    )
    _validate_pack_or_raise(pack, entry)
    return pack


def _validate_pack_or_raise(
    pack: StarterProfilePack, entry: StarterProfileCatalogEntry
) -> None:
    if pack.contract_version != STARTER_PROFILE_PACK_CONTRACT_VERSION:
        raise StarterProfileError(
            "starter_profile_invalid", "Starter Profile pack contract is unsupported."
        )
    if (
        pack.starter_profile_id != entry.starter_profile_id
        or pack.label != entry.label
        or pack.purpose_kind != entry.purpose_kind
        or pack.family.profile_family_id != entry.profile_family_id
        or pack.revision.portfolio_profile_id != entry.portfolio_profile_id
        or pack.revision.profile_revision != entry.profile_revision
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile pack identity disagrees with the catalog.",
        )
    if pack.family.purpose_kind != pack.purpose_kind:
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile Family purpose disagrees with the pack purpose.",
        )
    if (
        pack.revision.purpose_kind != pack.purpose_kind
        or pack.revision.profile_family_id != pack.family.profile_family_id
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile Revision identity or purpose is inconsistent.",
        )
    if (
        pack.revision.profile_revision != 1
        or pack.revision.predecessor_revision is not None
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Initial starter Profile pack must contain exact Revision 1 without "
            "a predecessor.",
        )
    if (
        not pack.revision.source_authority_references
        or not pack.revision.known_limitations
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile provenance and known limitations must be explicit.",
        )
    if not pack.requirements:
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile pack must contain explicit Requirements.",
        )
    requirement_ids = tuple(item.requirement_id for item in pack.requirements)
    if len(set(requirement_ids)) != len(requirement_ids):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile Requirement IDs must be unique.",
        )
    for section in pack.revision.sections:
        unsupported = set(section.allowed_candidate_kinds) - set(
            STARTER_PROFILE_CANDIDATE_KINDS_V1
        )
        if unsupported:
            raise StarterProfileError(
                "starter_profile_invalid",
                "Starter Profile section uses an unsupported Candidate kind.",
            )
    for requirement in pack.requirements:
        if requirement.profile_reference != pack.revision.reference:
            raise StarterProfileError(
                "starter_profile_invalid",
                "Starter Profile Requirement does not identify the exact Revision.",
            )
        if requirement.replaces_requirement_id is not None:
            raise StarterProfileError(
                "starter_profile_invalid",
                "Initial starter Requirements must not replace predecessor "
                "Requirements.",
            )
    issues = collect_profile_state_issues(
        project_profile_state((pack.family, pack.revision, *pack.requirements))
    )
    if issues:
        raise StarterProfileError(
            "starter_profile_invalid",
            f"Starter Profile aggregate failed Profile validation: {issues[0].code}.",
        )
    author = pack.family.created_by
    if (
        author.actor_kind != "system"
        or author.actor_id != "vitrine_starter_profile_catalog"
        or author.owning_system != "vitrine"
        or author.role_snapshot != "starter_profile_author"
        or pack.revision.created_by != author
        or pack.revision.created_at != pack.family.created_at
    ):
        raise StarterProfileError(
            "starter_profile_invalid",
            "Starter Profile authored provenance is not deterministic Vitrine "
            "catalog provenance.",
        )


def list_starter_profile_packs() -> tuple[StarterProfileSummary, ...]:
    """List packaged starters in deterministic catalog order without workspace I/O."""

    summaries: list[StarterProfileSummary] = []
    for entry in _load_catalog_entries():
        pack = _decode_pack(entry, _json_object(entry.resource_name))
        summaries.append(
            StarterProfileSummary(
                starter_profile_id=pack.starter_profile_id,
                label=pack.label,
                purpose_kind=pack.purpose_kind,
                profile_family_id=pack.family.profile_family_id,
                portfolio_profile_id=pack.revision.portfolio_profile_id,
                profile_revision=pack.revision.profile_revision,
                section_count=pack.section_count,
                requirement_count=pack.requirement_count,
            )
        )
    return tuple(summaries)


def get_starter_profile_pack(starter_profile_id: str) -> StarterProfilePack:
    """Return one exact packaged starter definition without touching a workspace."""

    entry = next(
        (
            item
            for item in _load_catalog_entries()
            if item.starter_profile_id == starter_profile_id
        ),
        None,
    )
    if entry is None:
        raise StarterProfileError(
            "starter_profile_not_found", "Starter Profile ID is not in the catalog."
        )
    return _decode_pack(entry, _json_object(entry.resource_name))


def validate_starter_profile_pack(
    starter_profile_id: str,
) -> StarterProfileValidationResult:
    """Validate one packaged starter using ordinary Profile aggregate rules."""

    try:
        get_starter_profile_pack(starter_profile_id)
    except StarterProfileError as error:
        if error.code == "starter_profile_not_found":
            raise
        return StarterProfileValidationResult(
            starter_profile_id=starter_profile_id,
            valid=False,
            issue_codes=(error.code,),
        )
    return StarterProfileValidationResult(
        starter_profile_id=starter_profile_id,
        valid=True,
        issue_codes=(),
    )

def _workspace_profile_state(
    workspace_root: str | Path,
) -> tuple[object, int | None]:
    # Imported lazily so catalog list/show/validate remain package-resource-only
    # operations and do not acquire workspace dependencies.
    from vitrine.profile_services import ProfileWorkflowError, load_profile_state

    try:
        return load_profile_state(workspace_root)
    except ProfileWorkflowError as error:
        raise StarterProfileError(error.code, str(error)) from error


def _component(
    component_kind: str,
    component_id: str,
    disposition: str,
    *,
    detail_code: str | None = None,
) -> StarterProfileInstallComponentDisposition:
    if disposition not in STARTER_PROFILE_COMPONENT_DISPOSITIONS:
        raise ValueError(f"unsupported starter Profile disposition: {disposition}")
    return StarterProfileInstallComponentDisposition(
        component_kind=component_kind,
        component_id=component_id,
        disposition=disposition,
        detail_code=detail_code,
    )


def _lifecycle_disposition(
    *,
    exact_revision_exists: bool,
    observed_status: str,
    has_component_conflict: bool,
) -> str:
    if has_component_conflict:
        return "lifecycle_conflict"
    if not exact_revision_exists:
        return "activate_new"
    if observed_status == "activated":
        return "already_active"
    if observed_status == "inactive":
        return "activate_existing_exact"
    return "lifecycle_conflict"


def plan_starter_profile_install(
    starter_profile_id: str,
    *,
    workspace_root: str | Path,
) -> StarterProfileInstallPlan:
    """Plan one explicit starter install without mutating canonical state.

    Exact immutable records may be reused; missing compatible records may be
    created by a later installer; identity collisions with different immutable
    content are surfaced as conflicts. Lifecycle state is observed only.
    """

    pack = get_starter_profile_pack(starter_profile_id)
    state_object, observed_state_revision = _workspace_profile_state(workspace_root)

    # Keep workspace dependencies lazy for catalog-only operations.
    from vitrine.profile_state import PortfolioProfileState

    if not isinstance(state_object, PortfolioProfileState):
        raise StarterProfileError(
            "profile_state_invalid",
            "Portfolio Profile state loader returned an unexpected value.",
        )
    state = state_object
    components: list[StarterProfileInstallComponentDisposition] = []

    existing_family = next(
        (
            item
            for item in state.families
            if item.profile_family_id == pack.family.profile_family_id
        ),
        None,
    )
    if existing_family is None:
        components.append(
            _component("family", pack.family.profile_family_id, "create")
        )
    elif existing_family == pack.family:
        components.append(
            _component("family", pack.family.profile_family_id, "reuse_exact")
        )
    else:
        components.append(
            _component(
                "family",
                pack.family.profile_family_id,
                "conflict",
                detail_code="immutable_content_conflict",
            )
        )

    reference = pack.revision.reference
    existing_revision = state.revision(reference)
    other_series_revisions = tuple(
        item
        for item in state.revisions
        if item.portfolio_profile_id == pack.revision.portfolio_profile_id
        and item.profile_revision != pack.revision.profile_revision
    )
    revision_component_id = (
        f"{pack.revision.portfolio_profile_id}:{pack.revision.profile_revision}"
    )
    if existing_revision is None and other_series_revisions:
        components.append(
            _component(
                "revision",
                revision_component_id,
                "conflict",
                detail_code="profile_series_identity_conflict",
            )
        )
    elif existing_revision is None:
        components.append(_component("revision", revision_component_id, "create"))
    elif existing_revision == pack.revision:
        components.append(
            _component("revision", revision_component_id, "reuse_exact")
        )
    else:
        components.append(
            _component(
                "revision",
                revision_component_id,
                "conflict",
                detail_code="immutable_content_conflict",
            )
        )

    existing_requirements = {
        item.requirement_id: item for item in state.requirements_for(reference)
    }
    starter_requirement_ids = {item.requirement_id for item in pack.requirements}
    for requirement in pack.requirements:
        existing = existing_requirements.get(requirement.requirement_id)
        if existing is None:
            disposition = "create"
            detail_code = None
        elif existing == requirement:
            disposition = "reuse_exact"
            detail_code = None
        else:
            disposition = "conflict"
            detail_code = "immutable_content_conflict"
        components.append(
            _component(
                "requirement",
                requirement.requirement_id,
                disposition,
                detail_code=detail_code,
            )
        )
    for requirement_id in sorted(
        set(existing_requirements).difference(starter_requirement_ids)
    ):
        components.append(
            _component(
                "requirement",
                requirement_id,
                "conflict",
                detail_code="unexpected_existing_requirement",
            )
        )

    observed_lifecycle_status = (
        "absent" if existing_revision is None else state.lifecycle_status(reference)
    )
    has_component_conflict = any(
        item.disposition == "conflict" for item in components
    )
    lifecycle_disposition = _lifecycle_disposition(
        exact_revision_exists=existing_revision is not None,
        observed_status=observed_lifecycle_status,
        has_component_conflict=has_component_conflict,
    )
    if lifecycle_disposition not in STARTER_PROFILE_LIFECYCLE_DISPOSITIONS:
        raise ValueError(
            "unsupported starter Profile lifecycle disposition: "
            f"{lifecycle_disposition}"
        )

    return StarterProfileInstallPlan(
        starter_profile_id=pack.starter_profile_id,
        label=pack.label,
        purpose_kind=pack.purpose_kind,
        profile_family_id=pack.family.profile_family_id,
        portfolio_profile_id=pack.revision.portfolio_profile_id,
        profile_revision=pack.revision.profile_revision,
        observed_state_revision=observed_state_revision,
        observed_lifecycle_status=observed_lifecycle_status,
        lifecycle_disposition=lifecycle_disposition,
        components=tuple(components),
    )


def _install_clock() -> datetime:
    return datetime.now(timezone.utc)


def _install_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _install_component_records(
    pack: StarterProfilePack,
    plan: StarterProfileInstallPlan,
) -> tuple[VitrineRecord, ...]:
    create_components = {
        (item.component_kind, item.component_id)
        for item in plan.components
        if item.disposition == "create"
    }
    values: list[VitrineRecord] = []
    family_key = ("family", pack.family.profile_family_id)
    revision_id = (
        f"{pack.revision.portfolio_profile_id}:{pack.revision.profile_revision}"
    )
    revision_key = ("revision", revision_id)
    if family_key in create_components:
        values.append(pack.family)
    if revision_key in create_components:
        values.append(pack.revision)
    for requirement in pack.requirements:
        if ("requirement", requirement.requirement_id) in create_components:
            values.append(requirement)
    return tuple(values)


def install_starter_profile(
    starter_profile_id: str,
    *,
    workspace_root: str | Path,
    actor: ActorAttribution,
    reason: str,
    authority_reference: str | None,
    expected_state_revision: int | None,
    clock: StarterInstallClock = _install_clock,
    id_factory: StarterInstallIdFactory = _install_id,
) -> StarterProfileInstallResult:
    """Explicitly install and activate one starter in one guarded commit.

    Pack-authored Family, Revision, and Requirement provenance remains fixed.
    A new activation event, when required, records the installing actor and
    actual installation time. Exact active installs are idempotent no-ops.
    """

    plan = plan_starter_profile_install(
        starter_profile_id,
        workspace_root=workspace_root,
    )
    if plan.observed_state_revision != expected_state_revision:
        raise StarterProfileError(
            "state_conflict",
            "Vitrine state changed or the install expectation is stale: "
            f"expected {expected_state_revision!r}, observed "
            f"{plan.observed_state_revision!r}.",
        )
    if plan.conflict_record_count:
        first = next(
            item for item in plan.components if item.disposition == "conflict"
        )
        raise StarterProfileError(
            "starter_profile_install_conflict",
            "Starter Profile install conflicts with existing immutable state: "
            f"{first.component_kind}:{first.component_id} "
            f"({first.detail_code or 'conflict'}).",
        )
    if plan.lifecycle_disposition == "lifecycle_conflict":
        raise StarterProfileError(
            "starter_profile_lifecycle_conflict",
            "Starter Profile exact Revision cannot be implicitly reactivated: "
            f"lifecycle status is {plan.observed_lifecycle_status}.",
        )
    if not plan.would_change:
        return StarterProfileInstallResult(
            plan=plan,
            activation_event_id=None,
            committed_component_ids=(),
            commit=None,
        )

    pack = get_starter_profile_pack(starter_profile_id)
    component_records = _install_component_records(pack, plan)

    # Read the exact state Revision that planning observed, rather than whatever
    # happens to be current after planning. The canonical commit guard catches
    # any race before publication.
    from vitrine.storage import (
        VitrineStorageConflictError,
        VitrineStorageNotFoundError,
        commit_record_batch,
        load_state_records,
    )

    if plan.observed_state_revision is None:
        current_records: tuple[VitrineRecord, ...] = ()
    else:
        try:
            current_records = load_state_records(
                workspace_root, plan.observed_state_revision
            )
        except VitrineStorageNotFoundError as error:
            raise StarterProfileError(
                "state_conflict",
                "The Profile state observed during install planning is no longer "
                "available.",
            ) from error

    activation_event: PortfolioProfileLifecycleEvent | None = None
    if plan.activation_required:
        now = clock()
        activation_event = PortfolioProfileLifecycleEvent(
            profile_lifecycle_event_id=id_factory("profile_event"),
            profile_revision=pack.revision.reference,
            event_kind="activated",
            event_at=now,
            effective_at=now,
            actor=actor,
            reason=reason,
            authority_reference=authority_reference,
        )

    pending_records = (
        *component_records,
        *((activation_event,) if activation_event is not None else ()),
    )
    if not pending_records:
        raise StarterProfileError(
            "starter_profile_install_invalid",
            "Starter Profile install planned a change but produced no records.",
        )

    profile_issues = collect_profile_state_issues(
        project_profile_state((*current_records, *pending_records))
    )
    if profile_issues:
        first_issue = profile_issues[0]
        raise StarterProfileError(
            first_issue.code.replace(".", "_"),
            first_issue.message,
        )

    try:
        commit = commit_record_batch(
            workspace_root,
            pending_records,
            expected_state_revision=expected_state_revision,
        )
    except VitrineStorageConflictError as error:
        raise StarterProfileError("state_conflict", str(error)) from error

    committed_component_ids = tuple(
        f"{item.component_kind}:{item.component_id}"
        for item in plan.components
        if item.disposition == "create"
    )
    if activation_event is not None:
        committed_component_ids = (
            *committed_component_ids,
            f"lifecycle:{activation_event.profile_lifecycle_event_id}",
        )
    return StarterProfileInstallResult(
        plan=plan,
        activation_event_id=(
            activation_event.profile_lifecycle_event_id
            if activation_event is not None
            else None
        ),
        committed_component_ids=committed_component_ids,
        commit=commit,
    )

