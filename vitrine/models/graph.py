"""Pure deterministic validation for complete Vitrine record graphs."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, fields
from typing import TypeVar

from .audiences import AudienceContext
from .candidates import CandidateEvaluation, PortfolioCandidate
from .curation import (
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    WorkingPortfolioCompositionRevision,
)
from .errors import (
    ValidationIssue,
    VitrineModelValidationError,
    VitrineRecordGraphError,
)
from .identity import (
    Portfolio,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    SnapshotEditionRef,
)
from .profiles import (
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileRevision,
)
from .snapshots import (
    SnapshotEdition,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
)

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)
S = TypeVar("S", bound=Hashable)


@dataclass(frozen=True, slots=True, kw_only=True)
class VitrineRecordGraph:
    portfolios: tuple[Portfolio, ...] = ()
    portfolio_subjects: tuple[PortfolioSubject, ...] = ()
    subject_links: tuple[PortfolioSubjectClassLink, ...] = ()
    profile_families: tuple[PortfolioProfileFamily, ...] = ()
    profile_revisions: tuple[PortfolioProfileRevision, ...] = ()
    profile_bindings: tuple[PortfolioProfileBinding, ...] = ()
    candidate_evaluations: tuple[CandidateEvaluation, ...] = ()
    candidates: tuple[PortfolioCandidate, ...] = ()
    selections: tuple[PortfolioSelection, ...] = ()
    placements: tuple[PortfolioPlacement, ...] = ()
    arrangements: tuple[SectionArrangementRevision, ...] = ()
    compositions: tuple[WorkingPortfolioCompositionRevision, ...] = ()
    audience_contexts: tuple[AudienceContext, ...] = ()
    materializations: tuple[SnapshotMaterializationRecord, ...] = ()
    snapshot_entries: tuple[SnapshotEntry, ...] = ()
    snapshot_omissions: tuple[SnapshotOmission, ...] = ()
    snapshot_manifests: tuple[SnapshotManifest, ...] = ()
    snapshot_seals: tuple[SnapshotSeal, ...] = ()
    snapshot_editions: tuple[SnapshotEdition, ...] = ()

    def __post_init__(self) -> None:
        for graph_field in fields(self):
            field_name = graph_field.name
            raw_values = getattr(self, field_name)
            if isinstance(raw_values, (str, bytes)):
                raise VitrineModelValidationError(
                    f"{field_name} must be an iterable record collection."
                )
            try:
                values = tuple(raw_values)
            except TypeError as error:
                raise VitrineModelValidationError(
                    f"{field_name} must be an iterable record collection."
                ) from error
            expected_type = GRAPH_COLLECTION_TYPES[field_name]
            for index, item in enumerate(values):
                if type(item) is not expected_type:
                    raise VitrineModelValidationError(
                        f"{field_name}[{index}] must be "
                        f"{expected_type.__name__}."
                    )
            object.__setattr__(self, field_name, values)


GRAPH_COLLECTION_TYPES: dict[str, type[object]] = {
    "portfolios": Portfolio,
    "portfolio_subjects": PortfolioSubject,
    "subject_links": PortfolioSubjectClassLink,
    "profile_families": PortfolioProfileFamily,
    "profile_revisions": PortfolioProfileRevision,
    "profile_bindings": PortfolioProfileBinding,
    "candidate_evaluations": CandidateEvaluation,
    "candidates": PortfolioCandidate,
    "selections": PortfolioSelection,
    "placements": PortfolioPlacement,
    "arrangements": SectionArrangementRevision,
    "compositions": WorkingPortfolioCompositionRevision,
    "audience_contexts": AudienceContext,
    "materializations": SnapshotMaterializationRecord,
    "snapshot_entries": SnapshotEntry,
    "snapshot_omissions": SnapshotOmission,
    "snapshot_manifests": SnapshotManifest,
    "snapshot_seals": SnapshotSeal,
    "snapshot_editions": SnapshotEdition,
}


def _index(values: Iterable[T], key: Callable[[T], K]) -> tuple[dict[K, T], set[K]]:
    result: dict[K, T] = {}
    duplicates: set[K] = set()
    for item in values:
        identity = key(item)
        if identity in result:
            duplicates.add(identity)
        else:
            result[identity] = item
    return result, duplicates


def _issue(
    code: str,
    message: str,
    record_type: str | None = None,
    record_id: str | None = None,
    field_path: tuple[str | int, ...] = (),
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        record_type=record_type,
        record_id=record_id,
        field_path=field_path,
    )


def _profile_key(value: PortfolioProfileRevision) -> tuple[str, int]:
    return value.portfolio_profile_id, value.profile_revision


def _composition_key(
    value: WorkingPortfolioCompositionRevision,
) -> tuple[str, int]:
    return value.portfolio_id, value.composition_revision


def _edition_key(value: SnapshotEdition) -> tuple[str, int]:
    return value.snapshot_series_id, value.edition_number


def _detect_chain_issues(
    values: Iterable[T],
    *,
    id_of: Callable[[T], K],
    predecessor_of: Callable[[T], K | None],
    series_of: Callable[[T], S],
    code_prefix: str,
    record_type: str,
) -> list[ValidationIssue]:
    value_tuple = tuple(values)
    items = {id_of(item): item for item in value_tuple}
    issues: list[ValidationIssue] = []
    successors: dict[K, list[K]] = {}
    for item in value_tuple:
        current = id_of(item)
        predecessor = predecessor_of(item)
        if predecessor is None:
            continue
        predecessor_item = items.get(predecessor)
        if predecessor_item is None:
            issues.append(
                _issue(
                    f"{code_prefix}.predecessor_missing",
                    "Referenced predecessor does not exist.",
                    record_type,
                    str(current),
                )
            )
            continue
        if series_of(predecessor_item) != series_of(item):
            issues.append(
                _issue(
                    f"{code_prefix}.predecessor_series_mismatch",
                    "Predecessor belongs to another record series.",
                    record_type,
                    str(current),
                )
            )
        successors.setdefault(predecessor, []).append(current)
    for predecessor, successor_ids in successors.items():
        if len(successor_ids) > 1:
            issues.append(
                _issue(
                    f"{code_prefix}.branch",
                    "A predecessor has more than one successor.",
                    record_type,
                    str(predecessor),
                )
            )
    for item in value_tuple:
        start = id_of(item)
        seen: set[K] = set()
        current = start
        while current in items:
            if current in seen:
                issues.append(
                    _issue(
                        f"{code_prefix}.cycle",
                        "Predecessor chain contains a cycle.",
                        record_type,
                        str(start),
                    )
                )
                break
            seen.add(current)
            predecessor = predecessor_of(items[current])
            if predecessor is None:
                break
            current = predecessor
    return issues


def collect_record_graph_issues(
    graph: VitrineRecordGraph,
) -> tuple[ValidationIssue, ...]:
    """Return all deterministic cross-record issues without filesystem access."""
    if not isinstance(graph, VitrineRecordGraph):
        raise TypeError("graph must be a VitrineRecordGraph.")
    issues: list[ValidationIssue] = []

    portfolios, duplicate_portfolios = _index(
        graph.portfolios, lambda item: item.portfolio_id
    )
    subjects, duplicate_subjects = _index(
        graph.portfolio_subjects, lambda item: item.portfolio_subject_id
    )
    links, duplicate_links = _index(
        graph.subject_links, lambda item: item.subject_link_id
    )
    families, duplicate_families = _index(
        graph.profile_families, lambda item: item.profile_family_id
    )
    profiles, duplicate_profiles = _index(graph.profile_revisions, _profile_key)
    bindings, duplicate_bindings = _index(
        graph.profile_bindings, lambda item: item.profile_binding_id
    )
    evaluations, duplicate_evaluations = _index(
        graph.candidate_evaluations, lambda item: item.candidate_evaluation_id
    )
    candidates, duplicate_candidates = _index(
        graph.candidates, lambda item: item.candidate_id
    )
    selections, duplicate_selections = _index(
        graph.selections, lambda item: item.selection_id
    )
    placements, duplicate_placements = _index(
        graph.placements, lambda item: item.placement_id
    )
    arrangements, duplicate_arrangements = _index(
        graph.arrangements, lambda item: item.arrangement_id
    )
    compositions, duplicate_compositions = _index(
        graph.compositions, _composition_key
    )
    audiences, duplicate_audiences = _index(
        graph.audience_contexts, lambda item: item.audience_context_id
    )
    materializations, duplicate_materializations = _index(
        graph.materializations, lambda item: item.materialization_id
    )
    entries, duplicate_entries = _index(
        graph.snapshot_entries, lambda item: item.snapshot_entry_id
    )
    omissions, duplicate_omissions = _index(
        graph.snapshot_omissions, lambda item: item.snapshot_omission_id
    )
    manifests, duplicate_manifests = _index(
        graph.snapshot_manifests, lambda item: item.manifest_id
    )
    seals, duplicate_seals = _index(
        graph.snapshot_seals, lambda item: item.seal_id
    )
    editions, duplicate_editions = _index(graph.snapshot_editions, _edition_key)

    duplicate_groups = (
        (duplicate_portfolios, "portfolio", "portfolio.duplicate"),
        (duplicate_subjects, "portfolio_subject", "portfolio_subject.duplicate"),
        (duplicate_links, "portfolio_subject_class_link", "subject_link.duplicate"),
        (duplicate_families, "portfolio_profile_family", "profile.family_duplicate"),
        (duplicate_profiles, "portfolio_profile_revision", "profile.revision_duplicate"),
        (duplicate_bindings, "portfolio_profile_binding", "profile_binding.duplicate"),
        (duplicate_evaluations, "candidate_evaluation", "candidate.evaluation_duplicate"),
        (duplicate_candidates, "portfolio_candidate", "candidate.duplicate"),
        (duplicate_selections, "portfolio_selection", "selection.duplicate"),
        (duplicate_placements, "portfolio_placement", "placement.duplicate"),
        (duplicate_arrangements, "section_arrangement_revision", "arrangement.duplicate"),
        (duplicate_compositions, "working_portfolio_composition_revision", "composition.duplicate"),
        (duplicate_audiences, "audience_context", "audience.duplicate"),
        (duplicate_materializations, "snapshot_materialization", "snapshot.materialization_duplicate"),
        (duplicate_entries, "snapshot_entry", "snapshot.entry_duplicate"),
        (duplicate_omissions, "snapshot_omission", "snapshot.omission_duplicate"),
        (duplicate_manifests, "snapshot_manifest", "snapshot.manifest_duplicate"),
        (duplicate_seals, "snapshot_seal", "snapshot.seal_duplicate"),
        (duplicate_editions, "snapshot_edition", "snapshot.edition_duplicate"),
    )
    for duplicate_ids, record_type, code in duplicate_groups:
        for duplicate_id in duplicate_ids:
            issues.append(
                _issue(code, "Duplicate record identity.", record_type, str(duplicate_id))
            )

    for portfolio in graph.portfolios:
        if portfolio.portfolio_subject_id not in subjects:
            issues.append(
                _issue(
                    "portfolio.subject_missing",
                    "Portfolio Subject does not exist.",
                    portfolio.record_type,
                    portfolio.portfolio_id,
                    ("portfolio_subject_id",),
                )
            )

    student_links: dict[object, str] = {}
    for link in graph.subject_links:
        if link.portfolio_subject_id not in subjects:
            issues.append(
                _issue(
                    "subject_link.subject_missing",
                    "Linked Portfolio Subject does not exist.",
                    link.record_type,
                    link.subject_link_id,
                    ("portfolio_subject_id",),
                )
            )
        prior_subject = student_links.get(link.student_reference)
        if prior_subject is not None and prior_subject != link.portfolio_subject_id:
            issues.append(
                _issue(
                    "subject_link.class_reference_conflict",
                    "One class-qualified student reference is linked to multiple Subjects.",
                    link.record_type,
                    link.subject_link_id,
                    ("student_reference",),
                )
            )
        else:
            student_links[link.student_reference] = link.portfolio_subject_id
    issues.extend(
        _detect_chain_issues(
            graph.subject_links,
            id_of=lambda item: item.subject_link_id,
            predecessor_of=lambda item: item.predecessor_link_id,
            series_of=lambda item: item.portfolio_subject_id,
            code_prefix="subject_link",
            record_type="portfolio_subject_class_link",
        )
    )

    for profile in graph.profile_revisions:
        if profile.profile_family_id is not None and profile.profile_family_id not in families:
            issues.append(
                _issue(
                    "profile.family_missing",
                    "Profile Family does not exist.",
                    profile.record_type,
                    f"{profile.portfolio_profile_id}:{profile.profile_revision}",
                    ("profile_family_id",),
                )
            )
        if profile.predecessor_revision is not None:
            predecessor_key = (
                profile.portfolio_profile_id,
                profile.predecessor_revision,
            )
            if predecessor_key not in profiles:
                issues.append(
                    _issue(
                        "profile.predecessor_missing",
                        "Profile predecessor revision does not exist.",
                        profile.record_type,
                        f"{profile.portfolio_profile_id}:{profile.profile_revision}",
                        ("predecessor_revision",),
                    )
                )

    for binding in graph.profile_bindings:
        if binding.portfolio_id not in portfolios:
            issues.append(
                _issue(
                    "profile_binding.portfolio_missing",
                    "Bound Portfolio does not exist.",
                    binding.record_type,
                    binding.profile_binding_id,
                    ("portfolio_id",),
                )
            )
        profile_key = (
            binding.profile_revision.portfolio_profile_id,
            binding.profile_revision.profile_revision,
        )
        if profile_key not in profiles:
            issues.append(
                _issue(
                    "profile_binding.revision_missing",
                    "Bound Profile Revision does not exist.",
                    binding.record_type,
                    binding.profile_binding_id,
                    ("profile_revision",),
                )
            )
    issues.extend(
        _detect_chain_issues(
            graph.profile_bindings,
            id_of=lambda item: item.profile_binding_id,
            predecessor_of=lambda item: item.predecessor_binding_id,
            series_of=lambda item: item.portfolio_id,
            code_prefix="profile_binding",
            record_type="portfolio_profile_binding",
        )
    )

    def profile_for_binding(binding_id: str) -> PortfolioProfileRevision | None:
        binding = bindings.get(binding_id)
        if binding is None:
            return None
        key = (
            binding.profile_revision.portfolio_profile_id,
            binding.profile_revision.profile_revision,
        )
        return profiles.get(key)

    for evaluation in graph.candidate_evaluations:
        evaluation_portfolio = portfolios.get(evaluation.portfolio_id)
        if evaluation_portfolio is None:
            issues.append(
                _issue(
                    "candidate.evaluation_portfolio_missing",
                    "Evaluation Portfolio does not exist.",
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
        elif evaluation_portfolio.portfolio_subject_id != evaluation.portfolio_subject_id:
            issues.append(
                _issue(
                    "candidate.evaluation_subject_mismatch",
                    "Evaluation Subject does not match Portfolio Subject.",
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
        evaluation_binding = bindings.get(evaluation.profile_binding_id)
        if evaluation_binding is None:
            issues.append(
                _issue(
                    "candidate.evaluation_binding_missing",
                    "Evaluation Profile Binding does not exist.",
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
        else:
            if evaluation_binding.portfolio_id != evaluation.portfolio_id:
                issues.append(
                    _issue(
                        "candidate.evaluation_binding_mismatch",
                        "Evaluation Binding belongs to another Portfolio.",
                        evaluation.record_type,
                        evaluation.candidate_evaluation_id,
                    )
                )
            if evaluation_binding.profile_revision != evaluation.profile_revision:
                issues.append(
                    _issue(
                        "candidate.evaluation_profile_mismatch",
                        "Evaluation Profile Revision differs from Binding.",
                        evaluation.record_type,
                        evaluation.candidate_evaluation_id,
                    )
                )
        evaluation_profile = profile_for_binding(evaluation.profile_binding_id)
        if evaluation_profile is not None:
            section_ids = {item.section_id for item in evaluation_profile.sections}
            invalid = set(evaluation.eligible_section_ids) - section_ids
            if invalid:
                issues.append(
                    _issue(
                        "candidate.eligible_section_missing",
                        "Evaluation references an unknown eligible section.",
                        evaluation.record_type,
                        evaluation.candidate_evaluation_id,
                    )
                )
        if evaluation.source_endpoint is not None:
            for assertion in evaluation.source_endpoint.subject_relationship_assertions:
                if assertion.portfolio_subject_id != evaluation.portfolio_subject_id:
                    issues.append(
                        _issue(
                            "source.subject_assertion_mismatch",
                            "Source assertion belongs to another Portfolio Subject.",
                            evaluation.record_type,
                            evaluation.candidate_evaluation_id,
                        )
                    )
                assertion_link = links.get(assertion.subject_link_id)
                if assertion_link is None:
                    issues.append(
                        _issue(
                            "source.subject_link_missing",
                            "Source assertion Subject link does not exist.",
                            evaluation.record_type,
                            evaluation.candidate_evaluation_id,
                        )
                    )
                elif assertion_link.portfolio_subject_id != assertion.portfolio_subject_id:
                    issues.append(
                        _issue(
                            "source.subject_link_mismatch",
                            "Source assertion Subject link belongs to another Subject.",
                            evaluation.record_type,
                            evaluation.candidate_evaluation_id,
                        )
                    )

    for candidate in graph.candidates:
        candidate_evaluation = evaluations.get(candidate.candidate_evaluation_id)
        if candidate_evaluation is None:
            issues.append(
                _issue(
                    "candidate.evaluation_missing",
                    "Candidate Evaluation does not exist.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
            continue
        if candidate_evaluation.outcome not in {"eligible", "conditionally_eligible"}:
            issues.append(
                _issue(
                    "candidate.positive_outcome_required",
                    "Candidate requires a positive Evaluation outcome.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
        context = (
            candidate.portfolio_id,
            candidate.portfolio_subject_id,
            candidate.profile_binding_id,
            candidate.profile_revision,
        )
        evaluation_context = (
            candidate_evaluation.portfolio_id,
            candidate_evaluation.portfolio_subject_id,
            candidate_evaluation.profile_binding_id,
            candidate_evaluation.profile_revision,
        )
        if context != evaluation_context:
            issues.append(
                _issue(
                    "candidate.evaluation_context_mismatch",
                    "Candidate and Evaluation contexts differ.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
        if candidate_evaluation.source_endpoint != candidate.source_endpoint:
            issues.append(
                _issue(
                    "candidate.source_endpoint_mismatch",
                    "Candidate endpoint differs from evaluated endpoint.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
        if not set(candidate.eligible_section_ids).issubset(
            set(candidate_evaluation.eligible_section_ids)
        ):
            issues.append(
                _issue(
                    "candidate.eligible_section_mismatch",
                    "Candidate expands the Evaluation's eligible sections.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
    issues.extend(
        _detect_chain_issues(
            graph.candidates,
            id_of=lambda item: item.candidate_id,
            predecessor_of=lambda item: item.predecessor_candidate_id,
            series_of=lambda item: (
                item.portfolio_id,
                item.profile_binding_id,
            ),
            code_prefix="candidate",
            record_type="portfolio_candidate",
        )
    )

    for selection in graph.selections:
        selected_candidate = candidates.get(selection.candidate_id)
        selected_evaluation = evaluations.get(selection.candidate_evaluation_id)
        if selected_candidate is None:
            issues.append(
                _issue(
                    "selection.candidate_missing",
                    "Selected Candidate does not exist.",
                    selection.record_type,
                    selection.selection_id,
                )
            )
        else:
            expected = (
                selected_candidate.portfolio_id,
                selected_candidate.portfolio_subject_id,
                selected_candidate.profile_binding_id,
                selected_candidate.profile_revision,
                selected_candidate.candidate_evaluation_id,
            )
            actual = (
                selection.portfolio_id,
                selection.portfolio_subject_id,
                selection.profile_binding_id,
                selection.profile_revision,
                selection.candidate_evaluation_id,
            )
            if expected != actual:
                issues.append(
                    _issue(
                        "selection.candidate_context_mismatch",
                        "Selection context differs from Candidate context.",
                        selection.record_type,
                        selection.selection_id,
                    )
                )
        if selected_evaluation is None:
            issues.append(
                _issue(
                    "selection.evaluation_missing",
                    "Selection Evaluation does not exist.",
                    selection.record_type,
                    selection.selection_id,
                )
            )
    issues.extend(
        _detect_chain_issues(
            graph.selections,
            id_of=lambda item: item.selection_id,
            predecessor_of=lambda item: item.predecessor_selection_id,
            series_of=lambda item: (item.portfolio_id, item.profile_binding_id),
            code_prefix="selection",
            record_type="portfolio_selection",
        )
    )

    candidate_selection_keys: dict[tuple[str, str, str], str] = {}
    for selection in graph.selections:
        key = (selection.portfolio_id, selection.profile_binding_id, selection.candidate_id)
        prior = candidate_selection_keys.get(key)
        if prior is not None and selection.predecessor_selection_id != prior:
            issues.append(
                _issue(
                    "selection.candidate_duplicate",
                    "Candidate has contradictory Selections in one Binding.",
                    selection.record_type,
                    selection.selection_id,
                )
            )
        else:
            candidate_selection_keys[key] = selection.selection_id

    for placement in graph.placements:
        placement_selection = selections.get(placement.selection_id)
        if placement_selection is None:
            issues.append(
                _issue(
                    "placement.selection_missing",
                    "Placement Selection does not exist.",
                    placement.record_type,
                    placement.placement_id,
                )
            )
        else:
            if (
                placement.portfolio_id != placement_selection.portfolio_id
                or placement.profile_binding_id != placement_selection.profile_binding_id
            ):
                issues.append(
                    _issue(
                        "placement.selection_context_mismatch",
                        "Placement context differs from Selection context.",
                        placement.record_type,
                        placement.placement_id,
                    )
                )
        placement_profile = profile_for_binding(placement.profile_binding_id)
        if placement_profile is None:
            continue
        section = next(
            (item for item in placement_profile.sections if item.section_id == placement.section_id),
            None,
        )
        if section is None:
            issues.append(
                _issue(
                    "placement.section_missing",
                    "Placement section does not exist in the Profile Revision.",
                    placement.record_type,
                    placement.placement_id,
                )
            )
        elif section.obligation == "prohibited":
            issues.append(
                _issue(
                    "placement.section_prohibited",
                    "Prohibited Profile section cannot contain Placements.",
                    placement.record_type,
                    placement.placement_id,
                )
            )

    placement_arrangements: dict[str, str] = {}
    for arrangement in graph.arrangements:
        for placement_id in arrangement.placement_ids:
            arranged_placement = placements.get(placement_id)
            if arranged_placement is None:
                issues.append(
                    _issue(
                        "arrangement.placement_missing",
                        "Arrangement Placement does not exist.",
                        arrangement.record_type,
                        arrangement.arrangement_id,
                    )
                )
                continue
            if (
                arranged_placement.portfolio_id != arrangement.portfolio_id
                or arranged_placement.profile_binding_id != arrangement.profile_binding_id
                or arranged_placement.section_id != arrangement.section_id
            ):
                issues.append(
                    _issue(
                        "arrangement.placement_context_mismatch",
                        "Arrangement contains a Placement from another context.",
                        arrangement.record_type,
                        arrangement.arrangement_id,
                    )
                )
            prior = placement_arrangements.get(placement_id)
            if prior is not None and prior != arrangement.arrangement_id:
                issues.append(
                    _issue(
                        "arrangement.placement_duplicate",
                        "Placement appears in more than one Arrangement.",
                        arrangement.record_type,
                        arrangement.arrangement_id,
                    )
                )
            placement_arrangements[placement_id] = arrangement.arrangement_id
    issues.extend(
        _detect_chain_issues(
            graph.arrangements,
            id_of=lambda item: item.arrangement_id,
            predecessor_of=lambda item: item.predecessor_arrangement_id,
            series_of=lambda item: (
                item.portfolio_id,
                item.profile_binding_id,
                item.section_id,
            ),
            code_prefix="arrangement",
            record_type="section_arrangement_revision",
        )
    )

    for composition in graph.compositions:
        composition_portfolio = portfolios.get(composition.portfolio_id)
        if composition_portfolio is None:
            issues.append(
                _issue(
                    "composition.portfolio_missing",
                    "Composition Portfolio does not exist.",
                    composition.record_type,
                    f"{composition.portfolio_id}:{composition.composition_revision}",
                )
            )
        elif composition_portfolio.portfolio_subject_id != composition.portfolio_subject_id:
            issues.append(
                _issue(
                    "composition.subject_mismatch",
                    "Composition Subject differs from Portfolio Subject.",
                    composition.record_type,
                    f"{composition.portfolio_id}:{composition.composition_revision}",
                )
            )
        composition_binding = bindings.get(composition.profile_binding_id)
        if composition_binding is None:
            issues.append(
                _issue(
                    "composition.binding_missing",
                    "Composition Binding does not exist.",
                    composition.record_type,
                    f"{composition.portfolio_id}:{composition.composition_revision}",
                )
            )
        elif (
            composition_binding.portfolio_id != composition.portfolio_id
            or composition_binding.profile_revision != composition.profile_revision
        ):
            issues.append(
                _issue(
                    "composition.binding_mismatch",
                    "Composition Binding or Profile Revision does not match.",
                    composition.record_type,
                    f"{composition.portfolio_id}:{composition.composition_revision}",
                )
            )
        for selection_id in composition.selection_ids:
            composition_selection = selections.get(selection_id)
            if composition_selection is None:
                issues.append(
                    _issue(
                        "composition.selection_missing",
                        "Composition Selection does not exist.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
            elif (
                composition_selection.portfolio_id != composition.portfolio_id
                or composition_selection.profile_binding_id != composition.profile_binding_id
            ):
                issues.append(
                    _issue(
                        "composition.selection_context_mismatch",
                        "Composition Selection belongs to another context.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
        for placement_id in composition.placement_ids:
            composition_placement = placements.get(placement_id)
            if composition_placement is None:
                issues.append(
                    _issue(
                        "composition.placement_missing",
                        "Composition Placement does not exist.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
            elif (
                composition_placement.portfolio_id != composition.portfolio_id
                or composition_placement.profile_binding_id != composition.profile_binding_id
            ):
                issues.append(
                    _issue(
                        "composition.placement_context_mismatch",
                        "Composition Placement belongs to another context.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
        included_arrangements = {
            arrangement_id: arrangements.get(arrangement_id)
            for arrangement_id in composition.arrangement_ids
        }
        covered_placement_ids = {
            placement_id
            for composition_arrangement in included_arrangements.values()
            if composition_arrangement is not None
            for placement_id in composition_arrangement.placement_ids
        }
        for placement_id in composition.placement_ids:
            if placement_id not in covered_placement_ids:
                issues.append(
                    _issue(
                        "composition.arrangement_incomplete",
                        "Composition Placement is not covered by an included Arrangement.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
        for arrangement_id in composition.arrangement_ids:
            composition_arrangement = arrangements.get(arrangement_id)
            if composition_arrangement is None:
                issues.append(
                    _issue(
                        "composition.arrangement_missing",
                        "Composition Arrangement does not exist.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
            elif (
                composition_arrangement.portfolio_id != composition.portfolio_id
                or composition_arrangement.profile_binding_id != composition.profile_binding_id
            ):
                issues.append(
                    _issue(
                        "composition.arrangement_context_mismatch",
                        "Composition Arrangement belongs to another context.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
            elif not set(composition_arrangement.placement_ids).issubset(
                composition.placement_ids
            ):
                issues.append(
                    _issue(
                        "composition.arrangement_contains_unlisted_placement",
                        "Composition Arrangement contains an unlisted Placement.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )
        if composition.predecessor_composition_revision is not None:
            predecessor = (
                composition.portfolio_id,
                composition.predecessor_composition_revision,
            )
            if predecessor not in compositions:
                issues.append(
                    _issue(
                        "composition.predecessor_missing",
                        "Composition predecessor revision does not exist.",
                        composition.record_type,
                        f"{composition.portfolio_id}:{composition.composition_revision}",
                    )
                )

    for audience in graph.audience_contexts:
        audience_portfolio = portfolios.get(audience.portfolio_id)
        if audience_portfolio is None or audience_portfolio.portfolio_subject_id != audience.portfolio_subject_id:
            issues.append(
                _issue(
                    "audience.portfolio_context_mismatch",
                    "Audience Portfolio or Subject context is invalid.",
                    audience.record_type,
                    audience.audience_context_id,
                )
            )
        audience_binding = bindings.get(audience.profile_binding_id)
        if audience_binding is None or audience_binding.profile_revision != audience.profile_revision:
            issues.append(
                _issue(
                    "audience.binding_mismatch",
                    "Audience Binding or Profile Revision is invalid.",
                    audience.record_type,
                    audience.audience_context_id,
                )
            )
            continue
        audience_profile = profile_for_binding(audience.profile_binding_id)
        if audience_profile is None:
            continue
        rule = next(
            (
                item
                for item in audience_profile.audience_rules
                if item.audience_rule_id == audience.audience_rule_id
            ),
            None,
        )
        if rule is None:
            issues.append(
                _issue(
                    "audience.profile_rule_missing",
                    "Audience rule does not exist in the Profile Revision.",
                    audience.record_type,
                    audience.audience_context_id,
                )
            )
        else:
            copied = (
                audience.audience_class,
                audience.purpose,
                audience.allowed_content_classes,
                audience.prohibited_content_classes,
                audience.required_review_classes,
                audience.presentation_class,
                audience.retention_policy_reference,
            )
            authoritative = (
                rule.audience_class,
                rule.purpose,
                rule.allowed_content_classes,
                rule.prohibited_content_classes,
                rule.required_review_classes,
                rule.presentation_class,
                rule.retention_policy_reference,
            )
            if copied != authoritative:
                issues.append(
                    _issue(
                        "audience.profile_rule_mismatch",
                        "Audience Context does not reproduce the exact Profile rule.",
                        audience.record_type,
                        audience.audience_context_id,
                    )
                )

    for materialization in graph.materializations:
        edition_key = (
            materialization.snapshot_edition.snapshot_series_id,
            materialization.snapshot_edition.edition_number,
        )
        if edition_key not in editions:
            issues.append(
                _issue(
                    "snapshot.materialization_edition_missing",
                    "Materialization Snapshot Edition does not exist.",
                    materialization.record_type,
                    materialization.materialization_id,
                )
            )
        if (
            materialization.candidate_id is not None
            and materialization.candidate_id not in candidates
        ):
            issues.append(
                _issue(
                    "snapshot.materialization_candidate_missing",
                    "Materialization Candidate does not exist.",
                    materialization.record_type,
                    materialization.materialization_id,
                )
            )
        if (
            materialization.selection_id is not None
            and materialization.selection_id not in selections
        ):
            issues.append(
                _issue(
                    "snapshot.materialization_selection_missing",
                    "Materialization Selection does not exist.",
                    materialization.record_type,
                    materialization.materialization_id,
                )
            )
        if (
            materialization.placement_id is not None
            and materialization.placement_id not in placements
        ):
            issues.append(
                _issue(
                    "snapshot.materialization_placement_missing",
                    "Materialization Placement does not exist.",
                    materialization.record_type,
                    materialization.materialization_id,
                )
            )

    edition_entry_paths: dict[tuple[SnapshotEditionRef, str], str] = {}
    edition_section_ordinals: dict[tuple[SnapshotEditionRef, str, int], str] = {}
    for entry in graph.snapshot_entries:
        entry_materialization = materializations.get(entry.materialization_id)
        if entry_materialization is None:
            issues.append(
                _issue(
                    "snapshot.entry_materialization_missing",
                    "Snapshot Entry Materialization does not exist.",
                    entry.record_type,
                    entry.snapshot_entry_id,
                )
            )
        elif entry_materialization.snapshot_edition != entry.snapshot_edition:
            issues.append(
                _issue(
                    "snapshot.entry_materialization_mismatch",
                    "Snapshot Entry and Materialization identify different Editions.",
                    entry.record_type,
                    entry.snapshot_entry_id,
                )
            )
        entry_path_key = (entry.snapshot_edition, entry.relative_path)
        prior = edition_entry_paths.get(entry_path_key)
        if prior is not None:
            issues.append(
                _issue(
                    "snapshot.entry_path_duplicate",
                    "Snapshot Entry path is duplicated within an Edition.",
                    entry.record_type,
                    entry.snapshot_entry_id,
                )
            )
        edition_entry_paths[entry_path_key] = entry.snapshot_entry_id
        ordinal_key = (entry.snapshot_edition, entry.section_id, entry.ordinal)
        prior_ordinal = edition_section_ordinals.get(ordinal_key)
        if prior_ordinal is not None:
            issues.append(
                _issue(
                    "snapshot.entry_ordinal_duplicate",
                    "Snapshot Entry ordinal is duplicated within a section.",
                    entry.record_type,
                    entry.snapshot_entry_id,
                )
            )
        edition_section_ordinals[ordinal_key] = entry.snapshot_entry_id

    for omission in graph.snapshot_omissions:
        omission_edition_key = (
            omission.snapshot_edition.snapshot_series_id,
            omission.snapshot_edition.edition_number,
        )
        if omission_edition_key not in editions:
            issues.append(
                _issue(
                    "snapshot.omission_edition_missing",
                    "Snapshot Omission Edition does not exist.",
                    omission.record_type,
                    omission.snapshot_omission_id,
                )
            )
        if omission.audience_context_id not in audiences:
            issues.append(
                _issue(
                    "snapshot.omission_audience_missing",
                    "Snapshot Omission Audience Context does not exist.",
                    omission.record_type,
                    omission.snapshot_omission_id,
                )
            )
        for reference, collection, code in (
            (omission.candidate_id, candidates, "snapshot.omission_candidate_missing"),
            (omission.selection_id, selections, "snapshot.omission_selection_missing"),
            (omission.placement_id, placements, "snapshot.omission_placement_missing"),
        ):
            if reference is not None and reference not in collection:
                issues.append(
                    _issue(
                        code,
                        "Snapshot Omission reference does not exist.",
                        omission.record_type,
                        omission.snapshot_omission_id,
                    )
                )

    for manifest in graph.snapshot_manifests:
        edition = editions.get(
            (
                manifest.snapshot_edition.snapshot_series_id,
                manifest.snapshot_edition.edition_number,
            )
        )
        if edition is None:
            issues.append(
                _issue(
                    "snapshot.manifest_edition_missing",
                    "Snapshot Manifest Edition does not exist.",
                    manifest.record_type,
                    manifest.manifest_id,
                )
            )
        else:
            expected_context = (
                edition.portfolio_id,
                edition.portfolio_subject_id,
                edition.profile_binding_id,
                edition.profile_revision,
                edition.composition_revision,
                edition.audience_context_id,
            )
            actual_context = (
                manifest.portfolio_id,
                manifest.portfolio_subject_id,
                manifest.profile_binding_id,
                manifest.profile_revision,
                manifest.composition_revision,
                manifest.audience_context_id,
            )
            if expected_context != actual_context:
                issues.append(
                    _issue(
                        "snapshot.manifest_context_mismatch",
                        "Snapshot Manifest context differs from Edition context.",
                        manifest.record_type,
                        manifest.manifest_id,
                    )
                )
        expected_entry_ids = tuple(
            item.snapshot_entry_id
            for item in graph.snapshot_entries
            if item.snapshot_edition == manifest.snapshot_edition
        )
        expected_omission_ids = tuple(
            item.snapshot_omission_id
            for item in graph.snapshot_omissions
            if item.snapshot_edition == manifest.snapshot_edition
        )
        if (
            manifest.entry_ids != expected_entry_ids
            or manifest.omission_ids != expected_omission_ids
        ):
            issues.append(
                _issue(
                    "snapshot.manifest_inventory_mismatch",
                    "Snapshot Manifest inventory does not match Edition records.",
                    manifest.record_type,
                    manifest.manifest_id,
                )
            )

    for seal in graph.snapshot_seals:
        sealed_manifest = manifests.get(seal.manifest_id)
        if sealed_manifest is None:
            issues.append(
                _issue(
                    "snapshot.seal_manifest_missing",
                    "Snapshot Seal Manifest does not exist.",
                    seal.record_type,
                    seal.seal_id,
                )
            )
        elif sealed_manifest.snapshot_edition != seal.snapshot_edition:
            issues.append(
                _issue(
                    "snapshot.seal_manifest_mismatch",
                    "Snapshot Seal and Manifest identify different Editions.",
                    seal.record_type,
                    seal.seal_id,
                )
            )

    for edition in graph.snapshot_editions:
        edition_ref = edition.reference
        edition_portfolio = portfolios.get(edition.portfolio_id)
        if edition_portfolio is None or edition_portfolio.portfolio_subject_id != edition.portfolio_subject_id:
            issues.append(
                _issue(
                    "snapshot.edition_portfolio_mismatch",
                    "Snapshot Edition Portfolio or Subject context is invalid.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        edition_binding = bindings.get(edition.profile_binding_id)
        if edition_binding is None or edition_binding.profile_revision != edition.profile_revision:
            issues.append(
                _issue(
                    "snapshot.edition_binding_mismatch",
                    "Snapshot Edition Binding or Profile Revision is invalid.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        if (edition.portfolio_id, edition.composition_revision) not in compositions:
            issues.append(
                _issue(
                    "snapshot.edition_composition_missing",
                    "Snapshot Edition Composition does not exist.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        if edition.audience_context_id not in audiences:
            issues.append(
                _issue(
                    "snapshot.edition_audience_missing",
                    "Snapshot Edition Audience Context does not exist.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        edition_manifest = manifests.get(edition.manifest_id)
        if edition_manifest is None or edition_manifest.snapshot_edition != edition_ref:
            issues.append(
                _issue(
                    "snapshot.edition_manifest_mismatch",
                    "Snapshot Edition Manifest is missing or identifies another Edition.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        edition_seal = seals.get(edition.seal_id)
        if edition_seal is None or edition_seal.snapshot_edition != edition_ref or edition_seal.manifest_id != edition.manifest_id:
            issues.append(
                _issue(
                    "snapshot.edition_seal_mismatch",
                    "Snapshot Edition Seal is missing or inconsistent.",
                    edition.record_type,
                    f"{edition.snapshot_series_id}:{edition.edition_number}",
                )
            )
        if edition.predecessor_edition is not None:
            predecessor = (edition.snapshot_series_id, edition.predecessor_edition)
            if predecessor not in editions:
                issues.append(
                    _issue(
                        "snapshot.edition_predecessor_missing",
                        "Snapshot Edition predecessor does not exist.",
                        edition.record_type,
                        f"{edition.snapshot_series_id}:{edition.edition_number}",
                    )
                )

    return tuple(
        sorted(
            issues,
            key=lambda item: (
                item.code,
                item.record_type or "",
                item.record_id or "",
                tuple(str(part) for part in item.field_path),
                item.message,
            ),
        )
    )


def validate_record_graph(graph: VitrineRecordGraph) -> None:
    """Raise when the Vitrine record graph contains relationship errors."""
    issues = collect_record_graph_issues(graph)
    if issues:
        raise VitrineRecordGraphError(issues)


__all__ = [
    "GRAPH_COLLECTION_TYPES",
    "VitrineRecordGraph",
    "collect_record_graph_issues",
    "validate_record_graph",
]
