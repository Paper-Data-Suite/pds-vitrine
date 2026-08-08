"""Low-density teacher-facing Portfolio Profile workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import (
    NavigationChoice,
    navigation_hint,
    parse_navigation_choice,
    print_navigation_options,
)
from pds_core.workspace import resolve_workspace_root

from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import (
    ActorAttribution,
    PortfolioProfileFamily,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
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
    ProfileMigrationAnalysis,
    ProfileRevisionSummary,
    ProfileWorkflowError,
    activate_profile_revision,
    analyze_profile_migration,
    bind_portfolio_profile,
    compose_profile_revision,
    create_profile_family,
    create_profile_overlay,
    create_profile_revision,
    get_portfolio_profile_binding,
    get_profile_revision,
    list_bindable_profile_revisions,
    list_profile_families,
    list_profile_revisions,
    load_profile_state,
    migrate_portfolio_profile,
    observe_profile_state_revision,
)
from vitrine.storage import VitrineStorageError


@dataclass(slots=True)
class ProfileMenuSession:
    actor: ActorAttribution | None = None


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    return input_fn(prompt).strip()


def _pause(input_fn: InputFunction) -> None:
    input_fn("Press Enter to continue...")


def _nav(output: TextIO) -> None:
    print_navigation_options(file=output)


def _navigation(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(value)


def _confirm(word: str, *, input_fn: InputFunction) -> bool:
    value = _read(input_fn, f"Type {word} to continue, or press Enter to cancel: ")
    if not value:
        return False
    navigation = _navigation(value)
    if navigation is NavigationChoice.BACK:
        return False
    return value.casefold() == word.casefold()


def _show_help(output: TextIO, input_fn: InputFunction) -> None:
    _write(
        output,
        "Portfolio Profile Help",
        "",
        "A Profile Revision is immutable policy for one Portfolio purpose.",
        "Creating a Revision does not activate it.",
        "Activation and Portfolio Binding are explicit actions.",
        "Newer revision numbers and timestamps never select policy automatically.",
        "Migration preserves the old Binding and creates a successor Binding.",
    )
    _pause(input_fn)


def _ensure_actor(
    session: ProfileMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> ActorAttribution | None:
    if session.actor is not None:
        return session.actor
    clear_fn()
    _write(output, "Teacher Identity", "")
    _nav(output)
    _write(output, "")
    raw = _read(input_fn, "Teacher identifier: ")
    navigation = _navigation(raw)
    if not raw or navigation is NavigationChoice.BACK:
        return None
    try:
        session.actor = ActorAttribution(
            actor_kind="authorized_adult",
            actor_id=raw,
            owning_system="local",
            role_snapshot="teacher",
        )
    except ValueError as error:
        _write(output, "", f"Identity problem: {error}")
        _pause(input_fn)
        return None
    return session.actor


def _authority_reason(
    session: ProfileMenuSession,
    title: str,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> tuple[ActorAttribution, str, str] | None:
    actor = _ensure_actor(
        session, input_fn=input_fn, output=output, clear_fn=clear_fn
    )
    if actor is None:
        return None
    clear_fn()
    _write(output, title, "")
    _nav(output)
    _write(output, "")
    authority = _read(input_fn, "Authority/reference: ")
    navigation = _navigation(authority)
    if not authority or navigation is NavigationChoice.BACK:
        return None
    reason = _read(input_fn, "Brief reason: ")
    navigation = _navigation(reason)
    if not reason or navigation is NavigationChoice.BACK:
        return None
    return actor, authority, reason


def _choose_revision(
    workspace: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    bindable_only: bool = False,
    exclude: ProfileRevisionRef | None = None,
) -> ProfileRevisionSummary | None:
    values = (
        list_bindable_profile_revisions(workspace)
        if bindable_only
        else list_profile_revisions(workspace)
    )
    values = tuple(item for item in values if item.reference != exclude)
    clear_fn()
    _write(output, "Select Profile Revision", "")
    if not values:
        _write(output, "No matching Profile Revisions were found.")
        _pause(input_fn)
        return None
    for index, item in enumerate(values, start=1):
        _write(
            output,
            f"{index}. {item.label} — {item.reference.portfolio_profile_id}@"
            f"{item.reference.profile_revision} ({item.lifecycle_status})",
        )
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(values):
        return values[int(choice) - 1]
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _choose_family(
    workspace: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> PortfolioProfileFamily | None:
    families = list_profile_families(workspace)
    clear_fn()
    _write(output, "Select Profile Family", "")
    if not families:
        _write(output, "No Profile Families exist yet.")
        _pause(input_fn)
        return None
    for index, family in enumerate(families, start=1):
        _write(output, f"{index}. {family.label} — {family.profile_family_id}")
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(families):
        return families[int(choice) - 1]
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _choose_portfolio(
    workspace: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    require_binding: bool | None = None,
) -> str | None:
    state, _ = load_profile_state(workspace)
    portfolios = []
    for item in sorted(state.portfolios, key=lambda item: item.portfolio_id):
        binding = state.active_binding(item.portfolio_id)
        if require_binding is True and binding is None:
            continue
        if require_binding is False and binding is not None:
            continue
        portfolios.append(item)
    clear_fn()
    _write(output, "Select Portfolio", "")
    if not portfolios:
        _write(output, "No matching Portfolios were found.")
        _pause(input_fn)
        return None
    for index, portfolio in enumerate(portfolios, start=1):
        label = portfolio.title_snapshot or portfolio.portfolio_id
        _write(output, f"{index}. {label} — {portfolio.portfolio_id}")
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(portfolios):
        return portfolios[int(choice) - 1].portfolio_id
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _show_success(
    message: str,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    clear_fn()
    _write(output, message)
    _pause(input_fn)


def _create_family(
    workspace: Path,
    session: ProfileMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_profile_state_revision(workspace)
    actor = _ensure_actor(session, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if actor is None:
        return
    clear_fn()
    _write(output, "Create Profile Family", "", "1. Improvement", "2. Showcase")
    _nav(output)
    _write(output, "")
    purpose_choice = _read(input_fn, "Purpose: ")
    navigation = _navigation(purpose_choice)
    if not purpose_choice or navigation is NavigationChoice.BACK:
        return
    purpose = {"1": "improvement", "2": "showcase"}.get(purpose_choice)
    if purpose is None:
        _write(output, navigation_hint())
        _pause(input_fn)
        return
    clear_fn()
    _write(output, "Create Profile Family", "")
    family_id = _read(input_fn, "Family ID: ")
    if not family_id or _navigation(family_id) is NavigationChoice.BACK:
        return
    label = _read(input_fn, "Display label: ")
    if not label or _navigation(label) is NavigationChoice.BACK:
        return
    description = _read(input_fn, "Description (optional): ") or None
    clear_fn()
    _write(
        output,
        "Review Profile Family",
        "",
        f"ID: {family_id}",
        f"Label: {label}",
        f"Purpose: {purpose}",
        "",
        "A Family groups related Profile series; it supplies no inherited rules.",
        "",
    )
    if not _confirm("CREATE", input_fn=input_fn):
        return
    family = PortfolioProfileFamily(
        profile_family_id=family_id,
        label=label,
        purpose_kind=purpose,
        description=description,
        created_at=datetime.now(timezone.utc),
        created_by=actor,
    )
    create_profile_family(workspace, family, expected_state_revision=expected)
    _show_success("Profile Family created.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _ask_positive_int(input_fn: InputFunction, prompt: str) -> int | None:
    raw = _read(input_fn, prompt)
    navigation = _navigation(raw)
    if not raw or navigation is NavigationChoice.BACK:
        return None
    if not raw.isdigit() or int(raw) < 1:
        return None
    return int(raw)


def _author_sections(
    *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> tuple[ProfileSectionDefinition, ...] | None:
    clear_fn()
    _write(output, "Profile Sections", "")
    count = _ask_positive_int(input_fn, "Number of sections: ")
    if count is None:
        return None
    result: list[ProfileSectionDefinition] = []
    for index in range(1, count + 1):
        clear_fn()
        _write(output, f"Section {index} of {count}", "")
        section_id = _read(input_fn, "Section ID: ")
        if not section_id:
            return None
        label = _read(input_fn, "Label: ")
        purpose = _read(input_fn, "Purpose: ")
        obligation = _read(input_fn, "Obligation [required/optional/conditional/prohibited]: ")
        if obligation == "prohibited":
            minimum = 0
            maximum: int | None = 0
            allowed: tuple[str, ...] = ()
        else:
            minimum_raw = _read(input_fn, "Minimum placements [0]: ") or "0"
            maximum_raw = _read(input_fn, "Maximum placements (blank = unbounded): ")
            if not minimum_raw.isdigit() or (maximum_raw and not maximum_raw.isdigit()):
                return None
            minimum = int(minimum_raw)
            maximum = int(maximum_raw) if maximum_raw else None
            allowed_raw = _read(input_fn, "Allowed candidate kinds (comma-separated): ")
            allowed = tuple(item.strip() for item in allowed_raw.split(",") if item.strip())
        relation_raw = _read(input_fn, "Required relationship kinds (comma-separated, optional): ")
        relationships = tuple(item.strip() for item in relation_raw.split(",") if item.strip())
        reflection = _read(input_fn, "Reflection [none/optional/required]: ") or "none"
        result.append(
            ProfileSectionDefinition(
                section_id=section_id,
                label=label,
                purpose=purpose,
                order=index,
                obligation=obligation,
                minimum_placements=minimum,
                maximum_placements=maximum,
                allowed_candidate_kinds=allowed,
                required_relationship_kinds=relationships,
                reflection_requirement=reflection,
            )
        )
    return tuple(result)


def _author_audiences(
    *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> tuple[ProfileAudienceRule, ...] | None:
    clear_fn()
    _write(output, "Audience Rules", "")
    count = _ask_positive_int(input_fn, "Number of audience rules: ")
    if count is None:
        return None
    result: list[ProfileAudienceRule] = []
    for index in range(1, count + 1):
        clear_fn()
        _write(output, f"Audience Rule {index} of {count}", "")
        rule_id = _read(input_fn, "Audience rule ID: ")
        audience_class = _read(input_fn, "Audience class: ")
        purpose = _read(input_fn, "Purpose: ")
        allowed_raw = _read(input_fn, "Allowed content classes (comma-separated): ")
        prohibited_raw = _read(input_fn, "Prohibited content classes (comma-separated): ")
        reviews_raw = _read(input_fn, "Required review classes (comma-separated): ")
        presentation = _read(input_fn, "Presentation class: ")
        result.append(
            ProfileAudienceRule(
                audience_rule_id=rule_id,
                audience_class=audience_class,
                purpose=purpose,
                allowed_content_classes=tuple(item.strip() for item in allowed_raw.split(",") if item.strip()),
                prohibited_content_classes=tuple(item.strip() for item in prohibited_raw.split(",") if item.strip()),
                required_review_classes=tuple(item.strip() for item in reviews_raw.split(",") if item.strip()),
                presentation_class=presentation,
            )
        )
    return tuple(result)


def _author_requirements(
    reference: ProfileRevisionRef,
    *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> tuple[PortfolioProfileRequirement, ...] | None:
    clear_fn()
    _write(output, "Profile Requirements", "")
    count = _ask_positive_int(input_fn, "Number of requirements: ")
    if count is None:
        return None
    result: list[PortfolioProfileRequirement] = []
    for index in range(1, count + 1):
        clear_fn()
        _write(output, f"Requirement {index} of {count}", "")
        requirement_id = _read(input_fn, "Requirement ID: ")
        kind = _read(input_fn, "Kind [section/selection/reflection/audience/approval/output]: ")
        obligation = _read(input_fn, "Obligation [required/optional/conditional/prohibited]: ")
        title = _read(input_fn, "Title: ")
        statement = _read(input_fn, "Policy statement: ")
        scope_kind = _read(input_fn, "Scope kind [portfolio/section/audience/output]: ")
        scope_reference = _read(input_fn, "Scope reference (optional): ") or None
        satisfaction = _read(input_fn, "Satisfaction class: ")
        authority_raw = _read(input_fn, "Authority references (comma-separated, optional): ")
        replaces = _read(input_fn, "Replaces requirement ID (optional): ") or None
        result.append(
            PortfolioProfileRequirement(
                portfolio_profile_id=reference.portfolio_profile_id,
                profile_revision=reference.profile_revision,
                requirement_id=requirement_id,
                requirement_kind=kind,
                obligation=obligation,
                title=title,
                statement=statement,
                scope_kind=scope_kind,
                scope_reference=scope_reference,
                satisfaction_class=satisfaction,
                authority_references=tuple(item.strip() for item in authority_raw.split(",") if item.strip()),
                replaces_requirement_id=replaces,
            )
        )
    return tuple(result)


def _create_revision(
    workspace: Path,
    session: ProfileMenuSession,
    *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    actor = _ensure_actor(session, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if actor is None:
        return
    family = _choose_family(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if family is None:
        return
    clear_fn()
    _write(output, "Profile Series and Revision", "")
    profile_id = _read(input_fn, "Profile series ID: ")
    revision_number = _ask_positive_int(input_fn, "Revision number: ")
    if not profile_id or revision_number is None:
        return
    existing = tuple(item for item in list_profile_revisions(workspace, portfolio_profile_id=profile_id))
    predecessor: int | None = None
    if existing:
        raw = _read(input_fn, "Direct predecessor revision (blank = none): ")
        if raw:
            if not raw.isdigit():
                return
            predecessor = int(raw)
    label = _read(input_fn, "Revision label: ")
    clear_fn()
    _write(output, "Applicability", "", "Leave fields blank when the Profile is not restricted by that context.")
    school_year_raw = _read(input_fn, "School years (comma-separated): ")
    institution_id = _read(input_fn, "Institution ID (optional): ") or None
    program_id = _read(input_fn, "Program ID (optional): ") or None
    content_raw = _read(input_fn, "Content areas (comma-separated): ")
    applicability = ProfileApplicability(
        school_years=tuple(item.strip() for item in school_year_raw.split(",") if item.strip()),
        institution_id=institution_id,
        program_id=program_id,
        content_areas=tuple(item.strip() for item in content_raw.split(",") if item.strip()),
    )
    sections = _author_sections(input_fn=input_fn, output=output, clear_fn=clear_fn)
    if sections is None:
        return
    audiences = _author_audiences(input_fn=input_fn, output=output, clear_fn=clear_fn)
    if audiences is None:
        return
    reference = ProfileRevisionRef(portfolio_profile_id=profile_id, profile_revision=revision_number)
    requirements = _author_requirements(reference, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if requirements is None:
        return
    clear_fn()
    _write(output, "Authority and Limitations", "")
    source_raw = _read(input_fn, "Source authority references (comma-separated, optional): ")
    limitation_raw = _read(input_fn, "Known limitation (optional): ")
    revision = PortfolioProfileRevision(
        portfolio_profile_id=profile_id,
        profile_revision=revision_number,
        profile_family_id=family.profile_family_id,
        predecessor_revision=predecessor,
        label=label,
        purpose_kind=family.purpose_kind,
        applicability=applicability,
        sections=sections,
        audience_rules=audiences,
        created_at=datetime.now(timezone.utc),
        created_by=actor,
        source_authority_references=tuple(item.strip() for item in source_raw.split(",") if item.strip()),
        known_limitations=(limitation_raw,) if limitation_raw else (),
    )
    clear_fn()
    _write(
        output,
        "Review Profile Revision",
        "",
        f"Profile: {profile_id}@{revision_number}",
        f"Purpose: {revision.purpose_kind}",
        f"Sections: {len(sections)}",
        f"Requirements: {len(requirements)}",
        f"Audience rules: {len(audiences)}",
        "",
        "Saving creates an immutable Revision. It does not activate it.",
        "",
    )
    if not _confirm("SAVE", input_fn=input_fn):
        return
    create_profile_revision(workspace, revision, requirements, expected_state_revision=expected)
    _show_success("Profile Revision saved. It remains inactive until explicitly activated.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _activate(
    workspace: Path, session: ProfileMenuSession, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    selected = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if selected is None:
        return
    context = _authority_reason(session, "Activate Profile Revision", input_fn=input_fn, output=output, clear_fn=clear_fn)
    if context is None:
        return
    actor, authority, reason = context
    clear_fn()
    _write(output, "Activate Profile Revision", "", f"Profile: {selected.reference.portfolio_profile_id}@{selected.reference.profile_revision}", f"Requirements: {selected.requirement_count}", "", "Activation makes this exact Revision eligible for new Bindings when applicable.", "")
    if not _confirm("ACTIVATE", input_fn=input_fn):
        return
    activate_profile_revision(workspace, selected.reference, actor=actor, reason=reason, authority_reference=authority, expected_state_revision=expected)
    _show_success("Profile Revision activated.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _binding_context(
    revision: PortfolioProfileRevision,
    *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> ProfileBindingContext | None:
    applicability = revision.applicability
    if not any((applicability.school_years, applicability.institution_id, applicability.program_id, applicability.content_areas, applicability.effective_from, applicability.effective_through)):
        return ProfileBindingContext()
    clear_fn()
    _write(output, "Binding Context", "", "Only fields required by this Profile are shown.")
    school_year = _read(input_fn, "School year: ") if applicability.school_years else None
    institution_id = _read(input_fn, "Institution ID: ") if applicability.institution_id is not None else None
    program_id = _read(input_fn, "Program ID: ") if applicability.program_id is not None else None
    content_area = _read(input_fn, "Content area: ") if applicability.content_areas else None
    as_of: date | None = None
    if applicability.effective_from is not None or applicability.effective_through is not None:
        raw = _read(input_fn, "As-of date (YYYY-MM-DD): ")
        try:
            as_of = date.fromisoformat(raw)
        except ValueError:
            return None
    return ProfileBindingContext(as_of=as_of, school_year=school_year, institution_id=institution_id, program_id=program_id, content_area=content_area)


def _bind(
    workspace: Path, session: ProfileMenuSession, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    portfolio_id = _choose_portfolio(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, require_binding=False)
    if portfolio_id is None:
        return
    selected = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, bindable_only=True)
    if selected is None:
        return
    revision = get_profile_revision(workspace, selected.reference)
    binding_context = _binding_context(revision, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if binding_context is None:
        return
    context = _authority_reason(session, "Bind Portfolio to Profile", input_fn=input_fn, output=output, clear_fn=clear_fn)
    if context is None:
        return
    actor, _authority, reason = context
    clear_fn()
    _write(output, "Bind Portfolio to Profile", "", f"Portfolio: {portfolio_id}", f"Profile: {selected.reference.portfolio_profile_id}@{selected.reference.profile_revision}", "", "This exact Binding remains until explicitly migrated.", "")
    if not _confirm("BIND", input_fn=input_fn):
        return
    bind_portfolio_profile(workspace, portfolio_id, selected.reference, actor=actor, binding_reason=reason, context=binding_context, expected_state_revision=expected)
    _show_success("Portfolio Profile Binding created.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _render_analysis(output: TextIO, analysis: ProfileMigrationAnalysis) -> None:
    impact = analysis.requirement_impact
    _write(
        output,
        f"Source: {analysis.source_profile_revision.portfolio_profile_id}@{analysis.source_profile_revision.profile_revision}",
        f"Target: {analysis.target_profile_revision.portfolio_profile_id}@{analysis.target_profile_revision.profile_revision}",
        "",
        f"Unchanged: {len(impact.unchanged)}",
        f"Added: {len(impact.added)}",
        f"Removed: {len(impact.removed)}",
        f"Replaced: {len(impact.replaced)}",
        f"Materially changed: {len(impact.materially_changed)}",
        f"Unresolved mapping: {len(impact.unresolved_mapping)}",
        f"Affected sections: {len(analysis.affected_section_ids)}",
        f"Potentially affected selections: {analysis.potentially_affected_selection_count}",
        f"Reapproval requirements: {len(analysis.reapproval_requirement_ids)}",
    )


def _migrate(
    workspace: Path, session: ProfileMenuSession, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    portfolio_id = _choose_portfolio(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, require_binding=True)
    if portfolio_id is None:
        return
    current = get_portfolio_profile_binding(workspace, portfolio_id)
    if current is None:
        return
    target = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, bindable_only=True, exclude=current.profile_revision)
    if target is None:
        return
    target_revision = get_profile_revision(workspace, target.reference)
    binding_context = _binding_context(target_revision, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if binding_context is None:
        return
    analysis = analyze_profile_migration(workspace, portfolio_id, target.reference, context=binding_context)
    clear_fn()
    _write(output, "Profile Migration Analysis", "")
    _render_analysis(output, analysis)
    if analysis.blocked:
        _write(output, "", "Migration is blocked until unresolved requirement mappings are corrected.")
        _pause(input_fn)
        return
    context = _authority_reason(session, "Migrate Portfolio Profile", input_fn=input_fn, output=output, clear_fn=clear_fn)
    if context is None:
        return
    actor, authority, reason = context
    clear_fn()
    _write(output, "Confirm Profile Migration", "")
    _render_analysis(output, analysis)
    _write(output, "", "Existing Portfolio content is preserved but is not automatically declared sufficient under the target Profile.", "")
    if not _confirm("MIGRATE", input_fn=input_fn):
        return
    migrate_portfolio_profile(workspace, portfolio_id, target.reference, actor=actor, migration_reason=reason, authority_reference=authority, context=binding_context, expected_state_revision=expected)
    _show_success("Portfolio migrated with a successor Profile Binding.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _overlay(
    workspace: Path, session: ProfileMenuSession, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    component = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, bindable_only=True)
    if component is None:
        return
    context = _authority_reason(session, "Create Local Profile Overlay", input_fn=input_fn, output=output, clear_fn=clear_fn)
    if context is None:
        return
    actor, authority, _reason = context
    clear_fn()
    _write(output, "Local Profile Overlay", "", "The teacher menu supports explicit requirement additions/replacements.")
    overlay_id = _read(input_fn, "Overlay ID: ")
    revision_number = _ask_positive_int(input_fn, "Overlay revision: ")
    label = _read(input_fn, "Label: ")
    count = _ask_positive_int(input_fn, "Number of requirement changes: ")
    if not overlay_id or revision_number is None or not label or count is None:
        return
    changes: list[ProfileOverlayRequirementChange] = []
    for index in range(1, count + 1):
        clear_fn()
        _write(output, f"Overlay Requirement Change {index} of {count}", "", "1. Add requirement", "2. Replace requirement")
        action_raw = _read(input_fn, "Choice: ")
        action = {"1": "add", "2": "replace"}.get(action_raw)
        if action is None:
            return
        requirement_id = _read(input_fn, "New requirement ID: ")
        replaces = _read(input_fn, "Replaces requirement ID: ") if action == "replace" else None
        kind = _read(input_fn, "Kind: ")
        obligation = _read(input_fn, "Obligation: ")
        title = _read(input_fn, "Title: ")
        statement = _read(input_fn, "Policy statement: ")
        scope_kind = _read(input_fn, "Scope kind: ")
        scope_reference = _read(input_fn, "Scope reference (optional): ") or None
        satisfaction = _read(input_fn, "Satisfaction class: ")
        requirement = ProfileOverlayRequirement(requirement_id=requirement_id, requirement_kind=kind, obligation=obligation, title=title, statement=statement, scope_kind=scope_kind, scope_reference=scope_reference, satisfaction_class=satisfaction, authority_references=(authority,), replaces_requirement_id=replaces or None)
        changes.append(ProfileOverlayRequirementChange(action=action, requirement=requirement))
    overlay = PortfolioProfileOverlayRevision(
        overlay_id=overlay_id,
        overlay_revision=revision_number,
        predecessor_overlay_revision=None,
        label=label,
        purpose_kind=component.purpose_kind,
        created_at=datetime.now(timezone.utc),
        created_by=actor,
        authority_reference=authority,
        component_revisions=(component.reference,),
        requirement_changes=tuple(changes),
    )
    clear_fn()
    _write(output, "Review Local Overlay", "", f"Overlay: {overlay_id}@{revision_number}", f"Base Profile: {component.reference.portfolio_profile_id}@{component.reference.profile_revision}", f"Requirement changes: {len(changes)}", "", "The Overlay is immutable and does not change its base Profile.", "")
    if not _confirm("SAVE", input_fn=input_fn):
        return
    create_profile_overlay(workspace, overlay, expected_state_revision=expected)
    _show_success("Local Overlay Revision saved.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _compose(
    workspace: Path, session: ProfileMenuSession, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    expected = observe_profile_state_revision(workspace)
    component = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn, bindable_only=True)
    if component is None:
        return
    state, _ = load_profile_state(workspace)
    compatible_overlays = tuple(item for item in state.overlays if component.reference in item.component_revisions)
    clear_fn()
    _write(output, "Select Local Overlay", "")
    if not compatible_overlays:
        _write(output, "No local Overlay Revisions reference this Profile.")
        _pause(input_fn)
        return
    for index, overlay in enumerate(compatible_overlays, start=1):
        _write(output, f"{index}. {overlay.label} — {overlay.overlay_id}@{overlay.overlay_revision}")
    _nav(output)
    _write(output, "")
    raw = _read(input_fn, "Choice: ")
    if not raw.isdigit() or not (1 <= int(raw) <= len(compatible_overlays)):
        return
    overlay = compatible_overlays[int(raw) - 1]
    actor = _ensure_actor(session, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if actor is None:
        return
    clear_fn()
    _write(output, "Effective Profile Identity", "")
    profile_id = _read(input_fn, "Effective Profile series ID: ")
    revision_number = _ask_positive_int(input_fn, "Effective revision: ")
    label = _read(input_fn, "Effective Profile label: ")
    family_id = _read(input_fn, "Profile Family ID (optional): ") or None
    authority = _read(input_fn, "Composition authority/reference: ")
    if not profile_id or revision_number is None or not label or not authority:
        return
    base = get_profile_revision(workspace, component.reference)
    sections = tuple(sorted((*base.sections, *overlay.section_additions), key=lambda item: item.order))
    audiences = tuple(sorted((*base.audience_rules, *overlay.audience_rule_additions), key=lambda item: item.audience_rule_id))
    effective = PortfolioProfileRevision(
        portfolio_profile_id=profile_id,
        profile_revision=revision_number,
        profile_family_id=family_id,
        predecessor_revision=None,
        label=label,
        purpose_kind=base.purpose_kind,
        applicability=base.applicability,
        sections=sections,
        audience_rules=audiences,
        created_at=datetime.now(timezone.utc),
        created_by=actor,
        source_authority_references=base.source_authority_references,
        known_limitations=tuple(dict.fromkeys((*base.known_limitations, *overlay.known_limitations))),
    )
    clear_fn()
    _write(output, "Review Effective Profile", "", f"Profile: {profile_id}@{revision_number}", f"Base: {component.reference.portfolio_profile_id}@{component.reference.profile_revision}", f"Overlay: {overlay.overlay_id}@{overlay.overlay_revision}", "", "The result is self-contained. Later component changes will not alter it.", "")
    if not _confirm("COMPOSE", input_fn=input_fn):
        return
    compose_profile_revision(workspace, effective, (component.reference,), (ProfileOverlayRevisionRef(overlay_id=overlay.overlay_id, overlay_revision=overlay.overlay_revision),), actor=actor, authority_reference=authority, expected_state_revision=expected)
    _show_success("Effective Profile Revision composed. It remains inactive until activated.", input_fn=input_fn, output=output, clear_fn=clear_fn)


def _view_profiles(
    workspace: Path, *, input_fn: InputFunction, output: TextIO, clear_fn: ClearFunction
) -> None:
    selected = _choose_revision(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn)
    if selected is None:
        return
    revision = get_profile_revision(workspace, selected.reference)
    clear_fn()
    _write(output, revision.label, "", f"Profile: {selected.reference.portfolio_profile_id}@{selected.reference.profile_revision}", f"Purpose: {revision.purpose_kind}", f"Lifecycle: {selected.lifecycle_status}", f"Bindable: {'yes' if selected.bindable else 'no'}", f"Sections: {len(revision.sections)}", f"Requirements: {selected.requirement_count}", f"Audience rules: {len(revision.audience_rules)}")
    _pause(input_fn)


def run_profile_menu(
    *,
    input_fn: InputFunction = input,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    """Run teacher Profile workflows using shared services and low-density screens."""
    workspace = resolve_workspace_root()
    session = ProfileMenuSession()
    while True:
        clear_fn()
        _write(
            output,
            "Portfolio Profiles",
            "",
            "1. View Profiles",
            "2. Create Profile Family",
            "3. Create Profile Revision",
            "4. Activate Profile Revision",
            "5. Bind Portfolio to Profile",
            "6. Migrate Portfolio Profile",
            "7. Local Profile Overlay",
            "8. Compose Effective Profile",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _show_help(output, input_fn)
            continue
        navigation = _navigation(choice)
        if navigation is NavigationChoice.BACK:
            return
        try:
            if choice == "1":
                _view_profiles(workspace, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "2":
                _create_family(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "3":
                _create_revision(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "4":
                _activate(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "5":
                _bind(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "6":
                _migrate(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "7":
                _overlay(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            elif choice == "8":
                _compose(workspace, session, input_fn=input_fn, output=output, clear_fn=clear_fn)
            else:
                _write(output, "Please choose 1-8, H, B, M, or Q.")
                _pause(input_fn)
        except (ProfileWorkflowError, VitrineStorageError, ValueError) as error:
            clear_fn()
            code = error.code if isinstance(error, ProfileWorkflowError) else "profile_workflow_error"
            _write(output, f"Profile problem [{code}]: {error}")
            _pause(input_fn)


__all__ = ["ProfileMenuSession", "run_profile_menu"]
